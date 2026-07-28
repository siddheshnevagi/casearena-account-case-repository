"""User account model.

Owns authentication state only (credentials, verification, lockout). The
prep profile lives in :mod:`app.models.profile` as a separate one-to-one
table — kept apart so auth concerns and onboarding/personalization concerns
don't grow into one god-table (see ARCHITECTURE.md ADR-01 for why this
module owns both instead of splitting across services).
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # FR: signup triggers "a verification step" (ADR-04) — tracked, not
    # enforced as a login gate in the MVP.
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verification_token: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Account lockout after N consecutive failed logins (FR, US-03 AC).
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ADR-03: set when the account is deleted but shared cases are retained.
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: dt.datetime.now(dt.timezone.utc), nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: dt.datetime.now(dt.timezone.utc),
        onupdate=lambda: dt.datetime.now(dt.timezone.utc),
        nullable=False,
    )

    # Target class passed explicitly by name (not just via the Mapped[]
    # annotation) so SQLAlchemy resolves it through the shared declarative
    # registry at mapper-configuration time — Profile/Case are never
    # actually imported into this module, to avoid a user<->profile<->case
    # import cycle. See app/models/__init__.py, which must import all three
    # before any query runs so the registry has every name registered.
    profile: Mapped["Profile"] = relationship(
        "Profile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    cases: Mapped[list["Case"]] = relationship("Case", back_populates="owner")
