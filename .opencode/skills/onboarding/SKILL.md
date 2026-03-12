---
name: onboarding
description: Use when you are in a repo you need to get familiar with before making changes.
---

# Onboarding

## When to Use
- You're new to this repo
- You're unsure how to run/test/build it
- You need to understand structure and risks before changing code

## What to Do
1. Identify project type (languages, frameworks, build tool)
2. Find how to run it (README, scripts, makefiles, CI)
3. Map the important directories and boundaries
4. Identify how testing/verification works (commands, locations)
5. Identify risk areas (auth, money, migrations, data loss)
6. Identify contribution patterns (naming, linting, commit/PR conventions)
7. Get git familiarity (current branch, uncommitted changes, recent commits)

## Output (Required)
Produce a "Repo Brief":
- Purpose (1 line)
- Key commands (install/test/build/dev) or "unknown" if not found
- Structure (5-10 bullets)
- Guardrails (what not to break)
- Biggest risk (1 bullet)
- Open question (0-1; only if truly blocked)

## Integration
- If you are about to implement something new, load `brainstorming` next.
- Keep `guidance` in mind for commits, testing, debugging, and security guardrails.
