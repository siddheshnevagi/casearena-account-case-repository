# Integrating Module 2 into the product-level repository

Target repo: `susanthl1998/AI-Case-Preparation-Platform` (the platform
skeleton provided by the tech architect).

## What that repo contains today

A folder/naming skeleton and nothing else: **38 files, all 0 bytes, except
`.gitignore`.** No implementation, no schema, no API spec, no ADRs. Every
structural decision it appears to make is a filename, not a design.

This matters for how we merge: there is no competing implementation to
reconcile against, and nothing of ours has been invalidated. The work is a
**mechanical relayout** of working, tested code — not a rewrite, and not a
negotiation over behavior.

## File mapping

Their skeleton slot → our implementation. Team 2 owns the rows marked ✅;
the rest belong to Team 1 (AI) and are listed only so the boundary is
explicit.

| Platform repo path | Ours | Owner |
|---|---|---|
| `backend/app/api/v1/auth.py` | `app/routers/auth.py` | ✅ Team 2 |
| `backend/app/api/v1/users.py` | `app/routers/profile.py` + `app/routers/account.py` | ✅ Team 2 |
| `backend/app/api/v1/cases.py` | `app/routers/cases.py` | ✅ Team 2 |
| `backend/app/api/v1/health.py` | `/health` + `/`, inline in `app/main.py` | ✅ Team 2 |
| `backend/app/core/config.py` | `app/config.py` | ✅ Team 2 |
| `backend/app/core/security.py` | `app/core/security.py` (already matches) | ✅ Team 2 |
| `backend/app/core/constants.py` | — (enums live with their models, see note) | ✅ Team 2 |
| `backend/app/database/postgres.py` | `app/database.py` | ✅ Team 2 |
| `backend/app/services/auth_service.py` | `app/core/security.py` + `app/core/deps.py` | ✅ Team 2 |
| `backend/app/services/case_service.py` | `app/services/cases.py` | ✅ Team 2 |
| `backend/app/main.py` | `app/main.py` | shared |
| `backend/app/database/mongodb.py` | n/a | Team 1 |
| `backend/app/database/vector_db.py` | n/a | Team 1 |
| `backend/app/api/v1/chat.py`, `interview.py` | n/a | Team 1 |
| `backend/app/services/ai_service.py`, `rag_service.py`, `evaluation_service.py` | n/a | Team 1 |

### Ours with no slot in their skeleton

These are not optional extras — the app does not run without the first
four. The skeleton simply has no folder for them yet, which is the main
thing to settle with the architect before merging:

| Ours | What it is |
|---|---|
| `app/models/` | SQLAlchemy ORM models — `User`, `Profile`, `Case`, `CaseFile` |
| `app/schemas/` | Pydantic request/response models |
| `alembic/` + `alembic.ini` | Migrations (`0001` schema, `0002` case_files) |
| `tests/` | Pytest suite covering the PRD acceptance criteria |
| `app/services/storage.py` | PDF storage abstraction (local / database / S3) |
| `scripts/promote_admin.py` | Admin promotion CLI (deliberately not an API) |
| `docs/ARCHITECTURE.md`, `API_CONTRACT.md`, `PRD_GAP_LOG.md` | Decision records + integration contract |

Their `docs/` uses a different shape (`API/`, `Architecture/`, `Database/`,
`Sprints/`, `UML/`), all empty. Ours map cleanly:
`ARCHITECTURE.md` → `docs/Architecture/`, `API_CONTRACT.md` → `docs/API/`,
and the models are the real content for `docs/Database/database-design.md`.

## The one behavioral change: URL versioning

Their layout implies an **`/api/v1` prefix**; our endpoints are currently
unprefixed (`/auth/login`, not `/api/v1/auth/login`).

This is the only difference in the whole mapping that changes observable
behavior, and it touches three things: our router registration, the
frontend's `VITE_API_BASE_URL`, and anything Team 1/Team 3 have already
written against `docs/API_CONTRACT.md`.

It is a small change (`prefix="/api/v1"` when including routers, plus the
contract doc), but it must be made **once, deliberately, with the other
teams told** — not discovered by Team 1 when their calls start 404ing.
Confirm the prefix with the architect before doing it.

## Open questions for the architect

Ask before merging, not during:

1. **Is `/api/v1` the required URL prefix?** We will adopt it; we need it
   confirmed so the contract doc and Team 1/Team 3 move together.
2. **Where do models, schemas, and migrations live?** The skeleton has no
   folder for them. We propose `backend/app/models/`,
   `backend/app/schemas/`, `backend/alembic/` — but the answer must be
   consistent across all three teams or the shared database gets three
   incompatible migration histories.
3. **Who owns migrations against the shared Neon database?** If all three
   teams run Alembic against one database, we need a single migration
   history and a rule about who applies it. This is the highest-risk
   coordination item on the list.
4. **Postgres or MongoDB for case metadata?** The skeleton has both
   `postgres.py` and `mongodb.py`. Module 2 deliberately put case metadata
   in Postgres — see ARCHITECTURE.md **ADR-02** (it is relational, heavily
   filtered, and joins to users; splitting it would create two sources of
   truth). We need the architect to confirm or overrule this explicitly,
   since Team 1 reads case data.
5. **Where does Team 3 (multiplayer / group prep) go?** The skeleton has no
   slot for EPIC-03 at all.
6. **Contribution flow?** Fork + PR, or direct branches on the platform
   repo? Any branch naming or review requirements?
7. **PDF storage.** We currently store PDFs in Postgres for a zero-budget
   demo (ADR-07). If the platform has a real object-storage budget, we flip
   `STORAGE_BACKEND=s3` — the code path already exists.

## Recommended sequence

**Do not restructure before the demo.** The working, tested code is in this
repo, deployed and verified. A layout refactor the night before a demo
risks the demo for zero demo-visible gain — the audience sees the app, not
the folder names.

1. **Now:** demo from this repo. Send the architect the questions above so
   answers arrive while we are not blocked on them.
2. **After the demo:** branch, relayout to the mapping above, adopt
   `/api/v1`, run the test suite, open a PR to the platform repo.
3. **Then:** update `docs/API_CONTRACT.md` with the final URLs and tell
   Team 1 and Team 3 in the same message.

Step 2 is mechanical and safe *because* of the test suite — the tests are
what make it possible to prove the relayout changed nothing behavioral.
Run `pytest` before and after; the results must be identical.
