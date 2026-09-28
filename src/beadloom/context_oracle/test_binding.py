"""Test binding: which graph node a test file belongs to, derived from where it lives.

A test file under ``<root>/<kind>/`` for a mirrored kind (``unit``, ``integration``)
names a code path with the rest of its path: ``tests/unit/<path>/test_<name>.py``
names ``<package>/<path>/<name>.py``, and a folder named after a module
(``tests/unit/<path>/<module>/test_*.py``) names that module. The node that OWNS
that code path — the most specific node whose source covers it, by the one rule
``infrastructure.repository`` holds — is the node the test binds to. No file
declares anything; the fact is stated once, by where the file is.

A test file inside the code, outside every test root — ``foo_test.go`` beside
``foo.go``, ``test_x.py`` beside ``x.py``, ``x.test.ts`` beside ``x.ts`` — binds
to the node whose source covers it, by the same ownership rule (BDL-074 G2, the
owner's ruling on review ``beadloom-b9ll`` M3). Its place binds it, never its
name: a Go test that names another package still belongs to the one it sits in.
The roots, the kind folders and the file-name patterns are the project's
:class:`~beadloom.context_oracle.test_layout.TestLayout`.

A build tool's test tree mirrors its code tree the same way, with no kind folder
between (BDL-074 G2b): ``src/test/java/<package>/BillingTest.java`` names
``src/main/java/<package>/Billing.java``, and SwiftPM's
``Tests/ShopTests/BillingTests.swift`` names ``Sources/Shop/Billing.swift`` — or
the ``Sources/Shop/Billing/`` folder, when that is what holds the code. The
language's test affix (``Test``, ``Tests``, ``TestCase``, ``IT``, ``ITCase``) is
taken off the name, and a SwiftPM test target ``<Target>Tests`` names ``<Target>``.

A node may also claim tests its path does not mirror, with a ``tests:`` list of
path prefixes in its YAML, resolved by the same ownership rule over those
prefixes. A declaration wins over the mirror: it is the statement a person made
about that one file.

Nothing is guessed. A test file outside the mirrored folders is ``unplaced`` —
recorded and counted, so a node with no bound test reads differently from a
repository whose tests are not laid out yet — and a mirror whose code no node
owns is ``unowned``. The heuristic this replaced (``test_mapper``, retired by
BDL-074 C2 once its last caller read the binding) matched names,
folders and imports, gave 532 mutmut copies to nodes and the root node 882 files
(measured on this repository, 2026-09-27).

Pure: every function takes the paths it reasons about. What a test file holds is
read by :mod:`.test_file_reader`; the walk and the storage live in the reindex.
"""

# beadloom:domain=context-oracle
# beadloom:feature=test-mapping

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

# The placement vocabulary is defined below both of its readers — this module, which
# assigns a placement, and the rule engine's `test_binding`, which judges it — and
# re-exported here under its old names (BDL-074 C3).
from beadloom.context_oracle.test_layout import MIRRORED_KINDS as MIRRORED_KINDS
from beadloom.context_oracle.test_layout import TestLayout
from beadloom.infrastructure.repository import (
    KIND_ACCEPTANCE,
    KIND_SELF_CHECK,
    label_test_kind,
    most_specific_owner,
)
from beadloom.infrastructure.repository import PLACEMENT_BESIDE_CODE as PLACEMENT_BESIDE_CODE
from beadloom.infrastructure.repository import PLACEMENT_MIRROR as PLACEMENT_MIRROR
from beadloom.infrastructure.repository import PLACEMENT_OTHER_KIND as PLACEMENT_OTHER_KIND
from beadloom.infrastructure.repository import PLACEMENT_OVERRIDE as PLACEMENT_OVERRIDE
from beadloom.infrastructure.repository import PLACEMENT_UNOWNED as PLACEMENT_UNOWNED
from beadloom.infrastructure.repository import PLACEMENT_UNPLACED as PLACEMENT_UNPLACED

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Mapping

    from beadloom.infrastructure.repository import RecordedTestLayout

#: The folder a project's tests live under by default, relative to its root.
TEST_ROOT = "tests"

#: Kinds laid out by folder whose binding is not the mirror: acceptance scenarios
#: bind by their ``@node:`` tag and self-checks test the repository itself.
OTHER_KINDS = frozenset({KIND_ACCEPTANCE, KIND_SELF_CHECK})

#: The framework stated when a project has no test file at all.
FRAMEWORK_NONE = "none"
#: How the frameworks of several test files are joined into one name.
_FRAMEWORK_JOIN = "+"

_DEFAULT_LAYOUT = TestLayout()

