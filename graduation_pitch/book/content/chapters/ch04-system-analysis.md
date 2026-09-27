## 4.1 System Analysis Overview

System analysis defines what FarmTrust must do, who it serves, what information it requires, and what boundaries protect it from unsupported use. The platform is designed as a lender-facing land assessment system rather than a general agricultural dashboard. This distinction affects the actors, workflows, requirements, and report language.

The system begins with a land parcel and a finance-review question. It gathers satellite evidence, prepares time-series indicators, interprets recent activity, estimates confidence, and presents a report. The reviewer uses the report as one input in a wider decision process. The system does not approve a loan, prove ownership, or diagnose the exact agronomic cause of every pattern.

The analysis in this chapter covers actors, use cases, functional requirements, non-functional requirements, data constraints, assistant requirements, escalation logic, and system limits.

[[PAGE_BREAK]]

## 4.2 Actors and Stakeholders

FarmTrust has a primary actor and several supporting stakeholders. The primary actor is the lender-side reviewer who needs a clear evidence report. Other stakeholders may use the output or influence the workflow, but the first product story remains centered on agricultural finance review.

Table: Table 4.1: Actors and stakeholder needs

| Actor or stakeholder | Main need | FarmTrust support | Boundary |
| --- | --- | --- | --- |
| Loan officer | Review a land parcel during credit assessment | Reads the land assessment report and confidence notes | Does not receive an automatic approval decision |
| Agricultural finance analyst | Understand activity evidence and limitations | Reviews charts, trends, risk notes, and observation quality | Must combine the report with other credit evidence |
| Portfolio manager | Monitor financed lands for follow-up attention | Uses consistent report categories across parcels | Does not treat satellite evidence as the only monitoring source |
| Field officer | Decide where physical inspection may be needed | Uses caution notes and weak-evidence flags | Confirms local causes on the ground |
| Borrower or farmer | Provide context about land use and season | May explain crop rotation, cutting, irrigation, or timing | Does not control the satellite evidence itself |
| Platform operator | Maintain users, access, and operational settings | Supports platform operation | Does not change evidence interpretation manually |

This actor structure reflects a responsible workflow. The system helps reviewers and field officers decide where attention is needed, while final finance judgement remains with the institution. It also acknowledges that farmers may hold local knowledge that satellite data cannot infer on its own.

[[PAGE_BREAK]]

## 4.3 Core Use Cases

The main use cases are organized around a land assessment review. A reviewer selects or receives a parcel, generates an assessment, reads the report, asks bounded questions, and decides what human follow-up is appropriate.

Table: Table 4.2: Core use cases

| Use case | User goal | System behaviour | Expected result |
| --- | --- | --- | --- |
| Define parcel for review | Identify the land to be assessed | Accepts a user-defined AOI as the assessment area | A clear area is available for satellite analysis |
| Generate land assessment | Convert satellite observations into review evidence | Retrieves observations, prepares indicators, and analyses activity | A lender-facing report is produced |
| Inspect activity history | Understand whether land appears active over time | Presents vegetation history, activity windows, and recent trend | Reviewer sees activity pattern and confidence |
| Review evidence quality | Decide whether the satellite record is strong enough | Shows observation coverage, gaps, and quality limitations | Reviewer understands how much weight to place on the report |
| Review risk and limitation notes | Identify issues needing attention | Highlights caution areas without claiming final causes | Reviewer can request follow-up when needed |
| Ask report questions | Clarify technical report content | Assistant answers from the report evidence | Reviewer receives grounded explanation |
| Escalate to field review | Use satellite evidence to guide human work | Report indicates uncertainty or caution signals | Field officer or analyst follows up outside the system |

These use cases show that FarmTrust is a workflow tool, not only a data-processing tool. Its value appears when the output helps a reviewer move from raw evidence to a clearer human decision process.

## 4.4 Review Workflow

The review workflow starts when a lender or analyst needs to assess an agricultural parcel. The analysis polygon is defined or selected. The system retrieves satellite observations for the relevant period and prepares the evidence record. Observations affected by cloud, weak quality, or missing coverage are handled carefully because they influence confidence.

