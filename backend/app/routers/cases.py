"""Case repository: browse/search/filter (US-04), upload and sharing
(US-04B), and admin moderation (FR-11).
"""
from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import String, cast, or_
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.deps import get_current_admin, get_current_user
from app.database import get_db
from app.models.case import Case, CaseType, Difficulty
from app.models.user import User
from app.schemas.case import CaseListResponse, CaseOut, CaseUpdateRequest, ModerateRequest
from app.services.cases import case_to_out
from app.services.storage import get_storage

router = APIRouter(prefix="/cases", tags=["cases"])
settings = get_settings()


def _visible_or_404(db: Session, case_id: int, current_user: User) -> Case:
    case = db.get(Case, case_id)
    if case is None or case.is_removed:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "case not found")
    is_owner = case.owner_id == current_user.id
    if not case.is_shared and not is_owner and not current_user.is_admin:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "case not found")
    return case


@router.get("", response_model=CaseListResponse)
def list_cases(
    case_type: CaseType | None = None,
    difficulty: Difficulty | None = None,
    industry: str | None = None,
    q: str | None = Query(default=None, description="keyword search, minimum 3 characters"),
    sort: str = Query(default="newest", pattern="^(newest|most_practiced)$"),
    scope: str = Query(default="community", pattern="^(community|mine)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CaseListResponse:
    query = db.query(Case).filter(Case.is_removed.is_(False))

    if scope == "mine":
        query = query.filter(Case.owner_id == current_user.id)
    else:
        query = query.filter(Case.is_shared.is_(True))

    if case_type is not None:
        query = query.filter(Case.case_type == case_type)
    if difficulty is not None:
        query = query.filter(Case.difficulty == difficulty)
    if industry:
        query = query.filter(Case.industry.ilike(f"%{industry}%"))

    if q is not None:
        keyword = q.strip()
        if len(keyword) >= 3:
            # JSON containment syntax differs between SQLite and Postgres,
            # so tags are matched via a dialect-agnostic substring check on
            # the serialized column — sufficient at the 500-case scale
            # NFR-02 targets, and simpler than branching on dialect.
            query = query.filter(or_(Case.title.ilike(f"%{keyword}%"), _tags_contain(keyword)))

    if sort == "most_practiced":
        query = query.order_by(Case.practice_count.desc(), Case.created_at.desc())
    else:
        query = query.order_by(Case.created_at.desc())

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return CaseListResponse(
        items=[case_to_out(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
        is_empty=total == 0,
    )


def _tags_contain(keyword: str):
    """Best-effort tag match across SQLite (JSON-as-text) and Postgres
    (native JSON) without branching the whole query builder on dialect.
    """
    return cast(Case.tags, String).ilike(f"%{keyword}%")


@router.get("/{case_id}", response_model=CaseOut)
def get_case(case_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Case:
    return _visible_or_404(db, case_id, current_user)


@router.get("/{case_id}/file")
def download_case_file(
    case_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Response:
    case = _visible_or_404(db, case_id, current_user)
    content = get_storage().read(case.storage_key)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{case.original_filename}"'},
    )


@router.post("", response_model=CaseOut, status_code=status.HTTP_201_CREATED)
async def upload_case(
    file: UploadFile = File(...),
    title: str = Form(...),
    case_type: CaseType = Form(...),
    difficulty: Difficulty = Form(...),
    industry: str | None = Form(default=None),
    tags: str | None = Form(default=None, description="comma-separated"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Case:
    if file.content_type != "application/pdf":
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "only PDF files are accepted")

    content = await file.read()
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"file exceeds the {settings.max_upload_size_bytes // (1024 * 1024)} MB limit",
        )

    # Save to storage first; only create the DB row if that succeeds, so a
    # failed upload never leaves an orphan record (NFR-04).
    storage_key = get_storage().save(content, file.filename or "case.pdf")

    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

    case = Case(
        owner_id=current_user.id,
        title=title,
        case_type=case_type,
        difficulty=difficulty,
        industry=industry,
        tags=tag_list,
        storage_key=storage_key,
        original_filename=file.filename or "case.pdf",
        file_size_bytes=len(content),
    )
    db.add(case)
    try:
        db.commit()
    except Exception:
        db.rollback()
        get_storage().delete(storage_key)
        raise
    db.refresh(case)
    return case


@router.patch("/{case_id}", response_model=CaseOut)
def update_case(
    case_id: int,
    payload: CaseUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Case:
    case = db.get(Case, case_id)
    if case is None or case.is_removed:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "case not found")
    if case.owner_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "only the owner can edit this case")

    for field in ("title", "case_type", "difficulty", "industry", "tags"):
        value = getattr(payload, field)
        if value is not None:
            setattr(case, field, value)

    db.commit()
    db.refresh(case)
    return case


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_case(case_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> None:
    case = db.get(Case, case_id)
    if case is None or case.is_removed:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "case not found")
    if case.owner_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "only the owner can delete this case")

    storage_key = case.storage_key
    db.delete(case)
    db.commit()
    get_storage().delete(storage_key)


@router.post("/{case_id}/share", response_model=CaseOut)
def share_case(case_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Case:
    case = db.get(Case, case_id)
    if case is None or case.is_removed:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "case not found")
    if case.owner_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "only the owner can share this case")

    case.is_shared = True
    case.shared_at = dt.datetime.now(dt.timezone.utc)
    db.commit()
    db.refresh(case)
    return case


@router.post("/{case_id}/withdraw", response_model=CaseOut)
def withdraw_case(case_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Case:
    case = db.get(Case, case_id)
    if case is None or case.is_removed:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "case not found")
    if case.owner_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "only the owner can withdraw this case")

    case.is_shared = False
    db.commit()
    db.refresh(case)
    return case


@router.post("/{case_id}/practice", response_model=CaseOut)
def record_practice(
    case_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Case:
    """Integration point for Team 1 (AI Trainer) — see docs/API_CONTRACT.md.
    Any authenticated user may log a practice event against a case they can
    see (their own, or a shared community case).
    """
    case = _visible_or_404(db, case_id, current_user)
    case.practice_count += 1
    db.commit()
    db.refresh(case)
    return case


@router.patch("/{case_id}/moderate", response_model=CaseOut)
def moderate_case(
    case_id: int,
    payload: ModerateRequest,
    _admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> Case:
    case = db.get(Case, case_id)
    if case is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "case not found")

    case.is_removed = True
    case.removal_reason = payload.removal_reason
    db.commit()
    db.refresh(case)
    return case
