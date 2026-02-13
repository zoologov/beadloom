# PLAN: BDL-011 — Plug & Play Onboarding

> **Last updated:** 2026-02-13
> **Beads:** 11
> **Waves:** 5

---

## DAG

```
Wave 1 (Foundation):
  BEAD-01 (root node + project name detection)
    ↓
  BEAD-02 (auto-rules generation)     [depends on BEAD-01]
  BEAD-03 (auto MCP config)           [independent]

Wave 2 (Doc generation):
  BEAD-04 (generate_skeletons)        [depends on BEAD-01]
    ↓
  BEAD-05 (generate_polish_data)      [depends on BEAD-04]

Wave 3 (CLI + MCP):
  BEAD-06 (docs generate + polish CLI) [depends on BEAD-04, BEAD-05]
  BEAD-07 (generate_docs MCP tool)     [depends on BEAD-05]
  BEAD-08 (enhanced init output)       [depends on BEAD-01..03, BEAD-04]

Wave 4 (Tests):
  BEAD-09 (integration tests)          [depends on BEAD-06..08]

Wave 5 (Dogfooding):
  BEAD-10 (self-apply on Beadloom)     [depends on BEAD-09]
  BEAD-11 (graph + CHANGELOG + docs)   [depends on BEAD-10]
```

## Critical Path

```
BEAD-01 → BEAD-02
         → BEAD-04 → BEAD-05 → BEAD-06 → BEAD-09 → BEAD-10 → BEAD-11
```

## Bead Details

### BEAD-01: Root node + project name detection (P0)
- Add `_detect_project_name()` to `scanner.py`
- Create root node in `bootstrap_project()`
- Add `part_of` edges from top-level nodes to root
- Tests: pyproject.toml, package.json, go.mod, Cargo.toml, directory fallback
- **Files:** `scanner.py`, `tests/test_onboarding.py`

### BEAD-02: Auto-rules generation (P0)
- Add `generate_rules()` to `scanner.py`
- Call from `bootstrap_project()` (only if rules.yml doesn't exist)
- Rules: domain-needs-parent, feature-needs-domain, service-needs-parent
- Tests: various node kind combinations, idempotency, YAML validation
- **Depends on:** BEAD-01 (root node needed for rules)
- **Files:** `scanner.py`, `tests/test_onboarding.py`

### BEAD-03: Auto MCP config (P0)
- Add `setup_mcp_auto()` to `scanner.py`
- Editor detection: .cursor → cursor, .windsurfrules → windsurf, default → claude-code
- Call from `bootstrap_project()`
- Tests: editor detection, JSON structure, idempotency
- **Independent** (no deps in Wave 1)
- **Files:** `scanner.py`, `tests/test_onboarding.py`

### BEAD-04: Doc skeleton generation (P0)
- Create `onboarding/doc_generator.py`
- Implement `generate_skeletons(project_root, nodes, edges)`
- Generate: architecture.md, domains/*/README.md, services/*.md
- Include: Mermaid diagram, edge lists, source paths
- Update `onboarding/__init__.py` re-exports
- Tests: file creation, markdown structure, idempotency
- **Depends on:** BEAD-01 (root node in graph)
- **Files:** `onboarding/doc_generator.py`, `onboarding/__init__.py`, `tests/test_doc_generator.py`

### BEAD-05: Polish data generation (P1)
- Add `generate_polish_data()` to `doc_generator.py`
- Read symbols from SQLite (post-reindex) or inline tree-sitter
- Return structured JSON: nodes with symbols/deps, architecture summary, prompt
- Tests: JSON structure, single-node mode, all-nodes mode
- **Depends on:** BEAD-04 (shared module)
- **Files:** `onboarding/doc_generator.py`, `tests/test_doc_generator.py`

### BEAD-06: CLI commands — docs generate + docs polish (P1)
- Add `docs` Click group to `cli.py`
- Add `docs generate` subcommand
- Add `docs polish` subcommand with --format json/text
- Tests: CLI invocation, output format
- **Depends on:** BEAD-04, BEAD-05
- **Files:** `services/cli.py`, `tests/test_cli_docs.py`

### BEAD-07: MCP tool — generate_docs (P1)
- Add `generate_docs` tool definition to `_TOOLS` list
- Add handler in `call_tool()` dispatcher
- Return `generate_polish_data()` as MCP TextContent
- Tests: MCP tool invocation, response format
- **Depends on:** BEAD-05
- **Files:** `services/mcp_server.py`, `tests/test_mcp.py`

### BEAD-08: Enhanced init output (P2)
- Update `init` command in `cli.py` to print ✓ summary
- Show: graph stats, rules count, docs count, MCP editor, index stats
- Show "Next steps" with actionable commands
- Tests: CLI output contains expected lines
- **Depends on:** BEAD-01, BEAD-02, BEAD-03, BEAD-04
- **Files:** `services/cli.py`, `scanner.py`

### BEAD-09: Integration tests (P1)
- Test full `init --bootstrap` on tmp project → rules + docs + MCP created
- Test `beadloom lint` after init → rules evaluated, 0 violations
- Test `beadloom ctx <node>` after init → doc chunks present
- Test `beadloom docs generate` → files created
- Test `beadloom docs polish --format json` → valid JSON
- Test idempotency: re-run init → no files overwritten
- **Depends on:** BEAD-06, BEAD-07, BEAD-08
- **Files:** `tests/test_integration_onboarding.py`

### BEAD-10: Dogfooding — self-apply on Beadloom (P0)
- Run `beadloom docs generate` on own project (expect skips)
- Compare auto-rules with hand-written rules.yml
- Run `beadloom docs polish --format json` and validate richness
- Test `generate_docs` MCP tool
- Run full pipeline: reindex → doctor → lint → ctx
- **Depends on:** BEAD-09
- **Files:** project-wide validation

### BEAD-11: Graph + CHANGELOG + docs update (P1)
- Add `doc-generator` feature node to services.yml
- Update CLI node summary: 20 commands
- Update MCP node summary: 9 tools
- Add new feature docs: SPEC.md for doc-generator
- Update: onboarding README, cli.md, mcp.md
- CHANGELOG entry, version bump if needed
- **Depends on:** BEAD-10
- **Files:** `.beadloom/`, `docs/`, `CHANGELOG.md`
