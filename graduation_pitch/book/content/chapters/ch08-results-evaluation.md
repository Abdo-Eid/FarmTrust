## 8.1 Implementation Overview

FarmTrust is implemented as a web-based lender-facing farm risk reporting platform. It connects a modern portal, a Python backend, a satellite-processing worker, file-based analysis artifacts, a lender report, and a bounded report explanation assistant. The result is a working path from land submission to evidence review.

The implementation follows the system design from Chapter 5: the portal presents the workflow, the backend coordinates jobs, the worker produces the evidence and assessment, the report layer converts that evidence into lender-readable language, and the assistant explains the report after the assessment exists. This separation matters because a finance reviewer must know which part created evidence and which part only explained it.

Table: Table 8.1: Implemented technology stack

| Area | Technology | Role |
| --- | --- | --- |
| Portal | Next.js, React, TypeScript | User interface and report surfaces |
| Maps | Leaflet | AOI drawing and geospatial context |
| Backend | FastAPI, Python | API, job coordination, report access |
| Processing | xarray, raster tools, NumPy, pandas | Satellite time-series processing |
| Data access | STAC and Sentinel-2 | Satellite observation retrieval |
| Styling | Tailwind CSS and UI primitives | Institutional report interface |
| Assistant | Configured language model with fallback | Bounded explanation over report evidence |

The stack was chosen for practical reasons: Python suits satellite processing, the web portal supports reviewer workflows, and the language-model component remains optional because the core assessment must work without generated explanation.

## 8.2 Backend and Processing Flow

The backend coordinates the user workflow. A land submission creates a job that moves through validation, satellite fetching, vegetation analysis, risk modeling, and report generation. This staged design keeps the lender-facing output explainable even when part of the pipeline fails or confidence is low.

The processing worker writes intermediate artifacts rather than only returning a final label. Satellite observations, quality metrics, smoothed curves, activity cycles, assessment outputs, and report evidence can therefore be reviewed separately. During development, this made method comparison and improvement possible without rewriting the whole application.

The backend also provides a stability boundary: the portal needs land status, progress, evidence summaries, and report content, not every processing detail. This lets the method improve while the reviewer-facing interface remains stable.

## 8.3 Portal Surfaces

The portal is designed as a financial review surface rather than a general farming dashboard. The main user flow is: open the land portfolio, add a user-defined AOI, wait for processing, review the land summary, inspect evidence, open the lender report, and export a portable report when needed.

The interface prioritizes decision outputs, confidence, risk drivers, and evidence access. A reviewer should first understand what the assessment says, then why it says it, then where the limitations are. The design avoids making free map exploration the main task because the primary workflow is case review.

[[PAGE_BREAK]]

Table: Table 8.2: Portal surfaces and review purpose

| Surface | Review purpose |
| --- | --- |
| Land portfolio | Track submitted lands and processing state |
| AOI input | Define the parcel for analysis |
| Processing view | Show job progress and failure state |
| Land summary | Present status, trend, confidence, and drivers |
| Evidence view | Let the reviewer inspect supporting signals |
| Lender report | Provide a grounded decision-support brief |
| Report assistant | Explain the report and answer bounded questions |

The portal also supports a layered reading experience. A reviewer can scan the report quickly, then inspect detailed evidence if needed. The system presents a conclusion, but it keeps the evidence close enough for the conclusion to be challenged.

## 8.4 Evidence View and Lender Report

The evidence view and lender report have different roles. The evidence view is closer to the analysis: time-series charts, activity records, quality indicators, and supporting metrics. The lender report is closer to decision support: headline assessment, observed and interpreted evidence, confidence notes, watch items, risk separation, and boundaries.

The lender report is the most important implementation surface because it turns technical analysis into review language. It presents the headline assessment, the four-part evidence read, the activity record, track record, risk and limitation items, cautious indicators, and a fixed boundaries section.

The report is separate from the assistant and remains available even if no language model is configured, because it is generated from deterministic project evidence.

The report's language is intentionally cautious. It can say that satellite evidence shows recent vegetation activity, that history is limited, or that confidence is low because of gaps. It cannot say that a loan should be approved, that the land will produce a specific yield, that a pest is absent, or that a crop has been proven from satellite imagery.

## 8.5 Report Explanation Assistant

The report explanation assistant is a bounded explanation layer over the lender report. It narrates the report in plain language and answers reviewer questions about report evidence, helping connect technical signals without creating new assessment evidence.

