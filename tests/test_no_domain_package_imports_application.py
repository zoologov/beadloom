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

from tests.support.module_imports import imported_modules, is_within


class TestTheInstrumentItself:
    """A scanner that reaches nothing passes vacuously, so it is measured first."""


    def test_a_function_local_import_is_seen(self) -> None:
        """The shape both removed instances had: an import inside a function body."""
        source = "def f():\n    from beadloom.application.reindex import reindex\n"
        assert imported_modules(source) == [(2, "beadloom.application.reindex")]

    def test_a_module_whose_name_merely_starts_alike_is_not_an_offender(self) -> None:
        """``beadloom.applications`` is not inside ``beadloom.application``."""
        assert not is_within("beadloom.applications", "beadloom.application")
        assert is_within("beadloom.application.reindex", "beadloom.application")


