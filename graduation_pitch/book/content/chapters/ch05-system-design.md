## 5.1 Design Overview

FarmTrust is designed as a satellite-to-report platform for agricultural finance review. The design begins with a user-defined AOI, transforms public satellite observations into time-series evidence, and presents the result as a lender-facing farm risk report. The platform is not a general crop-management application and it is not a loan-decision engine. Its purpose is narrower: to help a reviewer understand whether a submitted parcel shows recent agricultural activity, how strong the satellite evidence is, what limitations affect the assessment, and what follow-up questions should remain open.

The design problem is therefore both technical and communicative. The technical side must retrieve satellite imagery, prepare usable signals, identify activity patterns, and preserve enough intermediate evidence for review. The communicative side must prevent the output from becoming more confident than the evidence allows. A chart can look persuasive even when observation gaps exist. A report can sound decisive even when the system only has a medium-confidence signal. A language assistant can sound authoritative even when it is only explaining a grounded assessment report. The architecture is built to control these risks.

The system follows five connected responsibilities: the portal captures the land polygon and analysis state; the backend stores the land record and coordinates the job; the worker retrieves imagery, prepares signals, detects activity cycles, and computes the assessment; the report layer turns that assessment into a structured evidence summary; and the report explanation assistant explains the same summary without creating new assessment facts.

![Figure 5.1: System architecture of the FarmTrust platform.](fig01_system_architecture.png){width=6.0}

The main architectural decision is the separation between evidence creation and evidence explanation. The processing pipeline creates the assessment. The report and assistant consume it. This prevents the language-model component from becoming a hidden scoring engine, keeps the land assessment reproducible, and gives the reviewer a stable report even when the assistant is unavailable.

## 5.2 System Context and Review Actors

The platform is built around a reviewer who needs a concise but inspectable view of an agricultural parcel. In an agricultural finance workflow, the reviewer may need to compare many cases, identify which parcels deserve manual follow-up, and explain why a case looks active, uncertain, or limited. The reviewer does not need a raw satellite workstation. The reviewer needs a shaped report that separates evidence from interpretation.

FarmTrust also has a second audience: the technical reviewer of the graduation project. For this audience, the platform must show a coherent chain from area definition to satellite data, from satellite data to activity evidence, and from activity evidence to cautious finance-review language. This is why the architecture preserves intermediate artifacts and keeps the output vocabulary strict.

The landowner or applicant is not the direct operational user in the current build. The system does not collect a full farm application, field-visit record, repayment history, or legal ownership proof. It focuses on the satellite-evidence part of a broader review. This boundary matters because it prevents the project from implying that satellite time series alone can replace financial underwriting or legal verification.

## 5.3 Architectural Principles

Three principles guided the design.

1. Evidence before interpretation.
2. Conservative claims before persuasive wording.
3. Inspectable artifacts before hidden processing state.

The first principle means that the platform records observation quality, vegetation signals, smoothed analysis curves, detected activity cycles, assessment confidence, and risk flags as distinguishable stages. The reviewer should be able to ask what evidence a statement depends on: observed satellite record, model-derived interpretation, or confidence limitation.

The second principle protects the project from overclaiming. FarmTrust supports a lender's review, but it does not approve loans, predict yield, diagnose pests, identify exact crop type from satellite data alone, estimate income, or perform legal surveying. These boundaries shape the whole architecture, not only the final wording.

The third principle makes the platform easier to audit. A system that only stores a final label is difficult to inspect when the result is surprising. FarmTrust instead keeps separate evidence stages so a reviewer or developer can trace a result back through observation quality, time-series construction, activity detection, and report wording.

[[PAGE_BREAK]]

Table: Table 5.1: Main system responsibilities

| Responsibility | Main role | Output |
| --- | --- | --- |
| Portal | Capture user-defined AOI and display review surfaces | Land submission, summary, evidence views |
| Backend service | Validate requests and coordinate jobs | Land records, job state, report data |
| Analysis worker | Run satellite and time-series processing | Assessment artifacts and metrics |
| Report layer | Project assessment evidence into a lender format | Grounded assessment report |
| Explanation assistant | Explain the report in bounded language | Narration and question answers |

## 5.4 Component Architecture

The portal is a focused operational interface. Its role is to collect a user-defined AOI, display processing state, and present the assessment in a way that a financing reviewer can scan. It does not perform the satellite method in the browser, which keeps evidence generation consistent and allows the interface to evolve without changing the method.

The backend service is the coordination boundary. It accepts the land submission, validates the request, records the job state, and provides shaped report data to the portal. This protects the frontend from internal processing details while keeping the reviewer-facing contract understandable.

The analysis worker is the evidence generator. It handles the remote-sensing workflow: finding usable observations, extracting field-level signals, applying quality rules, producing the analysis curve, detecting activity cycles, and computing the assessment. The worker is intentionally separate from the report assistant, so generated explanation cannot quietly change the assessment result.

The report layer is the presentation boundary. It takes the computed assessment and organizes it into a structured report: observed evidence, interpretation, confidence, watch items, risk drivers, limitations, and boundaries. The report layer does not add new satellite facts. It converts existing evidence into a lender-readable shape.

The explanation assistant is an optional explanation layer. It reads the report and answers questions about it. It may make the report easier to understand, but it does not become a decision engine. This placement is a deliberate safety choice. In a finance-related system, language generation should explain evidence, not replace the evidence.

## 5.5 End-to-End Data Flow

The end-to-end flow starts when a user defines an analysis polygon. The platform stores the polygon, searches for satellite observations, builds a field-level observation record, calculates indicators, screens observations for usability, smooths the irregular time series, detects activity cycles, derives a land assessment, and publishes a grounded report. The same report then feeds the summary screen, evidence view, downloadable document, and assistant surface.

