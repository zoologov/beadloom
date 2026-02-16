# BDL-012 RFC — Onboarding Quality Bug-fixes

> **Status:** Implemented (v1.3.1)
> **Epic:** BDL-012

## Overview

10 fixes across 4 packages (`onboarding`, `infrastructure`, `context_oracle`, `services`). No new commands, no new tables. Every fix is backward-compatible.

---

## Fix #5 (HIGH): `doctor` shows 0% coverage

**Root cause:** `generate_skeletons()` creates doc files but never writes `docs:` field back into `services.yml`. Without `docs:`, `_build_doc_ref_map()` in reindex returns empty map → docs table has `ref_id IS NULL` → doctor reports "unlinked".

**Solution:** After creating skeleton files, update each node in `services.yml` with `docs: [relative_path]`.

**Files:**
- `onboarding/doc_generator.py` — `generate_skeletons()`: after `_write_if_missing()`, collect `{ref_id: rel_path}` mapping, then call new `_patch_docs_field()` to update YAML
- `onboarding/doc_generator.py` — new `_patch_docs_field(graph_dir, docs_map)`: reads `services.yml`, adds `docs:` to matching nodes, writes back

**Constraints:**
- Must preserve YAML comments and ordering (use round-trip or re-dump with `yaml.dump`)
- Only add `docs:` for newly created files, don't overwrite existing `docs:` values
- The `docs:` value is a list: `["docs/domains/auth/README.md"]`

**Test:** Bootstrap a temp project → assert nodes in services.yml have `docs:` field → reindex → doctor shows 0 warnings.

---

## Fix #6 (HIGH): `lint` false positives on nested domains

**Root cause:** `generate_rules()` generates `domain-needs-parent` with `has_edge_to: {ref_id: ROOT}`. Sub-domains have `part_of → parent_domain`, not `part_of → ROOT`. 25+ false positives on cdeep.

Also: `service-needs-parent` with `has_edge_to: {ref_id: ROOT}` catches the root node itself (root has kind=service but no `part_of` edge).

**Solution A — change generated rules (minimal):**
1. `domain-needs-parent`: change to `has_edge_to: {kind: domain}` OR `has_edge_to: {kind: service}` — this means "must be part_of any domain or service". But this needs OR-logic which NodeMatcher doesn't support.

**Solution B — rule engine enhancement + simpler rules (chosen):**
1. Add `NodeMatcher` support for empty matcher: `has_edge_to: {}` means "has at least one matching edge to ANY node". This is the `has_edge_to: any` semantic.
2. Change `domain-needs-parent` to: `has_edge_to: {}, edge_kind: part_of` — "every domain must have at least one `part_of` edge"
3. Change `service-needs-parent` to same: `has_edge_to: {}, edge_kind: part_of`
4. Skip root node in `for_matcher` by adding `exclude_ref_id` to `NodeMatcher`, OR detect root in `generate_rules()` and add `not_ref_id` field. Simpler: just exclude root in rule generation by not emitting `service-needs-parent` when only service is root.

**Chosen approach:**
- `NodeMatcher(ref_id=None, kind=None)` already matches ANY node (both checks pass when None). So `has_edge_to: {}` already works in `matches()`. The issue is in `_parse_require_rule()` validation — it may reject empty matcher. Fix: allow empty `has_edge_to` dict.
- `generate_rules()`: change both `domain-needs-parent` and `service-needs-parent` to use `has_edge_to: {}` with `edge_kind: part_of`
- Root exclusion: `generate_rules()` already filters root from service-needs-parent (line 451). For domain-needs-parent, root is never kind=domain so no issue.

**Files:**
- `graph/rule_engine.py` — `_parse_require_rule()`: allow empty `has_edge_to` dict (currently may require at least one field)
- `onboarding/scanner.py` — `generate_rules()`: change `has_edge_to` from `{ref_id: root}` to `{}` for rules 1 and 3

**Test:** Generate rules for hierarchical graph → lint → 0 violations for nested domains.

---

