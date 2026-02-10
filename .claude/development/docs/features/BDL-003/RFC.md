# RFC-0003: Phase 2 — Lower the Barrier

> **Status:** Accepted (implemented in v0.4.0)
> **Date:** 2026-02-10
> **Phase:** 2 (Strategy v0.4)
> **Depends on:** BDL-002 (v0.3.0 — agent-native pivot complete)

---

## 1. Summary

Phase 2 goal: **From `pip install` to useful context in under 5 minutes, on any project.**

Currently `beadloom init --bootstrap` generates a flat list of `kind: "service"` nodes from top-level subdirectories. No edges, no domain inference, no architecture awareness. This is a starting point — Phase 2 makes it smart.

Deliverables:

| # | Item | Effort | Priority |
|---|------|--------|----------|
| 2.1 | Architecture presets (`--preset`) | M | P1 |
| 2.2 | Smarter bootstrap (pattern detection, edge inference) | M | P1 |
| 2.3 | Zero-doc mode | S | P1 |
| 2.4 | Interactive bootstrap review | M | P2 |

## 2. Motivation

### 2.1 Problem: Bootstrap produces dumb output

`_cluster_by_dirs()` scans `src/*/` and creates one `kind: "service"` node per subdirectory. No edges. No domains. A project with `src/auth/`, `src/billing/`, `src/models/` gets three "service" nodes — but `models` is not a service, and there's no relationship between auth and billing.

Users must manually reclassify nodes and add edges before Beadloom becomes useful. This defeats the "5 minutes to value" promise.

### 2.2 Problem: No architecture awareness

A monolith has domains and features. Microservices have independent service boundaries. Monorepos have packages with explicit dependency manifests. The bootstrap should know the difference.

### 2.3 Problem: Docs are optional but UX doesn't say so

`reindex()` already handles missing docs gracefully. But the CLI never says "it's fine to use Beadloom without docs." Users who don't have a `docs/` directory may think Beadloom isn't for them.

### 2.4 Problem: No review before commit

Bootstrap writes YAML files directly. The user has no chance to review or correct the generated graph before running `reindex`. An interactive review step builds trust and catches mistakes.

## 3. Design

### 3.1 Architecture Presets

New module: `src/beadloom/presets.py`

```python
@dataclass
class PresetRule:
    """Maps directory name patterns to node kinds."""
    pattern: re.Pattern[str]
    kind: str  # domain, feature, service, entity
    confidence: str  # high, medium, low

@dataclass
class Preset:
    """Architecture preset defining node/edge generation rules."""
    name: str
    description: str
    dir_rules: list[PresetRule]  # how dirs map to node kinds
    default_kind: str  # fallback kind for unmatched dirs
    infer_part_of: bool  # generate part_of edges from nesting
    infer_deps_from_manifests: bool  # parse manifests for depends_on
```

**Three presets:**

| Preset | `default_kind` | Key rules |
|--------|----------------|-----------|
| `monolith` | `domain` | Top dirs → domains; `models/`,`entities/` → entity; `api/`,`routes/` → feature; `services/` → service; part_of edges from nesting |
| `microservices` | `service` | Top dirs → services; `shared/`,`lib/` → domain; subdirs → features; part_of edges |
| `monorepo` | `service` | `packages/`/`apps/` top dirs → services; shared packages → domain; manifest deps → depends_on edges |

**CLI integration:**

```bash
beadloom init --bootstrap --preset monolith
beadloom init --bootstrap --preset microservices
beadloom init --bootstrap --preset monorepo
beadloom init --bootstrap  # auto-detect or default to monolith
```

`--preset` added to both `init` command and `bootstrap_project()` function signature.

**Auto-detection heuristic** (when no preset specified):
- If `services/` or `cmd/` dir exists → microservices
- If `packages/` or `apps/` dir exists → monorepo
- Otherwise → monolith

### 3.2 Smarter Bootstrap

Extend `bootstrap_project()` to use preset rules:

