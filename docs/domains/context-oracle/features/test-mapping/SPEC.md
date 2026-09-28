# Test Mapping

Test-to-node binding for the context-oracle domain: which graph node a test file
belongs to, derived from where the file lives.

**Source:** `src/beadloom/context_oracle/test_binding.py`,
`src/beadloom/context_oracle/test_file_reader.py`

---

## Specification

### Purpose

Bind each test file to the graph node whose code it tests, so the graph and the
context bundles can report which nodes have tests and name them. Since BDL-074 C1
the binding is derived from the test file's path. The name-guessing heuristic it
replaced (`test_mapper.py`) was deleted in BDL-074 C2, once its last caller, the
debt report, read the binding instead.

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

### Readers of the binding

- **`ctx`.** The context bundle carries the focus node's `extra["tests"]` under
  `tests` and, since BDL-074 C2, the project's test files by placement under
  `test_placements` (`{placement: count}`, read by
  `infrastructure.repository.count_test_files_by_placement`; `{}` for an index
  older than the test tables). When any file is unplaced, the Markdown output adds
  one line under `Tests:` built from `describe_unplaced()`:
  `U of N test file(s) are unplaced (not under tests/integration/ or tests/unit/)
  and bind to no node, so the count above can be short`.
- **Debt report.** `_count_untested()` in `application/debt_report/collect.py`
  counts a node as untested when it carries `extra["tests"]` with an empty
  `test_files`. While any test file is unplaced the count is withheld (0), and the
  report's `test_population` says why, in the same `describe_unplaced()` sentence.
  See the [debt report](../../../application/features/debt-report/SPEC.md).
- **Lint.** Since BDL-074 C3 the rule engine judges the binding: `test_binding` reports a
  test file bound to no node and a node with no bound test file, and
  `test_import_boundary` narrows an import boundary to the tests of matching nodes. Both
  read `test_files` and `test_imports`, and `test_binding` counts placement `other_kind`
  as bound by other means rather than judging it. See the
  [rule-engine SPEC](../../../graph/features/rule-engine/SPEC.md).

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
  `PLACEMENT_UNPLACED`, `PLACEMENT_OTHER_KIND` — the placement values. Defined in
  `infrastructure/repository.py` since BDL-074 C3 and re-exported here under the same
  names, so an import from this module still answers. The vocabulary sits below both of
  its readers: this module assigns a placement and the rule engine's `test_binding` judges
  it, and a vocabulary two peer domains share belongs below both rather than in the one that
  wrote it down first.
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
- `describe_unplaced(counts: Mapping[str, int]) -> str | None` — the sentence that
  says how many test files are unplaced and bind to no node; `None` when none is.
  `ctx` and the debt report both print it.

Module `src/beadloom/context_oracle/test_file_reader.py`:

- `TestFileContents` — frozen dataclass: `test_count`, `imports`.
- `read_test_file(text: str) -> TestFileContents`.
- `count_test_functions(text: str) -> int`.

Module `src/beadloom/infrastructure/repository.py`:

- `PLACEMENT_MIRROR` (`"mirror"`), `PLACEMENT_OVERRIDE` (`"override"`),
  `PLACEMENT_UNOWNED` (`"unowned"`), `PLACEMENT_UNPLACED` (`"unplaced"`),
  `PLACEMENT_OTHER_KIND` (`"other_kind"`) — where the placement values are defined.
- `count_test_files_by_placement(conn) -> dict[str, int]` — indexed test files per
  placement; `{}` when the `test_files` table does not exist.

## Testing

Tests: `tests/test_a_test_file_binds_to_the_node_its_path_mirrors.py` (binding and
reader), `tests/test_reindex_indexes_test_files_in_their_own_tables.py` (the
tables and `extra["tests"]`), `tests/test_reindex_tests.py`,
`tests/test_ctx_and_debt_report_read_the_test_binding.py` (the `ctx` line and the
debt report's count), and the acceptance scenarios in
`tests/acceptance/features/test_files_bind_to_the_node_their_path_mirrors.feature` and
`tests/acceptance/features/ctx_and_debt_report_read_the_test_binding.feature`.