## Fix #7 (MEDIUM): Dependencies always empty in skeletons

**Root cause:** `generate_skeletons()` reads edges from YAML (`services.yml`), which only has `part_of` edges at bootstrap time. `depends_on` edges are created by import resolver during `reindex`. The `_edges_for()` function filters out `part_of`, leaving nothing.

**Solution:** After reindex completes, `generate_skeletons()` should also read edges from SQLite (`edges` table) and merge with YAML edges.

**Files:**
- `onboarding/doc_generator.py` — `_edges_for()`: add optional `conn` parameter to also query SQLite edges
- `onboarding/doc_generator.py` — `generate_skeletons()`: try to open SQLite DB (best-effort), pass conn to edge resolution
- `onboarding/doc_generator.py` — `generate_polish_data()`: already has conn from context, pass to `_edges_for()`

**Alternative (simpler, chosen):** `generate_skeletons()` is called during bootstrap BEFORE reindex. Deps won't exist yet. Instead, fix `generate_polish_data()` to read edges from SQLite (it runs POST-reindex). Skeletons stay with "(none)" — users run `docs polish` to get real deps. Add a note in skeleton: "Run `beadloom docs polish` after reindex to populate dependencies."

**Files:**
- `onboarding/doc_generator.py` — `generate_polish_data()`: query `edges` table from SQLite conn (already available), merge into node data

**Test:** Bootstrap → reindex → `docs polish --format json` → verify `depends_on` list is populated.

---

## Fix #8 (MEDIUM): `docs polish` text format = 1 line

**Root cause:** Text format only outputs `data["instructions"]` — a single AI prompt string. The `nodes` and `architecture` data are discarded.

**Solution:** Render a human-readable text report from polish data.

**Format:**
```
# Project: {name}
# Nodes needing enrichment: {count}

## {ref_id} ({kind})
   Source: {source}
   Summary: {summary}
   Depends on: X, Y, Z
   Used by: A, B
   Symbols: func1(), func2(), Class1
   Doc: {doc_path} ({status})

---
Instructions: {instructions}
```

**Files:**
- `onboarding/doc_generator.py` — new `_format_polish_text(data)` function
- `services/cli.py` — `docs_polish()`: use `_format_polish_text()` for text format instead of `data["instructions"]`

**Test:** `docs polish` without `--format json` → output > 10 lines, contains node names and symbols.

---

## Fix #14 (MEDIUM): Preset misclassifies mobile apps

**Root cause:** `detect_preset()` sees `services/` dir → returns MICROSERVICES. But in mobile apps (React Native, Flutter), `services/` contains internal API modules, not independent services.

**Solution:** Add mobile app detection before the `services/cmd` check.

**Heuristic:**
```python
# Mobile indicators — single-app projects
if (project_root / "app.json").exists():  # React Native / Expo
    return MONOLITH
if (project_root / "pubspec.yaml").exists():  # Flutter
    return MONOLITH
# Also check package.json for react-native/expo deps
pkg_json = project_root / "package.json"
if pkg_json.exists():
    content = json.loads(pkg_json.read_text())
    deps = {**content.get("dependencies", {}), **content.get("devDependencies", {})}
    if "react-native" in deps or "expo" in deps:
        return MONOLITH
```

**Files:**
- `onboarding/presets.py` — `detect_preset()`: add mobile checks before `services/cmd` check

**Test:** Create temp project with `app.json` + `services/` → preset = monolith.

---

## Fix #11 (MEDIUM): Missing language parsers warning

**Root cause:** `uv tool install beadloom` doesn't include tree-sitter grammars (optional deps). Bootstrap outputs "0 symbols" with no explanation.

**Solution:** Detect when configured languages have no available parser and warn.

**Files:**
- `context_oracle/code_indexer.py` — new `check_parser_availability(extensions)` → returns `{ext: bool}` dict
- `onboarding/scanner.py` or `services/cli.py` — after bootstrap, if symbols == 0 and languages configured, call `check_parser_availability()` and print warning:
  ```
  ⚠ No parser available for .ts, .tsx files.
  Install language support: uv tool install "beadloom[languages]"
  ```

