## 1.1 Background

Agriculture depends on land, climate, labour, timing, and finance. A farm can fail to produce not only because the farmer lacks skill, but also because working capital arrives late, the lender cannot verify the condition of the land, or the financing process depends on slow and uneven information. Agricultural credit therefore has a practical evidence problem: the lender needs to know whether the land appears active, whether the recent record is reliable, and whether the observed signals support further review.

Many agricultural finance workflows still depend on documents, verbal trust, collateral information, field visits, and reports that may arrive after important seasonal decisions have passed. These sources remain necessary. A field visit can observe local conditions that a satellite cannot see, and documents remain essential for legal and administrative review. The limitation is scale and continuity: one visit, photograph, or document does not always show whether vegetation activity has been consistent across the recent season.

This challenge is especially relevant where farms are small, crop calendars are seasonal, land parcels may be fragmented, and financing needs are tied to short planting and harvest windows. Remote sensing cannot replace local agronomic knowledge, farmer interviews, or formal land records, but it can help show whether a parcel displayed vegetation activity, whether the observation history has gaps, and whether the latest activity period appears strong, weak, interrupted, or uncertain.

FarmTrust is built around this evidence need. It uses satellite observations to support agricultural finance review by converting land boundaries and time-series imagery into a structured lender-facing assessment. The project does not attempt to automate lending decisions. It presents evidence in a form that a human reviewer can inspect, question, and combine with other sources.

## 1.2 Agricultural Finance Context

Agricultural lending differs from many other types of lending because the financed activity is biological, seasonal, and exposed to uncertainty. A crop may look weak during a normal pre-planting period, strong greenness may not prove profitable yield, and a low satellite index may represent recent harvest rather than crop failure. The time at which evidence is read is therefore as important as the evidence itself.

For lenders, the practical need is not a scientific map for its own sake. The need is a defensible summary that helps answer narrow but important questions: Does the land show recent vegetation activity? Is the observation record good enough to support that reading? Is the latest activity period aligned with the land's recent history? Are there evidence gaps or risk signals that should be reviewed by a person?

The Egyptian agricultural context makes these questions important. Agricultural land may be highly productive, but financing review can be slowed by fragmented records, field inspection logistics, and the cost of repeated monitoring. A scalable evidence tool can help lenders focus human attention where it is most needed and make review more consistent by applying the same reporting logic to submitted agricultural parcels.

## 1.3 Motivation

The motivation of FarmTrust is to transform raw satellite observations into a clear, careful, and finance-oriented report. A raw vegetation chart is not enough for this purpose. A lender-facing system must explain what was observed, what was inferred, how confident the assessment is, and what the system cannot know from satellite imagery alone.

![Figure 1.1: From satellite observations to finance-review evidence.](satellite_to_decisions.png){width=6.0}

Figure 1.1 summarizes the basic product idea. The system begins with a user-defined analysis polygon and repeated satellite observations. It prepares vegetation and moisture signals, studies activity over time, estimates evidence confidence, and produces a report that a lender can read. The figure is intentionally described as a decision-support path rather than an automated decision path, because FarmTrust is not a loan approval engine.

The project was also motivated by the risk of overclaiming. Satellite images can be persuasive, especially when displayed as colourful maps or smooth charts. However, a visually strong chart does not automatically prove crop identity, yield, income, pest status, legal ownership, or repayment ability. This project therefore treats language as part of the engineering problem: the report must be useful, but it must also say "the evidence suggests" where the evidence is suggestive and "not enough evidence" where the record is weak.

## 1.4 Project Contribution

FarmTrust contributes a practical satellite-to-report workflow for agricultural finance review. The contribution is not a new satellite mission, a new lending policy, or a universal crop model. It is a coherent platform design that connects public satellite data, field-level time-series analysis, conservative evidence modelling, and a bounded explanation assistant.

The first contribution is the transformation of satellite observations into land-level evidence. Sentinel-2 imagery is processed into signals that describe vegetation activity, moisture context, and observation quality across time rather than as isolated snapshots. The second contribution is a finance-oriented assessment structure: land status, recent trend, activity-window performance, risk signals, confidence, and limitations are organized around review questions rather than sensor bands.

