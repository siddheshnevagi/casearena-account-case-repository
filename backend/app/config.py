"""Centralized application settings, loaded from environment variables.

See ``.env.example`` for the full list of variables a deployment must
provide. Nothing here hardcodes a secret — local dev falls back to
clearly-fake defaults so the app boots without a `.env` file, but every
fallback is something you would never accept in staging/production.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_name: str = "CaseArena — Account Management & Case Repository"
    environment: str = "development"
    debug: bool = True

    # Database — Postgres in staging/production (Cloud SQL, per ADR-01),
    # SQLite acceptable for a zero-dependency local smoke test.
    database_url: str = "sqlite:///./dev.db"

    # Auth
    jwt_secret_key: str = "dev-only-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Account lockout (FR: "5 consecutive failures -> temporary lock")
    max_failed_login_attempts: int = 5
    lockout_duration_minutes: int = 15

    # File uploads (FR-09: PDF up to 10 MB)
    max_upload_size_bytes: int = 10 * 1024 * 1024
    upload_storage_dir: str = "./storage/uploads"

    # Where uploaded PDFs live. One of:
    #   "local"    — disk, dev only; wiped on redeploy on most hosts
    #   "database" — bytes in Postgres; no extra vendor/credentials needed
    #   "s3"       — AWS S3, or S3-compatible (Cloudflare R2) via
    #                s3_endpoint_url; the right choice past demo volumes
    # Anything other than "local" survives a restart. See ADR-07.
    storage_backend: str = "local"
    s3_bucket_name: str = ""
    s3_region: str = "auto"
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    s3_endpoint_url: str = ""  # leave blank for real AWS S3; set for R2/MinIO/etc.

    # CORS — the frontend origin(s) allowed to call this API
    cors_allow_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
