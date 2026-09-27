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


def _is_within(module: str, package: str) -> bool:
    return module == package or module.startswith(package + ".")


class TestTheInstrumentItself:
    """A scanner that reaches nothing passes vacuously, so it is measured first."""


    def test_a_function_local_import_is_seen(self) -> None:
        """The shape both removed instances had: an import inside a function body."""
        source = "def f():\n    from beadloom.application.reindex import reindex\n"
        assert imported_modules(source) == [(2, "beadloom.application.reindex")]

    def test_a_module_whose_name_merely_starts_alike_is_not_an_offender(self) -> None:
        """``beadloom.applications`` is not inside ``beadloom.application``."""
        assert not _is_within("beadloom.applications", "beadloom.application")
        assert _is_within("beadloom.application.reindex", "beadloom.application")


