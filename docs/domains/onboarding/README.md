# Onboarding

Project bootstrap, documentation import, and architecture-aware initialization.

## Specification

### Modules

- **scanner.py** — `bootstrap_project()` scans source directories, classifies subdirectories using preset rules, infers edges from directory nesting, generates `.beadloom/_graph/services.yml` + `.beadloom/config.yml`. Also provides `import_docs()` for classifying existing .md files (ADR, feature, architecture, other).
- **presets.py** — Architecture presets (`monolith`, `microservices`, `monorepo`) with directory classification rules and edge inference logic.

### CLI Commands

```bash
beadloom init --bootstrap [--preset {monolith,microservices,monorepo}]
beadloom init --import DOCS_DIR
beadloom init  # interactive mode
```

## API

Module `src/beadloom/onboarding/scanner.py`:
- `bootstrap_project(root, preset=None)` — auto-generate graph from code structure
- `import_docs(root, docs_dir)` — classify and import existing documentation

Module `src/beadloom/onboarding/presets.py`:
- `get_preset(name)` — get preset configuration
- `detect_preset(root)` — auto-detect architecture from directory structure

## Testing

Tests: `tests/test_onboarding.py`, `tests/test_presets.py`, `tests/test_cli_init.py`
