# Production deployment — Module 2 (Account Management & Case Repository)

Four pieces, in this order (each step needs a value produced by the one
before it):

1. **Database** — Neon (managed Postgres)
2. **Object storage** — Cloudflare R2 (S3-compatible; real AWS S3 also works, see the note in step 2)
3. **Backend** — Render (Docker, runs `backend/Dockerfile` as-is)
4. **Frontend** — Vercel (static Vite build)

None of these steps can be done by an AI agent on your behalf — each is a
real account signup / real payment method / real API credential, which is
exactly the kind of thing that has to be a human, deliberate action. This
doc is the checklist; you click through it.

**Before you start:** this replaces Codespaces as the source of truth.
Once deployed, `git push` to `main` auto-redeploys both Render and Vercel
(once you connect them, which is the default when importing from GitHub) —
no more manual restarts or copying `.env.example`.

---

## Step 1 — Database: Neon

1. Go to **https://neon.tech** → sign up (GitHub OAuth is fastest).
2. Create a project (e.g. `casearena`).
3. Neon shows a connection string like:
   ```
   postgres://<user>:<password>@<host>/<dbname>?sslmode=require
   ```
4. **Edit the scheme** — SQLAlchemy needs the `psycopg2` driver named
   explicitly. Change `postgres://` to `postgresql+psycopg2://` at the
   very start, keep everything else (including `?sslmode=require`) as-is:
   ```
   postgresql+psycopg2://<user>:<password>@<host>/<dbname>?sslmode=require
   ```
5. Save this string — it's your `DATABASE_URL` in Step 3.

## Step 2 — Object storage: Cloudflare R2

Local disk storage (this app's dev default) gets wiped on almost every
PaaS redeploy or restart — silently deleting every uploaded PDF. Real
object storage is not optional for a hosted deployment.

1. Go to **https://dash.cloudflare.com** → sign up → **R2** in the sidebar.
2. Create a bucket (e.g. `casearena-cases`).
3. **Manage R2 API Tokens** → create a token with **Object Read & Write**,
   scoped to that bucket.
4. Note down: **Access Key ID**, **Secret Access Key**, and your
   **Account ID** (shown on the R2 overview page).
5. Your values for Step 3:
   ```
   STORAGE_BACKEND=s3
   S3_BUCKET_NAME=casearena-cases
   S3_REGION=auto
   S3_ACCESS_KEY_ID=<access key id>
   S3_SECRET_ACCESS_KEY=<secret access key>
   S3_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com
   ```

**Prefer real AWS S3 instead?** Create a bucket + an IAM user scoped to
`s3:PutObject`/`s3:GetObject`/`s3:DeleteObject` on it, leave
`S3_ENDPOINT_URL` blank, set `S3_REGION` to the bucket's real AWS region
(e.g. `us-east-1`). The code path is identical either way — see
`backend/app/services/storage.py`'s `S3CompatibleStorage`.

## Step 3 — Backend: Render

1. Go to **https://render.com** → sign up → connect your GitHub account,
   authorize access to `casearena-account-case-repository`.
2. **New +** → **Blueprint** → select this repo. Render should detect
   `render.yaml` at the repo root and prompt you for the env vars it marks
   `sync: false`.
   (If Blueprint doesn't pick it up: **New +** → **Web Service** → select
   the repo → **Root Directory**: `backend` → **Runtime**: `Docker`.)
3. **Plan: choose Starter, not Free.** Render's free tier spins the
   service down after 15 minutes of inactivity — the first request after
   that is a 30–60 second cold start. For a live demo, that's a real risk
   of an audience staring at a spinner. Starter is a few dollars for the
   day; you can downgrade or delete the service right after.
4. Fill in the environment variables:
   - `DATABASE_URL` = the Neon string from Step 1
   - `JWT_SECRET_KEY` = a real random secret — generate one anywhere with
     `python3 -c "import secrets; print(secrets.token_urlsafe(48))"`,
     e.g. in the Codespace terminal
   - `S3_BUCKET_NAME`, `S3_REGION`, `S3_ACCESS_KEY_ID`,
     `S3_SECRET_ACCESS_KEY`, `S3_ENDPOINT_URL` = from Step 2
   - `CORS_ALLOW_ORIGINS` — leave a placeholder like `["https://placeholder.vercel.app"]`
     for now; you'll come back and set the real Vercel URL after Step 4
5. Deploy. Render gives you a URL like `https://casearena-backend.onrender.com`.
6. **Run migrations against the new database** — Render dashboard → your
   service → **Shell** tab (runs inside the live container, `DATABASE_URL`
   already set):
   ```bash
   alembic upgrade head
   ```
7. Confirm: visit `https://casearena-backend.onrender.com/health` →
   should return `{"status":"ok"}`. Then `/docs` for the Swagger UI.

## Step 4 — Frontend: Vercel

1. Go to **https://vercel.com/new** → import
   `casearena-account-case-repository`.
2. Framework preset: **Vite**. Root Directory: `frontend`. Build command
   and output directory are Vite's defaults (`npm run build`, `dist`) —
   no changes needed.
3. **Environment Variables** (this is a build-time value — Vite bakes
   `VITE_*` vars into the static bundle, so it must be set *before* the
   first deploy, not edited into the running site after):
   ```
   VITE_API_BASE_URL=https://casearena-backend.onrender.com
   ```
   (your actual Render URL from Step 3)
4. Deploy. Vercel gives you a URL like `https://casearena-....vercel.app`.
5. **Go back to Render** and update `CORS_ALLOW_ORIGINS` to the real
   Vercel URL:
   ```
   CORS_ALLOW_ORIGINS=["https://casearena-....vercel.app"]
   ```
   Env var changes on Render require a redeploy to take effect — trigger
   one from the dashboard (Manual Deploy → Deploy latest commit).

## Step 5 — Smoke test before the demo, not during it

Run this whole list yourself, tonight, not tomorrow morning:

- [ ] Visit the Vercel URL, sign up a fresh account
- [ ] Complete onboarding
- [ ] Upload `backend/seed-data/sample-profitability-case.pdf` (and a
      couple more PDFs with different case types/difficulties, for
      testing filters)
- [ ] Share a case, confirm it shows up under Community
- [ ] **Hard-refresh the page entirely**, or reopen in a new browser —
      confirm the case and its PDF still load. This is the real test that
      storage is actually on R2/S3 and not silently falling back to local
      disk (which would still work *during* the same server process, but
      vanish on Render's next restart)
- [ ] Try case type / difficulty filters and search
- [ ] Sign up a second account, confirm ownership restrictions (no
      edit/delete/share on another user's case)
- [ ] If demoing admin moderation: see below

### Promoting an admin in production

`backend/scripts/promote_admin.py` needs direct DB access — there's
deliberately no API for this (see the script's docstring). From Render's
**Shell** tab:
```bash
python scripts/promote_admin.py <email>
```

## If something breaks right before the demo

- **Render**: dashboard → your service → **Events** tab → redeploy the
  last known-good deploy.
- **Vercel**: dashboard → your project → **Deployments** tab → pick any
  previous deployment → **Promote to Production**.
- Both take under a minute and don't require touching code.
