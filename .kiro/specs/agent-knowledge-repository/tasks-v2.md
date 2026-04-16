# AKR v2 Implementation Plan

## Overview

Incremental improvements to the Agent Knowledge Repository: lazy model loading, export/import, duplicate detection, hardcoded model, audit CLI, disk space checks, output formatting, steering updates, and stats command.

## Tasks

- [x] 1. Lazy model loading
  - [x] 1.1 Refactor `KnowledgeService.__init__` to defer `EmbeddingEngine` initialization — store config but don't create the engine until first use
  - [x] 1.2 Add `_get_embedding_engine()` lazy property that initializes on first call and caches the instance
  - [x] 1.3 Update `commit()`, `fetch()`, and `update()` to call `_get_embedding_engine()` instead of `self.embedding_engine`
  - [x] 1.4 Verify `akr-list` and `akr-delete` no longer trigger model loading (add unit test that mocks EmbeddingEngine and asserts it's never called)
  - [x] 1.5 Run full test suite, fix any breakage from the refactor

- [x] 2. Remove configurable embedding model
  - [x] 2.1 Hardcode `BAAI/bge-small-en-v1.5` in `EmbeddingEngine.__init__` — remove `model_name` parameter, use constant
  - [x] 2.2 Remove `embedding_model` field from `AKRConfig` dataclass and `_DEFAULTS`
  - [x] 2.3 Remove `embedding_model` from `validate_config()` and `load_config()`
  - [x] 2.4 Update `KnowledgeService` to not pass model name to `EmbeddingEngine`
  - [x] 2.5 Remove `embedding_model` from README config example and docs
  - [x] 2.6 Hardcode embedding dimension (384) as a constant in `embedding.py` — remove the probe-based dimension detection
  - [x] 2.7 Update tests to remove model name references, run full suite

- [x] 3. Output format option
  - [x] 3.1 Add `--format json|text|brief` argument to `akr_fetch` in `cli.py` (default: `json`)
  - [x] 3.2 Add `--format json|text|brief` argument to `akr_list` in `cli.py` (default: `json`)
  - [x] 3.3 Create `akr/formatters.py` with three formatter functions:
    - `format_json(artifacts)` — current JSON behavior
    - `format_brief(artifacts)` — one line per artifact: `[id] title (score)` for fetch, `[id] title (updated_at)` for list
    - `format_text(artifacts)` — human-readable multi-line: title, tags, source_context, truncated content (first 200 chars)
  - [x] 3.4 Wire formatters into `akr_fetch` and `akr_list` based on `--format` flag
  - [x] 3.5 Write unit tests for each formatter
  - [x] 3.6 Update README CLI usage section with `--format` examples

- [x] 4. Add delete guidance to steering file
  - [x] 4.1 Add "When to Delete Knowledge" section to `.kiro/steering/agent-knowledge.md` covering: stale/outdated artifacts, knowledge superseded by updates, incorrect entries discovered during fetch, artifacts with no remaining relevance
  - [x] 4.2 Update steering file test to verify delete guidance section exists

- [x] 5. Duplicate detection on commit
  - [x] 5.1 Add `--check-duplicates` flag to `akr_commit` in `cli.py`
  - [x] 5.2 Add `--force` flag to `akr_commit` to override duplicate warning
  - [x] 5.3 Add `check_duplicates()` method to `KnowledgeService` — embeds the new content, runs a fetch with a tight threshold (e.g., 0.3), returns list of similar artifact IDs
  - [x] 5.4 Wire into `akr_commit`: if `--check-duplicates` is set and similar artifacts found, output warning JSON with similar IDs and exit 0 without committing (unless `--force`)
  - [x] 5.5 Write unit tests for duplicate detection (mock embedding engine, verify similar artifacts are flagged)
  - [x] 5.6 Update steering file to reference `--check-duplicates` flag

- [x] 6. Disk space check on large commits
  - [x] 6.1 Add `disk_space_check()` utility in `akr/utils.py` — uses `shutil.disk_usage()` to check free space on the repo partition
  - [x] 6.2 Define constants: `LARGE_ARTIFACT_THRESHOLD = 10240` (10KB content), `MIN_FREE_SPACE = 104857600` (100MB)
  - [x] 6.3 Call `disk_space_check()` in `KnowledgeService.commit()` before writing, only when content length exceeds `LARGE_ARTIFACT_THRESHOLD`
  - [x] 6.4 Raise `RepositoryError` with clear message if free space is below `MIN_FREE_SPACE`
  - [x] 6.5 Write unit tests (mock `shutil.disk_usage` to simulate low disk space)

- [x] 7. Export/import commands
  - [x] 7.1 Add `akr-export` entry point to `pyproject.toml` and `cli.py`
    - Args: `--output <path>` (required), `--repo <mode>`
    - Exports all artifacts as a JSON array to the specified file
    - Does NOT export embeddings (they get regenerated on import)
  - [x] 7.2 Add `export_artifacts()` method to `KnowledgeService` — calls `list_artifacts` with no filters and high limit, serializes to JSON
  - [x] 7.3 Add `akr-import` entry point to `pyproject.toml` and `cli.py`
    - Args: `--input <path>` (required), `--repo <mode>`, `--strategy skip|update` (default: `skip`)
    - `skip`: skip artifacts whose ID already exists in the target repo
    - `update`: overwrite existing artifacts if the imported version has a newer `updated_at`
  - [x] 7.4 Add `import_artifacts()` method to `KnowledgeService` — reads JSON file, validates each artifact, generates embeddings, inserts/updates based on strategy
  - [x] 7.5 Write unit tests for export (verify JSON output matches repo contents)
  - [x] 7.6 Write unit tests for import with `skip` strategy (existing artifacts untouched)
  - [x] 7.7 Write unit tests for import with `update` strategy (newer artifacts overwrite)
  - [x] 7.8 Update README with export/import usage examples

- [x] 8. Audit trail CLI command
  - [x] 8.1 Add `akr-audit` entry point to `pyproject.toml` and `cli.py`
    - Args: `--id <uuid>` (required), `--repo <mode>`
    - Returns JSON array of audit records: `[{"changed_at": "...", "previous_content": {...}}, ...]`
  - [x] 8.2 Add `get_audit_trail()` method to `ArtifactRepository` — queries `audit_trail` table by artifact_id, ordered by changed_at DESC
  - [x] 8.3 Add `get_audit_trail()` method to `KnowledgeService` — delegates to repo
  - [x] 8.4 Write unit tests (commit, update twice, verify audit returns 2 records in correct order)

- [x] 9. Repository stats command
  - [x] 9.1 Add `akr-stats` entry point to `pyproject.toml` and `cli.py`
    - Args: `--repo <mode>`
    - Output JSON: `{"artifact_count": N, "db_size_bytes": N, "last_updated": "...", "tags": {"tag": count, ...}, "repo_mode": "..."}`
  - [x] 9.2 Add `get_stats()` method to `ArtifactRepository` — queries artifact count, max updated_at, tag distribution via `json_each`
  - [x] 9.3 Add `get_stats()` method to `KnowledgeService` — aggregates across repos, adds DB file size via `os.path.getsize`
  - [x] 9.4 Write unit tests for stats (empty repo, repo with artifacts, tag distribution)

- [-] 10. Final validation
  - [x] 10.1 Run full test suite
  - [ ] 10.2 Update README AND steering doc & hook with all new commands and options where appropriate
  - [ ] 10.3 Commit and push
