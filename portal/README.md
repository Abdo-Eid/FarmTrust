# FarmTrust Portal

Next.js 14 web portal for FarmTrust — a satellite-based land assessment tool for banks and agricultural financiers in Egypt.

## Stack

- **Next.js 14** (App Router) + **TypeScript**
- **Tailwind CSS** with custom teal/turquoise design tokens
- **Bun** runtime
- **TanStack Query v5** for data fetching and job polling
- **MapLibre GL** for AOI input and evidence workbench maps
- **Recharts** for NDVI time-series visualization
- **@react-pdf/renderer** for PDF report generation
- **NextAuth v4** for authentication
- **React Hook Form + Zod** for form validation
- **Radix UI** for accessible primitives (Dialog, Tabs, Select)

## Getting Started

```bash
bun install
bun dev
```

Portal runs at `http://localhost:3000`.

## Demo Credentials

| Email | Password | Role |
|-------|----------|------|
| analyst@farmtrust.eg | demo123 | Analyst |
| admin@farmtrust.eg | demo123 | Admin |
| reviewer@ncb.eg | demo123 | Analyst |

> These credentials are hardcoded in `src/app/api/auth/[...nextauth]/route.ts`. Remove and replace with real DB auth before production.

## Screens

| Route | Screen |
|-------|--------|
| `/login` | Login |
| `/lands` | Lands List |
| `/lands/new` | Add Land (AOI input + map) |
| `/lands/[id]` | Processing Status (live polling) |
| `/lands/[id]/summary` | Land Assessment Summary |
| `/lands/[id]/workbench` | Geospatial Evidence Workbench |
| `/lands/[id]/evidence` | Evidence & Data Tables |
| `/lands/[id]/report` | Report Export (PDF) |
| `/admin` | System Administration |

## Environment

```env
# .env.local
NEXT_PUBLIC_API_BASE=/api        # swap to http://localhost:8000 for real FastAPI
NEXTAUTH_SECRET=your-secret
NEXTAUTH_URL=http://localhost:3000
```

Setting `NEXT_PUBLIC_API_BASE` to the FastAPI backend URL is the only change needed to switch from mock data to live data — no code changes required.

## Mock Data

All API responses are served by Next.js Route Handlers under `src/app/api/` using mock data from `src/lib/mocks/`. The mock dataset includes 12 land records covering all status, confidence, and risk flag combinations.
