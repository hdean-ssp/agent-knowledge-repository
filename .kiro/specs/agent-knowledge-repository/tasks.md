# Implementation Plan: Agent Knowledge Repository

## Overview

Implement the Agent Knowledge Repository (AKR) — a Python CLI tool enabling AI agents to commit, retrieve, update, and manage knowledge artifacts in a local vector-searchable repository. The implementation follows a bottom-up approach: foundational models and utilities first, then infrastructure layers (embedding, storage, locking), then business logic, and finally the CLI entry points and steering file. Each task builds incrementally on prior work, with property-based and unit tests woven in close to the code they validate.

## Tasks

- [x] 1. Set up project structure, packaging, and error hierarchy
  - [x] 1.1 Create `pyproject.toml` with package metadata, entry points for `akr-commit`, `akr-fetch`, `akr-update`, `akr-delete`, `akr-list`, and dependencies (`sqlite-vec`, `fastembed`, `pytest`, `hypothesis`)
    - Define `[project.scripts]` mapping each `akr-*` command to `akr.cli:<function>`
    - Set `requires-python = ">=3.9"`
    - _Requirements: 14.1, 14.2, 14.3, 14.5, 14.6, 14.7_
  - [x] 1.2 Create package directory `akr/` with `__init__.py`
    - _Requirements: 14.3_
  - [x] 1.3 Create `akr/errors.py` with the full exception hierarchy: `AKRError`, `ValidationError`, `ArtifactNotFoundError`, `EmbeddingModelError`, `RepositoryError`, `LockTimeoutError`, `ConfigValidationError`
    - Each exception should carry structured detail (field names, messages) for JSON error formatting
    - _Requirements: 1.4, 3.2, 4.2, 6.5, 9.4_

- [x] 2. Implement data models, schema validation, and serialization
  - [x] 2.1 Create `akr/schema.py` with `KnowledgeArtifact` dataclass and `SchemaValidator`
    - Define `KnowledgeArtifact` with fields: `id`, `title`, `content`, `tags`, `source_context`, `created_at`, `updated_at`, `metadata`
    - Implement `SchemaValidator.validate()` that checks required fields (title, content, tags, source_context), non-empty strings, tags as non-empty list, auto-populates `id` (UUID v4), `created_at`, `updated_at` (ISO 8601)
    - Raise `ValidationError` with descriptive messages on invalid input
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 1.2, 3.3_
  - [x] 2.2 Create `akr/serialization.py` with `serialize_artifact`, `deserialize_artifact`, and `pretty_print_artifact`
    - `serialize_artifact` converts `KnowledgeArtifact` to JSON string
    - `deserialize_artifact` parses JSON string back to `KnowledgeArtifact`
    - `pretty_print_artifact` formats with 2-space indentation
    - _Requirements: 13.1, 13.2, 13.3, 13.4_
  - [x]* 2.3 Write property test for schema validation (invalid payloads rejected)
    - **Property 2: Invalid payloads are rejected by schema validation**
    - Use Hypothesis `invalid_artifact()` strategy to generate dicts missing required fields, with empty strings, or empty tag lists
    - Verify `ValidationError` is raised and no side effects occur
    - **Validates: Requirements 1.2, 3.3, 5.1, 5.4**
  - [x]* 2.4 Write property test for serialization round-trip
    - **Property 13: Serialization round-trip**
    - Use Hypothesis `valid_artifact()` strategy to generate random `KnowledgeArtifact` objects
    - Verify `deserialize_artifact(serialize_artifact(a))` produces identical field values
    - **Validates: Requirements 13.4**
  - [x]* 2.5 Write property test for pretty-print producing valid JSON
    - **Property 14: Pretty-print produces valid JSON**
    - Use Hypothesis `valid_artifact()` strategy
    - Verify output is valid JSON, contains newlines, and round-trips correctly
    - **Validates: Requirements 13.3**

