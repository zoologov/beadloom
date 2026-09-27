# Test Mapping

Test-to-node binding for the context-oracle domain: which graph node a test file
belongs to, derived from where the file lives.

**Source:** `src/beadloom/context_oracle/test_binding.py`,
`src/beadloom/context_oracle/test_file_reader.py`,
`src/beadloom/context_oracle/test_mapper.py`

---

## Specification

### Purpose

Bind each test file to the graph node whose code it tests, so the graph and the
context bundles can report which nodes have tests and name them. Since BDL-074 C1
the binding is derived from the test file's path. The earlier name-guessing
heuristic (`test_mapper`) no longer writes `nodes.extra["tests"]`.

### The binding rule

`bind_test_file(path, *, code_files, scan_paths, node_sources, overrides)` returns
a `BoundTestFile` (`path`, `kind`, `ref_id`, `placement`). It applies three steps
in order:

1. **Declaration.** A node may list path prefixes under an optional `tests:` key in
   its graph YAML. The prefixes are resolved like `source:` — a trailing `/` is a
   directory, anything else is one file — and the most specific prefix covering
   the test file wins. A declaration wins over the mirror. Placement: `override`.
2. **Kind folder.** The segment after `tests/` is the kind. `unit` and
   `integration` are mirrored kinds (`MIRRORED_KINDS`). `acceptance` and
   `self_check` are laid out by folder but are not bound here (`OTHER_KINDS`):
   acceptance scenarios bind by their `@node:` tag
   ([scenario binding](../../../graph/features/scenario-binding/SPEC.md)).
   A file outside every kind folder is `unplaced`. A file under an other kind is
   `other_kind`.
3. **Mirror.** For a mirrored kind, `mirrored_code_path()` turns the path beneath
   the kind folder into a code path. `tests/unit/<path>/test_<name>.py` names
   `<root><path>/<name>.py`, and `<name>_test.py` names the same module. When
   `<root><path>/` holds no code but the module `<root><path>.py` exists, the
   folder names that module, so `tests/unit/<path>/<module>/test_*.py` binds to
   `<module>.py`. The roots are each scan path and each package directly beneath
   one. When several roots resolve, the deepest wins; two equally deep roots
   resolve to nothing. The node that owns the mirrored code path — the most
   specific covering `source`, by `infrastructure.repository.most_specific_owner`
   — is the node. Placement: `mirror`, or `unowned` when no node owns that path.

A file-source node is reached only when the test file is named for its module or
sits in a folder named for it. Otherwise the enclosing directory node owns the
mirrored path.

### Placements

| Placement | Bound to a node | Meaning |
|-----------|-----------------|---------|
| `mirror` | yes | The mirrored code path is owned by a node |
| `override` | yes | A node's `tests:` declaration covers the file |
| `unowned` | no | Under `unit`/`integration`, and no node owns the mirrored code path |
| `unplaced` | no | Not under a kind folder: the layout has not reached the file |
| `other_kind` | no | Under `acceptance` or `self_check`, which bind by other means |

### What a test file holds

`read_test_file(text)` parses the file once with `ast` and returns
`TestFileContents(test_count, imports)`:

- `test_count` counts the functions a file defines: module-level `test*`
  functions and `test*` methods of `Test*` classes, sync or async. A parametrised
  function counts once.
- `imports` are `(line, module)` pairs in the code index's form: `import a.b`
  records `a.b`, `from a.b import c` records `a.b`, a relative import records
  nothing. Unlike the tree-sitter code-import extractor, `import a.b as c` is
  recorded.
- Text that does not parse holds nothing (`test_count=0`, no imports).

Measured on this repository's 462 test files: the tree-sitter import extractor
took 2.2 s for the imports alone, and the whole cold indexing step built on this
reader took 0.87 s (darwin, Python 3.13).

### `extra["tests"]`

The reindex step that walks `tests/` and stores the binding lives in the
[reindex feature](../../../application/features/reindex/SPEC.md)
(`application/reindex/test_index.py`). It rebuilds `nodes.extra["tests"]` from
the binding for every node that has a `source` or a `tests:` declaration, in the
four-key shape its readers expect:

- `framework` — `pytest` when any test file exists under `tests/`, else `none`.
- `test_files` — the node's own bound files united with every `part_of`
  descendant's (`union_over_descendants`). The union counts a file reached
  through two children once.
- `test_count` — the sum of `test_count` over those files.
- `coverage_estimate` — `estimate_coverage()`: more than 3 files `high`, 1-3
  `medium`, 0 with a framework `low`, 0 without one `none`. These thresholds are
  the heuristic's, unchanged.

