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

#: Modules whose ``open()`` is a *container* rather than text I/O. Keying on the
#: attribute name alone reads ``tarfile.open(fileobj=...)`` as an unstated text
#: read, which it is not — it has no codec to state. Found by rooting the sweep
#: at ``tests/`` (``beadloom-0mdo.64``): ``src/beadloom`` happens to contain no
#: such call, so the blind spot was invisible while the only root was the
#: package. Receivers are matched by module NAME, so an aliased import reads as
#: unknown and stays in the population — the safe direction.
CONTAINER_OPENERS = frozenset({"tarfile", "zipfile", "gzip", "bz2", "lzma", "shelve", "dbm"})

#: Modules whose ``open()`` returns a FILE DESCRIPTOR rather than a stream.
#: ``os.open`` decodes nothing — it hands back an int, and whatever wraps that
#: int states its own codec — so it has no codec to state and no
#: ``UnicodeDecodeError`` to catch. Read as a text open it produces a false
#: positive in both instruments at once: the codec sweep asks for an
#: ``encoding=`` the call has no parameter for, and the handler ledger asks a
#: handler around it to catch a decode failure that cannot happen. Found by
#: ``beadloom-0mdo.66``, whose exclusive create (``O_CREAT | O_EXCL``) is the
#: first ``os.open`` in ``src/beadloom`` — the same way ``CONTAINER_OPENERS``
#: above was found, by a call this package had never made.
DESCRIPTOR_OPENERS = frozenset({"os"})

#: Where ``encoding`` sits when it is passed positionally. Nobody has to pass it
#: that way and five sites in this suite do (``read_text("utf-8")``), so a sweep
#: that reads keywords only reports call sites that already state their codec.
#: Index is into ``call.args`` and differs by receiver, hence two tables.
_ENCODING_ARG_INDEX_METHOD = {"read_text": 0, "write_text": 1, "open": 2}
_ENCODING_ARG_INDEX_FUNCTION = {"open": 3}


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


def states_encoding(call: ast.Call) -> bool:
    """Whether *call* names its codec — by keyword OR positionally.

    ``Path.read_text("utf-8")`` states its codec exactly as firmly as
    ``read_text(encoding="utf-8")`` does, and a guard that cannot see the
    positional form asks five correct sites in this suite to be edited.
    """
    if keyword(call, "encoding") is not None:
        return True
    name = called_name(call)
    if name is None:
        return False
    table = (
        _ENCODING_ARG_INDEX_METHOD
        if isinstance(call.func, ast.Attribute)
        else _ENCODING_ARG_INDEX_FUNCTION
    )
    index = table.get(name)
    return index is not None and len(call.args) > index


def _module_open(call: ast.Call, modules: frozenset[str]) -> bool:
    """``<module>.open(...)`` where ``<module>`` is one of *modules*.

    Receivers are matched by module NAME, so an aliased import reads as unknown
    and stays in the population — the safe direction.
    """
    return (
        called_name(call) == "open"
        and isinstance(call.func, ast.Attribute)
        and isinstance(call.func.value, ast.Name)
        and call.func.value.id in modules
    )


def is_container_open(call: ast.Call) -> bool:
    """``tarfile.open(...)`` and friends — an ``open`` with no codec to state."""
    return _module_open(call, CONTAINER_OPENERS)


def is_descriptor_open(call: ast.Call) -> bool:
    """``os.open(...)`` — an ``open`` that returns a descriptor and decodes nothing."""
    return _module_open(call, DESCRIPTOR_OPENERS)


def opens_without_a_codec(call: ast.Call) -> bool:
    """An ``open()`` neither instrument should ask about: a container's or a descriptor's."""
    return is_container_open(call) or is_descriptor_open(call)


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
    if opens_without_a_codec(call):
        return False
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
