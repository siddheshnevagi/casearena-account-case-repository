"""Password hashing and JWT issuing/verification.

Uses ``bcrypt`` directly rather than passlib: passlib's bcrypt backend has
been broken by bcrypt's own 4.1+ releases removing the ``__about__`` shim
passlib probes for, and pinning bcrypt below that just to keep passlib
happy is a needless constraint. One direct dependency, no wrapper.
"""
from __future__ import annotations

import datetime as dt
import secrets

import bcrypt
import jwt

from app.config import get_settings

settings = get_settings()


def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def generate_verification_token() -> str:
    return secrets.token_urlsafe(32)


def _create_token(user_id: int, email: str, is_admin: bool, token_type: str, expires_delta: dt.timedelta) -> str:
    now = dt.datetime.now(dt.timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "is_admin": is_admin,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: int, email: str, is_admin: bool) -> str:
    return _create_token(
        user_id, email, is_admin, "access", dt.timedelta(minutes=settings.access_token_expire_minutes)
    )


def create_refresh_token(user_id: int, email: str, is_admin: bool) -> str:
    return _create_token(
        user_id, email, is_admin, "refresh", dt.timedelta(days=settings.refresh_token_expire_days)
    )


class TokenError(Exception):
    pass


def decode_token(token: str, expected_type: str) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError("invalid token") from exc

    if payload.get("type") != expected_type:
        raise TokenError(f"expected a {expected_type} token")
    return payload
