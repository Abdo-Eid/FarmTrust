# T-12 — Graduation Book Writing

## Goal

Write the graduation project book in English quickly and coherently, using the existing FarmTrust documentation, pipeline notes, app screenshots, and analysis figures instead of starting from a blank page.

The book should present FarmTrust as a satellite-based agricultural land assessment and reporting system for agricultural finance decision support. It should be honest about current scope, limitations, and future work.

## Scope

### IN

- Use the book template and sources now in-repo at `graduation_pitch/book/` (chapters in `book/content/chapters/`, figures in `book/assets/`, generators in `book/*.py`). It was originally supplied from an external `Downloads` copy; that path is gone and the repo copy is the source of truth.
- Build the book around the current FarmTrust project truth from `docs/PROJECT.md`, `docs/ENGINEERING.md`, `docs/PIPELINE.md`, `docs/UI.md`, and active task decisions.
- Reuse existing writing logs under `docs/documentations/` to speed up chapter drafting.
- Include screenshots from the app: landing/entry, lands list, AOI drawing, processing, summary, evidence, report/export, the polished lender **report card** (`/lands/[id]/packet`), and the **"Ask the assistant"** tab (narration + English and Arabic chat).
- Tell the grounded report story (now shipped, not future): the deterministic **evidence packet** (Observed → Interpreted → Confidence → Watch, per-claim confidence + provenance levels) and the **bounded AI report assistant** (claim-typed, deterministic-first, grounded by prompt, reasons with user-declared crops, never asserts crop/yield/loan) — a distinctive responsible-AI contribution.
- Include selected graphs/figures from `outputs/exploration/figs/`, especially timeline, quality, vegetation indices, spatial evidence, cut-front, NDRE, MSAVI, and HMM validation where relevant.
- Use the Menofia parcel and isolated `outputs/exploration/` work as the main case study.
- Keep claim discipline: FarmTrust is decision support, not automated loan approval, crop identity proof, yield prediction, pest diagnosis, or legal surveying.
- Use **reader-facing terminology only** — no internal development names in the book prose (no "Layer 5/6/7" or milestone numbering, no task IDs like T-04/T-11, no code identifiers such as `claim_type`/`source_mode` or file/function names). See the terminology map in *Knowledge to Keep*.
- Keep the book **figure-rich** — analysis graphs, pipeline visualizations, app screenshots, and generated diagrams. Every visual is catalogued in `docs/TASKS/T-12-figure-manifest.md` (caption, source, type, target chapter, status); chapters reference it rather than inventing figure metadata.
- Present the R&D **comparisons as paper-style numeric tables** (like the model/ablation comparison tables in research papers) plus a natural-language interpretation in the project's own voice ("we noticed…", "we chose… by reasoning…"). Mined from the research logs into `docs/TASKS/T-12-comparison-tables.md`; numbers quoted verbatim, single-parcel/dataset results reported honestly as such.

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

