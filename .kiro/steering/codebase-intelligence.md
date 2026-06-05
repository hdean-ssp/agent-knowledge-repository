---
inclusion: auto
---

# Codebase Intelligence: genero-tools + AKR + System Documentation

You have access to three complementary intelligence systems for working in Genero/4GL codebases:

- **genero-tools** (Tier 1) — structural knowledge (what the code *is*): function signatures, call graphs, type resolution, schema impact, code metrics, module dependencies
- **AKR** (Tier 2) — experiential knowledge (what you've *learned*): bug patterns, architectural decisions, gotchas, code patterns discovered across sessions
- **System Documentation** (Tier 3) — business logic knowledge (what the system *does* and *why*): module purposes, data flows, integrations, batch processes, domain context

Use all three together. Structural queries are instant and deterministic. Experiential queries surface hard-won knowledge that would otherwise require re-discovery. Documentation provides business-level understanding of what modules are supposed to do and how they relate. See `.kiro/steering/system-documentation.md` for the full documentation file reference.

## Three-Tier Workflow

### Before modifying code:
1. **Structural (genero-tools)** — understand the function, its callers, callees, and types
2. **Experiential (AKR)** — fetch known issues, patterns, or decisions related to that area
3. **Business context (System Documentation)** — read the relevant module summary or cross-cutting doc from `$ELECTRA_DOCUMENTATION/` to understand what the module is supposed to do, its data flows, and integration points. See `.kiro/steering/system-documentation.md` for the file lookup table.
4. Work with full context from all three sources

### After completing work:
1. **Commit learnings** — if you discovered something non-obvious, commit it to AKR
2. Especially commit: why something was tricky, what the blast radius was, what the resolution approach was

## genero-tools Query Reference

genero-tools is available via the `$GENERO_TOOLS_PATH` environment variable, which points directly to `query.sh`. Invoke via:

```bash
bash $GENERO_TOOLS_PATH <command> [args...]
```

If the target project has `workspace.db` and `modules.db` in the current directory, queries use those automatically. Otherwise, set `SIGNATURES_DB` and `MODULES_DB` environment variables.

### Function queries
```bash
# Find a function by exact name
bash $GENERO_TOOLS_PATH find-function <name>

# Find with resolved LIKE types (shows actual schema types)
bash $GENERO_TOOLS_PATH find-function-resolved <name>

# Search by pattern (glob-style)
bash $GENERO_TOOLS_PATH search-functions "get_*"

# List all functions in a file
bash $GENERO_TOOLS_PATH list-file-functions <path>
```

### Call graph / dependency analysis
```bash
# What does this function call?
bash $GENERO_TOOLS_PATH find-function-dependencies <name>

# What calls this function?
bash $GENERO_TOOLS_PATH find-function-dependents <name>

# Find functions never called by anything
bash $GENERO_TOOLS_PATH find-dead-code

# Find the full call chain from one function to another
bash $GENERO_TOOLS_PATH find-call-chain <from_function> <to_function>

# Find functions that call both of two given functions
bash $GENERO_TOOLS_PATH find-common-callers <func1> <func2>
```

### Schema queries and impact analysis
```bash
# Get full table definition with all columns
bash $GENERO_TOOLS_PATH get-table <table_name>

# Get a single column definition
bash $GENERO_TOOLS_PATH get-column <table_name> <column_name>

# Search tables by name pattern
bash $GENERO_TOOLS_PATH search-tables "acc*"

# Search columns by name across all tables
bash $GENERO_TOOLS_PATH search-columns "cus_*"

# Resolve a LIKE reference (table.column or table.*)
bash $GENERO_TOOLS_PATH resolve-like "account.acc_code"

# Which functions break if I change a table?
bash $GENERO_TOOLS_PATH find-functions-using <table_name>

# Which functions reference a specific column?
bash $GENERO_TOOLS_PATH find-functions-using <table_name> <column_name>
```

### Module queries
```bash
# Find a module by exact name
bash $GENERO_TOOLS_PATH find-module <name>

# Search modules by name pattern
bash $GENERO_TOOLS_PATH search-modules "core_*"

# Find modules that use a specific file
bash $GENERO_TOOLS_PATH list-file-modules <filename>

# Find all functions in a module
bash $GENERO_TOOLS_PATH find-functions-in-module <name>

# Find which module(s) contain a function
bash $GENERO_TOOLS_PATH find-module-for-function <name>

# Find functions in a module that call a specific function
bash $GENERO_TOOLS_PATH find-functions-calling-in-module <module> <func>

# Find modules that a module depends on
bash $GENERO_TOOLS_PATH find-module-dependencies <name>

# Find dependents within a module
bash $GENERO_TOOLS_PATH find-dependents-in-module <module> <func>
```

### File references and authorship
```bash
# Find files related to a code reference (ticket, CR number)
bash $GENERO_TOOLS_PATH find-reference "PRB-299"

# Search references by pattern (partial match)
bash $GENERO_TOOLS_PATH search-references "PRB"

# Search references by prefix
bash $GENERO_TOOLS_PATH search-reference-prefix "EH100512"

# Find files modified by an author
bash $GENERO_TOOLS_PATH find-author "Rich"

# Get all references for a specific file
bash $GENERO_TOOLS_PATH file-references "./src/utils.4gl"

# Get all authors who modified a specific file
bash $GENERO_TOOLS_PATH file-authors "./src/utils.4gl"

# Show what areas an author has expertise in
bash $GENERO_TOOLS_PATH author-expertise "Chilly"

# Find recently modified files (default 30 days)
bash $GENERO_TOOLS_PATH recent-changes 7
```

### File dependencies (GLOBALS/IMPORT)
```bash
# Show what a file depends on (GLOBALS/IMPORT)
bash $GENERO_TOOLS_PATH file-deps <file_path>

# Find files that depend on a globals file or import
bash $GENERO_TOOLS_PATH file-dependents <name>
```

### Type resolution debugging
```bash
# Find all unresolved LIKE type references
bash $GENERO_TOOLS_PATH unresolved-types

# Filter by error type (missing_table, missing_column, invalid_pattern)
bash $GENERO_TOOLS_PATH unresolved-types --filter missing_table

# Paginate results
bash $GENERO_TOOLS_PATH unresolved-types --limit 10 --offset 5

# Validate type resolution data consistency
bash $GENERO_TOOLS_PATH validate-types
```

### Batch queries
```bash
# Execute multiple queries in a single batch from a JSON file
bash $GENERO_TOOLS_PATH batch-query queries.json

# Execute batch with output written to file
bash $GENERO_TOOLS_PATH batch-query --input queries.json --output results.json
```

### Database management
```bash
# Create both databases from JSON files
bash $GENERO_TOOLS_PATH create-dbs

# Create workspace.db from workspace.json
bash $GENERO_TOOLS_PATH create-signatures-db

# Create modules.db from modules.json
bash $GENERO_TOOLS_PATH create-modules-db
```

### Output format options (for editor integration)
Append these to any function query:
```bash
--format=vim              # Concise single-line function signatures
--format=vim-hover        # Multi-line format with file location and metrics
--format=vim-completion   # Tab-separated format for completion

--filter=functions-only   # Exclude procedures (no return type)
--filter=no-metrics       # Remove complexity and LOC metrics
--filter=no-file-info     # Remove file path and line number
```

## When to Use Which Tool

| Question | Tool | Command/File |
|----------|------|--------------|
| What does this function do? (signature, params, returns) | genero-tools | `find-function` / `find-function-resolved` |
| What calls this function? | genero-tools | `find-function-dependents` |
| What does this function call? | genero-tools | `find-function-dependencies` |
| How does function A reach function B? | genero-tools | `find-call-chain` |
| What functions call both X and Y? | genero-tools | `find-common-callers` |
| What will break if I change this table/column? | genero-tools | `find-functions-using` |
| What type does this LIKE reference resolve to? | genero-tools | `resolve-like` |
| What columns does a table have? | genero-tools | `get-table` / `get-column` |
| Which module is this function in? | genero-tools | `find-module-for-function` |
| What does this module depend on? | genero-tools | `find-module-dependencies` |
| What GLOBALS/IMPORT does this file use? | genero-tools | `file-deps` |
| Which files include this globals file? | genero-tools | `file-dependents` |
| Who owns this code? | genero-tools | `file-authors` / `author-expertise` |
| What ticket/CR relates to this file? | genero-tools | `find-reference` / `search-references` |
| What changed recently? | genero-tools | `recent-changes` |
| Has anyone fixed a similar bug before? | AKR | `akr-fetch --query "..."` |
| Why was this designed this way? | AKR | `akr-fetch --query "..."` |
| What gotchas exist in this area? | AKR | `akr-fetch --query "..."` |
| What patterns apply to this type of change? | AKR | `akr-fetch --query "..."` |
| What does this module do from a business perspective? | System Docs | `$ELECTRA_DOCUMENTATION/01-module-summaries/<module>.md` |
| How does data flow between modules? | System Docs | `$ELECTRA_DOCUMENTATION/02-data-flows.md` |
| What external systems does this integrate with? | System Docs | `$ELECTRA_DOCUMENTATION/03-integration-catalogue.md` |
| What batch/overnight processes exist? | System Docs | `$ELECTRA_DOCUMENTATION/04-process-inventory.md` |
| What's the claims/quote/ARS business process? | System Docs | `$ELECTRA_DOCUMENTATION/03-level3/<relevant>.md` |
| Is this area well-documented or a known gap? | System Docs | `$ELECTRA_DOCUMENTATION/06-gap-register.md` |

## Combined Patterns

### Pre-modification checklist
Before modifying a function, gather full context:
```bash
# 1. Structural: understand the function
bash $GENERO_TOOLS_PATH find-function-resolved <name>
bash $GENERO_TOOLS_PATH find-function-dependents <name>
bash $GENERO_TOOLS_PATH find-function-dependencies <name>

# 2. Experiential: check for known issues
akr-fetch --query "<function_name> issues patterns"

# 3. Business context: understand the module's purpose
# Read the relevant file from $ELECTRA_DOCUMENTATION/
# (see .kiro/steering/system-documentation.md for which file to read)
cat $ELECTRA_DOCUMENTATION/01-module-summaries/<module>.md
```

### Post-fix knowledge commit
After resolving a non-trivial issue, commit the learning:
```bash
akr-commit --check-duplicates --json '{
  "title": "Fix: <concise description>",
  "content": "<what the issue was, root cause, how it was fixed, and what to watch for>",
  "tags": ["bug-fix", "<module-name>", "<relevant-category>"],
  "source_context": "<file_path>:<function_name>",
  "metadata": {"affected_functions": "<comma-separated list from dependents query>"}
}'
```

### Schema change impact documentation
When a schema change is proposed, document the blast radius:
```bash
# Get impact
bash $GENERO_TOOLS_PATH find-functions-using <table> <column>

# Commit as knowledge for future reference
akr-commit --check-duplicates --json '{
  "title": "Schema impact: <table>.<column> used in N functions",
  "content": "<list of affected functions and modules, migration notes>",
  "tags": ["schema-impact", "architecture", "<table-name>"],
  "source_context": "database.sch:<table>.<column>"
}'
```

### Discovering and recording dead code
```bash
# Find dead code
bash $GENERO_TOOLS_PATH find-dead-code

# If cleanup is planned, record the candidates
akr-commit --check-duplicates --json '{
  "title": "Dead code candidates identified <date>",
  "content": "<list of functions and their files>",
  "tags": ["dead-code", "cleanup-candidate", "architecture"],
  "source_context": "workspace-wide analysis"
}'
```

## Generating the Databases

If `workspace.db` or `modules.db` don't exist yet in the target project, generate them. The `generate_all.sh` script is in the same directory as `query.sh`:

```bash
# From the target Genero codebase directory:
bash $(dirname $GENERO_TOOLS_PATH)/generate_all.sh .

# Or with a specific schema file:
bash $(dirname $GENERO_TOOLS_PATH)/generate_all.sh . /path/to/database.sch

# Incremental re-runs are fast (<1s if nothing changed)
```

Generated files: `workspace.json`, `workspace.db`, `modules.json`, `modules.db`, `workspace_resolved.json`
