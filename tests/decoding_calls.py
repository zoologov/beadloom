"""The AST shape of a call whose text a codec decides — one definition, two readers.

Two instruments in this suite ask questions about the same set of calls, and
they must not answer them from two private copies of "what a text-I/O call
looks like":

* :mod:`tests.test_locale_independent_io` asks *is the codec STATED* — the
  BDL-061.42 sweep, which fails the day a call site omits ``encoding=``;
* :mod:`tests.test_decode_handlers` asks *can this call RAISE, and is the
  handler around it as wide* — the BDL-061.68 ledger.

The questions differ (a ``write_text`` can pick the wrong codec but never
raises ``UnicodeDecodeError``; a ``read_text(errors="replace")`` states its
codec and cannot raise), so the two verdicts stay in their own modules. What
lives here is only what they share: how to read a call out of an AST and decide
what kind of I/O it is. BDL-061.40 extracted :mod:`tests.ambient_codec` for the
same reason — the epic's own finding is that one fact told twice drifts.
"""

from __future__ import annotations

import ast

#: ``pathlib`` text I/O whose codec is ``locale.getpreferredencoding(False)``
#: unless ``encoding=`` says otherwise.
TEXT_READWRITE = frozenset({"read_text", "write_text"})

#: ``subprocess`` entry points that decode the child's streams when asked for
#: text. ``PLW1514`` does not cover these — measured on ruff 0.16.3 — so this
#: leg belongs to the AST instruments and to no linter. The same measurement
#: found the other half of why these instruments stay: ``PLW1514`` reports
#: ``read_text`` only where it can infer a ``Path`` receiver, and nothing here
#: needs that inference.
SUBPROCESS_CALLS = frozenset({"run", "Popen", "check_output", "check_call", "call"})


def called_name(call: ast.Call) -> str | None:
    """``p.read_text()`` -> ``"read_text"``; ``open(p)`` -> ``"open"``."""
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    if isinstance(call.func, ast.Name):
        return call.func.id
    return None


def keyword(call: ast.Call, name: str) -> ast.expr | None:
    """The value passed as *name*, or ``None`` when the call does not pass it."""
    for kw in call.keywords:
        if kw.arg == name:
            return kw.value
    return None


def is_true(node: ast.expr | None) -> bool:
    """Whether *node* is the literal ``True`` (a variable reads as unknown)."""
    return isinstance(node, ast.Constant) and node.value is True


def open_mode(call: ast.Call) -> str:
    """The literal mode of an ``open()`` / ``Path.open()`` call ('r' when dynamic)."""
    mode = keyword(call, "mode")
    if mode is None:
        positional = 0 if isinstance(call.func, ast.Attribute) else 1
        if len(call.args) > positional:
            mode = call.args[positional]
    if isinstance(mode, ast.Constant) and isinstance(mode.value, str):
        return mode.value
    return "r"


def is_text_open(call: ast.Call) -> bool:
    """An ``open()`` in text mode — the one that decodes."""
    return called_name(call) == "open" and "b" not in open_mode(call)


def is_text_subprocess(call: ast.Call) -> bool:
    """A ``subprocess`` call that asks for decoded streams."""
    if called_name(call) not in SUBPROCESS_CALLS:
        return False
    return is_true(keyword(call, "text")) or is_true(keyword(call, "universal_newlines"))


def decoding_can_raise(call: ast.Call) -> bool:
    """Whether a decode failure in *call* surfaces as an exception.

    ``errors="replace"`` / ``"surrogateescape"`` / ``"ignore"`` answer the
    question at the call site: the read becomes total and no handler is needed.
    Only ``strict`` — stated or defaulted — can raise, and a ledger that lists
    the others asks for a judgement that has already been made.
    """
    errors = keyword(call, "errors")
    if errors is None:
        return True
    return isinstance(errors, ast.Constant) and errors.value == "strict"
