<!-- beadloom:badge-start -->
> ✅ **fresh**
> 
> last synced 2026-06-13T22:53:18.143877+00:00 · coverage 100% (`onboarding`)
> 
> _Validation by Beadloom `doc_sync` — same source as `sync-check`._
<!-- beadloom:badge-end -->

# Onboarding

Project bootstrap, documentation import, and architecture-aware initialization.

## Features

Each feature has its own `SPEC.md`:

- **[Agent Prime](features/agent-prime/SPEC.md)** — compact project context for AI sessions (`beadloom prime`).
- **[Doc Generator](features/doc-generator/SPEC.md)** — doc skeletons + polish data from the graph (`beadloom docs generate` / `polish`).
- **[Config Check](features/config-check/SPEC.md)** — AgentConfigAsCode drift detection (`beadloom config-check`).
- **[Branch Protection](features/branch-protection/SPEC.md)** — strict trunk-based `main` protection (`beadloom setup-branch-protection`).
- **[Agentic Flow Setup](features/agentic-flow-setup/SPEC.md)** — scaffold the multi-agent dev flow 1:1 (`beadloom setup-agentic-flow`).
- **[AI Tech-Writer Setup](features/ai-techwriter-setup/SPEC.md)** — scaffold the packaged AI tech-writer harness (`beadloom setup-ai-techwriter`).

## Specification

### Modules

