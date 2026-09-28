# Test Mapping

Test-to-node binding for the context-oracle domain: which graph node a test file
belongs to, derived from where the file lives.

**Source:** `src/beadloom/context_oracle/test_binding.py`,
`src/beadloom/context_oracle/test_file_reader.py`,
`src/beadloom/context_oracle/test_layout.py`

---

## Specification

### Purpose

Bind each test file to the graph node whose code it tests, so the graph and the
context bundles can report which nodes have tests and name them. Since BDL-074 C1
the binding is derived from the test file's path. The name-guessing heuristic it
replaced (`test_mapper.py`) was deleted in BDL-074 C2, once its last caller, the
debt report, read the binding instead.

A test binds in one of three ways, and never by a guess at its name: by the
**mirror** of its path under a test root or a build tool's test tree, by its place
**beside the code** inside a node's source, or by a node's **`tests:`** declaration.
A file none of the three reaches binds to nothing and records why.

### Configuration: the test layout

Where a project keeps its tests and which files are tests is its test layout
(`test_layout.TestLayout`, BDL-074 G2 and `beadloom-2mj3.13`), read from an optional
`tests:` block in `.beadloom/config.yml`. Every key has a default, so a project that
declares nothing is read by the defaults below.

| Key | Default | A declared value |
|-----|---------|------------------|
| `roots` | `[tests]` | replaces the list |
| `kinds` | each kind in the folder of its own name: `unit`, `integration`, `acceptance`, `self_check` | replaces the folder of that one kind |
| `patterns` | the five framework groups below | replaces all five groups |
| `mirrors` | `src/test/java: src/main/java`, `src/test/kotlin: src/main/kotlin`, `Tests: Sources` | replaces all three trees |
| `beside_code` | `true` | `true` or `false` |

The default `patterns`, each group named for the framework its files belong to:

| Language | Group | Default file-name patterns |
|----------|-------|----------------------------|
| Python | `pytest` | `test_*.py`, `*_test.py` |
| Go | `go_test` | `*_test.go` |
| JavaScript, TypeScript | `jest` | `*.test.*`, `*.spec.*` |
| Java, Kotlin | `junit` | `*Test.java`, `*Tests.java`, `*TestCase.java`, `*IT.java`, `*ITCase.java`, `*Test.kt`, `*Tests.kt` |
| Swift | `xctest` | `*Tests.swift` |

The Java, Kotlin and Swift patterns are each ecosystem's own convention: Maven Surefire's
and Failsafe's default includes, the Kotlin documentation's and Spring Initializr's class
names, and the name the XCTest and Swift Testing templates generate. The Surefire and
Failsafe prefix forms `Test*.java` and `IT*.java` are left out, because a prefix also
names production classes such as `TestDataBuilder`.

The default `mirrors` are the build tools' standard test trees: Maven and Gradle keep
Java and Kotlin tests in `src/test/<language>/` beside `src/main/<language>/`, and a
SwiftPM package keeps each test target `Tests/<Target>Tests/` beside `Sources/<Target>/`.

```yaml
# .beadloom/config.yml — every key optional
tests:
  roots: [tests]                  # laid out by kind: <root>/<kind>/...
  kinds:
    unit: unit
    integration: integration
    acceptance: acceptance
    self_check: self_check
  patterns:                       # framework name -> file-name patterns
    pytest: ["test_*.py", "*_test.py"]
  mirrors:                        # test tree -> the code tree it mirrors
    src/test/java: src/main/java
  beside_code: true
```

A root or a test tree is read only when a folder of exactly that spelling exists, so on
a case-insensitive disk `tests/` and a SwiftPM `Tests/` are not read as each other. A
declaration that cannot be used — a `roots` that is not a list of folders, a kind
Beadloom does not know, a `beside_code` that is not a boolean — is a reindex warning
naming the key, and the default stands for that key.

This repository declares `roots: [tests]`, the four kinds, `pytest` patterns only and
`beside_code: false`. `beside_code` is off because five modules under `src/` are named
like tests (`context_oracle/test_binding.py`, `test_file_reader.py`,
`graph/rules/test_binding.py`, `test_import_boundary.py`,
`application/reindex/test_index.py`), and a file name cannot tell a test module from a
module about tests. A project with such modules has to switch it off the same way.

### The binding rule

