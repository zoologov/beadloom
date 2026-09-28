"""Every module a Python source imports, and whether a module lies within a package."""

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


def is_within(module: str, package: str) -> bool:
    return module == package or module.startswith(package + ".")
