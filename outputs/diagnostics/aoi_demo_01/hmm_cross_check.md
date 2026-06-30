# HMM cross-check vs deterministic detector — aoi_demo_01

> Research cross-check (`isolated_research_cross_check`, provenance level 2).
> Diagnostic only — not consumed by scoring; does not change production output.

- Detector cycles: **4**
- HMM cycles: **4** (delta +0)
- Matched within ±30d of peak: **4**
- Mean |SOS| / |POS| / |EOS| delta (days): 2.75 / 0.0 / 9.5
- Lifecycle agreement: 1.0
- Overall agreement within tolerance: **True**

| detector season | SOS Δ | POS Δ | EOS Δ | lifecycle match |
|---|---|---|---|---|
| season_01 | -6 | +0 | +8 | True |
| season_02 | +0 | +0 | +10 | True |
| season_03 | +3 | +0 | +9 | True |
| season_04 | -2 | +0 | +11 | True |
