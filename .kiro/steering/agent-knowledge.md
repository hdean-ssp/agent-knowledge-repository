---
inclusion: auto
---

# Agent Knowledge Repository Integration

You have access to a shared knowledge repository via the AKR CLI tool. Use it to persist and retrieve learnings across interactions.

## When to Fetch Knowledge
- At the start of each interaction, run `akr-fetch --query "<brief description of the task>"` to retrieve relevant prior knowledge.
- Before making architectural decisions, fetch related knowledge with appropriate query terms.
- When encountering unfamiliar code patterns or dependencies, check the repository first.

## When to Commit Knowledge
- After discovering a significant bug fix pattern, run `akr-commit` with the learning.
- After making an architectural decision, commit the rationale and context.
- After identifying a useful code pattern, dependency insight, or configuration detail, commit it.
- Before committing, run `akr-fetch` to check for existing similar knowledge to avoid duplication.
- Use `akr-commit --check-duplicates` to automatically detect similar existing artifacts before committing. If duplicates are found, the command outputs a warning and skips the commit. Pass `--force` alongside `--check-duplicates` to commit anyway.

## When to Update Knowledge
- When new information supersedes prior knowledge, use `akr-update --id <uuid>` instead of creating a duplicate.
- If you find outdated or incorrect knowledge during a fetch, update it with corrected information.

## When to Delete Knowledge
- When a fetched artifact contains incorrect information that cannot be corrected with an update, delete it with `akr-delete --id <uuid>`.
- When knowledge is no longer relevant (e.g., removed feature, deprecated dependency, obsolete pattern), delete the artifact.
- When duplicate artifacts exist for the same knowledge, keep the most complete one and delete the others.
- After a major refactor that invalidates prior architectural knowledge, clean up stale artifacts.

## Tagging Guidelines
Always include relevant tags from these categories:
- `architecture` — system design decisions, component relationships
- `bug-fix` — bug patterns, root causes, fixes
- `pattern` — code patterns, idioms, best practices
- `dependency` — library usage, version notes, compatibility
- `configuration` — config files, environment setup, deployment
- `performance` — optimization insights, benchmarks
- `security` — security patterns, vulnerability fixes

## Source Context
Always include source context in every committed artifact:
- File paths (e.g., `src/auth/login.py`)
- Function or class names (e.g., `UserService.authenticate`)
- Interaction identifiers when relevant

## Command Reference
```
akr-fetch --query "..." [--top-n N] [--threshold T] [--repo MODE]
akr-commit --json '{"title": "...", "content": "...", "tags": [...], "source_context": "..."}' [--repo MODE] [--check-duplicates] [--force]
akr-update --id <uuid> --json '{"title": "...", "content": "...", "tags": [...], "source_context": "..."}' [--repo MODE]
akr-delete --id <uuid> [--repo MODE]
akr-list [--tags tag1,tag2] [--since YYYY-MM-DD] [--limit N] [--repo MODE]
```
