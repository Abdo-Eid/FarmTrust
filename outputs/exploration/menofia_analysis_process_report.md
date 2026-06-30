# Menofia NDVI Analysis — Process Report & Post-Mortem

**Parcel:** one field, Menofia governorate, Nile Delta, Egypt (Sentinel-2 MGRS tiles 36RTU / 36RUU)
**Input:** `indices_timeseries.csv` — 2 years of field-mean satellite indices (21 Jun 2024 → 19 Jun 2026)
**Deliverable:** `menofia_ndvi_report.html` (self-contained), built by `analyze.py` + `report_template.html`
**Date written:** 23 June 2026

This document records two things you asked for: **how the analysis was actually built and how it reached its conclusions**, and — just as important — **the mistakes I made along the way, why I made them, and how each was fixed.** It is written so you (or anyone) could reproduce the work or audit the reasoning.

---

## 1. The objective

Read two years of NDVI (and related indices) for a single Delta parcel and pull out everything defensible: how many crops per year, when each was planted and harvested, how vigorous it was, how uniform the field is, where stress shows up — and whether planting seasons can be detected from the satellite signal alone. A secondary goal that emerged: connect what the satellite sees to what you know happened on the ground.

---

## 2. The data I was given

The CSV was already in the ideal shape for this work: **field-mean values per acquisition date**, not raw pixels. That one fact removed most of the noise problems before they started.

| Property | Value |
|---|---|
| Rows (acquisitions) | 280 (was 262; start extended to 2 May 2024) |
| Date range | 02 May 2024 → 19 Jun 2026 (778 days) |
| Observations per year | 2024: 65 · 2025: 142 · 2026: 55 |
| Median gap between scenes | ~2 days (Sentinel-2 A+B, two overlapping tiles) |
| Indices present | NDVI, EVI, NDMI, NDWI, MNDWI — each as `mean` and `p95` |
| Quality columns | `valid_fraction`, `min_cloud_cover` |
| Sensor | Sentinel-2 L2A (surface reflectance), 10 m |

Quality reality: `valid_fraction` averaged 0.88, but **30 rows had no usable NDVI** (fully clouded) and 33 rows were below 0.8. That had to be handled before any smoothing.

---

## 3. How the analysis was built (the pipeline)

The whole thing is one linear pipeline. Each stage feeds the next, and the same pipeline would scale to more fields or more years without rework.

### 3.1 Quality control
- Dropped rows with no NDVI (cloud).
- Kept rows with `valid_fraction ≥ 0.5`.
- Collapsed any duplicate dates.
- Result: **262 raw → 231 clean observations.**

### 3.2 Regular daily grid + weighted Whittaker smoother
Satellite series are irregular and gappy (clouds delete dates), so they can't be analysed directly. I put every index on a **daily grid** and reconstructed it with a **weighted Whittaker smoother** (λ = 6000, second-order differences):

- Observed dates get their value with a **weight equal to their `valid_fraction`** (clearer scenes count more); gap days get weight 0.
- The smoother **gap-fills and denoises in a single pass** — it is the one step that does both.
- Implemented with a plain NumPy dense solve (728×728) because SciPy would not finish installing in the sandbox in time; the math is identical.

This is the backbone of every chart and every number downstream.

### 3.3 Multi-peak phenology detection
Critically, I did **not** fit a single-season model (the common mistake when people port temperate-crop methods to the Delta). This field carries **two crops a year**, so the detector must find multiple peaks:

- Find peaks on the smoothed NDVI (min height 0.40, min prominence 0.18, min spacing 55 days).
- Find the troughs between them (prominence 0.08).
- For each crop cycle, bounded by its flanking troughs:
  - **POS** (peak of season) = the peak date.
  - **Baseline** = the lower of the two trough values (bare-soil floor).
  - **SOS / EOS** (start / harvest) = where NDVI crosses **20 % of that cycle's amplitude** on the way up / down. Using a per-cycle amplitude threshold (not one fixed NDVI value) is what makes it robust when a winter crop and a summer crop have different shapes.
  - **Greenness integral** = area under the curve above baseline — a biomass / yield proxy.
- **Edge handling:** explicit logic for crops that are only partly inside the record (the summer-2024 crop was already standing when the data begins).

### 3.4 Crop labelling
First from the Delta cropping calendar (winter = wheat/berseem, summer = corn), then — once you provided them — replaced with your **confirmed field notes**. The curve shapes were used as independent corroboration.

