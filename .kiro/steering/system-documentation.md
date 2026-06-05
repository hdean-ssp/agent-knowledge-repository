---
inclusion: auto
---

# System Documentation Layer

You have access to structured system documentation that provides business-level understanding of the electRa/Castle system. This is the **third tier** of your intelligence stack:

1. **genero-tools** — structural codebase queries (what the code *is*)
2. **AKR** — experiential knowledge (what you've *learned* across sessions)
3. **System Documentation** — business logic and module detail (what the system *does* and *why*)

## When to Use System Documentation

Use the documentation layer when you need:
- Business context for a module (what it does from a user/domain perspective)
- Understanding of data flows between modules
- Integration details (external systems, protocols, formats)
- Process/batch job context (what runs overnight, scheduling, dependencies)
- Module relationships and boundaries
- Gap awareness (what's known vs unknown)

## Documentation Location

Documentation is available via the `$ELECTRA_DOCUMENTATION` environment variable, which points to the documentation root directory. Access files via:

```bash
cat $ELECTRA_DOCUMENTATION/<filename>
```

### Entry Point
- `00-system-map.md` — Top-level overview of all functional areas (start here)

### Module Summaries (Level 2)
- `01-module-summaries/customer-management.md`
- `01-module-summaries/policy-lifecycle.md`
- `01-module-summaries/claims.md`
- `01-module-summaries/accounts-finance.md`
- `01-module-summaries/reporting.md`
- `01-module-summaries/batch-processing.md`
- `01-module-summaries/web-services.md`
- `01-module-summaries/job-scheduling.md`
- `01-module-summaries/printing-spooler.md`
- `01-module-summaries/administration.md`

### Cross-Cutting Documents
- `02-data-flows.md` — How data moves between modules and external systems
- `03-integration-catalogue.md` — All external system connections (protocols, formats, purposes)
- `04-process-inventory.md` — Batch processes, overnight jobs, scheduled workflows
- `05-akr-coverage-matrix.md` — Maps AKR artifacts to documentation sections
- `06-gap-register.md` — Known gaps in documentation/knowledge

### Detailed Breakdowns (Level 3)
- `03-level3/claims-workflow.md` — Claims state machine, NCD impact
- `03-level3/action-lists-arob.md` — Workflow automation engine
- `03-level3/quote-engine.md` — Rating flow, Quotes Hub, multi-insurer
- `03-level3/ars-services.md` — All 10 ARS services, file formats
- `03-level3/accounts-reconciliation.md` — Payment reconciliation pipeline

## Three-Tier Workflow

When working on a task that touches a functional area:

```
# Tier 1: Structural — what does the code look like?
bash $GENERO_TOOLS_PATH find-function-resolved <name>
bash $GENERO_TOOLS_PATH find-function-dependents <name>

# Tier 2: Experiential — any known issues or patterns?
akr-fetch --query "<relevant terms>"

# Tier 3: Business context — what is this module supposed to do?
# Read the relevant file from $ELECTRA_DOCUMENTATION/
cat $ELECTRA_DOCUMENTATION/01-module-summaries/<module>.md
```

## Which Documentation File to Read

| Working on... | Read this file |
|---------------|----------------|
| Any module — need orientation | `00-system-map.md` |
| Customer/policy/claims code | Relevant `01-module-summaries/*.md` |
| Integration or external system | `03-integration-catalogue.md` |
| Overnight/batch/scheduled job | `04-process-inventory.md` |
| Data movement between areas | `02-data-flows.md` |
| Quote/rating engine | `03-level3/quote-engine.md` |
| Claims processing | `03-level3/claims-workflow.md` |
| Accounts reconciliation | `03-level3/accounts-reconciliation.md` |
| ARS/renewal services | `03-level3/ars-services.md` |
| Action lists/AROB automation | `03-level3/action-lists-arob.md` |
| Checking if something is documented | `05-akr-coverage-matrix.md` |
| Finding gaps in knowledge | `06-gap-register.md` |

## Rules

- Read the system map first if you've never worked in the area before.
- Don't read ALL module summaries — only the one relevant to the current task.
- The documentation is a snapshot; for precise current-state queries, use genero-tools.
- If you discover the documentation is outdated or incomplete for an area you're working in, note it but don't update the docs unless the user asks.
- The documentation supplements but does not replace reading actual source code for implementation work.
