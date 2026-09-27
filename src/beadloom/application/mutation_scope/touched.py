# beadloom:domain=application
# beadloom:component=mutation-scope
"""Which lines a unified diff touched, and which functions those lines fall in (BDL-074 D1).

A mutation run per change mutates the functions a change touched, so the first
question is which ones those are. Both halves are pure: the diff is text and the
source is text, so neither reads the disk or the index.

**A function is what a runner mutates as a unit**: a top-level function, or a
method of a top-level class, named ``Class.method``. A function nested inside
another belongs to the outer one, because its body is part of the outer body and
has no mutants of its own. A decorator belongs to the function it decorates,
because changing it changes what the function does. A touched line inside no
function — a module constant, a class attribute — is COUNTED rather than
dropped, because no mutant of it exists and the report must say so.

Only Python is read. The declared scope defaults to Python (the scope checker's
languages), and a source that does not parse raises ``SyntaxError`` so the caller
can name the file rather than guess its functions.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

#: The new-side header of a file in a unified diff; ``/dev/null`` is a deletion.
_NEW_FILE = re.compile(r"^\+\+\+ (?:b/)?(?P<path>.+?)\s*$")

#: A hunk header. The new side is ``+start[,count]``; a count of 0 is a pure deletion.
_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(?P<start>\d+)(?:,(?P<count>\d+))? @@")

_DELETED = "/dev/null"

_FUNCTION_NODES = (ast.FunctionDef, ast.AsyncFunctionDef)


@dataclass(frozen=True)
class TouchedFunctions:
    """The functions a set of lines fell in, and how many lines fell in none."""

    functions: tuple[str, ...]
    outside: int


def changed_lines(diff_text: str) -> dict[str, frozenset[int]]:
    """The new-side lines each file's hunks touched, keyed by the path the diff names.

    Written for ``git diff --unified=0``: every hunk then holds only changed
    lines. A pure deletion (``+start,0``) touches line ``start``, the line the
    removed ones followed, because that is the position inside whatever held
    them. A deleted file names no line: there is nothing left to mutate.
    """
    lines: dict[str, set[int]] = {}
    current: str | None = None
    for line in diff_text.splitlines():
        header = _NEW_FILE.match(line)
        if header is not None:
            path = header.group("path").strip('"')
            current = None if path == _DELETED else path
            continue
        hunk = _HUNK.match(line)
        if hunk is None or current is None:
            continue
        lines.setdefault(current, set()).update(_hunk_lines(hunk))
    return {path: frozenset(touched) for path, touched in lines.items() if touched}


def _hunk_lines(hunk: re.Match[str]) -> range:
    start = int(hunk.group("start"))
    count = 1 if hunk.group("count") is None else int(hunk.group("count"))
    if count == 0:
        return range(max(start, 1), max(start, 1) + 1)
    return range(start, start + count)


def touched_functions(source: str, lines: Iterable[int]) -> TouchedFunctions:
    """The functions of *source* that *lines* fall in, once each, in source order.

    Raises ``SyntaxError`` when *source* does not parse.
    """
    spans = list(_function_spans(ast.parse(source)))
    wanted = set(lines)
    named: list[str] = []
    inside: set[int] = set()
    for name, first, last in spans:
        hit = {line for line in wanted if first <= line <= last}
        if hit:
            named.append(name)
            inside |= hit
    return TouchedFunctions(functions=tuple(named), outside=len(wanted - inside))


def _function_spans(module: ast.Module) -> Iterator[tuple[str, int, int]]:
    """``(name, first line, last line)`` of each unit a runner mutates, in order."""
    for node in module.body:
        if isinstance(node, _FUNCTION_NODES):
            yield node.name, _first_line(node), _last_line(node)
        elif isinstance(node, ast.ClassDef):
            for member in node.body:
                if isinstance(member, _FUNCTION_NODES):
                    yield f"{node.name}.{member.name}", _first_line(member), _last_line(member)


def _first_line(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    return min([node.lineno, *(decorator.lineno for decorator in node.decorator_list)])


def _last_line(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    return node.end_lineno if node.end_lineno is not None else node.lineno
