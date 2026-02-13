# Onboarding

Project bootstrap, documentation import, and architecture-aware initialization.

## Specification

### Modules

- **scanner.py** — `bootstrap_project()` scans source directories, classifies subdirectories using preset rules, infers edges from directory nesting, generates `.beadloom/_graph/services.yml` + `.beadloom/config.yml`. Also detects project name, generates architecture rules, and configures MCP for the detected editor. Provides `import_docs()` for classifying existing .md files (ADR, feature, architecture, other).
- **presets.py** — Architecture presets (`monolith`, `microservices`, `monorepo`) with directory classification rules and edge inference logic.
- **doc_generator.py** — `generate_skeletons()` creates docs/ tree from graph nodes; `generate_polish_data()` returns structured JSON for AI-driven doc enrichment.

### CLI Commands

```bash
beadloom init --bootstrap [--preset {monolith,microservices,monorepo}]
beadloom init --import DOCS_DIR
beadloom init  # interactive mode
beadloom docs generate   # create doc skeletons from graph
beadloom docs polish     # structured data for AI enrichment
```

## API

Module `src/beadloom/onboarding/scanner.py`:
- `bootstrap_project(root, preset=None)` — auto-generate graph from code structure (incl. root node, rules, MCP config)
- `import_docs(root, docs_dir)` — classify and import existing documentation
- `generate_rules(nodes, edges)` — generate architecture rules from graph structure
- `setup_mcp_auto(project_root)` — auto-detect editor and create MCP config

Module `src/beadloom/onboarding/presets.py`:
- `get_preset(name)` — get preset configuration
- `detect_preset(root)` — auto-detect architecture from directory structure

Module `src/beadloom/onboarding/doc_generator.py`:
- `generate_skeletons(project_root, nodes?, edges?)` — create docs/ tree from graph
- `generate_polish_data(project_root, ref_id?)` — return structured JSON for AI enrichment

## Testing

Tests: `tests/test_onboarding.py`, `tests/test_presets.py`, `tests/test_cli_init.py`, `tests/test_doc_generator.py`, `tests/test_cli_docs.py`, `tests/test_integration_onboarding.py`
