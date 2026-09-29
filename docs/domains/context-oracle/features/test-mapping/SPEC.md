# Test Mapping

Test-to-node binding for the context-oracle domain: which graph node a test file
belongs to, derived from where the file lives.

**Source:** `src/beadloom/context_oracle/test_binding.py`,
`src/beadloom/context_oracle/test_file_reader.py`,
`src/beadloom/context_oracle/test_layout.py`

**Parts:** two component nodes are `part_of` this feature (`beadloom-2mj3.15`): `test-layout`
(`test_layout.py`) and `test-file-reader` (`test_file_reader.py`). Each has its own node so that
its unit tests bind to it rather than to `context-oracle`, and each declares `docs_absent` with
a reason: this SPEC documents both, in "Configuration: the test layout" and "What a test file
holds". Both modules carry `feature=test-mapping` beside their `component=` annotation, so this
SPEC keeps its sync pair with each.

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
(`test_layout.TestLayout`, BDL-074 G2, `beadloom-2mj3.13` and `beadloom-2mj3.15`), read
from an optional `tests:` block in `.beadloom/config.yml`. Every key has a default, so a
project that declares nothing is read by the defaults below.

| Key | Default | A declared value |
|-----|---------|------------------|
| `roots` | `[tests, test, spec, __tests__]`, each read only where a folder of exactly that spelling exists | replaces the list |
| `kinds` | each kind in the folder of its own name: `unit`, `integration`, `acceptance`, `self_check` | replaces the folder of that one kind |
| `patterns` | the five framework groups below | replaces all five groups |
| `mirrors` | `src/test/java: src/main/java`, `src/test/kotlin: src/main/kotlin`, `Tests: Sources` | replaces all three trees |
| `beside_code` | `true` | `true` or `false` |

`test/` and `spec/` joined `tests/` as default roots by the owner's ruling of 2026-09-28
(`beadloom-2mj3.15`, NG1), in place of a walk over the whole project, and a top-level
`__tests__/` joined them under the same ruling (`beadloom-2mj3.17`), because NG1 named all
three places. A flat `test/`, `spec/` or top-level `__tests__/` folder is read without a
declaration, and a file there binds by the mirror or a `tests:` list, or is read and counted
`unplaced`.

The index records only the roots that exist (`RecordedTestLayout.roots`) and keeps the roots
looked for and not found apart (`RecordedTestLayout.absent_roots`), so `ctx`, the debt report
and `beadloom mutation` name only the roots a project has. A project with none of them, and
with tests read beside the code, is told which were looked for:

```
a test file is read when its path matches a pattern of ... and it lies beside a node's code, since none of the roots tests, test, spec, __tests__ exists
```

When tests beside the code are not read, the clause ends `under a root, and none of the roots
tests, test, spec, __tests__ exists`. A record that names no absent root says `no root is
recorded` in place of `none of the roots ... exists` (`beadloom-2mj3.19`).

A pattern matches the END of a file's project-relative path, case-sensitively
(`test_layout.pattern_matches()`). A pattern without a `/` matches the file name. A pattern
with a `/` is the folder form: it matches the path's last folders and the name, segment by
segment, where a `**` segment stands for any number of folders: zero or more between two
segments, at least one at the end, because a path names a file. So `__tests__/**` is every file under a
`__tests__/` folder at any depth, and `src/test/**/*.java` is every `.java` file under
`src/test/`.

The default `patterns`, each group named for the framework its files belong to, in the order
they are matched:

| Language | Group | Default patterns |
|----------|-------|------------------|
| Python | `pytest` | `test_*.py`, `*_test.py` |
| Go | `go_test` | `*_test.go` |
| JavaScript, TypeScript | `jest` | `*.test.*`, `*.spec.*`, `__tests__/**/*.[jt]s`, `__tests__/**/*.[jt]sx` |
| Java, Kotlin | `junit` | `*Test.java`, `*Tests.java`, `*TestCase.java`, `*IT.java`, `*ITCase.java`, `*Test.kt`, `*Tests.kt`, `src/test/**/*.java`, `src/test/**/*.kt` |
| Swift | `xctest` | `*Tests.swift`, `*Tests/**/*.swift` |

