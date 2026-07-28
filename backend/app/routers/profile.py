"""Onboarding, profile management, and the personalized dashboard.

Implements US-03's onboarding requirement (FR-03), profile editing
(FR-05, Should-have), and the dashboard ordering rule (FR-04): cases
matching the user's target firm type are surfaced first. The ordering is
intentionally simple rule-based sorting, not a recommendation model — the
PRD's non-goals explicitly exclude AI-based recommendations for v1.0.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.case import Case
from app.models.profile import Profile
from app.models.user import User
from app.schemas.profile import DashboardOut, OnboardingRequest, ProfileOut, ProfileUpdateRequest
from app.services.cases import case_to_out, case_types_for_preferences

router = APIRouter(tags=["profile"])


def _get_or_create_profile(db: Session, user: User) -> Profile:
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if profile is None:
        profile = Profile(user_id=user.id)
        db.add(profile)
        db.flush()
    return profile


@router.post("/profile/onboarding", response_model=ProfileOut)
def complete_onboarding(
    payload: OnboardingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Profile:
    profile = _get_or_create_profile(db, current_user)
    profile.target_firm_type = payload.target_firm_type
    profile.case_preferences = payload.case_preferences
    profile.onboarding_completed = True
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/profile/me", response_model=ProfileOut)
def get_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Profile:
    return _get_or_create_profile(db, current_user)


@router.patch("/profile/me", response_model=ProfileOut)
def update_profile(
    payload: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Profile:
    profile = _get_or_create_profile(db, current_user)
    if payload.target_firm_type is not None:
        profile.target_firm_type = payload.target_firm_type
    if payload.case_preferences is not None:
        profile.case_preferences = payload.case_preferences
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> DashboardOut:
    """FR-04: dashboard ordered by the user's stated preference. See
    ARCHITECTURE.md ADR-06 — ordering is driven by ``case_preferences``
    (which map onto the consulting-only case taxonomy), not by
    ``target_firm_type`` directly, since Product Management has no
    matching case types in v1.0.
    """
    profile = _get_or_create_profile(db, current_user)

    base_query = db.query(Case).filter(Case.is_shared.is_(True), Case.is_removed.is_(False))
    preferred_types = case_types_for_preferences(profile.case_preferences)

    if preferred_types:
        matching = (
            base_query.filter(Case.case_type.in_(preferred_types)).order_by(Case.created_at.desc()).limit(10).all()
        )
        remaining_slots = 10 - len(matching)
        others = []
        if remaining_slots > 0:
            others = (
                base_query.filter(Case.case_type.notin_(preferred_types))
                .order_by(Case.created_at.desc())
                .limit(remaining_slots)
                .all()
            )
        cases = matching + others
    else:
        # No matched preference — newest-first. For a Product Management
        # user this is the documented v1.0 limitation (ADR-06), not an
        # error: there is no PM-specific case type to prioritize yet.
        cases = base_query.order_by(Case.created_at.desc()).limit(10).all()

    return DashboardOut(
        profile=ProfileOut.model_validate(profile),
        recommended_cases=[case_to_out(c) for c in cases],
    )