_PY_SUFFIX = ".py"
#: The test affixes a language's convention puts on a class or file name, longest
#: first so ``TestCase`` is taken off before ``Test``.
_TEST_AFFIXES = {
    ".java": ("TestCase", "ITCase", "Tests", "Test", "IT"),
    ".kt": ("Tests", "Test"),
    ".swift": ("Tests",),
}
#: SwiftPM names a test target after the target it tests, plus this suffix.
_TEST_TARGET_SUFFIX = "Tests"
_PACKAGE_MARKER = "__init__.py"
_TEST_PREFIX = "test_"
_TEST_SUFFIX = "_test"

#: More bound files than this reads as ``high`` coverage; the thresholds are the
#: ones the heuristic used, kept so a consumer's reading of the label is unchanged.
_HIGH_COVERAGE_FILES = 3


@dataclass(frozen=True)
class BoundTestFile:
    """One test file: its kind folder, the node it binds to and how it was placed."""

    path: str
    kind: str | None
    ref_id: str | None
    placement: str


def is_test_file(path: str) -> bool:
    """Whether a file *path* (or a bare name) is a test under the default layout's patterns."""
    return _DEFAULT_LAYOUT.is_test_file(path)


def name_frameworks(frameworks: Iterable[str]) -> str:
    """One framework name for a set of them — ``go_test+pytest`` — or ``none``."""
    return _FRAMEWORK_JOIN.join(sorted(set(frameworks))) or FRAMEWORK_NONE


def bind_test_file(
    path: str,
    *,
    code_files: Collection[str],
    scan_paths: Iterable[str],
    node_sources: Iterable[tuple[str, str]],
    overrides: Iterable[tuple[str, str]],
    layout: TestLayout = _DEFAULT_LAYOUT,
) -> BoundTestFile:
    """Bind the test file at *path* (relative to the project root) to a node.

    *code_files* are the project's indexed code paths, *node_sources* and
    *overrides* ``(ref_id, source-or-prefix)`` pairs, *layout* the project's test
    layout. The declaration wins; then, under a root, the mirror for a mirrored
    kind; outside every root, the node whose source covers the file, when the
    layout reads tests beside the code; everything else binds to nothing and
    says why.
    """
    located = layout.locate(path)
    kind, under_kind = located if located is not None else (None, "")
    declared = most_specific_owner(overrides, path)
    if declared is not None:
        return BoundTestFile(path, kind, declared, PLACEMENT_OVERRIDE)
    tree = layout.mirror_of(path)
    if tree is not None:
        _, code_root, below = tree
        target = tree_mirrored_code_path(code_root, below, code_files=code_files)
        owner = most_specific_owner(node_sources, target) if target is not None else None
        return BoundTestFile(
            path, None, owner, PLACEMENT_MIRROR if owner is not None else PLACEMENT_UNOWNED
        )
    if located is None:
        return _beside_code(path, node_sources, layout)
    if kind is None:
        return BoundTestFile(path, None, None, PLACEMENT_UNPLACED)
    if kind not in MIRRORED_KINDS:
        return BoundTestFile(path, kind, None, PLACEMENT_OTHER_KIND)
    mirrored = mirrored_code_path(under_kind, code_files=code_files, scan_paths=scan_paths)
    owner = most_specific_owner(node_sources, mirrored) if mirrored is not None else None
    if owner is None:
        return BoundTestFile(path, kind, None, PLACEMENT_UNOWNED)
    return BoundTestFile(path, kind, owner, PLACEMENT_MIRROR)


def _beside_code(
    path: str, node_sources: Iterable[tuple[str, str]], layout: TestLayout
) -> BoundTestFile:
    """A file outside every root: the node its source covers, if the layout reads it."""
    owner = most_specific_owner(node_sources, path) if layout.beside_code else None
    if owner is None:
        return BoundTestFile(path, None, None, PLACEMENT_UNPLACED)
    return BoundTestFile(path, None, owner, PLACEMENT_BESIDE_CODE)


def mirrored_code_path(
    under_kind: str,
    *,
    code_files: Collection[str],
    scan_paths: Iterable[str],
) -> str | None:
    """The code path a test file's path beneath its kind folder names, or ``None``.

    ``graph/rules/test_layers.py`` names ``<root>graph/rules/layers.py`` when
    ``<root>graph/rules/`` holds code, and ``<root>graph/rules.py`` when that
    module exists instead. The roots are each scan path and each package directly
    beneath one; when several roots hold the mirrored folder the deepest wins, and
    two equally deep roots are a question the path cannot answer.
    """
    posix = PurePosixPath(under_kind)
    folder = "" if str(posix.parent) == "." else f"{posix.parent}/"
    module = f"{_module_stem(posix.name)}{_PY_SUFFIX}"
    code_dirs = _directories_holding(code_files)
    found: dict[int, set[str]] = {}
    for root in _code_roots(scan_paths, code_files):
        target = _resolve_in_root(root, folder, module, code_files, code_dirs)
        if target is not None:
            found.setdefault(len(root), set()).add(target)
    if not found:
        return None
    deepest = found[max(found)]
    return next(iter(deepest)) if len(deepest) == 1 else None


