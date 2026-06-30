# Local Interpretation Context

Purpose: preserve local agronomy and interpretation lessons that were not obvious from satellite observations alone. Future agents should use this as context when interpreting numbers, charts, and maps, especially for Menofia / Nile Delta parcels.

This document is context, not automatic truth. Use it to avoid naive interpretations, but keep claims grounded in observed evidence, user-provided notes, and explicit confidence labels.

## Use Rules

- Treat local crop/management details as context or user-provided notes, not as automatically detected facts.
- Separate measurement from interpretation: observed signal, inferred pattern, local explanation, and confidence.
- Do not infer exact crop identity, yield, pest damage, income, or legal status from satellite signals alone.
- Broad labels such as `summer cycle` and `winter cycle` are allowed as calendar descriptors, not crop labels.
- Synthetic/model-derived curve values can support season analysis, but only real usable observations are direct evidence.

## Local Lessons

| Topic | Naive interpretation risk | Local/context correction | How future agents should use it |
|---|---|---|---|
| Berseem cutting pattern | Pixel maps show a static crop boundary or sensor noise. | Winter pixel variability can be a moving berseem/fodder cutting front. Freshly cut strips drop in NDVI, then regrow while another strip is cut elsewhere. | If winter maps show moving low/high NDVI bands, consider progressive fodder cutting before declaring crop split, stress, or sensor artifact. |
| Wheat + berseem in one parcel | A wide mean-vs-p95 gap means stand failure. | Mixed winter management is common; a parcel may contain wheat and berseem, or staggered berseem cutting. | Use p95/spread as patchiness evidence only. Mention possible mixed management when supported, but require user notes for exact explanation. |
| Beans/fasolia before wheat | Wheat is late, weak, or missing because it does not match the normal wheat calendar. | Some farmers plant `fasolia`/beans before wheat to use the land more intensively. This can delay wheat by about one month. | Future crop/rotation-aware calendars should support delayed wheat expectations. Current general logic should avoid penalising late green-up without rotation context. |
| Berseem cut count | Multiple NDVI dips inside winter mean crop failure or repeated stress. | Berseem is cut repeatedly for animal feed. Dips followed by regrowth can be normal management. | Treat repeated winter dips as possible cut/regrowth cycles, especially when field context says berseem. Do not call them damage without corroboration. |
| Summer corn and Fall Armyworm | Healthy NDVI means healthy yield. | The isolated work showed FAW-damaged corn can still look like a clean, uniform canopy from Sentinel-2. Greenness is not yield. | Never claim FAW absence, pest status, yield, or income from NDVI/NDRE alone. Use wording like `satellite does not show canopy collapse`, not `crop was healthy`. |
| NDRE | Red-edge solves pest detection. | NDRE moved almost in lockstep with NDVI on the parcel (`r = 0.99`) and did not expose hidden FAW damage at 20 m. It is useful mainly where NDVI saturates. | Keep NDRE for future dense-canopy headroom, vigour, nitrogen/stress context. Do not use it as a pest or yield detector. |
| Dense winter canopy | NDVI peak values fully describe canopy vigour. | NDVI can saturate near dense winter canopy. NDRE may retain headroom where NDVI flattens. | For future index expansion, use NDRE to add dense-canopy nuance, while keeping the same no-yield/no-pest guardrails. |
| Summer moisture | Lower summer NDMI means crop failure. | Summer corn has higher water demand and may naturally show lower moisture than winter crops. | Use NDMI as a moisture watch/relative stress indicator, not a definitive failure claim. Pair it with timing, cycle strength, and local irrigation context. |
| Water/rice inference | Any wet-looking green-up means flooding or rice. | The isolated work found a relative MNDWI comparison was misleading because the whole-series median was dominated by dense-canopy values. Standing water needs careful absolute/contextual interpretation. | Use MNDWI cautiously for surface-water/flooding signal. Avoid crop/rice claims unless supported by strong water evidence and local context. |
| Edge cycles | A cycle without observed start/end is not real. | The record can start or end inside a real crop cycle. Extending the record recovered the summer 2024 cycle; latest cycles can be open/incomplete. | Preserve `open_left`, `open_right`, or incomplete cycle status. Do not force a full-season interpretation. |
| Smoothing | Strong smoothing always improves phenology. | The isolated work found that a too-strong smoother erased a real between-crop bare-soil trough and mis-dated corn green-up. | Smoothing must preserve troughs and transitions needed for season detection. Validate that smoothing does not erase local agronomic events. |
| Exact crop identity | Shape/timing proves wheat, berseem, corn, or beans. | Shape and timing can narrow possibilities, but exact crop identity depends on user notes, ground truth, or stronger labelled models. | Say `consistent with`, `calendar-aligned`, or `user-declared`; do not say exact crop identity is detected automatically. |
| Pixel maps | Maps are always more truthful than field means. | Pixel maps revealed useful structure, but also caused an initial wrong interpretation that user feedback corrected. The parcel has only about `6 x 18` 10 m pixels. | Pixel maps are useful for visual explanation, but high-risk for over-reading. Start with numeric spatial evidence; use selected static maps only when visually useful and clearly caveated. |
| Field-mean CSV | Field means hide too much to trust. | Recomputed raw-pixel NDVI matched the delivered CSV well (`r = 0.94`), so field-mean time series was a faithful backbone for the parcel. | Keep field-level time series as the primary robust signal; use pixel evidence as supporting context, not the core decision basis. |
| Central walkway / local field features | Thin spatial patterns are crop zones. | Local features such as a `mamsha`/central walkway may faintly appear and can be confused with crop boundaries. | Mention only with strong visual support and local confirmation. Avoid automated claims from small linear artifacts. |

## Point 8 Decision Context

Current direction: use numeric spatial evidence now, with selected static visuals where they are both useful and visually compelling. Full pixel-map workflows and interactive raster maps remain future work.

Current implementation intent:

- Carry numeric spatial signals such as mean, p95, and mean-vs-p95 spread into reporting.
- Use those signals for cautious field uniformity / patchiness language.
- Include one or a small number of static visual artifacts later when they add real explanatory value and look good, such as a cycle peak map or winter variability/cut-front figure.
- Do not build a full pixel-level map UI in the current pass.

Future work:

- Static pixel-map generation pipeline for selected report figures.
- Interactive raster/time-slice map UI.
- Crop/rotation-aware calendar using user-declared or locally configured expectations.
- NDRE/MSAVI index expansion with strict guardrails.
