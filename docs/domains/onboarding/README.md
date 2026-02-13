# Onboarding

Project bootstrap, documentation import, and architecture-aware initialization.

## Specification

### Modules

- **scanner.py** — `bootstrap_project()` scans source directories, classifies subdirectories using preset rules, infers edges from directory nesting, generates `.beadloom/_graph/services.yml` + `.beadloom/config.yml`. Also detects project name, generates architecture rules, and configures MCP for the detected editor. Provides `import_docs()` for classifying existing .md files (ADR, feature, architecture, other). `generate_rules()` creates structural rules with empty `has_edge_to: {}` matcher for hierarchy validation. `_detect_framework_summary()` detects Django/React/Python/Docker patterns. `_sanitize_ref_id()` strips parentheses from Expo router dirs.
- **presets.py** — Architecture presets (`monolith`, `microservices`, `monorepo`) with directory classification rules and edge inference logic. `detect_preset()` checks for mobile app indicators (React Native/Expo via `package.json`, Flutter via `pubspec.yaml`) before falling back to directory heuristics.
- **doc_generator.py** — `generate_skeletons()` creates docs/ tree from graph nodes, writes `docs:` field back to `services.yml` via `_patch_docs_field()`. `generate_polish_data()` returns structured JSON for AI-driven doc enrichment with SQLite dependency edges. `format_polish_text()` renders multi-line human-readable polish output.

### CLI Commands

```bash
beadloom init --bootstrap [--preset {monolith,microservices,monorepo}]
beadloom init --import DOCS_DIR
beadloom init  # interactive mode
beadloom docs generate   # create doc skeletons from graph
beadloom docs polish     # structured data for AI enrichment (text or JSON)
```

## API

Module `src/beadloom/onboarding/scanner.py`:
- `bootstrap_project(root, preset=None)` — auto-generate graph from code structure (incl. root node, rules, MCP config)
- `import_docs(root, docs_dir)` — classify and import existing documentation
- `generate_rules(nodes, edges)` — generate architecture rules with empty matcher for hierarchy validation
- `setup_mcp_auto(project_root)` — auto-detect editor and create MCP config

Module `src/beadloom/onboarding/presets.py`:
- `get_preset(name)` — get preset configuration
- `detect_preset(root)` — auto-detect architecture (mobile-aware: checks React Native/Expo/Flutter first)

Module `src/beadloom/onboarding/doc_generator.py`:
- `generate_skeletons(project_root, nodes?, edges?)` — create docs/ tree from graph, write `docs:` back to YAML
- `generate_polish_data(project_root, ref_id?)` — return structured JSON with SQLite dependency edges
- `format_polish_text(data)` — render polish data as multi-line human-readable text

## Testing

Tests: `tests/test_onboarding.py`, `tests/test_presets.py`, `tests/test_cli_init.py`, `tests/test_doc_generator.py`, `tests/test_cli_docs.py`, `tests/test_integration_onboarding.py`, `tests/test_bead06_misc_fixes.py`
