## 9.1 Case Study Overview

This chapter is the main case study for the graduation project. It uses an agricultural parcel in El-Kom Al-Akhdar, Shebin El-Kom District, Menoufia Governorate, Egypt, as a worked example for evaluating how satellite evidence can support a lender-readable land assessment. The parcel is not presented as proof of national performance. It is useful because it contains the kinds of conditions a real reviewer must handle: repeated vegetation activity, uneven observation quality, within-parcel variation, and a winter pattern that requires local interpretation.

FarmTrust is the built platform that turns land evidence into a bounded report. The figures in this chapter come from the team's case-study analysis and research work; they explain the evidence behind the design and reporting choices. They should not be read as certified model outputs or as proof of crop identity, yield, income, ownership, or repayment ability.

The chapter answers seven practical questions: whether the land appears active, whether the observation record supports that reading, whether additional vegetation indices change the interpretation, whether smoothing preserves agricultural cycles, whether an independent phenology check supports the cycle boundaries, what spatial evidence adds, and how local context should affect report language.

[[PAGE_BREAK]]

Table: Table 9.1: Case-study questions and reporting discipline

| Question | Evidence used | Conservative reporting rule |
| --- | --- | --- |
| Is the land active? | Two-year greenness timeline and detected cycles | Report observed activity, not income or yield |
| Is the record reliable? | Quality and gap profile | Lower confidence when usable observations are sparse |
| Do other indices change the reading? | Vegetation-index comparison | Use them as context, not proof of hidden conditions |
| Is smoothing reasonable? | Smoothing rationale and cycle detector | Preserve agricultural cycles without following noise |
| Are cycle boundaries plausible? | Independent phenology cross-check | Treat agreement as support, not universal validation |
| Is the parcel spatially uniform? | Peak-greenness distribution | Describe variation cautiously on a small parcel |
| Does local context matter? | Cut-and-regrowth pattern | Avoid failure language without corroboration |

The central lesson is that a useful land report should be traceable without becoming overconfident. The case study shows strong evidence of agricultural activity, but it also shows why the report must separate observation from interpretation and confidence from risk.

## 9.2 Timeline Evidence and Activity Cycles

The primary signal is the greenness timeline. Greenness does not diagnose every agronomic condition, but it is a strong starting point because crop growth usually appears as a rise and fall in vegetation indices over time. For finance review, the timeline helps answer whether the parcel has recently shown vegetation activity, whether that activity repeats, and whether the latest activity resembles previous cycles.

![Figure 9.1: Two-year greenness timeline with detected activity cycles for the El-Kom Al-Akhdar parcel.](fig05_greenness_timeline.png){width=4.8}

The timeline shows repeated vegetation cycles rather than a static or abandoned surface. This supports an "active land" interpretation, but it does not turn the curve into a loan decision. Some cycle boundaries are supported by dense observations; others pass through weaker intervals and should be treated as approximate. A decline is also not automatically negative. Depending on timing and local context, it may represent harvest, cutting, grazing, field preparation, water limitation, or an observation issue.

This is why the report should use the timeline as evidence history, not as a final verdict. The strongest statement is that the declared parcel shows recent and repeated vegetation activity in the satellite record. The report should avoid stronger claims about yield, crop identity, income, or repayment ability.

[[PAGE_BREAK]]

## 9.3 Observation Quality and Evidence Confidence

Remote-sensing conclusions depend on observation quality as much as index values. Sentinel-2 scenes are affected by cloud, haze, shadow, timing, and mixed-edge pixels; sparse or cloudy intervals reduce certainty in timing, peak height, and cycle boundaries.

![Figure 9.2: Observation quality and gap profile for the El-Kom Al-Akhdar parcel.](fig06_quality_profile.png){width=4.8}

Report confidence alongside evidence: state repeated activity while flagging intervals with weaker observation support so reviewers can see where timing or peak estimates are less certain.

Table: Table 9.2: Evidence features and report effect

| Evidence feature | Case-study reading | Report effect |
| --- | --- | --- |
| Repeated rise-and-fall cycles | Recurring vegetation activity is visible | Supports active-land language |
| Clear peaks | Several intervals reach strong greenness highs | Supports seasonal activity review |
| Troughs between cycles | Lower-greenness periods appear between active intervals | Describe as transition, cutting, harvest, or bare-soil possibility |
| Short observation gaps | Main pattern remains readable | Mention interpolation or reduced certainty |
| Long cloudy intervals | Timing becomes less certain | Reduce confidence for affected dates |
| Edge-sensitive pixels | Values may mix field and non-field surfaces | Read small spatial differences cautiously |

