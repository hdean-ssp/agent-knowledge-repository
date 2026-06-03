---
inclusion: auto
---

# Codebase Intelligence: genero-tools + AKR Integration

You have access to two complementary intelligence systems for working in Genero/4GL codebases:

- **genero-tools** — structural knowledge (what the code *is*): function signatures, call graphs, type resolution, schema impact, code metrics, module dependencies
- **AKR** — experiential knowledge (what you've *learned*): bug patterns, architectural decisions, gotchas, code patterns discovered across sessions

Use both together. Structural queries are instant and deterministic. Experiential queries surface hard-won knowledge that would otherwise require re-discovery.

## Two-Tier Workflow

### Before modifying code:
1. **Structural** — use genero-tools to understand the function, its callers, callees, and types
2. **Experiential** — use AKR to fetch known issues, patterns, or decisions related to that area
3. Work with full context from both sources

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
```

### Schema impact analysis
```bash
# Which functions break if I change a table?
bash $GENERO_TOOLS_PATH find-functions-using <table_name>

# Which functions reference a specific column?
bash $GENERO_TOOLS_PATH find-functions-using <table_name> <column_name>

# Resolve a LIKE reference to its actual type
bash $GENERO_TOOLS_PATH resolve-like <table.column>
```

### Module queries
```bash
# Find a module by name
bash $GENERO_TOOLS_PATH find-module <name>

# Find all functions in a module
bash $GENERO_TOOLS_PATH find-functions-in-module <name>

# Find which module(s) contain a function
bash $GENERO_TOOLS_PATH find-module-for-function <name>

# Find module dependencies
bash $GENERO_TOOLS_PATH find-module-dependencies <name>
```

### File references and authorship
```bash
# Find files related to a code reference (ticket, CR number)
bash $GENERO_TOOLS_PATH find-reference "PRB-299"

# Find files modified by an author
bash $GENERO_TOOLS_PATH find-author "Rich"

# Show what areas an author has expertise in
bash $GENERO_TOOLS_PATH author-expertise "Chilly"

# Find recently modified files
bash $GENERO_TOOLS_PATH recent-changes 30
```

### File dependencies
```bash
# Show what a file depends on (GLOBALS/IMPORT)
bash $GENERO_TOOLS_PATH file-deps <file_path>

# Find files that depend on a globals file
bash $GENERO_TOOLS_PATH file-dependents <name>
```

### Type resolution debugging
```bash
# Find all unresolved LIKE references
bash $GENERO_TOOLS_PATH unresolved-types

# Validate type resolution consistency
bash $GENERO_TOOLS_PATH validate-types
```

## When to Use Which Tool

| Question | Tool | Command |
|----------|------|---------|
| What does this function do? (signature, params, returns) | genero-tools | `find-function` / `find-function-resolved` |
| What calls this function? | genero-tools | `find-function-dependents` |
| What will break if I change this table? | genero-tools | `find-functions-using` |
| Has anyone fixed a similar bug before? | AKR | `akr-fetch --query "..."` |
| Why was this designed this way? | AKR | `akr-fetch --query "..."` |
| What's the complexity of this function? | genero-tools | `find-function` (metrics in output) |
| What gotchas exist in this area? | AKR | `akr-fetch --query "..."` |
| Who owns this code? | genero-tools | `file-authors` / `author-expertise` |
| What's the module structure? | genero-tools | `find-module` / `find-functions-in-module` |
| What patterns apply to this type of change? | AKR | `akr-fetch --query "..."` |

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
