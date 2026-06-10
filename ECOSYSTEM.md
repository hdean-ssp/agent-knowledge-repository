# Ecosystem: How AKR Connects

```
                        ┌──────────────────────────────────┐
                        │   electRa/Castle Codebase        │
                        │       ~/work/genero              │
                        └───────────────┬──────────────────┘
                                        │ scanned by
                                        ▼
                        ┌──────────────────────────────────┐
                        │         genero-tools             │
                        │  workspace.db · modules.db       │
                        └──────┬───────────────────┬───────┘
                               │                   │
               queried by      │                   │  databases read by
                               ▼                   ▼
               ┌───────────────────┐   ┌───────────────────────────────┐
               │    genero-vim     │   │       electra-vault           │
               │  Vim/Neovim IDE   │   │  Obsidian vault generator     │
               │  plugin           │   │  (combines all 3 tiers)       │
               └───────────────────┘   └──────┬──────────┬────────────┘
                                              │          │
                            reads via         │          │  reads docs from
                            akr-export        │          │
                                              ▼          ▼
┌─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐
│                                                                           │
│  ┌════════════════════════════════════════┐   ┌────────────────────────┐  │
│  ║  agent-knowledge-repository (AKR)  ◄══╬═══╬═ electra-documentation  │  │
│  ║  ★ THIS REPO ★                        ║   │  references AKR IDs    │  │
│  ║                                        ║   │  (~35 pages)           │  │
│  ║  • Persistent AI agent memory          ║   └────────────────────────┘  │
│  ║  • ~165 semantic-searchable artifacts  ║                               │
│  ║  • Steering files + hooks for agents   ║                               │
│  ║  • Team-shared SQLite knowledge base   ║                               │
│  ╚════════════════════════════════════════╝                               │
│                                                                           │
└─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘
                    ▲                   ▲
                    │                   │
          agents commit/fetch    steering files + hooks
          knowledge via CLI      copied into target projects
```

## Role in the Ecosystem

AKR is the **experiential knowledge layer** — it captures what AI agents learn while working in the codebase and makes that knowledge persistent and searchable across sessions and team members.

## Connections

| Repo | Relationship |
|------|-------------|
| **genero-tools** | AKR's `codebase-intelligence` steering file teaches agents to combine `akr-fetch` with `query.sh` structural lookups for richer context |
| **electra-documentation** | Built using AKR artifacts as source material; references artifact IDs throughout (137 artifacts mapped in coverage matrix) |
| **electra-vault** | Reads AKR via `akr-export` to generate ~165 interlinked Obsidian knowledge pages (Tier 2 of the vault) |
| **genero-vim** | No direct dependency, but agents using genero-vim with AKR steering benefit from combined structural + experiential intelligence |

## Three-Tier Knowledge Model

```
Tier 1 (Structure)     genero-tools     → functions, calls, schema, metrics
Tier 2 (Experience)    AKR              → patterns, decisions, bug fixes, gotchas
Tier 3 (Business)      electra-docs     → architecture, data flows, integrations
                              │
                              ▼
                       electra-vault     → unified interlinked graph
```
