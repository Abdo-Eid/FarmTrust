## 3.1 Problem Statement

Agricultural lenders need reliable evidence about land activity before and during financing review. Traditional review can depend on borrower documents, collateral information, trust relationships, field officer visits, and local knowledge. These sources are important, but they may not show whether a land parcel has displayed vegetation activity across time, whether the recent evidence is reliable, or whether the latest pattern deserves additional review.

The problem addressed by FarmTrust is the gap between available satellite imagery and usable lender-facing evidence. Sentinel-2 imagery is public and repeated, but the raw data is not directly usable by most finance reviewers. It must be retrieved, filtered, summarized, interpreted, and explained without turning uncertain observations into unsupported conclusions.

The project therefore asks how a satellite-based system can support agricultural finance review while remaining honest about its limits. The answer is not a single vegetation index, a map screenshot, or an automated credit score. The answer is a structured workflow that converts land boundaries and satellite time series into a confidence-aware assessment report.

This problem has three dimensions. The technical dimension is processing satellite observations into field-level evidence. The interpretive dimension is separating observed signals, inferred activity patterns, confidence limits, and unknown causes. The communication dimension is presenting that evidence in language that a lender can use without implying that the system makes the lending decision.

## 3.2 Research and Product Questions

The work is guided by questions that connect remote sensing, system design, and finance review.

1. How can Sentinel-2 observations be transformed into a field-level time series suitable for agricultural activity review?
2. How can vegetation and moisture signals be interpreted without claiming crop identity, yield, pest status, or income?
3. How can the system detect recent activity windows while preserving confidence limits caused by clouds, missing observations, and incomplete cycles?
4. How can a lender-facing report explain land activity evidence clearly to a non-specialist reviewer?
5. How can an explanation assistant answer follow-up questions without inventing information or making credit decisions?

These questions define FarmTrust as a decision-support system. The aim is not to replace lenders, agronomists, surveyors, or field officers. The aim is to give them a clearer and more consistent evidence base.

## 3.3 General Objective

The general objective of FarmTrust is to design and implement a satellite-supported land assessment platform for agricultural finance review. The platform should help a reviewer understand whether a selected land parcel appears agriculturally active, whether recent activity is visible, how reliable the observation record is, and what limitations remain outside the satellite evidence.

This objective is intentionally narrower than a full digital lending system. FarmTrust does not calculate repayment ability, approve loan applications, or replace institutional lending policy. It supports the evidence-gathering stage by producing a structured report that can be used together with borrower data, field notes, legal documents, and lender judgement.

[[PAGE_BREAK]]

## 3.4 Technical Objectives

The technical objectives focus on the complete satellite-to-report path. The platform must accept a user-defined AOI, retrieve relevant observations, transform them into interpretable signals, assess activity and confidence, and present the result in a report.

Table: Table 3.1: Technical objectives and expected outputs

| Objective area | Objective | Expected output |
| --- | --- | --- |
| Land definition | Represent the parcel as the area to be assessed | Clear analysis polygon |
| Observation retrieval | Use repeated Sentinel-2 observations for the selected land | Time-series evidence record |
| Observation quality | Identify gaps, weak observations, and reliability limits | Evidence-coverage notes |
| Signal calculation | Build vegetation and moisture indicators | Field-level activity indicators |
| Time-series reading | Smooth and structure the time series cautiously | Readable activity pattern |
| Activity detection | Identify recent vegetation activity windows and incomplete edges | Activity-cycle summary |
| Assessment | Produce status, trend, risk notes, and confidence | Lender-facing assessment |
| Explanation | Answer bounded questions over the report | Grounded report explanations |

These objectives are linked. A report cannot be trusted if the evidence record is weak. A confidence note cannot be meaningful if quality limitations are not recorded. An assistant cannot be safe if the report itself does not define what can and cannot be claimed.

## 3.5 User Objectives

The user objectives are centered on finance review. A loan officer or agricultural finance analyst should be able to open a report and understand the main evidence without needing to inspect raw satellite scenes. The report should answer practical questions while still exposing uncertainty.

The reviewer should be able to understand whether the parcel shows recent vegetation activity, whether the latest activity period appears strong or weak, whether the observation record contains important gaps, whether risk or caution signals deserve attention, and what the satellite evidence cannot prove. The report should help the reviewer decide whether to proceed with normal review, request additional field evidence, or treat the satellite evidence as insufficient.

A secondary objective is consistency. If two parcels are reviewed by the same system, the report structure should make comparison easier by presenting the same categories of evidence: status, trend, activity, confidence, risk, limitation, and explanation.

## 3.6 Assumptions

