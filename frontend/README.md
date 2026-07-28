# Frontend — Account Management & Case Repository

React + Vite + Tailwind CSS SPA implementing Module 2's UI, built directly
against [`../docs/API_CONTRACT.md`](../docs/API_CONTRACT.md).

## Requirements

- Node.js 20+

## Setup

```bash
cp .env.example .env.local   # set VITE_API_BASE_URL if the backend isn't on localhost:8000
npm install
npm run dev                  # http://localhost:5173
```

The backend must be running (see `../backend/README.md`) and its CORS
config (`CORS_ALLOW_ORIGINS` in `backend/.env`) must include this dev
server's origin — the default `.env.example` on both sides already
matches (`http://localhost:5173`).

`npm install` will generate `package-lock.json` on first run — commit it
once you have it, so CI (`.github/workflows/ci.yml`) can switch from
`npm install` to `npm ci` with real dependency caching.

## Building

```bash
npm run build      # outputs to dist/
npm run preview    # serve the production build locally
```

`VITE_API_BASE_URL` is baked into the static build at build time, not read
at runtime — set it in your hosting provider's environment variables
*before* the first production build, not after. See
[`../docs/DEPLOYMENT.md`](../docs/DEPLOYMENT.md) for the full production
deployment checklist (Vercel, plus the backend/database/storage it talks to).

## Project structure

```
src/
  main.jsx              Entry point — router + AuthProvider wiring
  App.jsx                 Route table (public vs. ProtectedRoute)
  api/
    client.js               Single axios instance: attaches the bearer
                             token, transparently refreshes it once on 401
  context/
    AuthContext.jsx          Current user, login/signup/logout
  components/
    ProtectedRoute.jsx        Redirects to /login if not authenticated
    Navbar.jsx
    CaseCard.jsx               Renders exactly the fields US-04's AC requires
    EmptyState.jsx             "No cases match" + reset-filters (US-04 AC)
  pages/
    Signup.jsx / Login.jsx
    Onboarding.jsx             Target firm type (mandatory) + preferences
    Dashboard.jsx              Personalized recommendations (FR-04)
    Repository.jsx             Browse/search/filter/sort (US-04)
    CaseDetail.jsx             View, share/withdraw, delete, admin moderate
    Upload.jsx                 PDF upload with client-side size/type checks
                               (server is still the source of truth — see
                               backend FR-09 validation)
    Profile.jsx                Edit profile, delete account
```

## How auth state works

`AuthContext` holds the current user (fetched from `GET /auth/me`) and
exposes `login`/`signup`/`logout`. Tokens live in `localStorage` (read/
written only through `src/api/client.js` — nowhere else in the app touches
`localStorage` directly, so token handling stays in one place). On a 401
from any non-auth endpoint, the axios interceptor tries `POST /auth/refresh`
once and retries the original request; if that also fails, tokens are
cleared and the next protected-route render redirects to `/login`.

## Known limitations (v1.0, matching the PRD's non-goals)

No OAuth login, no case ratings/comments, no bookmarking UI, no mobile app
(the layout is responsive to mobile browser widths per NFR-03, but this is
a web app, not a native app). See the root README's MoSCoW table for the
full scope line.