`bind_test_file(path, *, code_files, scan_paths, node_sources, overrides, layout=)`
returns a `BoundTestFile` (`path`, `kind`, `ref_id`, `placement`). `layout` defaults to
`TestLayout()`. It applies these steps in order:

1. **Declaration.** A node may list path prefixes under an optional `tests:` key in
   its graph YAML. The prefixes are resolved like `source:` — a trailing `/` is a
   directory, anything else is one file — and the most specific prefix covering
   the test file wins. A declaration wins over every other step. Placement: `override`.
2. **Build tool's test tree.** A file under one of the layout's `mirrors` names a path
   in the code tree it mirrors, by `tree_mirrored_code_path()`, with no kind folder
   between. The language's test affix is taken off the file name — `Test`, `Tests`,
   `TestCase`, `IT`, `ITCase` for Java, `Test`, `Tests` for Kotlin, `Tests` for Swift —
   and a SwiftPM test target `<Target>Tests` names `<Target>`. So
   `src/test/java/<pkg>/BillingTest.java` names `src/main/java/<pkg>/Billing.java`, and
   `Tests/ShopTests/BillingTests.swift` names `Sources/Shop/Billing.swift`. The subject
   resolves to that file when it exists, else to a `<subject>/` folder holding code,
   else to the file path inside a folder holding code, which that folder's owner owns.
   The owning node binds. Placement: `mirror` (`kind` is `None`), or `unowned` when the
   mirrored folder holds no code or no node owns it.
3. **Beside the code.** A file outside every root and every test tree binds to the node
   whose source covers it — `foo_test.go` beside `foo.go`, `x.test.ts` beside `x.ts` —
   by the same ownership rule. Its place binds it, never its name. Placement:
   `beside_code`, or `unplaced` when no node's source covers it or the layout has
   `beside_code: false`.
4. **Kind folder.** Under a root, the segment after the root is the kind folder. `unit`
   and `integration` are mirrored kinds (`MIRRORED_KINDS`). `acceptance` and
   `self_check` are laid out by folder but are not bound here (`OTHER_KINDS`):
   acceptance scenarios bind by their `@node:` tag
   ([scenario binding](../../../graph/features/scenario-binding/SPEC.md)).
   A file under a root but in no kind folder, or directly in one, is `unplaced`. A
   file under an other kind is `other_kind`.
5. **Mirror.** For a mirrored kind, `mirrored_code_path()` turns the path beneath
   the kind folder into a code path. `tests/unit/<path>/test_<name>.py` names
   `<root><path>/<name>.py`, and `<name>_test.py` names the same module. When
   `<root><path>/` holds no code but the module `<root><path>.py` exists, the
   folder names that module, so `tests/unit/<path>/<module>/test_*.py` binds to
   `<module>.py`. The roots are each scan path and each package directly beneath
   one. When several roots resolve, the deepest wins; two equally deep roots
   resolve to nothing. The node that owns the mirrored code path — the most
   specific covering `source`, by `infrastructure.repository.most_specific_owner`
   — is the node. Placement: `mirror`, or `unowned` when no node owns that path.
   The module name is always a `.py` name, so for a file in another language the
   folder decides: the node owning `<root><path>/` binds it.

A file-source node is reached only when the test file is named for its module or
sits in a folder named for it. Otherwise the enclosing directory node owns the
mirrored path.

### Placements

| Placement | Bound to a node | Meaning |
|-----------|-----------------|---------|
| `mirror` | yes | The mirrored code path is owned by a node: under a mirrored kind folder, or in a build tool's test tree |
| `beside_code` | yes | Outside every root and test tree, inside a node's source (BDL-074 G2) |
| `override` | yes | A node's `tests:` declaration covers the file |
| `unowned` | no | Under `unit`/`integration` or a test tree, and no node owns the mirrored code path |
| `unplaced` | no | Not under a kind folder or a test tree, and not inside a node's source: the layout has not reached the file |
| `other_kind` | no | Under `acceptance` or `self_check`; the file's recorded `kind` says which (BDL-074 F1) |

An `other_kind` file carries its kind folder as `kind`, and the two kinds bind differently. An
acceptance step file runs scenarios that bind to a node through their `@node:` tags, which the
`scenario_binding` rules judge. A self-check tests the project's own files and configuration and
binds to no node by design. Every surface that counts them names each kind by its own count,
never under one phrase.

### Which files are read

