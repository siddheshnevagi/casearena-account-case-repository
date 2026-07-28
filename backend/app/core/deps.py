"""FastAPI dependencies for authentication and authorization.

``get_current_user`` is the dependency Team 3 was told (PRD §9) to expect
as "the auth interface" — see docs/API_CONTRACT.md for how to validate the
same JWTs from another service without importing this module directly.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import TokenError, decode_token
from app.database import get_db
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing bearer token")

    try:
        payload = decode_token(credentials.credentials, expected_type="access")
    except TokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc

    user = db.get(User, int(payload["sub"]))
    if user is None or user.is_deleted:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "user no longer exists")
    return user


def get_current_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "admin privileges required")
    return user
