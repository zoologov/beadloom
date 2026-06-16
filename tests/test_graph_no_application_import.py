# beadloom:domain=graph
"""Architectural invariant: the ``graph`` domain must not import ``application``.

BDL-059 S3 (.11) — the layering inversion fix. ``graph`` is a domain layer and
``application`` sits above it; a domain reaching UP into application violates the
DDD dependency rule (``architecture-layers``).  Historically ``graph/linter.py``
and ``graph/import_resolver.py`` worked around this with *function-local* imports
of ``beadloom.application.reindex`` — invisible to the static import scanner, so
``lint --strict`` stayed green while the inversion lived on.

This test pins the invariant at the SOURCE level (AST scan), catching both
module-level and function-local imports, so the workaround cannot creep back.
"""

from __future__ import annotations

import ast
from pathlib import Path

import beadloom.graph as graph_pkg

_GRAPH_DIR = Path(graph_pkg.__file__).parent


def _import_targets(tree: ast.AST) -> list[str]:
    """Collect every imported module path in an AST (module-level + nested)."""
    targets: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            targets.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            targets.append(node.module)
    return targets


def test_graph_package_does_not_import_application() -> None:
    """No module under ``graph/`` imports ``beadloom.application`` (any depth)."""
    offenders: list[str] = []
    for py_file in sorted(_GRAPH_DIR.rglob("*.py")):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for target in _import_targets(tree):
            if target == "beadloom.application" or target.startswith("beadloom.application."):
                offenders.append(f"{py_file.name}: imports {target}")

    assert not offenders, (
        "graph domain must not import application (layering inversion):\n"
        + "\n".join(offenders)
    )