1. **Multi-level scanning**: Scan 2 levels deep (not just `src/*/`)
2. **Pattern-based classification**: Dir name patterns → node kind (via preset rules)
3. **Edge inference**:
   - `part_of` edges: nested dirs are part_of parent dirs
   - `depends_on` edges: from manifest analysis (monorepo only)
4. **Confidence levels**: high (strong pattern match), medium (default), low (fallback)

**Directory pattern → kind mapping (monolith example):**

| Pattern | Kind | Confidence |
|---------|------|------------|
| `models`, `entities`, `schemas` | entity | high |
| `api`, `routes`, `controllers`, `handlers`, `views` | feature | high |
| `services`, `core`, `engine` | service | high |
| `utils`, `common`, `shared`, `helpers`, `lib` | service | medium |
| Everything else | domain (monolith) / service (micro) | medium |

### 3.3 Zero-Doc Mode

Minimal changes:

1. **Config schema**: Add optional `docs_dir: null` to `config.yml` when no docs found
2. **Interactive init**: When no `docs/` found, display message:
   ```
   No docs/ directory found — that's fine!
   Beadloom works great with code-only: graph nodes, annotations, context oracle.
   Add docs later when you need doc-sync tracking.
   ```
3. **Bootstrap output**: Distinguish "0 docs indexed" vs "docs disabled"
4. **AGENTS.md template**: Conditional section — skip doc-sync instructions when zero-doc

### 3.4 Interactive Bootstrap Review

After `bootstrap_project()` generates graph, show it before writing:

1. **Rich table** with generated nodes (ref_id, kind, source, confidence)
2. **Edge list** if any edges were inferred
3. **Summary line**: "Generated X nodes, Y edges from Z source files"
4. **Confirmation prompt**: `Proceed? [Y/n/edit]`
   - `Y` (default): write YAML and continue
   - `n`: cancel
   - `edit`: print path to YAML, exit for manual editing

This applies only to `interactive_init()` flow. `--bootstrap` flag skips review (non-interactive).

## 4. Implementation Plan

### 4.1 File Changes

| File | Change |
|------|--------|
| `src/beadloom/presets.py` | NEW — preset definitions and auto-detection |
| `src/beadloom/onboarding.py` | Extend `bootstrap_project()` with preset param, multi-level scan, edge inference, review |
| `src/beadloom/cli.py` | Add `--preset` flag to `init` command |
| `tests/test_presets.py` | NEW — preset logic tests |
| `tests/test_onboarding.py` | Extend with preset, zero-doc, review tests |

### 4.2 Execution Order

| # | Bead | Depends on | Status |
|---|------|------------|--------|
| 2.3 | Zero-doc mode | — | TODO |
| 2.1 | Architecture presets | — | TODO |
| 2.2 | Smarter bootstrap | 2.1 | TODO |
| 2.4 | Interactive review | 2.1, 2.2 | TODO |

### 4.3 What Stays Unchanged

- DB schema (`db.py`) — node kinds already support domain/feature/service/entity/adr
- Graph loader (`graph_loader.py`) — reads whatever YAML we generate
- Reindex pipeline (`reindex.py`) — unchanged
- MCP tools — unchanged
- Doc sync engine — unchanged

## 5. Success Criteria

- [ ] `beadloom init --bootstrap --preset monolith` generates domain/feature/entity nodes with edges
- [ ] `beadloom init --bootstrap --preset microservices` generates service nodes with part_of edges
- [ ] `beadloom init --bootstrap --preset monorepo` reads manifests for depends_on edges
- [ ] `beadloom init --bootstrap` without `--preset` auto-detects architecture
- [ ] Zero-doc projects bootstrap without errors or misleading messages
- [ ] Interactive init shows node/edge preview before writing YAML
- [ ] All tests pass (`uv run pytest`)
- [ ] `mypy --strict` passes
- [ ] `ruff check` passes

## 6. Non-Goals

- No import-level dependency analysis (tree-sitter import parsing — Phase 5 scope)
- No new DB schema changes
- No new MCP tools
- No changes to doc sync engine
- No TUI or graph visualization beyond simple Rich table