The system then calculates vegetation and moisture indicators and studies their behaviour across time. The aim is to identify recent activity, trend, and activity-cycle characteristics without overstating the cause of each movement. The assessment is organized into a report that the reviewer reads in a practical order: summary, charts and evidence notes, risk and limitation notes, and optional assistant explanation.

The workflow ends outside the system. The reviewer may accept the satellite evidence as supportive, request additional documents, ask for a field visit, or mark the satellite record as insufficient. FarmTrust supports this judgement but does not replace it.

## 4.5 Functional Requirements

Functional requirements describe what the platform must do from the user's point of view. Because FarmTrust is a finance-support system, the requirements are organized around evidence preparation, report generation, and responsible explanation.

Table: Table 4.3: Functional requirements

| Requirement area | Requirement | Description |
| --- | --- | --- |
| Parcel definition | The system shall assess a selected user-defined AOI | The AOI must be the spatial basis for all evidence and reporting |
| Satellite retrieval | The system shall use repeated Sentinel-2 observations | The report must be based on a time series rather than a single image |
| Observation screening | The system shall identify weak or missing observations | Cloud gaps and limited evidence must influence confidence |
| Indicator calculation | The system shall calculate vegetation and moisture signals | Indicators must support activity and context interpretation |
| Time-series analysis | The system shall study activity over time | The report must describe recent trend and activity windows |
| Confidence assessment | The system shall expose evidence strength and uncertainty | Reviewers must know when the satellite record is strong or weak |
| Risk and limitation notes | The system shall identify caution areas | Notes must support review without diagnosing unsupported causes |
| Report generation | The system shall produce a lender-facing assessment report | Output must be understandable to non-specialist finance users |
| Report explanation | The system shall answer bounded questions over the report | The assistant must explain report evidence without creating new claims |
| Human review support | The system shall support follow-up decisions | Output should help decide when field or document review is needed |

These requirements deliberately avoid automatic approval or rejection. The system is successful when it improves the quality and consistency of review, not when it makes the final credit decision.

## 4.6 Report Content Requirements

The report is the central user-facing artifact. It must be concise enough for a lender to read, but complete enough to show why the assessment was made. A report that only gives a status label is not sufficient. A report that only gives technical charts is also not sufficient. The report must connect summary, evidence, confidence, and limitations.

The assessment summary should present land status, recent trend, and confidence in plain language. The evidence section should show vegetation and moisture history with explanatory text so that a non-specialist user can understand what the charts represent. The recent-activity section should describe the latest relevant activity window and mark incomplete or weak evidence clearly.

The risk and limitation section should separate caution signals from evidence limitations. A caution signal may indicate unusual decline, weak recent activity, or an interrupted pattern. An evidence limitation may indicate cloud gaps, limited history, small parcel size, or AOI uncertainty. These categories should not be mixed, because a weak observation record is not the same as weak land performance.

The report should also include explicit non-claims. It should explain that the system does not prove crop identity, yield, pest status, income, cadastral validity, or loan eligibility. This discipline keeps the report useful without making it misleading.

[[PAGE_BREAK]]

## 4.7 Non-Functional Requirements

Non-functional requirements describe how the system should behave. For FarmTrust, usability, reliability, transparency, maintainability, and security are especially important because the output may influence finance review.

Table: Table 4.4: Non-functional requirements

| Quality area | Requirement | Reason |
| --- | --- | --- |
| Usability | Reports should be readable by non-specialist finance users | The target user may not understand remote-sensing terminology |
| Transparency | Evidence, confidence, and limitations should be visible | The reviewer must understand why the system reached its assessment |
| Reliability | The system should handle missing or weak satellite records gracefully | Cloud gaps and limited observations are normal in remote sensing |
| Maintainability | The workflow should be structured so methods can improve over time | Future work may add better validation, screenshots, or models |
| Performance | Report generation should be practical for review workflows | Users should not wait unnecessarily for routine assessment |
| Security | User and review data should be protected | Finance-related review data can be sensitive |
| Consistency | Similar evidence should be reported using similar language | Lender workflows require comparable review standards |
| Explainability | Assistant responses should stay grounded in the report | Language-model output must not create unsupported conclusions |

