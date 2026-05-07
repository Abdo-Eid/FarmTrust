# FarmTrust Portal

Satellite-based land intelligence portal for agricultural financing decisions.

## Stack

| Layer | Choice |
|---|---|
| Framework | Next.js 16 (App Router, Turbopack) |
| Runtime | Bun |
| Language | TypeScript |
| Styling | Tailwind CSS |
| Maps | react-leaflet 5 + Leaflet 1.9 |
| Auth | better-auth (email/password, SQLite session store) |
| DB | `bun:sqlite` — `dev.db` file at project root |
| Forms | react-hook-form + zod |
| Charts | Recharts |
| PDF | @react-pdf/renderer |
| Data fetching | TanStack Query |

## First-time setup

```bash
bun install
bun setup        # creates DB tables + seeds 3 mock users
bun dev
```

Open [http://localhost:3000](http://localhost:3000).

## Scripts

| Command | What it does |
|---|---|
| `bun dev` | Dev server with Turbopack |
| `bun build` | Production build |
| `bun start` | Serve production build |
| `bun typecheck` | TypeScript check (no emit) |
| `bun db:migrate` | Run better-auth schema migrations |
| `bun db:seed` | Seed mock users into dev.db |
| `bun setup` | `db:migrate` + `db:seed` (run once after clone) |

## Demo credentials

| Email | Password | Role |
|---|---|---|
| analyst@farmtrust.eg | demo123 | analyst |
| admin@farmtrust.eg | demo123 | admin |
| reviewer@ncb.eg | demo123 | analyst |

> Remove the credentials hint block in `src/app/(auth)/login/page.tsx` before production.

## Environment

`.env.local` is present for dev. Required variables:

```
BETTER_AUTH_SECRET=   # any random string — change in production
BETTER_AUTH_URL=      # full app URL (e.g. https://farmtrust.eg)
NEXT_PUBLIC_API_BASE= # internal API base path (default: /api)
```

## Map tiles

- **Satellite + labels**: Esri World Imagery + CartoDB light-only-labels (no key required)
- **Street / RGB mode**: OpenStreetMap (no key required)

## Auth notes

- Sessions stored in `dev.db` (SQLite, gitignored, auto-created by `bun db:migrate`)
- Route protection: `src/proxy.ts` (Next.js 16 proxy, fast cookie check)
- To swap to real users: replace `MOCK_USERS` in `scripts/seed.ts` with a DB lookup in `src/lib/auth.ts`
- SSO-ready: add an OIDC / Azure AD provider to `betterAuth({})` in `src/lib/auth.ts`
