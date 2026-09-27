## 2.1 Remote Sensing for Agricultural Review

Remote sensing is the collection of information about the Earth's surface without direct physical contact. In agriculture, satellite remote sensing is used to observe vegetation cover, crop growth patterns, moisture context, bare soil periods, and surface change across time. These observations are not direct measurements of profit, creditworthiness, or farmer behaviour, but they can provide useful evidence about whether a land parcel appears active and whether its recent history is visible enough to support review.

For agricultural finance, the value of remote sensing is repetition. A field visit gives a strong local observation at one time. A satellite time series gives a weaker but repeated observation over many dates. When used carefully, this record can help a lender understand whether vegetation activity appeared consistently, whether recent activity changed, and whether the available observations are too limited to support a confident reading.

Remote sensing also creates a common evidence structure. Instead of relying only on manually written descriptions, a reviewer can inspect dates, charts, evidence quality, and explicit limitations. FarmTrust uses remote sensing in this limited sense: satellite imagery is one evidence source in a lender-facing assessment, not a complete agronomic diagnosis.

## 2.2 Sentinel-2 Imagery

Sentinel-2 is a public multispectral satellite mission widely used for land and vegetation monitoring. It provides visible, near-infrared, red-edge, and shortwave infrared bands that can support vegetation and moisture interpretation. Its open availability makes it suitable for a graduation project and for an affordable first version of a land-assessment platform.

The mission is useful for FarmTrust because it balances availability, spectral richness, and spatial detail. The visible and near-infrared bands support common vegetation indices such as NDVI. Red-edge bands can add context in dense vegetation conditions. Shortwave infrared bands support moisture-related interpretation. The repeated observation schedule makes it possible to build a time series rather than depend on a single image.

However, Sentinel-2 is not a perfect field inspector. Clouds can hide the land, haze can weaken the observation, and small parcels may contain mixed pixels. The revisit schedule can miss short events, especially when cloudy periods remove otherwise usable observations. For this reason, FarmTrust pairs Sentinel-2 evidence with confidence scoring, quality notes, and cautious language.

Table: Table 2.1: Sentinel-2 strengths and limits for finance-oriented land assessment

| Aspect | Strength | Limitation | Design response |
| --- | --- | --- | --- |
| Availability | Public imagery supports a low-cost platform | Missing or delayed scenes can occur | Report evidence coverage and gaps |
| Spectral bands | Vegetation and moisture signals can be derived | Signals remain indirect and context-dependent | Avoid yield, pest, and income claims |
| Repeated observation | Activity history can be reviewed over time | Cloudy periods can hide important events | Use time-series confidence, not single-date certainty |
| Spatial detail | Field-level summaries are possible for submitted parcels | Small parcels can contain few or mixed pixels | Surface parcel-size and AOI limits |
| Interpretation | Charts can make land activity visible | Charts can be over-read without agronomic context | Use conservative report language |

## 2.3 Vegetation and Moisture Indices

Vegetation indices combine spectral bands into simpler numerical signals. They do not directly reveal farm income or crop success, but they can make satellite observations easier to interpret. In agricultural monitoring, these indices help describe greenness, canopy development, moisture context, and possible surface-water signals.

NDVI is the main greenness index because it is simple, widely understood, and useful for observing vegetation activity. A higher NDVI value often indicates stronger green vegetation, while a lower value can indicate bare soil, sparse vegetation, harvest, cutting, or stress. Its limitation is that it can saturate in dense canopies and cannot prove yield or crop identity.

Other indices add context rather than final answers. NDRE can help in denser vegetation where red-edge information is useful. EVI supports canopy-vigour interpretation under some conditions. NDMI provides relative moisture context using near-infrared and shortwave infrared information. NDWI and MNDWI may support water-related interpretation, but soil background, canopy cover, and mixed pixels can affect the reading.

Table: Table 2.2: Vegetation-index decision boundaries used in the project

| Index or signal | What it adds | What it cannot show | How FarmTrust uses it |
| --- | --- | --- | --- |
| NDRE red-edge signal | Dense-canopy headroom and vigour where NDVI can saturate | Hidden pest damage; it tracked NDVI at about r = 0.99 in the research work and did not reveal Fall Armyworm damage | Headroom and context only; never a pest or yield detector |
| NDVI / NDRE greenness | Canopy greenness and vegetation activity | Actual yield or pest status; damaged corn can still look like a clean canopy | Prefer "no canopy collapse" over "healthy"; never claim pest, yield, or income |
| NDMI moisture signal | Relative moisture or stress watch | A failure verdict; summer corn can naturally read lower because of higher water demand | Relative stress watch paired with timing and irrigation context |
| MNDWI water signal | Possible surface-water signal | Reliable absolute water; canopy-dominated medians can skew a relative comparison | Cautious surface-water signal only; no rice or flooding claim without stronger evidence |

