# CONTEXT: BDL-051 (EPIC) — Beadloom governs itself

> **Status:** Approved
> **Created:** 2026-06-11
> **PRD/RFC:** ./PRD.md · ./RFC.md

---

## State

- **Graph model:** nodes declared in `.beadloom/_graph/services.yml` (6 domains: context-oracle, doc-sync, graph, onboarding, infrastructure, application; 15 features; services). Code annotated `# beadloom:domain=X` / `# beadloom:feature=Y` (parsed by `context_oracle/code_indexer.py` → `code_symbols.annotations`). A module with `domain=` but no `feature=` → attributed to the domain, lands in `docs/domains/<X>/README.md`.
- **Lint:** `graph/rule_engine.py` + `.beadloom/_graph/rules.yml` — rule types `require` / `forbid_import` / `cardinality` (e.g. `domain-size-limit: max_symbols 200`, severity warn — `graph` is 202>200). New `unregistered-feature-candidate` check slots into this engine.
- **`code_symbols`:** tree-sitter symbol index (853 symbols); powers sync-check (`symbols_hash`), rules, ctx/why. The lint reads its `annotations`/`file_path`.
- **ai_techwriter harness:** `tools/ai_techwriter/` — invoked `python -m tools.ai_techwriter`; vendored into target repos by `onboarding/ai_techwriter_setup.py` (`HARNESS_MODULES` → `*.py.txt` + `sync_vendored_harness` drift-guard). `config.yml scan_paths: [src]` → tools/ NOT scanned (no node/symbols/sync-check). BDL-049/050 model: PR-triggered, `--target pr-branch`, verdict {ok/flagged/infra}, loop-guard, AI_TW_PAT.
- **MCP process-tools (BDL-048):** `services/mcp_server.py` — `task_init`/`bead_context`/`complete_bead`/`checkpoint`. `checkpoint` appends an ACTIVE.md note; neither it nor `complete_bead` maintains the bead-status TABLE.
- **Repo:** strict trunk-based (PR per slice via consolidated `ci.yml`; `enforce_admins:true`). See [[project_trunk_based]].

## Decisions (from PRD/RFC)

- 4 trunk-based slices: S1 def+sprawl-lint → S2 ai_agents move + retire vendoring → S3 onboarding re-model + 6-domain audit → S4 process-tools ACTIVE-table fix + adoption.
- Sprawl-lint = `unregistered-feature-candidate` (warn): per domain, files with `domain=`/no-`feature=`/≥N symbols (N=5).
- ai_agents: `tools/ai_techwriter` → `src/beadloom/ai_agents/ai_techwriter/`; **retire vendoring** (harness ships in the package; `python -m beadloom.ai_agents.ai_techwriter`); recipe/provisioner → package-data; `ai_agents` boundary rule.
- onboarding new features: config-check, branch-protection, agentic-flow-setup, ai-techwriter-setup; config_reader/presets stay domain-level.
- ACTIVE-table maintenance in the MCP tools (code) + coordinator adoption (process). Orchestration stays main-loop (BDL-048 G4).

## Code standards (from CLAUDE.md §0.1)

- Python 3.10+, SQLite, Click, Rich, tree-sitter. pytest (≥80% changed). ruff. mypy --strict (no `Any`/ignore w/o reason). DDD boundaries (`lint --strict`). No bare except, no `import *`, no mutable defaults. Shell: `-f`.
- New domain `ai_agents/` must respect DDD direction (consumes application/context_oracle/graph read APIs; not imported BY core).

## Constraints / invariants

- **Every slice is an independently-green PR on the consolidated `ci.yml`** (gate + tests 3.10–3.13 + site-build + ai-techwriter). main green by construction.
- **The ai_agents move is behavior-preserving** — BDL-049/050 ai-techwriter model byte-identical; S2's PR re-runs the live agent on the new path (dogfood).
- New code fail-safe: sprawl-lint = warn-only (never blocks); ACTIVE-table updater = best-effort (falls back to append; never crashes the tool).
- Anonymize third-party project names in committed artifacts.

## Definition of done

All G1–G8 met: documented feature definition; `unregistered-feature-candidate` lint live (flags the onboarding sprawl, clean after re-model); `ai_agents/ai_techwriter` graph-tracked (symbols/sync-check/lint/SPEC) with vendoring retired + CI green on the new path; onboarding re-modeled + 6 domains audited; `checkpoint`/`complete_bead` maintain the ACTIVE.md table; docs/CHANGELOG/ROADMAP updated; speed work renumbered to BDL-052; suite + `ci.yml` green per slice.