`discover_test_files()` in the [reindex](../../../application/features/reindex/SPEC.md)
reads the files under each root and each present test tree whose name matches a pattern,
skipping `__pycache__/`, `__snapshots__/` and `node_modules/`. A test beside the code is
taken from the code scan rather than a second walk, so it is read only when it lies under
`scan_paths` in a language the code index parses, and only when the layout has
`beside_code: true`. A file no pattern matches is not a test file, wherever it is.

### What a test file holds

`read_test_file(text, *, suffix=".py")` returns `TestFileContents(test_count, imports)`.
A Python file is parsed once with `ast`:

- `test_count` counts the functions a file defines: module-level `test*`
  functions and `test*` methods of `Test*` classes, sync or async. A parametrised
  function counts once.
- `imports` are `(line, module)` pairs in the code index's form: `import a.b`
  records `a.b`, `from a.b import c` records `a.b`, a relative import records
  nothing. Unlike the tree-sitter code-import extractor, `import a.b as c` is
  recorded.
- Text that does not parse holds nothing (`test_count=0`, no imports).

A file in another language is counted by the line its tests are written in, the retired
mapper's forms, and its imports are not read (BDL-074 G2):

| Suffix | Counted |
|--------|---------|
| `.go` | `func Test...(` |
| `.js`, `.jsx`, `.ts`, `.tsx`, `.mjs`, `.cjs`, `.vue` | an `it(` or `test(` call |
| `.java`, `.kt` | `@Test` |
| `.swift` | `func test...(`, and a function Swift Testing marks `@Test`, once, whatever it is named |

Any other suffix counts 0: a count the reader cannot take is not guessed.

Measured on this repository's 462 test files: the tree-sitter import extractor
took 2.2 s for the imports alone, and the whole cold indexing step built on this
reader took 0.87 s (darwin, Python 3.13).

### `extra["tests"]`

The reindex step that walks the test roots and stores the binding lives in the
[reindex feature](../../../application/features/reindex/SPEC.md)
(`application/reindex/test_index.py`). It rebuilds `nodes.extra["tests"]` from
the binding for every node that has a `source` or a `tests:` declaration, in the
four-key shape its readers expect:

- `framework` — named from the pattern groups the node's bound files matched,
  joined by `+` when there are several (`go_test+pytest`), by `name_frameworks()`
  (BDL-074 G2). A node with no bound file states the frameworks of the project's test
  files. `none` only when the project has no test file at all.
- `test_files` — the node's own bound files united with every `part_of`
  descendant's (`union_over_descendants`). The union counts a file reached
  through two children once.
- `test_count` — the sum of `test_count` over those files.
- `coverage_estimate` — `estimate_coverage()`: more than 3 files `high`, 1-3
  `medium`, 0 with a framework `low`, 0 without one `none`. These thresholds are
  the heuristic's, unchanged.

The reindex also records the layout it read in the index, as `meta.test_layout`
(`infrastructure.repository.RecordedTestLayout`): each kind's folders, the kinds the
config declares, `beside_code`, the roots, the framework names and the test trees
present. The readers that state a count state it against that record, and an index
whose recorded layout differs from the config is rebuilt by the next incremental
reindex rather than reported as unchanged.

A node's `tests:` prefix that covers no indexed test file is a reindex warning, because
an inert declaration reads exactly like one that works. The hint in parentheses is added
only when the prefix has no trailing `/`:

```
Node 'billing': `tests:` prefix 'tests/e2e' covers no indexed test file, so it binds nothing (a folder is declared with a trailing '/')
```

### The transition

Measured on this repository by `beadloom reindex` on 2026-09-28 (`features/BDL-074` at
`293db6b5`): 615 test files, 271 bound to a node (72 under `tests/unit/` and 199 under
`tests/integration/`, all by the mirror), 167 `unplaced`, 74 acceptance step and 103
self-check. None is bound beside the code, because this repository has
`beside_code: false`. When the binding landed (BDL-074 C1, 2026-09-27) the same count
read 462 test files, 0 bound, 392 `unplaced` and 70 `other_kind`. The heuristic it
replaced gave the root node 882 files and bound 532 mutmut copies under `mutants/` to
nodes.

A node with 0 bound tests is distinguishable from a repository whose tests are not
laid out: `beadloom reindex` prints the placement counts on its `Tests:` line, and
the `test_files` table records each file's placement.

### Readers of the binding

