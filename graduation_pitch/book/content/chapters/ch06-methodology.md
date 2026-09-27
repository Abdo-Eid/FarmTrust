## 6.1 Methodology Overview

The FarmTrust methodology converts a user-drawn land polygon into a confidence-aware agricultural land assessment. The method is not based on one satellite image or one vegetation value. It uses a sequence of observations over time, filters them for usable evidence, creates a model-derived analysis curve, detects vegetation activity cycles, and summarizes the result for finance review.

The methodology was designed for the current project scope: agricultural parcels in Egypt, Sentinel-2 imagery as the satellite evidence source, a recent two-year observation window, and a lender-facing report. The output is decision support. It does not claim automated loan approval, exact crop identity, yield prediction, pest diagnosis, income estimation, or legal and cadastral verification.

The central idea is that agricultural land should be assessed as a time process. A field may look bare after harvest, highly green at canopy peak, mixed during staggered cutting, or uncertain during cloudy periods. FarmTrust therefore focuses on repeated observations, cycle shape, evidence coverage, and confidence.

Table: Table 6.1: Methodology stages

| Stage | Main input | Main output |
| --- | --- | --- |
| Area definition | User-drawn polygon | Analysis polygon and area |
| Satellite retrieval | Polygon and time window | Sentinel-2 observation stack |
| Quality screening | Scene classification and valid pixels | Usable observation record |
| Index calculation | Spectral bands | Vegetation and moisture signals |
| Smoothing | Irregular observations | Daily analysis curve |
| Activity-cycle detection | Smoothed greenness curve | Activity windows and boundaries |
| Assessment | Cycles, gaps, indicators | Status, trend, confidence, risks |
| Report generation | Assessment evidence | Grounded lender report |

## 6.2 Area of Interest and Satellite Source

The first methodological step is defining the area of interest. In the current system, the user draws a polygon around the land parcel. This step looks simple, but it strongly affects the rest of the method. Agricultural parcels are spatial objects. A small AOI error can include roads, canals, neighboring crops, bare soil, or buildings. Those pixels can distort the field-level signal and may create false evidence of weak vegetation or mixed behavior.

The platform treats the polygon as the analysis area for the satellite review, not as a legal survey. It is a practical area chosen by the user for evidence extraction. The report should not present it as proof of ownership or exact cadastral geometry.

After the land is defined, FarmTrust retrieves Sentinel-2 Level-2A observations. Sentinel-2 is suitable for this project because it provides open multispectral imagery with visible, near-infrared, shortwave-infrared, and red-edge bands. These bands support vegetation, moisture, and water-related indicators at a revisit frequency that can reveal agricultural activity over time. The method uses the satellite record to study temporal behavior rather than relying on a single inspection moment.

The raw imagery is preserved as an evidence record that keeps observation dates, spectral bands, quality information, and provenance together. If a preprocessing rule changes, the same source evidence can be reprocessed and compared.

## 6.3 Observation Quality and Evidence Coverage

Remote-sensing analysis is only as reliable as the observations it uses. Clouds, cloud shadows, atmospheric issues, partial coverage, and long revisit gaps can create false drops or false trends. A cloudy period can make a healthy field appear inactive if the method treats missing evidence as bad evidence. For this reason, FarmTrust records observation quality before interpreting vegetation behavior.

The parcel-analysis figures in this chapter use an agricultural parcel in El-Kom Al-Akhdar, Shebin El-Kom District, Menoufia Governorate, Egypt. The figures come from the team's case-study analysis and are used to illustrate the method on a real parcel record rather than as universal validation for all Egyptian fields.

![Figure 6.1: Observation quality and gap profile for the El-Kom Al-Akhdar parcel.](fig06_quality_profile.png){width=4.7}

The quality profile directly affects confidence. A report with strong vegetation cycles and good observation coverage can support a stronger assessment than a report with the same apparent cycles but long gaps. Conversely, a weak or unclear result during a poor observation window should not be presented as a strong land-risk conclusion.

Observation quality also affects smoothing and cycle detection. Poor observations can pull the curve downward and create artificial troughs, while excessive filtering can hide real change. FarmTrust treats quality screening as a balance between contamination control and signal preservation.

## 6.4 Vegetation and Moisture Indices

