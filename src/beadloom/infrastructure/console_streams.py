# beadloom:component=console-streams
"""The process's own stdout/stderr survive a terminal that cannot spell a glyph.

Found by the ``tests-locale`` 8-bit leg (BDL-061.42), and it is the one place in
that sweep where UTF-8 is the **wrong** answer. Every other byte stream Beadloom
writes is a contract — a hook, ``AGENTS.md``, JSON, graph YAML — read back by us
or by another program, so it is UTF-8 by definition. A terminal is not: its codec
is genuinely the operator's locale, and writing UTF-8 into a latin-1 terminal
would put mojibake on their screen. What was wrong was not the codec but the
**error handler**.

MEASURED on ``ghcr.io/astral-sh/uv:python3.13-bookworm-slim`` with
``LC_ALL=en_US.ISO-8859-1`` (``PYTHONUTF8=0``, ``PYTHONCOERCECLOCALE=0``), and
both rows are output nobody would call cosmetic:

* ``python -m beadloom.ai_agents.ai_techwriter --help`` exits **1** with
  ``UnicodeEncodeError: 'latin-1' codec can't encode character '\\u2192'``
  raised inside ``click.echo`` — the help text carries an arrow;
* ``beadloom guard working-branch`` on a passing project writes **nothing** to
  stdout, because the verdict line carries an em dash and the write died. A
  guard whose PASS is silent is indistinguishable from a guard that never ran,
  which is the exact failure this epic exists to remove.

The two non-UTF-8 rooms differ in their handler, not in whether they are
affected, and the earlier version of this paragraph got that wrong. It said the
C/POSIX locale already gives ``sys.stdout`` the ``backslashreplace`` handler, so
the same glyph degrades and nothing raises. MEASURED on CPython 3.13.7 / Darwin
arm64 under ``LC_ALL=C PYTHONUTF8=0 PYTHONCOERCECLOCALE=0``, to a pipe and to a
tty alike, ``sys.stdout`` is ``ascii`` with **``surrogateescape``** — and that
handler re-encodes lone surrogates and nothing else, so an ordinary non-ASCII
character raises exactly as it does under ``strict``. A named 8-bit locale gets
``strict``. Both rooms raise; only the handler that has to be recognised
differs.

The cost of that mistake, MEASURED in the same room with the streams separated
and the exit code read from ``$?`` without a pipe: ``beadloom docs audit`` exits
**1** after writing 1321 bytes of a partial report, with
``UnicodeEncodeError: 'ascii' codec can't encode character '\\xb1'`` raised at
``rich/console.py`` in ``self.file.write(text)`` — the PLUS-MINUS sign of the
tolerance label. Click is not in the same position, which is why the harness's
``--help`` survives this room either way: Click replaces an ASCII stdout with a
UTF-8 writer of its own, while Rich writes to ``sys.stdout`` as it finds it.
No CI leg observes any of this — the ``tests-locale`` legs run ``pytest`` and
``beadloom ci`` runs under the default UTF-8 locale — so it reaches an adopter
on a C-locale container rather than us.

**This is an encode site and it is not the mirror of the decode sites.** Where
Beadloom reads bytes it does not own — ``bd``'s JSON, a git ref name, a
filesystem path — ``surrogateescape`` is chosen deliberately and argued at each
call site (see :mod:`beadloom.services.bd_seam.client`): it is the only handler
that is injective, so no comparison can be given a wrong answer by a byte.
Nothing here compares anything. The consumer is a terminal, the requirement is
that the process finishes, and ``backslashreplace`` is the total function where
``surrogateescape`` is a partial one. Making the two directions agree would
answer the encode question with the decode question's reason.

The fix applies CPython's own C-locale policy everywhere: keep the terminal's
codec, replace ``strict`` with ``backslashreplace``. A character the terminal
cannot show is then printed as its escape — visible, greppable, and never fatal.
Nothing that must be exact is affected: ``--json`` payloads are consumed by
programs through a pipe whose codec this does not change, and every file we
write states ``encoding="utf-8"`` at its own call site.
"""

from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import IO

#: What CPython already applies to ``sys.stderr``, MEASURED in every room this
#: module names. Not ``replace``: U+FFFD tells a reader a character was there
#: and nothing about which, while ``\uXXXX`` names it and can be searched.
TOLERANT_ERRORS = "backslashreplace"

#: The handlers a console stream carries when nobody chose one — ``strict``
#: under a named locale, ``surrogateescape`` under C/POSIX. Both are the image's
#: and both raise on an ordinary non-ASCII character, so both are relaxed.
#: :data:`TOLERANT_ERRORS` is strictly wider than either: every character they
#: encode it also encodes, and the ones they raise on it names.
IMAGE_DEFAULT_ERRORS = frozenset({"strict", "surrogateescape"})

#: The environment variable that carries an operator's handler for the standard
#: streams, in the form ``[codec][:errors]``.
_HANDLER_ENV_VAR = "PYTHONIOENCODING"


def _operator_named_a_handler() -> bool:
    """Whether the handler on the standard streams was chosen rather than inherited.

    The handler's NAME cannot answer this, which is the defect this module was
    corrected for: ``surrogateescape`` is CPython's C-locale default and is also
    what an operator piping byte-exact names would ask for. ``PYTHONIOENCODING``
    is the one channel that carries the request, and its codec half is not a
    request about the handler — ``PYTHONIOENCODING=utf-8`` states a codec and
    leaves the handler to CPython.
    """
    _, _, errors = os.environ.get(_HANDLER_ENV_VAR, "").partition(":")
    return bool(errors.strip())


def tolerate_unencodable_output(streams: Iterable[IO[str]] | None = None) -> tuple[str, ...]:
    """Relax an :data:`IMAGE_DEFAULT_ERRORS` handler to :data:`TOLERANT_ERRORS`.

    Returns the names of the streams actually reconfigured, so a caller (and the
    test suite) can tell "nothing needed changing" from "nothing was done" —
    a silent no-op is how a policy stops being applied without anyone noticing.

    Deliberately conservative in three ways. A stream that is not a
    ``TextIOWrapper`` — Click's test runner, a captured pipe, a redirected
    buffer — has no ``reconfigure`` and is left alone. A handler the operator
    named through ``PYTHONIOENCODING`` outranks ours and is left alone, even
    when it is one the image also hands out; a handler nobody named is a
    default, whatever it is called. And the codec itself is never touched: the
    terminal's encoding is the operator's, not ours to override.

    ``PYTHONIOENCODING`` governs ``sys.stdout`` and ``sys.stderr``, which are
    what this function exists for; a caller that passes another stream — the
    tests do — gets the same policy, because the question being answered is
    still "did anyone choose this handler".
    """
    if _operator_named_a_handler():
        return ()
    targets = (sys.stdout, sys.stderr) if streams is None else streams
    relaxed: list[str] = []
    for stream in targets:
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None or getattr(stream, "errors", None) not in IMAGE_DEFAULT_ERRORS:
            continue
        try:
            reconfigure(errors=TOLERANT_ERRORS)
        except (OSError, ValueError):
            # A stream that refuses to be reconfigured keeps its own policy;
            # the command still runs, which is the property being protected.
            continue
        relaxed.append(getattr(stream, "name", repr(stream)))
    return tuple(relaxed)