def _resolve_in_root(
    root: str,
    folder: str,
    module: str,
    code_files: Collection[str],
    code_dirs: Collection[str],
) -> str | None:
    """The code path *folder* + *module* names under *root*, if the root holds it."""
    directory = f"{root}{folder}"
    if not folder or directory in code_dirs:
        return f"{directory}{module}"
    as_module = f"{root}{folder.rstrip('/')}{_PY_SUFFIX}"
    return as_module if as_module in code_files else None


def tree_mirrored_code_path(
    code_root: str, below: str, *, code_files: Collection[str]
) -> str | None:
    """The code path a file *below* a build tool's test tree names in *code_root*.

    The file names ``<code_root>/<folders>/<subject><suffix>`` when that file
    exists, the ``<subject>/`` folder when that holds code instead, and the same
    file path when only its folder holds code — the folder's owner owns it.
    ``None`` when the mirrored folder holds no code.
    """
    posix = PurePosixPath(below)
    folders = list(posix.parts[:-1])
    code_dirs = _directories_holding(code_files)
    if folders and folders[0].endswith(_TEST_TARGET_SUFFIX):
        target = folders[0][: -len(_TEST_TARGET_SUFFIX)]
        if target and f"{code_root}/{target}/" in code_dirs:
            folders[0] = target
    directory = f"{code_root}/{''.join(f'{folder}/' for folder in folders)}"
    subject = _subject_stem(posix.name)
    as_file = f"{directory}{subject}{posix.suffix}"
    if as_file in code_files:
        return as_file
    if f"{directory}{subject}/" in code_dirs:
        return f"{directory}{subject}/"
    return as_file if directory in code_dirs else None


def _subject_stem(file_name: str) -> str:
    """``BillingTest.java`` and ``BillingTests.swift`` name ``Billing``."""
    posix = PurePosixPath(file_name)
    for affix in _TEST_AFFIXES.get(posix.suffix, ()):
        if posix.stem.endswith(affix) and len(posix.stem) > len(affix):
            return posix.stem[: -len(affix)]
    return _module_stem(file_name)


def _module_stem(file_name: str) -> str:
    """``test_loader.py`` and ``loader_test.py`` both name ``loader``."""
    stem = PurePosixPath(file_name).stem
    if stem.startswith(_TEST_PREFIX):
        return stem[len(_TEST_PREFIX) :]
    if stem.endswith(_TEST_SUFFIX):
        return stem[: -len(_TEST_SUFFIX)]
    return stem


def _code_roots(scan_paths: Iterable[str], code_files: Collection[str]) -> list[str]:
    """Each scan path as a prefix, and each package directly beneath one."""
    roots: list[str] = []
    for scan_path in scan_paths:
        cleaned = scan_path.strip().strip("/")
        root = "" if cleaned in ("", ".") else f"{cleaned}/"
        roots.append(root)
        for code_file in code_files:
            if not code_file.startswith(root):
                continue
            rest = PurePosixPath(code_file[len(root) :]).parts
            if len(rest) == 2 and rest[1] == _PACKAGE_MARKER:
                roots.append(f"{root}{rest[0]}/")
    return sorted(set(roots))


def _directories_holding(code_files: Collection[str]) -> frozenset[str]:
    """Every directory, as ``a/b/``, that holds a code file at any depth."""
    directories: set[str] = set()
    for code_file in code_files:
        parts = PurePosixPath(code_file).parts[:-1]
        for depth in range(1, len(parts) + 1):
            directories.add("/".join(parts[:depth]) + "/")
    return frozenset(directories)


def union_over_descendants(
    direct: Mapping[str, Collection[str]],
    parent_children: Mapping[str, Iterable[str]],
) -> dict[str, frozenset[str]]:
    """Each node's own files united with every descendant's, each file once.

    The union, not the sum: a file reached through two children is one file,
    which is what gave the root node 882 files under the heuristic's sum.
    """
    union: dict[str, frozenset[str]] = {}

    def collect(ref_id: str, visiting: frozenset[str]) -> frozenset[str]:
        if ref_id in union:
            return union[ref_id]
        files: set[str] = set(direct.get(ref_id, ()))
        for child in parent_children.get(ref_id, ()):
            if child not in visiting:
                files |= collect(child, visiting | {ref_id})
        result = frozenset(files)
        if not visiting:
            union[ref_id] = result
        return result

    for ref_id in {*direct, *parent_children}:
        union[ref_id] = collect(ref_id, frozenset())
    return union


