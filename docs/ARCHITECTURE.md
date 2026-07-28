# Module 2 — Architecture Decisions

Module: **Account Management & Case Repository** (EPIC-02, Team 2)
Status: Living document — update whenever a decision below is revisited.

This document exists because the module's own PRD and the product-wide
Technical Requirements & Architecture Document disagree on a few points, and
because a couple of things the PRD calls "open questions" needed an answer
before code could be written. Each entry below is a decision record: the
conflict or gap, the decision, and the reasoning, so anyone picking this up
later (including Team 1 and Team 3) understands *why*, not just *what*.

## ADR-01: Backend framework and datastore — Supabase vs. FastAPI + Cloud SQL

**Conflict.** The Module 2 PRD
(`docs/source-materials/CaseArena_PRD_AccountMgmt_CaseRepository.docx`,
§9 Assumptions) states: *"Backend assumed to be Supabase (Postgres) with
insert-only row-level security, consistent with the team's prior sprint
work."* The product-wide
`docs/source-materials/Technical Requirements & Architecture Document.pdf`
— which applies to all three teams — specifies **Python + FastAPI** as the
primary backend framework, **Google Cloud SQL (PostgreSQL)** for accounts,
auth and sessions, deployed on **Google Cloud Run**, with GitHub Actions +
Docker for CI/CD. It does not mention Supabase anywhere.

**Decision.** Build this module on **FastAPI + SQLAlchemy + PostgreSQL**,
matching the product-wide architecture, not Supabase.

**Why.** The architecture document is the cross-team contract: Team 1 (AI
Trainer) and Team 3 (Multiplayer) are told to integrate against "the auth
interface" and "the case schema" from this module, and they were scoped
assuming the product-wide stack. Standardizing on one backend framework and
one hosting model across all three teams avoids duplicated auth
implementations and three different deployment pipelines. Supabase's
row-level security is a nice property, but it is a single-team assumption
written before the cross-team architecture doc existed; nothing in the PRD's
actual requirements (FR-01–FR-11, NFR-01–NFR-05) depends on Supabase
specifically — they depend on hashed passwords, session handling, and
per-user data isolation, all of which FastAPI + Postgres deliver directly.
Ownership checks (a user can only read/write their own profile and private
cases) are enforced in the FastAPI dependency/service layer rather than via
Postgres RLS policies — functionally equivalent for this MVP's needs, and it
keeps authorization logic in one place (Python) instead of split across the
app and the database.

**Consequence.** `backend/` is a FastAPI project with Alembic migrations
against Postgres (see `backend/README.md`). Local dev can point
`DATABASE_URL` at a Dockerized Postgres (via `docker-compose.yml`) or at
SQLite for a zero-dependency smoke test; Postgres is the target for
staging/production, matching Cloud SQL.

## ADR-02: Case repository metadata — Postgres vs. MongoDB

**Conflict.** The architecture document lists "Case repository metadata" as
a MongoDB Atlas responsibility, alongside chat history and AI evaluation
results. But the PRD's acceptance criteria for the repository (US-04)
require compound filtering (case type + difficulty + industry), keyword
search across title and tags, sorting, and a hard 2-second response target
over up to 500 cases (NFR-02) — all things a relational store with indexes
does well and a document store makes harder to guarantee.

**Decision.** Case records (title, type, difficulty, industry, tags, owner,
sharing state, file reference) live in **Postgres**, alongside users and
profiles, as the system of record for this module's CRUD and search.