Length target: around 100 pages total after the final screenshot pass, including front matter, bibliography, and Arabic part at the end. The prose-only draft may land around 85-95 rendered pages before screenshots are inserted.

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
| 7 | Evidence Modeling and Land Assessment | T-11 decisions, `docs/documentations/06-smoother-detector-hmm-refactor-log.md`, `docs/PIPELINE.md` §Report evidence packet, `docs/DECISIONS.md` (Layer 5), `farmtrust_core` docs/outputs | Activity cycles, detector algorithm, HMM cross-check, confidence, status vocabulary, absence gate, indicators, spatial evidence, risk logic, and the grounded **evidence packet** (Observed → Interpreted → Confidence → Watch; per-claim confidence + provenance levels; claim discipline). |
| 8 | Implementation, Lender Report, and Bounded AI Assistant | `docs/PIPELINE.md`, `docs/UI.md`, `docs/TASKS/T-04-ai-report-assistant.md`, `docs/DECISIONS.md` (Layers 6–7), `api/assistant/*` + `api/assistant/knowledge.md`, app screenshots | Stack, modules, API/worker, portal screens, evidence views, the polished **lender report card**, and the **bounded AI assistant**: deterministic-first narration + analyst chat over the packet, claim typing/provenance, Azure `gpt-4o` via `langchain-openai` gated off when unconfigured, grounding by system prompt, a curated runtime-loaded knowledge file, reasoning with user-declared crops, and the always-on deterministic brief fallback. |
| 9 | Case Study, Results, and Evaluation | `outputs/exploration/`, `outputs/exploration/figs/`, `outputs/diagnostics/<aoi>/`, `docs/documentations/05-local-interpretation-context.md`, `docs/documentations/06-smoother-detector-hmm-refactor-log.md` | Menofia parcel, figures, pipeline visualization, HMM agreement tables, local corrections, evaluation, what worked, limitations. |
| 10 | Conclusion and Future Work | `docs/FUTURE.md`, T-11 decisions | Summary; what shipped (incl. the evidence packet, lender report card, and the bounded AI assistant); honest limitations; genuinely-future work only: crop/rotation-aware calendar, NDRE/MSAVI expansion, monitoring, neighbour baselines, response streaming, multilingual narration, and the heavy code-enforced guardrail validator. |

**Report & assistant thread (the showcase).** FarmTrust's most distinctive and most recent contribution — the grounded **evidence packet** (Ch 7), the lender **report card**, and the **bounded, claim-disciplined AI assistant** (Ch 8) — is a strong example of *responsible* LLM use: deterministic-first, every narration line typed and sourced, grounded strictly by the system prompt + a curated knowledge file, reasoning with user-declared context but never asserting crop/yield/loan. Tie it back to the "bounded LLM use" framing introduced in Chapter 2's related work, and feature it as a primary results highlight in Chapter 9. This is what differentiates FarmTrust from a generic NDVI dashboard.

Template note: the current Python template has a generic Chapter 9 named `Business Model and Market Value`. Replace or heavily refocus it as `Case Study, Results, and Evaluation` unless university requirements explicitly require a business chapter. If required, business value should be a short section inside Chapter 1 or Chapter 10, not the main technical story.

Recommended page budget:

| Part | Target pages |
|---|---:|
| Front matter, abstract, lists, project summary | 10-14 |
| Chapters 1-4 | 30-36 |
| Chapters 5-8 | 38-42 |
| Chapter 9 case study/evaluation | 12-14 |
| Chapter 10, bibliography, Arabic part | 10-14 |
| Final screenshot pass | 5-15 |
| Total after screenshots | Around 100 |

## Task List

