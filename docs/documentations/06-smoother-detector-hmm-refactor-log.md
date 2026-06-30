# Smoother, Detector, and HMM Cross-Check Refactor Log

Date started: 2026-06-30

## Purpose

This document tracks the technical work, evidence, and design decisions from the
smoother + activity-window-detector refactor and the HMM cross-check. It is
written as a normal long-form documentation log so it can later support the
graduation book (Chapters 6 — Satellite Data Pipeline & Methodology, 7 — Evidence
Modeling, and 9 — Case Study). It is **not** a repo activity log: branches, merge
details, and task mechanics belong in `docs/TASKS/`; durable research evidence
and design reasoning belong here.

Evidence is labeled as **measured**, **code-derived method**, **interpretation**,
or **recommendation** where useful.

---

## 1. Summary

The vegetation **smoother** and the activity-window **detector** were rebuilt, an
HMM cross-check was added, and the `outputs/` tree was reorganized. The smoother
moved from a per-point index-domain polynomial fit (mislabeled "Savitzky-Golay")
to a quality-weighted **Whittaker–Eilers** smoother on a regular **daily grid**
with a phenology-timescale smoothness parameter. The detector was rebuilt on that
daily curve using **peak/trough + asymmetric per-limb amplitude thresholds**,
slope confirmation, sub-peak merging, and crossing-reachability lifecycle. A
deterministic 4-state Gaussian **HMM** was added purely as an independent
cross-check. `scipy` became a base dependency.

The work was driven by T-11 (isolated-parcel evidence → pipeline improvement) and
an audit that found concrete defects in the mid-refactor code.

---

## 2. The audit — what was wrong (measured)

- **Smoother fit on observation index, not time** (code-derived). The production
  smoother fit a local cubic on the integer observation index rather than real
  days; on irregular cloud-gapped Sentinel-2 cadence this distorts the curve by
  up to ~0.06–0.12 NDVI where a window straddles a gap. It was published under the
  name `linear_fill_savitzky_golay`, which only holds on a uniform grid.
- **Dead second smoother with published parameters.** A gap-aware
  median/weighted-mean smoother was imported but never called; its parameters
  (`max_smoothing_gap_days`, `local_window_days`, `minimum_local_neighbors`) were
  still written into `quality_metrics.json`, describing a smoother that did not run.
- **Detector merged two real cycles across a temporal gap** (measured). Peak
  min-distance was computed as an *observation-index* count from the median
  cadence and passed to `find_peaks`, so two cycles ~60 days apart but close in
  index were merged. A repo test (`test_two_activity_windows_…`) failed.
- **Open-edge cycles mislabeled `complete`** (measured). Boundary peaks were
  consumed by the main loop before the open-edge handling, so partially-observed
  cycles were emitted as fully-observed. Two repo tests failed
  (`test_open_left/right_…`).
- **One constant overloaded three ways** and several dead constants
  (`STRONG_PROMINENCE_NOISE_RATIO`, `MAX_INACTIVE_BREAK_DAYS`), plus a redundant
  `crossing_date` field always equal to `start_date`.

Net: 3 of the repo's own detector tests were red on the working tree before the
rebuild.

---

## 3. New smoother — weighted Whittaker on a daily grid

**Method (code-derived).** `farmtrust_core/preprocess/analysis_curve.py`. Build a
daily grid from first→last observed date; place each observation with a weight
from `valid_fraction` (looser `>= 0.30` inclusion gate, clipped to `[0.1, 1.0]`),
0 on unobserved days. Solve the penalized least-squares system
`(W + lambda · DᵀD) z = W y` with a 2nd-order difference penalty `D` (banded SPD,
`scipy.linalg.solveh_banded`). The strict `valid_fraction >= 0.90` usable gate is
unchanged and still drives gap/evidence metrics.

**Choosing lambda — phenology timescale, not GCV (key finding).** Lambda is set
from a target smoothing timescale: `lambda = (T / 2·pi)^4`, so a ~45-day window
gives `lambda ≈ 2631` — an agronomic constant, not a per-AOI fit. Generalized
cross-validation was evaluated and **rejected as the default** because it
undersmooths daily-gridded NDVI:

| lambda | effective DoF (trace H) on `aoi_demo_01` | behavior |
|---:|---:|---|
| 1 | ~176 | GCV minimum — fits cloud dips & noise (undersmoothed) |
| 100 | ~64 | still too rough |
| 3000 | ~29 | domain-appropriate — recovers the real cycles |
| 100000 | ~13 | oversmoothed |

