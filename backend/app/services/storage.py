"""File storage abstraction for uploaded case PDFs.

Local dev writes to disk. The architecture document specifies Google Cloud
Storage for production ("Store PDFs, documents, uploads"); this module's
code never depends on the filesystem beyond this file — everywhere else in
the app deals in an opaque ``storage_key`` string. Swapping in a GCS-backed
implementation later means adding one class here and changing which one
``get_storage()`` returns; no router or model changes.
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


_storage_instance: Storage | None = None


def get_storage() -> Storage:
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = LocalDiskStorage(settings.upload_storage_dir)
    return _storage_instance