- [x] Inspect the Python book template at `C:\Users\abdulhamed\Downloads\graduation_book_python\graduation_book_python`.
- [x] Identify the template format, build command, folder structure, and where chapters/assets live.
- [x] Create or map chapter files to the agreed book structure.
- [x] Inventory existing docs and map each doc to chapter sections.
- [x] Inventory available figures and choose the strongest 10-14 — done in `docs/TASKS/T-12-figure-manifest.md` (variant graphs flagged for de-dup).
- [x] Create the figure list with captions and source paths — `docs/TASKS/T-12-figure-manifest.md`.
- [x] Capture the app screenshots (S-01..S-15 in the manifest) with consistent browser size/zoom — incl. the lender report, the assistant narration, an Arabic answer, and a grounded refusal.
- [ ] Produce the diagrams to generate (architecture, data flow, evidence read, assistant grounding, evidence-grounding ladder) — D-01..D-05 in the manifest. **Progress:** D-01..D-04 generated into `graduation_pitch/book/assets/` and redesigned in a cleaner thesis-ready style; D-05 not used in this slice.
- [ ] Screenshot the pipeline visualizations (V-01/V-02) for the methodology / case-study chapters.
- [x] Built the comparison-tables reference (`docs/TASKS/T-12-comparison-tables.md`) — **12 single-comparison tables** under 5 section headers (Dataset & research framing · Vegetation-index decisions · Season detection & smoothing · Agronomic interpretation lessons · Crop/yield ML exploration). Each table is one like-for-like comparison (same options on the same columns), never a merged theme; the ingestion/storage plumbing is set aside. Numbers verbatim, reader-facing voice. (The intermediate raw 137-table extraction was a working artifact and was deleted; it is regenerable from the `docs/documentations/` logs.)
- [x] Weave all 12 curated scientific comparison tables into the Background, Methodology, Evidence, Case Study, and Evaluation chapters, replacing broad summary tables where possible. Render-verified in the 101-page PDF pass.
- [x] Draft Chapter 5: System Architecture and Design.
- [x] Draft Chapter 6: Satellite Data Pipeline and Methodology.
- [x] Draft Chapter 7: Evidence Modeling and Land Assessment.
- [x] Draft Chapter 8: Implementation, Lender Report, and Bounded AI Assistant.
- [x] Draft Chapter 9: Case Study, Results, and Evaluation.
- [x] Draft Chapter 1: Introduction.
- [x] Draft Chapter 10: Conclusion and Future Work.
- [x] Draft Chapter 3: Problem Definition, Objectives, and Scope.
- [x] Draft Chapter 4: Requirements and System Analysis.
- [x] Draft Chapter 2: Background / Literature Review.
- [x] Write the grounded evidence-packet section (Ch 7) and the report-card + bounded-AI-assistant sections (Ch 8), with the claim-discipline / responsible-LLM framing.
- [x] Replace the text-only S-01..S-15 placeholders with the final interface evidence gallery in Chapter 10, with no broken image references.
- [x] Capture the new report/assistant screenshots: lender report card (`/lands/[id]/packet`), assistant narration with claim-type pills, an English chat answer, an Arabic chat answer (clean RTL), and a grounded crop/yield/loan refusal.
- [ ] Add citations/references where required by the template or university rules.
- [x] Review for claim discipline: no unsupported crop/yield/pest/loan/legal claims. Final scan passed for book content after screenshot insertion.
- [x] Build/export the book from the Python template.
- [x] Review generated PDF/HTML for broken figures, formatting, captions, and table overflow. Final DOCX/PDF render QA passed after screenshot insertion; no HTML output in this template.

## Feedback Log

