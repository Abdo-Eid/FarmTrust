# Land-Use Due-Diligence — Methodology & Monitoring Spec

**Purpose.** Turn a satellite record of a farm parcel into a *trustworthy, auditable* read of whether the land is productively used, whether that use is changing, how confident we are, and what should trigger caution — for a **non-technical decision-maker**. Calibrated primarily for **lending / valuation**, with the same engine re-tuned for compliance, abandonment-detection, and insurance.

**Two modes, one engine.**
- **Origination snapshot** — a single, maximally-defensible read of the field's whole history, used at loan origination / valuation. (The lender card.)
- **Ongoing monitoring** — the same engine re-run each new season, raising an alert only when a risk signal lights up. Used to service an existing exposure.

The companion `lender_land_use_card.html` is the snapshot for one parcel; this document is the framework behind it.

---

## 1. The core principle — keep the inference ladder visible

The satellite measures one narrow thing: how much living canopy is present, where and when. Everything a decision-maker cares about is *inferred* from the shape of that signal over time. The trustworthy move is to never let a judgment masquerade as a measurement. Every claim carries its **rung**:

| Rung | Example | Nature |
|---|---|---|
| **Measured** | "The field was green on this date." | Near-fact (modulo clouds/atmosphere) |
| **Pattern** | "A green-up → peak → senescence cycle occurred." | Strong on managed cropland |
| **Labelled** | "That cycle is winter cereal." | Needs calendar prior or ground truth |
| **Judgment** | "The land is productively used / declining." | Most inferred — decision-relevant |

Every output is therefore presented in **four layers, in order**: **Observed → Interpreted → Confidence → Watch.** Trust comes from the last box — stating what we *can't* tell them — not from a confident-sounding complete story.

---

## 2. What counts as meaningful activity, and the state vocabulary

Activity is a **temporal signature**, not a bright snapshot: the signature of cultivation is **repeated high-amplitude cycles that return to bare soil** (~0.15 → ~0.8 → back, then again). From that come the honest headline metrics — cycles per year (cropping intensity), agreement with the local calendar, and cumulative greenness as a rough productivity proxy.

