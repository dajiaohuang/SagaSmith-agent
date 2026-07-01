# SagaSmith Refactor — Handover

> Branch: `refactor/v1` | Base: nanobot v0.2.2 | Date: 2026-07-01

## Goal

Rebuild SagaSmith from a clean nanobot v0.2.2 base, with D&D and CoC as **equal built-in systems** sharing a common TTRPG infrastructure layer. Tighten custom tooling by deduplicating ChromaDB, SQLAlchemy, and embedding code.

## Architecture

```
nanobot/                          # Pure nanobot v0.2.2 (HKUDS/nanobot)
│
├── ttrpg/                        # 🆕 Shared TTRPG infrastructure
│   ├── _paths.py                 #    ~/.sagasmith runtime paths
│   ├── db/base.py                #    Database + Base (SQLAlchemy)
│   ├── vector/client.py          #    VectorStore singleton (ChromaDB)
│   ├── vector/search.py          #    chroma_dense_search
│   └── rules/embedding.py        #    BgeM3Embedder + EmbeddingProfile
│
├── dnd/                          # D&D-specific (models, services, d20 engine)
│   ├── db/models/                #    Campaign, Character, Combat, etc.
│   ├── db/campaigns.py           #    CampaignService
│   ├── db/snapshots.py           #    Snapshot save/load + DAG branching
│   ├── db/recap.py               #    Diff-based recap generation
│   ├── db/memory.py              #    Campaign long-term memory
│   ├── db/undo.py                #    Undo/redo
│   ├── db/characters.py          #    Character CRUD
│   ├── db/module_content.py      #    Module import (PDF, Markdown)
│   ├── db/module_progress.py     #    Scene progress tracking
│   ├── db/migration.py           #    Alembic migration harness
│   ├── db/migrations/            #    9 migration scripts
│   ├── engine.py                 #    d20 engine loader (Rust-backed)
│   ├── modules/search.py         #    ModuleSearchService (lexical + dense)
│   ├── rules/search.py           #    RuleSearchService (3-tier)
│   ├── rules/ingest.py           #    Rule ingest pipeline
│   ├── rules/parser.py           #    SRD Markdown parser
│   ├── memory_search.py          #    Campaign memory search
│   └── vector/__init__.py        #    Re-exports from ttrpg
│
├── coc/                          # CoC7-specific (models, services, d100 engine)
│   ├── db/models/                #    Campaign, Character, Sanity, etc.
│   ├── db/campaigns.py           #    CampaignService
│   ├── db/snapshots.py           #    Snapshot save/load
│   ├── db/recap.py               #    Recap generation
│   ├── db/memory.py              #    Campaign memory
│   ├── db/undo.py                #    Undo/redo
│   ├── db/characters.py          #    Character CRUD
│   ├── db/module_content.py      #    Module import
│   ├── db/module_progress.py     #    Scene progress
│   ├── engine/                   #    d100 engine
│   │   ├── dice/rolls.py         #       d100 + bonus/penalty dice
│   │   ├── checks/skill.py       #       5 success levels
│   │   ├── checks/combat.py      #       Melee/ranged + DB
│   │   ├── checks/sanity.py      #       SAN loss + insanity
│   │   ├── checks/chase.py       #       Chase system
│   │   ├── development.py        #       Skill/luck growth
│   │   └── templates.py          #       Data templates
│   ├── modules/search.py         #    ModuleSearchService (adapted from D&D)
│   ├── rules/search.py           #    RuleSearchService (3-tier)
│   ├── rules/ingest.py           #    Rule ingest pipeline
│   ├── rules/parser.py           #    SRD Markdown parser
│   ├── memory_search.py          #    Campaign memory search
│   └── vector/__init__.py        #    Re-exports from ttrpg
│
├── skills/
│   ├── dnd-dm/                   # D&D DM skill (always-on) + SRD references
│   ├── dnd-campaign-manager/     # D&D campaign lifecycle skill
│   ├── dnd-module-gen/           # D&D module generation skill
│   ├── coc7-keeper/              # CoC Keeper skill (always-on)
│   └── coc7-campaign-manager/    # CoC campaign lifecycle skill
│
├── agent/tools/
│   ├── dnd_campaign.py           # tool: dnd_campaign
│   ├── dnd_save.py               # tool: dnd_save
│   ├── dnd_character.py          # tool: dnd_character
│   ├── dnd_rules.py              # tool: dnd_rules
│   ├── dnd_memory.py             # tool: dnd_memory
│   ├── dnd_module.py             # tool: dnd_module
│   ├── coc7_campaign.py          # tool: coc7_campaign
│   ├── coc7_save.py              # tool: coc7_save
│   ├── coc7_character.py         # tool: coc7_character
│   ├── coc7_rules.py             # tool: coc7_rules
│   ├── coc7_memory.py            # tool: coc7_memory
│   └── coc7_module.py            # tool: coc7_module
│
└── templates/
    ├── SOUL.md                   # Minthara Baenre (D&D DM persona)
    ├── IDENTITY.md               # D&D identity constraints
    └── coc/
        ├── SOUL.md               # CoC Keeper persona
        ├── IDENTITY.md           # CoC identity constraints
        └── AGENTS.md             # Session protocol
```

