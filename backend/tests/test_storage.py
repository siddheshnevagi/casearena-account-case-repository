"""Storage backend behavior.

DatabaseStorage is exercised here rather than through the API because the
router tests deliberately pin LocalDiskStorage (see conftest.py) — this is
where the "bytes actually survive a round-trip through Postgres" claim
gets checked, and where the two backends are held to the same contract.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.database
from app.database import Base
# Imported explicitly so CaseFile is registered on Base.metadata before
# create_all() runs below, rather than relying on storage.py's import.
from app.models.case_file import CaseFile  # noqa: F401
from app.services.storage import (
    DatabaseStorage,
    LocalDiskStorage,
    S3CompatibleStorage,
    _build_storage,
)
from tests.conftest import make_pdf_bytes


@pytest.fixture()
def db_storage(monkeypatch):
    """DatabaseStorage bound to a throwaway in-memory database.

    The class imports ``SessionLocal`` lazily inside each method, so
    patching the module attribute is enough to redirect it — no global
    engine reconfiguration needed.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    monkeypatch.setattr(
        app.database,
        "SessionLocal",
        sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True),
    )
    return DatabaseStorage()


def test_database_storage_round_trip(db_storage):
    content = make_pdf_bytes(2048)
    key = db_storage.save(content, "my case.pdf")
    assert db_storage.read(key) == content


def test_database_storage_preserves_file_extension(db_storage):
    key = db_storage.save(make_pdf_bytes(), "quarterly report.pdf")
    assert key.endswith(".pdf")


def test_database_storage_keys_are_unique_per_upload(db_storage):
    content = make_pdf_bytes()
    first = db_storage.save(content, "case.pdf")
    second = db_storage.save(content, "case.pdf")
    # Identical bytes and filename must not collide — uploads are
    # independent objects, and a shared key would let one user's delete
    # remove another user's case.
    assert first != second


def test_database_storage_delete_removes_content(db_storage):
    key = db_storage.save(make_pdf_bytes(), "case.pdf")
    db_storage.delete(key)
    with pytest.raises(FileNotFoundError):
        db_storage.read(key)


def test_database_storage_delete_is_idempotent(db_storage):
    # Matches LocalDiskStorage and S3: routers/cases.py calls delete() as
    # compensating cleanup on a failed upload, so a second delete (or a
    # delete of a never-saved key) must not raise.
    db_storage.delete("nonexistent-key.pdf")


def test_database_storage_read_missing_key_raises_filenotfound(db_storage):
    with pytest.raises(FileNotFoundError):
        db_storage.read("nonexistent-key.pdf")


def test_local_disk_storage_read_missing_key_also_raises_filenotfound(tmp_path):
    # The contract DatabaseStorage above is matching — asserted here so a
    # change to either backend's failure mode breaks a test.
    storage = LocalDiskStorage(str(tmp_path / "uploads"))
    with pytest.raises(FileNotFoundError):
        storage.read("nonexistent-key.pdf")


class TestBackendSelection:
    """``_build_storage`` reads the shared cached Settings instance, so
    these mutate attributes on it in place (see conftest.py's docstring)."""

    def test_selects_database_backend(self, settings, monkeypatch):
        monkeypatch.setattr(settings, "storage_backend", "database")
        assert isinstance(_build_storage(), DatabaseStorage)

    def test_selection_is_case_and_whitespace_insensitive(self, settings, monkeypatch):
        monkeypatch.setattr(settings, "storage_backend", "  Database ")
        assert isinstance(_build_storage(), DatabaseStorage)

    def test_unknown_backend_raises_instead_of_falling_back_to_local(self, settings, monkeypatch):
        # The important case: a typo must not silently produce local-disk
        # storage on a host that wipes disk on restart.
        monkeypatch.setattr(settings, "storage_backend", "databse")
        with pytest.raises(RuntimeError, match="unknown STORAGE_BACKEND"):
            _build_storage()

    def test_s3_backend_without_bucket_raises(self, settings, monkeypatch):
        monkeypatch.setattr(settings, "storage_backend", "s3")
        monkeypatch.setattr(settings, "s3_bucket_name", "")
        with pytest.raises(RuntimeError, match="S3_BUCKET_NAME"):
            _build_storage()

    def test_s3_backend_builds_with_a_bucket(self, settings, monkeypatch):
        monkeypatch.setattr(settings, "storage_backend", "s3")
        monkeypatch.setattr(settings, "s3_bucket_name", "casearena-test")
        monkeypatch.setattr(settings, "s3_region", "us-east-1")
        monkeypatch.setattr(settings, "s3_access_key_id", "test-key")
        monkeypatch.setattr(settings, "s3_secret_access_key", "test-secret")
        # boto3 builds a client lazily without contacting AWS, so this
        # stays a pure unit test — no network, no credentials needed.
        assert isinstance(_build_storage(), S3CompatibleStorage)
