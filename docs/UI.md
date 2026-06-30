# UI/UX Concept Document — Institutional Land Intelligence

## Table of Contents
* Purpose
* Product Positioning
* Scope Alignment
* Primary User Goals
* Core User Flows
* System States
* Screens as Functional Surfaces
* Transitions Between Screens
* Decision Notes
* Visual Design Brief — Geospatial Financial Intelligence Style

## Purpose

Define the conceptual UI/UX in behavioral terms: what users need to do, how they move through the system, how the system behaves, and what each screen enables. This document avoids component-level styling details except where essential to product meaning (trust, clarity, evidence).

## Product Positioning

This product is a **geospatial financial intelligence system**. It treats agricultural land as a monitored asset and produces **decision-ready outputs**:

* status (stable / risk / uncertain)
* trend over time
* last-season performance
* explicit land risk flags
* satellite evidence coverage
* assessment confidence with rationale
* a shareable PDF record

The UI should feel like a **monitoring control surface + financial dossier**, not a farming app and not a generic AI dashboard.

## Scope Alignment

Single land AOI input (Egypt-wide, **1–200 feddan**). Outputs include:

* Land Status
* 2-Year Trend
* Last-Season Performance
* Land Risk Flags
* Satellite Evidence Coverage
* Assessment Confidence (band + rationale)
* PDF Export

## Primary User Goals

* Evaluate land suitability and risk quickly enough to support financing decisions without field visits.
* Monitor financed land for meaningful changes and early warning signals.
* Produce a shareable report that captures outcomes **and evidence**.
* Maintain a clear record of all submitted lands and their current state over time.

## Core User Flows

### Financing Review (New Land)

1. Enter the system and open the **Lands List** (primary hub).
2. Start a new land analysis and define AOI by drawing a polygon on the map.
3. Submit; land appears in the list with **Processing** status.
4. When complete, open **Land Summary**; review decision outputs, satellite evidence coverage, assessment confidence, and drivers.
5. Drill into **Evidence** if needed; export **PDF**; return to list.

### Monitoring (Existing Land)

1. Open **Lands List**; filter/sort to financed or flagged lands.
2. Open a land; review **latest summary** and trend deltas.
3. If risk/uncertainty is flagged, open **Evidence** to validate.
4. Export an updated PDF if required.

### Post-Season Review

1. Open a land from the list with a completed season.
2. Review last-season performance and multi-period trend.
3. Export final report for archival.

## System States

### First-Time / Empty System

* **User sees:** an empty Lands List with a short “what this system does” explanation.
* **User can do next:** start a new land analysis, view an example output snapshot, read “how it works”.

### Entry and Navigation

* **Loading:** navigation visible; fetch list data and keep the work area responsive.
* **Error:** list cannot load; show retry + contact guidance.
* **Success:** Lands List loads with statuses and primary actions.

### AOI Submission

* **Drawing:** user clicks land corners on the map; clicking near the first corner closes the polygon.
* **Editing:** before submission, user can drag polygon corners or clear and redraw the AOI.
* **Validation:** calculated polygon area must be within 1–200 feddan; block submission until the polygon is closed and valid.
* **Success:** submit the drawn polygon geometry and calculated area; the land enters the processing flow.

### Analysis Run (Asynchronous)

* **Waiting:** Lands List shows Processing + last update time; optional progress details in land status view.
* **Error:** Lands List shows Failed; open failure reason; allow resubmit.
* **Success:** Lands List shows Review Ready; Land Summary becomes available.

### Summary and Evidence

* **Loading:** show partial data if available; allow return to list.
* **Error/Partial:** show known values; mark evidence limitations; explain assessment-confidence impact and what is missing.
* **Success:** decision outputs visible; satellite evidence coverage and assessment confidence explicit; evidence accessible to validate or challenge.

### PDF Export

* **Loading:** show generation progress; allow return to summary.
* **Error:** show reason; allow retry.
* **Success:** report downloadable/shareable; return to summary or list.


## Screens as Functional Surfaces

### Screens Designed (11 total) — Quick Reference

