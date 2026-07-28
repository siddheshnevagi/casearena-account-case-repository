"""File storage abstraction for uploaded case PDFs.

``STORAGE_BACKEND`` selects one of three implementations:

- ``local``    — disk. Development only; most hosts wipe disk on redeploy.
- ``database`` — bytes in Postgres. No extra vendor or credentials, which
                 is why the demo deployment uses it (ARCHITECTURE.md ADR-07).
- ``s3``       — AWS S3 or any S3-compatible store (Cloudflare R2, MinIO).
                 The right choice past demo volumes.

Everywhere else in the app deals only in an opaque ``storage_key`` string,
so this is the only file that knows where bytes actually live — swapping
backends needs no router, model, or schema change. Adding another means
one class here plus one branch in ``_build_storage()``.
"""
from __future__ import annotations

import abc
import uuid
from pathlib import Path

from app.config import get_settings

# Imported at module level (not lazily inside DatabaseStorage) so the model
# is always registered on ``Base.metadata`` wherever this module is
# imported. Nothing else in the app imports app.models.case_file, and
# ``Base.metadata.create_all()`` only creates tables for models that have
# actually been imported — without this, table creation silently skips
# case_files. ``SessionLocal`` is still looked up lazily inside the methods
# so tests can redirect it at a throwaway database.
from app.models.case_file import CaseFile

settings = get_settings()


class Storage(abc.ABC):
    @abc.abstractmethod
    def save(self, content: bytes, original_filename: str) -> str:
        """Persist ``content`` and return an opaque storage key."""

    @abc.abstractmethod
    def read(self, storage_key: str) -> bytes:
        """Return the raw bytes for a previously-saved storage key."""

    @abc.abstractmethod
    def delete(self, storage_key: str) -> None:
        """Remove a previously-saved object, if present."""


class LocalDiskStorage(Storage):
    def __init__(self, base_dir: str) -> None:
        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, storage_key: str) -> Path:
        # storage_key is always a uuid4 hex we generated ourselves in
        # save(); never derived from user input, so there is no path
        # traversal surface here.
        return self._base_dir / storage_key

    def save(self, content: bytes, original_filename: str) -> str:
        suffix = Path(original_filename).suffix
        storage_key = f"{uuid.uuid4().hex}{suffix}"
        self._path_for(storage_key).write_bytes(content)
        return storage_key

    def read(self, storage_key: str) -> bytes:
        return self._path_for(storage_key).read_bytes()

    def delete(self, storage_key: str) -> None:
        path = self._path_for(storage_key)
        if path.exists():
            path.unlink()


class S3CompatibleStorage(Storage):
    """Works against real AWS S3 or any S3-compatible provider (Cloudflare
    R2, MinIO, ...) by pointing ``endpoint_url`` at that provider — R2 in
    particular needs this since it speaks the S3 API but isn't AWS.
    """

    def __init__(
        self,
        bucket: str,
        region: str,
        access_key_id: str,
        secret_access_key: str,
        endpoint_url: str | None = None,
    ) -> None:
        import boto3

        self._bucket = bucket
        self._client = boto3.client(
            "s3",
            region_name=region,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            endpoint_url=endpoint_url or None,
        )

    def save(self, content: bytes, original_filename: str) -> str:
        suffix = Path(original_filename).suffix
        storage_key = f"{uuid.uuid4().hex}{suffix}"
        self._client.put_object(
            Bucket=self._bucket,
            Key=storage_key,
            Body=content,
            ContentType="application/pdf",
        )
        return storage_key

    def read(self, storage_key: str) -> bytes:
        response = self._client.get_object(Bucket=self._bucket, Key=storage_key)
        return response["Body"].read()

    def delete(self, storage_key: str) -> None:
        # S3's delete_object is idempotent — deleting a key that doesn't
        # exist returns success rather than raising, matching
        # LocalDiskStorage.delete's "no-op if absent" behavior.
        self._client.delete_object(Bucket=self._bucket, Key=storage_key)


class DatabaseStorage(Storage):
    """Stores PDF bytes in Postgres (``case_files`` table).

    Chosen for the demo deployment because it needs no object-storage
    account, no credentials, and no second vendor — the database
    connection the app already has is the only dependency, so there is
    one less thing that can be misconfigured (see ARCHITECTURE.md ADR-07).

    **Not** the right answer at scale: every byte flows through the app
    process, bytes bloat the database (and its backups), and there is no
    CDN in front. Switch to ``STORAGE_BACKEND=s3`` when uploads grow
    beyond demo volumes — ``cases.storage_key`` is backend-agnostic, so
    that swap needs no schema change (only a migration of existing bytes).

    Uses its own short-lived session rather than the request's: the
    calling router already treats storage as non-transactional and
    compensates by deleting the stored object if the metadata insert
    fails (see ``routers/cases.py``), so a separate transaction here
    matches the behavior the rest of the code was written against.
    """

    def save(self, content: bytes, original_filename: str) -> str:
        from app.database import SessionLocal

        suffix = Path(original_filename).suffix
        storage_key = f"{uuid.uuid4().hex}{suffix}"
        with SessionLocal() as session:
            session.add(CaseFile(storage_key=storage_key, content=content))
            session.commit()
        return storage_key

    def read(self, storage_key: str) -> bytes:
        from app.database import SessionLocal

        with SessionLocal() as session:
            row = session.query(CaseFile).filter(CaseFile.storage_key == storage_key).one_or_none()
            if row is None:
                # Mirrors LocalDiskStorage, which raises FileNotFoundError
                # for a missing key, so callers see one failure mode
                # regardless of which backend is configured.
                raise FileNotFoundError(f"no stored object for key {storage_key!r}")
            return row.content

    def delete(self, storage_key: str) -> None:
        from app.database import SessionLocal

        with SessionLocal() as session:
            session.query(CaseFile).filter(CaseFile.storage_key == storage_key).delete()
            session.commit()


_storage_instance: Storage | None = None


def _build_storage() -> Storage:
    # Normalized, and unknown values raise rather than falling back to
    # local disk: a typo'd STORAGE_BACKEND on a hosted deployment would
    # otherwise "work" until the next restart wiped every upload, with
    # nothing in the logs. Failing at startup is far cheaper.
    backend = settings.storage_backend.strip().lower()

    if backend == "local":
        return LocalDiskStorage(settings.upload_storage_dir)

    if backend == "database":
        return DatabaseStorage()

    if backend == "s3":
        if not settings.s3_bucket_name:
            raise RuntimeError("STORAGE_BACKEND=s3 requires S3_BUCKET_NAME to be set")
        return S3CompatibleStorage(
            bucket=settings.s3_bucket_name,
            region=settings.s3_region,
            access_key_id=settings.s3_access_key_id,
            secret_access_key=settings.s3_secret_access_key,
            endpoint_url=settings.s3_endpoint_url,
        )

    raise RuntimeError(
        f"unknown STORAGE_BACKEND {settings.storage_backend!r} — "
        "expected one of: local, database, s3"
    )


def get_storage() -> Storage:
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = _build_storage()
    return _storage_instance