![Figure 8.1: How the report assistant stays grounded in the lender report.](fig04_assistant_grounding.png){width=6.0}

The assistant reads the grounded report, the activity record, the confidence notes, the boundaries, and curated agricultural interpretation guidance. If the user provides crop context, it may reason with that user-declared context, but it must not infer crop identity from satellite data alone or estimate yield, income, pest status, or a financing decision.

The system also includes a rule-based summary path, so the report can still be narrated when the language model is unavailable. The model is therefore an explanation enhancement, not a dependency for the core assessment.

[[PAGE_BREAK]]

Table: Table 8.3: Assistant safety design

| Design element | Safety purpose |
| --- | --- |
| Report-first input | Keeps answers tied to existing evidence |
| Rule-based fallback | Keeps narration available without a model |
| Evidence-type labels | Shows whether text is observed, interpreted, or uncertain |
| Boundaries block | Prevents loan, yield, pest, legal, and crop-proof claims |
| User-declared context rule | Allows reasoning with user input without inventing facts |

## 8.6 Grounded Question Answering

The assistant's question-answering behavior follows the same evidence boundary as the report. Questions about confidence, latest activity, or watch items can be answered from observation gaps, cycle clarity, signal reliability, and limitations.

Questions outside that boundary require a different answer. If the user asks for crop proof, yield, income, or loan approval, the assistant should explain that the report does not support that conclusion.

This refusal behavior is part of responsible design. In a bounded decision-support system, refusing unsupported conclusions is as important as answering supported questions.

## 8.7 Bilingual Explanation and Local Usability

The report assistant supports both English and Arabic explanation, which matters in Egypt where reviewers may move between Arabic communication and English technical terminology. Bilingual support is a usability requirement: a reviewer should be able to ask in Arabic and still receive an answer that respects the same evidence boundaries.

Arabic answers must follow the same rules as English answers, explaining observed evidence, cautious interpretation, confidence, and limitations without becoming more assertive because the language changed.

The final interface evidence is included in the closing gallery of Chapter 10. It shows the assistant narration, English question answering, Arabic question answering, and a grounded refusal on an implemented land report rather than as a planned feature.

## 8.8 Responsible Language-Model Use

The assistant demonstrates responsible language-model use in a decision-support system. FarmTrust takes a narrow approach: the assistant sits beside the report, not inside scoring logic. Its job is explanation, not decision-making.

This design is important for finance. A lender may ask why confidence is low or what should be watched, and the assistant can answer from report evidence. If the user asks for yield, pest diagnosis, legal or cadastral certainty, or loan approval, the correct answer is a refusal or limitation statement.

Table: Table 8.4: Responsible assistant behavior

| User request type | Allowed response | Boundary |
| --- | --- | --- |
| Explain report confidence | Explain gaps, cycle clarity, and evidence strength | Must use report evidence |
| Summarize latest activity | Describe detected activity window and limitations | No crop proof |
| Use user-declared crop context | Reason with the declared context | Attribute it as user-provided |
| Estimate yield or income | Refuse and explain limitation | No yield model in current scope |
| Decide loan approval | Refuse and redirect to human review | Report is decision support only |

## 8.9 Current Implementation Limitations

The current implementation is a thesis-stage system, not a complete production banking system. Job execution uses a direct worker path rather than a full multi-user queue. Storage is local and simple. The report uses satellite evidence as the core assessment source and treats user-provided context as explanatory context. Broader user testing and interface evidence still need to be completed for the final thesis version.

The satellite method also has scientific limitations. Sentinel-2 imagery can miss important events because of clouds or timing. Small parcels can contain few pixels. Greenness can hide pest damage or yield variation. Local crop rotations can shift timing. The implementation handles these issues by lowering confidence, exposing evidence limitations, and keeping unsupported claims out of the report.

The assistant also has limits. It can explain report evidence, but it cannot improve weak satellite coverage, inspect the field, validate legal documents, or know the farmer's actual management decisions unless the user provides that context.

## 8.10 Summary

The implementation shows that FarmTrust is not only a theoretical remote-sensing pipeline. It connects a working web portal, a satellite analysis flow, a lender report, and a bounded explanation assistant. Its main contribution is the disciplined connection between evidence and language: technical signals become readable assessment statements, but every statement remains limited by what the evidence can support.

This implementation prepares the ground for the case-study chapter. Chapter 9 evaluates the method on the El-Kom Al-Akhdar parcel, shows how the evidence behaves in practice, and explains what the results can and cannot prove.
