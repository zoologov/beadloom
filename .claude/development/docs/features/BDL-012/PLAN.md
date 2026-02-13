# BDL-012 PLAN — Bead Decomposition

## DAG

```
BEAD-01 (#5 doctor coverage)  ──┐
BEAD-02 (#6 lint rules)        ──┼──→ BEAD-07 (integration + dogfood)
BEAD-03 (#7+#8 polish)         ──┤
BEAD-04 (#14 preset detect)    ──┤
BEAD-05 (#11 parser warning)   ──┤
BEAD-06 (#9,#10,#12,#13 misc)  ──┘
```

## Beads

### BEAD-01: Fix doctor 0% coverage — write `docs:` back to YAML (P0)
- **Issue:** #5
- **Files:** `onboarding/doc_generator.py`
- **Task:** `generate_skeletons()` writes `docs:` field to services.yml after creating files
- **Test:** Bootstrap temp project → services.yml has `docs:` → reindex → doctor 0 warnings
- **Blocks:** BEAD-07

### BEAD-02: Fix lint false positives — empty matcher + rule generation (P0)
- **Issue:** #6
- **Files:** `graph/rule_engine.py`, `onboarding/scanner.py`
- **Task:** Allow empty `has_edge_to: {}` in rule engine. Change `generate_rules()` to use `{}` instead of `{ref_id: root}`.
- **Test:** Hierarchical graph → lint → 0 violations. Empty matcher matches any node.
- **Blocks:** BEAD-07

### BEAD-03: Fix polish — SQLite edges + text format (P1)
- **Issue:** #7, #8
- **Files:** `onboarding/doc_generator.py`, `services/cli.py`
- **Task:** `generate_polish_data()` reads edges from SQLite. New `_format_polish_text()` for rich text output.
- **Test:** Polish JSON has real deps. Polish text > 10 lines with node details.
- **Blocks:** BEAD-07

### BEAD-04: Fix preset auto-detect for mobile apps (P1)
- **Issue:** #14
- **Files:** `onboarding/presets.py`
- **Task:** Add mobile detection (app.json/expo/react-native) before services/cmd check.
- **Test:** Temp project with app.json + expo in package.json + services/ → monolith.
- **Blocks:** BEAD-07

### BEAD-05: Warn about missing language parsers (P1)
- **Issue:** #11
- **Files:** `context_oracle/code_indexer.py`, `services/cli.py`
- **Task:** `check_parser_availability(extensions)` → warning in CLI when parsers missing.
- **Test:** Mock get_lang_config → None for .ts → warning printed.
- **Blocks:** BEAD-07

### BEAD-06: Misc fixes — summaries, ref_ids, reindex, counts (P2)
- **Issue:** #9, #10, #12, #13
- **Files:** `onboarding/scanner.py`, `infrastructure/reindex.py`, `services/cli.py`
- **Task:**
  - #9: Detect Django/React patterns in summaries
  - #10: Strip parens from ref_ids
  - #12: Track parser fingerprint in reindex
  - #13: Show created vs skipped count
- **Test:** Each sub-issue gets a unit test.
- **Blocks:** BEAD-07

### BEAD-07: Integration test + dogfood on cdeep & dreamteam (P0)
- **Issue:** All
- **Files:** `tests/test_integration_onboarding.py`, CHANGELOG, UX-Issues
- **Task:** Run `beadloom init --bootstrap` on cdeep and dreamteam. Verify doctor 0, lint 0, symbols > 0, preset correct. Update CHANGELOG, close UX issues.
- **Blocked by:** BEAD-01..06

## Waves

| Wave | Beads | Parallel? |
|------|-------|-----------|
| 1 | BEAD-01, BEAD-02, BEAD-04 | Yes — independent packages |
| 2 | BEAD-03, BEAD-05, BEAD-06 | Yes — independent packages |
| 3 | BEAD-07 | No — integration |

## Critical Path

BEAD-01 + BEAD-02 → BEAD-07 (HIGH severity fixes must land first)