### 3.5 Reporting
Six matplotlib charts saved as PNG, then embedded into a directly-authored HTML template. (See §6 — this part is where I had to change my approach.)

---

## 4. What the analysis found (final, corrected result)

| Cycle | Season | Crop (your notes) | Green-up (SOS) | Peak (POS) | Harvest (EOS) | Days | Peak NDVI | Field-gap |
|---|---|---|---|---|---|---|---|---|
| C1 | Summer | corn | 18 May 2024 | 10 Jul 2024 | 30 Aug 2024 | 104 | 0.76 | 0.08 |
| C2 | Winter | wheat + berseem (½ / ½) | 08 Oct 2024 | 01 Feb 2025 | 02 May 2025 | 206 | 0.88 | **0.13** |
| C3 | Summer | corn (unsprayed) | 15 Jun 2025 | 28 Jul 2025 | 11 Sep 2025 | 88 | 0.81 | 0.04 |
| C4 | Winter | berseem (clover) | 05 Oct 2025 | 17 Mar 2026 | 31 May 2026 | 238 | 0.87 | 0.04 |

*(Updated after you extended the start to 2 May 2024 — corn 2024 is now a fully-bracketed cycle with its own green-up, no longer "partial". See §16.)*

**Cropping intensity ≈ 2.0 cycles/year** — confirmed double-crop. Headline reads, each tied to its evidence:

- **The half/half winter field showed up in the data** as the widest field-average-vs-greenest-pixel gap in the record (0.13) — two crops establishing at different speeds, not a failure.
- **The berseem-only year was readable from shape alone**: it peaked ~37 days later, ran ~36 days longer, and had the flat multi-cut plateau clover gives.
- **Last year's corn shows no Fall Armyworm fingerprint in NDVI** — and that is a limitation of the index, not a contradiction of your experience (see §5.4).
- **No rice, ever** — MNDWI never exceeds −0.30, nowhere near standing water.

---

## 5. What I fell into, and why (the honest part)

I made four real mistakes. None of them survived into the final report, but you deserve to know what they were and what caused them.

### 5.1 Scope drift — I built a rice detector for a field that has never grown rice
**What happened:** In the first version I added logic to flag "flooded rice transplanting" from the water indices, and built a whole chart and report section around it.
**Why:** I reached for an impressive Delta-specific feature (rice *is* common in the Delta) instead of staying with what your data and your situation actually called for. You named it exactly: *"you are drifting too much."*
**Root cause:** Adding capability you didn't ask for, on a hypothesis I never checked against the data first.
**Fix:** Removed it entirely. Then I checked the data properly and it agreed with you — MNDWI never approaches open-water values — so "no rice" became a one-line confirmation instead of a feature.
**Lesson:** Anchor on the grower's reality and the data in front of me before adding clever detectors.

### 5.2 A mis-calibrated threshold made the rice flag fire on *every* cycle
**What happened:** The flood detector returned `True` for all four cycles — obviously wrong.
**Why:** I compared the water index at each crop's establishment against the **whole-series median**. But that median is dominated by dense-canopy values (very negative MNDWI), so *every* green-up — when the field is briefly bare/wet — looked "wetter than usual." The test was **relative when it needed to be absolute** (real standing water sits near 0; this field never gets there).
**Root cause:** Wrong reference baseline — a classic, easy-to-miss statistical error.
**Fix:** The feature was deleted, so the bug went with it. The general lesson stuck: a "wetter than average" signal is not the same as "standing water."

### 5.3 The first run missed a whole crop and under-counted the rotation
**What happened:** Version 1 found only 3 cycles (intensity 1.5/yr) and missed the summer-2024 corn entirely.
**Why:** That corn crop was already standing when the record begins, so its left side is censored. Peak detection ranks peaks by **prominence** (height above the surrounding valleys); with no valley visible on the truncated side, its prominence computed as tiny (~0.03) and it was filtered out.
**Root cause:** Standard peak detection has a blind spot at the edges of a record.
**Fix:** Added explicit **edge-cycle handling** — if the series starts high and descends to a trough, register a *partial* cycle. That recovered the summer-2024 corn and corrected the intensity to the right ~2.0/year.