Every default is an ecosystem's own convention: Jest's default `testMatch`, Maven Surefire's
and Failsafe's default includes, the Kotlin documentation's and Spring Initializr's class
names, and the name the XCTest and Swift Testing templates generate. The Surefire and
Failsafe prefix forms `Test*.java` and `IT*.java` are left out, because a prefix also names
production classes such as `TestDataBuilder`. The folder-form defaults read what the retired
mapper read and a name pattern cannot state (`beadloom-2mj3.15`): a file under Jest's
`__tests__/`, and any file in a build tool's test tree whatever it is named, because Gradle
runs every class there, Kotest names a class `*Spec` and a SwiftPM test target holds helpers
under any name.

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
  patterns:                       # framework name -> patterns (a name, or the end of a path)
    pytest: ["test_*.py", "*_test.py"]
    jest: ["*.test.ts", "__tests__/**"]
  mirrors:                        # test tree -> the code tree it mirrors
    src/test/java: src/main/java
  beside_code: true
```

A root or a test tree is read only when a folder of exactly that spelling exists, so on
a case-insensitive disk `tests/` and a SwiftPM `Tests/`, or `spec/` and `Spec/`, are not read
as each other. A declaration that cannot be used is a reindex warning naming the key, and the
default stands for that key: a `roots` that is not a list of folders, a kind Beadloom does not
know, a `beside_code` that is not a boolean, a `patterns` that does not map each framework
name to a list of file patterns (a name, or the end of a path). A `roots` list that names the project itself or a
folder outside it — `.`, `/`, `./`, `..`, `a/../b` — is refused whole, because `.` would walk
`.git`, `.venv` and a mutmut copy of the code, and `..` a folder outside the project:

```
`tests.roots` in .beadloom/config.yml must be a list of folders inside the project, none of them the project itself or outside it; the default (tests, test, spec, __tests__) is used
```

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
reads the files under each root and each present test tree whose project-relative PATH
matches a pattern, skipping `__pycache__/`, `__snapshots__/` and `node_modules/`. A test
beside the code is taken from the code scan rather than a second walk, so it is read only
when it lies under `scan_paths` in a language the code index parses, and only when the
layout has `beside_code: true`. A file no pattern matches is not a test file, wherever it is.
A file outside every root, every test tree and every node's source is not read, whatever its
path: binding it would take a guess at its node. So `ctx` and the debt report state, every
time, the patterns and the roots a test file is read under (`describe_test_file_recognition()`),
and a count of test files reads as a count of the files that clause names.

### What is not bound: the non-goals

A test binds by the mirror, by its place beside the code, or through a node's `tests:` list,
and never by a guess (PRD BDL-074 Non-goals, owner, 2026-09-28). `beadloom-2mj3.15` enumerated
32 conventions of the retired name-guessing mapper, proved 23 no worse than it on fixtures
against its measured figures, and ruled out the rest as guessing. What each ruled-out
convention does now, and the declaration that restores the retired mapper's figures:

| Non-goal | The retired mapper | What Beadloom does | The declaration that binds it |
|----------|--------------------|--------------------|-------------------------------|
| NG2 — an Xcode sibling test target (`ShopTests/` beside `Shop/`) is not paired by default | paired it by the file name | the pairing depends on the project's own name, so no fixed folder can be a default. `ShopTests/` is outside every root, test tree and node source, so it is not read: `ctx` shows 0 bound and the debt report counts every covered node untested, with the recognition clause | one line, `tests.mirrors: {ShopTests: Shop}`, which binds `ShopTests/BillingTests.swift` to the node owning `Shop/Billing/` |
| NG3 — a test is not bound by what it imports, nor by a folder named after a node (`tests/<ref>/`) | bound it by `import <ref>` or the folder name | an import names fixtures, helpers and collaborators as well as the subject. The file is read and counted `unplaced`, and the debt report withholds its untested count, so the score does not move | a node's `tests:` list (`tests: [tests/billing/]`), or the mirror layout |
| NG4 — a framework is not named from a marker file without a test file (`conftest.py`, `jest.config.*`, an empty `src/test/` or `*Tests/` folder) | named the framework, estimated `low` and counted untested 0 | the framework reads `none` and every covered node counts untested, with the recognition clause | none: a project with no test says so and scores that |

For an Xcode project the three mean: its tests in `ShopTests/` are not read until it declares
`tests.mirrors: {ShopTests: Shop}` (NG2). Declared mirrors replace the three default trees,
which an Xcode project does not use. A file in `ShopTests/` then binds by its mirrored path,
never by what it imports (NG3). A `ShopTests/` folder holding no test file names no framework
(NG4).

NG1 was not accepted as a non-goal: the retired mapper also bound a flat `test/` or `spec/`
file, or a file in a top-level `__tests__/`, by its name, and each of those folders is now a
default root (`beadloom-2mj3.15`, `beadloom-2mj3.17`). The file is read and counted
`unplaced` rather than ignored, so the debt report withholds its count as main scored it. A
`tests:` list binds it without a `roots` declaration.

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
config declares, `beside_code`, the roots present, the framework names, the test trees
present, since `beadloom-2mj3.15` each group's patterns in the order they are matched, and
since `beadloom-2mj3.17` the roots in force that the project does not have. The readers that
state a count state it against that record, and an index whose recorded layout differs from
the config, or from the roots and test trees on disk, is rebuilt by the next incremental
reindex rather than reported as unchanged. A record written before the patterns were recorded reads with no
patterns, and the changed record forces one test re-index.

A node's `tests:` prefix that covers no indexed test file is a reindex warning, because
an inert declaration reads exactly like one that works. The hint in parentheses is added
only when the prefix has no trailing `/`:

```
Node 'billing': `tests:` prefix 'tests/e2e' covers no indexed test file, so it binds nothing (a folder is declared with a trailing '/')
```

### The transition

Measured on this repository by `beadloom reindex` on 2026-09-28 (`features/BDL-074` at `909a0098`):
620 test files, 275 bound to a node (74 under `tests/unit/` and 201 under `tests/integration/`, all
by the mirror), 167 `unplaced`, 75 acceptance step and 103 self-check. The five files over the 615
measured at `293db6b5` are `beadloom-2mj3.15`'s new test files, and the default roots `test/`,
`spec/` and `__tests__/` changed nothing here, because this repository declares `roots: [tests]` and
has none of those folders (`620 = 275/167/75/103`, unchanged after `beadloom-2mj3.17`). At
`067df32a` (2026-09-29) the count reads 623 test files, 278 bound, 167 `unplaced`, 75 acceptance
step and 103 self-check: the three bound files over 620 are `beadloom-2mj3.19`'s new test files.
None is bound beside the code, because this repository has `beside_code: false`. When the binding
landed (BDL-074 C1, 2026-09-27) the same count read 462 test files, 0 bound, 392 `unplaced` and 70
`other_kind`. The heuristic it replaced gave the root node 882 files and bound 532 mutmut copies
under `mutants/` to nodes.

A node with 0 bound tests is distinguishable from a repository whose tests are not
laid out: `beadloom reindex` prints the placement counts on its `Tests:` line, and
the `test_files` table records each file's placement.

### Readers of the binding

- **`ctx`.** The context bundle carries the focus node's `extra["tests"]` under `tests` and, since
  BDL-074 C2, the project's test files by placement under `test_placements` (`{placement: count}`,
  read by `infrastructure.repository.count_test_files_by_placement`; `{}` for an index older than
  the test tables). Since BDL-074 G2 the builder also states the unplaced sentence into the bundle,
  as `test_unplaced` (a string, or `null` when no file is unplaced), built by `describe_unplaced()`
  against the layout the index recorded. When it is set, the Markdown output adds one line under
  `Tests:`. On this repository, measured at `067df32a` on 2026-09-29: `167 of 623 test file(s) are
  unplaced (not under tests/integration/ or tests/unit/) and bind to no node, so the count above can
  be short`. The folders are the recorded roots' mirrored kind folders and the test trees present,
  and `, nor inside a node's source` follows them when tests beside the code are read. Under the
  default roots the sentence names the unit and integration folders of the roots that exist
  (`beadloom-2mj3.17`). With no root and no test tree present it reads `(inside no node's source)`
  when tests beside the code are read, and `(under no root)` when they are not. A cached bundle
  built before the key existed falls back to the default layout's sentence. Since `beadloom-2mj3.15`
  the bundle also carries `test_recognition`, the `describe_test_file_recognition()` clause (`null`
  without a recorded layout), and the Markdown output prints it capitalised under `Tests:` every
  time, after the unplaced line when there is one. On this repository: `A test file is read when its
  path matches a pattern of pytest (test_*.py, *_test.py) under the root tests`.
