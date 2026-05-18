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

## Gap Diagnostics Usage

Status: unresolved

Current output contracts include gap diagnostics under "plus gap diagnostics." We need to decide how the pipeline should use them.

Topics to resolve:
- Which stages consume `long_gap_count` and `long_gap_windows`.
- How seasonal analysis should interpret long gaps and gap overlap.
- How scoring/confidence should use `gap_overlap_count`, `gap_overlap_risk`, and `gap_overlap_stage`.
- How these diagnostics should appear in final lender-facing evidence.
- Whether gap diagnostics only lower confidence or can also change labels/flags.

Resolution target:
- Update `docs/ENGINEERING.md` with the chosen pipeline behavior.
- Update `docs/DECISIONS.md` if this becomes a committed policy.
