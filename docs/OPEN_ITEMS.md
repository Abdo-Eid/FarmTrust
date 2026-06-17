# Open Items

Purpose: temporary holding place for unresolved project-wide topics that need a decision or deeper discussion. Clear items from this file after they are resolved and promoted into the right canonical doc.

## Satellite Source Selection

Status: unresolved

We need to explore available satellite source options and decide when and why to use each one.

Topics to resolve:
- Sentinel-2 as the current implemented path.
- Landsat as a possible fallback or complement.
- Other possible sources if needed.
- When each source is appropriate.
- Tradeoffs: revisit frequency, spatial resolution, cloud coverage, cost, data availability, licensing, and pipeline complexity.

Resolution target:
- Update `docs/ENGINEERING.md` with the chosen source strategy.
- Update `docs/DECISIONS.md` if the decision changes or refines the current satellite-source decision.

## Evidence Coverage Thresholds

Status: partially resolved

Gap diagnostics are now interpreted as satellite evidence limitations, not land/farmer risk. The remaining work is to choose validated thresholds and contract fields for user-facing evidence coverage.

Topics to resolve:
- Thresholds for `satellite_evidence_coverage`: good / fair / limited / insufficient.
- Minimum usable observation count for a complete assessment.
- Maximum allowed gap size or `gap_ratio` before an assessment becomes incomplete.
- How strongly `gap_overlap_count`, `gap_overlap_risk`, and `gap_overlap_stage` affect assessment confidence.
- Exact API/report fields for satellite evidence coverage and assessment-confidence rationale.

Resolution target:
- Update `docs/PIPELINE.md` with chosen thresholds and interpretation rules.
- Update `docs/ENGINEERING.md` if API/interface contracts change.
- Update `docs/DECISIONS.md` if threshold policy becomes a durable commitment.
