# T-13 — Pipeline-Improvement Triage & Proposal

## Links

* TASK: T-11 (origin — isolated parcel analysis to pipeline improvement)
* TASK: T-09 (assessment window & season calendar), T-10 (land-status rules)
* DECISIONS: `2026-06-30 — Decision: Grounded report evidence packet ...`

## Goal

Carried from T-11 when it closed: T-11 compared the isolated one-parcel analysis against the production pipeline and shipped the high-confidence findings directly as Layers 1–7 (smoother/detector refactor, evidence packet, report card, assistant). What remains is the *triage and write-up* that T-11 deferred — turning the leftover differences into an explicit, prioritized improvement plan rather than ad-hoc implementation.

Decide which observed differences are **true pipeline defects**, which are **reporting gaps**, which are **one-parcel anomalies**, and which **need more validation parcels** before acting — then produce a prioritized improvement proposal in minimal, independently-shippable slices.

## Scope

### IN

- Triage the remaining T-11 differences (those not already shipped in Layers 1–7) into: true defect / reporting gap / one-parcel anomaly / needs-more-parcels.
- Pull in additional validation parcels where a single-parcel finding is not yet trustworthy.
- Produce a prioritized pipeline-improvement proposal with minimal implementation slices, each scoped enough to become its own follow-up task.

### OUT

- Implementing the slices themselves (each becomes its own task once prioritized).
- Re-deriving the findings already shipped via T-11 Layers 1–7.

## Task List

- [ ] Decide which differences are true pipeline defects, which are reporting gaps, which are one-parcel anomalies, and which need more validation parcels. (carried from T-11)
- [ ] Produce a prioritized pipeline-improvement proposal with minimal implementation slices. (carried from T-11)

## Feedback Log

- 2026-07-01: Created when T-11 closed. T-11 shipped its high-confidence findings as Layers 1–7; its two remaining analysis/proposal items (triage + prioritized proposal) were carried here. The date-window and land-status comparison items went to T-09 and T-10 respectively; the report/LLM explanation-value comparison went to T-02 validation.

## Open Questions

- How many additional validation parcels are needed before a one-parcel finding is promoted to a real defect?

## Done Summary

- Pending.
