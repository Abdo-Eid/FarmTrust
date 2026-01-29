# Contributing to FarmTrust

Thanks for contributing.

## Quick start
1) Read: `docs/PROJECT.md`, `docs/ENGINEERING.md`, `docs/DECISIONS.md`, `docs/index.md`
2) Declare your role + outputs to the lead before starting work.

## Work tracking (issue-first with pragmatic exceptions)
Create an Issue when:
- it's planned work
- it requires coordination or review
- Work spans multiple roles or interfaces
- It touches contracts/architecture or shared truth
- It is more than 1-2 days of effort
- It affects the demo path

PR-only is OK when:
- The change is small and contained (<= half day)
- It is refactor/cleanup with no interface changes
- It is a quick fix that does not need planning

Untracked is OK when:
- The work is exploratory or ambiguous
- The result may be discarded
- It does not affect demo path or shared interfaces

If a spike becomes real work, open an Issue and link it retroactively.

## Branch naming
Use `role/short-topic`.
Examples by role: `frontend/aoi-draw`, `ml-ts/gap-fill`, `ml-seasonal/season-patterns`, `ml-scoring/season-rules`, `ingestion/stac-fetch`, `lead/demo-path`.
Other naming styles (not default): label-based branches like `feature/aoi-draw`, `bug/fix-job-log`, `chore/update-docs`.

## Commit messages
Use Conventional Commits and include an issue close token at the end when there is an Issue.
Example:
```
feat(api): add job status endpoint (Closes #123)
```

## Pull requests
- Do not push to `main`. Always create a branch and open a PR.
- Link to an Issue when applicable.
- Lead may merge without review; request a review when possible.
- Update docs if you change shared scope, interfaces, or decisions.

## Doc updates (Aha!Kit rules)
- Product/scope/roadmap/options/open questions -> `docs/PROJECT.md`
- Architecture/ops/interfaces/pipeline/risks -> `docs/ENGINEERING.md`
- Decisions -> `docs/DECISIONS.md` (append-only)
- Execution detail -> a single workstream file in `docs/WORKSTREAMS/`

## Not sure where to write?
Use `docs/inbox.md` for raw capture. Do not edit or reorganize existing inbox content.
