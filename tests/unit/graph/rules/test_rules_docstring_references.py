"""Every symbol a `graph/rules/` module docstring names must still exist.

BDL-062 `.11` (`beadloom-viaj.11`). The bead that produced this file found
`doc_area.py`'s module docstring still describing `_common_prefix`, the function
`.9` had deleted hours earlier when it replaced the unanimity rule with
`_source_root`. Two standing rules shape what is here, and they are cited by
name.

**UNCHECKED IS NOT CLEAN, AND THE CHECKER MUST SAY WHICH.** This check closes
exactly one half of that defect class and must not be read as closing the other.
It resolves references a docstring makes *by name* — ``_private`` symbols in
double backticks and ``:func:``/``:meth:``/``:attr:``/``:class:``/``:mod:``
roles. It cannot see a docstring that describes a deleted function in prose
without naming it, which is precisely the shape the `.11` defect had: the stale
text read "the longest directory prefix every node source shares" and never
wrote `_common_prefix` down. So this test was never red on the defect it was
written beside. It was proved to bite by injecting a dead reference, and that is
a weaker claim, stated here rather than left for a reader to assume.

**A GREEN COUNT IS NOT A CHECKED COUNT.** A regex that quietly stops matching
turns this file green over nothing, so the denominator is asserted too:
:func:`test_the_reference_sweep_checks_a_real_population` fails if the sweep
finds fewer references than the package is known to carry.
"""

from __future__ import annotations

import ast
import dataclasses
import importlib
import re
from pathlib import Path

import pytest

import beadloom.graph.rules as rules_package

#: A private symbol named in double backticks — ``_source_root``. Dunders are
#: excluded: in this package ``__init__`` names the module FILE, not a symbol.
PRIVATE_REFERENCE = re.compile(r"``(_(?!_)[A-Za-z0-9_]+)(?:\(\))?``")

#: A Sphinx-style cross-reference role, the other way this package names a symbol.
ROLE_REFERENCE = re.compile(r":(?:func|meth|attr|class|mod|data):`~?([^`]+)`")

#: The number of named references the package carried when this test was written
#: (32, measured over 11 modules). Asserted as a floor, so a regex that decays
#: cannot pass this file over an empty population.
KNOWN_REFERENCE_FLOOR = 30

RULES_DIR = Path(rules_package.__file__ or "").parent


def _rules_modules() -> list[Path]:
    """Every module of the rule-engine package, in a stable order."""
    return sorted(RULES_DIR.glob("*.py"))


def _module_docstring(path: Path) -> str | None:
    """The module docstring of *path*, or ``None`` when it has none."""
    return ast.get_docstring(ast.parse(path.read_text(encoding="utf-8")))


def _top_level_names(path: Path) -> set[str]:
    """Every name *path* binds at module level, including imports."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            names.update(t.id for t in node.targets if isinstance(t, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
        elif isinstance(node, ast.Import | ast.ImportFrom):
            names.update(alias.asname or alias.name.split(".")[0] for alias in node.names)
    return names


def _has_member(owner: object, name: str) -> bool:
    """Whether *owner* carries *name*, counting a dataclass field as present.

    ``hasattr`` alone is wrong here: a dataclass field declared with
    ``field(default_factory=...)`` leaves no class attribute behind, so
    ``FactSet.not_applicable`` — a real field :mod:`.summary_facts` legitimately
    cites — would be reported dead.
    """
    if hasattr(owner, name):
        return True
    if dataclasses.is_dataclass(owner):
        return any(f.name == name for f in dataclasses.fields(owner))
    return name in getattr(owner, "__annotations__", {})


def _resolve(reference: str, *, local_names: set[str]) -> bool:
    """Whether *reference* names something that exists.

    Three shapes occur in this package: a relative ``.sibling`` module, a dotted
    path into the codebase, and a bare name defined in the citing module.
    """
    reference = reference.strip().lstrip("~").removesuffix("()")
    if reference.startswith("."):
        return (RULES_DIR / f"{reference.lstrip('.')}.py").exists()

    parts = reference.split(".")
    for cut in range(len(parts), 0, -1):
        try:
            owner: object = importlib.import_module(".".join(parts[:cut]))
        except ImportError:
            continue
        for attribute in parts[cut:]:
            if not _has_member(owner, attribute):
                return False
            owner = getattr(owner, attribute, None)
            if owner is None:  # a dataclass field resolves but yields no object
                return True
        return True
    return parts[-1] in local_names


def _references(path: Path) -> list[str]:
    """Every symbol the module docstring of *path* names."""
    docstring = _module_docstring(path)
    if docstring is None:
        return []
    return [m.group(1) for m in PRIVATE_REFERENCE.finditer(docstring)] + [
        m.group(1) for m in ROLE_REFERENCE.finditer(docstring)
    ]


@pytest.mark.parametrize("module_path", _rules_modules(), ids=lambda p: p.name)
def test_module_docstring_names_no_symbol_that_no_longer_exists(module_path: Path) -> None:
    """A docstring that cites a deleted symbol is documentation that lies.

    `sync-check` structurally cannot catch this: a docstring is not a doc pair,
    it lives inside the very file whose hash defines the pair's freshness, and a
    file is always fresh with respect to itself. This test is the only thing
    standing between the package and that silence.
    """
    local_names = _top_level_names(module_path)
    dead = [
        reference
        for reference in _references(module_path)
        if not _resolve(reference, local_names=local_names)
    ]
    assert not dead, (
        f"{module_path.name} docstring names {dead}, which no longer exists — "
        f"update the prose or restore the symbol"
    )


def test_the_reference_sweep_checks_a_real_population() -> None:
    """The sweep must not go green by matching nothing.

    Without this, a change to either pattern turns every case above into a pass
    over an empty list, which is the green count that is not a checked count.
    """
    total = sum(len(_references(path)) for path in _rules_modules())
    assert total >= KNOWN_REFERENCE_FLOOR, (
        f"the docstring sweep found only {total} named references across "
        f"{len(_rules_modules())} modules, below the {KNOWN_REFERENCE_FLOOR} this "
        f"package is known to carry — the patterns have stopped matching"
    )
