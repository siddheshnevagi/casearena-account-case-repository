"""Signup, verification, login, refresh, and current-user lookup.

Implements US-03 (account creation) and the auth-related FRs (FR-01, FR-02)
plus NFR-01 (hashed passwords, session handling). Account lockout after
repeated failed logins is here too, per the US-03 acceptance criteria.
"""
from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.deps import get_current_user
from app.core.security import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_verification_token,
    hash_password,
    verify_password,
)
from app.database import get_db
from app.models.profile import Profile
from app.models.user import User
from app.schemas.token import AccessTokenResponse, RefreshRequest, TokenResponse
from app.schemas.user import LoginRequest, SignupRequest, SignupResponse, UserOut, VerifyRequest

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


@router.post("/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, db: Session = Depends(get_db)) -> SignupResponse:
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "an account with this email already exists")

    token = generate_verification_token()
    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        verification_token=token,
    )
    db.add(user)
    db.flush()  # populate user.id before creating the dependent profile row

    # An empty profile row so onboarding (US-03 AC) has something to update.
    db.add(Profile(user_id=user.id))
    db.commit()
    db.refresh(user)

    return SignupResponse(id=user.id, email=user.email, is_verified=user.is_verified, verification_token=token)


@router.post("/verify")
def verify(payload: VerifyRequest, db: Session = Depends(get_db)) -> dict:
    user = db.query(User).filter(User.verification_token == payload.token).first()
    if user is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid verification token")

    user.is_verified = True
    user.verification_token = None
    db.commit()
    return {"message": "account verified"}


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.email == payload.email, User.is_deleted.is_(False)).first()

    if user is not None and user.locked_until is not None:
        now = dt.datetime.now(dt.timezone.utc)
        locked_until = user.locked_until
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=dt.timezone.utc)
        if locked_until > now:
            retry_after = int((locked_until - now).total_seconds())
            raise HTTPException(
                status.HTTP_423_LOCKED,
                {"detail": "account temporarily locked due to repeated failed logins", "retry_after_seconds": retry_after},
            )
        # Lock window has passed — reset before evaluating this attempt.
        user.failed_login_attempts = 0
        user.locked_until = None

    if user is None or not verify_password(payload.password, user.hashed_password):
        if user is not None:
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= settings.max_failed_login_attempts:
                user.locked_until = dt.datetime.now(dt.timezone.utc) + dt.timedelta(
                    minutes=settings.lockout_duration_minutes
                )
            db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "incorrect email or password")

    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()

    access_token = create_access_token(user.id, user.email, user.is_admin)
    refresh_token = create_refresh_token(user.id, user.email, user.is_admin)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> AccessTokenResponse:
    try:
        token_payload = decode_token(payload.refresh_token, expected_type="refresh")
    except TokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc

    user = db.get(User, int(token_payload["sub"]))
    if user is None or user.is_deleted:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "user no longer exists")

    access_token = create_access_token(user.id, user.email, user.is_admin)
    return AccessTokenResponse(access_token=access_token, expires_in=settings.access_token_expire_minutes * 60)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
