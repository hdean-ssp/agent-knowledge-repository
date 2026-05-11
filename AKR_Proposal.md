# Agent Knowledge Repository (AKR)

## Team-Wide Adoption Proposal

---

## What Is AKR?

In short: a shared brain for our AI agents.

Right now, every time we start a new AI session, the agent knows nothing about our codebase, our decisions, or the problems we've already solved. AKR fixes that. It's a lightweight tool that lets agents **save what they learn** and **recall it later**, across sessions and across the whole team.

Think of it like a team wiki that writes itself, except it's searchable by meaning (not just keywords) and agents use it automatically without us having to do anything.

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│   TODAY (without AKR)                                               │
│                                                                     │
│   Dev A's Agent          Dev B's Agent          Dev C's Agent       │
│   ┌───────────┐          ┌───────────┐          ┌───────────┐       │
│   │ Learns X  │          │ Learns X  │          │ Learns X  │       │
│   │ (again)   │          │ (again)   │          │ (again)   │       │
│   │           │          │           │          │           │       │
│   │ Forgets   │          │ Forgets   │          │ Forgets   │       │
│   │ next      │          │ next      │          │ next      │       │
│   │ session   │          │ session   │          │ session   │       │
│   └───────────┘          └───────────┘          └───────────┘       │
│                                                                     │
│   Each agent starts from zero, every time.                          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

                              vs.

┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│   WITH AKR                                                          │
│                                                                     │
│   Dev A's Agent          Dev B's Agent          Dev C's Agent       │
│   ┌───────────┐          ┌───────────┐          ┌───────────┐       │
│   │ Learns X  │          │ Needs X?  │          │ Needs X?  │       │
│   │           │          │           │          │           │       │
│   │ Commits   │          │ Fetches   │          │ Fetches   │       │
│   │ to AKR ───┼──┐       │ from AKR◄─┼──┐       │ from AKR◄─┼──┐    │
│   └───────────┘  │       └───────────┘  │       └───────────┘  │    │
│                  │                      │                      │    │
│                  ▼                      │                      │    │
│          ┌──────────────────────────────────────────────────┐  │    │
│          │           Shared Knowledge Base                  │  │    │
│          │                                                  │◄─┘    │
│          │  Bug fixes, patterns, decisions, gotchas...      │       │
│          │  Searchable by meaning (vector embeddings)       │       │
│          └──────────────────────────────────────────────────┘       │
│                                                                     │
│   Learn once, benefit everywhere.                                   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## What Does It Actually Deliver?

AKR is a **CLI tool + agent integration** that provides:

1. **A persistent knowledge store** backed by a single SQLite file (no servers, no infrastructure)
2. **Semantic search** so agents find relevant knowledge by meaning, not exact keyword matches
3. **Automatic integration** with AI agents via steering files and hooks, so agents fetch and commit knowledge without developer intervention
4. **Team-wide sharing** via a shared repository path (network mount, shared filesystem, etc.)
5. **Full audit trail** so you can see what was learned, when, and what changed

The core loop is simple:

```
Agent encounters something useful
        │
        ▼
   akr-commit  (saves it with tags and context)
        │
        ▼
   Stored as text + vector embedding in SQLite
        │
        ▼
Later, any agent on the team runs akr-fetch
        │
        ▼
   Semantic search finds relevant knowledge
        │
        ▼
   Agent uses it immediately, no re-discovery needed
```

---

## Problems This Solves

### Knowledge evaporates between sessions

AI agents have zero memory between conversations. Every new chat means re-exploring the same code, re-discovering the same patterns, re-learning the same quirks. That's wasted time and wasted credits.

### Everyone's agent re-learns the same things

Without shared knowledge, five developers means five agents independently figuring out the same build system, the same legacy code traps, the same deployment steps. That's five times the cost for the same outcome.

### Tribal knowledge lives in people's heads (or Teams messages)

The obscure fix for that one Jenkins issue, the reason we pinned that dependency, the workaround for that API quirk. It's scattered across old messages, or worse, only in someone's memory. When they're off or move on, it's gone.

### Agents give inconsistent advice

Without shared context, one developer's agent suggests pattern A while another's suggests pattern B for the same problem. The codebase drifts apart.

### Credits burn on re-discovery

Agents spend tokens exploring and reasoning about things that were already figured out last week. That's real money.

---

## Benefits

| Benefit | What it means for us |
|---------|---------------------|
| **Lower credit usage** | Agents retrieve known answers instead of re-exploring. Fewer tokens per interaction. |
| **Faster onboarding** | New starters' agents immediately know what the team knows |
| **Consistent code** | Shared patterns and decisions mean agents align on approach |
| **Self-maintaining docs** | Knowledge grows as agents work. No one has to write wiki pages. |
| **Zero infrastructure** | No servers, no Docker, no API keys. One pip install and you're done. |
| **Full audit trail** | Every change is versioned. You can trace why something was recorded. |
| **Works offline** | All embeddings run locally on CPU. No external calls. |

---

## Use Cases

### Capturing a bug fix

Dev spends an hour debugging a concurrency issue. Their agent commits the root cause and fix. Next time anyone hits something similar, their agent already knows the answer.

