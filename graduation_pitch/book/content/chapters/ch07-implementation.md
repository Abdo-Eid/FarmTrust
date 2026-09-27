## 7.1 Evidence Modeling Overview

After the satellite pipeline detects vegetation activity cycles, FarmTrust must decide how to turn technical outputs into a report that a financing reviewer can understand. This is the role of evidence modeling. Evidence modeling is the bridge between measured signals and lender-facing language.

The design goal is not to make the report sound more certain than the data allows. The design goal is to make each conclusion auditable. A statement in the report should belong to one of four reader-facing groups: observed evidence, interpreted meaning, confidence, or watch items.

![Figure 7.1: Four-part evidence read used in the assessment report.](fig03_evidence_read.png){width=6.0}

The evidence model is also where FarmTrust's claim discipline becomes practical. A strong greenness curve can support a statement about canopy activity. It cannot, by itself, support yield, pest absence, income, repayment likelihood, or a loan decision.

## 7.2 Activity Cycles as the Main Evidence Unit

FarmTrust uses vegetation activity cycles as the main evidence unit because agricultural land is dynamic. A single vegetation value can be high or low for many reasons: planting stage, harvest, fodder cutting, cloud contamination, irrigation timing, bare soil between cycles, or a true decline. A cycle gives context by showing a rise, a peak, and a decline over time.

The system records the number of detected cycles, whether each cycle is complete or open, the peak timing, the peak greenness, the duration, and supporting quality information. These records support statements such as "the land showed recent vegetation activity" or "the available history is limited." They do not support crop identity unless the user separately provides that context.

Table: Table 7.1: Activity-cycle evidence fields

| Evidence field | What it supports | What it does not prove |
| --- | --- | --- |
| Cycle count | Repeated vegetation activity | Crop rotation by itself |
| Peak timing | Calendar pattern | Exact crop identity |
| Peak greenness | Canopy-strength signal | Yield or income |
| Open or complete state | Boundary certainty | Future performance |
| Gap overlap | Confidence adjustment | Farmer behavior |
| Within-field spread | Possible spatial variation | Cause of variation by itself |

An activity cycle is therefore a conservative unit. It describes a pattern that satellite data can observe reasonably well without pretending to know every agronomic cause behind the pattern.

## 7.3 From Signals to Report Statements

The report does not simply print every metric produced by the pipeline. A lender-facing report must select and organize evidence. FarmTrust therefore maps pipeline outputs into a smaller set of statement types.

Observed statements describe what the satellite record supports directly: usable observations, vegetation activity, index behavior, cycle count, dates, gaps, and spatial spread. Interpreted statements describe cautious meaning derived from those observations: recent activity, limited history, possible watch conditions, or uncertainty caused by weak evidence. Confidence statements explain why the system is more or less certain. Watch statements highlight items that deserve manual attention without turning them into hard claims.

This structure helps a reviewer read the report at two speeds. At a quick speed, the reviewer can scan the headline, confidence, and watch items. At a careful speed, the reviewer can inspect which observed evidence supports each interpretation. The same structure also helps the assistant because it gives generated explanations a strict evidence map.

## 7.4 Land Status, Trend, and Latest Performance

The land assessment combines activity-cycle evidence into three main statements: land status, trend, and latest activity-window performance. Land status describes whether the interval shows active, intermittent, inactive, or uncertain behavior. Trend describes whether the available history appears improving, stable, declining, or uncertain. Latest performance describes whether the latest usable activity window is good, interrupted, weak, or provisional.

These labels are conservative. One recent good cycle can support an active status, but it does not prove a stable long-term track record. A short observation window can show activity but still leave trend uncertain. Similarly, a weak or interrupted activity window may deserve attention, but it should not automatically become a high-risk financing decision.

Table: Table 7.2: Assessment vocabulary and meaning

| Output | Reader-facing meaning | Safety rule |
| --- | --- | --- |
| Land status | Interval-level activity pattern | Never based on one latest point alone |
| Trend | Direction across activity cycles | Uncertain if history is too short |
| Latest performance | Quality of the latest detected cycle | Provisional if the cycle is still open |
| Risk tier | Decision-support summary | Not an automated lending decision |
| Assessment confidence | Reliability of the assessment | Not confidence in profit or repayment |

The vocabulary intentionally avoids words that sound like full underwriting decisions. A parcel can be "active" without being a good loan case, and a trend can be "stable" without proving future income.

## 7.5 Absence Gate and Inactivity Claims

Inactivity and abandonment are especially sensitive claims. A lack of observed vegetation can be caused by cloud gaps, a short window, recent harvest, bare soil between cycles, or true absence of cultivation. FarmTrust therefore uses an absence gate before making inactivity statements. The absence gate asks whether the system has enough evidence to support a cautious absence claim.

If activity is present, the report says so. If activity is not visible but the evidence is weak, the report should say that absence is uncertain rather than labeling the land inactive. If evidence is insufficient, the safest action is to lower confidence or request manual review. This protects the lender from overreacting to missing satellite evidence and protects the landowner from being penalized for data gaps.

The absence gate is a good example of the platform's wider reasoning style. The system should not reward itself for being decisive. It should be decisive only when evidence supports decisiveness. In many cases, the correct assessment is not "good" or "bad"; it is "visible activity exists," "history is limited," or "manual review is needed."

## 7.6 Risk Flags and Evidence Limitations

The system distinguishes land risk from evidence limitation. Land risk flags describe possible concerns in the land signal, such as persistent weak vegetation, possible water-related issues, or land-use change indicators. Evidence limitations describe limitations in the satellite record, such as long gaps, sparse observations, unclear boundaries, or open activity windows.