- **Debt report.** `_count_untested()` in `application/debt_report/collect.py`
  counts a node as untested when it carries `extra["tests"]` with an empty
  `test_files`. While any test file is unplaced the count is withheld (0), and the
  report's `test_population` says why, in the same `describe_unplaced()` sentence against
  the recorded layout. Whenever a layout is recorded, counted and withheld alike, the
  population ends with `; ` and what a test file is read by
  (`describe_test_file_recognition()`, `beadloom-2mj3.15`), so "all N test file(s) placed"
  reads as "all N files those patterns matched". Under the default layout the clause is
  `a test file is read when its path matches a pattern of go_test (*_test.go), jest
  (*.test.*, *.spec.*, __tests__/**/*.[jt]s, __tests__/**/*.[jt]sx), junit (...), pytest
  (test_*.py, *_test.py) or xctest (*Tests.swift, *Tests/**/*.swift) under ...`, where
  `...` names the roots and test trees that exist, followed by `or beside a node's code`, and
  every `junit` pattern is named where `(...)` stands here. With no root and no test tree it
  ends `and it lies beside a node's code, since none of the roots tests, test, spec, __tests__
  exists` (`beadloom-2mj3.17`, reworded by `beadloom-2mj3.19`). A record written before the
  patterns were recorded names the groups alone.
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
  runner's fallback. Its `Binding:` line states the unplaced share over the folders of the
  recorded layout (`ChangePlan.test_layout`), as `ctx` and the debt report do. See the [mutation-scope component](../../../application/components/mutation-scope/DOC.md).

