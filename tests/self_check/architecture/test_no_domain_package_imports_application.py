"""Self-checks of this repository's graph, rules and code structure (BDL-074 A3).

Moved out of ``tests/test_no_domain_package_imports_application.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from tests.test_no_domain_package_imports_application import (
    _is_within,
    imported_modules,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence


REPO_ROOT = Path(__file__).resolve().parents[3]


GRAPH_DIR = REPO_ROOT / ".beadloom" / "_graph"


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


def test_no_package_imports_a_layer_above_it() -> None:
    """No file under a layer's ``source:`` imports a package of a higher layer."""
    tags = declared_layer_tags()
    offenders = upward_imports(tags, sources_by_layer_tag(tags))
    assert not offenders, (
        "an import runs against the declared layer direction "
        f"({' -> '.join(tags)}):\n{_describe(offenders)}"
    )
