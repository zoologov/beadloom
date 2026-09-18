"""A directory shaped the way mutmut leaves the package it runs the suite in.

One responsibility: build, on disk, the thing a guard must decline to be fooled
by. It is a PROXY and says so — the only proof BDL-072 accepts is a dispatched
``Mutation`` run (bead ``beadloom-e8m4``). What this module buys is a red that
runs in three seconds instead of three hours.

**Every shape below was copied from output mutmut 3.7.0 actually produced**, on
2026-09-18, by calling its own ``write_all_mutants_to_file`` over
``src/beadloom/doc_sync/tables.py``. Three of them decide whether a guard is
fooled:

* the declared function KEEPS its name and its body and gains a decorator —
  ``@_mutmut_mutated(mutants_x_cells_of__mutmut)``. So a population derived from
  the copy still holds ``cells_of``, and a fix that dropped every name mutmut
  touched would lose it;
* beside it sit ``x_cells_of__mutmut_orig`` — a verbatim copy of the body — and
  ``x_cells_of__mutmut_1..N``, one per mutant. These are the names that arrived
  in the failing run's report (BDL-UX #289);
* the module gains a top-level ``mutants_x_cells_of__mutmut`` dict and one
  assignment per mutant.

mutmut is a dev dependency and is never imported here: this module writes text,
so the mimic builds in an environment that has no runner installed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

#: The import mutmut injects at the top of every module it mutates.
TRAMPOLINE_IMPORT = (
    "from mutmut.mutation.trampoline import wrap_in_trampoline as _mutmut_mutated, MutantDict"
)

#: One mutated module, spelled as mutmut spells it. Three of the four bodies here
#: split a line on a pipe, so a reader that does not decline the generated names
#: reports three sites where the package declares one — the failure this mimic
#: exists to reproduce.
_MUTATED_TABLES = (
    '''"""What a markdown table row is — the mimic of a mutated copy."""

import re

_ROW_RE = re.compile(r"^\\s*\\|(.*)\\|\\s*$")

'''
    + TRAMPOLINE_IMPORT
    + '''
mutants_x_cells_of__mutmut: MutantDict = {}  # type: ignore


@_mutmut_mutated(mutants_x_cells_of__mutmut)
def cells_of(line):
    """The declared body, which keeps its name under mutation."""
    match = _ROW_RE.match(line)
    if match is None:
        return None
    return [cell.strip() for cell in match.group(1).split("|")]


def x_cells_of__mutmut_orig(line):
    """mutmut's verbatim copy of the body above."""
    match = _ROW_RE.match(line)
    if match is None:
        return None
    return [cell.strip() for cell in match.group(1).split("|")]


def x_cells_of__mutmut_1(line):
    """A mutant of another expression: the pipe split survives it."""
    match = _ROW_RE.match(line)
    if match is not None:
        return None
    return [cell.strip() for cell in match.group(1).split("|")]


def x_cells_of__mutmut_2(line):
    """A mutant of the literal itself: the split is there, on another string."""
    match = _ROW_RE.match(line)
    if match is None:
        return None
    return [cell.strip() for cell in match.group(1).split("XX|XX")]


mutants_x_cells_of__mutmut['_mutmut_orig'] = x_cells_of__mutmut_orig  # type: ignore
mutants_x_cells_of__mutmut['x_cells_of__mutmut_1'] = x_cells_of__mutmut_1  # type: ignore
mutants_x_cells_of__mutmut['x_cells_of__mutmut_2'] = x_cells_of__mutmut_2  # type: ignore
'''
)

#: A mutated METHOD, which mutmut mangles with its own separator instead of an
#: underscore (``mutmut/mutation/trampoline_templates.py:1``). Held here so a
#: reader can see that the two spellings are one class of name.
_MUTATED_ROW = (
    '''"""A class whose method was mutated — the second name shape."""

'''
    + TRAMPOLINE_IMPORT
    + """
mutants_xǁRowǁcells__mutmut: MutantDict = {}  # type: ignore


class Row:
    @_mutmut_mutated(mutants_xǁRowǁcells__mutmut)
    def cells(self, line):
        return line.split("|")

    def xǁRowǁcells__mutmut_orig(self, line):
        return line.split("|")

    def xǁRowǁcells__mutmut_1(self, line):
        return line.split("|")
"""
)

#: What the mimic holds, as ``relative path -> source``. Named so a test can say
#: what it walked rather than count files it never listed.
MIMIC_MODULES: dict[str, str] = {
    "__init__.py": '"""The mimic package."""\n',
    "doc_sync/__init__.py": "",
    "doc_sync/tables.py": _MUTATED_TABLES,
    "doc_sync/row.py": _MUTATED_ROW,
}

#: The sites the mimic's package DECLARES, as ``(module path, enclosing
#: function)`` — the answer a guard must still give when it reads the copy.
DECLARED_SITES_IN_THE_MIMIC = (
    ("doc_sync/row.py", "cells"),
    ("doc_sync/tables.py", "cells_of"),
)

#: Every generated name the mimic carries, so a test can state the population it
#: proved the helper declines instead of asserting over an unnamed set.
GENERATED_NAMES_IN_THE_MIMIC = (
    "mutants_xǁRowǁcells__mutmut",
    "mutants_x_cells_of__mutmut",
    "xǁRowǁcells__mutmut_1",
    "xǁRowǁcells__mutmut_orig",
    "x_cells_of__mutmut_1",
    "x_cells_of__mutmut_2",
    "x_cells_of__mutmut_orig",
)


def write_mutmut_copy(root: Path) -> Path:
    """Write the mimic package under *root* and return the package directory.

    The directory is named ``beadloom`` so a path built from it reads like the
    one under ``mutants/src/`` that fooled the guard.
    """
    package = root / "beadloom"
    for relative, source in MIMIC_MODULES.items():
        path = package / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
    return package