- 2026-06-29: User said the graduation book will be in English and that existing docs/logs under `docs/documentations/` should make writing faster.
- 2026-06-29: User said screenshots from the app and graphs/figures should be included.
- 2026-06-29: User provided the book template path: `C:\Users\abdulhamed\Downloads\graduation_book_python\graduation_book_python`.
- 2026-06-29: Template inspected. It is a Python DOCX generator with `content/book.json`, Markdown chapters under `content/chapters/`, image assets under `assets/`, and build command `python generate_graduation_book.py`.
- 2026-06-29: User clarified the final book should target 80-110 pages including the Arabic part, with a 1-2 page abstract.
- 2026-06-29: User prefers quality over speed: the writing should take time, read like a human researcher wrote it, and not look rushed.
- 2026-06-29: User approved changing the template chapter structure where it improves the FarmTrust story.
- 2026-07-01: Enhanced the plan to fold in the now-shipped Layers 5–7 (grounded evidence packet, lender report card, bounded AI assistant) — previously framed as future work. They are now a core part of the book: the packet anchors Chapter 7, the report card + assistant anchor Chapter 8, and the responsible-bounded-LLM angle becomes a showcase results highlight (Ch 9) tied to Chapter 2's bounded-LLM related work. Source maps, the figure/screenshot list, and the task list were updated accordingly.
- 2026-07-01: User wants the R&D comparisons shown as paper-style numeric tables (à la model/ablation tables) plus natural-language interpretation ("we noticed… / by sense…"). Built `docs/TASKS/T-12-comparison-tables.md` by mining all `docs/documentations/` research logs (automated extraction across 9 logs → 144 raw comparisons → 137 tables), each with "what we observed / what we did and why" in the project's voice, grouped by chapter. Numbers quoted verbatim (spot-checked against the logs); reader-facing terminology only.
- 2026-07-01: User asked to keep only the **high-value** comparisons, not every one. Curated the 137 down to **41** — the comparisons that drove a real design decision or capture a key finding — dropping ~90 granular crop-classification / yield-transfer ablation variants (near-duplicate feature-importance and per-fold tables). Filtered by exact heading so no number was altered.
- 2026-07-01: 41 was still too many separate micro-tables. User asked to distill further and de-emphasise the early ingestion logs (00/01). **Dropped the 12 low-level ingestion/storage plumbing comparisons** (satellites, processing level, scene/tile, mosaics, windowed reads, dedup, export format, band handling, AOI input, window-vs-tile cost).
- 2026-07-01: User clarified — don't merge comparisons into a thematic table unless they genuinely fit ONE table (same options, same columns). My first pass over-grouped (a λ sweep, an agreement check, an ablation, and yield variants forced under shared columns). Restructured into **12 single-comparison tables under 5 section headers**: each table is now one like-for-like comparison (e.g. the λ sweep, the detector-vs-HMM agreement, the three-run ablation, the random-vs-LOZO split, and the yield variants are each their own table). Section headers stay for navigation; tables are never merged across structures. Numbers re-verified verbatim.
- 2026-07-01: Deleted the intermediate raw 137-table extraction (`T-12-comparison-tables-full-extract.md`) — it was a derived working artifact (the source logs under `docs/documentations/` are the record, and it is regenerable). The curated 12-table reference is the deliverable; the raw extract should not be committed.
- 2026-07-01: User clarified two requirements. (1) The book must **not mention internal development names** ("Layer 5/6/7", task IDs, code identifiers) — added a reader-facing terminology map and a decision; book prose uses product/academic language only. (2) The book must be **figure-rich** (graphs, app screenshots, generated images, diagrams) and needs a **separate figure-details file** — created `docs/TASKS/T-12-figure-manifest.md` cataloguing all 17 existing analysis graphs, the pipeline visualizations + smoothing/detection illustrations, the app screenshots to capture, and the diagrams to generate, with a strongest-10–14 shortlist.
- 2026-07-01: Supervisor/source-citation note refined: in-book captions no longer use repeated `Source:` phrases or "FarmTrust analysis" wording. FarmTrust is treated as the built platform/project output, while figures from `outputs/` are described as the team's case-study analysis / research work. Parcel-origin context is stated once in prose as an agricultural parcel in El-Kom Al-Akhdar, Shebin El-Kom District, Menoufia Governorate, Egypt.
- 2026-07-01: Implemented the first writing sprint inside `graduation_book_python/`. Preserved the English and Arabic cover metadata, rewrote `content/book.json` body metadata/front matter, drafted substantial Chapters 5–8, lightly aligned Chapters 1, 3, 9, and 10 to avoid template contradictions, copied selected ready figures into `assets/`, and generated four book-ready diagrams: architecture, data flow, four-part evidence read, and assistant grounding. Screenshots and the fifth optional grounding-ladder diagram remain open.
- 2026-07-01: Built `generated_graduation_book.docx` successfully and exported a 52-page PDF for visual QA. Checked all-page thumbnail sheets plus representative cover, abstract, figure/table, bibliography, and Arabic pages. Fixed an awkward Chapter 2 table/page split before final build. Rendered QA artifacts are temporary and should be removed from `graduation_book_python/rendered_pages/` after inspection.
- 2026-07-01: User changed the target to around 100 pages, expecting the final screenshot pass to add the remaining pages. Next sprint revised Chapters 1-10 in detail, expanded the table/figure-rich prose draft, cleaned caption source language, added text-only screenshot placeholders, and synced `content/book.json` front-matter lists to the current chapter captions.
- 2026-07-01: Compressed the expanded prose after an initial 115-page render landed too high for the screenshot plan. The subsequent sprint render exported to **96 pages before screenshots**, with 36 tables and 19 figures in the synced front matter after the figure-audit correction and corn-comparison insertion. Visual QA checked all-page thumbnails plus detailed dense/table/figure pages, cover, abstract, chapter openings, placeholder pages, bibliography, and Arabic pages. Forbidden-term and broken-image scans passed; `rendered_pages/` should be cleaned after inspection.
- 2026-07-01: Figure audit found that `f11_sweep.png` / `fig10_smoothing_sweep.png` is a moving cut-front raster sequence, not a smoothing-strength sweep. Corrected Chapter 6 to use prose + Table 6.3 for smoothness selection, moved the raster sequence into Chapter 9 cut-and-regrowth interpretation, and updated the figure manifest wording.
- 2026-07-01: User clarified that the corn-season comparison plot is a different plot type from the regular vegetation-index time-series. Kept the Chapter 6 time-series explanation, and inserted the corn comparison into Chapter 9.9 as a one-time explanation of season-to-season comparison plots, peak markers, paired NDVI/NDMI curves, and the shaded Fall Armyworm risk window.
- 2026-07-01: Integrated all 12 curated scientific comparison tables from the comparison-table reference into Chapters 2, 6, 7, and 9, using the scientific logs as the numeric source of truth while keeping filenames and internal development wording out of book prose. Replaced the broad research-summary tables with specific index-boundary, ground-truth, dataset-coverage, smoother/detector, HMM agreement, crop-classification, ablation, validation, model-attempt, and yield-transfer tables. The refreshed render exports to **98 pages before screenshots**, with **41 tables** and **19 figures** in synced front matter.
- 2026-07-01: Redesigned the generated report/architecture figures (`satellite_to_decisions.png`, `fig01_system_architecture.png`, `fig02_data_flow.png`, `fig03_evidence_read.png`, `fig04_assistant_grounding.png`) to remove the beige slide background and dark title bars. The new versions use a white thesis-page background, simple outlined boxes, lighter arrows, larger labels, and a restrained teal/blue palette. Added `graduation_book_python/generate_diagram_assets.py` so the assets can be regenerated consistently.
- 2026-07-01: Polished table rendering in `graduation_book_python/`: text-heavy tables now use light thesis grids with better padding and alignment, numeric comparison tables use booktabs-style minimal rules, dense tables use controlled compact grids, and long floating metrics are rounded for readable in-book comparison. Render QA fixed the Chapter 9 long-decimal wrapping and the Table 9.8 orphan-row split.
- 2026-07-01: Rewrote the English and Arabic abstracts to reflect the current `PROJECT.md` direction more closely: lender-facing farm risk report first, satellite evidence and confidence-aware assessment, bounded report assistant as explanation, and clear non-goals around loan approval, exact crop identity, yield, pests, legal boundaries, and income. Final render is **101 pages**; English abstract spans pages 3-4, Arabic summary starts on page 98, and Arabic abstract spans pages 99-100.
- 2026-07-01: Added markdown page-break support and used it only for stubborn layout control. Final layout pass keeps Table 9.5 and Table 10.1 intact, places 9.10 Evaluation and Limitations naturally on page 89, moves 9.11 Chapter Summary to page 90, removes the blank page before placeholders, fixes Arabic/English bidi token rendering in Arabic prose, and keeps `rendered_pages/` clean except for the full PDF after QA.
- 2026-07-01: Revised the Arabic/English bidi fix after visual review showed the LRM-only approach was not enough. Arabic body prose now emits Arabic text as RTL runs and Latin tokens such as `FarmTrust`, `Sentinel-2`, and `PDF` as LTR runs; the fragile Arabic acronym-list sentence was rewritten in Arabic prose to avoid mixed-direction list reversal.
- 2026-09-27: Repo restructure. The book workspace moved from a flat `graduation_book_python/` layout to `graduation_book_python/book/` (`content/`, `assets/`, `generate_*.py`), so earlier entries in this log referring to `graduation_book_python/assets/`, `content/`, `rendered_pages/`, or `generate_diagram_assets.py` mean the `book/` equivalents. Only sources are tracked; `outputs/` (generated DOCX/PDF/PPTX) and `archive/` are gitignored and regenerable. The separate PPTXGenJS pitch deck under `graduation_book_python/presentation/` was retired in favour of the self-contained HTML deck.
- 2026-09-27: Second restructure. The book workspace and the pitch deck are now consolidated under a single top-level `graduation_pitch/` directory: the book is `graduation_pitch/book/`, the HTML deck is `graduation_pitch/presentation/`, and generated deliverables are `graduation_pitch/outputs/`. The standalone root-level `presentation/` directory and the `graduation_book_python/` directory no longer exist; earlier entries naming those paths mean their `graduation_pitch/` equivalents. The deck's system design brief remains at `graduation_pitch/presentation/system_design_brief/`, and its figures resolve against `graduation_pitch/book/assets/`.

