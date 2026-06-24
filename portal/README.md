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
| Forms | react-hook-form + zod |
| Charts | Recharts |
| PDF | @react-pdf/renderer |
| Data fetching | TanStack Query |

## First-time setup

```bash
bun install
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

## Environment

`.env.local` is present for dev. Required variables:

```
NEXT_PUBLIC_API_BASE= # internal API base path (default: /api)
```

## Map tiles

- **Satellite + labels**: Esri World Imagery + CartoDB light-only-labels (no key required)
- **Street / RGB mode**: OpenStreetMap (no key required)

## Portal notes

- This portal is the interface for the work produced by the FarmTrust pipeline.
- It loads directly into the lands and assessment surfaces.
- The backend API stays separate at `http://localhost:8000`.