The third contribution is claim discipline. FarmTrust avoids unsupported statements about yield, crop identity, pest damage, income, legal boundaries, or loan approval. The fourth contribution is a grounded explanation assistant that helps reviewers understand an already-computed report without inventing evidence or changing the assessment.

Table: Table 1.1: Main outputs of FarmTrust

| Output | Purpose for review | Boundary |
| --- | --- | --- |
| Land assessment summary | Gives a quick reading of recent activity, status, confidence, and caution areas | Does not approve or reject financing |
| Vegetation and moisture charts | Shows how the parcel changed across time | Does not prove yield or crop identity |
| Activity-cycle interpretation | Identifies rises, peaks, declines, and recent activity windows | Does not replace agronomic field inspection |
| Evidence-quality notes | Explains cloud gaps, weak observations, and confidence limits | Does not make poor data look certain |
| Bounded report assistant | Explains report content and answers report-based questions | Does not invent information outside the report |

## 1.5 Platform Scope

The current platform scope is a satellite-based land assessment and reporting system for agricultural finance support. A user defines or selects a land polygon. The system retrieves Sentinel-2 observations for the selected area and time period, prepares observation records, calculates field-level signals, analyses vegetation activity, and produces a lender-facing report.

The report is the primary output. It includes a concise status summary, recent trend, activity-window reading, evidence confidence, risk and limitation notes, charts, and explanations of what the system can and cannot conclude. The current implementation also includes a grounded explanation assistant. The assistant is bounded to the report: it can explain confidence, trends, and caution notes, but it is not the source of the assessment.

The project also includes research work around vegetation indices, smoothing, cycle detection, spatial interpretation, crop classification, and yield transfer. These studies informed the design choices of FarmTrust, but they are not all product features. Research results on crop classification and yield prediction are discussed as learning evidence, while the platform itself remains focused on land activity, evidence confidence, and lender-facing assessment.

## 1.6 Claim Boundaries

A central principle of this project is that the system must not claim more than its evidence can support. Satellite imagery provides repeated observation, but it does not directly observe every cause behind the signal. A drop in vegetation can come from harvest, fodder cutting, irrigation stress, cloud contamination, crop failure, or normal seasonal transition. A strong greenness signal can indicate active vegetation, but it does not automatically prove high income or low credit risk.

FarmTrust can support statements about observed greenness, relative moisture context, recent activity, activity-cycle shape, evidence gaps, and confidence. It cannot independently prove legal ownership, exact crop type, exact yield, pest diagnosis, farmer income, repayment ability, or final loan eligibility. Those decisions require other evidence and human responsibility.

These boundaries are design requirements, not disclaimers added at the end. A system that overstates satellite evidence may appear more powerful, but it becomes less trustworthy for finance. In a lending context, a careful "uncertain" can be more valuable than an unsupported confident answer.

[[PAGE_BREAK]]

## 1.7 Target Users

The primary users of FarmTrust are loan officers and agricultural finance analysts. These users need an efficient way to review land activity evidence before or during financing decisions. They may not have time to interpret raw satellite bands, but they can use a clear report that explains recent activity, confidence, and limitations.

A downstream user group may be portfolio managers. After financing, a portfolio manager may need to monitor financed lands and identify parcels where observation records show possible inactivity, unusual decline, or weak evidence. Other potential users include agribusinesses, development organizations, and public-sector agricultural programs. These uses are outside the first product focus, but they share the same need for scalable evidence in human review.

## 1.8 Document Organization

This graduation book is organized into ten chapters. Chapters 1 to 4 introduce the problem, background, objectives, scope, requirements, and analysis. Chapters 5 to 8 describe the system architecture, satellite data pipeline, evidence modelling approach, implementation, lender report, and bounded report assistant. Chapter 9 presents the case study, research findings, evaluation position, and limitations. Chapter 10 concludes the work and outlines future improvements.

The book distinguishes between the built FarmTrust platform and the team's research work. FarmTrust refers to the platform output: the assessment workflow, report, and explanation assistant. The research work refers to experiments, comparisons, and case-study analysis used to justify design choices and define honest product boundaries.
