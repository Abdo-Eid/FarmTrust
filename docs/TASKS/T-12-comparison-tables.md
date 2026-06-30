# FarmTrust — Comparison Tables Reference

*Companion reference for the graduation book. A **distilled** set focused on the scientific and modeling decisions — index choices, season-detection and smoothing work, agronomic interpretation lessons, and the crop/yield machine-learning exploration. The low-level data-ingestion and storage comparisons have been set aside. **Each table is a single, like-for-like comparison** (the same options measured on the same columns); related tables share a section heading but are never merged unless they truly fit one table. Numbers are quoted verbatim from the project's research logs under `docs/documentations/` (the source of record — regenerable from there if a cut comparison is ever needed); figures live in `T-12-figure-manifest.md`. Single-parcel / single-dataset results are reported honestly as such, not as universal validation.*

**Caveat on scope.** Many of the strongest-looking numbers are single-parcel, single-AOI, or single-dataset results: the crop-classification AOI checks rest on one or two known parcels, the yield-transfer experiments are validated against one farmer's remembered harvest, and the season-detection cross-checks run on two parcels. They are evidence for direction and for the discipline of the system, not universal validation.

---

## Dataset & research framing

### Multi-country yield dataset — coverage

| Country | Fields | Years (crops) |
|---|---|---|
| Argentina | 751 | 2017–2024 (soybean, corn, wheat) |
| Brazil | 551 | 2017–2024 (soybean, corn, wheat) |
| Germany | 299 | 2016–2022 (wheat, rapeseed) |
| Uruguay | 572 | 2018–2022 (soybean) |
| **Total** | **2,173** | 4 crops, 2016–2024 |

**What we observed:** Coverage spans four countries with different crop mixes, and crop is partly entangled with country — Germany contributes wheat only, and corn appears only in Argentina and Brazil.
**What we did and why:** We combined the countries into one multi-country, multi-year dataset to test cross-domain generalisation, and flagged the crop–country coupling as a known structural risk so a domain shortcut would not be mistaken for true new-region skill.

### Two research streams

| Aspect | Field-level crop-mapping stream | Morocco AOI-validation stream |
|---|---|---|
| Input | seasonal field sequence, 20 timesteps | static mean AOI / field features |
| Focus | temporal sequence modelling | inference validation against a known AOI |
| AOI evidence | none reported | direct, but low confidence |
| Status | research-only | research-only |

**What we observed:** The two streams use different feature contracts and label sets, so their metrics are not directly comparable, and strong internal metrics do not by themselves prove AOI behaviour.
**What we did and why:** We treated both as research-only and used the AOI-validation stream as the more honest deployment test, even though its confidence was low.

---

## Vegetation-index decisions

### Which index, for what

| Index / signal | What it adds | What it cannot show | How we use it |
|---|---|---|---|
| NDRE (red-edge) | dense-canopy headroom / vigour where NDVI saturates | hidden pest damage — tracked NDVI almost exactly (r = 0.99, 20 m) and did not reveal Fall Armyworm | headroom/context only; never a pest or yield detector |
| NDVI / NDRE greenness | canopy greenness | actual yield or pest status — damaged corn can still look like a clean canopy | never claim pest, yield, or income; prefer "no canopy collapse" over "healthy" |
| NDMI (moisture) | relative moisture / stress watch | a failure verdict — summer corn naturally reads lower (higher water demand) | relative stress watch paired with timing/irrigation context |
| MNDWI (water) | surface-water signal | reliable absolute water — a canopy-dominated median skews a relative comparison | cautious surface-water signal only; no rice/flood claim without strong evidence |

**What we observed:** The naive hopes for these indices did not hold — red-edge tracked NDVI almost exactly (r = 0.99), greenness is not yield or pest status, and the water/moisture signals are easily misread.
**What we did and why:** We use each index only for the signal it can honestly carry and built guardrails so the system never converts greenness or moisture into yield, pest, or failure claims.

---

## Season detection & smoothing decisions

### Smoothness (λ) selection — the sweep