## Decisions

- [decision] Book language is English.
- [decision] Start from existing FarmTrust docs and outputs instead of writing from scratch.
- [decision] Use current realistic scope: AOI input -> Sentinel-2 ingestion -> time-series indices -> preprocessing -> activity-cycle analysis -> land assessment -> evidence report -> portal.
- [decision] Include app screenshots and selected analysis figures.
- [decision] Menofia parcel / isolated `outputs/exploration/` work is the main case study, with local-context caveats.
- [decision] Target around 100 pages including Arabic section after screenshots; prose-only draft can land around 85-95 pages before screenshots.
- [decision] Abstract should be 1-2 pages.
- [decision] Use a revised 10-chapter structure centered on FarmTrust's strongest story: satellite evidence -> activity cycles -> confidence-aware land assessment -> lender-facing report.
- [decision] Replace or refocus the generic business-model chapter as a case study/results/evaluation chapter unless university rules require a business chapter.
- [decision] When writing starts, the template folder should be copied into the current workspace/project directory, then edited there.
- [decision] The book prose uses reader-facing, academic/product terminology only. It must NOT expose internal development vocabulary: no "Layer 5/6/7" / milestone numbering, no task IDs (T-04, T-11, …), and no code identifiers (`claim_type`, `source_mode`, function/file names). Task docs are *sources*, not content; map them to neutral language (see the terminology map in *Knowledge to Keep*).
- [decision] The book is figure-rich and every visual is catalogued in a dedicated manifest, `docs/TASKS/T-12-figure-manifest.md` (working IDs, captions, sources, types, target chapters, status, and the strongest-10–14 shortlist). Chapters reference the manifest; they do not invent figure metadata.
- [decision] R&D comparisons are presented as **paper-style numeric comparison tables** (à la model/ablation tables) plus a short natural-language interpretation in the project's own voice ("what we observed" / "what we did and why"). They are mined from the `docs/documentations/` research logs into `docs/TASKS/T-12-comparison-tables.md`; numbers are quoted verbatim, qualitative comparisons are presented as aspect tables, and single-parcel/dataset results are reported honestly (not universal validation).
- [decision] In-book figure captions should be descriptive and should not repeat `Source:` phrases. FarmTrust means the built platform/project output; research figures from `outputs/` should be discussed as the team's case-study analysis or research work, not as "FarmTrust analysis." Parcel-origin context is stated once in prose where needed.
- [decision] `f11_sweep.png` is cut-and-regrowth spatial evidence, not smoothing-selection evidence. Until a true smoothing-strength comparison figure exists, Chapter 6 should explain smoothness selection with prose and Table 6.3 only.
- [decision] Thesis tables should be styled by content and purpose, not by one default table type: descriptive tables use a clean light-grid style, numeric comparisons use booktabs-style minimal rules, and only large text-heavy tables use compact grids. Long raw floating-point values are rounded in the book while the interpretation remains based on the source experiments.

