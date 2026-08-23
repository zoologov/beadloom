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

Why the ASCII leg is green while the 8-bit one is not — the asymmetry that made
this invisible for two slices: under the C/POSIX locale CPython already gives
``sys.stdout`` the ``backslashreplace`` handler, so the same glyph degrades to
``\\u2192`` and nothing raises. A *named* 8-bit locale is a real locale, gets
``strict``, and raises. So the defect is reachable only on the row that exists
precisely because "non-UTF-8" and "ASCII" are not the same environment.

The fix applies CPython's own C-locale policy everywhere: keep the terminal's
codec, replace ``strict`` with ``backslashreplace``. A character the terminal
cannot show is then printed as its escape — visible, greppable, and never fatal.
Nothing that must be exact is affected: ``--json`` payloads are consumed by
programs through a pipe whose codec this does not change, and every file we
write states ``encoding="utf-8"`` at its own call site.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import IO

#: What CPython already applies to ``sys.stdout`` under the C locale, and to
#: ``sys.stderr`` always. Not ``replace``: U+FFFD tells a reader a character was
#: there and nothing about which, while ``\uXXXX`` names it and can be searched.
TOLERANT_ERRORS = "backslashreplace"


def tolerate_unencodable_output(streams: Iterable[IO[str]] | None = None) -> tuple[str, ...]:
    """Relax ``strict`` to :data:`TOLERANT_ERRORS` on the console streams.

    Returns the names of the streams actually reconfigured, so a caller (and the
    test suite) can tell "nothing needed changing" from "nothing was done" —
    a silent no-op is how a policy stops being applied without anyone noticing.

    Deliberately conservative in three ways. A stream that is not a
    ``TextIOWrapper`` — Click's test runner, a captured pipe, a redirected
    buffer — has no ``reconfigure`` and is left alone. A stream whose handler is
    already non-strict (an operator's ``PYTHONIOENCODING=utf-8:replace``, or
    stderr, which CPython hands us as ``backslashreplace``) is left alone, so an
    explicit choice outranks ours. And the codec itself is never touched: the
    terminal's encoding is the operator's, not ours to override.
    """
    targets = (sys.stdout, sys.stderr) if streams is None else streams
    relaxed: list[str] = []
    for stream in targets:
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None or getattr(stream, "errors", None) != "strict":
            continue
        try:
            reconfigure(errors=TOLERANT_ERRORS)
        except (OSError, ValueError):
            # A stream that refuses to be reconfigured keeps its own policy;
            # the command still runs, which is the property being protected.
            continue
        relaxed.append(getattr(stream, "name", repr(stream)))
    return tuple(relaxed)