We resolve to a **fixed vocabulary**, never a 0–100 score (a score invents precision and can't be audited):

- **Current state:** `Actively cropped (2+ cycles)` · `Single-cropped` · `Idle / fallow` · `Unclear (insufficient data)`
- **Change flag:** `Stable` · `Intensifying` · `Declining` · `Changed character` · `Too soon to tell`

Guard against the false positives: stable moderate greenness can be an orchard or weeds (used, but not the cycling we read); a lone green flush can be volunteers, not a planted crop.

---

## 3. Confidence — earned, shown, and shared with the absence gate

Confidence is computed from concrete, auditable inputs and surfaced as **High / Medium / Low with its reason**:

- **Data sufficiency** — how many *clean* (low-cloud) observations support each cycle, and how tightly spaced.
- **Signal clarity** — clean, high-amplitude cycles vs ambiguous wiggles.
- **Repetition** — does the pattern recur across years and agree with the calendar.
- **Corroboration** — multiple indices, or ground truth, agreeing.

**The absence gate (the most important rule).** Before we may ever say *idle* rather than *unclear*:

1. There is an expected-crop window (from the field's history / local calendar).
2. **Data-sufficiency test:** across that window, were the clean observations spaced *tighter than a green-up could hide in*? A crop cycle is a ~3-week green-up and a weeks-long peak. If clean-look gaps are shorter than that, a flat low signal genuinely means bare ground. If gaps are wider, the answer is **Unclear, not idle.**
3. Only if data is sufficient **and** greenness stays below the green-up threshold throughout → `Idle / fallow`.

A confident *idle* means **no detected crop this season**, *not abandoned* — fallow is legitimate management. Whether several idle seasons in a row is a problem is the decision-maker's call. (MSAVI, a soil-adjusted index, sharpens step 3: its cleaner bare-soil floor separates "genuinely bare" from "sparse green" more confidently than NDVI — see the technical report's MSAVI section.)

---

## 4. Baseline — the field's own history *and* its neighbours

- **Own history** defines the field's *expected rhythm* (how many cycles, when) — used to notice "this season is off for *this* field."
- **Neighbours** (comparable nearby parcels, same season) are the *weather control* — they tell us whether a deviation is field-specific or area-wide.

**Rule:** raise a field-specific flag only when the field deviates from its own history **and** diverges from its neighbours. If the whole neighbourhood moved together, that is environment (a dry year) — reported as *context*, not an alarm. "Comparable" must be defined (same cropping system, similar size, ideally same water source) or the control is noisy.

---

## 5. The origination snapshot (the card)

Contains, in plain language: the **state** + overall confidence; the four-layer read; a **two-year activity record** (the cycles, visually); a **track-record gauge** (how many seasons toward a certifiable trend); a **confidence breakdown** (each claim, its level, what it rests on); a **risk register** (the Watch box); and an explicit **"what this does not tell you"** boundary.

---

## 6. Ongoing monitoring — alert rules

The same engine re-run each new acquisition cycle. An alert fires when:

| Signal | Alert | Gate |
|---|---|---|
| No green-up in an expected-crop window | Possible fallow / idle | only if data-sufficiency test passes |
| Peak vigour / greenness-integral materially below own history **and** neighbours | Declining productivity (field-specific) | requires neighbour set |
| Green-up then mid-season collapse | In-season failure | — |
| Cycle shape/timing changes character | Use changed (crop switch) | — |
| Clean observations thin out | Confidence dropped — not readable this season | inverse of an alarm: suppress false signals |

A region-wide move is reported as *context*, never a field alarm. To run live, monitoring needs the **seasonal satellite feed** (the same pipeline that produced the snapshot).

---

## 7. Lending calibration (why lending-first)

Lending is the most demanding case, so designing for it yields the others as re-tunings of one dial:

- **Under-claim, never over-claim.** Bias conservative on every positive verdict — an optimistic read makes a bad loan.
- **Confidence is the product**, honestly calibrated — "likely double-cropped, medium confidence, here's why" beats a false-precise "productive: yes."
- **Track record is the headline**, and two years is explicitly *not* a trend — surfaced as a gauge ("2 of ~5 seasons"), never dressed up as certainty.
- **The Watch box is the risk register** the lender prices off.

Re-tunings: *compliance* biases hard against false "idle" accusations; *abandonment-hunting* lowers the bar to flag "possibly idle, go look"; *insurance* foregrounds the temporal/event panel.

---

## 8. Hard boundaries (non-negotiable)

- **Greenness ≠ yield ≠ income.** The card may say "actively cultivated, vigorous canopy" but never "productive" in the sense of *yielded well*. The Fall Armyworm case proves it — healthy canopy, failed crop. Yield, price, costs, income, water rights, and title stay permanently outside the read.
- **Resolution gate.** Below ~0.3 ha or for fragmented parcels, drop confidence and say "field too small to read reliably."
- **Data-integrity gate.** The read is only as good as the input is complete; a cross-check that the data is whole and matches its source gates every output — never build a verdict on partial or mismatched data.

---

## 9. Inputs required to operate

1. **Accurate field boundaries** — to compute a clean field-mean.
2. **A neighbour set** — comparable parcels for the weather-controlled baseline (without it, the *relative-risk* and several monitoring alerts are unavailable).
3. **As many years of history as available** — the track-record gauge is only as strong as the years behind it.
4. **A live seasonal feed** — for ongoing monitoring.

---

## 10. This parcel, as a worked example

A ~0.9 ha Menofia field, 2.1-year Sentinel-2 record (248 clean looks, 89%; 38–67 per cycle; 2–3 day gaps).

- **State:** Actively double-cropped — **high confidence** (a crop could not have hidden in those gaps).
- **Record:** winter cereal/forage → summer corn, four consecutive cycles, no missed season, returning to bare soil each turnover.
- **Track record:** stable across both years — **provisional** (2 of ~5 seasons); one change of character (winter wheat+berseem → berseem-only).
- **Risk register:** yield invisible (2025 corn was Fall-Armyworm-damaged yet read healthy); short record; crop-character change; small parcel; no neighbour baseline yet.
- **Does not tell you:** yield, income, costs, water rights, title.

The honest summary a lender can act on: *the collateral land is genuinely and consistently farmed, intensively, with a stable rotation — a real positive signal that kills the "claimed-farmland-actually-idle" risk — but the satellite is silent on what the land earns, and two years is a baseline, not a guarantee.*
