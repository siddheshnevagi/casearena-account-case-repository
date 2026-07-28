# Deployment — Module 2 (Account Management & Case Repository)

This guide deploys the app at **zero cost, with no credit card required**
at any step.

| Piece | Service | Cost | Card needed? |
|---|---|---|---|
| Database | Neon (managed Postgres) | Free — 0.5 GB | No |
| PDF storage | The Postgres database itself | Free — no extra service | No |
| Backend API | Render (Docker, free instance) | Free — 750 hrs/month | No¹ |
| Frontend | Vercel (Hobby) | Free | No |

¹ Render does not require a card for free web services. If yours ever
asks for one, stop and see [If Render asks for a card](#if-render-asks-for-a-card).

**Why PDFs go in Postgres here:** object storage (S3, Cloudflare R2) is the
right answer at scale, but R2 requires a payment method on file even on its
free tier, and every extra vendor is another set of credentials that can be
wrong at 11pm the night before a demo. `STORAGE_BACKEND=database` stores
uploaded bytes in the database the app is already connected to — no second
account, no keys. The S3 path is fully implemented and one env var away when
you outgrow this; see ARCHITECTURE.md ADR-07 for the tradeoff in full.

Steps are ordered by dependency — each one needs a value the previous
produced. Budget ~25 minutes total.

---

## Step 1 — Database: Neon

1. Go to **https://neon.com** → **Sign up** (GitHub OAuth is fastest).
2. Create a project, e.g. `casearena`.
3. Copy the connection string it shows you. It looks like:
   ```
   postgresql://<user>:<password>@<host>/<db>?sslmode=require
   ```
4. **Change the scheme** — SQLAlchemy needs the driver named explicitly.
   Replace the leading `postgresql://` with `postgresql+psycopg2://`,
   leaving everything else (including `?sslmode=require`) untouched:
   ```
   postgresql+psycopg2://<user>:<password>@<host>/<db>?sslmode=require
   ```
5. Keep this handy — it is your `DATABASE_URL` for Steps 2 and 3.

> Neon's free compute sleeps after 5 minutes idle and wakes in well under a
> second, so this is invisible in normal use.

## Step 2 — Create the tables

Render's free instances have no shell, so run migrations from your
Codespace (it already has Python and Alembic installed, and Neon is
reachable from anywhere). In the Codespace terminal:

```bash
cd backend
DATABASE_URL='postgresql+psycopg2://...your neon string...' alembic upgrade head
```

Quote the string — it contains characters the shell would otherwise
interpret. You should see Alembic apply revisions `0001` and `0002`.

This is a one-time step. It is deliberately not automatic on container
boot, so a bad migration can never get half-applied by a restart.

## Step 3 — Backend: Render

1. Go to **https://render.com** → sign up → connect GitHub, authorizing
   access to `casearena-account-case-repository`.
2. **New +** → **Blueprint** → pick this repo. Render reads `render.yaml`
   from the repo root and will prompt for the values marked `sync: false`.
   (Fallback if Blueprint isn't detected: **New +** → **Web Service** →
   this repo → Root Directory `backend`, Runtime `Docker`, Instance Type
   **Free**, and add the env vars below by hand.)
3. Confirm the instance type is **Free**.
4. Set the environment variables:

   | Variable | Value |
   |---|---|
   | `DATABASE_URL` | the Neon string from Step 1 |
   | `JWT_SECRET_KEY` | a real random secret — see below |
   | `CORS_ALLOW_ORIGINS` | `["https://placeholder.vercel.app"]` for now; fixed in Step 4 |

   `STORAGE_BACKEND=database` is already set by `render.yaml` — leave it.

   Generate the JWT secret in your Codespace terminal:
   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(48))"
   ```
   Do not reuse the `dev-only-secret-change-me` default; it is public in
   this repo, and anyone with it can mint valid tokens for your API.

5. Deploy. You get a URL like `https://casearena-backend.onrender.com`.
6. Verify: open `<your-render-url>/health` → `{"status":"ok"}`.
   Then `/docs` for the Swagger UI.

## Step 4 — Frontend: Vercel

1. Go to **https://vercel.com/new** → import
   `casearena-account-case-repository` (sign in with GitHub).