## Invariants

- Nothing is guessed: a test file binds by a declaration, by the mirror of its path
  under a root or a test tree, or by its place inside a node's source, and otherwise
  binds to nothing and records why (its placement). A file's path decides only whether
  it is a test, by the declared patterns, never which node it tests.
- A file outside every root, every test tree and every node's source is not read, and the
  readers that state a count state what a test file is read by, every time.
- A root is a folder inside the project: a `roots` list naming `.`, `/` or a path through
  `..` is refused whole, and the default stands.
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
  pairs). Methods: `framework_of(path) -> str | None` (the first group whose pattern the
  project-relative path matches; a bare file name is a path with no folder, which a name
  pattern matches and a folder pattern does not), `is_test_file(path) -> bool`,
  `folder_of(kind) -> str`,
  `kind_prefixes(kind) -> tuple[str, ...]` (`root/folder/` for every root),
  `locate(path) -> tuple[str | None, str] | None` (`None` under no root, else the kind and
  the path below it), `mirror_of(path) -> tuple[str, str, str] | None` (the test tree,
  the code tree and the path below), and `recorded(present_mirror_roots=(),
  present_roots=None) -> RecordedTestLayout` (*present_roots* are the roots the project has,
  `None` for all of them; the record's `roots` and `kind_prefixes` hold those, and
  `absent_roots` the rest, `beadloom-2mj3.17`).
