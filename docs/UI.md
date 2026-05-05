# UI/UX Concept Document — Institutional Land Intelligence (MVP)

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

Define the conceptual UI/UX for the MVP in behavioral terms: what users need to do, how they move through the system, how the system behaves, and what each screen enables. This document avoids component-level styling details except where essential to product meaning (trust, clarity, evidence).

## Product Positioning

This product is a **geospatial financial intelligence system**. It treats agricultural land as a monitored asset and produces **decision-ready outputs**:

* status (stable / risk / uncertain)
* trend over time
* last-season performance
* explicit risk flags
* confidence with rationale
* a shareable PDF record

The UI should feel like a **monitoring control surface + financial dossier**, not a farming app and not a generic AI dashboard.

## Scope Alignment

Single land AOI input (Egypt-wide, **1–200 feddan**). Outputs include:

* Land Status
* 2-Year Trend
* Last-Season Performance
* Risk Flags
* Confidence (band + rationale)
* PDF Export

## Primary User Goals

* Evaluate land suitability and risk quickly enough to support financing decisions without field visits.
* Monitor financed land for meaningful changes and early warning signals.
* Produce a shareable report that captures outcomes **and evidence**.
* Maintain a clear record of all submitted lands and their current state over time.

## Core User Flows

### Financing Review (New Land)

1. Enter the system and open the **Lands List** (primary hub).
2. Start a new land analysis and define AOI (polygon or point + area).
3. Submit; land appears in the list with **Processing** status.
4. When complete, open **Land Summary**; review decision outputs, confidence, and drivers.
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

* **Loading:** navigation visible; authenticate and fetch list data; allow sign-out.
* **Error:** session invalid or list cannot load; show retry + contact guidance; allow sign-out.
* **Success:** Lands List loads with statuses and primary actions.

### AOI Submission

* **Loading:** inline validation for Egypt boundary + area limits; allow edits.
* **Error:** show exact constraint violated and a clear fix path; block submission.
* **Success:** confirm submission; return to Lands List with new item in Processing.

### Analysis Run (Asynchronous)

* **Waiting:** Lands List shows Processing + last update time; optional progress details in land status view.
* **Error:** Lands List shows Failed; open failure reason; allow resubmit.
* **Success:** Lands List shows Review Ready; Land Summary becomes available.

### Summary and Evidence

* **Loading:** show partial data if available; allow return to list.
* **Error/Partial:** show known values; mark gaps; explain confidence impact and what is missing.
* **Success:** decision outputs visible; confidence explicit; evidence accessible to validate or challenge.

### PDF Export

* **Loading:** show generation progress; allow return to summary.
* **Error:** show reason; allow retry.
* **Success:** report downloadable/shareable; return to summary or list.


## Screens as Functional Surfaces

### Screens Designed (9 total) — Quick Reference

1. **Lands List Control Hub** — Primary operational hub; sidebar, stat cards, lands table with status/risk/confidence columns.
2. **Add Land AOI Input** — AOI capture; two-column form (left: fields, right: map preview). Methods: polygon upload or point+area. Validates 1–200 feddan.
3. **Land Processing Status** — Job progress display; circular progress (left), pipeline timeline (right). Steps: AOI Validation ✓, Satellite Data ✓, Vegetation Analysis ⏳, Risk Modeling ⏳.
4. **Geospatial Evidence Workbench** — Analyst deep-dive; map canvas (left 70%) + analytical sidebar (right 30%) with NDVI chart, anomalies, notes.
5. **System Admin Control** — User management table; left nav (User Management selected), main panel with 5 admin users, roles, status, actions.
6. **Active Monitoring Queue** — High-risk alert dashboard; stat cards (18 alerts, 5 signals, 3 visits, 8,450 feddan), financed assets table with trend sparklines.
7. **Institutional Login Screen** — Auth entry; centered form with email, password, institutional branding.
8-9. **Lands List Variants** — Responsive/state alternatives of main list (2 additional variants).

### Entry / Login

**Purpose:** validate access and route to work.
**Decisions:** none beyond auth success/failure.
**Information required:** credentials/session token.

### Lands List (Primary Hub)

**Purpose:** operational hub for all land assets across lifecycle stages.
**Decisions:** what to open next, what needs attention, what to start/resubmit/export.
**Information required:**

* Land ID / name
* Area (feddan), governorate
* Lifecycle status (Processing, Review Ready, Monitoring, Failed)
* Last update
* High-level risk signal + confidence band (at-a-glance)

**Important:** Lands List should not be a map view. It is a **queue/control list**.

### Add Land (AOI Input)

**Purpose:** capture land definition and trigger analysis.
**Decisions:** AOI shape & area; ensure constraints met.
**Information required:** polygon coordinates or point + area; constraint confirmation.

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
* Risk flags (with drivers)
* Confidence band + rationale
* Evidence entry points

#### Decision Support Rules

