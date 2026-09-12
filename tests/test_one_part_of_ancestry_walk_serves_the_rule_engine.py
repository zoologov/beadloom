"""One `part_of` ancestry walk is reachable from `graph/rules/`, and no layer tag is written down.

BDL-070 A1 (`beadloom-e64o`). The epic exists because three bodies answered "what
layer is this node in" and disagreed, so a fourth body — a shared lookup that
climbed `part_of` on its own beside `import_resolver._part_of_ancestors` — would
have added a disagreement while claiming to remove one. Both properties are
derived from the source here rather than asserted in a review comment.

**What "a walk" means, stated because the derivation depends on it.** A function
is an ancestry walk when it is ABOUT `part_of` — its name says so, or one of its
string constants is the edge kind — and it is TRANSITIVE: it holds a `while`
loop, calls itself, or calls a function defined inside it. A body that reads the
`part_of` rows out of SQLite and hands them to someone else is not a walk by this
definition, and that is the shape `_part_of_ancestors` was left in.

**What the derivations cannot see.** The import walk follows `import` and
`from ... import` by name, so a module reached through `importlib` or an alias is
outside it. The literal scan compares whole string constants, so a tag assembled
from pieces (`"layer-" + name`) is outside it. Both are stated rather than
denied — this is a guard, not a proof.
"""

from __future__ import annotations

import ast
from pathlib import Path

import yaml

from beadloom.application.source_derivation.source_tree import (
    functions_in,
    module_tree,
    python_files,
)

SRC = Path(__file__).resolve().parents[1] / "src"
PACKAGE = SRC / "beadloom"
RULES_YML = Path(__file__).resolve().parents[1] / ".beadloom" / "_graph" / "rules.yml"

#: The one walk. Named here so a failure says which body is supposed to survive.
THE_WALK = "beadloom/graph/rules/layers.py::part_of_generations"

#: Files still holding a layer tag as a literal, each with the bead that removes
#: it. Compared for EQUALITY, so a stale entry fails as loudly as a new literal:
#: an exemption that outlives its reason is how the next `_LAYER_TAGS` gets in.
LITERAL_EXEMPTIONS = {
    # `_LAYER_TAGS` / `_LAYER_RANK` — removed by BDL-070 A5 (`beadloom-06dz`),
    # which brings `architecture_view` onto the shared lookup.
    "beadloom/application/architecture_view.py",
}

PART_OF = "part_of"


def _declared_layer_tags() -> set[str]:
    """Every layer tag this project DECLARES, read from the declaration."""
    document = yaml.safe_load(RULES_YML.read_text(encoding="utf-8"))
    tags = set(document.get("tags") or {})
    for rule in document.get("rules") or []:
        for layer in (rule.get("layers") or []) if isinstance(rule, dict) else []:
            tags.add(str(layer["tag"]))
    return tags


def _module_name(path: Path) -> str:
    relative = path.relative_to(SRC).with_suffix("")
    parts = relative.parts[:-1] if relative.name == "__init__" else relative.parts
    return ".".join(parts)


def _imported_modules(tree: ast.Module) -> set[str]:
    """Module names the file imports, in both `import x` and `from x import y` form."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module)
            names.update(f"{node.module}.{alias.name}" for alias in node.names)
    return {name for name in names if name.startswith("beadloom")}


def _modules_reachable_from(start: Path) -> dict[str, Path]:
    """Every beadloom module a file under *start* can reach by importing.

    A package's `__init__` travels with any module inside it, because importing
    `beadloom.graph.loader` executes `beadloom/graph/__init__.py` — which is how
    `import_resolver` is reachable from `graph/rules/` without any file there
    naming it.
    """
    by_name = {_module_name(path): path for path in python_files(PACKAGE)}

    def with_packages(name: str) -> set[str]:
        parts = name.split(".")
        return {".".join(parts[:depth]) for depth in range(1, len(parts) + 1)}

    frontier = {_module_name(path) for path in python_files(start)}
    reached: dict[str, Path] = {}
    while frontier:
        name = frontier.pop()
        for candidate in with_packages(name):
            path = by_name.get(candidate)
            if path is None or candidate in reached:
                continue
            reached[candidate] = path
            frontier |= _imported_modules(module_tree(path))
    return reached


def _is_transitive(function: ast.AST) -> bool:
    """True when the body climbs further than one step: a loop or a recursion."""
    if any(isinstance(node, ast.While) for node in ast.walk(function)):
        return True
    defined = {
        node.name
        for node in ast.walk(function)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    }
    called = {
        node.func.id
        for node in ast.walk(function)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    return bool(defined & called)


def _names_part_of(function: ast.AST, name: str) -> bool:
    if PART_OF in name:
        return True
    return any(
        isinstance(node, ast.Constant) and node.value == PART_OF for node in ast.walk(function)
    )


def _ancestry_walks_in(paths: dict[str, Path]) -> set[str]:
    walks: set[str] = set()
    for path in sorted(paths.values()):
        for function in functions_in(module_tree(path)):
            if _names_part_of(function, function.name) and _is_transitive(function):
                walks.add(f"{path.relative_to(SRC)}::{function.name}")
    return walks


class TestOneWalk:
    """The shared lookup replaces an ancestry walk; it does not add one."""

    def test_the_rule_engine_reaches_exactly_one_part_of_ancestry_walk(self) -> None:
        reachable = _modules_reachable_from(PACKAGE / "graph" / "rules")
        assert _ancestry_walks_in(reachable) == {THE_WALK}

    def test_the_import_resolver_is_in_the_population_this_asserts_over(self) -> None:
        """Without this, the assertion above could pass by reaching nothing."""
        reachable = _modules_reachable_from(PACKAGE / "graph" / "rules")
        assert "beadloom.graph.import_resolver" in reachable
        assert "beadloom.graph.rules.layers" in reachable


class TestNoLayerTagIsWrittenDown:
    """A layer is whatever the declaration names one — in `src/`, nothing else."""

    def test_the_declaration_names_the_tags_this_scan_looks_for(self) -> None:
        assert _declared_layer_tags() == {
            "layer-service",
            "layer-application",
            "layer-domain",
            "layer-infra",
        }

    def test_no_module_holds_a_layer_tag_as_a_literal_outside_the_named_exemptions(
        self,
    ) -> None:
        declared = _declared_layer_tags()
        holders = {
            str(path.relative_to(SRC))
            for path in python_files(PACKAGE)
            for node in ast.walk(module_tree(path))
            if isinstance(node, ast.Constant) and node.value in declared
        }
        assert holders == LITERAL_EXEMPTIONS

    def test_the_shared_lookup_itself_holds_no_tag(self) -> None:
        source = (PACKAGE / "graph" / "rules" / "layers.py").read_text(encoding="utf-8")
        assert not any(tag in source for tag in _declared_layer_tags())
