# PRD Gap Log — Module 2

Quick-reference index of every loose end found while implementing the
Module 2 PRD, and where it was resolved. Full reasoning lives in
[`ARCHITECTURE.md`](ARCHITECTURE.md) — this file is the scan-in-ten-seconds
version for standups and reviews.

| # | Gap / conflict found in PRD or RGD | Resolution | Detail |
|---|---|---|---|
| 1 | PRD assumes Supabase backend; product architecture doc mandates FastAPI + Cloud SQL Postgres | Built on FastAPI + Postgres, following the cross-team architecture doc | [ADR-01](ARCHITECTURE.md#adr-01-backend-framework-and-datastore--supabase-vs-fastapi--cloud-sql) |
| 2 | Architecture doc assigns "case repository metadata" to MongoDB; PRD's filter/search/sort/2-second NFR fits a relational store better | Cases live in Postgres as system of record; Mongo/vector projections are Team 1's downstream concern | [ADR-02](ARCHITECTURE.md#adr-02-case-repository-metadata--postgres-vs-mongodb) |
| 3 | Open question: what happens to shared cases when the owning account is deleted | Shared cases retained with `owner_deleted=true`, shown as "Anonymous"; private-only cases hard-deleted with the account | [ADR-03](ARCHITECTURE.md#adr-03-account-deletion-and-shared-cases) |
| 4 | "Verification step is triggered" on signup — mechanism unspecified, no email service in the architecture | Token-based verification stub; token returned in the signup response (dev-only), login not gated on it | [ADR-04](ARCHITECTURE.md#adr-04-signup-verification-step--mechanism) |
| 5 | Open question: content review queue before v1.1 | Confirmed no queue for v1.0, per PRD §11 — Admin removal is the only control | [ADR-05](ARCHITECTURE.md#adr-05-content-review-queue-for-uploads) |
| 6 | FR-04 dashboard ordering "by firm-type preference" has no case-type mapping for Product Management, since the frozen taxonomy is consulting-only | Ordering driven by `case_preferences`; PM users without a match fall back to newest-first, documented as a v1.0 limitation, not hidden | [ADR-06](ARCHITECTURE.md#adr-06-dashboard-ordering-when-the-case-taxonomy-has-no-product-management-types) |

If you find another gap while extending this module, add a row here and an
ADR entry in `ARCHITECTURE.md` in the same pass — don't let one exist
without the other.