- [x] 3. Checkpoint
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Implement configuration loader
  - [x] 4.1 Create `akr/config.py` with `AKRConfig` dataclass and `load_config()` function
    - `AKRConfig` fields: `repo_mode`, `shared_repo_path`, `user_repo_path`, `embedding_model`, `default_top_n`, `similarity_threshold`
    - `load_config()` searches `.kiro/knowledge-config.json` in project root then home directory
    - Falls back to sensible defaults (user mode, default paths, `BAAI/bge-small-en-v1.5`, top_n=5, threshold=0.3)
    - Raises `ConfigValidationError` for invalid values (negative top_n, threshold outside [0, 2], unknown repo_mode)
    - _Requirements: 9.1, 9.2, 9.3, 9.4_
  - [x]* 4.2 Write property test for configuration validation
    - **Property 9: Configuration validation rejects invalid values**
    - Use Hypothesis to generate config dicts with invalid values (negative `default_top_n`, out-of-range `similarity_threshold`, unknown `repo_mode`)
    - Verify `ConfigValidationError` is raised identifying the specific invalid field
    - **Validates: Requirements 9.4**
  - [x]* 4.3 Write unit tests for configuration defaults and file loading
    - Test that missing config file produces sensible defaults in user mode
    - Test that valid config file is loaded correctly
    - _Requirements: 9.3_

- [x] 5. Implement embedding engine
  - [x] 5.1 Create `akr/embedding.py` with `EmbeddingEngine` class
    - `__init__` accepts model name (default `BAAI/bge-small-en-v1.5`), initializes fastembed `TextEmbedding`
    - Raises `EmbeddingModelError` if model cannot be loaded
    - `embed(text)` returns float32 bytes compatible with sqlite-vec (via `struct.pack`)
    - `embed_batch(texts)` for batch embedding
    - `dimensions` property returns embedding dimension count (384)
    - _Requirements: 6.2, 6.4, 6.5, 6.7, 14.6_
  - [x]* 5.2 Write unit tests for embedding engine
    - Test that `embed()` returns bytes of correct length (384 * 4 = 1536 bytes)
    - Test that `EmbeddingModelError` is raised for invalid model name
    - Test that `dimensions` property returns 384
    - _Requirements: 6.2, 6.5_

- [x] 6. Implement file lock manager
  - [x] 6.1 Create `akr/locking.py` with `FileLockManager` and `FileLock` context manager
    - `acquire_write_lock(db_path, timeout)` creates/opens `<db_path>.lock` file and uses `fcntl.flock` for exclusive lock
    - `FileLock` implements `__enter__`/`__exit__` for context manager usage
    - Raises `LockTimeoutError` if lock cannot be acquired within timeout
    - _Requirements: 7.2, 7.3_
  - [x]* 6.2 Write unit tests for file lock manager
    - Test that lock is acquired and released correctly
    - Test that `LockTimeoutError` is raised on timeout with a competing lock
    - _Requirements: 7.2, 7.3_

- [x] 7. Implement repository layer
  - [x] 7.1 Create `akr/repository.py` with `ArtifactRepository` class
    - `__init__(db_path)` opens/creates SQLite database, loads sqlite-vec extension, enables WAL mode
    - `initialize_schema()` creates `artifacts`, `vec_artifacts` (vec0 virtual table, 384 dimensions), and `audit_trail` tables
    - `insert_artifact(artifact, embedding)` inserts into both `artifacts` and `vec_artifacts`
    - `get_artifact(artifact_id)` retrieves single artifact by ID
    - `update_artifact(artifact_id, artifact, embedding)` replaces content and vector, records audit trail
    - `delete_artifact(artifact_id)` removes from both tables
    - `search_by_vector(query_embedding, top_n, threshold)` performs KNN search using `vec_distance_cosine`
    - `list_artifacts(tags, since, limit, offset)` with tag AND-filter, date filter, pagination, sorted by `updated_at` DESC
    - `insert_audit_record(artifact_id, previous_content)` records previous version
    - _Requirements: 6.1, 6.3, 6.6, 1.1, 2.1, 3.1, 3.4, 4.1, 12.1, 12.2, 12.3, 12.4, 14.4, 14.5_
  - [x]* 7.2 Write unit tests for repository layer
    - Test schema initialization creates expected tables
    - Test insert and retrieve round-trip
    - Test update records audit trail entry
    - Test delete removes artifact and vector
    - Test list with tag and date filters
    - _Requirements: 6.1, 3.4, 4.1_

