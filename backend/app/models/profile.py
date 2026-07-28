"""Prep profile — one row per user, created during onboarding (US-03, FR-03).

Kept separate from ``User`` so "does this user exist and can they log in"
(auth) is independent of "has this user finished onboarding" (product
state) — a user can exist without a completed profile between signup and
onboarding.
"""
from __future__ import annotations

import datetime as dt
import enum

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer
from sqlalchemy import Enum as SAEnum
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TargetFirmType(str, enum.Enum):
    CONSULTING = "CONSULTING"
    PRODUCT_MANAGEMENT = "PRODUCT_MANAGEMENT"


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    # Mandatory single-select (FR-03). `name=` pinned explicitly — see the
    # matching comment in app/models/case.py for why.
    target_firm_type: Mapped[TargetFirmType | None] = mapped_column(
        SAEnum(TargetFirmType, name="targetfirmtype"), nullable=True
    )

    # Optional (PRD §6, US-03 AC) — free-form list of case-type preferences.
    case_preferences: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: dt.datetime.now(dt.timezone.utc), nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: dt.datetime.now(dt.timezone.utc),
        onupdate=lambda: dt.datetime.now(dt.timezone.utc),
        nullable=False,
    )

    # See app/models/user.py for why the target class is passed as an
    # explicit string rather than relying on the Mapped[] annotation alone.
    user: Mapped["User"] = relationship("User", back_populates="profile")
