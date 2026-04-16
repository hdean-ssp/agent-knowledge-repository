# Agent Knowledge Repository (AKR)

A lightweight CLI tool and framework that gives AI agents a shared, persistent memory. Agents commit what they learn, fetch what they need, and keep a living wiki of knowledge across every interaction.

## Installation

```bash
# Clone and install
git clone https://github.com/hdean-ssp/agent-knowledge-repository.git && cd agent-knowledge-repository
pip install -e .

# Verify it works
akr-list
```

That's it. All dependencies (sqlite-vec, fastembed) are pulled in automatically via pip. No system packages, no database servers, no API keys.

**Requirements:** Python 3.9+ (ships natively on RHEL 9)

## Why AKR?

Working in large, legacy codebases means hard-won knowledge gets lost between sessions. AKR solves this by giving every agent on your team a shared knowledge base they can read from and write to automatically — no manual wiki maintenance required.

## Credit Usage: With vs Without AKR

By leveraging stored knowledge, agents spend fewer tokens re-discovering context — resulting in measurably lower credit usage per interaction.

<table>
<tr>
<th></th>
<th align="center">Without AKR</th>
<th align="center">With AKR</th>
</tr>
<tr>
<td><strong>Credits</strong></td>
<td align="center"><img width="400" alt="without-akr-credits" src="https://github.com/user-attachments/assets/5b27ff5f-5a25-44c3-8baa-41d940b6db23" /></td>
<td align="center"><img width="400" alt="with-akr-credits" src="https://github.com/user-attachments/assets/449f4794-3db8-4d6e-8228-97b984c19e8b" /></td>
</tr>
<tr>
<td><strong>Prompt</strong></td>
<td align="center"><img width="400" alt="without-akr-prompt" src="https://github.com/user-attachments/assets/d54c80f3-dea1-4a33-9301-7e82a75d0947" /></td>
<td align="center"><img width="400" alt="with-akr-prompt" src="https://github.com/user-attachments/assets/77af8e52-9e23-40bb-9db6-ce001d530222" /></td>
</tr>
</table>

- **Living wiki** — Knowledge grows organically as agents work. Bug fix patterns, architectural decisions, dependency gotchas — all captured and searchable.
- **Semantic search** — Find relevant knowledge by meaning, not just keywords. Powered by vector embeddings and cosine similarity.
- **Zero infrastructure** — No database servers, no Docker, no API keys. Everything runs locally in a single SQLite file.
- **Team-wide or personal** — Shared repository for the whole team, per-user repo in `.kiro/`, or both simultaneously.
- **Automatic integration** — Steering files trigger knowledge fetch/commit during agent interactions without manual intervention.

## Tech Stack & Design Choices

| Component | Choice | Why |
|-----------|--------|-----|
| Language | Python 3.9+ | Ships natively on RHEL 9 |
| Vector storage | [sqlite-vec](https://github.com/asg017/sqlite-vec) | Zero-dependency C extension for SQLite. pip-installable, no server needed |
| Embeddings | [fastembed](https://github.com/qdrant/fastembed) (ONNX) | CPU-only, no PyTorch/TensorFlow, no API keys. ~100MB footprint |
| Default model | BAAI/bge-small-en-v1.5 | 384-dim vectors, quantized for CPU, strong general-purpose retrieval |
| Concurrency | `fcntl.flock` | Native Linux file locking for write serialization. Reads are concurrent via SQLite WAL mode |
| Storage | Single `.db` file per repo | Artifacts, vectors, and audit trail in one file. Easy backup and migration |

**All dependencies are pip-installable.** No `dnf install` or system packages required beyond Python itself.

## Configuration (optional)

Create `.kiro/knowledge-config.json` in your project root or home directory:

```json
{
  "repo_mode": "user",
  "shared_repo_path": "/var/lib/agent-knowledge-repo/",
  "embedding_model": "BAAI/bge-small-en-v1.5",
  "default_top_n": 5,
  "similarity_threshold": 1.0
}
```

Without a config file, AKR defaults to user mode (`~/.kiro/knowledge/`).

## CLI Usage

### Commit knowledge

```bash
akr-commit --json '{
  "title": "SQLite WAL mode for concurrent reads",
  "content": "Enable WAL mode with PRAGMA journal_mode=WAL to allow concurrent readers while a single writer holds the lock.",
  "tags": ["database", "performance", "pattern"],
  "source_context": "akr/repository.py:ArtifactRepository.__init__"
}'
```

Output: `{"id": "a1b2c3d4-...", "status": "committed"}`

Or from a file:

```bash
akr-commit --file artifact.json
```

### Fetch knowledge (semantic search)

```bash
akr-fetch --query "how to handle concurrent database writes"
```

Options:
- `--top-n 10` — number of results (default: 5)
- `--threshold 0.5` — similarity threshold (default: 0.3, lower = stricter)
- `--repo shared|user|both` — which repository to search

### Update knowledge

```bash
akr-update --id a1b2c3d4-... --json '{
  "title": "Updated: SQLite WAL mode",
  "content": "Updated content with new findings...",
  "tags": ["database", "performance"],
  "source_context": "akr/repository.py"
}'
```

Previous versions are preserved in an audit trail automatically.

### Delete knowledge

```bash
akr-delete --id a1b2c3d4-...
```

### List and browse

```bash
# List recent knowledge
akr-list

# Filter by tags (AND logic)
akr-list --tags database,performance

# Filter by date
akr-list --since 2024-01-01

# Pagination
akr-list --limit 10 --offset 20
```

## Agent Integration (Steering Files)

AKR ships with a steering file at `.kiro/steering/agent-knowledge.md` that automatically instructs agents to:

1. **Fetch** relevant knowledge at the start of each interaction
2. **Commit** significant learnings (bug fixes, architecture decisions, patterns)
3. **Update** existing knowledge when new info supersedes old
4. **Check for duplicates** before committing

The steering file uses `inclusion: auto` so it's loaded into agent context automatically.

## Repository Modes

| Mode | Storage path | Use case |
|------|-------------|----------|
| `user` (default) | `~/.kiro/knowledge/` | Personal agent memory |
| `shared` | `/var/lib/agent-knowledge-repo/` (configurable) | Team-wide knowledge base |
| `both` | Both paths | Personal + team knowledge, results annotated with source |

## Knowledge Artifact Schema

Every artifact follows a consistent structure:

```json
{
  "title": "Short descriptive title",
  "content": "Detailed knowledge content — this is what gets embedded for search",
  "tags": ["architecture", "bug-fix", "pattern"],
  "source_context": "path/to/file.py:ClassName.method",
  "metadata": {"optional": "key-value pairs"}
}

```

Fields `id`, `created_at`, and `updated_at` are auto-generated.

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
python3 -m pytest tests/ -v
```

## License

See [LICENSE](LICENSE) for details.