- [x] 8. Checkpoint
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Implement service layer
  - [x] 9.1 Create `akr/service.py` with `KnowledgeService` class and result dataclasses (`CommitResult`, `FetchResult`, `UpdateResult`, `DeleteResult`, `ListResult`)
    - `__init__(config)` initializes `SchemaValidator`, `EmbeddingEngine`, repository instances (shared/user based on config), `FileLockManager`
    - `commit(artifact_data, repo_mode)` validates, embeds, acquires write lock, stores, returns `CommitResult` with ID
    - `fetch(query, top_n, threshold, repo_mode)` embeds query, searches configured repos, merges results if "both" mode, annotates `source_repo`, returns sorted `FetchResult` list
    - `update(artifact_id, artifact_data, repo_mode)` validates, records audit, re-embeds, updates, returns `UpdateResult`
    - `delete(artifact_id, repo_mode)` removes artifact and embedding, returns `DeleteResult`
    - `list_artifacts(tags, since, limit, offset, repo_mode)` delegates to repository with filters, returns `ListResult`
    - Handle `ArtifactNotFoundError` for update/delete of non-existent IDs
    - _Requirements: 1.1, 1.3, 1.4, 2.1, 2.4, 3.1, 3.2, 3.4, 4.1, 4.2, 4.3, 7.1, 7.2, 7.3, 8.1, 8.2, 8.3, 8.4, 12.1, 12.2, 12.3, 12.4_
  - [x]* 9.2 Write property test for commit round-trip
    - **Property 1: Commit round-trip preserves artifact data**
    - Use Hypothesis `valid_artifact()` strategy, commit to in-memory repo, retrieve by returned ID
    - Verify title, content, tags, source_context, metadata are identical; timestamps are valid ISO 8601; embedding row exists
    - **Validates: Requirements 1.1, 5.2, 5.3, 6.2**
  - [x]* 9.3 Write property test for unique artifact IDs
    - **Property 3: Committed artifact IDs are unique**
    - Use Hypothesis to generate N valid payloads, commit all, verify all returned IDs are distinct non-empty strings
    - **Validates: Requirements 1.3**
  - [x]* 9.4 Write property test for fetch ordering and bounds
    - **Property 4: Fetch results are ordered by distance and bounded by top-N**
    - Commit several artifacts, fetch with random query, verify result count ≤ top_n, each has numeric distance, results sorted ascending by distance
    - **Validates: Requirements 2.1, 2.4, 6.3**
  - [x]* 9.5 Write property test for update replacing content and embedding
    - **Property 5: Update replaces artifact content and regenerates embedding**
    - Commit artifact, update with new payload, retrieve by ID, verify new content returned and embedding differs
    - **Validates: Requirements 3.1**
  - [x]* 9.6 Write property test for update audit trail
    - **Property 6: Update records previous version in audit trail**
    - Commit artifact, update it, query audit_trail table, verify previous content matches original
    - **Validates: Requirements 3.4**
  - [x]* 9.7 Write property test for delete removing artifact and embedding
    - **Property 7: Delete removes artifact and embedding**
    - Commit artifact, delete by ID, verify retrieval returns None and vec_artifacts has no row for that ID
    - **Validates: Requirements 4.1, 4.3**
  - [x]* 9.8 Write property test for dual-repo source annotation
    - **Property 8: Dual-repo fetch annotates source repository**
    - Set up both shared and user repos, commit artifacts to each, fetch in "both" mode, verify every result has `source_repo` field with value "shared" or "user"
    - **Validates: Requirements 8.4**
  - [x]* 9.9 Write property test for list ordering and limit
    - **Property 10: List returns results sorted by updated_at descending, bounded by limit**
    - Commit multiple artifacts, list with a limit, verify count ≤ limit and results sorted by `updated_at` descending
    - **Validates: Requirements 12.1, 12.4**
  - [x]* 9.10 Write property test for list tag filter
    - **Property 11: List tag filter returns only artifacts matching all specified tags**
    - Commit artifacts with various tag combinations, filter by a tag subset, verify every returned artifact contains all filter tags
    - **Validates: Requirements 12.2**
  - [x]* 9.11 Write property test for list date filter
    - **Property 12: List date filter returns only artifacts modified on or after the specified date**
    - Commit artifacts with various timestamps, filter by a `--since` date, verify every returned artifact has `updated_at` ≥ filter date
    - **Validates: Requirements 12.3**
  - [x]* 9.12 Write unit tests for service error handling
    - Test update with non-existent ID raises `ArtifactNotFoundError`
    - Test delete with non-existent ID raises `ArtifactNotFoundError`
    - Test commit with invalid payload raises `ValidationError`
    - Test fetch on empty repository returns empty list
    - _Requirements: 1.4, 2.2, 3.2, 4.2_