### The transition

Most of this repository's tests are not laid out under `tests/unit/` or
`tests/integration/` yet, so they bind to nothing. Measured on this repository's
index (2026-09-27): 462 test files, 0 bound to a node, 392 `unplaced`, 70
`other_kind`. Every node therefore reads 0 test files until the files are
relocated. The heuristic gave the root node 882 files and bound 532 mutmut copies
under `mutants/` to nodes.

A node with 0 bound tests is distinguishable from a repository whose tests are not
laid out: `beadloom reindex` prints the placement counts on its `Tests:` line, and
the `test_files` table records each file's placement.

### The heuristic that remains

`test_mapper.map_tests(project_root, source_dirs)` detects frameworks (pytest,
jest, go_test, junit, xctest), collects and counts test files, and maps them by
import analysis and name/path proximity. The reindex no longer calls it. Its one
remaining caller is the debt report's collector
(`application/debt_report/collect.py`), which reads `coverage_estimate` from it.
The project tree is walked once per call, with dependency, VCS, cache and build
directories pruned. `aggregate_parent_tests(mappings, parent_children)` rolls
child test counts onto childless parents; nothing in the reindex calls it.

## Invariants

- Nothing is guessed: a test file binds by a declaration or by the mirror of its
  path, and otherwise binds to nothing and records why (its placement).
- A declaration wins over the mirror.
- Ownership of a mirrored path or a declared prefix is decided by the same rule as
  code ownership (`most_specific_owner`): the longest covering prefix wins.
- Only `pytest`-named Python files (`test_*.py`, `*_test.py`) under `tests/` are
  bound. A non-Python project therefore reads `framework: none`, where the
  heuristic detected jest, go_test, junit or xctest.
- A parent's `test_files` is a union over its descendants, not a sum.
- The binding functions are pure: they take the paths they reason about, and the
  walk and the storage belong to the reindex.

## API

Module `src/beadloom/context_oracle/test_binding.py`:

- `TEST_ROOT` (`"tests"`), `MIRRORED_KINDS` (`unit`, `integration`),
  `OTHER_KINDS` (`acceptance`, `self_check`), `TEST_FILE_PATTERNS`.
- `PLACEMENT_MIRROR`, `PLACEMENT_OVERRIDE`, `PLACEMENT_UNOWNED`,
  `PLACEMENT_UNPLACED`, `PLACEMENT_OTHER_KIND` — the placement values.
- `FRAMEWORK_PYTEST`, `FRAMEWORK_NONE`.
- `BoundTestFile` — frozen dataclass: `path`, `kind`, `ref_id`, `placement`.
- `is_test_file(name: str) -> bool` — whether pytest collects a file of that name
  by default.
- `bind_test_file(path, *, code_files, scan_paths, node_sources, overrides) -> BoundTestFile`
  — bind one test file.
- `mirrored_code_path(under_kind, *, code_files, scan_paths) -> str | None` — the
  code path a path beneath a kind folder names.
- `union_over_descendants(direct, parent_children) -> dict[str, frozenset[str]]`
  — each node's files united with its descendants'.
- `estimate_coverage(file_count, *, framework_detected) -> str`.
- `summarize_tests(files, counts, *, framework) -> dict[str, object]` — one node's
  `extra["tests"]` in the four-key shape.

Module `src/beadloom/context_oracle/test_file_reader.py`:

- `TestFileContents` — frozen dataclass: `test_count`, `imports`.
- `read_test_file(text: str) -> TestFileContents`.
- `count_test_functions(text: str) -> int`.

Module `src/beadloom/context_oracle/test_mapper.py` (debt report only):

- `TestMapping` — dataclass: `framework`, `test_files`, `test_count`,
  `coverage_estimate`.
- `map_tests(project_root: Path, source_dirs: dict[str, str]) -> dict[str, TestMapping]`.
- `aggregate_parent_tests(mappings, parent_children) -> dict[str, TestMapping]`.

## Testing

Tests: `tests/test_a_test_file_binds_to_the_node_its_path_mirrors.py` (binding and
reader), `tests/test_reindex_indexes_test_files_in_their_own_tables.py` (the
tables and `extra["tests"]`), `tests/test_reindex_tests.py`,
`tests/test_test_mapper.py` (the heuristic), and the acceptance scenarios in
`tests/acceptance/features/test_files_bind_to_the_node_their_path_mirrors.feature`.