### 5.4 I had to actively resist over-claiming on Fall Armyworm
**What happened:** When you said last year's corn was badly hit, the tempting move was to "find" the damage in the data.
**Why it would have been wrong:** I went back and looked — last year's corn reads as a clean, uniform canopy peaking 0.80 (within-field gap ~0.04). The damage is **not** in the NDVI, for solid reasons: at 10 m resolution patchy whorl damage averages out; NDVI saturates near 0.8 so it can't separate healthy from moderately chewed; and FAW hits **yield and ears**, not canopy greenness.
**What I did:** Said so plainly, and pointed to what *would* help next time (a red-edge index like NDRE, watched through the whorl window, plus traps and scouting as the real front line).
**Lesson:** When the data can't support a claim the user would *like* to be true, saying so is the useful answer.

### 5.5 The build mistake: I jammed the whole HTML report into one Python string
**What happened:** The report generator crashed with `unterminated triple-quoted string literal`.
**Why:** I was constructing the entire HTML page — CSS braces, HTML quotes, and Python's own `{ }` expressions — inside a single giant Python f-string. Python and HTML/CSS were competing for the same `{`, `}`, and `"` characters, and eventually a combination broke the parser.
**Root cause:** Mixing two concerns (computation and presentation) in one brittle construct. You caught this directly: *"why not making it directly?"*
**Fix:** Separated them. `analyze.py` now does **only** the math and the charts. The page layout lives in `report_template.html`, authored as a normal HTML file (where braces and quotes are just text). The script fills in a handful of `@@TOKEN@@` slots with plain text replacement — no escaping conflicts possible. The bug class is gone, and both files are now simple to read.

---

## 6. What went right (so the post-mortem is balanced)

- **Field-mean over pixels** (your CSV did this) — killed most noise up front.
- **Weighted Whittaker** — gap-fills and denoises together, weighting by scene quality.
- **Multi-peak, not single-season** — the one decision that makes Delta phenology work at all.
- **Visual verification at every step** — I read the actual chart images, which is how the missed crop, the mis-firing flood flag, and the year-to-year shift were all caught. Looking beat trusting the numbers.
- **Honesty over impressiveness** on the FAW question.

---

## 7. How the work evolved (timeline)

1. **Advice first** — recommended a single pipeline (Sentinel-2 → field-mean → composite/smooth → phenology) before touching data.
2. **v1 build** — profiled the CSV, built smoother + phenology, generated a report. *Contained the rice over-reach and the missed crop.*
3. **Your correction** ("no rice; we grow berseem/wheat/corn; you're drifting") — removed rice logic, added edge handling, fixed labels, re-verified against the charts. Cycle count corrected to 4 (~2/yr).
4. **Visual pass** (at your prompt) — pulled three findings only visible in the images: the winter peak shifting ~5 weeks later year-on-year, the patchy 2024/25 establishment, and lower summer canopy moisture.
5. **Your ground truth** (half/half wheat-berseem; berseem-only; planting corn now; FAW last year) — turned inferred labels into confirmed ones, explained the patchy gap as the split field (later refined — the within-field winter signal is the berseem *cutting sweep*, see §11), and wrote the honest corn/FAW section.
6. **Architecture fix** — split the HTML out of the Python string after the f-string crash.

---

## 8. Honest limitations

- **Planting dates are estimates** (green-up minus ~1–3 weeks), not measured sowing dates.
- **Wheat vs berseem** is inferred from timing/shape; your notes are the ground truth, not the satellite.
- **NDVI cannot see Fall Armyworm** at this resolution — do not rely on it for pest detection.
- **The trailing edge is partial** (2026 corn is just starting); with the start extended to May 2024, summer-2024 corn is now fully bracketed (§16).
- Everything here points you to *where and when to look* — it does not replace walking the field.

---

## 9. Files produced

| File | Role |
|---|---|
| `menofia_ndvi_report.html` | The report — open this. Self-contained, six charts, cycle table, causal insights. |
| `report_template.html` | The page layout, authored directly as HTML (the clean approach). |
| `analyze.py` | Computation + charts only. Reusable on any parcel CSV in the same format. |
| `figs/` | The six chart PNGs. |
| `menofia_analysis_process_report.md` | This document. |

---

## 10. Suggested next step

*(Update — done: the red-edge bands were added to the cube and NDRE was computed and tested. See §15 for the result.)*