- [x] 10. Checkpoint
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Implement CLI layer
  - [x] 11.1 Create `akr/cli.py` with all five CLI entry points: `akr_commit`, `akr_fetch`, `akr_update`, `akr_delete`, `akr_list`
    - Each function uses `argparse` to parse CLI arguments as specified in the design
    - `akr_commit`: `--json`, `--file`, `--repo` arguments; outputs `{"id": "<uuid>", "status": "committed"}`
    - `akr_fetch`: `--query`, `--top-n`, `--threshold`, `--repo` arguments; outputs JSON array of results with score and source_repo
    - `akr_update`: `--id`, `--json`, `--file`, `--repo` arguments; outputs `{"id": "<uuid>", "status": "updated"}`
    - `akr_delete`: `--id`, `--repo` arguments; outputs `{"id": "<uuid>", "status": "deleted"}`
    - `akr_list`: `--tags`, `--since`, `--limit`, `--offset`, `--repo` arguments; outputs JSON array of artifact summaries
    - All errors caught at CLI layer and formatted as JSON to stdout; `AKRError` subclasses → exit 1, unexpected exceptions → exit 2
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.4, 3.1, 3.2, 3.3, 4.1, 4.2, 4.3, 12.1, 12.2, 12.3, 12.4_
  - [x]* 11.2 Write unit tests for CLI argument parsing and JSON output formatting
    - Test each command with valid arguments produces expected JSON output structure
    - Test each command with invalid arguments produces JSON error output with exit code 1
    - Test unexpected exception produces generic error with exit code 2
    - _Requirements: 1.4, 2.2, 3.2, 4.2_

- [x] 12. Create steering file
  - [x] 12.1 Create `.kiro/steering/agent-knowledge.md` with `inclusion: auto` frontmatter
    - Include rules for when to fetch (start of interaction, before architectural decisions)
    - Include rules for when to commit (bug fix patterns, architectural decisions, code patterns)
    - Include rules for when to update (superseding information, deduplication check)
    - Include tagging guidance and source context instructions
    - Include command reference for all five `akr-*` commands
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 11.1, 11.2, 11.3, 11.4_
  - [x]* 12.2 Write unit test for steering file structure
    - Verify file exists at expected path
    - Verify `inclusion: auto` directive is present in frontmatter
    - Verify file does not conflict with other steering file conventions
    - _Requirements: 10.3, 10.5_

- [x] 13. Final checkpoint
  - Ensure all tests pass, ask the user if questions arise.

- [x] 14. Write project documentation
  - [x] 14.1 Update `README.md` with project overview, tech stack/design choices, benefits, quick-start install guide, and CLI usage examples for all five `akr-*` commands

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation after each major layer
- Property tests validate the 14 correctness properties from the design document using Hypothesis
- Unit tests cover specific error scenarios, edge cases, and configuration defaults
- All code uses Python 3.9+ standard library where possible, with only `sqlite-vec`, `fastembed`, `pytest`, and `hypothesis` as external dependencies