This structure avoids two common errors: treating every point on the curve as equally reliable, or rejecting a useful two-year record because some observations are imperfect. The case study sits between those extremes.

## 9.4 Vegetation Index Comparison

NDVI is the primary, simple greenness signal; EVI, moisture, red-edge, and soil-adjusted indices add context. When multiple indices move together they increase confidence, but no index—or combination—proves pests, irrigation status, crop identity, or yield.

![Figure 9.3: Vegetation-index comparison during the case-study period for the El-Kom Al-Akhdar parcel.](fig07_vegetation_indices.png){width=4.8}

Summarize multi-signal relationships in plain language and avoid letting signal names substitute for transparent evidence and uncertainty statements.

Table: Table 9.3: Role of selected evidence signals

| Signal | Contribution | Remaining limit |
| --- | --- | --- |
| NDVI greenness | Main activity and cycle shape | Does not prove yield or crop identity |
| EVI context | Related canopy behavior | Does not diagnose all crop conditions |
| Moisture context | Relative water or canopy-moisture signal | Does not prove irrigation failure |
| Red-edge context | Extra canopy-vigor headroom | Does not prove pest or disease status |
| Soil-adjusted context | Helps when soil background matters | Does not replace field notes |

## 9.5 Smoothing and Activity-Cycle Detection

Satellite observations are uneven in time, and not every image is usable. The research work therefore transformed the observation record into a smoother daily curve so that agricultural cycles could be interpreted. This step must be conservative: weak smoothing follows noise and can create false small cycles, while excessive smoothing can erase real troughs between crop cycles.

The method choice shows why smoothing should reflect an agricultural timescale. Vegetation usually changes over weeks, not day-to-day jumps, but genuine management events can still happen within a season. A moderate phenology-scale smoother preserved the main activity cycles while reducing noise enough for stable reporting. The report should still make clear that the smooth daily curve is an interpretation of measured observations, not a claim that satellite values were observed every day.

## 9.6 Independent Phenology Cross-Check

The activity-cycle output was also compared with an independent phenology model. The purpose was not to replace the main detector, but to test whether a different modeling style identified the same broad seasonal structure. In the case-study parcel, the cross-check agreed with the main cycle count and aligned closely with peak timing.

![Figure 9.4: Independent phenology cross-check of detected activity cycles for the El-Kom Al-Akhdar parcel.](fig11_hmm_crosscheck.png){width=4.8}

This agreement supports the plausibility of the detected cycles, especially at peaks. It should not be overstated. One parcel does not validate the method across all crops, regions, parcel sizes, and cloud conditions. The correct conclusion is narrower: the selected cycle structure behaved reasonably on the main case study and can be presented as structured evidence with clear limitations.

## 9.7 Spatial Evidence and Within-Parcel Variation

A field-average timeline can hide variation inside the parcel. One area may green up earlier, remain more vigorous, or be cut before another area. Spatial peak greenness was therefore inspected to understand whether the parcel behaved uniformly or whether part of the field contributed differently to the average curve.

![Figure 9.5: Spatial distribution of cycle-peak greenness across the El-Kom Al-Akhdar parcel.](fig12_spatial_peaks.png){width=4.8}

The map shows that the field is not perfectly uniform at all times. This helps explain why an average curve may contain wide spreads or sharp transitions. However, the parcel is too small for precise zoning claims from satellite pixels alone. Edge mixture, strip management, and resolution limits can all affect the pattern. Spatial evidence should therefore be used as supporting context and, when material, as a reason to ask for field review rather than as a separate productivity score.

[[PAGE_BREAK]]

## 9.8 Cut-and-Regrowth Interpretation

The most important local lesson is the winter cut-and-regrowth pattern. A repeated greenness decline can look alarming if read without context. In a winter forage system, however, cutting followed by regrowth can be normal management. The field is not necessarily failing; it may be producing fodder, being cut, and then recovering.

![Figure 9.6: Winter cut-and-regrowth pattern observed in the El-Kom Al-Akhdar parcel.](fig13_cut_front.png){width=4.7}

The spatial sequence adds a second view of the same interpretation problem. Instead of treating the field as one average value, it shows a low-greenness strip moving across the parcel and then recovering. This pattern is more consistent with staged cutting and regrowth than with a whole-field collapse, but it should still be described cautiously because satellite pixels do not observe the farmer's management decision directly.

