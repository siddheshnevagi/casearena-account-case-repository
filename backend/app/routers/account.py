"""Account deletion, implementing the ADR-03 resolution: shared cases are
retained and anonymized, private-only cases are hard-deleted with the
account.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.case import Case
from app.models.user import User
from app.schemas.user import AccountDeletionResult
from app.services.storage import get_storage

router = APIRouter(prefix="/account", tags=["account"])


@router.delete("/me", response_model=AccountDeletionResult)
def delete_account(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> AccountDeletionResult:
    owned_cases = db.query(Case).filter(Case.owner_id == current_user.id).all()

    anonymized = 0
    deleted = 0
    storage = get_storage()
    for case in owned_cases:
        if case.is_shared:
            case.owner_deleted = True
            case.owner_id = None
            anonymized += 1
        else:
            storage.delete(case.storage_key)
            db.delete(case)
            deleted += 1

    # Scrub credentials so a "deleted" account can never authenticate again,
    # while keeping the row itself for referential integrity / audit trail
    # (NFR-01: protect user data even in the deletion path).
    current_user.is_deleted = True
    current_user.email = f"deleted-user-{current_user.id}@caseArena.invalid"
    current_user.hashed_password = ""
    current_user.verification_token = None
    db.commit()

    return AccountDeletionResult(
        message="account deleted",
        cases_anonymized=anonymized,
        cases_deleted=deleted,
    )