(measured on the real AOI). The timescale rule lands at `lambda ≈ 2631`
deterministically and is far more explainable ("we smooth vegetation over roughly
five weeks").

**Result (measured).** On `aoi_demo_01` the curve preserves the bare-soil floor
(min ≈ 0.17) while suppressing cloud dips, and `find_peaks` on it recovers the
**four** real crop cycles (peak day offsets 69 / 274 / 451 / 684), matching the
isolated Menofia analysis.

**Artifacts.** A new `season_analysis_curve.csv` (daily grid) is persisted next to
`ndvi_smoothed.csv`; the `*_smoothed` columns are the daily curve sampled at the
observation timestamps. `quality_metrics.json` smoothing keys now describe the
Whittaker (`weighted_whittaker_eilers_daily_grid`, `selected_lambda`,
`target_smoothing_days`, …).

---

## 4. New detector — peak/trough + asymmetric amplitude thresholds

**Method (code-derived).** `farmtrust_core/seasonal/seasons.py`, run on the daily
Whittaker curve.

- Peaks/troughs via `scipy.signal.find_peaks`, min peak separation in **real days**
  (fixes the merge bug).
- Per-cycle **per-limb** baselines and **asymmetric** thresholds: SOS at
  `baseline_left + ALPHA_START·amp` (`ALPHA_START = 0.20`, rising), EOS at
  `baseline_right + ALPHA_END·amp` (`ALPHA_END = 0.35`, falling — senescence reads
  at a higher fraction).
- **Slope-confirmation** gate (`SLOPE_CONFIRM_STEPS = 3`) rejects rain-flush false
  starts.
- **Sub-peak merging** (`CYCLE_SPLIT_AMPLITUDE_FRACTION = 0.50`): a trough splits a
  cycle only if it descends far enough toward bare soil; otherwise sub-peaks merge
  (a berseem multi-cut sawtooth stays **one** cycle — see the local-context lesson
  in `05-local-interpretation-context.md`).
- **Crossing-reachability lifecycle**: `complete` / `open_left` / `open_right` /
  `open_both` (fixes the open-edge mislabel). `is_open` is right-edge-only;
  `open_left` is surfaced via `lifecycle_status` + `provisional`.
- New additive fields: `season_calendar_label`, `greenup_rate`, `senescence_rate`,
  `integrated_ndvi`, `cycle_split_merged`, `daily_curve_lambda`. `crossing_date`
  removed. `season_id` sequenced across the combined confirmed+borderline list.

**Result (measured).** The 3 previously-failing detector tests pass. On
`aoi_demo_01` the detector reports 4 confirmed complete cycles (e.g. season_01:
summer cycle, peak NDVI 0.76, amplitude 0.58, integrated_ndvi 35.3).

---

## 5. HMM cross-check (research only — never production)

**Method (code-derived).** `outputs/tools/hmm_phenology.py` — a deterministic
4-state Gaussian HMM (LOW / RISING / HIGH / DECLINING on `[NDVI, slope]`,
Baum-Welch with fixed initialization, Viterbi decode). It runs on the same daily
curve and its cycles are compared to the production detector by
`outputs/tools/hmm_comparison.py`. It writes `outputs/diagnostics/<aoi>/hmm_cross_check.{json,md}`
and **never** alters `season_windows.json` or scoring.

**Result (measured).**

| AOI | detector cycles | HMM cycles | matched | mean \|SOS Δ\| | mean \|POS Δ\| | mean \|EOS Δ\| | lifecycle agreement |
|---|---:|---:|---:|---:|---:|---:|---:|
| `aoi_demo_01` | 4 | 4 | 4 | 2.75 d | 0.0 d | 9.5 d | 1.0 |
| `land-c925…` | 1 | 1 | 1 | 1.0 d | 0.0 d | 11.0 d | 1.0 |

Peak dates agree exactly; SOS within a few days; EOS runs ~10 days later under the
HMM than under the detector's 35%-amplitude EOS.

**Why it stays a cross-check (recommendation/interpretation).** The deterministic
detector is the production backbone for explainability (a lender-auditable
boundary rule), determinism without a learned fit, robustness on sparse/short
parcels (a 4-state HMM is under-determined on a single partial cycle), and the
T-11 provenance ladder (deterministic-pipeline-result vs research cross-check).
Two AOIs cannot prove generalization. The agreement is the *success criterion of
the cross-check*, not a reason to switch. **Open follow-up:** the consistent EOS
Δ ≈ +10 d is a real question about where "end of season" should sit.

---

## 6. Validation

- `uv run pytest` (relevant suites): the analysis-curve, activity-window, HMM
  cross-check, real-AOI invariant, and evidence-gate suites pass (53 passing in the
  combined run); the 3 previously-failing detector tests pass.
- Real-AOI invariant tests assert plausibility, not golden values (no golden-file
  regression, per T-11): cycle-count plausibility, no false abandonment, monotonic
  boundaries, correct lifecycle, determinism, bare-soil troughs preserved, lambda
  in-bounds. Run on both AOIs.
- Determinism: no RNG in production or in the HMM library (only in tests); identical
  output across repeated runs.
- A NaN bug was found and fixed during this work: the CSV-loaded analysis curve
  set `daily_curve_lambda = NaN`; it now recovers the deterministic timescale
  lambda (production was already correct).

---

## 7. outputs/ reorganization

`data/` holds production pipeline artifacts only. `outputs/` is non-production:

- `outputs/exploration/` — the original isolated one-parcel (Menofia) analysis.
- `outputs/tools/` — diagnostic code: `hmm_phenology.py`, `hmm_comparison.py`,
  `season_detector_comparison.py`, `visualize_pipeline_outputs.py`.
- `outputs/diagnostics/<aoi>/` — generated diagnostics (`pipeline_visualization.html`,
  `hmm_cross_check.{json,md}`).

`farmtrust_core/` and the production `scripts/` import none of `outputs/`.

---

## 8. Figures & artifacts (with provenance levels)

Provenance ladder (from T-11): L3 = rerunnable artifact (committed script + inputs
+ params + output); L4 = pipeline artifact with stable contract. L3+ may be shipped
in the book; core scoring/status targets L4.

| Artifact | Provenance | Use for the book |
|---|---|---|
| `outputs/diagnostics/<aoi>/pipeline_visualization.html` (raw + interpolation + Whittaker curve + cycles + HMM band) | L3 (rerunnable via `outputs/tools/visualize_pipeline_outputs.py`) | Methodology + case-study visual (interactive; export a static frame at write time) |
| `outputs/diagnostics/<aoi>/hmm_cross_check.{json,md}` | L3 (rerunnable) | Cross-check evidence table (Ch 7/9) |
| `season_analysis_curve.csv` (daily Whittaker curve) | L4 (pipeline artifact) | Smoother methodology (Ch 6) |
| GCV-vs-timescale table (§3) | measured, reproducible from `analysis_curve.py` | Smoother methodology — justify lambda choice (Ch 6) |
| HMM agreement table (§5) | measured | Evaluation (Ch 9) |
| `outputs/exploration/figs/f1_timeline.png`, `f3_veg.png`, `f14_hmm.png`, `msavi_vs_ndvi.png`, … | L2–3 (isolated analysis) | Case study with caveats (Ch 9); promote to L3 before shipping |

**Note (recommendation):** the pipeline visualization is interactive HTML. Static
book-ready PNGs (raw + Whittaker curve + cycles; HMM-vs-detector; old-vs-new
smoother) are **deferred** to when the chapter is written, to keep this pass focused.

---

## 9. Book-chapter mapping

- **Ch 6 — Satellite Data Pipeline & Methodology:** the Whittaker smoother (§3), the
  GCV-vs-timescale justification, `season_analysis_curve.csv`.
- **Ch 7 — Evidence Modeling & Land Assessment:** the detector algorithm (§4), the
  HMM cross-check as independent validation (§5).
- **Ch 9 — Case Study, Results & Evaluation:** the 4-cycle Menofia result, the HMM
  agreement tables, the pipeline visualization, and the local-context caveats from
  `05-local-interpretation-context.md`.

---

## 10. Open questions / future work

- **EOS threshold:** HMM's senescence end runs ~10 days later than the detector's
  35%-amplitude EOS — decide where "end of season" should sit.
- **HMM as a confidence signal (not a detector):** feed HMM agreement into the
  detector's confidence (raise when HMM confirms a cycle, flag when it disagrees)
  without it owning the boundaries.
- **Envelope reweighting** in the Whittaker is implemented but default-off; enable
  only if multi-AOI validation shows residual cloud dips.
- **Multi-AOI validation:** two parcels cannot calibrate global thresholds; widen
  the validation set before any threshold tuning.
- **Static figures:** generate book-ready PNGs at chapter-writing time.

---

## 11. Evidence packet — the report correctness layer (2026-06-30)

After the smoother/detector rewrite, the next layer (T-11 Decision Point 9) was the
**report evidence packet**: a single grounded artifact that turns the separate
deterministic outputs (land assessment, activity cycles, indicators, confidence,
absence gate) into the lender-readable `Observed → Interpreted → Confidence → Watch`
structure the project had only ever shown in a hand-built HTML mock-up
(`outputs/exploration/lender_land_use_card.html`).

- **What it is:** `farmtrust_core/report/evidence_packet.py` builds
  `data/assessment/<aoi>/report_evidence_packet.json` as a deterministic projection
  over the four upstream artifacts — it computes no new numbers and embeds no
  wall-clock, so the same inputs give a byte-identical packet.
- **Shape:** a cautious `headline`, a typed `claims[]` list grouped into the four
  layers, an `activity_record`, a `track_record` gauge (seasons toward a certifiable
  trend), a `risk_register` that separates **land risks** from **evidence
  limitations**, fixed `boundaries` ("what this does NOT tell you"), and cautious
  pass-through `indicators`.
- **Claim discipline made mechanical:** because the builder is template-driven it
  *cannot* name a crop or assert yield — those terms exist only inside the fixed
  boundary-exclusion list. A test guards this with a word-boundary scan for crop
  tokens across the whole packet.
- **Provenance, deliberately staged:** per-claim metadata is lightweight here
  (`layer` + `confidence` + `rests_on`); the full provenance schema that the bounded
  assistant needs is deferred to T-04 so the packet schema settles first.

**Book-chapter mapping:** this belongs in **Ch 7 — Evidence Modeling & Land
Assessment** as the bridge between the deterministic pipeline outputs and the
lender-facing report — the point where measured signal becomes a structured,
confidence-aware, claim-disciplined narrative. The packet JSON is a clean figure
source (a labelled four-layer diagram) for that chapter.