Since corn is going in now and Fall Armyworm is the live concern, the highest-value follow-up is **not** another NDVI chart — it is tracking this 2026 corn with a **red-edge (NDRE) index** through the whorl/vegetative window (mid-June to late July), flagging any deviation from a healthy-year track, as a "go scout the field" nudge. That requires a live Sentinel-2 feed for the parcel; wiring it to whatever produced this CSV is the natural extension of the pipeline already built here.

---

## 11. Going deeper — the raw Sentinel-2 cube (added after delivery)

You then opened access to the raw cube (`cube.zarr`, a Zarr v3 store of 10 m pixels) plus `run_metadata.json` and `scenes_index.jsonl`. I decoded the cube **directly — no `zarr` or `xarray`, just NumPy and the `zstd` command-line tool** — because those libraries would not install in the sandbox. The cube is a 6 × 18 pixel grid (~60 × 180 m), 262 dates, bands B02/B03/B04/B08/B11 + SCL, raw digital numbers with the `boa_baseline_04_00` offset. Three findings:

**(1) Validation — the delivered CSV is faithful.** Recomputing NDVI from the raw bands (applying the −1000 reflectance offset and SCL masking) and averaging over the field reproduces the delivered `ndvi_mean` with **r = 0.94 and near-zero bias across 232 dates**. Every conclusion in the report therefore rests on data that matches the underlying pixels.

**(2) The within-field winter pattern is your berseem cutting, caught in motion.** Averaged over two years the field is uniform, but within a winter the berseem area shows strong *moving* structure: consecutive cloud-free scenes show a freshly-cut strip (low NDVI) appear in one part of the field, regrow over ~3 weeks, while a new strip is cut elsewhere — the alternating, advancing fodder harvest you described, with the central walkway (mamsha) faintly visible down the middle. This is the **cutting pattern, not a clean wheat/berseem boundary**: that block split is *not* spatially resolvable in a 6 × 18 image (you confirmed this). In **summer 2025 corn** the structure vanishes — one uniform crop — which proves the winter pattern is real field management, not sensor noise. *(Correction: I first read this diagonal as a static wheat-vs-berseem split at ~40/60 by pixel. That was wrong — it is the moving cut-front; your feedback fixed it. The figure now shows the cut-front migrating over five weeks.)*

**(3) Berseem cutting log.** Each fodder cut drops NDVI then regrows. The field-mean resolves ~2 synchronized early cuts (Nov–Jan) then plateaus as cutting staggers across the field; **per-pixel the median is ~5 cuts** for the 2025/26 berseem (recomputed on the clean, full cube — the earlier ~3 came from the stale mount; see §16). That lands right in the 4–6 a Miskawi berseem really takes. Still a floor, since NDVI saturation and the 5-day revisit miss the shortest regrowth. (You confirmed berseem here is cut for animal feed — which is exactly why the variability signal works as a discriminator.)

## 12. Reading the data like the full pipeline (remote sensing → analyst → agronomist)

This is the interpretation layer you asked for: what I *observed* in the numbers and images, and what I *interpret* from it — passed through the three roles, because a raw number means nothing to a farmer until it is translated.

- **Observed:** NDVI rises and falls twice a year, flooring near 0.18 between. → *Remote sensing:* two distinct canopy cycles separated by bare soil. → *Analyst:* cropping intensity ≈ 2.0 / year. → **Interpretation (agronomist):** a classic Delta winter→summer double-crop; the land is almost never idle.

- **Observed:** the 2025/26 winter peak fell in March, ~37 days later than 2024/25's February peak, over a longer, flatter plateau. → *Remote sensing:* later, broader green season. → *Analyst:* +37 d phase shift, +36 d duration, flatter profile. → **Interpretation:** a crop/management change — a single-hump cereal (wheat) gave way to a multi-cut forage (berseem). You confirmed it.

- **Observed:** in winter 2024/25 the greenest pixels ran ~0.13 NDVI above the field average during establishment, with a diagonal high-variability band in the pixel maps. → *Remote sensing:* spatial heterogeneity in one season only. → *Analyst:* within-field spread peaks in winter, collapses in summer. → **Interpretation:** two crops sharing one field — half wheat, half berseem — not a stand failure.