| Smoothness λ | Effective degrees of freedom | Read |
|---|---|---|
| λ = 1 (cross-validation minimum) | ~176 | undersmoothed |
| λ = 100 | ~64 | still too rough |
| λ = 3000 | ~29 | domain-appropriate (recovers real cycles) |
| λ = 100000 | ~13 | oversmoothed |
| phenology-timescale rule (~45-day window) | **λ ≈ 2631** | chosen |

**What we observed:** The cross-validation minimum (λ = 1) undersmoothed and chased noise; the agronomically right amount of smoothing sat near λ ≈ 3000.
**What we did and why:** We set λ from a ~45-day phenology timescale (≈ 2631) — "we smooth vegetation over roughly five weeks" is an explainable constant, not a per-AOI fit.

### Smoother & detector design decisions

| Decision | Options weighed | What we chose | Evidence / why |
|---|---|---|---|
| Smoother design | old index-domain polynomial vs quality-weighted daily-grid smoother | quality-weighted daily-grid | old fit distorts the curve up to ~0.06–0.12 NDVI across a gap; new preserves the bare-soil floor (min ≈ 0.17) and recovers four cycles (peak-day offsets 69 / 274 / 451 / 684) |
| Smoothing strength | strong vs trough/transition-preserving | trough-preserving | over-strong smoothing erased a real between-crop bare-soil trough and mis-dated corn green-up |
| Per-limb amplitude thresholds | one symmetric threshold vs asymmetric per-limb | asymmetric per-limb | rising limb = baseline + 0.20 × amplitude; falling limb = baseline + 0.35 × amplitude (senescence reads higher) |
| Sub-peak merging | split at the trough vs merge sub-peaks | merge shallow sub-peaks | split only when the trough descends ≥ 0.50 of amplitude; else a multi-cut sawtooth becomes one cycle, not many false cycles |
| Edge / open cycles | original record vs extended record | preserve open-left/right/incomplete | extending the record recovered a genuine summer 2024 cycle that looked unreal without an observed start/end |

**What we observed:** A naive smoother-and-detector chain failed in characteristic ways — distorting curves across gaps, erasing real troughs, misplacing edges, and over-splitting multi-cut sawtooths; three of our own detector tests were red.
**What we did and why:** We rebuilt around the choices above; afterwards all detector tests pass (3 red before → 53 passing after the rebuild), fixing a cross-gap cycle-merge bug and open-edge mislabeling.

### Deterministic detector vs HMM cross-check

| Agreement metric | Demo AOI parcel | Second land parcel |
|---|---|---|
| detector cycles | 4 | 1 |
| HMM cycles | 4 | 1 |
| matched cycles | 4 | 1 |
| mean \|start-of-season Δ\| | 2.75 d | 1.0 d |
| mean \|peak Δ\| | 0.0 d | 0.0 d |
| mean \|end-of-season Δ\| | 9.5 d | 11.0 d |
| lifecycle agreement | 1.0 | 1.0 |

**What we observed:** The deterministic detector and an independent four-state HMM agree exactly on cycle count and peak dates across both parcels.
**What we did and why:** We keep the deterministic detector as the production backbone and the HMM as a research-only cross-check (it never alters windows or scoring); two AOIs cannot prove generalisation, so we report it as a cross-check, not validation.

---

## Agronomic interpretation lessons

### Naive satellite reading vs ground truth

| Naive reading | Local / ground-truth correction | How we use it |
|---|---|---|
| Late wheat green-up means a problem | a beans-before-wheat rotation can delay green-up by about one month | don't penalise late green-up without rotation context |
| A wide mean-vs-p95 gap means stand failure | mixed winter management (wheat + berseem, or staggered cutting) also widens it | use the spread as patchiness evidence only; require user notes for the exact explanation |
| Repeated winter NDVI dips mean failure/stress | berseem cut-and-regrowth — fodder cut repeatedly, then regrows | treat repeated winter dips as possible cut/regrowth, never damage without corroboration |
| Moving winter NDVI bands mean a static boundary or sensor noise | a moving fodder cutting front — freshly cut strips drop, then regrow | consider progressive cutting before declaring a crop split or artifact |
| Pixel maps can be read directly | on a ~6 × 18 pixel parcel at 10 m, over-reading drove an early wrong interpretation that user feedback corrected | start from numeric spatial evidence; use static maps only when useful and clearly caveated |
| Shape and timing can prove the exact crop | they only narrow possibilities; user notes / ground truth / labelled models confirm identity | phrase as "consistent with" / "calendar-aligned" / "user-declared", not automatic detection |
| The delivered field-mean series might be unreliable | recomputed raw-pixel NDVI matched it at r = 0.94 | keep the field-mean time series as the robust backbone; pixel evidence is supporting context |

