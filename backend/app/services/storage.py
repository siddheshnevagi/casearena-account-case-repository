"""File storage abstraction for uploaded case PDFs.

Local dev writes to disk; production writes to S3 (or any S3-compatible
object store — Cloudflare R2, etc.), selected by ``STORAGE_BACKEND``.
Everywhere else in the app deals only in an opaque ``storage_key`` string,
so this is the only file that knows where bytes actually live. Adding a
future backend means adding one class here and one branch in
``get_storage()``; no router or model changes.
"""
from __future__ import annotations

import abc
import uuid
from pathlib import Path

from app.config import get_settings

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


_storage_instance: Storage | None = None


def get_storage() -> Storage:
    global _storage_instance
    if _storage_instance is None:
        if settings.storage_backend == "s3":
            if not settings.s3_bucket_name:
                raise RuntimeError(
                    "STORAGE_BACKEND=s3 requires S3_BUCKET_NAME to be set"
                )
            _storage_instance = S3CompatibleStorage(
                bucket=settings.s3_bucket_name,
                region=settings.s3_region,
                access_key_id=settings.s3_access_key_id,
                secret_access_key=settings.s3_secret_access_key,
                endpoint_url=settings.s3_endpoint_url,
            )
        else:
            _storage_instance = LocalDiskStorage(settings.upload_storage_dir)
    return _storage_instance