def estimate_coverage(file_count: int, *, framework_detected: bool) -> str:
    """``high`` / ``medium`` / ``low`` / ``none`` from how many files are bound."""
    if file_count > _HIGH_COVERAGE_FILES:
        return "high"
    if file_count >= 1:
        return "medium"
    return "low" if framework_detected else "none"


def describe_unplaced(
    counts: Mapping[str, int], layout: RecordedTestLayout | None = None
) -> str | None:
    """The share of a project's test files that bind to nothing because of where they are.

    *counts* are test files by placement, *layout* the test layout the index
    recorded. ``None`` when no file is unplaced: then a node with no bound test has
    none, and there is nothing to qualify. Otherwise a reader of any per-node count
    must be told the count can be short — which ``ctx`` and the debt report both
    say, in this one sentence. It names the mirrored folders of the recorded roots,
    and, when tests beside the code are read, that no node's source holds the file;
    with no recorded layout it names the default folders.
    """
    unplaced = counts.get(PLACEMENT_UNPLACED, 0)
    if not unplaced:
        return None
    if layout is None:
        prefixes = [f"{TEST_ROOT}/{kind}/" for kind in MIRRORED_KINDS]
    else:
        prefixes = [p for kind in MIRRORED_KINDS for p in layout.kind_prefixes.get(kind, ())]
        prefixes += [f"{root}/" for root in layout.mirror_roots]
    beside = ", nor inside a node's source" if layout is not None and layout.beside_code else ""
    return (
        f"{unplaced} of {sum(counts.values())} test file(s) are unplaced "
        f"(not under {_either(sorted(prefixes))}{beside}) and bind to no node"
    )


def _either(items: list[str]) -> str:
    """``a``, ``a or b``, ``a, b or c``."""
    return " or ".join(items) if len(items) < 3 else f"{', '.join(items[:-1])} or {items[-1]}"


def describe_test_file_recognition(layout: RecordedTestLayout) -> str:
    """What makes a file a test file this project's index reads, in one clause.

    A file no pattern matches, or one outside every root, every test tree and
    every node's source, is not read at all, so a count of test files is a count
    of the files this clause names. ``ctx`` and the debt report state it every
    time (``beadloom-2mj3.15``), not only when the count is zero (review
    ``beadloom-b9ll`` M3): "all 1 test file(s) placed" read as "every test file"
    on a project whose Jest ``__tests__/`` files were not read (M-new-1). It
    names each group's patterns; a record written before they were recorded
    names the groups alone.
    """
    groups = (
        [f"{name} ({', '.join(group)})" for name, group in sorted(layout.patterns)]
        if layout.patterns
        else sorted(layout.frameworks)
    )
    all_roots = (*layout.roots, *layout.mirror_roots)
    roots = ", ".join(all_roots)
    where = f"the root {roots}" if len(all_roots) == 1 else f"the roots {roots}"
    beside = " or beside a node's code" if layout.beside_code else ""
    return (
        f"a test file is read when its path matches a pattern of {_either(groups)} "
        f"under {where}{beside}"
    )


def describe_unbound(
    counts: Mapping[str, int],
    kinds: Mapping[str, int],
    layout: RecordedTestLayout | None = None,
) -> str | None:
    """Every test file bound to no node, stated by why — ``None`` when there is none.

    *counts* are test files by placement, *kinds* the ``other_kind`` files by their
    recorded kind, *layout* the test layout the index recorded. The unplaced share
    is :func:`describe_unplaced`'s sentence over that layout, the one ``ctx`` and
    the debt report state, so a surface that also shows the other reasons states
    the same number and the same folders for "unplaced" (BDL-074 F1; review
    ``beadloom-b9ll`` m-new-2): the unowned files and each kind are named beside it
    by their own count, never folded into it.
    """
    parts = [part for part in (describe_unplaced(counts, layout),) if part is not None]
    unowned = counts.get(PLACEMENT_UNOWNED, 0)
    if unowned:
        parts.append(f"{unowned} unowned (under a mirrored folder whose code no node owns)")
    if kinds:
        named = " and ".join(
            f"{count} {label_test_kind(kind)}" for kind, count in sorted(kinds.items())
        )
        parts.append(f"{named} file(s) bind to no node by their kind")
    return "; ".join(parts) or None


def summarize_tests(
    files: Collection[str], counts: Mapping[str, int], *, framework: str
) -> dict[str, object]:
    """A node's tests in the four-key shape every ``extra["tests"]`` reader expects."""
    return {
        "framework": framework,
        "test_files": sorted(files),
        "test_count": sum(counts.get(path, 0) for path in files),
        "coverage_estimate": estimate_coverage(
            len(files), framework_detected=framework != FRAMEWORK_NONE
        ),
    }