The most important non-functional requirement is not speed alone. It is trustworthiness. A fast report is not useful if it is unclear or overconfident. FarmTrust must therefore balance performance with traceability and caution.

[[PAGE_BREAK]]

## 4.8 Data Constraints

The quality of the assessment depends on the quality of the input data. A satellite-based system is constrained by parcel geometry, observation availability, atmospheric conditions, sensor resolution, and the length of the historical record.

Table: Table 4.5: Data constraints and expected handling

| Constraint | How it can affect assessment | Required handling |
| --- | --- | --- |
| Cloud cover | Reduces usable observations and creates gaps | Lower confidence and report evidence gaps |
| Small parcel size | Increases sensitivity to mixed pixels and AOI errors | Report parcel-size and AOI limitations where relevant |
| Inaccurate AOI | Summarizes the wrong area or mixes neighbouring land | Treat AOI accuracy as a review dependency |
| Short history | Makes trend and cycle reading less reliable | Mark limited history and avoid strong conclusions |
| Missing recent observations | Weakens latest activity assessment | State that recent evidence is incomplete |
| Mixed management | Can create complex spatial and temporal patterns | Use cautious language and request local context |
| Seasonal transition | Low greenness may be normal after harvest or before planting | Avoid interpreting low values as failure by default |

These constraints explain why confidence is essential. A report should not show the same level of certainty for every parcel. When the evidence is weak, confidence must fall and the language must become more cautious.

## 4.9 Assistant Requirements

The report assistant is part of the user experience, but it is not the authority that creates the assessment. Its purpose is to explain the report and help the reviewer understand technical content.

The assistant should answer questions about what the report says, what the charts mean, why confidence is limited, and what the risk notes imply. It should explain terms such as vegetation index, activity window, observation gap, and confidence. It may also help the reviewer understand why field confirmation or borrower context could be reasonable when evidence is weak.

The assistant should not approve or reject a loan. It should not invent crop identity, estimate yield, diagnose pests, or create new risk scores. If the user asks a question that requires information outside the report, the assistant should state that the report does not contain enough evidence and point back to the available information.

## 4.10 Review and Escalation Logic

A finance-support system should help users decide what to do next without turning the report into an approval engine. FarmTrust supports three broad evidence outcomes.

The first outcome is supportive evidence. If the parcel shows clear recent activity and the observation record is strong, the report can support normal finance review. This does not mean approval. It means the satellite evidence does not raise a major activity concern.

The second outcome is follow-up needed. If the parcel shows weak activity, unusual decline, poor recent evidence, or conflicting signals, the report can suggest that a human reviewer request additional evidence, such as a field visit, borrower explanation, recent photographs, or agronomic notes.

The third outcome is insufficient satellite evidence. If the record is too cloudy, too short, or too uncertain, the report should not force a conclusion. The responsible output is to state that satellite evidence is limited and that other review sources are needed.

## 4.11 System Limits

The system has limits that must remain visible to users. It cannot determine legal land ownership, prove the exact crop, estimate harvest quantity, diagnose pests or disease, verify farmer income, or assess repayment ability. It cannot turn a satellite chart into a full credit decision.

The system is also limited by the available observation period. A parcel may have been active before the selected time window or may become active after the latest available image. A recent cloudy period can hide meaningful changes. A field may be temporarily bare after harvest and still be part of normal productive agriculture.

These limits are the reason FarmTrust is designed as a transparent report rather than a black-box decision. A responsible system should know when to speak and when to state uncertainty.

## 4.12 Summary

The system analysis shows that FarmTrust must serve a finance-review workflow rather than a generic mapping workflow. Its primary users need clear land activity evidence, confidence, risk notes, and limitations. Its main use cases begin with parcel definition and end with human review decisions outside the platform.

The functional requirements focus on satellite observation, time-series analysis, assessment, report generation, and bounded explanation. The non-functional requirements emphasize usability, transparency, reliability, maintainability, security, consistency, and grounded explanation. The data constraints explain why confidence and cautious language are required.

Together, these requirements define FarmTrust as a lender-facing decision-support platform. It is valuable because it turns repeated satellite observations into structured evidence while preserving the human responsibility and local context required for agricultural finance.