**Why.** MongoDB in the architecture doc is grouped with genuinely
document-shaped, high-write, schema-flexible data (chat transcripts, AI
evaluation blobs) — not with the tightly-tagged, relationally-filtered case
records this module owns. Keeping cases in Postgres also means Team 1's
"case schema must be frozen by end of Week 2" dependency (PRD §9) is a
single, unambiguous SQL schema to freeze, not a schema split across two
databases. If Team 1's AI Trainer later needs case content in a document or
vector form (for embeddings/RAG per the architecture doc's §6), that is a
downstream projection this module's API can feed — not a reason to move the
source of truth. This module does not implement that projection; it is
Team 1's concern, and the API contract (`docs/API_CONTRACT.md`) exposes what
Team 1 needs to build it.

## ADR-03: Account deletion and shared cases

**Gap.** Both the PRD (§11 Risks) and the Requirements Gathering Document
(§8) flag this as an open question, with a proposed-but-unconfirmed
resolution: *"shared cases remain with an 'anonymous' contributor label."*

**Decision.** Adopted as specified, made concrete: on account deletion,
cases the user had shared to the community are retained with
`owner_deleted = true` and the API reports the contributor as `"Anonymous"`
instead of the (now-gone) user's identity. Cases that were never shared
(private-only) are hard-deleted along with the account, since no other user
has a claim on them. This is enforced in one place: the account-deletion
service function, not scattered across endpoints.

**Why.** This matches the proposal already on record in both source
documents and closes the gap rather than leaving deletion behavior
undefined, which the requirements-traceability principle in the RGD (§7 —
"no orphan requirements") argues against leaving unresolved.

## ADR-04: Signup "verification step" — mechanism

**Gap.** FR/AC for US-03 says *"an account is created and a verification
step is triggered"* but never specifies the channel (email, OTP, SMS) or
whether an unverified account can log in. The PRD's non-goals list rules out
password reset via SMS but says nothing about signup verification, and no
email-sending infrastructure appears anywhere in the architecture document.

**Decision.** Implement token-based email verification as a stub: signup
generates a verification token and a `POST /auth/verify` endpoint accepts
it; the response to signup includes the token directly (clearly marked
`dev_only`) instead of emailing it, since no transactional email service is
provisioned for the MVP. An unverified account **can** log in — verification
is tracked but not enforced as a login gate.

**Why.** Blocking login on email verification with no email service to
deliver the token would make signup a dead end, contradicting the "onboarding
completable in under 2 minutes" NFR-03 target. Returning the token directly
keeps the feature demonstrably working end-to-end for the MVP demo and
leaves a single, clearly-labeled seam (`app/services/notifications.py`) where
a real email provider drops in later without changing the auth flow.

## ADR-05: Content review queue for uploads

**Gap.** RGD §8 leaves open "whether a content review queue is needed
before v1.1." The PRD resolves this for v1.0: upload guidelines plus Admin
removal rights (FR-11) are the only controls; no pre-publication review
queue.

**Decision.** No review queue in v1.0. `is_shared` cases are visible
immediately on sharing. Admin removal (soft-delete, `is_removed = true`,
with a `removal_reason`) is the only moderation control, exactly as scoped.

**Why.** This isn't a gap this module needed to resolve — the PRD already
decided it. Recorded here only so the "no review queue" behavior reads as a
deliberate MVP scope choice if someone finds it while testing, not a missing
feature.

## ADR-06: Dashboard ordering when the case taxonomy has no Product Management types

**Gap.** FR-04 requires the dashboard to be "ordered by the user's
firm-type preference," and the one concrete example given (US-03 AC) is
*"Given a user who selected Consulting … consulting-type cases appear first."*
But the case taxonomy (`case_type`), derived in the Requirements Gathering
Document from document analysis of existing casebooks, is entirely
consulting-flavored: `PROFITABILITY`, `MARKET_ENTRY`,
`MERGERS_ACQUISITIONS`, `PRICING`, `OPERATIONS`. There is no PM-specific
case type, so "order by firm-type preference" has no direct mapping for a
user who selected Product Management.

**Decision.** Dashboard ordering is driven primarily by the optional
`case_preferences` a user picks at onboarding (e.g. `["M&A", "Pricing"]`),
matched against `case_type` — this satisfies the Consulting example
directly, since a Consulting user's preferences are naturally drawn from
the (consulting-only) taxonomy. For a Product Management user with no
matching preferences, the dashboard falls back to newest-first, and this
fallback is surfaced as a known v1.0 limitation rather than hidden behind
an invented case-type mapping.

**Why.** Inventing a "PM maps to Operations" rule (an earlier draft of this
code did exactly that) would quietly misrepresent unrelated cases as
PM-relevant with no basis in the requirements documents. Making the gap
visible is more useful to whoever picks up v1.1: the real fix is extending
the case taxonomy with PM-specific types (product sense, metrics,
guesstimates, RCA), which is a taxonomy change requiring Team 1
sign-off (schema freeze), not something this module should do unilaterally
mid-MVP.

## ADR-07: Demo hosting under a zero-budget constraint

**Context.** ADR-01 commits this module to Postgres, matching the
product-wide architecture doc's Google Cloud SQL + Cloud Run + Google
Cloud Storage target. Two constraints applied to the first live demo:
nobody had GCP provisioned yet, and the team had **no budget at all** —
not "keep it cheap", but zero spend, and in practice also no willingness
to put a card on file (several "free tier" products still require one).

**Decision.** Demo deployments use **Neon** (free managed Postgres),
**Render**'s free Docker instances for the API, **Vercel** Hobby for the
frontend, and store uploaded PDFs **as bytes in Postgres**
(`STORAGE_BACKEND=database`) rather than in object storage. See
`docs/DEPLOYMENT.md`. None of these require a payment method.

**Why PDFs in the database.** The obvious choice was Cloudflare R2 (free
10 GB, S3-compatible, and `S3CompatibleStorage` already supports it), but
R2 requires a card on file to activate. Storing bytes in Postgres removes
the entire second vendor: no extra account, no access keys, one fewer
thing that can be misconfigured under time pressure. At demo volumes — a
handful of PDFs of a few MB each against Neon's 0.5 GB — the usual
objections don't bite yet.

They do bite later, and deliberately so: bytes in the database inflate
backups, every download flows through the app process, and there is no CDN.
`DatabaseStorage` documents this in its own docstring so the next person
doesn't mistake it for an endorsement. The migration path is
`STORAGE_BACKEND=s3` plus a one-time copy of `case_files` rows into a
bucket; `cases.storage_key` is backend-agnostic, so no schema change is
involved.

**Why this doesn't contradict ADR-01.** Nothing in this module talks to
Postgres or object storage in a provider-specific way.
`backend/app/database.py` accepts any `DATABASE_URL` SQLAlchemy
understands, and Neon is the same Postgres engine and driver Cloud SQL
would be. `S3CompatibleStorage` speaks the S3 API, which GCS also supports
via its
[S3-compatibility mode](https://cloud.google.com/storage/docs/interoperability).
Swapping either is an environment-variable change, not a code change —
the same property ADR-01's "Consequence" section claimed for the database,
now extended to storage and enforced by the `Storage` ABC.

**Consequence.** `docs/DEPLOYMENT.md` describes a demo deployment, not a
production one, and says so. Whoever owns the real launch environment
should replace it with GCP provisioning steps (Cloud SQL, a GCS bucket +
IAM service account, Cloud Run) and move PDF bytes out of Postgres as part
of that work. Render's free tier in particular is unsuitable for anything
beyond a demo: it sleeps after 15 minutes idle with a ~1 minute cold start,
and is capped at 750 instance-hours per month.

## Summary for integrators (Team 1 / Team 3)

- Auth: JWT bearer tokens issued by this module's `/auth/login`; see
  `docs/API_CONTRACT.md` for the token shape and the dependency you can
  reuse to validate them in your own FastAPI services.
- Case schema: frozen relational shape in `backend/app/models/case.py`,
  exposed read-only (for shared cases) via `GET /cases`; source of truth is
  Postgres, not MongoDB, per ADR-02 above.
- User profile: `target_firm_type` and `case_preferences` are readable via
  `GET /profile/me` once a bearer token is presented.