- `pattern_matches(pattern: str, path: str) -> bool` (`beadloom-2mj3.15`) — whether a
  pattern matches the end of a project-relative path: the file name for a pattern without
  a `/`, the last folders and the name for the folder form, `**` any number of folders.
  Case-sensitive on every platform.
- `load_test_layout(project_root) -> tuple[TestLayout, list[str]]` — the layout
  `.beadloom/config.yml` declares, and a sentence for each unusable part of it. An
  unreadable config yields the default layout and one sentence.
- `layout_from_config(config) -> tuple[TestLayout, list[str]]` — the same over a parsed
  mapping.
- `DEFAULT_ROOTS` (`("tests", "test", "spec", "__tests__")`), `DEFAULT_PATTERNS`, `DEFAULT_MIRRORS`,
  `CONFIG_PATH`, `CONFIG_KEY`.
- `KIND_UNIT`, `KIND_INTEGRATION`, `MIRRORED_KINDS`, `KINDS` (acceptance, integration,
  self_check, unit).

Module `src/beadloom/context_oracle/test_binding.py`:

- `TEST_ROOT` (`"tests"`, the root the unplaced sentence names with no recorded layout),
  `MIRRORED_KINDS` (`unit`, `integration`,
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
- `is_test_file(path: str) -> bool` — whether a project-relative path, or a bare file name,
  is a test under the default layout's patterns.
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
  `, nor inside a node's source` when tests beside the code are read. With no folder to name
  it says `inside no node's source` or `under no root` (`beadloom-2mj3.17`). With no layout
  it names the default folders. `ctx` and the debt report both print it.
- `describe_test_file_recognition(layout: RecordedTestLayout) -> str` (BDL-074 G2) — what
  makes a file a test file this index reads, in one clause: `a test file is read when its
  path matches a pattern of`, each group with its patterns in parentheses (the group names
  alone for a record without patterns), the recorded roots and test trees, and `or beside a
  node's code` when that is read. With none recorded it says
  `and it lies beside a node's code, since none of the roots <absent roots> exists`, or
  `under a root, and none of the roots <absent roots> exists` when tests beside the code are
  not read; with no absent root recorded, `no root is recorded` replaces
  `none of the roots ... exists` (`beadloom-2mj3.17`, reworded by `beadloom-2mj3.19`). `ctx`
  and the debt report state it every time (`beadloom-2mj3.15`).
- `describe_unbound(counts: Mapping[str, int], kinds: Mapping[str, int], layout: RecordedTestLayout | None = None) -> str | None`
  (BDL-074 F1) — every test file bound to no node, stated by why: `describe_unplaced()`'s
  sentence over *layout*, then `W unowned (under a mirrored folder whose code no node owns)` when non-zero,
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
  `RecordedTestLayout.patterns` (`beadloom-2mj3.15`) holds each group's patterns in match
  order, encoded as `[[name, [pattern, ...]], ...]`; `()` for an older record.
  `RecordedTestLayout.absent_roots` (`beadloom-2mj3.17`) holds the roots in force the project
  does not have, encoded as `absent_roots`; `()` for an older record. Its `roots` and
  `kind_prefixes` hold only the roots that exist.
- `count_test_files_by_placement(conn) -> dict[str, int]` — indexed test files per
  placement; `{}` when the `test_files` table does not exist.
- `count_other_kind_test_files(conn) -> dict[str, int]` — `other_kind` files per recorded
  kind; `{}` when the `test_files` table does not exist.

## Testing

Tests bound to `test-mapping`, its own and its two components' (103 tests in 10 files, measured
by `beadloom ctx test-mapping` on 2026-09-28 at `a7b888a8`):