1. **Lands List Control Hub** — Primary operational hub; sidebar, stat cards, lands table with status, land risk, satellite evidence coverage, and assessment-confidence columns.
2. **Add Land AOI Input** — AOI capture; draw-only polygon input. On desktop, form is left and map is right; on mobile, map appears above the form. Method: click land corners on the map, click near the first corner to close, drag corners before submit, and validate calculated area against 1–200 feddan.
3. **Land Processing Status** — Job progress display; circular progress (left), pipeline timeline (right). Steps: AOI Validation ✓, Satellite Data ✓, Vegetation Analysis ⏳, Risk Modeling ⏳.
4. **Geospatial Evidence Workbench** — Analyst deep-dive; map canvas (left 70%) + analytical sidebar (right 30%) with NDVI chart, anomalies, notes.
5. **System Operations Control** — Backend/API status panel; left nav for system sections, main panel with pipeline status, API connection, and portal notes.
6. **Active Monitoring Queue** — High-risk alert dashboard; stat cards (18 alerts, 5 signals, 3 visits, 8,450 feddan), financed assets table with trend sparklines.
7. **Portal Launch Screen** — Direct entry surface; centered brand panel with a short description of the interface and a primary action into the Lands List.
8. **Lender Report Card** — Evidence-grounded decision brief rendered from the evidence packet; route `/lands/[id]/packet`. Displays observed conditions, interpreted drivers, confidence levels, watch claims with track record, land risk vs evidence limitation, and cautious indicators. Linked from the Land Summary action bar.
9. **Group/Portfolio Summary** — Collection view for portfolio monitoring; route `/lands/groups/[id]`. Aggregated risk signals and trend snapshots across grouped lands.
10-11. **Lands List Variants** — Responsive/state alternatives of main list (2 additional variants).

### Entry

**Purpose:** route directly to the work surfaces.
**Decisions:** which land or dashboard to open next.
**Information required:** none beyond the selected navigation target.

### Lands List (Primary Hub)

**Purpose:** operational hub for all land assets across lifecycle stages.
**Decisions:** what to open next, what needs attention, what to start/resubmit/export.
**Information required:**

* Land ID / name
* Area (feddan), governorate
* Lifecycle status (Processing, Review Ready, Monitoring, Failed)
* Last update
* High-level land risk signal + satellite evidence coverage + assessment-confidence band (at-a-glance)

**Important:** Lands List should not be a map view. It is a **queue/control list**.

### Add Land (AOI Input)

**Purpose:** capture land definition and trigger analysis.
**Decisions:** AOI shape & area; ensure constraints met.
**Information required:** polygon coordinates from drawn map corners; calculated feddan area; constraint confirmation.
**Current portal behavior:** draw polygon only; point+area and GeoJSON upload are not primary flows. The mock API keeps existing fixture lands and returns newly submitted lands as queued until backend processing is connected.

### Land Status Detail (Within a Land)

**Purpose:** keep users informed during asynchronous processing without leaving context.
**Decisions:** wait, return later, resubmit if failed.
**Information required:** run state, timestamps, failure reason if any.

### Land Summary (One-Page Decision Brief)

**Purpose:** decision-ready brief supporting financing and monitoring actions.
**Decisions:** proceed/hold/decline/monitor-only + whether evidence review is required.

**What must be present:**

* Land Status
* Trend (2-year)
* Last-season performance
* Land risk flags (with drivers)
* Satellite evidence coverage
* Assessment-confidence band + rationale
* Evidence entry points: action bar offers **Workbench** (deep-dive analyst view), **Evidence** (supporting data drill-down), **Report Card** (grounded evidence packet at `/lands/[id]/packet`), and **Export PDF** (portable record)

#### Decision Support Rules

* Outputs are consistent and generic: **Proceed**, **Hold**, **Decline**, **Monitor-Only**.
* Recommendation is tied to explicit drivers: status, trend shifts, land risk flags, satellite evidence coverage, and assessment-confidence band.
* **Low assessment confidence or missing evidence defaults to Hold**, with a clear reason and what to review.

#### Assessment Confidence & Evidence Handling

* Assessment confidence is displayed as a band with a brief rationale; it means confidence in FarmTrust's assessment, not confidence in the land itself.
* Satellite evidence coverage is displayed separately from land risk flags.
* Missing/weak satellite evidence is surfaced inline and tagged to impacted outputs.
* Uncertainty alters the recommended action and highlights the evidence to inspect.

### Evidence / Data (Optional Surface)

**Purpose:** provide supporting data for summary outputs.
**Decisions:** confirm or challenge conclusions; determine escalation.
**Information required:** time series snapshots, contextual map views (where needed), data notes.

