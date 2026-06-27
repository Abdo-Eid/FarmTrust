# T-08 - Crop Research Review And Synthesis

## Goal

Review the crop-classification research work merged from PR #10 and PR #11, refine each part after testing, and decide whether to combine the strongest ideas into one coherent research direction.

This task manages the work. The detailed running log and graduation-book evidence are kept in `docs/documentations/02-crop-research-review-log.md`.

## Scope

IN:
- Review PR #10 field-level crop mapping report and notebooks.
- Test, inspect, or convert PR #10 notebooks as needed before trusting them as evidence.
- Review PR #11 XGBoost notebooks, research scripts, validation docs, and dependency changes.
- Refine research docs so claims, limitations, and commands match the branch.
- Compare both research paths and decide what is worth combining.
- Preserve a clean evidence trail for the graduation book.

OUT:
- Production FarmTrust crop-category output.
- FarmTrust canonical land assessment contract changes unless explicitly approved later.
- Treating notebook metrics as production validation.
- Committing generated datasets, model binaries, pickles, or local research outputs.

## Role Split

- Driver: run the review, tests, notebook checks, and doc refinements.
- Reviewer: verify claims, reproducibility, script behavior, and validation strength.
- Curator: maintain the long-form review log and keep graduation-book evidence organized.

## Chosen approach

Review PR #10 first, because its notebooks are currently blocked by nbformat compatibility and its report contains the broader LSTM/ensemble experiment history.

Then review PR #11, because it has executable research scripts and AOI validation evidence that can be tested more directly.

After both reviews, compare them across target labels, feature schema, preprocessing, validation strength, artifact readiness, and usefulness for FarmTrust. Only then decide whether to synthesize one combined crop-classification research direction.

## Task List

- [x] Create active task document for the crop research review.
- [x] Create initial long-form review log document.
- [x] Review PR #10 report claims and scope language.
- [x] Validate or convert PR #10 notebooks to nbformat v4 so trusted notebook inspection works.
- [x] Test or inspect PR #10 notebook outputs after conversion/validation.
- [x] Build YieldSAT feature-store extraction (`05-yieldsat_crop_mapping_feature_store`) and baseline (`06-yieldsat_crop_mapping_baseline`) notebooks.
- [x] Replace old `crop_mapping_v1_reflectance_baseline.ipynb` with `06-yieldsat_crop_mapping_baseline.ipynb`.
- [x] Test selected weather retrieval from free Open-Meteo API for a sample Egypt bbox — succeeded.
- [x] Delete superseded PR #10 notebooks: `crop_mapping_full_features_final`, `crop_mapping_light_reduced_final`, `crop_mapping_aggressive_feature_reduction`.
- [x] Retire old PR #10 report after preserving useful findings in the research review log.
- [x] Refine PR #10 docs based on testing and notebook review.
- [ ] Review PR #11 notebooks with trusted notebook tooling.
- [ ] Run lightweight PR #11 script checks such as compile and `--help`.
- [ ] Fix stale PR #11 documentation commands that reference removed training code.
- [ ] Fix or document the sibling import behavior in `diagnose_aoi_shared_5label.py`.
- [ ] Update dependency docs so the `ml` extra is no longer described as empty.
- [ ] Compare PR #10 and PR #11 research directions.
- [ ] Decide whether to combine both works into one follow-up research path.
- [ ] Record final review outcome and graduation-book summary material.

## Feedback Log

- 2026-06-27: User wants a normal document under `docs/documentations/` to track the work/log for later graduation-book use, plus an active task to manage the review.
- 2026-06-27: Initial review direction: test/refine PR #10, test/refine PR #11, then possibly combine the good parts from both.
- 2026-06-27: User approved converting the four PR #10 notebooks in place so existing paths and docs stay valid.
- 2026-06-27: User clarified that the documentation log should focus on research, technical data/model work, experiments, evidence, and findings, not repo activity.
- 2026-06-27: User confirmed the three remaining PR #10 crop-mapping notebooks do not introduce new value beyond the cleaner feature-store approach and approved deleting them.
- 2026-06-27: User approved removing the old PR #10 report after preserving its useful historical findings in the research review log.

## Decisions

- This review keeps crop classification research-only unless the user explicitly promotes it later.
- The detailed work log lives in `docs/documentations/02-crop-research-review-log.md`, not only in this task file.
- The documentation log is for research/data/model evidence; repo process tracking stays in this task file.
- PR #10 and PR #11 will be reviewed separately before synthesis.
- The old PR #10 raw-raster notebook variants are retired; useful findings stay in the review log, while active experimentation moves through the YieldSAT feature-store notebooks.
- The old PR #10 report is deleted; `docs/documentations/02-crop-research-review-log.md` is now the source for preserved PR #10 evidence and limitations.

## Open Questions

- Which PR #10 model path should be treated as the main candidate after testing: full-feature ensemble, reduced LSTM, or report-only evidence?
- Should PR #11 scripts be made package-executable with `python -m`, or is file-script execution enough for this research branch?
- What evidence format is needed for the graduation book: screenshots, tables, narrative, or all three?

## Knowledge to Keep

- PR #10 targets field-level `wheat / corn / other` screening and reports strong internal grouped metrics, but still needs external validation.
- PR #10 notebooks were converted in place to nbformat v4.5 and normalized with missing cell IDs so trusted `nb read --no-output` inspection works.
- Three PR #10 raw-raster variants were deleted after review because the feature-store pipeline supersedes them: full features, light reduced features, and aggressive feature reduction.
- The old PR #10 report was useful for historical framing but became stale after the feature-store baseline; its durable points were preserved in the review log before deletion.
- PR #11 targets research-only XGBoost AOI validation. The Morocco-only model predicted the known Corn AOI correctly with low confidence, while the AOI-compatible five-label model failed by predicting Wheat.
- Current FarmTrust engineering truth still says crop category is not part of the current land assessment contract.
- The final synthesis must preserve preprocessing details: feature order, scaling, SCL masking assumptions, artifact paths, and validation limitations.

## Done Summary

Pending. This task is active.