This split is important because both can lead to caution, but they imply different next steps. A land risk flag may lead the reviewer to inspect the case more closely. An evidence limitation may lead the reviewer to wait for more observations, review another time window, or supplement the satellite report with field knowledge. Mixing these categories would make the report less fair and less actionable.

Table: Table 7.3: Risk vs evidence limitation

| Category | Example | Appropriate reviewer response |
| --- | --- | --- |
| Land risk | Repeated weak vegetation signal | Inspect evidence and request explanation |
| Land risk | Possible water-related persistence | Review timing and local irrigation context |
| Evidence limitation | Long cloudy gap | Lower confidence or wait for more data |
| Evidence limitation | Short history | Avoid strong trend claims |
| Evidence limitation | Open latest activity window | Treat latest performance as provisional |

This distinction also supports clearer report writing. The report should not say that a cloudy period is a risk in the land; it should say that the evidence is limited by clouds. These differences make the report more defensible.

## 7.7 Confidence and Grounding Levels

Confidence in FarmTrust means confidence in the assessment, not confidence in the borrower, future income, or repayment. The confidence label answers a specific question: how strongly does the satellite evidence support the report statement? This is a narrower and safer meaning than general financial confidence.

The report also benefits from grounding levels. Some statements come from direct observation, such as usable observation dates or vegetation index behavior. Some statements are model-derived, such as smoothed cycle boundaries. Some are interpretations, such as "recent activity is visible." Some are limitations, such as "yield cannot be estimated." Keeping these levels separate helps the reviewer understand how strong each statement is.

This approach is especially important for the report assistant. If a user says that the crop was wheat, the assistant may reason with that declared context, but it should not rewrite the satellite evidence as if the platform itself proved wheat.

## 7.8 Grounded Assessment Report

The grounded assessment report is the structured report object used by the portal, downloadable report, and explanation assistant. It reorganizes the assessment into a human-readable evidence read. The report has a headline, a list of evidence statements, an activity record, a track-record view, a split risk register, cautious indicators, limitations, and a boundaries section.

The boundaries section is deliberately explicit. It tells the reader what the satellite assessment does not claim: it does not approve or reject a loan, prove legal ownership or exact boundaries, estimate yield or income, diagnose pests, or automatically identify crop type. These boundaries make the system more useful, not less useful, because they tell the reviewer how to use the report responsibly.

Table: Table 7.4: Report evidence structure

| Report part | Purpose |
| --- | --- |
| Observed | Directly supported satellite and time-series facts |
| Interpreted | Conservative meaning derived from the evidence |
| Confidence | Why the assessment is high, medium, low, or uncertain |
| Watch | Items that deserve review without becoming hard claims |
| Boundaries | What the report cannot conclude |

The report is also designed to be readable without the assistant. The assistant can explain, but the report itself must remain complete and inspectable.

## 7.9 Independent Phenology Cross-Check

The project also used an independent phenology cross-check during research. The cross-check recovered matched cycle counts and close peak timing on the reference parcels, which increased confidence that the deterministic activity-cycle detector was not simply producing arbitrary boundaries. However, this result is reported honestly: two parcels are not enough to prove general validity.

![Figure 7.2: Independent phenology cross-check for the El-Kom Al-Akhdar parcel.](fig11_hmm_crosscheck.png){width=4.6}

Table: Table 7.5: Deterministic detector compared with an independent phenology cross-check

| Agreement metric | Demo AOI parcel | Second land parcel |
| --- | --- | --- |
| Detector cycles | 4 | 1 |
| HMM cycles | 4 | 1 |
| Matched cycles | 4 | 1 |
| Mean start-of-season difference | 2.75 days | 1.0 day |
| Mean peak difference | 0.0 days | 0.0 days |
| Mean end-of-season difference | 9.5 days | 11.0 days |
| Lifecycle agreement | 1.0 | 1.0 |

The production design keeps the deterministic detector as the main method and treats the independent cross-check as research evidence. It is useful for evaluation and method confidence, but it does not rewrite the assessment or serve as universal validation.

## 7.10 Spatial Evidence

Some evidence is temporal, and some is spatial. The strongest current spatial evidence comes from field-level peak maps and within-field spread statistics. These can show whether a field behaved uniformly or whether certain zones appeared weaker or stronger. Spatial evidence is useful, but it must be handled carefully on small parcels because a small field may contain only a limited number of satellite pixels.

![Figure 7.3: Spatial map of cycle-peak greenness across the El-Kom Al-Akhdar parcel.](fig12_spatial_peaks.png){width=4.4}

For this reason, FarmTrust treats field-mean time series as the backbone and spatial maps as supporting context. A patchy map can suggest where to look, but it should not become a standalone conclusion about crop type, yield, or management quality. In small fields, spatial evidence is best read as a prompt for review rather than as a precise map of agronomic causes.

Spatial evidence is still valuable because it can reveal patterns that a single mean curve hides, such as weaker zones, moving cutting patterns, or mixed management. The report should present these patterns as context and watch items, not as complete explanations.

## 7.11 Summary

Evidence modeling is where FarmTrust becomes more than a vegetation chart. The system turns satellite time series into a cautious assessment by using activity cycles, confidence rules, absence safeguards, split risk categories, explicit grounding levels, and report boundaries. This structure makes the output suitable for agricultural finance review because it is useful, readable, and honest about uncertainty.

The next chapter explains how this evidence model appears in the implemented portal, lender report, and bounded report explanation assistant.
