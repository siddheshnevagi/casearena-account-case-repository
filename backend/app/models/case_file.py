"""Uploaded PDF bytes, stored in Postgres.

Only used when ``STORAGE_BACKEND=database`` (see
``app/services/storage.py``). Deliberately a *separate* table from
``cases`` rather than a column on it: case metadata is read constantly
(every browse/search/filter query) while the bytes are read only when
someone opens a specific PDF, and keeping a multi-megabyte column out of
the metadata table stops every ``SELECT * FROM cases`` from dragging it
along.

The link is by ``storage_key``, not a foreign key, so this table stays an
implementation detail of the storage layer — ``cases.storage_key`` means
the same opaque thing whether the bytes live here, on local disk, or in
S3, and switching backends needs no schema change.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CaseFile(Base):
    __tablename__ = "case_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Matches cases.storage_key. Unique because storage keys are uuid4s
    # generated per upload — a collision would mean silently serving the
    # wrong PDF, so let the database enforce it rather than trusting uuid4.
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False, unique=True, index=True)

    # bytea on Postgres, BLOB on SQLite.
    content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: dt.datetime.now(dt.timezone.utc), nullable=False
    )
