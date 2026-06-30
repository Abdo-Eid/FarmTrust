# Cross-Team Brief — Satellite Land-Use Subsystem

*For the other agent reviewing this with fresh eyes. This is the satellite analysis / decision-layer half. You're on an adjacent part and we've hit crossing points. Two things up front so you can trust this brief: (1) it separates what is **actually built** from what we have only **designed/discussed**; (2) the crossing points in §5 are potential integration surface — **none of the integration is built yet** — flagged so our two halves don't duplicate work or design incompatible interfaces.*

---

## 1. What this subsystem is

Takes a Sentinel-2 time series for **one** farm parcel (Menofia, Nile Delta, ~0.9 ha; tiles 36RTU/36RUU; 10 m) and produces a phenology / crop-cycle read, a multi-index health read, and a draft **land-use decision** (calibrated for lending) with explicit confidence and a "what we can't tell you" boundary. Guiding principle: keep the inference ladder visible — *Measured → Pattern → Labelled → Judgment* — and present every output as **Observed → Interpreted → Confidence → Watch**.

Scope today: **a single field, two-year record.** Everything below is at that scale unless noted.

---

## 2. Data contract we consume (a real dependency — see crossing points)

**Field-mean CSV** (`indices_timeseries.csv`), one row per acquisition:
`solar_day, timestamp, item_id(s), mgrs_tiles, min_cloud_cover, valid_fraction, {ndvi,evi,ndmi,ndwi,mndwi}_{mean,p95}`.

**Raw cube** (`cube.zarr`, Zarr v3, zstd):
- 10 m: B02, B03, B04, B08 — (time, 6, 18)
- 20 m `/20m/`: B05, B06, B07, B8A, B11, SCL — (time, 3, 10)
- coords `time, x, y, spatial_ref`; raw DN with offset policy `boa_baseline_04_00` (−1000, /10000)
- provenance: `run_metadata.json` (`g15f.run_metadata.v2`), `scenes_index.jsonl` (`g15f.scenes_index.v4`)

Current record: 2 May 2024 → 19 Jun 2026, 280 acquisitions, 248 clean (89%).

**Integrity gate we enforce:** refuse to build unless `CSV rows == cube time steps (root == 20 m)`.

---

## 3. What is actually BUILT (and validated, on this one field)

The analysis pipeline and the methods behind it:

1. **QC + weighting** — keep `valid_fraction ≥ 0.5`, weight observations by quality.
2. **Weighted Whittaker smoother** (λ=3000, daily grid) — gap-fills + denoises in one pass. λ tuned to keep the between-crop bare-soil troughs (λ=6000 over-smoothed and erased one).
3. **Multi-peak phenology** (not a single-season model — this field double-crops): per cycle SOS/EOS at 20 % of the cycle's amplitude, POS, duration, amplitude, greenness integral (biomass proxy); edge-cycle handling.
4. **Crop labelling** from Delta calendar timing + curve shape, confirmed by grower ground truth (this field only).
5. **Multi-index** — NDMI (moisture/stress), NDWI/MNDWI (ruled out rice), NDVI mean-vs-p95 (uniformity), year-over-year overlay.
6. **Pixel-level** — decode the cube directly (NumPy + `zstd` CLI, offset + SCL mask); spatial maps, temporal-variability maps, the berseem cutting-sweep. Validation: NDVI recomputed from raw bands matches the CSV at **r = 0.94**.
7. **NDRE** (B8A,B05) — tracks NDVI (r=0.99); useful as headroom where NDVI saturates; **not** a Fall-Armyworm detector at 20 m.
8. **MSAVI2** — tracks NDVI (r=0.98); cleaner bare-soil floor for fallow / planting-onset.
9. **HMM cross-check** — 4-state Gaussian HMM (Baum-Welch + Viterbi) on the smoothed series; reproduces the threshold cycles to ~4 d (green-up) / ~1 d (harvest), with no hand-set threshold. An unsupervised confirmation the cycles are real.

**Built artifacts:** `menofia_ndvi_report.html` (technical read, 14 figures), `menofia_analysis_process_report.md` (methods + decisions + honest limits), `lender_land_use_card.html` + `lender_methodology_monitoring.md` (the decision layer as a written card + spec), and `analyze.py` / `cube_figs.py` (the pipeline).

Headline result on the field: double-cropped (~2 cycles/yr); the key honest finding is **greenness ≠ yield** — the 2025 corn was Fall-Armyworm-damaged yet read healthy from orbit; neither NDVI nor NDRE could see it.

---

## 4. What is only DESIGNED / DISCUSSED (not built)

Worked through in conversation, **no code, no results yet**:

- A **per-field feature store** that accumulates the label-free phenology feature vectors across many fields/seasons.
- **Unsupervised structure discovery** — clustering (k-Shape/DTW) into cropping archetypes.
- **Anomaly + change detection** — Isolation Forest / autoencoder + BFAST as a monitoring engine.
- An **active-learning / data-collection loop** — the system surfaces the most informative fields to ground-truth as it's used, building local labels over time (the product pivot).
- **Ongoing monitoring as a running service** — we have written the *alert rules*, but nothing runs on a live feed.
- The **neighbour-controlled baseline** — comparing a field to comparable neighbours; needs neighbouring fields we don't have yet.
- The **confidence/decision framework** — designed and documented, but only instantiated on this one field.

All of §4 depends on having a **population of fields**, which we don't have yet (today = one demo parcel).

---

## 5. Crossing points to align on (nothing here is built — flagging the seams)

1. **Data contract / schema (§2).** Our pipeline is wired to the CSV columns + cube schema (`g15f.*`). If your side produces or transforms that data, this schema is our shared interface — who owns the schema of record?
2. **Ingestion / QA pipeline + the integrity gate.** Our preflight mirrors an ingestion-validation idea. If you own ingestion, our gate should match yours, not reinvent it.
3. **Field boundaries (AOI) + neighbour sets.** We *consume* parcel polygons and would need a "comparable neighbours" set; we don't produce these. Does your side?
4. **Feature store (proposed).** If/when we build §4, the per-field feature vectors need somewhere to live — is there already a store on your side, or do we define it?
5. **Label store + data-collection loop (proposed).** The active-learning pivot needs a place to put collected ground-truth labels and a human-in-the-loop step. Likely the biggest overlap if your part touches data collection.
6. **Output / product surface (proposed).** Do our decision cards / alerts feed a shared UI or API, or stay standalone?

---

## 6. Status table

| Item | Status |
|---|---|
| Phenology / crop cycles (one field) | **Built + validated** (HMM cross-check; r=0.94 vs raw pixels) |
| Multi-index, pixel-level, NDRE, MSAVI | **Built** (one field) |
| Decision card + methodology | **Built as documents** (one field; monitoring is a spec, not running) |
| Crop labels | **Confirmed by grower** for this field; no trained classifier |
| Multi-year stability / trend | **Provisional** — 2 years is a baseline, not a trend |
| Feature store, clustering, anomaly, active-learning, live monitoring | **Designed/discussed only — not built** (need many fields) |
| Neighbour baseline | **Not built** — needs neighbouring fields |
| Pest (Fall Armyworm) detection | **Out of reach** from satellite — needs drone + scouting |

---

## 7. What I'd want back from you

To return the favour: (a) what your part *is*, with inputs/outputs; (b) the schema(s) you own (so we align the data contract); (c) where you think our halves integrate; (d) the one or two decisions you're unsure about. I'll review it the same way — fresh eyes for collisions, duplicated work, and unstated assumptions at the seams.
