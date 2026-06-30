# T-12 — Graduation Book Writing

## Goal

Write the graduation project book in English quickly and coherently, using the existing FarmTrust documentation, pipeline notes, app screenshots, and analysis figures instead of starting from a blank page.

The book should present FarmTrust as a satellite-based agricultural land assessment and reporting system for agricultural finance decision support. It should be honest about current scope, limitations, and future work.

## Scope

### IN

- Inspect the provided book template/project at `C:\Users\abdulhamed\Downloads\graduation_book_python\graduation_book_python`.
- Build the book around the current FarmTrust project truth from `docs/PROJECT.md`, `docs/ENGINEERING.md`, `docs/PIPELINE.md`, `docs/UI.md`, and active task decisions.
- Reuse existing writing logs under `docs/documentations/` to speed up chapter drafting.
- Include screenshots from the app: landing/entry, lands list, AOI drawing, processing, summary, evidence, report/export, and later polished report/card if available.
- Include selected graphs/figures from `outputs/exploration/figs/`, especially timeline, quality, vegetation indices, spatial evidence, cut-front, NDRE, MSAVI, and HMM validation where relevant.
- Use the Menofia parcel and isolated `outputs/exploration/` work as the main case study.
- Keep claim discipline: FarmTrust is decision support, not automated loan approval, crop identity proof, yield prediction, pest diagnosis, or legal surveying.

### OUT

- Overpromising features that are future work, such as monitoring, neighbour baseline, crop/rotation-aware calendar, full pixel-map UI, or unrestricted AI decisions.
- Rewriting the whole project scope only for the book.
- Treating isolated one-parcel findings as universal validation.
- Adding unsupported claims about exact crop type, yield, pests, income, or loan approval.

## Role Split

- Driver: convert existing docs and outputs into book sections and figures.
- Reviewer: check claim discipline, scope honesty, clarity for academic review, and whether figures support the text.
- Curator: keep source mapping clear so every chapter points back to existing project evidence.

## Chosen approach

Write the book from strongest existing material first, not from chapter one sequentially.

Quality target: the book must read like a careful human research project, not rushed/generated. The writing should use formal academic English, clear transitions, figure introductions, explanatory captions, and honest limitations.

Length target: 80-110 pages total, including front matter, bibliography, and Arabic part at the end.

Abstract target: 1-2 pages.

Fast writing order:

1. System Design.
2. Satellite Data Pipeline and Methodology.
3. Evidence Modeling and Land Assessment.
4. Implementation and User Interface.
5. Case Study, Results, and Evaluation.
6. Introduction.
7. Conclusion and Future Work.
8. Background / Literature Review last.

Recommended book structure:

| Chapter | Title | Main source material | Notes |
|---|---|---|---|
| 1 | Introduction | `docs/PROJECT.md` | Problem, motivation, users, objectives, impact, current scope. |
| 2 | Background and Related Work | `docs/documentations/02-crop-research-review-log.md`, `03-yieldsat-dataset.md`, `04-morocco-crop-classification-scientific-log.md` | Remote sensing, Sentinel-2, indices, time series, agricultural finance, report explanation, bounded LLM use. |
| 3 | Problem Definition, Objectives, and Scope | `docs/PROJECT.md`, T-11 decisions | Precise problem, project objectives, assumptions, non-goals, claim discipline. |
| 4 | Requirements and System Analysis | `docs/PROJECT.md`, `docs/UI.md` | Users, use cases, functional/non-functional requirements, constraints. |
| 5 | System Architecture and Design | `docs/ENGINEERING.md`, `docs/PIPELINE.md`, `docs/pipeline-walkthrough.md` | Backend, frontend, data flow, artifacts, API, storage, report layer. |
| 6 | Satellite Data Pipeline and Methodology | `docs/PIPELINE.md`, `docs/pipeline-walkthrough.md`, `docs/documentations/06-smoother-detector-hmm-refactor-log.md`, ingestion docs | AOI, STAC, Sentinel-2, `cube.zarr`, SCL mask, indices, preprocessing, Whittaker smoothing + lambda choice, gap analysis. |
| 7 | Evidence Modeling and Land Assessment | T-11 decisions, `docs/documentations/06-smoother-detector-hmm-refactor-log.md`, `farmtrust_core` docs/outputs | Activity cycles, detector algorithm, HMM cross-check, confidence, status vocabulary, absence gate, indicators, spatial evidence, risk logic. |
| 8 | Implementation and User Interface | `docs/PIPELINE.md`, `docs/UI.md`, app screenshots | Stack, modules, API/worker, portal screens, evidence views, report UI. |
| 9 | Case Study, Results, and Evaluation | `outputs/exploration/`, `outputs/exploration/figs/`, `outputs/diagnostics/<aoi>/`, `docs/documentations/05-local-interpretation-context.md`, `docs/documentations/06-smoother-detector-hmm-refactor-log.md` | Menofia parcel, figures, pipeline visualization, HMM agreement tables, local corrections, evaluation, what worked, limitations. |
| 10 | Conclusion and Future Work | `docs/FUTURE.md`, T-11 decisions | Summary, limitations, crop/rotation calendar, NDRE/MSAVI, monitoring, neighbours, LLM/chat. |

