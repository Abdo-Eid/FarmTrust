# Inbox

Use this folder for raw intake documents.
Drop files directly under `docs/inbox/` (no nested docs folder).

## Naming
- Prefer: `YYYY-MM-DD-short-topic.md`

## Metadata
Use YAML front matter at the top of each inbox doc.

Required for working docs:
- `stage: added`

Only for docs that must stay verbatim:
- `keep_as_user: true`

Working-doc lifecycle:
- `added -> adapted|discussed|clarification`
- after extraction/promotion (or explicit discard), delete the working doc

If a doc is large or mixed, split it into multiple titled docs before adapting each part.

## Minimal template
```md
---
stage: added
title: short title
---

# Short title

Raw notes...
```

### Verbatim template (keep)

```md
---
keep_as_user: true
title: short title
---

# Short title

Raw notes that must remain verbatim...
```