* Outputs are consistent and generic: **Proceed**, **Hold**, **Decline**, **Monitor-Only**.
* Recommendation is tied to explicit drivers: status, trend shifts, risk flags, confidence band.
* **Low confidence or missing evidence defaults to Hold**, with a clear reason and what to review.

#### Confidence & Uncertainty Handling

* Confidence displayed as a band with a brief rationale.
* Missing/weak data is surfaced inline and tagged to impacted outputs.
* Uncertainty alters the recommended action and highlights the evidence to inspect.

### Evidence / Data (Optional Surface)

**Purpose:** provide supporting data for summary outputs.
**Decisions:** confirm or challenge conclusions; determine escalation.
**Information required:** time series snapshots, contextual map views (where needed), data notes.

#### Escalation & Exception Rules

* Evidence is surfaced proactively when risk flags are new/worsening or conflict with summary.
* If evidence contradicts recommendation, shift to **Hold** and request review.

### Report Export (PDF)

**Purpose:** portable record for sharing/archival.
**Decisions:** export now/later; attach to case.
**Information required:** summary outputs + key evidence highlights + confidence rationale.

### Admin / Settings (Minimal)

**Purpose:** manage access, roles, permissions.
**Decisions:** role assignment, access changes.
**Information required:** users, roles, permissions.

## Transitions Between Screens

* Entry/Login → Lands List: auth success + list loaded.
* Lands List → Add Land: new analysis initiated.
* Add Land → Lands List: land created as Processing.
* Lands List → Land Status: open Processing/Failed item for progress/error details.
* Lands List → Land Summary: open Review Ready/Monitoring item.
* Land Summary → Evidence: drill down to validate drivers.
* Land Summary → PDF Export: generate report.
* Any Screen → Error State: load/validation failure; retry or return to list.

## Decision Notes

* One combined list centered on lands; analysis runs are recorded inside each land’s history.
* One summary screen; role emphasis changes content prominence, not layout.
* Lands List stays a **control surface**, not a map canvas.


# Visual Design Brief — Geospatial Financial Intelligence Style (Updated)

## Design Tokens (From Stitch Implementation) — Quick Reference

**Colors:**
- **Primary:** `#3D5A4B` (Deep Moss Green) — sidebar, active nav, primary buttons
- **Secondary:** `#D4A373` (Gold/Sand) — highlights, interactive elements
- **Background Light:** `#F3F1EB` (Warm Sand) — page background
- **Background Dark:** `#1A2321` (Very Dark Green) — dark mode background
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
Avoid: consumer farming aesthetic, generic AI gradients, marketing analytics SaaS vibes.

## 2. Overall Visual Personality

**Tone:** controlled, modern, structured, authoritative.
**Feel:** “monitoring control surface” + “financial dossier”.
**Energy:** introduce *engineered geometry and a focal zone* so it doesn’t feel dusty or buried.

## 3. Layout System

* Strong grid alignment and clear zones.
* Sections behave like **structured panels**, not floating bubbly cards.
* Lands List: data-forward queue; no map panel inside list.
* Use **contained surfaces + subtle technical background motifs** (thin arcs/lines) to signal system intelligence.

## 4. Shape Language

* Minimal rounding (0–4px), no pill-heavy UI.
* Thin borders, restrained shadows.
* Geometric header planes/overlays allowed (subtle, structured).

## 5. Color System (Rebalanced: less “earth”, more “system”)

**Primary Palette:**
- **Primary accent:** Deep Moss Green (`#3D5A4B`) — sidebar, active states, authority zones.
- **Secondary accent:** Gold/Sand (`#D4A373`) — highlights, interactive elements, secondary buttons.
- **Light background:** Warm Sand (`#F3F1EB`) — page background, neutral comfort.
- **Dark background:** Very Dark Green (`#1A2321`) — dark mode, deep atmospheric.
- **Work surfaces:** White (`#FFFFFF`) / Dark Green (`#2C3A35`) — panels, tables, primary areas.
- **Status signals:** Green/Amber/Red — stable/processing/risk indicators only.

**Rule:** Institutional warm neutrals for comfort; moss-green authority accents for rigor; minimal color for functional signals.

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

**Institutional geospatial financial intelligence interface: warm neutral surfaces for comfort, slate/black analytical contrast for rigor, deep moss authority accents, and subtle engineered geometry to signal system intelligence—without drifting into generic SaaS or AI aesthetics.**

## 13. Visual Priority Hierarchy (Non-Negotiable)

All screens must preserve this visual dominance order:

1. Decision Output & Status
2. Confidence Band
3. Risk Drivers
4. Data & Evidence Access
5. Interface Chrome

Constraint: interface chrome (panels, headers, navigation, framing elements) must never visually overpower decision content.

## 14. Expressive Zone Limitation

The geometric header band is the only expressive or atmospheric zone in the interface.

Constraint: all non-header surfaces must remain calm, neutral, structured, and free from decorative treatment.

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
* confidence bands

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