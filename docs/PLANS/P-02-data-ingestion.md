# P-02 — Data Ingestion (Phase A)

## Links

* PROJECT: `<PROJECT §Phase A ownership>`
* ENGINEERING: `<ENGINEERING §Architecture | ENGINEERING §Data & signals | ENGINEERING §Pipeline>`

## Ownership & boundaries

**Owner:** Data Ingestion role

## Overview of my task

My job in Phase A is to make satellite data reliably available for analysis on Egyptian land plots. Practically, that means: given an AOI, I can fetch imagery and compute index time-series for the last 24 months so the next roles can build on it.

Because the portal/UI isn’t ready yet, I won’t wait for real AOI input. I’ll start with fixture AOIs (sample polygons / point+area) to prove the full ingestion loop end-to-end: AOI → imagery → indices → stored results. Once that works, swapping fixtures for real AOIs should be a clean interface change, not a redesign.

The primary source is Sentinel-2 through STAC (Planetary Computer or AWS Open Data). Landsat is a fallback only when Sentinel-2 coverage is insufficient. I’ll also add a local caching option (script or notebook) so the rest of the team can iterate without repeatedly hitting STAC endpoints during development.

I’ll use exploration notebooks for quick validation (what comes back from STAC, AOI edge cases, visual sanity checks). Any approach that proves stable gets promoted into the ingestion module; notebooks stay as “evidence + explanation,” not production.

When ingestion runs, it produces time-series for NDVI, EVI, NDMI, NDWI, and MNDWI over the last 24 months. The goal is to hand off clear time-series to the ML preprocessing team—data flow first, sophistication later.

### In scope

* Satellite access:

  * Primary: **Sentinel-2** via STAC
  * Fallback: **Landsat** (only when Sentinel-2 coverage is insufficient)
* AOI handling:

  * Accept **polygon** AOIs and **point + area** AOIs (converted to polygon)
  * Geometry validation + clear failure modes
* Time-series extraction:

  * Indices: **NDVI, EVI, NDMI, NDWI, MNDWI**
  * Window: **last 24 months**
  * I need to learn which time-series granularity to use (per-scene timestamps vs fixed interval like monthly), what that changes for downstream modeling, and what tradeoffs matter for Phase A before deciding.
* Minimal persistence:

  * Store AOIs and time-series results with minimal metadata

### Out of scope (explicit non-goals)

* Preprocessing: gap handling, smoothing, interpolation
* Feature engineering beyond raw index series
* Scoring/classification/decisioning
* API endpoints, portal UI integration (beyond defining interfaces/contracts)

## Outcomes (what “done” looks like)

1. Given a valid AOI, we can fetch imagery and compute index time-series for the last 24 months.
2. Results are persisted and are retrievable for ML/preprocessing work.
3. The pipeline is **reproducible** for the team (UV environment + fixtures + documented run path).
4. Analysis/ML can run locally using **cached sample data** to avoid repeated STAC calls during development.

## Data flow (Phase A slice)

1. **AOI intake**
   Validate/repair polygon OR convert point+area → polygon. Persist AOI (same AOI hash → reuse).
2. **Imagery query**
   Query Sentinel-2 STAC for the 24-month window and AOI footprint. If coverage is insufficient, query Landsat fallback.
3. **Index computation**
   Compute NDVI/EVI/NDMI/NDWI/MNDWI per timestamp.
4. **Persist results**
   Write time-series results + extraction metadata.
5. **Dev acceleration**
   Cache fixtures and sample fetch results for local iteration.

## R&D approach (time-boxed)

* Use **exploration notebooks** for STAC query patterns, AOI edge cases, and index extraction verification.
* Time-box spikes **3–5 days max** per unknown area.
* End of spike:

  * Promote the working approach into production module(s)
  * Keep notebooks as “evidence + explanation,” but don’t let them become the system

## Plan & milestones (2-day execution target)

### Milestone 1 — Environment + access (Day 1)

**Deliverables**

* UV environment + lockfile committed
* STAC access proven for Sentinel-2; Landsat fallback endpoint identified
* Notebook: “STAC quickstart + AOI query examples”

**Acceptance**

* A sample AOI can fetch imagery metadata and at least one scene item successfully.

### Milestone 2 — Index time-series extraction (Days 1–2)

**Deliverables**

* Working extraction for NDVI/EVI/NDMI/NDWI/MNDWI over 24 months on fixture AOIs
* Basic error handling (timeouts, empty results, partial coverage)

**Acceptance**

* Running the extraction on fixtures produces a consistent time-series shape and timestamps.

### Milestone 3 — Minimal persistence (Day 2)

**Deliverables**

* Insert/update strategy (reuse existing AOIs; rerun/version strategy)

**Acceptance**

* Fixture run persists AOIs + time-series and can be queried back reliably.

### Milestone 4 — Handoff readiness (Day 2)

**Deliverables**

* Caching script/notebook for sample data (cache location + TTL + opt-out documented)
* Short “How to run ingestion on fixtures” README snippet
* ML handoff note: units, timestamps, missing-data behavior, edge cases

**Acceptance**

* Another team member can clone repo, set up env, run fixture ingestion, and see persisted results.

## Checklist (Definition of Done)

* [ ] UV environment committed (`uv.lock`) + minimal setup snippet in README
* [ ] Exploration notebooks exist (tagged “prototype”):

  * Notes: notebooks live in repo root and use the `ingest_` prefix.
  * [ ] STAC access + query templates
  * [ ] AOI handling (polygon + point/area conversion)
  * [ ] Index extraction verification + visual sanity checks
* [ ] Caching mechanism for sample AOIs/satellite calls documented (location + TTL + opt-out)
* [ ] AOI mapping implemented with clear outcomes:

  * [ ] valid → proceed
  * [ ] repairable → repaired + logged
  * [ ] invalid → rejected + actionable error
* [ ] Extraction produces raw 24-month series for NDVI/EVI/NDMI/NDWI/MNDWI on fixtures
* [ ] Persistence added (AOIs + time-series + minimal metadata) and is queryable
* [ ] Fixture-based integration run is stable and repeatable (record a sample output for regression)
* [ ] ML handoff note written: fields, units, timestamps, quality flags, missing data behavior
