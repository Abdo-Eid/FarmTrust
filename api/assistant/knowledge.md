# FarmTrust field knowledge (Nile Delta / Egypt)

Curated local agronomy and interpretation knowledge for reasoning about satellite
land-assessment reports. This is **background to reason with** and to sense-check
what a user tells you — it is **not** proof of what grew on any specific parcel.
Edit this file to teach the assistant; it is loaded into the prompt as-is.

## How to use it

- Keep three things separate: the measured signal, your interpretation, and what the user told you.
- Satellite greenness cannot prove crop identity, yield, pests, or income — never assert those from the signal alone.
- "summer" / "winter" / "transition" are calendar descriptors, not crop names.
- When a user declares a crop or a rotation, treat it as ground truth and reason forward from it.

## Cropping calendar

- **Winter (≈ Nov–May):** wheat; berseem / Egyptian clover (a fodder crop cut several times a season); sometimes faba beans or fasolia before wheat, which can delay the wheat green-up by about a month.
- **Summer (≈ May–Oct):** maize (corn), rice, cotton; occasionally a short vegetable cycle.
- **Rotation:** 2–3 complete vegetation cycles per year is a normal intensive rotation here — a winter + summer pair is the common base, and a short third cycle is what pushes a year to three.

## Interpretation lessons

- **Berseem cutting:** repeated NDVI dips-and-regrowths inside a single winter window are usually normal cut/regrowth fodder management, not crop failure or stress.
- **Mixed winter management:** a parcel may hold wheat and berseem together, or staggered berseem cutting. A wide mean-vs-p95 (within-field) spread is patchiness / field-uniformity evidence only — not proof of a crop split or stand failure. Raise mixed management as a possibility unless the user confirms it.
- **Beans/fasolia before wheat:** a late or weak-looking wheat window can simply be a rotation where beans preceded wheat. Do not read a late green-up as failure without rotation context.
- **Greenness is not yield:** a clean, uniform canopy can still hide pest damage (e.g. Fall Armyworm in summer maize). Never claim pest presence or absence, yield, or income from the signal. Prefer "the satellite does not show canopy collapse" over "the crop was healthy".
- **Red-edge (NDRE):** tends to track NDVI closely and does not, on its own, expose hidden pest damage. Treat it as dense-canopy vigour / nitrogen context, not a pest or yield detector.
- **Moisture (NDMI):** summer crops such as maize have higher water demand and can naturally read lower moisture than winter crops. Use NDMI as a relative moisture / stress watch, not a failure verdict.
- **Surface water (MNDWI):** use cautiously for a standing-water / flood signal; a dense canopy can dominate the series and mislead. Avoid rice or flooding claims without strong, contextual water evidence.
- **Edge / open cycles:** the observation record can start or end inside a real cycle. Keep open or incomplete cycles as open — do not force them into a full season.
- **Crop identity:** shape and timing can narrow the possibilities but cannot prove a crop. Say "consistent with", "calendar-aligned", or "user-declared" — never that a crop was automatically detected.
- **Spatial detail:** small parcels have few pixels, so pixel patterns are easy to over-read. Treat the field-mean time series as the robust backbone and within-field spread as supporting context only.