#### Escalation & Exception Rules

* Evidence is surfaced proactively when land risk flags are new/worsening or conflict with summary.
* If evidence contradicts recommendation, shift to **Hold** and request review.

### Report Card & Report Export

**Report Card (On-Screen):** a grounded evidence packet rendered as a lender-facing decision brief at route `/lands/[id]/packet`. Built during `report_generation` from land assessment, season windows, quality metrics, and run metadata. Displays observed conditions, interpreted drivers, confidence levels, watch claims with track record, risk register (land risk vs evidence limitation), and cautious indicators. Links to this card appear in the Land Summary action bar and are separate from PDF export.

**Report Export (PDF):** a portable, archival version of summary outputs + key evidence highlights + satellite evidence coverage + assessment-confidence rationale for sharing or case attachment.

**Purpose (both):** portable and shareable records; the Report Card is the in-app evidence surface, while the PDF is the downloadable artifact.
**Decisions:** which report surface to review or share; export now/later; attach to case.
**Information required:** summary outputs + key evidence highlights + satellite evidence coverage + assessment-confidence rationale.

### Admin / Settings (Minimal)

**Purpose:** surface lightweight system and backend configuration.
**Decisions:** portal/pipeline configuration checks and operational notes.
**Information required:** API endpoint, deployment status, interface notes.

## Transitions Between Screens

* Entry → Lands List: navigation selects the list view.
* Lands List → Add Land: new analysis initiated.
* Add Land → Land Status: land created as queued/processing, then summary becomes available when analysis succeeds.
* Lands List → Land Status: open Processing/Failed item for progress/error details.
* Lands List → Land Summary: open Review Ready/Monitoring item.
* Land Summary → Evidence: drill down to validate drivers.
* Land Summary → PDF Export: generate report.
* Any Screen → Error State: load/validation failure; retry or return to list.

## Decision Notes

* One combined list centered on lands; analysis runs are recorded inside each land’s history.
* One summary screen; role emphasis changes content prominence, not layout.
* Lands List stays a **control surface**, not a map canvas.
* Mock fixture lands remain in the portal to present all states; only newly submitted polygon inputs are intended to flow into real processing once backend integration is connected.


# Visual Design Brief — Current Portal Style

## Design Tokens (Current Portal Implementation) — Quick Reference

**Colors:**
- **Primary:** `#16A085` / `#1ABC9C` (Teal) — primary buttons, active controls, analytical accents
- **Dark Primary:** `#0D2B27` (Dark Teal) — sidebar and deep navigation areas
- **Secondary:** `#D4A373` (Gold/Sand) — optional highlights and secondary accents
- **Background Light:** `#F3F1EB` (Warm Sand) — page background
- **Background Dark:** `#082420` / `#0D2B27` (Very Dark Teal) — dark mode and deep navigation surfaces
- **Surfaces Light:** `#FFFFFF` (White) — panels, cards, tables
- **Surfaces Dark:** `#2C3A35` (Dark Green) — dark mode work areas
- **Table Headers:** `#E8E6DF` (light) / `#25302C` (dark) — section dividers
- **Status Colors:** Green (active), Amber (caution), Red (risk)

**Typography:** Inter (body + display) — neutral technical report style  
**Borders:** 0–4px radius (minimal, institutional feel)  
**Icons:** Material Symbols Outlined (Google Fonts CDN) — thin line style  
**Patterns:** 40px tech-grid for geospatial; geo-overlay gradient for headers  
**Shadows:** Minimal, foreground separation only

## 1. Design Intent

Create an interface for a **geospatial land risk intelligence system for financial institutions**.
It must communicate: **institutional trust, analytical clarity, engineered reliability, evidence-first decisions**.
The current portal expresses this through a warm sand workspace, dark teal navigation, white report panels, compact tables, thin Material Symbols icons, and teal analytical actions.

## 2. Overall Visual Personality

**Tone:** controlled, modern, structured, institutional.
**Feel:** “monitoring control surface” + “financial dossier”.
**Energy:** teal accents and compact analytical panels keep the interface active without becoming playful.

## 3. Layout System

* Strong grid alignment and clear zones.
* Sections behave like **structured panels** using white surfaces, thin borders, and restrained shadows.
* Lands List: data-forward queue; no map panel inside list.
* Page background uses warm sand; work areas use white cards/panels; navigation uses dark teal.