2. **Root Directory**: `frontend`. Framework preset should auto-detect as
   **Vite**; build command `npm run build` and output `dist` are correct
   defaults — leave them.
3. **Environment Variables** — add before deploying:
   ```
   VITE_API_BASE_URL = https://casearena-backend.onrender.com
   ```
   (your real Render URL from Step 3)

   This must be set *before* the first build. Vite bakes `VITE_*` values
   into the static bundle at build time; editing it afterwards does
   nothing until you redeploy.
4. Deploy. You get a URL like `https://casearena-xyz.vercel.app`.
5. **Return to Render** → your service → **Environment** → set
   `CORS_ALLOW_ORIGINS` to your real Vercel URL:
   ```
   ["https://casearena-xyz.vercel.app"]
   ```
   Save. Render redeploys automatically on env var changes; wait for it to
   go green before testing. Without this the browser blocks every API call
   with a CORS error.

## Step 5 — Smoke test tonight, not tomorrow

Run this whole list yourself, now. Every item has caught a real bug at
some point in this project.

- [ ] Open the Vercel URL → sign up a fresh account
- [ ] Complete onboarding (pick Consulting + a couple of case preferences)
- [ ] Upload `backend/seed-data/sample-profitability-case.pdf`
- [ ] Upload 3–4 more PDFs with **different case types and difficulties** —
      you need variety to demo filters convincingly
- [ ] Open a case → **View PDF** → confirm it actually renders
- [ ] Share a case → confirm it appears under Community
- [ ] **Close the browser entirely, reopen, log back in, open the PDF
      again.** This is the real durability check — it proves bytes came
      back out of Postgres rather than out of a process that is about to
      be recycled
- [ ] Repository: try case-type filter, difficulty filter, and search
      (3+ characters)
- [ ] Set filters that match nothing → confirm the empty state + reset
- [ ] Sign up a **second** account → confirm the first user's shared case
      is visible but has **no** edit/delete/share buttons
- [ ] Log out, fail a login 5× → confirm the lockout message

### Promoting an admin (only if demoing moderation)

Same pattern as migrations — run it from the Codespace against Neon:

```bash
cd backend
DATABASE_URL='postgresql+psycopg2://...' python scripts/promote_admin.py you@example.com
```

## Demo-day operational notes

**Warm it up first.** Render free instances spin down after 15 minutes
idle; the next request takes ~1 minute while it wakes, and the audience
watches a loading page. Five minutes before you present, open
`<your-render-url>/health` and then the Vercel URL, and click through one
page. Both stay warm as long as you keep using them.

Optionally, keep it awake across the whole demo window with a free pinger
(**https://cron-job.org** or UptimeRobot's free tier) hitting
`<your-render-url>/health` every 10 minutes. Note the free budget is 750
instance-hours/month and a permanently-awake service burns ~730 — fine for
one service, but don't leave a pinger running all month if you later add a
second free service.

**Have the Codespace open as a backup.** It is a known-working environment;
if something goes wrong with hosting mid-demo you can fall back to it
rather than debugging live.

**Rollback, if a deploy breaks something:**
- Render → service → **Events** → redeploy the last good deploy
- Vercel → project → **Deployments** → pick a previous one → **Promote to
  Production**

Both take under a minute and need no code changes.

## If Render asks for a card

Render's free web services shouldn't require one. If yours does, the
closest no-card substitute is **Hugging Face Spaces** with the Docker SDK —
genuinely free, and it only sleeps after 48 hours of inactivity rather than
15 minutes, which is better demo behavior. It needs a small change (Spaces
serve on port 7860, declared via `app_port` in the Space's README
frontmatter). Ask and I'll write those steps out.

## Moving to the production stack later

This is a demo deployment, chosen under a zero-budget constraint. The
product-wide architecture document targets Google Cloud SQL, Google Cloud
Storage and Cloud Run. Nothing here blocks that migration — see
ARCHITECTURE.md ADR-07 — but whoever owns the real launch environment
should replace this document's steps rather than build on them, and should
move PDF bytes out of Postgres and into object storage
(`STORAGE_BACKEND=s3`) as part of that work.