The pipeline calculates multiple field-level indicators from the satellite bands. NDVI and EVI describe greenness and canopy vigor. NDRE provides red-edge context that can help in dense vegetation, although the research work showed that it should not be treated as hidden proof of pest status or yield. NDMI provides a relative moisture signal. NDWI and MNDWI provide cautious water-related signals. These indices are evidence signals, not final decisions.

Because Figure 6.2 is the first vegetation-index time-series plot in the book, it is useful to explain how this type of plot should be read. The horizontal axis is calendar time, and the vertical axis is an index value calculated from satellite bands, not a direct measurement of yield or crop quality. Each colored curve represents one signal for the same land parcel: for example, NDVI is used as the main greenness signal, EVI is a supporting canopy-vigor signal, and NDMI adds canopy-moisture context. Peaks show periods when the parcel has a stronger vegetation or moisture response; troughs show lower signal periods that may correspond to harvest, cutting, bare soil, crop transition, cloud-affected evidence, or another local condition. When a plot includes shaded background windows, those windows mark calendar periods that help compare the signal with expected seasonal or management timing. FarmTrust uses this plotting style because agricultural activity is a pattern through time. A lender or reviewer can see whether the land greens up, whether activity repeats, whether different indices agree, and where the report should remain cautious instead of turning a curve into an unsupported claim.

![Figure 6.2: Vegetation indices compared across the El-Kom Al-Akhdar parcel record.](fig07_vegetation_indices.png){width=4.7}

Different indices respond to different parts of the canopy and water signal, but the method remains conservative. A green canopy can still have pest damage. A low moisture indicator can reflect timing or irrigation rather than permanent stress. The report therefore uses index behavior as supporting evidence, not as proof of agronomic facts that the satellite record cannot confirm.

[[PAGE_BREAK]]

Table: Table 6.2: Main signal interpretation

| Signal | Main use | Important limitation |
| --- | --- | --- |
| NDVI | General greenness and activity pattern | Can saturate and cannot prove yield |
| EVI | Supporting canopy vigor signal | Still does not identify crop type |
| NDRE | Dense-canopy headroom and red-edge context | Not pest proof and not yield proof |
| NDMI | Relative moisture and stress watch | Needs seasonal and irrigation context |
| NDWI / MNDWI | Cautious surface-water evidence | Can be misleading under dense canopy |
| Field spread | Within-field uniformity evidence | Does not explain the cause by itself |

## 6.5 Building the Analysis Curve

Satellite observations arrive at irregular dates and with variable quality. A direct line between raw observations can exaggerate noise, while an over-smoothed curve can erase real agricultural transitions. FarmTrust therefore uses a quality-weighted smoothing approach to produce a model-derived daily analysis curve. The daily curve is used for shape analysis, while the original observation record remains the evidence layer for quality and confidence.

![Figure 6.3: Raw observations transformed into a smooth analysis curve.](fig08_smoothing_illustration.png){width=4.6}

The distinction between observed data and the analysis curve is methodologically important. The daily curve should not be read as if the satellite directly observed the field every day. It is an analytical representation built from the available observations, and confidence still depends on the quality and density of those observations.

The smoother protects the field-level signal from isolated bad points without removing real troughs between crop cycles. The challenge is to smooth at an agricultural timescale rather than at a purely statistical minimum.

## 6.6 Smoothness Selection

The smoothing strength is selected from an agricultural timescale rather than fitted separately for each land parcel. In the research work, very low smoothing followed noise, while very high smoothing erased real troughs between vegetation cycles. The numeric sweep in Table 6.3 shows why the selected value is a domain choice rather than a blind statistical minimum.

Table: Table 6.3: Smoothness lambda sweep used in method selection

| Smoothness lambda | Effective degrees of freedom | Method read |
| --- | --- | --- |
| lambda = 1, cross-validation minimum | About 176 | Undersmoothed; follows noise |
| lambda = 100 | About 64 | Still too rough |
| lambda = 3000 | About 29 | Domain-appropriate; recovers real cycles |
| lambda = 100000 | About 13 | Oversmoothed; erases useful transitions |
| Phenology-timescale rule, about 45 days | lambda about 2631 | Chosen |

The choice is intentionally explainable. A reviewer or examiner can understand the statement "we smooth vegetation over roughly five weeks" more easily than a per-parcel parameter that silently changes for each case. This also prevents the method from chasing small observation errors as if they were real agricultural events.

## 6.7 Activity-Cycle Detection

