# Portal

Next.js portal for AOI input, summary view, and PDF download.

## Setup Instructions

This directory is configured as a workspace in the FarmTrust monorepo running on **Bun**.

### Prerequisites

- [Bun](https://bun.sh) installed (version 1.0 or higher)
- Root `package.json` already configured with workspace support

### Initial Setup

If this is a fresh setup and the Next.js app hasn't been scaffolded yet, run:

```bash
# From the repository root
bun create next-app ./portal --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"
```

This will scaffold a Next.js app inside the `/portal` directory with:
- TypeScript support
- Tailwind CSS
- ESLint configuration
- App Router
- `src/` directory structure
- `@/*` import alias

### Development

Once the Next.js app is scaffolded, you can run it from the **repository root** using workspace scripts:

```bash
# Development mode (from root)
bun dev:portal

# Build for production (from root)
bun build:portal

# Start production server (from root)
bun start:portal
```

Or directly from within the `/portal` directory:

```bash
# Navigate to portal
cd portal

# Development mode
bun dev

# Build for production
bun build

# Start production server
bun start
```

### Project Structure

After scaffolding, the portal will contain:
- `src/app/` - Next.js App Router pages and layouts
- `src/components/` - Reusable React components
- `public/` - Static assets
- `package.json` - Portal-specific dependencies
- `next.config.ts` - Next.js configuration
- `tailwind.config.ts` - Tailwind CSS configuration
- `tsconfig.json` - TypeScript configuration

### Integration

The portal integrates with:
- **API** (`/api`) - FastAPI backend for job submission and results
- **Contracts** (`/contracts`) - Shared JSON schemas for type safety
- **Shared** (`/shared`) - Common utilities and helpers
