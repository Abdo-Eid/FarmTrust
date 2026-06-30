# T-09 — Assessment Window Configuration & Season Calendar

## Links

- PROJECT: §Current-build scope (what we ship first) | §Big picture (end-to-end)
- ENGINEERING: §Current-build backend flow | §Interfaces
- DECISIONS: 2026-06-24 — Pipeline correction — fill+smooth preprocessing, hybrid-threshold activity detection

## Goal

Let users control and understand the assessment window instead of always ending at today, and optionally provide agro-phenology calendar guidance so the window aligns with meaningful seasonal boundaries.

## Scope

### IN

- Explore window configuration options: explicit dates, preset intervals, calendar-assisted presets.
- Evaluate Egypt agro-phenology calendars (winter/summer/Nili seasons) as a reference source for window recommendations, and document what is available, reliable, and how it would be consumed.
- Design the API contract change for window start/end dates (extend `CreateLandPayload`).
- Design the portal UI for window selection (date pickers, preset buttons, calendar overlay on map).
- Produce a recommended approach with clear trade-offs.

### OUT

- Implementation of the chosen approach (follow-up task).
- Backend changes to use the new window fields in `worker.py` (currently `start = end - timedelta(days=lookback_days)` at line 133–134).
- Portal UI implementation.
- Actual integration of a phenology database or third-party calendar API.

## Role Split

- Driver: explore options, document trade-offs, recommend approach.
- Reviewer: confirm the recommendation is buildable within current-build constraints.
- Curator: if agro-phenology calendars become product truth, ripple into `PROJECT.md` and `ENGINEERING.md`.

## Chosen Approach

*To be decided. Options to evaluate are listed below.*

## Options

### Option A — Explicit start/end dates

User picks both dates on a calendar widget. The API replaces `lookback_days` with `start_date` / `end_date` (optional; fall back to 24-month lookback).

- **Trade-off**: Most transparent and flexible. Risk: users pick poor windows that break seasonal context.
- **Evidence needed**: API contract diff, portal date-picker feasibility.
- **Decision trigger**: User needs full control for non-standard assessments.
- **Kill condition**: Portal UX complexity outweighs benefit.

### Option B — Preset intervals

User chooses from labelled presets: "Last 6 months", "Last 12 months", "Last 24 months", "Current agronomic season". Presets map to date ranges computed server-side.

- **Trade-off**: Simple UX but less flexible. "Current agronomic season" needs a hard-coded or configurable calendar.
- **Evidence needed**: Calendar source quality, typical season boundaries for Egypt.
- **Decision trigger**: User prefers guided UX over full control.
- **Kill condition**: Season boundaries too variable to preset reliably.

### Option C — Calendar-assisted recommendation

System suggests optimal windows from known agro-phenology calendars (e.g. winter: Nov–Apr, summer: Apr–Aug, Nili: Jul–Oct for Egypt). User can accept or override. Suggestion appears as a timeline overlay on the map.

- **Trade-off**: Best lender-facing guidance; most complex to build and maintain.
- **Evidence needed**: Existence, quality, and license of Egypt phenology reference data. Integration cost estimate.
- **Decision trigger**: User wants automated guidance as a differentiator.
- **Kill condition**: No reliable, per-governorate phenology source exists; calendar maintenance cost is too high.

## Task List

- [ ] Document current window behavior: `api/worker.py` lines 133–134 hardcode `end = date.today()`, no user-facing window control.
- [ ] Map the current API contract: `CreateLandPayload.lookback_days` (default 730, ge 90, le 1825) and `api/schemas.py:29`.
- [ ] Research available Egypt agro-phenology calendars (FAO, Ministry of Agriculture, published research, open datasets) and assess reliability, granularity, and licensing.
- [ ] For each Option (A, B, C), write: API diff, portal UX sketch, effort estimate.
- [ ] Evaluate Option C calendar source quality: winter/summer/Nili boundaries per governorate vs national generic.
- [ ] Decide on chosen approach; record in this file and add a `DECISIONS.md` entry.
- [ ] Promote chosen approach to `PROJECT.md` (`§Current-build scope`) and `ENGINEERING.md` (`§Interfaces`) if it changes shared truth.

## Feedback Log

- 2026-06-28: User validated a 6-month run and could not tell where seasons started/ended. Window boundary was always end-of-today, making seasonal context unclear. Requested options for window configuration and possible phenology calendar recommendations.

## Decisions

*To be filled.*

## Open Questions

- [clarification needed] Should Egypt season boundaries use a single national calendar (NOV–APR winter, APR–AUG summer, JUL–OCT Nili) or per-governorate tables?
- [clarification needed] If Option C is chosen, should the calendar come from a curated file in the repo or an external lookup?
- [assumption] Portal date picker is implementable with the existing Leaflet map + Radix UI date components.

## Knowledge to Keep

- Current window is hard-coded in `api/worker.py` at lines 133–134 with `lookback_days` passed from `Land` model.
- Activity-window detection (`farmtrust_core/seasonal/seasons.py`) uses NDVI-only hybrid threshold and does not consider agro-phenology calendars.
- Egypt has three main agricultural seasons: Winter (Nov–Apr), Summer (Apr–Aug), Nili (Jul–Oct).
- Validate whether per-governorate variation matters (Nile Delta vs desert reclamation vs Upper Egypt).

## Done Summary

- Pending.