- **scanner.py** — `bootstrap_project()` scans source directories, classifies subdirectories using preset rules, infers edges from directory nesting, generates `.beadloom/_graph/services.yml` + `.beadloom/config.yml`. Also detects project name, generates architecture rules, configures MCP for the detected editor, and creates IDE adapter files via `setup_rules_auto()`. Provides `import_docs()` for classifying existing .md files (ADR, feature, architecture, other). `generate_rules()` creates structural rules with empty `has_edge_to: {}` matcher for hierarchy validation. `_detect_framework_summary()` detects 20+ framework patterns (Django, Flask, FastAPI, NestJS, Angular, Next.js, Expo, React Native, Spring Boot, Actix, Gin, Vue, SwiftUI, Jetpack Compose, UIKit, Express, etc.). `_build_contextual_summary()` combines framework detection, tree-sitter symbol counts, README excerpts, and entry-point labels into a 120-char summary. `_sanitize_ref_id()` strips parentheses from Expo router dirs. `generate_agents_md()` creates `.beadloom/AGENTS.md` with the MCP tool list (built from the canonical `MCP_TOOL_CATALOG`, currently 18 tools) and architecture rules; preserves user content between `<!-- beadloom:custom-start -->` / `<!-- beadloom:custom-end -->` HTML comment markers (migrates old `## Custom` format automatically). It delegates to `build_agents_md_content()` — a pure in-memory builder (extracting the preserved custom block via `_extract_agents_custom_content()`) — so the AgentConfigAsCode drift checker (`config_sync.py`) can re-run the exact same generation logic without writing to disk. `_detect_rule_type()` maps all 7 YAML keys (`require`, `deny`, `forbid_cycles`, `layers`, `check`, `forbid_import`, `forbid`) to canonical type strings. `_build_rules_section()` uses `_detect_rule_type()` to produce accurate rule type labels for all 9 rules. `prime_context()` returns compact project context (static config + dynamic DB queries) for AI agent sessions. `_discover_entry_points()` detects CLI, script, server, and app entry points across 8 languages (Python Click/Typer/argparse, Go, Rust, Java, Kotlin, Swift, JS/TS). `_quick_import_scan()` infers `depends_on` edges between clusters by sampling code imports via tree-sitter. `interactive_init()` runs the interactive initialization wizard with re-init detection, mode selection, and auto-reindex. `non_interactive_init()` runs initialization without prompts for CI/script use, supporting `mode` (bootstrap/import/both), `force` (delete existing .beadloom/), and automatic doc linking + skeleton generation + reindex. `auto_link_docs()` fuzzy-matches existing `docs/` markdown files to graph nodes by ref_id similarity (exact path, stem match, partial match) and patches the `docs:` field in `services.yml`. `_ingest_readme()` extracts project metadata (description, tech stack, architecture notes) from README/CONTRIBUTING/ARCHITECTURE files. `refresh_claude_md()` refreshes auto-managed sections in `.claude/CLAUDE.md` between `<!-- beadloom:auto-start SECTION -->` / `<!-- beadloom:auto-end -->` marker pairs by regenerating dynamic content (project info facts) while preserving everything outside markers. Supports `dry_run` mode for preview. `_parse_markers()` extracts marker pairs from text. `_auto_insert_markers()` inserts markers around section 0.1 on first refresh if no markers exist. `_render_project_info_section()` generates the dynamic project-info content (stack, distribution, tests, linter, type checking, docs, architecture, version).
- **presets.py** — Architecture presets (`monolith`, `microservices`, `monorepo`) with directory classification rules and edge inference logic. `Preset` dataclass defines `name`, `description`, `dir_rules`, `default_kind`, `infer_part_of`, `infer_deps_from_manifests`. `PresetRule` dataclass maps directory name patterns to node kinds with confidence levels. `detect_preset()` checks for mobile app indicators (React Native/Expo via `package.json`, Flutter via `pubspec.yaml`) before falling back to directory heuristics.
- **doc_generator.py** — `generate_skeletons()` creates docs/ tree from graph nodes (architecture.md, domain READMEs, service pages, feature SPECs with `_doc_path_for_node()` resolution), writes `docs:` field back to `services.yml` via `_patch_docs_field()`, and generates `.beadloom/README.md` quick-start. `generate_polish_data()` returns structured JSON for AI-driven doc enrichment with SQLite dependency edges via `_enrich_edges_from_sqlite()`, symbol change detection (`_detect_symbol_changes()` / `_detect_symbol_changes_with_conn()`), and routes/activity/tests from `nodes.extra` via `_load_extra_from_sqlite()`. `format_polish_text()` renders multi-line human-readable polish output including symbol drift warnings, routes, activity level, and test metadata. SQLite operations in `_load_symbols_by_source()` and `_load_extra_from_sqlite()` catch `sqlite3.OperationalError` and log at debug level (non-fatal degradation when tables are missing).
- **config_reader.py** — `read_deep_config()` extracts scripts, workspaces, path aliases, and build metadata from project configuration files. Parses `pyproject.toml` ([project.scripts], [tool.pytest], [tool.ruff], [build-system]), `package.json` (scripts, workspaces, engines), `tsconfig.json` (compilerOptions.paths, baseUrl), `Cargo.toml` ([workspace] members, [features]), and `build.gradle`/`build.gradle.kts` (plugins, dependencies via regex). Merges results from multiple config sources with deduplication for scripts and workspaces.
- **ai_techwriter_setup.py** — Backs `beadloom setup-ai-techwriter --platform {github,gitlab}` (BDL-047 / F4.1, G8; BDL-051 / S2). Since the harness now ships INSIDE the installed `beadloom` package (`beadloom.ai_agents.ai_techwriter`), the scaffold **no longer vendors any Python** (the BDL-047/048 `HARNESS_MODULES` / `vendor_harness` / `sync_vendored_harness` drift-guard machinery is retired). `scaffold(target_root, platform=...)` idempotently drops: the chosen platform's CI wrapper (`_scaffold_github()` / `_scaffold_gitlab()` — GitLab appends job-only to an existing `.gitlab-ci.yml`, never blindly clobbering, and skips an already-wired file) which invokes `python -m beadloom.ai_agents.ai_techwriter`; the operator artifacts `tools/ai_techwriter/{recipe.yaml, provision-runner.sh}` (`_scaffold_recipe()` / `_scaffold_provision_runner()`) copied from the harness package data via `importlib.resources` — the recipe a readable reference of the agent's blast radius, the provisioner a hardened, idempotent (`0o755`) runner-stand-up script (`--platform/--repo/--token`, `set -euo pipefail`, fail-hard RAM (~2 GB min, ~4 GB recommended) + disk (~5 GB) prechecks, swap guaranteed *before* apt, GitHub Actions runner *or* GitLab Runner registration, best-effort+verified Goose/beadloom/bd installs); and the ≤3-step `docs/guides/ai-techwriter.md` (`_scaffold_guide()`). Raises `ValueError` on an unknown platform. `templates_root()` locates the packaged workflow/guide assets; `_read_harness_data()` reads the recipe/provisioner from the harness package.
- **agentic_flow_setup.py** — Backs `beadloom setup-agentic-flow` (BDL-048). `scaffold(project_root, *, force=False)` idempotently drops Beadloom's proven multi-agent dev flow into a target repo: the role subagents (`AGENT_FILES` → `.claude/agents/{dev,test,review,tech-writer}.md`) + slash skills (`COMMAND_FILES` → `.claude/commands/{coordinator,task-init,checkpoint,templates}.md`) are vendored **byte-identical** from the package-data assets (`onboarding/templates/agentic_flow/`, inert `.md.txt` copies of the live `.claude/`), and `.claude/CLAUDE.md` is dropped (only when absent, or with `force`) then its `project-info` auto-region is regenerated for the TARGET project via `refresh_claude_md`. `_scaffold_vendored()` is idempotent — a matching file is left alone, a hand-edited file is skipped (unless `force`) so user edits are not clobbered; returns `ScaffoldResult` (files written/skipped + the CLAUDE.md path + changed sections). The vendored CLAUDE.md carries a neutral `__BEADLOOM_PROJECT_NAME__` token in its `## 0.1 Project:` heading, substituted with the detected project name on scaffold (`_claude_md_base()`). `sync_agentic_flow(live_claude_root)` is the drift guard (principle: preserve the flow 1:1): it refreshes the packaged `.md.txt` assets from the live `.claude/` (and snapshots `CLAUDE.md` with the project name tokenized), asserted byte-for-byte in the test suite. `templates_root()` / `vendored_flow_root()` locate the packaged assets.
- **branch_protection.py** — Backs `beadloom setup-branch-protection` (BDL-049, contexts updated in BDL-050). An idempotent `main`-branch-protection helper for the trunk-based flow (CLAUDE.md §6): every change integrates via a PR (no direct push) and the consolidated `ci.yml` checks are **required status checks**, so the pipeline becomes true enforcement (hardening BDL-048 G5). `build_protection_payload(*, status_check_contexts=DEFAULT_STATUS_CHECK_CONTEXTS)` builds the GitHub request body — `required_status_checks {strict: true, contexts}`, `enforce_admins: true`, `required_pull_request_reviews {required_approving_review_count: 0}`, `restrictions: null` — so a PR IS required and even admins cannot direct-push (strict trunk-based), but the **owner is NOT locked out** (can self-merge once the pipeline is green, since 0 required reviews + the un-filtered `ci.yml` checks). `DEFAULT_STATUS_CHECK_CONTEXTS = ("gate", "tests (3.10)", "tests (3.11)", "tests (3.12)", "tests (3.13)", "site-build", "ai-techwriter")` are the **real** consolidated `ci.yml` check-run names (BDL-050 — the job names + the un-filtered 3.10-3.13 matrix legs); a required context MUST match a real check-run name EXACTLY and must NOT be a path-filtered workflow's check (under `strict` it would never run → permanently-unmergeable PR/`main`), which is why BDL-050 dropped the `tests` paths filter. `BranchProtectionRequest` (frozen dataclass: owner/repo/branch/`status_check_contexts`) exposes `endpoint()`, `payload_json()` (deterministic `sort_keys`), and `gh_args()` (the `gh api --method PUT … --input -` argv). `apply_branch_protection(owner, repo, *, branch="main", status_check_contexts=..., runner=None)` builds the declarative `PUT .../protection` and runs it through an injectable `GhRunner` seam (defaults to the real `gh` CLI; tests pass a fake that records argv + stdin without touching GitHub). `PUT .../protection` is declarative, so re-running re-settles the same state (idempotent).
- **config_sync.py** — AgentConfigAsCode drift detection. `check_config_drift(project_root, conn)` re-runs the SAME `setup-rules --refresh` generator in memory and diffs its output against on-disk content, returning a `ConfigDrift(file, reason)` per drifted artifact (deterministically sorted by file). It reuses `build_agents_md_content()` (AGENTS.md), `refresh_claude_md(dry_run=True)` (CLAUDE.md auto-managed sections), and the `_RULES_ADAPTER_TEMPLATE` / `_is_beadloom_adapter()` adapter helpers — never a parallel reimplementation. Checks ONLY auto-managed regions: AGENTS.md diffing ignores the user `custom` block (`_agents_auto_region()`), CLAUDE.md diffing covers only the `auto-start`/`auto-end` marker sections, so editing human prose can never trip it (avoids the #73 false-positive class). Absent target files are skipped (not drift). As of BDL-048, `check_config_drift` also covers the **scaffolded agentic-flow files**: when the flow is fully scaffolded (`_agentic_flow_scaffolded()`), `_agentic_flow_drifts()` byte-compares each present vendored `agents/*` + `commands/*` file against the shipped template. `refresh_agentic_flow_files(project_root)` is the `config-check --fix` companion — it re-drops the vendored flow files into a scaffolded repo (gated on the flow already being present, so it never forces the flow onto a repo that did not adopt it). The `conn` parameter is accepted for signature symmetry with the `beadloom ci` orchestrator. Backs the `beadloom config-check [--fix]` command.

### CLI Commands

```bash
beadloom init --bootstrap [--preset {monolith,microservices,monorepo}]
beadloom init --import DOCS_DIR
beadloom init  # interactive mode
beadloom init --yes [--mode {bootstrap,import,both}] [--force]  # non-interactive mode
beadloom docs generate   # create doc skeletons from graph
beadloom docs polish     # structured data for AI enrichment (text or JSON)
beadloom docs audit      # scan project docs for stale fact mentions (text or JSON)
beadloom prime           # compact project context for AI agent injection
beadloom setup-rules     # create IDE adapter files (.cursorrules, etc.)
beadloom setup-rules --refresh           # refresh auto-managed CLAUDE.md sections
beadloom setup-rules --refresh --dry-run # preview changes without writing
beadloom setup-agentic-flow              # scaffold the packaged multi-agent dev flow into .claude/
beadloom setup-agentic-flow --force      # overwrite hand-edited scaffolded flow files
beadloom config-check                    # detect agent-config drift (exit 1 on drift)
beadloom config-check --fix              # regenerate drifted artifacts (+ restore flow files), then re-check
beadloom setup-branch-protection --repo OWNER/NAME            # protect main: PR required + consolidated ci.yml checks required (gate/tests (3.10..3.13)/site-build/ai-techwriter) (GitHub)
beadloom setup-branch-protection --repo OWNER/NAME --dry-run  # print the gh api call + payload without touching GitHub
beadloom snapshot save [--label LABEL]           # save current graph state
beadloom snapshot list [--json]                  # list all saved snapshots
beadloom snapshot compare OLD_ID NEW_ID [--json] # compare two snapshots
```

## API

Module `src/beadloom/onboarding/scanner.py`:
- `scan_project(project_root)` -- scan project structure, return manifests, source_dirs, file_count, languages
- `classify_doc(doc_path)` -- classify a markdown document (adr, feature, architecture, other)
- `bootstrap_project(root, *, preset_name=None)` -- auto-generate graph from code structure (incl. root node, rules, MCP config, AGENTS.md, IDE rules)
- `import_docs(root, docs_dir)` -- classify and import existing documentation
- `generate_rules(nodes, edges, project_name, rules_path)` -- generate architecture rules with empty matcher for hierarchy validation
- `setup_mcp_auto(project_root)` -- auto-detect editor and create MCP config
- `setup_rules_auto(project_root)` -- auto-detect IDEs and create adapter files (`.cursorrules`, `.windsurfrules`, `.clinerules`); content-aware: skips user-edited files
- `generate_agents_md(project_root)` -- generate `.beadloom/AGENTS.md` with the MCP tool list (from `MCP_TOOL_CATALOG`, currently 18 tools) and rules; preserves content between `<!-- beadloom:custom-start -->` / `<!-- beadloom:custom-end -->` HTML comment markers (auto-migrates old `## Custom` format)
- `prime_context(project_root, *, fmt="markdown")` -> `str | dict[str, Any]` -- compact project context for AI agent injection (static + dynamic layers, <=2K tokens); returns markdown string or JSON dict depending on *fmt*
- `interactive_init(project_root)` -- interactive wizard with re-init detection, mode selection, review table, auto-reindex
- `non_interactive_init(project_root, *, mode="bootstrap", force=False)` -- non-interactive init for CI/scripts; supports bootstrap/import/both modes, force-deletes existing .beadloom/ when force=True, auto-links docs, generates skeletons, runs reindex
- `auto_link_docs(project_root, nodes)` -- fuzzy-match existing docs/ files to graph nodes by ref_id (exact path, stem, partial match); patches docs: field in services.yml via _patch_docs_field; returns count of linked docs
- `refresh_claude_md(project_root, *, dry_run=False)` -> `list[str]` -- refresh auto-managed sections in `.claude/CLAUDE.md` between marker pairs; returns list of change descriptions; supports dry_run for preview without writing

Module `src/beadloom/onboarding/presets.py`:
- `Preset` -- frozen dataclass: name, description, dir_rules, default_kind, infer_part_of, infer_deps_from_manifests
- `PresetRule` -- frozen dataclass: pattern, kind, confidence
- `Preset.classify_dir(dir_name)` -- return (kind, confidence) for a directory name
- `PRESETS` -- dict mapping preset names to `Preset` instances
- `detect_preset(root)` -- auto-detect architecture (mobile-aware: checks React Native/Expo/Flutter first)

Module `src/beadloom/onboarding/doc_generator.py`:
- `generate_skeletons(project_root, nodes?, edges?)` -- create docs/ tree from graph, write `docs:` back to YAML, generate `.beadloom/README.md`
- `generate_polish_data(project_root, ref_id?)` -- return structured JSON with SQLite dependency edges, symbol change detection, routes/activity/tests
- `format_polish_text(data)` -- render polish data as multi-line human-readable text with symbol drift, routes, activity, tests

Module `src/beadloom/onboarding/config_sync.py`:
- `ConfigDrift(file, reason)` -- frozen dataclass describing one drifted agent-config artifact
- `check_config_drift(project_root, conn)` -- regenerate AGENTS.md + CLAUDE.md auto-sections + IDE adapters in memory and diff vs disk; returns sorted `list[ConfigDrift]` (auto-managed regions only)

Module `src/beadloom/onboarding/ai_techwriter_setup.py`:

- `scaffold(target_root, platform=...)` -- drop the platform CI wrapper (calling `python -m beadloom.ai_agents.ai_techwriter`) + the operator artifacts (`recipe.yaml`/`provision-runner.sh` from package data) + the getting-started guide (idempotent); raises `ValueError` on an unknown platform. **No Python vendoring** (BDL-051 / S2 — the harness ships in the wheel).
- `_scaffold_provision_runner(target_root)` -- drop the hardened, idempotent, executable `provision-runner.sh` (swap-first, RAM/disk prechecks, GitHub/GitLab runner registration) into `tools/ai_techwriter/` (from harness package data)
- `_scaffold_recipe(target_root)` -- drop a readable copy of the Goose recipe (harness package data) into `tools/ai_techwriter/` for operator reference
- `templates_root()` -- locate the packaged workflow/guide scaffold assets
- `PLATFORMS` -- supported CI platforms (`github`, `gitlab`)

Module `src/beadloom/onboarding/agentic_flow_setup.py`:
- `scaffold(project_root, *, force=False)` -- scaffold the packaged dev flow (vendored `agents/*` + `commands/*` byte-identical + CLAUDE.md auto-regions per-project); idempotent; returns `ScaffoldResult`
- `sync_agentic_flow(live_claude_root)` -- refresh the packaged `.md.txt` assets from the live `.claude/` (drift guard; asserted byte-for-byte in tests)
- `templates_root()` / `vendored_flow_root()` -- locate the packaged scaffold assets
- `AGENT_FILES` / `COMMAND_FILES` -- the vendored role + command file stems
- `ScaffoldResult` -- dataclass: files written/skipped + CLAUDE.md path + changed sections

Module `src/beadloom/onboarding/config_sync.py` (BDL-048 additions):
- `refresh_agentic_flow_files(project_root)` -- re-drop the vendored agentic-flow files into a scaffolded repo (the `config-check --fix` companion; gated on the flow already being present)

Module `src/beadloom/onboarding/branch_protection.py` (BDL-049):
- `build_protection_payload(*, status_check_contexts=DEFAULT_STATUS_CHECK_CONTEXTS)` -- build the GitHub branch-protection request body (PR required, the consolidated `ci.yml` checks required under `strict`, `enforce_admins: true` → strict trunk-based even for admins, 0 required reviews, `restrictions: null` → owner NOT locked out, can self-merge once the pipeline is green)
- `apply_branch_protection(owner, repo, *, branch="main", status_check_contexts=..., runner=None)` -- configure branch protection via `gh api` PUT (idempotent/declarative); `runner` is an injectable `GhRunner` (defaults to the real `gh` CLI); returns the `BranchProtectionRequest` sent
- `BranchProtectionRequest` -- frozen dataclass (owner/repo/branch/`status_check_contexts`); `endpoint()`, `payload_json()` (deterministic), `gh_args()`
- `GhRunner` -- `Protocol` for the injected `gh` runner (`(argv, stdin) -> stdout`)
- `DEFAULT_STATUS_CHECK_CONTEXTS = ("gate", "tests (3.10)", "tests (3.11)", "tests (3.12)", "tests (3.13)", "site-build", "ai-techwriter")` / `DEFAULT_BRANCH = "main"` -- the consolidated `ci.yml` required check-runs (BDL-050) + the default trunk

Module `src/beadloom/onboarding/config_reader.py`:
- `read_deep_config(project_root)` -- extract scripts, workspaces, path aliases from pyproject.toml, package.json, tsconfig.json, Cargo.toml, build.gradle

## Testing

Tests: `tests/test_onboarding.py`, `tests/test_presets.py`, `tests/test_cli_init.py`, `tests/test_doc_generator.py`, `tests/test_cli_docs.py`, `tests/test_integration_onboarding.py`, `tests/test_bead06_misc_fixes.py`, `tests/test_config_reader.py`, `tests/test_auto_link_docs.py`, `tests/test_init_doc_generation.py`, `tests/test_snapshot.py`, `tests/test_cli_snapshot.py`, `tests/test_refresh_claude_md.py`, `tests/test_config_sync.py`, `tests/test_cli_config_check.py`, `tests/test_cli_setup_ai_techwriter.py`, `tests/test_cli_setup_agentic_flow.py`, `tests/test_branch_protection.py`