![Figure 9.7: Moving low-greenness strip during winter cut-and-regrowth in the El-Kom Al-Akhdar parcel.](fig10_cut_regrowth_sequence.png){width=4.8}

This example explains the difference between land risk and evidence limitation. A greenness dip may be a risk if it indicates sustained decline or failed recovery. The same dip may be normal if it is part of a repeated cut-and-regrowth sequence. Satellite greenness alone cannot identify the management decision with certainty, so the report should state the observed decline and recovery, describe the pattern as consistent with cutting when context supports it, and ask for field context if the distinction affects the finance review.

Table: Table 9.4: Case-study corrections to naive readings

| Naive reading | More careful interpretation | Report effect |
| --- | --- | --- |
| A winter dip means crop failure | It may be forage cutting followed by regrowth | Avoid failure language without corroboration |
| A late green-up means a problem | Planting or rotation timing may differ | Ask for crop-calendar context |
| A moving low-greenness band is noise | It may reflect staged cutting | Use spatial evidence as support only |
| Shape proves the crop | Shape narrows possibilities but does not prove identity | Use "consistent with" rather than "is" |

## 9.9 Selected Research and Development Comparisons

The research work included additional experiments that shaped the final boundaries of FarmTrust. These comparisons explain why the product focuses on evidence reporting rather than automatic crop, pest, yield, or loan decisions. They also show that several attractive ideas were rejected or deferred because the evidence was not strong enough for lender-facing claims.

Figure 9.8 is a season-to-season comparison plot. Unlike a single parcel-history chart, it aligns two corn seasons on the same summer calendar window so their curves can be compared directly. The vertical axis is a satellite index value. Solid lines show NDVI greenness, dotted lines show NDMI canopy-moisture context, and the gray and green colors separate the two seasons. The star markers show each season's NDVI peak. The shaded window marks the whorl/vegetative period when Fall Armyworm pressure would matter agronomically. The figure is used as a boundary example: both seasons reached high and fairly uniform greenness, so this satellite view did not show a clear Fall Armyworm fingerprint. It supports activity evidence, not pest diagnosis or proof that a pest problem was absent.

![Figure 9.8: Corn-season comparison of greenness and canopy-moisture signals during a Fall Armyworm risk window.](fig14_corn_season_comparison.png){width=4.6}

Table: Table 9.5: Research-only AOI crop-classification probabilities

| Parcel and known class | Class probabilities | Research outcome |
| --- | --- | --- |
| C1, corn | alfalfa 0.0002 / corn 0.9998 | Correct in this narrow check, high model probability |
| C3, corn | alfalfa 0.0081 / corn 0.9919 | Correct in this narrow check, high model probability |
| C4, alfalfa | alfalfa 0.5684 / corn 0.4316 | Correct in this narrow check, moderate model probability |

The direct AOI check showed that a narrow crop-classification path could work on the tested parcels. It did not prove that automatic crop identity was ready for FarmTrust. The alfalfa case was correct but much less confident, and the test set was too narrow to become a production claim.

The next comparisons ask a harder question: whether model strength survives changes in feature set and geography. The probabilities and metric values in this section are rounded for readable comparison, while the interpretation remains based on the underlying experiment records. This matters because a lender-facing system cannot rely on a result that only looks strong under one convenient validation setup.

Table: Table 9.6: Feature-set ablation in the crop-classification research

| Run | XGBoost macro-F1 | CatBoost macro-F1 |
| --- | --- | --- |
| Full research feature set available from the experiment inputs | 0.988 | 0.977 |
| No weather | 0.907 | 0.895 |
| Sentinel-2 and scene-classification only | 0.915 | 0.879 |

The ablation shows that the richer research feature set was strongest in the experiment, while optical imagery alone still carried useful crop signal. This is boundary-setting research evidence, not a reason to add automatic crop identity to the current lender report.

Table: Table 9.7: In-distribution and out-of-zone crop-classification validation

| Validation split | Macro-F1 | Note |
| --- | --- | --- |
| Random stratified split | 0.793 | Train/test parcels 6187 / 1547 |
| Leave-one-zone-out, el haouz best case | 0.580 | Best held-out-zone result |
| Leave-one-zone-out, Gharb worst case | 0.189 | Performance collapses out of zone |

This table is one of the strongest reasons for restraint. A random split makes the model look usable, but a harder geographic validation shows that performance can collapse. FarmTrust therefore treats crop classification as research progress rather than a dependable product feature.