The table reflects a design principle used throughout the project: a narrower honest claim is better than a wider unsupported one. If greenness is strong, the report can say that vegetation activity appears strong. It should not say that the farmer will repay the loan. If moisture context is weak, the report can flag a watch item. It should not diagnose the cause without supporting evidence.

## 2.4 Time-Series Interpretation

Agricultural land is dynamic. A single satellite image may be misleading because land passes through bare soil, planting, growth, cutting, harvest, and residue stages. A low greenness value may be normal before planting or after harvest. A temporary dip may represent a fodder cut followed by regrowth. A strong peak may represent vegetation activity without proving the exact crop or yield.

Time-series analysis reduces this risk by studying the shape of vegetation activity across many dates. Instead of asking only what the land looked like on one date, the system asks how the signal changed over time. Did the signal rise from a low baseline? Did it reach a clear peak? Did it decline afterward? Were there enough usable observations to trust the pattern?

FarmTrust uses activity cycles to organize this interpretation. A cycle is a period of vegetation activity that includes a rise, peak, and decline, although real data may contain incomplete edges or missing observations. Cycle-based interpretation is more suitable for agriculture than single-date classification because it respects seasonality and supports cautious report language such as recent activity, limited history, interrupted cycle, or uncertain trend.

The difference between observed values and interpreted shape is important. Observed values are the actual satellite-derived records available on particular dates. Interpreted shape is a smoothed and structured reading used to understand the agricultural pattern. The report should not pretend that a smoothed daily curve is directly observed every day.

## 2.5 Smoothing and Phenology Decisions

Satellite time series are noisy. Clouds, haze, changing view conditions, atmospheric effects, and mixed pixels can produce small movements that are not meaningful agricultural changes. If the system reacts to every small movement, it may detect false cycles. If it smooths too strongly, it may erase real troughs between crops or hide a harvest and regrowth pattern. The smoothing problem therefore affects the honesty of the final assessment.

The team's research work compared different smoothing strengths and detector behaviours. Very low smoothing followed noise. Very high smoothing removed useful agricultural transitions. The chosen direction uses a phenology-scale rule: it smooths vegetation over an agricultural timescale rather than tuning the curve separately for every parcel. This makes the method easier to explain and reduces the risk of fitting noise as if it were true crop behaviour.

The same discipline applies to cycle detection. A detector must decide whether a rise is large enough to count, whether shallow sub-peaks belong to one crop cycle or several false cycles, and how to handle cycles that begin before or end after the observation window. FarmTrust therefore treats activity windows as evidence summaries with confidence limits, not as perfect declarations of planting and harvest dates.

## 2.6 Agronomic Interpretation Lessons

Remote sensing must be interpreted with agricultural caution. A pattern that looks obvious from a chart may have more than one explanation on the ground. This is especially true in small parcels, mixed management systems, and fields with fodder cutting or crop rotation.

The team's research work included case-study interpretation lessons that directly influenced the product boundaries. These lessons showed that naive satellite reading can be wrong when it is separated from local crop calendars and field knowledge. A late green-up may not mean failure. A wide difference between field-average and high-performing pixels may not mean stand collapse. Repeated winter dips may reflect cut-and-regrowth management rather than damage.

[[PAGE_BREAK]]

Table: Table 2.3: Interpretation lessons from the team's research work

| Naive satellite reading | Local or agronomic correction | How the book and report use it |
| --- | --- | --- |
| Late wheat green-up means a problem | Beans-before-wheat rotation can delay green-up by about one month | Do not penalize late green-up without rotation context |
| A wide mean-versus-high-pixel gap means stand failure | Mixed winter management, including wheat with berseem or staggered cutting, can also widen it | Use spread as patchiness evidence only; require field notes for the exact cause |
| Repeated winter greenness dips mean failure or stress | Berseem cut-and-regrowth can create repeated dips followed by recovery | Treat repeated winter dips as possible cut-and-regrowth, not damage without corroboration |
| Moving winter low-greenness bands mean a static geometry issue or sensor noise | A moving fodder cutting front can create freshly cut strips that drop and then regrow | Consider progressive cutting before declaring a crop split or artifact |
| Pixel maps can be read directly | On a small parcel of roughly 6 x 18 pixels at 10 m, over-reading maps drove an early wrong interpretation | Start from numeric spatial evidence; use static maps only when useful and clearly caveated |
| Shape and timing prove exact crop identity | Shape and timing only narrow possibilities; field notes or labels confirm identity | Use "consistent with", "calendar-aligned", or "user-declared", not automatic detection |
| The delivered field-mean series might be unreliable | Recomputed raw-pixel NDVI matched the delivered field-mean series at r = 0.94 | Keep the field-mean time series as the robust backbone; pixel evidence remains supporting context |

