"""Test file reader: the test functions and the imports one test file holds.

A Python file is parsed; a file in another language is counted by the one line
its tests are written in (BDL-074 G2), and its imports are not read. The forms
are the retired mapper's, so a Go or JS/TS count reads what it read on main:
``func Test...(`` for Go, an ``it(`` or ``test(`` call for JS/TS, ``@Test`` for
JUnit and ``func test...(`` for XCTest. Swift also counts a function Swift Testing
marks ``@Test`` (the form the Xcode 16 templates generate), once, whatever it is
named (``beadloom-2mj3.13``). A suffix with no form counts zero — a count this
reader cannot take is not guessed.

One ``ast`` parse answers both questions. Measured on this repository's 462 test
files on 2026-09-28: the tree-sitter import extractor the code index uses took
2.2 s for the imports alone, because it walks every token of every file; the
whole cold indexing step built on this reader, parse and resolution included,
took 0.87 s.

The import form is the code index's (``graph.import_resolver``), so a rule reads
test imports the way it reads code imports: ``import a.b`` records ``a.b``,
``from a.b import c`` records ``a.b``, and a relative import records nothing. One
difference, stated rather than copied: ``import a.b as c`` is recorded here,
where the tree-sitter extractor drops an aliased import.
"""

# beadloom:domain=context-oracle
# beadloom:feature=test-mapping

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

_TEST_FUNCTION_PREFIX = "test"
_TEST_CLASS_PREFIX = "Test"

_PYTHON_SUFFIX = ".py"

#: The line a test is written in, by the suffix of the file that holds it.
_GO_TEST = re.compile(r"^\s*func\s+Test\w*\s*\(", re.MULTILINE)
_JS_TEST = re.compile(r"(?:^|\s)(?:test|it)\s*\(", re.MULTILINE)
_JUNIT_TEST = re.compile(r"@Test\b")
_XCTEST_TEST = re.compile(
    r"(?:@Test\b[^\n]*\n?\s*func\s+\w+|^\s*func\s+test\w*)\s*\(", re.MULTILINE
)
_TEST_FORMS: dict[str, re.Pattern[str]] = {
    ".go": _GO_TEST,
    **dict.fromkeys((".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".vue"), _JS_TEST),
    ".java": _JUNIT_TEST,
    ".kt": _JUNIT_TEST,
    ".swift": _XCTEST_TEST,
}

#: The fields through which a statement holds further statements (a handler and a
#: match case are not statements, and hold them the same way).
_BLOCK_FIELDS = ("body", "orelse", "finalbody", "handlers", "cases")


@dataclass(frozen=True)
class TestFileContents:
    """What a test file holds: its test functions and its imports by line."""

    __test__ = False  # a product type, not a pytest test class

    test_count: int
    imports: tuple[tuple[int, str], ...]


def read_test_file(text: str, *, suffix: str = _PYTHON_SUFFIX) -> TestFileContents:
    """The tests *text* defines, and its absolute imports when it is Python.

    For Python (*suffix* ``.py``, the default): module-level ``test*`` functions
    and ``test*`` methods of ``Test*`` classes, sync or async, count. A
    parametrised function counts once: these are the functions a file defines,
    not the cases a run collects. Text that does not parse holds nothing. For
    another suffix, see the module docstring.
    """
    if suffix != _PYTHON_SUFFIX:
        form = _TEST_FORMS.get(suffix)
        return TestFileContents(
            test_count=len(form.findall(text)) if form is not None else 0, imports=()
        )
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return TestFileContents(test_count=0, imports=())
    return TestFileContents(test_count=_count_tests(tree), imports=_imports(tree))


def count_test_functions(text: str) -> int:
    """The number of test functions in *text*; see :func:`read_test_file`."""
    return read_test_file(text).test_count


def _count_tests(tree: ast.Module) -> int:
    count = 0
    for node in tree.body:
        if _is_test_function(node):
            count += 1
        elif isinstance(node, ast.ClassDef) and node.name.startswith(_TEST_CLASS_PREFIX):
            count += sum(1 for member in node.body if _is_test_function(member))
    return count


def _is_test_function(node: ast.stmt) -> bool:
    return isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith(
        _TEST_FUNCTION_PREFIX
    )


def _imports(tree: ast.Module) -> tuple[tuple[int, str], ...]:
    found: list[tuple[int, str]] = []
    for node in _statements(tree):
        if isinstance(node, ast.Import):
            found.extend((node.lineno, alias.name) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.append((node.lineno, node.module))
    return tuple(sorted(set(found)))


def _statements(tree: ast.Module) -> Iterator[ast.AST]:
    """Every statement, at any depth, without entering an expression.

    An import is always a statement, so the expressions — nine in ten of a test
    file's nodes — are never visited. ``ast.walk`` visits them all, which cost
    about three times the parse on this repository's suite.
    """
    stack: list[ast.AST] = list(tree.body)
    while stack:
        node = stack.pop()
        yield node
        for block in _BLOCK_FIELDS:
            children = getattr(node, block, None)
            if isinstance(children, list):
                stack.extend(child for child in children if isinstance(child, ast.AST))
