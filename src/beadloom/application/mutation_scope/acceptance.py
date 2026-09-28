# beadloom:domain=application
# beadloom:component=mutation-scope
"""The acceptance step files that run a node's scenarios (BDL-074 G1).

An acceptance step file binds to no node by its path: the scenarios it runs bind
through their ``@node:`` tags. So a change to a node's code selects the step files
whose loaded scenarios carry that node's tag, and no other — a step file is never
the fallback, because what it exercises can be read.

**What is read, and what is not guessed.** A step file is parsed as Python and
read for the LITERAL paths it hands to pytest-bdd's ``scenarios(...)`` (every
positional argument) or ``scenario(...)`` (the first). A path is resolved from the
step file's own folder — pytest-bdd's default — and a folder stands for every
``.feature`` beneath it. A computed path, a ``bdd_features_base_dir`` setting, a
step file that does not parse and a feature that cannot be read select nothing:
following them would be a guess, and a guess here would read as a binding. A
``scenario(...)`` binding is credited with every tag of its feature, which can
select a file a little more widely than the one scenario it runs, never less.
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

from beadloom.graph.scenarios import parse_feature

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from pathlib import Path

#: pytest-bdd's two loaders, and how many leading arguments of each name a feature.
_LOADERS = {"scenarios": None, "scenario": 1}

#: The suffix of a Gherkin file, which a folder argument stands for.
_FEATURE_SUFFIX = ".feature"


def acceptance_files_by_node(
    project_root: Path, step_files: Iterable[str]
) -> dict[str, tuple[str, ...]]:
    """Each node named by a loaded scenario's tag -> the step files that load it, by path."""
    by_node: dict[str, list[str]] = {}
    tags_of: dict[Path, frozenset[str]] = {}
    for step_file in sorted(step_files):
        nodes: set[str] = set()
        for feature in _loaded_features(project_root, step_file):
            if feature not in tags_of:
                tags_of[feature] = _node_tags(feature)
            nodes |= tags_of[feature]
        for node in nodes:
            by_node.setdefault(node, []).append(step_file)
    return {node: tuple(files) for node, files in sorted(by_node.items())}


def _loaded_features(project_root: Path, step_file: str) -> Iterator[Path]:
    """The feature files *step_file* hands to pytest-bdd by a literal path."""
    path = project_root / step_file
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=step_file)
    except (OSError, UnicodeDecodeError, SyntaxError, ValueError):
        return
    for literal in _literal_feature_paths(tree):
        target = path.parent / literal
        if target.is_dir():
            yield from sorted(target.rglob(f"*{_FEATURE_SUFFIX}"))
        elif target.is_file():
            yield target


def _literal_feature_paths(tree: ast.AST) -> Iterator[str]:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _called_name(node.func)
        if name not in _LOADERS:
            continue
        for argument in node.args[: _LOADERS[name]]:
            if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                yield argument.value


def _called_name(func: ast.expr) -> str | None:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _node_tags(feature: Path) -> frozenset[str]:
    try:
        text = feature.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return frozenset()
    scenarios, _unreadable = parse_feature(text, path=feature.as_posix())
    return frozenset(node for scenario in scenarios for node in scenario.nodes)