![Figure 5.2: End-to-end data flow from analysis polygon to lender report.](fig02_data_flow.png){width=6.0}

This flow is intentionally staged rather than collapsed into one opaque process. Each stage has a clear input and output: analysis polygon, observations, indicators, smoothed curve, activity windows, assessment, and report. This structure makes the report easier to audit when the result is surprising.

The direct staged flow is appropriate for the current graduation-project build. It is easier to validate than a fully distributed production system and gives the team a stronger basis for explaining the method. A larger deployment could later introduce cloud storage, job queues, retry policies, access-control roles, and monitoring dashboards. Those additions would improve operational scale, but they would not change the central design rule: the report should remain grounded in inspectable evidence.

## 5.6 Data Contracts and Artifact Strategy

FarmTrust uses structured handoffs between the major components. The portal submits a user-defined AOI and receives shaped review data. The backend starts the analysis and tracks job state. The worker writes evidence artifacts. The report layer emits a stable report structure. The assistant reads that structure and produces explanation text.

For the current build, lightweight persistence is enough for lands and jobs, while analysis outputs are stored as local artifacts. This choice supports transparency. The source imagery record, index time series, quality metrics, activity-cycle output, assessment, and report summary can be inspected separately. It also helps debugging: if the final report appears surprising, the team can inspect the stage where the surprise first appears.

Table: Table 5.2: Artifact roles in the current build

| Artifact role | Why it exists | How it supports trust |
| --- | --- | --- |
| Source imagery record | Keeps satellite bands, dates, and provenance together | Reprocessing can occur without changing the original evidence |
| Index time series | Converts imagery into field-level signals | Reviewers can see dates, quality, and indicator values |
| Quality metrics | Records gaps and usable observations | Low confidence can be explained as evidence limitation |
| Activity-cycle output | Captures vegetation windows and boundaries | Land status is based on interval behavior, not one date |
| Land assessment | Combines status, trend, risk flags, and confidence | Portal and report use one assessment source |
| Grounded report | Converts assessment into review language | Every claim has confidence and limitation framing |

This artifact strategy also protects against a common remote-sensing mistake: treating a smoothed chart as if every daily point were directly observed. FarmTrust keeps the original observations separate from the model-derived analysis curve. The smooth curve helps identify shape and timing, but confidence still depends on the actual observation record.

## 5.7 Report Boundary and Assistant Boundary

The report boundary defines what the platform is allowed to say. The report may say that the parcel showed recent vegetation activity, that activity was repeated across detected cycles, that satellite evidence is limited, or that a watch item deserves manual review. The report may not say that a loan should be approved, that a borrower will repay, that a crop type is proven, that yield is known, or that pests are absent.

The assistant boundary is even stricter because generated language can sound more confident than the underlying report. The assistant is allowed to explain the report, summarize it in plain language, answer questions about the report evidence, and reason with user-declared context. It is not allowed to create new assessment facts, change the assessment, or answer outside the evidence boundary. When the evidence is not enough, the assistant should say that the report cannot support the requested conclusion.

This design makes the assistant useful without making it dangerous. A reviewer may ask why confidence is medium, what the latest activity cycle means, or which follow-up item matters most. Those questions are inside the report. Questions about yield, crop proof, loan approval, pest diagnosis, or legal and cadastral certainty are outside the report and should receive a limitation answer.

## 5.8 Security, Privacy, and Operational Controls

Although the current build is a thesis implementation, the architecture still follows basic controls. The portal and backend separate user interaction from processing; the worker handles long-running analysis outside the browser; and the assistant reads the report object rather than arbitrary internal state. The most important concern for this scope is preventing misuse of evidence. An analysis polygon identifies a real location, and a report can influence review, so limitations and provenance must remain visible.

## 5.9 Failure Handling and Review Transparency

Failure handling is part of the design because remote-sensing systems often fail in ordinary ways. A polygon may be too small or badly drawn. A time window may have poor satellite coverage. Clouds may remove important observations. The latest activity cycle may be open at the edge of the record. The assistant may be unavailable. A robust review platform should not hide these conditions.

FarmTrust handles these cases by exposing processing state, lowering confidence where evidence is weak, separating evidence limitations from land risks, and keeping a rule-based report path available. If the assistant is unavailable, the report remains usable. If satellite evidence is limited, the system states that limitation rather than forcing a high-confidence result.

This approach makes the platform more honest. A financing reviewer does not only need positive results. The reviewer also needs to know when the evidence is not enough. A low-confidence report can still be useful if it clearly explains why confidence is low and what follow-up evidence would help.

## 5.10 Design Tradeoffs

The current design chooses explainability over automation. It uses conservative rules and transparent evidence summaries rather than an opaque credit score. This limits the system's headline ambition, but it makes the output more defensible for finance support.

The design also chooses satellite-only evidence for the core assessment. Field visits, weather data, soil records, irrigation schedules, farmer histories, and repayment records would all improve a real financing workflow, but they remain outside the core build because the project focuses on the satellite-evidence contribution.

A third tradeoff is the use of a bounded language-model assistant. A language model can reduce friction by explaining a technical report in natural language and by answering follow-up questions. However, the model can also overstate what it knows. FarmTrust resolves this by making the assistant dependent on the report, keeping a rule-based summary as a fallback, and treating unsupported questions as limitation cases.

## 5.11 Summary

The architecture is built around one question: can a reviewer see what the system concluded and why? FarmTrust answers by keeping the pipeline modular, preserving evidence artifacts, separating assessment from explanation, and using cautious report language. The result is a coherent path from satellite imagery to finance-ready decision support. The design does not remove uncertainty; it makes uncertainty visible, which is essential for responsible use in agricultural finance review.