**What we observed:** Repeatedly, the "obvious" satellite reading was wrong on the ground — late green-up was a bean rotation, wide spread and winter dips were normal fodder management, and tiny-parcel pixel maps invited over-reading the field means already captured (r = 0.94).
**What we did and why:** We let local knowledge and ground truth override the naive reading, leaning on the robust field-mean series and treating pixel maps and crop identity as caveated, never as standalone proof.

---

## Crop & yield ML exploration — outcomes & validation

### Crop classifier — direct AOI prediction across seasons

| Parcel (truth) | Class probabilities | Outcome |
|---|---|---|
| C1 (corn) | alfalfa 0.000153 / corn 0.999847 | correct, high confidence |
| C3 (corn) | alfalfa 0.008052 / corn 0.991948 | correct, high confidence |
| C4 (alfalfa) | alfalfa 0.568402 / corn 0.431598 | correct, only moderate |

**What we observed:** The Morocco-only binary model called all three AOI parcels correctly, but the alfalfa parcel only moderately.
**What we did and why:** We treat this as single-AOI evidence of direction, not production validation.

### Feature-set ablation (three runs × two models)

| Run | XGBoost macro-F1 | CatBoost macro-F1 |
|---|---|---|
| Full (production-accessible) | 0.9884342211460856 | 0.9771205181159838 |
| No weather | 0.9067736353625925 | 0.8947039897039897 |
| Sentinel-2 / scene-classification only | 0.9146175345060715 | 0.8792108041827037 |

**What we observed:** Weather is the largest single booster, but optical imagery alone still holds at ~0.91 macro-F1.
**What we did and why:** We backed an imagery-first baseline with weather as a tested optional enhancement.

### In-distribution vs out-of-zone generalization

| Validation split | Macro-F1 | Note |
|---|---|---|
| Random stratified | 0.7929820237919876 | train/test parcels 6187 / 1547 |
| Leave-one-zone-out — el haouz (best) | 0.580155 | |
| Leave-one-zone-out — Gharb (worst) | 0.188885 | collapses out-of-zone |

**What we observed:** A random split (0.79) badly overstates skill; held out by zone, performance collapses (0.19 on Gharb).
**What we did and why:** We read the evidence as a same-distribution Morocco baseline, not a robust unseen-zone classifier — a geography-leakage lesson.

### The four crop-model attempts

| Attempt | Result | Verdict |
|---|---|---|
| Morocco-only binary LightGBM | passed the C1/C3 corn and C4 alfalfa AOI check | the one narrow path that solved the demo |
| Morocco-only XGBoost | correct corn prediction, low confidence | usable only as weak evidence |
| Full merged five-label model | blocked (missing artifact and bands) | not runnable on the AOI |
| AOI-compatible five-label model | wrong wheat prediction | schema-compatible but not separable |

**What we observed:** Only a narrow, AOI-compatible boundary solved the demo check; schema compatibility alone did not guarantee crop separability.
**What we did and why:** We kept the passing result as a single-AOI demo, not production validation, and did not ship a crop classifier.

### Yield transfer — predictions vs the farmer's observed range

| Variant | Predicted yield |
|---|---|
| Imagery-only baseline | ~1113.2 kg |
| Timing-robust first pass | ~1084.8 kg |
| Compact-soil variant | ~1021.9 kg |
| No-raw-band timing-robust | ~1014.8 kg |
| Direct-valid-pixel-free no-raw-band | ~1032.3 kg |
| PLSRegression appendix | ~1065.7 kg |
| **Farmer's observed** | **~600–800 kg** (plot ~1277.8 m² / 0.1278 ha / 0.304 feddan) |

**What we observed:** Every variant overpredicts against the farmer's remembered 600–800 kg (the no-raw-band pass at ~1014.8 kg is the lowest).
**What we did and why:** We report this as a real cross-region transfer gap, not a tuning failure — and did not ship a yield model.
