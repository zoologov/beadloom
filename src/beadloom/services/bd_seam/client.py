# beadloom:service=mcp-server
# beadloom:component=bd-seam
"""Mockable seam over the ``bd`` (beads) CLI.

The MCP process-tools (``task_init`` / ``complete_bead`` / ``checkpoint``)
drive the beads issue tracker. Rather than scatter ``subprocess`` calls across
the handlers, every ``bd`` invocation funnels through :func:`run_bd` — a single,
thin, **mockable** seam (mirrors the F4.1 harness's ``run_command``). Tests patch
:func:`run_bd` (or the module-level ``subprocess.run``) so the tools run WITHOUT
a real ``bd`` binary and without network.

Whenever ``bd`` does not answer — not installed, not executable, wedged past the
timeout, or printing bytes this process cannot read — :func:`run_bd` raises
:class:`BdUnavailableError` with a message naming the cause; the calling tool
converts that into a structured error payload (the agentic flow already requires
``bd``), and the guard probe converts it into a *skip with a reason*. A non-zero
exit is not that case: it is bd answering, and it is returned as a
:class:`BdResult`.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass

# services -> application is the sanctioned direction; this is the ONE definition
# of "an exception as a readable clause that names its class" (BDL-061.36), and a
# reader compares the seam's wording with the guard boundary's.
from beadloom.application.guards.models import exception_detail

# Default per-call timeout (seconds) so a wedged `bd` never hangs a tool call.
_BD_TIMEOUT_S = 60

#: The codec that turns bd's bytes into text, STATED rather than inherited from
#: the image. ``text=True`` decodes with ``locale.getpreferredencoding(False)``,
#: so on a container whose locale is not UTF-8 a bead title with one non-ASCII
#: byte either raised (``ascii``) or came back as a different title
#: (``latin-1``) — neither visible on the author's UTF-8 machine (BDL-061.37).
#: bd speaks JSON, and JSON is UTF-8 by definition (RFC 8259 §8.1), so UTF-8 is
#: bd's contract rather than a guess about the environment.
_BD_ENCODING = "utf-8"

#: ``surrogateescape`` rather than ``strict``, stated by which way each fails.
#: What the callers *decide* with is machine tokens — bead ids, statuses, the
#: JSON structure — while the non-ASCII part is display text (titles, stderr
#: prose). ``strict`` would make one stray byte in one bead's title unreadable,
#: the seam would report bd unavailable, and ``bead-claimed`` would skip for the
#: whole project: a gate switched off by display text. ``surrogateescape`` is
#: injective, so every token still decodes to a distinct string and no comparison
#: can be given a wrong answer; the cost is that such a title reaches the reader
#: with ``\udcff``-style escapes in it, which is ugly and true.
_BD_DECODE_ERRORS = "surrogateescape"

_NOT_INSTALLED = (
    "`bd` CLI not found on PATH — the agentic flow requires beads (bd) to be installed"
)
_COULD_NOT_RUN = "`bd` could not be run to completion ({detail})"


class BdUnavailableError(RuntimeError):
    """Raised when ``bd`` cannot be run to completion — for any reason.

    Not only "not installed": a bd that cannot be executed (``PermissionError``),
    one that wedges past the timeout (``subprocess.TimeoutExpired``) and one whose
    answer cannot be decoded are all the same fact to every caller — *bd did not
    answer* — and each caller already has a right response to it (the MCP tools
    return a structured error, the guard probe returns ``None`` so the guard skips
    with a reason). Before BDL-061.37 those escaped the seam as themselves and
    reached the guard boundary as ``error``/exit 2, blocking an edit for a reason
    that was not the real one. The message always names the underlying class.
    """


@dataclass(frozen=True)
class BdResult:
    """Outcome of a single ``bd`` invocation."""

    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        """True when ``bd`` exited 0."""
        return self.returncode == 0


def run_bd(args: list[str], *, cwd: str | None = None) -> BdResult:
    """Invoke ``bd`` with *args* and capture its output.

    Parameters
    ----------
    args:
        Arguments passed to ``bd`` (without the leading ``bd``), e.g.
        ``["show", "bd-1", "--json"]``.
    cwd:
        Optional working directory for the invocation.

    Returns
    -------
    BdResult
        Captured ``returncode`` / ``stdout`` / ``stderr``.

    Raises
    ------
    BdUnavailableError
        If ``bd`` cannot be run to completion — missing, not executable, wedged,
        or answering in bytes that are not text. A non-zero *exit* is not this:
        that is bd answering, and it comes back as a :class:`BdResult`.
    """
    try:
        # `bd` is resolved from PATH by design; argv is fixed (no shell, no user-built path).
        completed = subprocess.run(  # noqa: S603
            ["bd", *args],  # noqa: S607
            cwd=cwd,
            capture_output=True,
            encoding=_BD_ENCODING,
            errors=_BD_DECODE_ERRORS,
            timeout=_BD_TIMEOUT_S,
            check=False,
        )
    except FileNotFoundError as exc:
        # Kept separate from the clause below because it is the one failure with
        # a remedy the reader can act on: install bd.
        raise BdUnavailableError(_NOT_INSTALLED) from exc
    except Exception as exc:  # as wide as the sentence it holds; see the class
        # The seam's promise is "a BdResult, or BdUnavailableError" — an
        # enumeration of classes is narrower than that promise, which is how a
        # 60-second timeout and a decode failure used to escape it. `Exception`,
        # not `BaseException`: an interrupt is the process being stopped, not bd
        # declining. Nothing is swallowed — the class is named in the message and
        # the original is chained, so a bug of ours still arrives with its
        # traceback rather than disguised as a missing binary.
        raise BdUnavailableError(_COULD_NOT_RUN.format(detail=exception_detail(exc))) from exc
    return BdResult(
        returncode=completed.returncode,
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
    )