The project depends on assumptions that define how the system should be interpreted. The selected analysis polygon is assumed to be a reasonable representation of the parcel under review. If the polygon is wrong, too broad, or too narrow, the satellite summary may represent the wrong land or mix multiple land covers.

Sentinel-2 observations are assumed to be relevant to vegetation activity at the parcel scale, but not perfect. Cloud gaps, haze, mixed pixels, and small-parcel resolution can affect the evidence. The system therefore reports confidence and limitations rather than treating all observations as equally reliable.

Vegetation activity is assumed to be relevant to agricultural finance review, but it is not the only relevant factor. Borrower history, legal documents, repayment capacity, market conditions, and local agronomic knowledge remain outside the satellite-only assessment. The explanation assistant is also assumed to be useful only when grounded in the report; if a question goes beyond the report evidence, the assistant should narrow the answer or state that the report does not contain enough information.

## 3.7 Non-Goals

The non-goals protect the project from unsupported claims. FarmTrust is not a legal land-surveying system. It does not prove ownership, cadastral accuracy, or land tenure. It also does not replace field inspection when a lender requires physical verification.

FarmTrust is not a crop-identification or yield-estimation product in its current scope. The system may describe activity patterns that are consistent with agriculture, but it does not automatically declare the exact crop from satellite imagery alone. Greenness and activity can support interpretation, but yield depends on many factors that are not fully visible in satellite images.

FarmTrust is not a pest or disease diagnostic system. Some satellite patterns may raise caution, but they do not identify the cause of a problem by themselves. Finally, FarmTrust is not a loan approval system. It can support evidence review, but it should not approve, reject, price, or rank loan applications as a final decision.

Table: Table 3.2: In-scope and out-of-scope claims

| Area | In scope | Out of scope |
| --- | --- | --- |
| Land activity | Recent greenness, activity windows, trend, confidence | Exact crop identity, yield, income, pest status, or causal diagnosis |
| Observation quality | Cloud gaps, limited history, weak evidence | Making poor evidence appear certain |
| Risk support | Caution notes for review | Final credit risk decision |
| Agronomic meaning | Conservative interpretation of patterns | Pest diagnosis or exact cause |
| Finance use | Decision-support report | Loan approval or rejection |
| Explanation assistant | Report-based answers | New scores or invented evidence |

## 3.8 Success Criteria

The project is successful if it produces a clear and coherent land assessment workflow that can be understood by a finance reviewer and defended by the available evidence. Success is not measured by making the boldest claim. It is measured by whether the platform presents useful evidence while respecting its boundaries.

The first criterion is evidence traceability: the report should connect assessments to visible charts, activity notes, and confidence explanations. The second is claim discipline: the system should avoid unsupported statements about yield, crop identity, pest status, income, ownership, or credit approval. The third is usability: a non-specialist lender should be able to read the report without becoming a remote-sensing expert. The fourth is completeness: the workflow should cover area definition, data, analysis, report, and explanation. The final criterion is grounded explanation: the assistant should help users understand the report without creating new assessments.

## 3.9 Decision-Support Scope

FarmTrust is best understood as a decision-support platform. Decision support means that the system informs a human process without taking responsibility for the final decision. This distinction is important because agricultural finance involves financial, legal, social, and agronomic factors that cannot be reduced to a satellite time series.

In practice, the platform can help a lender prioritize attention. A parcel with clear recent activity and good evidence coverage may proceed through the normal review path. A parcel with weak land-activity signals may need field follow-up, while a parcel with poor satellite coverage may need additional evidence before any conclusion is drawn. This keeps land-risk language separate from evidence-limitation language.

Confidence is central to this scope. High confidence means the observation record supports the statement more strongly. Low confidence means the reviewer should not depend heavily on the satellite evidence alone.

## 3.10 Project Limitations

The current implementation is limited by satellite revisit timing, cloud gaps, mixed pixels, AOI accuracy, small-parcel resolution, and limited validation coverage. These limits are expected in satellite-based land assessment and are addressed through reporting rather than hidden.

The project is also limited by the absence of complete ground-truth data for all possible crops, seasons, and regions. Case-study evidence can demonstrate the logic of the method and reveal important interpretation lessons, but it cannot prove universal performance. For this reason, the book reports research findings as evidence for design choices, not as universal validation.

Finance outcomes are not determined by land activity alone. A parcel may show active vegetation while the borrower still has credit risk for reasons outside satellite observation. Conversely, a weak satellite record may result from cloud gaps or a normal seasonal transition rather than a weak borrower. These limitations define where FarmTrust is useful: it makes land activity evidence clearer, faster to review, and more disciplined, but it does not substitute for human judgement, field evidence, or institutional credit policy.