## 4. Shape Language

* Minimal-to-moderate rounding: most surfaces use 2–4px; status/risk chips may use pill shapes for quick scanning.
* Thin borders, restrained shadows.
* Header bands and top bars may use teal identity treatments, but content panels remain calm and structured.

## 5. Color System (Current Portal)

**Primary Palette:**
- **Primary accent:** Teal (`#16A085`, `#1ABC9C`) — buttons, links, active controls, analytical highlights.
- **Dark navigation:** Dark Teal (`#0D2B27`, `#082420`) — sidebar and deep navigation areas.
- **Secondary accent:** Gold/Sand (`#D4A373`) — optional highlights and secondary emphasis.
- **Light background:** Warm Sand (`#F3F1EB`) — page background, neutral comfort.
- **Dark background:** Very Dark Teal (`#082420`) — deep navigation/dark surfaces.
- **Work surfaces:** White (`#FFFFFF`) / Dark Green (`#2C3A35`) — panels, tables, primary areas.
- **Status signals:** Green/Amber/Red — stable/processing/risk indicators only.

**Rule:** Warm neutrals carry the workspace; teal carries product identity and action; green/amber/red are reserved for status, confidence, and risk meaning.

## 6. Typography

Neutral technical sans-serif, report-like hierarchy.
Prioritize:

1. status + recommendation
2. key numbers
3. section titles
4. supporting text

Avoid trendy decorative fonts.

## 7. Data Presentation Style

* Analytical, not decorative.
* Minimal gradients; clear axes/labels/units.
* Avoid flashy animations; clarity > spectacle.

## 8. Component Style

* Panels resemble report sections with crisp headers.
* Buttons are secondary; data is primary.
* Use one “identity focal zone” (header band with subtle geometric overlays) to add modern energy without clutter.

## 9. Motion and Interaction Tone

Subtle fades only.
No bouncy, sliding, or playful motion.

## 10. Iconography

Thin technical line icons (GIS/analysis vibe).
Avoid expressive or cartoon icons.

## 11. Avoid

Neon AI gradients, bubbly cards, excessive rounding, playful color blocking, startup hero illustrations.

## 12. Final Style Positioning Statement

**Institutional geospatial financial intelligence interface: warm neutral surfaces, dark teal navigation, white report panels, compact analytical tables, and teal action accents. The interface should feel structured and operational, not consumer-farming or marketing-led.**

## 13. Visual Priority Hierarchy (Non-Negotiable)

All screens must preserve this visual dominance order:

1. Decision Output & Status
2. Confidence Band
3. Risk Drivers
4. Data & Evidence Access
5. Interface Chrome

Constraint: interface chrome (sidebar, top bar, panels, headers, framing elements) must never visually overpower decision content.

## 14. Expressive Zone Limitation

The page header band and dark teal navigation are the primary identity zones in the interface.

Constraint: all main content surfaces must remain calm, neutral, structured, and free from decorative treatment.

## 15. Surface Contrast Levels

| Surface Type | Contrast Role |
|--------------|---------------|
| Background atmosphere | Lowest contrast |
| Primary work surfaces (panels, tables) | Medium contrast |
| Data zones (tables, charts) | Highest clarity |

Constraint: data layers must always read clearly above atmospheric textures and background motifs.

## 16. Information Density Principle

The interface should read like a financial reporting tool: compact, efficient, and structured.

Constraint: avoid excessive whitespace that makes the system feel light, consumer-like, or SaaS-marketing oriented.

## 17. Status Color Usage Rule

Status colors are functional signals only.

Allowed usage:

* status labels
* risk icons
* assessment-confidence bands

Disallowed usage:

* panel backgrounds
* decorative color blocks
* large non-functional UI areas

## 18. Shadow Philosophy

Shadows are permitted only to separate foreground surfaces from the atmospheric background.

Constraint: shadows must not create floating-card effects or playful depth language.

## 19. Map Usage Rule

Maps are evidence tools, not primary interface surfaces.

Constraint: primary workflow remains list, summary, and analysis first; maps appear only in evidence or contextual drill-down views.

## 20. Anti-SaaS Guardrail

Behavioral check: if a visual change makes the product feel lighter, friendlier, playful, or app-like, treat it as likely incorrect for this system and re-evaluate against institutional intent.