- **`ctx`.** The context bundle carries the focus node's `extra["tests"]` under
  `tests` and, since BDL-074 C2, the project's test files by placement under
  `test_placements` (`{placement: count}`, read by
  `infrastructure.repository.count_test_files_by_placement`; `{}` for an index
  older than the test tables). Since BDL-074 G2 the builder also states the unplaced
  sentence into the bundle, as `test_unplaced` (a string, or `null` when no file is
  unplaced), built by `describe_unplaced()` against the layout the index recorded. When
  it is set, the Markdown output adds one line under `Tests:`. On this repository:
  `167 of 615 test file(s) are unplaced (not under tests/integration/ or tests/unit/)
  and bind to no node, so the count above can be short`. The folders are the recorded
  roots' mirrored kind folders and the test trees present, and `, nor inside a node's
  source` follows them when tests beside the code are read. A cached bundle built
  before the key existed falls back to the default layout's sentence.
- **Debt report.** `_count_untested()` in `application/debt_report/collect.py`
  counts a node as untested when it carries `extra["tests"]` with an empty
  `test_files`. While any test file is unplaced the count is withheld (0), and the
  report's `test_population` says why, in the same `describe_unplaced()` sentence against
  the recorded layout. When the index holds no test file at all and a layout is recorded,
  the population adds what a test file is read by (`describe_test_file_recognition()`):
  under the default layout, `a test file is read when its name matches a pattern of
  go_test, jest, junit, pytest or xctest under the root tests or beside a node's code`.
  See the [debt report](../../../application/features/debt-report/SPEC.md).
- **Lint.** Since BDL-074 C3 the rule engine judges the binding: `test_binding` reports a
  test file bound to no node and a node with no bound test file, and
  `test_import_boundary` narrows an import boundary to the tests of matching nodes. Both
  read `test_files` and `test_imports`. `test_binding` does not judge placement
  `other_kind`, and its population statement names those files by recorded kind and count
  (BDL-074 F1), each with the folder it was recognised by and whether `tests.kinds`
  declared that folder (BDL-074 G2). See the
  [rule-engine SPEC](../../../graph/features/rule-engine/SPEC.md).
- **Per-change mutation.** `beadloom mutation --changed-since` selects the files bound to
  a changed node whatever placement bound them, and lists the `unplaced` files as the
  runner's fallback. See the [mutation-scope component](../../../application/components/mutation-scope/DOC.md).

## Invariants

- Nothing is guessed: a test file binds by a declaration, by the mirror of its path
  under a root or a test tree, or by its place inside a node's source, and otherwise
  binds to nothing and records why (its placement). A file name decides only whether
  a file is a test, by the declared patterns, never which node it tests.
- A declaration wins over the mirror and over the place beside the code.
- Ownership of a mirrored path, a place beside the code or a declared prefix is decided
  by the same rule as code ownership (`most_specific_owner`): the longest covering
  prefix wins.
- The layout is configuration: a project whose tests are laid out another way declares
  its roots, patterns, kind folders and test trees rather than being read by a
  heuristic. A key that cannot be used is reported, and its default stands.
- The kind of a file under a root is its folder's. The folder is trusted, not verified:
  what a file holds is never checked against its kind.
- A parent's `test_files` is a union over its descendants, not a sum.
- The binding functions are pure: they take the paths they reason about, and the
  walk and the storage belong to the reindex. `load_test_layout()` is the one function
  that reads a file.

## API

Module `src/beadloom/context_oracle/test_layout.py` (BDL-074 G2):

- `TestLayout` — frozen dataclass: `roots`, `patterns` (`(framework, patterns)` pairs),
  `kind_folders`, `declared_kinds`, `beside_code`, `mirrors` (`(test tree, code tree)`
  pairs). Methods: `framework_of(name) -> str | None` (the first group whose pattern the
  name matches), `is_test_file(name) -> bool`, `folder_of(kind) -> str`,
  `kind_prefixes(kind) -> tuple[str, ...]` (`root/folder/` for every root),
  `locate(path) -> tuple[str | None, str] | None` (`None` under no root, else the kind and
  the path below it), `mirror_of(path) -> tuple[str, str, str] | None` (the test tree,
  the code tree and the path below), and `recorded(present_mirror_roots=()) ->
  RecordedTestLayout`.
