"""Test binding: which graph node a test file belongs to, derived from where it lives.

A test file under ``tests/<kind>/`` for a mirrored kind (``unit``, ``integration``)
names a code path with the rest of its path: ``tests/unit/<path>/test_<name>.py``
names ``<package>/<path>/<name>.py``, and a folder named after a module
(``tests/unit/<path>/<module>/test_*.py``) names that module. The node that OWNS
that code path — the most specific node whose source covers it, by the one rule
``infrastructure.repository`` holds — is the node the test binds to. No file
declares anything; the fact is stated once, by where the file is.

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
from fnmatch import fnmatch
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

# The placement vocabulary is defined below both of its readers — this module, which
# assigns a placement, and the rule engine's `test_binding`, which judges it — and
# re-exported here under its old names (BDL-074 C3).
from beadloom.infrastructure.repository import PLACEMENT_MIRROR as PLACEMENT_MIRROR
from beadloom.infrastructure.repository import PLACEMENT_OTHER_KIND as PLACEMENT_OTHER_KIND
from beadloom.infrastructure.repository import PLACEMENT_OVERRIDE as PLACEMENT_OVERRIDE
from beadloom.infrastructure.repository import PLACEMENT_UNOWNED as PLACEMENT_UNOWNED
from beadloom.infrastructure.repository import PLACEMENT_UNPLACED as PLACEMENT_UNPLACED
from beadloom.infrastructure.repository import most_specific_owner

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Mapping

#: The folder a project's tests live under, relative to its root.
TEST_ROOT = "tests"

#: Kinds whose path under ``tests/<kind>/`` mirrors the code.
MIRRORED_KINDS = frozenset({"unit", "integration"})

#: Kinds laid out by folder whose binding is not the mirror: acceptance scenarios
#: bind by their ``@node:`` tag and self-checks test the repository itself.
OTHER_KINDS = frozenset({"acceptance", "self_check"})

#: The file names pytest collects by default.
TEST_FILE_PATTERNS = ("test_*.py", "*_test.py")


#: The framework every indexed test file is written for.
FRAMEWORK_PYTEST = "pytest"
#: The framework stated when a project has no test file at all.
FRAMEWORK_NONE = "none"

_PY_SUFFIX = ".py"
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


def is_test_file(name: str) -> bool:
    """Whether a file NAME is one pytest collects by default."""
    return any(fnmatch(name, pattern) for pattern in TEST_FILE_PATTERNS)


def bind_test_file(
    path: str,
    *,
    code_files: Collection[str],
    scan_paths: Iterable[str],
    node_sources: Iterable[tuple[str, str]],
    overrides: Iterable[tuple[str, str]],
) -> BoundTestFile:
    """Bind the test file at *path* (relative to the project root) to a node.

    *code_files* are the project's indexed code paths, *node_sources* and
    *overrides* ``(ref_id, source-or-prefix)`` pairs. The declaration wins; then
    the mirror, for a mirrored kind; everything else binds to nothing and says why.
    """
    kind, under_kind = _split_kind(path)
    declared = most_specific_owner(overrides, path)
    if declared is not None:
        return BoundTestFile(path, kind, declared, PLACEMENT_OVERRIDE)
    if kind is None:
        return BoundTestFile(path, None, None, PLACEMENT_UNPLACED)
    if kind not in MIRRORED_KINDS:
        return BoundTestFile(path, kind, None, PLACEMENT_OTHER_KIND)
    mirrored = mirrored_code_path(under_kind, code_files=code_files, scan_paths=scan_paths)
    owner = most_specific_owner(node_sources, mirrored) if mirrored is not None else None
    if owner is None:
        return BoundTestFile(path, kind, None, PLACEMENT_UNOWNED)
    return BoundTestFile(path, kind, owner, PLACEMENT_MIRROR)


def _split_kind(path: str) -> tuple[str | None, str]:
    """The kind folder of *path* and the path beneath it, or ``(None, "")``."""
    parts = PurePosixPath(path).parts
    if len(parts) < 3 or parts[0] != TEST_ROOT:
        return None, ""
    kind = parts[1]
    if kind not in MIRRORED_KINDS | OTHER_KINDS:
        return None, ""
    return kind, "/".join(parts[2:])


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


def describe_unplaced(counts: Mapping[str, int]) -> str | None:
    """The share of a project's test files that bind to nothing because of where they are.

    *counts* are test files by placement. ``None`` when no file is unplaced: then a
    node with no bound test has none, and there is nothing to qualify. Otherwise a
    reader of any per-node count must be told the count can be short — which ``ctx``
    and the debt report both say, in this one sentence.
    """
    unplaced = counts.get(PLACEMENT_UNPLACED, 0)
    if not unplaced:
        return None
    folders = " or ".join(f"{TEST_ROOT}/{kind}/" for kind in sorted(MIRRORED_KINDS))
    return (
        f"{unplaced} of {sum(counts.values())} test file(s) are unplaced "
        f"(not under {folders}) and bind to no node"
    )


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
