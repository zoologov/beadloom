# beadloom:component=console-streams
"""The process's own stdout/stderr survive the room they are written into.

Two rooms, one responsibility: a terminal that cannot spell a glyph (the error handler,
below) and a pipe that will not wait (:func:`write_whole`, at the end of this module).

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

import contextlib
import os
import select
import sys
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from typing import IO, TextIO

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


# --- A pipe that will not wait (BDL-UX #226) -------------------------------------------
#
# MEASURED at 12c35cf3 (Darwin arm64, CPython 3.13.7): `beadloom ci --format rich` wrote
# its whole report with one `click.echo`, and on a pipe whose write end was set
# non-blocking and whose reader started late it raised `BlockingIOError: [Errno 35] write
# could not complete without blocking` after 83518 of 229492 bytes. An agent's shell hands
# `git push` exactly such a pipe, so the bigger the honest report, the likelier the Gate
# died on its output rather than on a check.
#
# The flag lives on the open file description, which every holder of that end of the pipe
# shares, so it is set blocking for the write and put back as it was found: a parent that
# chose non-blocking writes keeps its choice. Another holder can flip it back mid-write,
# which is why an `EAGAIN` is still expected and retried. The retry is on raw `os.write`,
# which reports how many bytes it took, so nothing is dropped and nothing is written twice;
# a text stream that raises half-way through a write cannot say how much of it went out.
#
# The wait for room is `poll`, not `select`. `select(2)` takes no descriptor at or above
# FD_SETSIZE (1024), and CPython raises `ValueError: filedescriptor out of range in
# select()` for one: PR #106's CI (Linux, CPython 3.13) handed this writer descriptor 4066
# after a long suite, and the writer that exists to survive the pipe raised instead.
# `poll(2)` has no such limit. Windows has no `poll`, and its `select` takes sockets only,
# so there the writer pauses for `_RETRY_PAUSE` and retries: the same bytes, a coarser wait.

#: How long the writer pauses before retrying a refused write on a platform with no ``poll``.
_RETRY_PAUSE = 0.01


def _descriptor(stream: TextIO) -> int | None:
    """The file descriptor under *stream*, or ``None`` for a stream that has none."""
    try:
        return stream.fileno()
    except (AttributeError, OSError, ValueError):
        # A test runner's buffer, a `StringIO`: `io.UnsupportedOperation` is both an
        # OSError and a ValueError, and a closed stream raises ValueError.
        return None


@contextlib.contextmanager
def _blocking(fd: int) -> Iterator[None]:
    """*fd* in blocking mode for the duration, then in the mode it was found in."""
    try:
        was_blocking = os.get_blocking(fd)
    except OSError:
        yield
        return
    if not was_blocking:
        with contextlib.suppress(OSError):
            os.set_blocking(fd, True)
    try:
        yield
    finally:
        if not was_blocking:
            with contextlib.suppress(OSError):
                os.set_blocking(fd, False)


def _wait_for_room(fd: int) -> None:
    """Return once *fd* can take more bytes, or after :data:`_RETRY_PAUSE` without ``poll``.

    A reader that has gone away also ends the wait (``POLLERR``/``POLLHUP``), and the retry
    then raises ``BrokenPipeError`` rather than waiting forever.
    """
    poll = getattr(select, "poll", None)
    if poll is None:
        time.sleep(_RETRY_PAUSE)
        return
    poller = poll()
    poller.register(fd, select.POLLOUT)
    poller.poll()


def _write_all(fd: int, payload: bytes) -> None:
    """Every byte of *payload* to *fd*, waiting for room whenever the pipe has none."""
    pending = memoryview(payload)
    while pending:
        try:
            written = os.write(fd, pending)
        except BlockingIOError:
            _wait_for_room(fd)
            continue
        pending = pending[written:]


def write_whole(text: str, stream: TextIO) -> None:
    """Write *text* and a newline to *stream* whole, whatever its descriptor's mode.

    The bytes are the stream's own codec and error handler applied to the text, so a
    terminal gets what ``stream.write`` would have given it. A stream with no descriptor
    is written through its own ``write``. Text the stream had buffered goes out first.
    The call waits for as long as the reader takes, as a blocking write does: a report
    is never dropped or cut short because its reader was slow.
    """
    line = text + "\n"
    fd = _descriptor(stream)
    if fd is None:
        stream.write(line)
        stream.flush()
        return
    payload = line.encode(stream.encoding, stream.errors or "strict")
    with _blocking(fd):
        stream.flush()
        _write_all(fd, payload)