These lessons matter because FarmTrust is meant for finance review. A misleading confident statement can affect a real borrower or lender. The system therefore separates what was observed from what was interpreted, and it describes uncertainty as part of the evidence rather than as an error to hide.

## 2.7 Agricultural Finance Evidence

A lender needs evidence that is timely, clear, and defensible. Remote sensing can support this need by giving repeated observations of land activity, but the evidence must be translated into a review format. A loan officer should not be expected to read raw bands or decide whether a smoothing method is appropriate.

The most relevant finance questions are practical. Has the land shown recent vegetation activity? Is the latest activity window strong or weak compared with the recent history? Are there observation gaps that reduce confidence? Is there a risk signal that should prompt closer inspection? What does the system explicitly not know?

FarmTrust is designed around these questions. The output is not a raw remote-sensing product. It is a grounded assessment report that includes charts, evidence notes, confidence, and limitations so that the lender can use the information responsibly. This framing avoids the weakness of analytics products that present a score without explaining what the score means.

## 2.8 Crop Classification and Yield Prediction as Research Boundaries

The broader research work included crop-classification and yield-prediction experiments. These experiments clarified what the platform should not ship as a claim. Crop identity depends on labels, region, season, management, feature availability, and validation design, while yield depends on many factors that satellite imagery cannot observe directly.

Table: Table 2.4: Multi-country yield dataset coverage used in research framing

| Country | Fields | Years and crops |
| --- | --- | --- |
| Argentina | 751 | 2017-2024; soybean, corn, wheat |
| Brazil | 551 | 2017-2024; soybean, corn, wheat |
| Germany | 299 | 2016-2022; wheat, rapeseed |
| Uruguay | 572 | 2018-2022; soybean |
| Total | 2,173 | Four crops across 2016-2024 |

The dataset coverage is scientifically useful, but it also shows why transfer is difficult. Crop and geography are partly entangled: for example, Germany contributes wheat only, while corn appears in Argentina and Brazil. A model can therefore learn domain shortcuts unless its results are checked carefully.

[[PAGE_BREAK]]

Table: Table 2.5: Crop and yield research streams compared

| Aspect | Field-level crop-mapping stream | Morocco AOI-validation stream |
| --- | --- | --- |
| Input | Seasonal field sequence with 20 timesteps | Static mean AOI or field features |
| Focus | Temporal sequence modelling | Inference validation against a known AOI |
| AOI evidence | Not directly reported in the field-level stream | Direct, but low-confidence and limited |
| Status | Research-only | Research-only |

The two streams use different feature contracts and label sets, so their metrics are not directly comparable. This boundary is central to the credibility of FarmTrust. The platform is strongest when it supports land activity review, evidence quality, and cautious risk interpretation. It would be weaker if it presented uncertain crop or yield models as production-ready.

## 2.9 Bounded Language-Model Explanation

Language models can make technical reports easier to understand. They can summarize, answer follow-up questions, and translate technical language into more accessible explanations. This is valuable for a lender-facing platform because many users will not be remote-sensing specialists.

However, language models also create risk. If a model is allowed to answer freely, it may invent unsupported details, overstate confidence, or respond to a loan decision question as if the satellite report were a complete credit assessment. In agricultural finance, this risk is serious because the answer may influence a human decision.

FarmTrust therefore uses a bounded explanation approach. The assistant explains an already-computed report. It is expected to answer from the report evidence, clarify the meaning of charts and confidence notes, and refuse or narrow questions that go beyond the available evidence. It should not create new risk scores, approve or reject loans, identify crops from imagination, estimate yield, or diagnose pests.

## 2.10 Summary of the Literature and Design Gap

The background reviewed in this chapter leads to a clear design gap. Remote sensing provides repeated evidence about land activity, and Sentinel-2 provides a practical public data source. Vegetation and moisture indices can support interpretation, but each index has strict limits. Time-series analysis and smoothing can reveal agricultural cycles, but the method must preserve uncertainty. Agricultural finance needs clear reports, not only scientific charts. Language models can improve explanation, but only when they are bounded to verified evidence.

FarmTrust addresses this gap by combining these elements into a lender-facing platform. Its value is narrow and defensible: it turns repeated satellite observations into a conservative assessment that helps human reviewers understand land activity, confidence, and limitations.