## Open Questions

- [partly answered] What exact university template constraints apply: page count, chapter names, citation style, font, margins, cover page, abstract length, and required appendices? Page target is around 100 including Arabic part after screenshots; abstract target is 1-2 pages. Citation style, required chapter names, and appendices still need confirmation.
- [answered] Does the Python template build PDF, HTML, DOCX, or multiple formats? It builds `generated_graduation_book.docx`; the helper can render DOCX pages or full PDF using Microsoft Word automation.
- [open] Are Arabic captions/abstract required in addition to the English book?
- [open] Which app screens are stable enough for final screenshots?
- [partly answered] What deadline and minimum acceptable page count should guide the writing depth? Target is around 100 final pages with screenshots; exact deadline still needed.

## Knowledge to Keep

- Strong source docs:
  - `docs/PROJECT.md` for product problem, scope, outputs, non-goals.
  - `docs/ENGINEERING.md` for architecture and stack.
  - `docs/PIPELINE.md` and `docs/pipeline-walkthrough.md` for technical pipeline explanation.
  - `docs/UI.md` for portal/user-flow explanation.
  - `docs/documentations/05-local-interpretation-context.md` for local agronomy interpretation caveats.
  - `docs/TASKS/T-11-isolated-parcel-analysis-pipeline-improvement.md` for latest research decisions and implementation direction.
  - `docs/TASKS/T-04-ai-report-assistant.md` for the bounded AI assistant design, decisions, boundaries, and the responsible-LLM framing.
  - `docs/DECISIONS.md` (Layer 5/6/7 entries) for the evidence-packet, report-card, and assistant decisions.
  - `docs/PIPELINE.md` §Report evidence packet for the grounded packet structure and surfaces.
  - `api/assistant/knowledge.md` for the curated field knowledge the assistant reasons with (and how the local-context lessons were generalized for production).
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
- Strong screenshot candidates (shipped report/assistant surfaces):
  - Lender report card at `/lands/[id]/packet` — verdict, four-layer Observed/Interpreted/Confidence/Watch read, activity timeline, track-record gauge, split risk register, dark "what this does NOT tell you" boundaries block.
  - Assistant tab — narration with evidence-type tags + a source badge; an English chat answer; an Arabic chat answer (clean RTL); a grounded crop/yield/loan refusal.