- `load_test_layout(project_root) -> tuple[TestLayout, list[str]]` — the layout
  `.beadloom/config.yml` declares, and a sentence for each unusable part of it. An
  unreadable config yields the default layout and one sentence.
- `layout_from_config(config) -> tuple[TestLayout, list[str]]` — the same over a parsed
  mapping.
- `DEFAULT_ROOTS`, `DEFAULT_PATTERNS`, `DEFAULT_MIRRORS`, `CONFIG_PATH`, `CONFIG_KEY`.
- `KIND_UNIT`, `KIND_INTEGRATION`, `MIRRORED_KINDS`, `KINDS` (acceptance, integration,
  self_check, unit).

Module `src/beadloom/context_oracle/test_binding.py`:

- `TEST_ROOT` (`"tests"`, the default root), `MIRRORED_KINDS` (`unit`, `integration`,
  re-exported from `test_layout`), `OTHER_KINDS` (`acceptance`, `self_check`).
- `PLACEMENT_MIRROR`, `PLACEMENT_BESIDE_CODE`, `PLACEMENT_OVERRIDE`, `PLACEMENT_UNOWNED`,
  `PLACEMENT_UNPLACED`, `PLACEMENT_OTHER_KIND` — the placement values. Defined in
  `infrastructure/repository.py` since BDL-074 C3 and re-exported here under the same
  names, so an import from this module still answers. The vocabulary sits below both of
  its readers: this module assigns a placement and the rule engine's `test_binding` judges
  it, and a vocabulary two peer domains share belongs below both rather than in the one that
  wrote it down first.
- `FRAMEWORK_NONE`. `TEST_FILE_PATTERNS` and `FRAMEWORK_PYTEST` were removed in BDL-074 G2:
  the patterns and the framework names are the layout's.
- `BoundTestFile` — frozen dataclass: `path`, `kind`, `ref_id`, `placement`.
- `is_test_file(name: str) -> bool` — whether a file name is a test under the default
  layout's patterns.
- `name_frameworks(frameworks) -> str` — one name for a set of frameworks, sorted and
  joined by `+`, or `none`.
- `bind_test_file(path, *, code_files, scan_paths, node_sources, overrides, layout=TestLayout()) -> BoundTestFile`
  — bind one test file.
- `mirrored_code_path(under_kind, *, code_files, scan_paths) -> str | None` — the
  code path a path beneath a kind folder names.
- `tree_mirrored_code_path(code_root, below, *, code_files) -> str | None` — the code path
  a file below a build tool's test tree names in *code_root*; `None` when the mirrored
  folder holds no code.
- `union_over_descendants(direct, parent_children) -> dict[str, frozenset[str]]`
  — each node's files united with its descendants'.
- `estimate_coverage(file_count, *, framework_detected) -> str`.
- `summarize_tests(files, counts, *, framework) -> dict[str, object]` — one node's
  `extra["tests"]` in the four-key shape.
- `describe_unplaced(counts: Mapping[str, int], layout: RecordedTestLayout | None = None) -> str | None`
  — the sentence that says how many test files are unplaced and bind to no node; `None`
  when none is. It names the recorded layout's mirrored folders and test trees, adding
  `, nor inside a node's source` when tests beside the code are read; with no layout it
  names the default folders. `ctx` and the debt report both print it.
- `describe_test_file_recognition(layout: RecordedTestLayout) -> str` (BDL-074 G2) — what
  makes a file a test file this index reads, in one clause: the frameworks, the roots and
  test trees, and `or beside a node's code` when that is read.
- `describe_unbound(counts: Mapping[str, int], kinds: Mapping[str, int]) -> str | None`
  (BDL-074 F1) — every test file bound to no node, stated by why: `describe_unplaced()`'s
  sentence, then `W unowned (under a mirrored folder whose code no node owns)` when non-zero,
  then `A acceptance step and S self-check file(s) bind to no node by their kind`, joined by
  `; `. `None` when no file is bound to no node. `beadloom mutation --changed-since` prints it
  on its `Binding:` line, so its unplaced count is the one `ctx` and the debt report state.

Module `src/beadloom/context_oracle/test_file_reader.py`:

- `TestFileContents` — frozen dataclass: `test_count`, `imports`.
- `read_test_file(text: str, *, suffix: str = ".py") -> TestFileContents`.
- `count_test_functions(text: str) -> int` — the Python count.

Module `src/beadloom/infrastructure/repository.py`:

- `PLACEMENT_MIRROR` (`"mirror"`), `PLACEMENT_BESIDE_CODE` (`"beside_code"`),
  `PLACEMENT_OVERRIDE` (`"override"`), `PLACEMENT_UNOWNED` (`"unowned"`),
  `PLACEMENT_UNPLACED` (`"unplaced"`), `PLACEMENT_OTHER_KIND` (`"other_kind"`) — where the
  placement values are defined.
- `KIND_ACCEPTANCE` (`"acceptance"`), `KIND_SELF_CHECK` (`"self_check"`),
  `KIND_UNRECORDED` (`"unrecorded"`, stated for an `other_kind` row that recorded no kind)
  and `label_test_kind(kind) -> str` (`acceptance step`, `self-check`, otherwise the kind as
  recorded) — BDL-074 F1. `OTHER_KINDS` is built from the first two.
- `TEST_LAYOUT_KEY` (`"test_layout"`), `RecordedTestLayout` and
  `read_test_layout(conn) -> RecordedTestLayout | None` — the layout record in `meta`
  (BDL-074 G2); `None` for an index written before it or a record that does not parse.
- `count_test_files_by_placement(conn) -> dict[str, int]` — indexed test files per
  placement; `{}` when the `test_files` table does not exist.
- `count_other_kind_test_files(conn) -> dict[str, int]` — `other_kind` files per recorded
  kind; `{}` when the `test_files` table does not exist.

## Testing

Tests bound to `test-mapping` (50 tests in 5 files, measured by `beadloom ctx test-mapping`
on 2026-09-28), all under `tests/unit/context_oracle/test_binding/`:
`test_a_test_file_binds_to_the_node_its_path_mirrors.py` (the binding),
`test_a_test_beside_the_code_binds_to_the_node_covering_it.py` (beside the code),
`test_a_test_in_a_build_tools_test_tree_binds_by_its_mirror.py` (the test trees and the
affixes), `test_the_unplaced_sentence_names_the_declared_folders.py` and
`test_the_unplaced_share_is_one_sentence.py` (`describe_unplaced`). Beside them, bound to
`context-oracle`: `tests/unit/context_oracle/test_layout/test_the_test_layout_is_read_from_config.py`
and `tests/unit/context_oracle/test_layout/test_java_kotlin_and_swift_tests_are_named_by_convention.py`
(the layout and its defaults),
`tests/unit/context_oracle/test_file_reader/test_a_test_file_is_read_for_its_tests_and_imports.py`
and `tests/unit/context_oracle/test_file_reader/test_a_test_file_in_another_language_is_counted.py`
(the reader). Bound to `reindex`:
`tests/integration/application/reindex/test_reindex_indexes_test_files_in_their_own_tables.py`,
`tests/integration/application/reindex/test_reindex_tests.py`,
`tests/integration/application/reindex/test_tests_are_found_beside_the_code_and_under_declared_roots.py`
and `tests/integration/application/reindex/test_a_build_tools_test_tree_is_indexed_by_its_mirror.py`
(the tables, `extra["tests"]`, the recorded layout and the `tests:` warning). Elsewhere:
`tests/unit/services/commands/test_the_ctx_markdown_states_the_tests_line.py` and
`tests/unit/services/commands/test_the_ctx_markdown_prints_the_bundles_unplaced_sentence.py`
(the `ctx` line),
`tests/integration/context_oracle/builder/test_the_context_bundle_states_the_unplaced_sentence_of_the_recorded_layout.py`
(`test_unplaced`),
`tests/integration/application/debt_report/test_the_debt_report_reads_the_test_binding.py`
and `tests/integration/application/debt_report/test_an_adopter_scores_what_it_scored_before.py`
(the debt report's count, on a Go module, three Python layouts and the Maven, Gradle-Kotlin
and SwiftPM layouts),
`tests/integration/infrastructure/repository/test_test_files_are_counted_by_their_kind.py`
(the counts by kind), and the acceptance scenarios in
`tests/acceptance/features/test_files_bind_to_the_node_their_path_mirrors.feature`,
`tests/acceptance/features/ctx_and_debt_report_read_the_test_binding.feature`,
`tests/acceptance/context-oracle/test-mapping/tests_beside_the_code_bind.feature` and
`tests/acceptance/context-oracle/test-mapping/tests_in_a_build_tools_test_tree_bind.feature`.