- **Observed:** summer corn peaked at only 0.80 with NDMI sitting low. → *Remote sensing:* moderate canopy, drier than winter. → *Analyst:* peak below the 0.87 winter ceiling; NDVI–NDMI gap widest in summer. → **Interpretation:** corn under Delta-summer water demand — watch NDMI for irrigation stress. (This does **not** reveal the Fall Armyworm damage; NDVI can't — see §5.4.)

- **Observed:** MNDWI never rises above −0.30. → *Remote sensing:* no open-water signal, ever. → *Analyst:* water index bounded well below flooding values. → **Interpretation:** no rice / flooding on this parcel — exactly as you said.

The reason for stacking the three roles: "σ = 0.15 in the winter zone" is meaningless to a grower; the chain turns it into "the berseem half is being cut for fodder." That translation *is* the product.

---

## 13. What scales to the whole village, what is per-field, and what is unique to your land

The same pipeline runs at three very different scales. Knowing which insight belongs at which scale is what keeps the product honest: some things are reliable across thousands of fields at once, some need a field boundary, and some only exist because of ground truth like yours.

### A. Village-scale — compute once over every field, read as aggregates

Run the identical extract → smooth → phenology pipeline over a grid (or a field-boundary layer) covering the whole village, then summarise. These are robust *because* they average over many parcels:

- **Cropping calendar of the village** — the distribution of green-up / peak / harvest dates across all fields → "winter sowing runs late-Sept to late-Oct; summer corn goes in May–June." A planning and canal-scheduling product.
- **Cropping-intensity map** — cycles per year per field → who double-crops, who leaves land fallow.
- **Crop-mix proportions** — from curve shape (single hump = cereal/wheat, saw-tooth = forage/berseem, short summer hump = corn) → "~X % of the winter area is berseem vs wheat." A fodder-vs-grain balance for the cooperative.
- **Year-over-year shift** — is the *whole village* greening up earlier or later (climate, water scheduling)?
- **Productivity & anomaly screening** — greenness-integral totals and trends; fields far below their neighbours flagged for a visit. The extension / insurance / early-warning layer.
- **Water-stress hotspots** — NDMI anomalies across the village during a heat spell.

*Audience: cooperative, agricultural extension, water authority, insurer, buyer.*

### B. Field-scale — the same numbers, one parcel at a time (needs a field boundary)

Everything in this report, per field: cycle count, SOS/POS/EOS, planting and harvest windows, peak vigour, greenness integral (yield proxy), year-over-year comparison, in-season NDMI stress flags, and — for forage — the berseem cut log. This is the individual-farmer / agronomist view. The only extra ingredient over the village layer is the **parcel boundary**, so the field-mean is clean.

### C. Unique to your land — needs ground truth, more pixels, or more bands

These do **not** generalise; this is where local knowledge is irreplaceable:

- **The berseem cutting sweep inside one field** — the satellite catches the cut-front *moving* across the field only because berseem is harvested progressively for fodder *and* this parcel has enough 10 m pixels and cloud-free revisits to see it. The clean wheat/berseem *block* split, by contrast, is **not** resolvable at 10 m here (it is buried under the cutting pattern). Most fields are single-crop, or too small (<~0.3 ha) to show any sub-field structure at all.
- **Exact crop identity** — timing/shape narrows it (cereal vs forage vs corn) but can't prove wheat-vs-berseem, or which summer crop, without your notes or a red-edge classifier.
- **Fall Armyworm / pest damage** — not visible in 10 m NDVI at all (needs NDRE + scouting); crop- and field-specific.
- **Exact sowing and cut dates** — the satellite gives windows; the true dates live in your records.
- **The "why"** — variety, irrigation method, why one zone differs — only you know.

### Quick reference

| Insight | Best scale | Needs | Reliability |
|---|---|---|---|
| Planting / harvest calendar | Village | nothing extra | High |
| Cropping intensity (cycles/yr) | Village or field | — | High |
| Crop mix (cereal / forage / corn) | Village | curve shape | Medium–High |
| Vigour / yield proxy / trend | Field (sum to village) | boundary | Medium–High |
| Stress / anomaly screening | Village → field | NDMI, neighbours | Medium |
| Crop identity (exact) | Field | ground truth / red-edge | Medium |
| Within-field zones / crop split | Bespoke | many pixels + 2 crops | Low–Medium |
| Berseem cut count | Field | dense revisit | Medium (a floor) |
| Pest (FAW) detection | — | red-edge + scouting | Not from NDVI |

**Rule of thumb:** the more an insight averages over space and time, the more the satellite can be trusted on its own; the more it drills into one field at one moment, the more it needs your ground truth. Your parcel sits at the far "bespoke" end — small, split, and intensively managed — which is exactly why it was such a good stress-test for the method.

---

## 14. Recommended additional Sentinel-2 bands

You originally loaded **B02, B03, B04, B08, B11 + SCL** — enough for NDVI, EVI, NDMI, NDWI, MNDWI. You have **since added the red-edge set** (B05/B06/B07/B8A at 20 m); see §15 for what NDRE actually showed. The full menu and priorities, for reference:

| Band(s) | What it is | Why you'd want it | Priority |
|---|---|---|---|
| **B05, B06, B07 + B8A** | red-edge (705 / 740 / 783 nm) + narrow NIR (865 nm) | Enables **NDRE** and red-edge chlorophyll indices: sensitive to chlorophyll / nitrogen and early stress, and they **saturate later than NDVI** so they see canopy decline NDVI misses. This is the direct fix for the Fall Armyworm blind spot and for nitrogen / early-stress monitoring on corn. | **High** |
| **B12** | SWIR2 (2190 nm) | With B11 enables **NBR / NDII** and cellulose-absorption indices: better crop-water stress, **residue vs bare soil**, tillage detection, and cleaner senescence/harvest timing. Strengthens the moisture story you already have. | **Medium** |
| **B01** | coastal aerosol (443 nm) | Mostly atmospheric-correction QA / aerosol; little direct agronomic value. | Low |
| **B09** | water vapour (945 nm) | Atmospheric water-vapour correction QA; not a crop signal. | Low |
| **AOT, WVP** | aerosol & water-vapour rasters | Per-pixel atmospheric-quality flags; advanced QA only. | Low |

**The highest-value addition was the red-edge set (B05 / B06 / B07 / B8A) — and you have now added it.** It unlocks NDRE for in-season stress and nitrogen work. What it did and did not reveal for Fall Armyworm is in §15 below.

---

## 15. Update — red-edge bands added, NDRE tested

You upgraded the cube with the red-edge bands (B05/B06/B07/B8A) at 20 m and regenerated the CSV. I computed **NDRE = (B8A − B05)/(B8A + B05)** directly from the new bands and re-ran the Fall Armyworm question. The honest result, in three points:

- **NDRE moves almost in lockstep with NDVI here (r = 0.99).** At this field's scale it does **not** expose a hidden Fall Armyworm signal in the average — even red-edge, at 20 m, cannot see patchy whorl-scale damage. Adding it did not turn the satellite into a FAW detector for this parcel.
- **Where NDRE genuinely helps: saturated canopy.** In the dense winter crop NDVI pins near 0.89 (saturated) while NDRE sits at ~0.65 with headroom to spare. That makes NDRE the better index for grading vigour and nitrogen in thick berseem/wheat where NDVI flattens — a real, keepable gain.
- **Corn 2025 (the FAW year) reads a touch below 2024** in both indices at each crop's own peak (≈0.68 vs 0.75 NDVI; ≈0.54 vs 0.58 NDRE). Consistent with the damage you described, but the gap is small and confounded by the partial 2024 record and different planting dates — not a call to make from orbit alone.

**Net:** the red-edge upgrade was worth doing — it strengthens dense-canopy and nitrogen monitoring and is the right band set to keep — but it **confirms rather than overturns** the earlier conclusion: Fall Armyworm is a scouting / drone-scale problem, and satellite (even red-edge) is a backstop, not the front line. The figure for this is section 10 of the HTML report.

---

## 16. Update — start extended to 2 May 2024 (and two engineering catches)

You extended the record's start to 2 May 2024 (now 280 acquisitions, 02 May 2024 → 19 Jun 2026). The payoff and two process lessons:

**The win — corn 2024 is now a full crop.** The record previously began mid-summer-2024, so that corn was a *partial* cycle with no start. The earlier data now shows the **tail of the previous winter crop** senescing in early May, a **bare-soil trough ~mid-May**, then the corn green-up — so corn 2024 has its own SOS (~18 May), peak (10 Jul) and a planting estimate. All four cycles are now fully bracketed.

**Catch 1 — a stale mount, caught by a guard.** When I first re-read the folder I saw a *corrupt, partly-synced* copy: malformed `run_metadata.json`, a `premature end` on the time chunk, a 263-row CSV ending 7 May 2026. The preflight check you added to `analyze.py` (CSV-rows must equal cube-time-steps, root == 20 m) **correctly refused to build** on it. You then verified the real local artifact (280 rows, clean) and mounted a fresh copy; pointing the pipeline there, the preflight passed (280 == 280) and the build proceeded. Lesson: that row-count cross-check is cheap insurance against shipping a report off half-synced data — worth keeping.

**Catch 2 — the smoother had erased a real feature.** With the longer record, corn 2024's green-up was first mis-dated to the very first day (2 May). Cause: the Whittaker smoother at λ=6000 flattened the sharp early-May bare-soil trough (raw NDVI ~0.18) up to ~0.33, so no between-crop trough was detected and the start defaulted to the record edge. Fix: lower λ to **3000**, which restores those between-crop troughs while still smoothing the berseem cutting saw-tooth (verified: 4 clean peaks + 4 clean troughs, no winter fragmentation). Lesson: a smoother strong enough to denoise can also erase the exact transitions phenology depends on — validate that it preserves the features you need to detect.

**Also corrected here:** rebuilding the pixel figures from the clean cube put the berseem cut count at **~5 per pixel** (the stale copy had given ~3) — right in the 4–6 range real Miskawi berseem takes.

---

## 17. Side test — MSAVI vs NDVI

A quick check of whether a soil-adjusted index (**MSAVI2**, built from the same red/NIR bands) beats NDVI on this field. The result: **for phenology they are interchangeable** — the two track almost identically over the record (**r = 0.98**), same cycles and timing, so the crop calendar would be unchanged. MSAVI differs only at the *edges* of the cover range. It **strips the soil background**, so between-crop troughs read genuinely bare (~0.10–0.14 vs NDVI's ~0.25), and it **saturates less** — at the corn peak the same field reads NDVI 0.79 vs MSAVI 0.52, which spreads dense and moderate canopy further apart.

**Takeaway:** keep NDVI as the familiar backbone, and carry MSAVI specifically for **bare-soil / fallow / planting-onset** detection — exactly the *"is the land idle or just starting?"* question — where its cleaner floor adds real confidence. It does **not** lift the ceiling that matters (still no Fall Armyworm). The 2×2 figure (spatial on top, temporal below) is section 11 of the HTML report.

---

## 18. Side test — Hidden Markov Model (unsupervised cross-check)

Tested whether an *independent, threshold-free* method recovers the same crop cycles. A **4-state Gaussian HMM** — states LOW / RISING / HIGH / DECLINING, Gaussian emissions on [NDVI value, slope], trained with **Baum-Welch (EM)**, decoded with **Viterbi** — was run on the smoothed NDVI; activity windows are contiguous RISING/HIGH/DECLINING runs merged across LOW gaps < 15 days (matching the current merge rule).

**Result: the two methods agree.** The HMM's windows land on the same four crop cycles as the current threshold approach, with boundaries agreeing to **~4 days at green-up and ~1 day at harvest**. Because the HMM uses **no hand-set threshold** — it learns the state emissions and transitions from the data — this is a genuine cross-validation: the cycles are a property of the field, not an artefact of the 20 %-amplitude rule. (State self-persistence came out 0.97–0.99, as expected for a smooth phenology curve.)

| | Current (threshold) | HMM (unsupervised) |
|---|---|---|
| Method | 20 % of amplitude + merge | Baum-Welch + Viterbi, 4 Gaussian states |
| Thresholds | hand-set | learned from data |
| Cycles found | 4 | 4 (+ a 6-day edge sliver) |
| Boundary agreement | — | ~4 d start, ~1 d end |
| Per-day state | no | yes, probabilistic |

- **What HMM adds:** learned (not hand-tuned) thresholds; a probabilistic state for every day (built-in uncertainty); it is well-cited for remote-sensing phenology; and it works on a single series. It needs a *slope* feature alongside the value, since RISING and DECLINING sit at the same NDVI level.
- **What the current approach keeps:** simpler and directly interpretable (start = 20 % of amplitude), with the per-cycle yield-proxy metrics falling straight out.
- **Honest note:** both rest on the same smoothed signal, so the HMM doesn't change the conclusions — it is a more principled, threshold-free route to the *same* windows, plus a per-day state label. The lone difference (a 6-day HMM sliver at the record start) is the previous winter crop's tail at the edge, not a real extra cycle. *For project credibility this is useful: an unsupervised probabilistic model independently reproducing the rule-based baseline is exactly the kind of validation a committee respects.*

Figure: section 12 of the HTML report.