Template note: the current Python template has a generic Chapter 9 named `Business Model and Market Value`. Replace or heavily refocus it as `Case Study, Results, and Evaluation` unless university requirements explicitly require a business chapter. If required, business value should be a short section inside Chapter 1 or Chapter 10, not the main technical story.

Recommended page budget:

| Part | Target pages |
|---|---:|
| Front matter, abstract, lists, project summary | 8-12 |
| Chapters 1-4 | 22-28 |
| Chapters 5-8 | 35-45 |
| Chapter 9 case study/evaluation | 12-18 |
| Chapter 10, bibliography, Arabic part | 10-15 |
| Total | 80-110 |

## Task List

- [x] Inspect the Python book template at `C:\Users\abdulhamed\Downloads\graduation_book_python\graduation_book_python`.
- [x] Identify the template format, build command, folder structure, and where chapters/assets live.
- [ ] Create or map chapter files to the agreed book structure.
- [ ] Inventory existing docs and map each doc to chapter sections.
- [ ] Inventory available figures in `outputs/exploration/figs/` and choose the strongest 10-14 figures.
- [ ] Capture app screenshots with consistent browser size/zoom.
- [ ] Create a figure list with captions and source paths.
- [ ] Draft Chapter 5: System Architecture and Design.
- [ ] Draft Chapter 6: Satellite Data Pipeline and Methodology.
- [ ] Draft Chapter 7: Evidence Modeling and Land Assessment.
- [ ] Draft Chapter 8: Implementation and User Interface.
- [ ] Draft Chapter 9: Case Study, Results, and Evaluation.
- [ ] Draft Chapter 1: Introduction.
- [ ] Draft Chapter 10: Conclusion and Future Work.
- [ ] Draft Chapter 3: Problem Definition, Objectives, and Scope.
- [ ] Draft Chapter 4: Requirements and System Analysis.
- [ ] Draft Chapter 2: Background / Literature Review.
- [ ] Add citations/references where required by the template or university rules.
- [ ] Review for claim discipline: no unsupported crop/yield/pest/loan/legal claims.
- [ ] Build/export the book from the Python template.
- [ ] Review generated PDF/HTML for broken figures, formatting, captions, and table overflow.

## Feedback Log

- 2026-06-29: User said the graduation book will be in English and that existing docs/logs under `docs/documentations/` should make writing faster.
- 2026-06-29: User said screenshots from the app and graphs/figures should be included.
- 2026-06-29: User provided the book template path: `C:\Users\abdulhamed\Downloads\graduation_book_python\graduation_book_python`.
- 2026-06-29: Template inspected. It is a Python DOCX generator with `content/book.json`, Markdown chapters under `content/chapters/`, image assets under `assets/`, and build command `python generate_graduation_book.py`.
- 2026-06-29: User clarified the final book should target 80-110 pages including the Arabic part, with a 1-2 page abstract.
- 2026-06-29: User prefers quality over speed: the writing should take time, read like a human researcher wrote it, and not look rushed.
- 2026-06-29: User approved changing the template chapter structure where it improves the FarmTrust story.