## What's Shared vs System-Specific

| Component | Shared (`ttrpg/`) | D&D (`dnd/`) | CoC (`coc/`) |
|---|---|---|---|
| **Database** | `Base`, `Database`, `default_database_url()` | ORM models, `CampaignService`, etc. | ORM models, `CampaignService`, etc. |
| **Vector** | `VectorStore` singleton, `chroma_dense_search()` | `dnd_rules` / `dnd_modules` collections | `coc7_rules` / `coc7_modules` collections |
| **Embedding** | `EmbeddingProfile`, `BgeM3Embedder`, `Embedder` protocol | — | — |
| **Dice Engine** | — | d20 + advantage/disadvantage | d100 + bonus/penalty dice |
| **Combat** | — | HP/AC/initiative | Melee/ranged + Damage Bonus |
| **Special** | — | Spell slots, class levels | Sanity, luck, chases, skill growth |
| **Rules Search** | 3-tier pattern (exact→lexical→dense) | D&D SRD ingestion | CoC 7e SRD ingestion |
| **Module Search** | lexical + dense pattern | D&D module chunking | CoC module chunking |
| **Tools** | — | 6 tools (`dnd_*`) | 6 tools (`coc7_*`) |

## Key Design Decisions

1. **One ChromaDB instance** — `VectorStore` singleton in `ttrpg.vector.client`, collections namespaced by system prefix (`dnd_*`, `coc7_*`)
2. **One Database infrastructure** — `ttrpg.db.base.Database` takes `system` parameter for path resolution (`~/.sagasmith/dnd/dnd.db` vs `~/.sagasmith/coc7/coc7.db`)
3. **One Embedding engine** — `ttrpg.rules.embedding.BgeM3Embedder` shared, env vars control profiles per system (`TTRPG_EMBEDDING_*`)
4. **Tools auto-discovered** — `ToolLoader` scans `nanobot.agent.tools.*` for `Tool` subclasses; all 12 tools registered automatically
5. **Skills as SKILL.md** — Each system's skill definitions are pure SKILL.md files; the agent runtime injects them based on active campaign

## Env Vars

### Shared
| Variable | Default | Purpose |
|---|---|---|
| `TTRPG_EMBEDDING_MODE` | `auto` | `auto`, `cpu`, or `gpu` |
| `TTRPG_EMBEDDING_MODEL` | — | Override BGE model |
| `TTRPG_EMBEDDING_BATCH_SIZE` | `8` | Batch size for encoding |
| `CHROMA_DB_URL` | — | Remote ChromaDB HTTP server |
| `CHROMA_DB_PATH` | — | Persistent ChromaDB path |
| `DATABASE_URL` | — | Fallback DB URL for all systems |

### D&D
| Variable | Default | Purpose |
|---|---|---|
| `DND_DATABASE_URL` | `~/.sagasmith/dnd/dnd.db` | SQLite path |
| `DND_EMBEDDING_PROFILES` | `bge_m3` | Comma-separated profile list |
| `DND_DENSE_DISABLED` | `1` | Set to `0` to enable dense vectors |

### CoC
| Variable | Default | Purpose |
|---|---|---|
| `COC7_DATABASE_URL` | `~/.sagasmith/coc7/coc7.db` | SQLite path |
| `COC7_EMBEDDING_PROFILES` | `bge_m3` | Comma-separated profile list |
| `COC7_DENSE_DISABLED` | `1` | Set to `0` to enable dense vectors |

## Todo / Known Gaps

- [ ] **CoC migrations** — CoC `db/` has no Alembic migration scripts yet (D&D has 9)
- [ ] **CoC rule SRD files** — `coc7-keeper/srd/` needs CoC 7e reference files (similar to D&D's SRD)
- [ ] **CoC module ingest** — `coc/rules/ingest.py` needs `ensure_bundled_rules_ingested()` tested
- [ ] **CoC `memory_search.py`** — stub implementation, needs the same DAG-based search as D&D
- [ ] **Database `upgrade_schema()`** — current implementation shells out to `alembic`; consider programmatic API
- [ ] **Rust d20 engine** — `dnd/engine.py` references `skills/dnd-dm/dnd-engine/src/dnd_engine`; ensure bundled correctly
- [ ] **Test suite** — no ttrpg-specific tests yet
- [ ] **Tool namespaces** — consider `dnd.campaign` / `coc7.campaign` naming instead of flat `dnd_campaign` / `coc7_campaign`

## Commit History

```
578f815 feat: integrate CoC7 domain + skills + tools on ttrpg shared layer
39ab6d3 feat: integrate D&D domain + skills + tools on ttrpg shared layer
22499c8 feat: reset to nanobot v0.2.2 + add shared ttrpg infrastructure
```

## Upstream Updatess

```bash
# Pull latest nanobot
git fetch upstream-nanobot
git merge upstream-nanobot/main

# Pull latest SagaSmith-agent (original)
git fetch upstream-sagasmith
```
