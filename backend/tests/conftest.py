"""Shared pytest fixtures.

Tests run against an isolated in-memory SQLite database per test function
(via StaticPool, so the single in-memory connection is shared across the
app's own session-per-request pattern) — fast, and requires no external
Postgres just to run the suite. Postgres-specific behavior (native enums,
etc.) is exercised in CI against a real Postgres service instead of here;
see .github/workflows/ci.yml.

Settings are loaded once via ``lru_cache`` and several modules bind
``settings = get_settings()`` at import time, so tests that need to tweak a
setting (e.g. the upload size limit) must mutate attributes on the shared
cached instance in place, rather than trying to replace it — replacing
would only affect modules that call ``get_settings()`` again afterwards.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.database import Base, get_db
from app.main import app
import app.services.storage as storage_module
from app.services.storage import LocalDiskStorage


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session, tmp_path):
    storage_module._storage_instance = LocalDiskStorage(str(tmp_path / "uploads"))

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    storage_module._storage_instance = None


@pytest.fixture()
def settings():
    """The single cached Settings instance — mutate attributes on it
    directly (see module docstring) rather than reassigning."""
    return get_settings()


def make_pdf_bytes(size_bytes: int = 1024) -> bytes:
    header = b"%PDF-1.4\n"
    padding = b"0" * max(0, size_bytes - len(header))
    return header + padding


@pytest.fixture()
def signup_and_login(client):
    """Return a helper that signs up + logs in a fresh user, returning
    (auth_headers, user_id)."""

    def _do(email: str = "student@iiml.ac.in", password: str = "supersecret1"):
        signup_resp = client.post("/auth/signup", json={"email": email, "password": password})
        assert signup_resp.status_code == 201, signup_resp.text
        user_id = signup_resp.json()["id"]

        login_resp = client.post("/auth/login", json={"email": email, "password": password})
        assert login_resp.status_code == 200, login_resp.text
        token = login_resp.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}, user_id

    return _do