```bash
akr-commit --json '{
  "title": "Payment module deadlock on concurrent order updates",
  "content": "Root cause: nested transactions acquire locks in inconsistent order. Fix: always acquire account lock before order lock.",
  "tags": ["bug-fix", "concurrency", "payments"],
  "source_context": "src/payments/OrderService.java:process"
}'
```

### Recording a team decision

Team agrees on an approach. Committed once, every agent on the team respects it going forward.

```bash
akr-commit --json '{
  "title": "API versioning - URL path prefix",
  "content": "Use /api/v2/ path prefix for new endpoints. Header-based versioning rejected due to proxy issues. v1 endpoints unchanged until Q3.",
  "tags": ["architecture", "api", "decision"],
  "source_context": "docs/adr/007-api-versioning.md"
}'
```

### Flagging a dependency gotcha

Someone discovers a subtle version incompatibility. No one else has to hit the same wall.

```bash
akr-commit --json '{
  "title": "Jackson 2.15+ breaks custom deserializers with generics",
  "content": "Upgrading jackson-databind past 2.15.0 causes ClassCastException in GenericResponseDeserializer. Workaround: pin to 2.14.x or rewrite using TypeFactory.constructParametricType().",
  "tags": ["dependency", "bug-fix", "jackson"],
  "source_context": "pom.xml, src/common/GenericResponseDeserializer.java"
}'
```

### Searching by meaning

An agent working on auth doesn't need to know the exact title of a previous artifact. It just asks:

```bash
akr-fetch --query "how do we handle token refresh"
```

Vector search finds the most relevant results even if the wording is completely different from what was originally stored.

---

## Technical Implementation

### How It Works Under the Hood

```
┌──────────┐      ┌───────────────┐      ┌──────────────────┐
│          │      │               │      │                  │
│  CLI     │─────►│  Service      │─────►│  SQLite DB       │
│  Commands│      │  Layer        │      │  + sqlite-vec    │
│          │◄─────│               │◄─────│  (vector search) │
└──────────┘      └───────┬───────┘      └──────────────────┘
                          │
                  ┌───────▼───────┐
                  │   Embedding   │
                  │   Engine      │
                  │  (fastembed,  │
                  │   CPU-only)   │
                  └───────────────┘
```

### Tech Stack

| Component | Choice | Why |
|-----------|--------|-----|
| Language | Python 3.9+ | Ships natively on RHEL 9 |
| Vector storage | sqlite-vec | Zero-dependency SQLite extension, pip-installable |
| Embeddings | fastembed (ONNX) | CPU-only, no PyTorch, no API keys, ~100MB |
| Default model | BAAI/bge-small-en-v1.5 | 384-dim vectors, fast on CPU, strong retrieval quality |
| Concurrency | fcntl.flock + SQLite WAL | Concurrent reads, serialised writes, no conflicts |
| Storage | Single .db file | Artifacts + vectors + audit trail in one file |

### Concurrency (Multiple Developers)

```
  Dev A (reading)     Dev B (reading)     Dev C (writing)
       │                   │                    │
       ▼                   ▼                    ▼
  ┌─────────────────────────────────────────────────┐
  │              SQLite (WAL mode)                  │
  │                                                 │
  │  Reads: fully concurrent, never blocked         │
  │  Writes: one at a time via file lock            │
  │  No data corruption, no conflicts               │
  └─────────────────────────────────────────────────┘
```

### Repository Modes

```
┌────────────────────────────────────────────────────────┐
│                                                        │
│  "user" mode     Personal repo at ~/.kiro/knowledge/   │
│                  Good for personal notes and WIP       │
│                                                        │
│  "shared" mode   Team repo at a shared path            │
│                  Team decisions, patterns, fixes       │
│                                                        │
│  "both" mode     Searches both, merges results         │
│                  Best of both worlds                   │
│                                                        │
└────────────────────────────────────────────────────────┘
```

---

## What It Takes to Set Up

### Per developer (one-time)

```bash
pip install -e /path/to/agent-knowledge-repository
```

That's it. All dependencies come in via pip. No system packages needed.

### Team config (one-time)

Add to each project's `.kiro/knowledge-config.json`:

```json
{
  "repo_mode": "both",
  "shared_repo_path": "/path/to/shared/mount/"
}
```

Copy the steering file and hook into the project's `.kiro/` directory, and agents start using AKR automatically.

### Storage

- Single `.db` file per repository
- Even thousands of artifacts fit in under 50MB
- Backup = copy the file. Migration = export to JSON, import elsewhere.

---

## Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| Stale or incorrect knowledge | Audit trail + update/delete commands; agents can flag outdated info |
| Storage growth | Artifacts are small text; growth is minimal |
| Embedding model download | ~100MB one-time download, cached locally after that |
| Write conflicts | File locking handles this; reads are never blocked |
| Shared DB availability | SQLite is robust; regular backups via `akr-export` |

---

## Summary

AKR gives our AI agents a shared memory. Every bug fix, every decision, every gotcha becomes permanently searchable knowledge that benefits the whole team, automatically, with no manual upkeep.

It requires no infrastructure, installs in one command, and integrates transparently with our existing AI tooling. Adopting it team-wide as we move to our next dev system means we compound what we learn rather than repeatedly rediscovering it.