- Book-facing terminology (never expose internal development names in prose):
  - internal "evidence packet" / "Layer 5" → **"grounded assessment report"** or "structured evidence summary".
  - internal "report card" / "Layer 6" → **"lender report"** or "assessment report".
  - internal "assistant" / "Layer 7" → **"report assistant"** or "grounded report explanation assistant".
  - internal `claim_type` / `provenance_level` → **"evidence type"** / **"confidence (grounding) level"**.
  - internal "deterministic brief" → **"rule-based summary"** / "non-AI summary".
  - "Observed / Interpreted / Confidence / Watch" is already reader-facing — keep it.
  - Omit task IDs (T-04, T-11, …), "Layer N" numbering, file paths, and function names from the prose entirely.
- Caption/source wording for the book:
  - Do not repeat `Source:` inside figure captions.
  - For case-study figures, use descriptive captions such as "for the El-Kom Al-Akhdar parcel."
  - In prose, describe figure origin as the team's case-study analysis / research work on an agricultural parcel in El-Kom Al-Akhdar, Shebin El-Kom District, Menoufia Governorate, Egypt.
  - Use FarmTrust for the built platform/project output, not as a label for every internal research graph.
- Figure plan: `docs/TASKS/T-12-figure-manifest.md` is the single source of truth for every figure/graph/screenshot/diagram (caption, source, type, target chapter, status, shortlist).
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

- Current writing sprint completed: detailed Chapters 1-10 revised inside `graduation_book_python/`, source wording cleaned, all 12 scientific comparison tables integrated, generated diagrams redesigned, table styling polished, English/Arabic abstracts expanded to the 1-2 page target, final app screenshots S-01..S-15 inserted as an interface evidence gallery, `book.json` synced, DOCX generated, and a 111-page PDF render visually checked. Remaining work: citation-style tightening if the university requires it.
