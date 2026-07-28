# CaseArena — Module 2: Account Management & Case Repository

CaseArena is an AI-powered case-interview preparation platform for MBA
students, built as a 30-day MVP by three parallel teams:

| Module | Team | Status |
|---|---|---|
| AI Trainer (EPIC-01) | Team 1 | Owned by Team 1 — not in this repo |
| **Account Management & Case Repository (EPIC-02)** | **Team 2 — this repo** | In progress |
| Multiplayer Group Preparation (EPIC-03) | Team 3 | Owned by Team 3 — not in this repo |

This repository contains **only Module 2**. It is the foundation the other
two modules build on: both Team 1 and Team 3 assume a logged-in user with a
prep profile, and Team 1's AI Trainer draws practice cases from the
repository this module builds. See
[`docs/API_CONTRACT.md`](docs/API_CONTRACT.md) for exactly what this module
exposes to them.

## What this module does

- **Account management** — signup/login with hashed passwords, JWT
  sessions with timeout, account lockout after repeated failed logins,
  onboarding that captures a target firm type (Consulting / Product
  Management) and optional case preferences, and a personalized dashboard.
- **Case repository** — browse, keyword search, and filter a shared case
  library by type/difficulty/industry; upload your own PDF cases (private
  by default); share to, or withdraw from, the community; admin moderation
  for inappropriate content.

Full requirements: [`docs/source-materials/`](docs/source-materials/) has
the original PRD, requirements-gathering document, agile plan, and
architecture spec this was built from. Where those documents had gaps or
conflicts, [`docs/PRD_GAP_LOG.md`](docs/PRD_GAP_LOG.md) lists what was found
and [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) has the full reasoning
behind each resolution — read that before assuming a design choice here was
arbitrary.

## Repository layout

```
backend/    FastAPI + PostgreSQL API — see backend/README.md to run it
frontend/   React + Vite + Tailwind SPA — see frontend/README.md to run it
docs/
  ARCHITECTURE.md        Decision records for every PRD gap/conflict found
  API_CONTRACT.md         Integration contract for Team 1 / Team 3
  PRD_GAP_LOG.md          Quick index into ARCHITECTURE.md
  source-materials/       Original PRD, RGD, agile plan, architecture doc
.github/workflows/ci.yml  Backend tests (against Postgres) + frontend build
```

## Quickstart

Prerequisites: Python 3.12+, Node 20+, Docker (for local Postgres) — or
substitute your own Postgres instance.

```bash
# Backend
cd backend
cp .env.example .env
docker compose up -d db          # local Postgres
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload     # http://localhost:8000, docs at /docs

# Frontend (separate terminal)
cd frontend
cp .env.example .env
npm install
npm run dev                       # http://localhost:5173
```

See [`backend/README.md`](backend/README.md) and
[`frontend/README.md`](frontend/README.md) for configuration details,
running tests, and Docker deployment.

## Scope (MoSCoW, from the PRD)

**Must have (v1.0 — implemented):** signup/login with secure sessions;
onboarding capturing target firm type; personal dashboard; browse/search/
filter by case type and difficulty; mandatory case tagging; PDF upload up
to 10 MB; private-by-default sharing with share-to-community.

**Should have (implemented):** filter by industry, sort by newest/most
practised, edit profile after onboarding, withdraw a shared case.

**Could have (not in v1.0):** bookmarking, non-PDF upload formats, profile
completeness nudges.

**Won't have (v1.0, per PRD):** OAuth login, case ratings/comments, case
version history, email notifications, SMS password reset.

## Status and next steps

- Backend: implemented and unit-tested (SQLite in tests, Postgres via
  Docker Compose / Alembic for real runs — see `backend/README.md`).
- Frontend: implemented against the API contract above.
- Not yet done: wiring this repository into the shared product-level
  GitHub repo (each team currently has an independent local repo); real
  transactional email for signup verification (see ARCHITECTURE.md
  ADR-04); seeding the 25 launch cases called for in PRD §9 (a content
  task, not a code task).