The central analytical unit in FarmTrust is the vegetation activity cycle. The book uses this term carefully. An activity cycle is a detected rise, peak, and decline in the vegetation signal. It is not automatically a crop label and not automatically a full agronomic season. A winter or summer label only describes the calendar period of the peak.

The detector searches the smoothed greenness curve for peaks and surrounding troughs. Each cycle receives estimated start, peak, and end dates, plus information about whether the cycle is complete or open at the edge of the observation window. This matters because a land record may begin in the middle of a real growing cycle. Forcing such a cycle to look complete would create false certainty.

The detector also avoids over-splitting repeated small dips inside one cycle. This is important for Nile Delta fields where fodder crops may be cut and regrown several times during a winter period. Without this caution, the system could mistake normal management for multiple separate crop cycles or for crop stress. Table 6.4 summarizes the detector design decisions that were kept after the method refinement.

Table: Table 6.4: Smoother and detector design decisions

| Decision | Options weighed | Chosen approach | Evidence or reason |
| --- | --- | --- | --- |
| Smoother design | Polynomial fit vs daily quality-weighted grid | Quality-weighted daily grid | Earlier fitting shifted gaps by 0.06-0.12 NDVI; the selected method kept the 0.17 bare-soil floor and recovered four cycles |
| Smoothing strength | Very low, moderate, and very high lambda | Phenology-scale smoothing, about lambda 2631 | Low smoothing followed noise; high smoothing erased a between-crop trough and shifted a known summer green-up |
| Per-limb amplitude thresholds | One symmetric threshold vs separate limbs | Rise = baseline + 0.20 x amplitude; fall = baseline + 0.35 x amplitude | Senescence often remains greener than emergence |
| Sub-peak merging | Split every trough vs merge shallow dips | Split only when the trough drops at least 0.50 of amplitude | Avoids false cycles in multi-cut fodder patterns |
| Edge and open cycles | Force complete cycles vs preserve open edges | Preserve open-left, open-right, and incomplete cycles | Extended record recovered a genuine summer 2024 cycle |
| Verification checks | Keep rejected detector settings vs refine chain | Refined smoother and detector chain | Three rejected checks became 53 passing checks |

Figure 6.4 shows the resulting cycle-detection style on the smoothed greenness curve.

![Figure 6.4: Activity-cycle detection on the smoothed greenness curve.](fig09_activity_detection.png){width=4.6}

## 6.8 Evidence Coverage and Assessment Confidence

FarmTrust separates land condition from evidence reliability. A cloudy period, a long observation gap, or unclear cycle boundary is not a land risk by itself. It is an evidence limitation. The system therefore records satellite evidence coverage and assessment confidence separately from land risk flags.

Assessment confidence is based on the reliability of the evidence, the clarity of activity cycles, and the strength of the signal. A low-confidence assessment does not mean the land is bad. It means the available satellite evidence is not strong enough to support a confident conclusion. This distinction is essential for lender-facing use because a financing analyst must know whether caution comes from the land behavior or from the data record.

Table: Table 6.5: Confidence interpretation

| Condition | Interpretation in the report | Effect |
| --- | --- | --- |
| Good coverage and clear cycles | Evidence supports the assessment | Higher confidence |
| Moderate gaps or unclear boundaries | Assessment is usable with caution | Medium confidence |
| Sparse observations or major gaps | Evidence is too limited for certainty | Low confidence or manual review |
| Open latest cycle | Latest performance is still developing | Provisional wording |
| Conflicting indicators | Some signals do not align | Watch item or limitation note |

Confidence also affects the report tone. With strong coverage, the report can say that satellite evidence supports recent vegetation activity. With poor coverage, the report should say that activity appears possible or that the evidence is limited.

## 6.9 Methodological Boundaries

The methodology intentionally avoids several attractive but unsupported claims. Greenness cannot prove exact crop identity, yield, pest absence, or farm income. A clean canopy can hide pest damage. A repeated winter dip can be normal fodder cutting. A moisture signal can reflect irrigation timing rather than permanent stress.

These limitations are not weaknesses to hide. They are the reason the report includes confidence, boundaries, and a watch section. A method that states what it can and cannot conclude gives the reviewer a stronger basis for responsible action.

The method is strongest when it is used for evidence of activity, continuity, trend direction, observation quality, rough field uniformity, and conservative risk signals. The next chapter explains how these method outputs become a structured land assessment and a lender-facing report.