## Decisions

- [decision] Book language is English.
- [decision] Start from existing FarmTrust docs and outputs instead of writing from scratch.
- [decision] Use current realistic scope: AOI input -> Sentinel-2 ingestion -> time-series indices -> preprocessing -> activity-cycle analysis -> land assessment -> evidence report -> portal.
- [decision] Include app screenshots and selected analysis figures.
- [decision] Menofia parcel / isolated `outputs/exploration/` work is the main case study, with local-context caveats.
- [decision] Target 80-110 pages including Arabic section.
- [decision] Abstract should be 1-2 pages.
- [decision] Use a revised 10-chapter structure centered on FarmTrust's strongest story: satellite evidence -> activity cycles -> confidence-aware land assessment -> lender-facing report.
- [decision] Replace or refocus the generic business-model chapter as a case study/results/evaluation chapter unless university rules require a business chapter.
- [decision] When writing starts, the template folder should be copied into the current workspace/project directory, then edited there.

## Open Questions

- [partly answered] What exact university template constraints apply: page count, chapter names, citation style, font, margins, cover page, abstract length, and required appendices? Page target is 80-110 including Arabic part; abstract target is 1-2 pages. Citation style, required chapter names, and appendices still need confirmation.
- [answered] Does the Python template build PDF, HTML, DOCX, or multiple formats? It builds `generated_graduation_book.docx`; the helper can render DOCX pages or full PDF using Microsoft Word automation.
- [open] Are Arabic captions/abstract required in addition to the English book?
- [open] Which app screens are stable enough for final screenshots?
- [partly answered] What deadline and minimum acceptable page count should guide the writing depth? Target is 80-110 pages; exact deadline still needed.

## Knowledge to Keep

- Strong source docs:
  - `docs/PROJECT.md` for product problem, scope, outputs, non-goals.
  - `docs/ENGINEERING.md` for architecture and stack.
  - `docs/PIPELINE.md` and `docs/pipeline-walkthrough.md` for technical pipeline explanation.
  - `docs/UI.md` for portal/user-flow explanation.
  - `docs/documentations/05-local-interpretation-context.md` for local agronomy interpretation caveats.
  - `docs/TASKS/T-11-isolated-parcel-analysis-pipeline-improvement.md` for latest research decisions and implementation direction.
- Strong figure candidates:
  - `outputs/exploration/figs/f1_timeline.png`
  - `outputs/exploration/figs/f2_quality.png`
  - `outputs/exploration/figs/f3_veg.png`
  - `outputs/exploration/figs/f7_spatial_peaks.png`
  - `outputs/exploration/figs/f8_zones.png`
  - `outputs/exploration/figs/f10_cuts.png`
  - `outputs/exploration/figs/f11_sweep.png`
  - `outputs/exploration/figs/f12_ndre.png`
  - `outputs/exploration/figs/msavi_vs_ndvi.png`
  - `outputs/exploration/figs/f14_hmm.png`
- Claim discipline for book: decision support only; no automated loan approval, exact crop identity proof, yield prediction, pest diagnosis, income estimation, or legal land surveying.
- Template structure:
  - Main config: `content/book.json`.
  - Chapter files: `content/chapters/*.md`.
  - Assets: `assets/`.
  - Generator: `generate_graduation_book.py`.
  - Output: `generated_graduation_book.docx`.
  - Build command: `python generate_graduation_book.py`.
  - Figure syntax: `![Figure 2.1: Caption](image_name.png){width=3.6}` with images resolved from `assets/`.
  - Table syntax: `Table: Table x.x: Caption` followed by a Markdown table.
- Writing quality bar: do not dump docs directly. Rewrite into formal thesis style with transitions, explanation, figure references, careful captions, and limitations.

## Done Summary

- Pending.