- `test-mapping` (57 tests in 5 files), under `tests/unit/context_oracle/test_binding/`:
  `test_a_test_file_binds_to_the_node_its_path_mirrors.py` (the binding),
  `test_a_test_beside_the_code_binds_to_the_node_covering_it.py` (beside the code),
  `test_a_test_in_a_build_tools_test_tree_binds_by_its_mirror.py` (the test trees and the
  affixes), `test_the_unplaced_sentence_names_the_declared_folders.py` and
  `test_the_unplaced_share_is_one_sentence.py` (`describe_unplaced`, the recognition clause).
- `test-layout` (37 tests in 3 files), under `tests/unit/context_oracle/test_layout/`:
  `test_the_test_layout_is_read_from_config.py` (the keys and the default roots),
  `test_java_kotlin_and_swift_tests_are_named_by_convention.py` (the defaults) and
  `test_a_pattern_with_a_folder_matches_the_end_of_the_path.py` (the folder form and the
  refused roots).
- `test-file-reader` (9 tests in 2 files), under `tests/unit/context_oracle/test_file_reader/`:
  `test_a_test_file_is_read_for_its_tests_and_imports.py` and
  `test_a_test_file_in_another_language_is_counted.py`.

Bound to `reindex`:
`tests/integration/application/reindex/test_reindex_indexes_test_files_in_their_own_tables.py`,
`tests/integration/application/reindex/test_reindex_tests.py`,
`tests/integration/application/reindex/test_tests_are_found_beside_the_code_and_under_declared_roots.py`,
`tests/integration/application/reindex/test_a_build_tools_test_tree_is_indexed_by_its_mirror.py`
(the tables, `extra["tests"]`, the recorded layout and the `tests:` warning),
`tests/integration/application/reindex/test_every_convention_the_retired_mapper_read_is_read.py`
(the conventions proven no worse than the retired mapper) and
`tests/integration/application/reindex/test_a_convention_main_reached_by_a_guess_is_stated_not_guessed.py`
(the non-goals, the default roots `test/`, `spec/` and `__tests__/` read where they exist, and
the declarations that restore the retired mapper's figures, the Xcode mirror among them). Elsewhere:
`tests/unit/services/commands/test_the_ctx_markdown_states_the_tests_line.py`,
`tests/unit/services/commands/test_the_ctx_markdown_prints_the_bundles_unplaced_sentence.py`
and `tests/unit/services/commands/test_the_ctx_markdown_says_which_files_count_as_tests.py`
(the `ctx` lines),
`tests/integration/context_oracle/builder/test_the_context_bundle_states_the_unplaced_sentence_of_the_recorded_layout.py`
(`test_unplaced`, `test_recognition`),
`tests/integration/application/debt_report/test_the_debt_report_reads_the_test_binding.py`
and `tests/integration/application/debt_report/test_an_adopter_scores_what_it_scored_before.py`
(the debt report's count, one project per convention: a Go module, Python layouts, Jest
`__tests__/`, and the Maven, Gradle-Kotlin and SwiftPM layouts),
`tests/integration/infrastructure/repository/test_test_files_are_counted_by_their_kind.py`
(the counts by kind), and the acceptance scenarios in
`tests/acceptance/features/test_files_bind_to_the_node_their_path_mirrors.feature`,
`tests/acceptance/features/ctx_and_debt_report_read_the_test_binding.feature`,
`tests/acceptance/context-oracle/test-mapping/tests_beside_the_code_bind.feature`,
`tests/acceptance/context-oracle/test-mapping/tests_in_a_build_tools_test_tree_bind.feature`
and `tests/acceptance/context-oracle/test-mapping/every_convention_the_retired_mapper_read_is_read.feature`.
