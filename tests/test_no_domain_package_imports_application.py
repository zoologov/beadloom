# beadloom:domain=graph
"""Architectural invariant: no package imports one that the declaration puts above it.

BDL-059 S3 (`.11`) pinned one instance of this at the source level — the ``graph``
domain reaching up into ``application`` through *function-local* imports, which
were then invisible to the static import scanner, so ``lint --strict`` stayed
green while the inversion lived on. That test named ``graph`` and
``beadloom.application`` as two literals, so it could only ever catch the one
pair it was written for. BDL-070 `beadloom-46am` found the second pair by
measuring the graph instead of by reading this file:
``onboarding/scanner/init_flow.py`` imported ``beadloom.application.reindex``
twice, and it was the only reverse-direction edge of the 357 that inheritance
judges on this repository.

**Nothing here is written down.** The layer ORDER comes from the ``layers:``
rule in ``.beadloom/_graph/rules.yml`` and the membership from each node's own
``tags:`` and ``source:`` in its graph file, so a project whose layers are
declared ``tier-web`` / ``tier-core`` is checked the same way and this file does
not have to be edited when a layer, a package or a node is added.

Why a test and not the layer rule alone: the rule judges *nodes* and the edges
between them, and it does not run in the unit suite. This reads the source, so a
new upward import fails on the developer's machine at the moment it is written,
and it names the file and the line rather than the pair of nodes.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
GRAPH_DIR = REPO_ROOT / ".beadloom" / "_graph"


def imported_modules(source: str, filename: str = "<test>") -> list[tuple[int, str]]:
    """Every module path imported anywhere in *source*, with its line number.

    ``ast.walk`` rather than a pass over the module body, because the imports
    this catches are function-local: both of the two it was written for sit
    inside a function, and so did the two BDL-059 S3 removed.
    """
    found: list[tuple[int, str]] = []
    for node in ast.walk(ast.parse(source, filename=filename)):
        if isinstance(node, ast.Import):
            found.extend((node.lineno, alias.name) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None and node.level == 0:
            found.append((node.lineno, node.module))
    return found


def declared_layer_tags() -> list[str]:
    """The layer tags the rules file declares, topmost first."""
    rules = yaml.safe_load((GRAPH_DIR / "rules.yml").read_text(encoding="utf-8"))
    layered = [rule for rule in rules["rules"] if "layers" in rule]
    assert len(layered) == 1, f"expected one layered rule, found {len(layered)}"
    return [layer["tag"] for layer in layered[0]["layers"]]


def sources_by_layer_tag(tags: Sequence[str]) -> dict[str, list[str]]:
    """Each layer tag's ``source:`` paths, read off the nodes that carry it."""
    by_tag: dict[str, list[str]] = {tag: [] for tag in tags}
    for graph_file in sorted(GRAPH_DIR.glob("*.yml")):
        document = yaml.safe_load(graph_file.read_text(encoding="utf-8")) or {}
        for node in document.get("nodes") or []:
            source = node.get("source")
            if not source:
                continue
            for tag in node.get("tags") or ():
                if tag in by_tag:
                    by_tag[tag].append(source)
    return by_tag


def _module_path(source: str) -> str | None:
    """``src/beadloom/graph/`` -> ``beadloom.graph``; ``None`` for a non-Python source."""
    relative = source.strip("/")
    if not relative.startswith("src/"):
        return None
    return relative[len("src/") :].removesuffix(".py").replace("/", ".")


def _python_files(source: str) -> list[Path]:
    """Every ``.py`` file under a node's ``source:``, whether it names a file or a directory."""
    path = REPO_ROOT / source
    if path.is_dir():
        return sorted(path.rglob("*.py"))
    return [path] if path.suffix == ".py" and path.is_file() else []


def _is_within(module: str, package: str) -> bool:
    return module == package or module.startswith(package + ".")


def upward_imports(
    tags: Sequence[str], by_tag: dict[str, list[str]]
) -> list[tuple[str, int, str]]:
    """Every import from a lower layer into a package of a layer above it."""
    offenders: list[tuple[str, int, str]] = []
    for index, tag in enumerate(tags):
        above = [
            module
            for higher in tags[:index]
            for module in (_module_path(source) for source in by_tag[higher])
            if module is not None
        ]
        if not above:
            continue
        for source in by_tag[tag]:
            for py_file in _python_files(source):
                text = py_file.read_text(encoding="utf-8")
                for lineno, module in imported_modules(text, filename=str(py_file)):
                    if any(_is_within(module, package) for package in above):
                        offenders.append((str(py_file.relative_to(REPO_ROOT)), lineno, module))
    return offenders


def _describe(offenders: Iterable[tuple[str, int, str]]) -> str:
    return "\n".join(f"  {path}:{lineno} imports {module}" for path, lineno, module in offenders)


class TestTheInstrumentItself:
    """A scanner that reaches nothing passes vacuously, so it is measured first."""

    def test_the_declaration_names_at_least_two_layers(self) -> None:
        """With one layer there is no direction for an import to violate."""
        assert len(declared_layer_tags()) >= 2

    def test_every_declared_layer_holds_at_least_one_python_file(self) -> None:
        """A layer whose sources resolve to nothing would be checked in name only."""
        tags = declared_layer_tags()
        by_tag = sources_by_layer_tag(tags)
        empty = [
            tag
            for tag in tags
            if not any(_python_files(source) for source in by_tag[tag])
        ]
        assert not empty, f"declared layers with no Python file under any source: {empty}"

    def test_a_function_local_import_is_seen(self) -> None:
        """The shape both removed instances had: an import inside a function body."""
        source = "def f():\n    from beadloom.application.reindex import reindex\n"
        assert imported_modules(source) == [(2, "beadloom.application.reindex")]

    def test_a_module_whose_name_merely_starts_alike_is_not_an_offender(self) -> None:
        """``beadloom.applications`` is not inside ``beadloom.application``."""
        assert not _is_within("beadloom.applications", "beadloom.application")
        assert _is_within("beadloom.application.reindex", "beadloom.application")


def test_no_package_imports_a_layer_above_it() -> None:
    """No file under a layer's ``source:`` imports a package of a higher layer."""
    tags = declared_layer_tags()
    offenders = upward_imports(tags, sources_by_layer_tag(tags))
    assert not offenders, (
        "an import runs against the declared layer direction "
        f"({' -> '.join(tags)}):\n{_describe(offenders)}"
    )
