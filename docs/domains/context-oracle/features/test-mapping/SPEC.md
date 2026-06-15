# Test Mapping

Test-to-source mapping for the context-oracle domain.

**Source:** `src/beadloom/context_oracle/test_mapper.py`

---

## Specification

### Purpose

Detect the test framework(s) a project uses and map test files to the source
nodes they exercise, so the graph and context bundles can report which nodes
have test coverage and surface the tests relevant to a given node.

### How it works

`map_tests(project_root, source_dirs)` runs in stages: it detects the
frameworks present (pytest, jest, go_test, junit, xctest), collects the test
files for each, counts the test functions in each file by framework-specific
patterns, and associates each test file with source nodes by import analysis and
name/path proximity. The result is a `TestMapping` per source node carrying the
framework, the relevant test files, the test count, and a coarse coverage
estimate (`high` / `medium` / `low` / `none`).

`aggregate_parent_tests(mappings, parent_children)` rolls child test counts up
to parent nodes that have no direct tests of their own — typically following the
`part_of` edges — so a domain node reflects the coverage of its features.

## Invariants

- Mapping is heuristic (import analysis plus name/path proximity and framework
  conventions); it is best-effort, not exhaustive.
- A project with no detectable tests yields empty mappings rather than an
  error — test mapping never fails the index.
- Parent aggregation only fills in parents that have no direct test files of
  their own.

## API

Module `src/beadloom/context_oracle/test_mapper.py`:

- `TestMapping` — dataclass: `framework`, `test_files`, `test_count`,
  `coverage_estimate`.
- `map_tests(project_root: Path, source_dirs: dict[str, str]) -> dict[str, TestMapping]`
  — map test files to source nodes, keyed by `ref_id`.
- `aggregate_parent_tests(mappings, parent_children) -> dict[str, TestMapping]`
  — sum child coverage onto childless parents.

## Testing

Tests: `tests/test_test_mapper.py`
