# Notebooks

This folder contains the current staged review notebooks for the FarmTrust Phase A pipeline.

## Recommended reading order

1. `01-preprocessing_ndvi.ipynb`
    - Review duplicate merging, usability filtering, smoothing, and gap metrics.

2. `02-seasonal_review.ipynb`
    - Review detected season windows over the smoothed NDVI signal.

3. `03-phase_a_assessment_story.ipynb`
    - Review the full Phase A story: summary outputs, explicit gap diagnostics, season evidence, and risk flags.

## Notebook roles

- `01-preprocessing_ndvi.ipynb`
    - Preprocessing verification and visual QA.
- `02-seasonal_review.ipynb`
    - Seasonal-detection verification and season-level evidence review.
- `03-phase_a_assessment_story.ipynb`
    - Final Phase A assessment walkthrough and evidence notebook.

## Team guidance

- Prefer the notebooks above in order when validating a fresh AOI run.
- Treat notebooks as evidence and review artifacts, not the source of truth for shared implementation.
- Shared behavior belongs in `farmtrust_core/` and `scripts/`, with notebooks used to verify and explain it.
