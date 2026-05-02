---
name: guidance
description: Cross-cutting guardrails for commits, verification, debugging, and basic security.
---

# Guidance

## Commits
- Prefer conventional commits when committing: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`.
- Keep commits small and descriptive (why > what).
- Never commit secrets (`.env`, tokens, credentials).

## Verification (No TDD Enforcement)
- Prefer running existing tests/build.
- If tests exist: run the smallest relevant scope.
- If no tests: define a lightweight verification (smoke run, sample input/output).
- Always state what you verified and what you did not verify.

## Debugging
1. Reproduce (exact steps and error)
2. Localize (where it happens)
3. Hypothesize (2-3 likely causes)
4. Test hypotheses (logs/inspection)
5. Fix the smallest root-cause change
6. Verify (same repro + quick regression check)

## Security Basics
- Treat user input as untrusted.
- Do not log sensitive values.
- Avoid adding unvetted dependencies.