**Test:** Mock `get_lang_config()` to return None for `.ts` → verify warning printed.

---

## Fix #9 (LOW): Generic summaries

**Root cause:** Summaries are just "Domain: X (N files)" — repeat the dir name.

**Solution:** Detect framework patterns and include top symbols in summary.

**Heuristic in `_generate_summary()`:**
- Check for framework markers: `apps.py` → Django app, `index.tsx` → React component, `__init__.py` + `setup.py` → Python package
- Include top 3 public class/function names from symbols
- Format: "Django app managing user accounts (User, UserManager, authenticate)"

**Files:**
- `onboarding/scanner.py` — `_generate_summary()` (or wherever summaries are created): enhance with pattern detection and symbols

**Constraint:** Summary must stay under 120 chars. Symbols are best-effort (may not be available at bootstrap time).

**Test:** Dir with `apps.py` + `models.py` → summary mentions "Django app".

---

## Fix #10 (LOW): Parenthesized ref_ids

**Root cause:** Expo router uses `(tabs)` as directory name. `ref_id` becomes `(tabs)`, doc path becomes `services/(tabs).md`.

**Solution:** Sanitize ref_ids by stripping parentheses in scanner.

**Files:**
- `onboarding/scanner.py` — `_dir_to_ref_id()` or wherever ref_id is created: strip `()` → `tabs`

**Constraint:** Must not break existing graphs. Apply only at generation time, not retroactively.

**Test:** Dir named `(tabs)` → ref_id = `tabs`, doc = `services/tabs.md`.

---

## Fix #12 (LOW): `reindex` ignores new parser availability

**Root cause:** Incremental reindex checks file hashes, not parser availability. After installing tree-sitter-typescript, hashes haven't changed → "No changes detected".

**Solution:** Track available parsers as part of the file index state. When parser set changes, trigger full code reindex.

**Files:**
- `infrastructure/reindex.py` — `incremental_reindex()`: before diffing files, compare current `supported_extensions()` with stored set. If different → full code reindex.
- `infrastructure/reindex.py` — store parser fingerprint in a metadata row in `file_index` or a separate `meta` table key.

**Test:** Mock `supported_extensions()` to return different set → verify full reindex triggered.

---

## Fix #13 (INFO): Skeleton count includes pre-existing files

**Root cause:** `generate_skeletons()` returns `files_created` but CLI just prints the number. Pre-existing files are counted as `files_skipped` but not shown.

**Solution:** Print both counts in CLI output.

**Files:**
- `services/cli.py` — bootstrap command: change output from `"{created} skeletons"` to `"{created} skeletons created, {skipped} skipped (pre-existing)"`

**Test:** Bootstrap with pre-existing `architecture.md` → output shows "skipped" count > 0.

---

## Architecture

No new packages, tables, or commands. All changes are within existing modules:

```
onboarding/
  doc_generator.py  — #5 (docs: writeback), #7 (SQLite edges), #8 (text format)
  scanner.py        — #6 (rules), #9 (summaries), #10 (ref_id sanitize)
  presets.py        — #14 (mobile detect)
graph/
  rule_engine.py    — #6 (allow empty matcher)
context_oracle/
  code_indexer.py   — #11 (parser check)
infrastructure/
  reindex.py        — #12 (parser fingerprint)
services/
  cli.py            — #8 (text format), #11 (warning), #13 (count display)
```

## Risks

1. **YAML round-trip** (#5): `yaml.dump()` may reorder keys. Mitigate: use `sort_keys=False`.
2. **Empty matcher semantics** (#6): `NodeMatcher()` matching everything is by design but verify no rule relies on "match nothing" for empty.
3. **SQLite lock** (#7): `generate_polish_data()` opening DB is fine — it's read-only, WAL mode.
4. **Mobile heuristic** (#14): `app.json` exists in non-mobile projects. Mitigate: check for `expo` or `react-native` keys inside, not just file existence.
