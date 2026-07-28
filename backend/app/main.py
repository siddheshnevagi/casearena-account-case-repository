"""FastAPI application entrypoint.

Run locally with: ``uvicorn app.main:app --reload`` (see backend/README.md).
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import account, auth, cases, profile

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description=(
        "Account Management & Case Repository — Module 2 of CaseArena. "
        "See /docs for the interactive API reference, and docs/API_CONTRACT.md "
        "in the repository for the integration contract used by Team 1 and Team 3."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(cases.router)
app.include_router(account.router)


@app.get("/health", tags=["health"])
def health() -> dict:
    return {"status": "ok"}