Table: Table 9.8: Crop-model attempts and outcomes

| Attempt | Result | Verdict |
| --- | --- | --- |
| Binary LightGBM | Passed C1/C3 corn and C4 alfalfa check | Narrow demo success |
| Morocco XGBoost | Correct corn prediction, low confidence | Weak evidence only |
| Merged five-label model | Missing artifact and bands | Not runnable for the AOI |
| AOI five-label model | Wrong wheat prediction | Compatible, not separable |

The crop-model attempts show why execution success is not the same as scientific validation. A model can run and still be wrong, or it can be blocked because the required features are not available from the target AOI.

[[PAGE_BREAK]]

Table: Table 9.9: Yield-transfer predictions compared with the farmer-observed range

| Variant | Predicted whole-plot yield |
| --- | --- |
| Imagery-only baseline | 1113.2 kg |
| Timing-robust first pass | 1084.8 kg |
| Compact-soil variant | 1021.9 kg |
| No-raw-band timing-robust variant | 1014.8 kg |
| Direct-valid-pixel-free no-raw-band variant | 1032.3 kg |
| PLS regression appendix | 1065.7 kg |
| Farmer-observed range | 600-800 kg for a plot of about 1277.8 square meters, 0.1278 ha, or 0.304 feddan |

Every yield-transfer variant overpredicted the remembered whole-plot range. The result is useful because it is a negative scientific finding: the team did not treat a transferred yield model as good enough simply because it produced a number. For FarmTrust's current product scope, the correct product decision is to exclude yield estimation and use satellite evidence for activity, confidence, and review questions only.

## 9.10 Evaluation and Limitations

The case study supports the lender-report concept in four ways. It shows that satellite evidence can reveal repeated land activity, that observation quality can be exposed instead of hidden, that local interpretation affects the meaning of greenness changes, and that the system can present useful evidence while preserving the role of the human reviewer.

A second short-window parcel was used as a smaller diagnostic example. It is useful because it tests the same timing logic on a shorter record with one detected activity cycle rather than the four-cycle history of the main case-study parcel. The detector and the independent phenology check identified the same cycle count and the same peak date, while the end date differed by eleven days. This supports the idea that peak timing can be stable even when start and end boundaries remain approximate. The example does not validate the method universally; it shows how FarmTrust can expose timing agreement and timing uncertainty together.

![Figure 9.9: Short-window pipeline diagnostic showing one detected activity cycle and independent timing agreement.](fig15_short_window_pipeline_diagnostic.png){width=6.0}

Table: Table 9.10: Evaluation of the case-study report concept

| Evaluation dimension | Case-study result | Remaining limitation |
| --- | --- | --- |
| Evidence traceability | Claims connect to figures, tables, and observed patterns | Captions and text must remain disciplined |
| Activity assessment | Repeated vegetation cycles are visible | Activity does not prove yield or income |
| Confidence handling | Quality gaps are visible to the reviewer | Confidence depends on data availability |
| Local interpretation | Cut-and-regrowth can be explained cautiously | Ground notes are needed for stronger claims |
| Spatial context | Within-parcel variation can be inspected | Small maps can be over-read |
| Finance usefulness | The report can guide review questions | It does not make a loan decision |

The limitations are clear. The case study uses one main parcel, so it cannot establish performance across all Egyptian agricultural regions. It does not include systematic ground-truth visits across many parcels. It also depends on the user-defined AOI: if the polygon is shifted, too broad, or too narrow, the extracted signal may mix the target field with nearby land. Finally, satellite evidence cannot prove legal control, crop identity, yield, pest status, borrower income, or repayment capacity.

These limitations do not weaken the project when they are stated clearly. They show that FarmTrust is designed for responsible decision support. The proper conclusion is that satellite evidence becomes useful for finance review when it is structured, bounded, and paired with human judgement.

## 9.11 Chapter Summary

The El-Kom Al-Akhdar case study demonstrates the evidence logic behind FarmTrust. The timeline shows repeated vegetation activity; the quality profile shows where confidence should change; the index comparison explains why additional signals should remain contextual; the smoothing rationale supports a phenology-scale method; the independent cross-check supports the cycle structure; the spatial evidence adds useful within-parcel context; and the cut-and-regrowth pattern shows why local interpretation matters.

The chapter also explains why crop classification and yield estimation remain boundary-setting research topics rather than lender-report claims. The project's strongest contribution is narrower: a structured, traceable report that helps reviewers understand land activity and evidence limits without replacing financial judgement.
