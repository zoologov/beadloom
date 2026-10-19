"""A pipe set non-blocking, read only once its writer has been made to wait.

BDL-083 S1e2 (``beadloom-jwfc``, BDL-UX #226). The room this reproduces is an agent's
shell: it hands a command a pipe it reads when it gets to it, and sets the write end
non-blocking, so a write that does not fit fails with ``EAGAIN`` at once instead of
waiting for the reader.

A reader that starts after a fixed delay measures the machine's speed rather than the
writer: it races a writer that is still computing. This one starts on a condition the
writer causes. It drains when the pipe has held at least :data:`FULL_ENOUGH` bytes,
unchanged, for :data:`STILL_FOR` seconds (the writer is waiting for room it was not
given), or when the writer has closed its end. A writer that does not wait fails while
the reader is still idle, which is exactly what the room does to it.
"""

from __future__ import annotations

import fcntl
import os
import subprocess
import sys
import termios
import threading
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

#: The smallest pipe capacity among the rooms this suite runs in: Darwin starts a pipe
#: at 16 KiB and grows it to 64 KiB, Linux gives 64 KiB. A pipe holding this much is a
#: pipe whose writer has written past what a small write needs.
FULL_ENOUGH = 16 * 1024

#: How long the pipe's content must stay unchanged before the reader reads it as a
#: writer that is waiting.
STILL_FOR = 0.3

#: How often the reader looks at the pipe while it is idle.
_POLL = 0.02

#: The bound on a whole run, so a writer that never finishes fails the test instead of
#: hanging the suite.
_TIMEOUT = 120.0

#: How much one read takes from the pipe.
_CHUNK = 64 * 1024


@dataclass(frozen=True)
class LateRead:
    """What the late reader received, and the write end's mode when the writer was done."""

    received: bytes
    nonblocking_after: bool

    @property
    def text(self) -> str:
        return self.received.decode("utf-8", "replace")


def _available(read_end: int) -> int:
    """The bytes waiting in the pipe, as the kernel counts them."""
    raw = fcntl.ioctl(read_end, termios.FIONREAD, b"\0\0\0\0")
    return int.from_bytes(raw, sys.byteorder)


class _LateReader(threading.Thread):
    """Drains *read_end* once the writer waits or is done, then to end of file."""

    def __init__(self, read_end: int, writer_done: threading.Event) -> None:
        super().__init__(daemon=True)
        self._read_end = read_end
        self._writer_done = writer_done
        self.chunks: list[bytes] = []

    def _wait_for_a_waiting_writer(self) -> None:
        last, since = -1, time.monotonic()
        while not self._writer_done.is_set():
            held = _available(self._read_end)
            if held != last:
                last, since = held, time.monotonic()
            elif held >= FULL_ENOUGH and time.monotonic() - since >= STILL_FOR:
                return
            time.sleep(_POLL)

    def run(self) -> None:
        self._wait_for_a_waiting_writer()
        while chunk := os.read(self._read_end, _CHUNK):
            self.chunks.append(chunk)


def read_late(write: Callable[[int], None]) -> LateRead:
    """Call *write* with the write end of a non-blocking pipe and read the pipe late.

    *write* owns nothing: the write end is closed here once it returns, which is the
    reader's end of file.
    """
    read_end, write_end = os.pipe()
    os.set_blocking(write_end, False)
    done = threading.Event()
    reader = _LateReader(read_end, done)
    reader.start()
    try:
        write(write_end)
        nonblocking_after = not os.get_blocking(write_end)
    finally:
        done.set()
        os.close(write_end)
        reader.join(_TIMEOUT)
        os.close(read_end)
    assert not reader.is_alive(), "the late reader did not reach end of file"
    return LateRead(b"".join(reader.chunks), nonblocking_after)


def run_read_late(argv: list[str], *, cwd: Path, env: dict[str, str]) -> tuple[int, LateRead]:
    """Run *argv* with its stdout and stderr on one late-read non-blocking pipe."""
    returncode: list[int] = []

    def _run(write_end: int) -> None:
        proc = subprocess.run(  # noqa: S603 - argv is built by the test that calls this
            argv,
            cwd=cwd,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=write_end,
            stderr=write_end,
            check=False,
            timeout=_TIMEOUT,
        )
        returncode.append(proc.returncode)

    read = read_late(_run)
    return returncode[0], read
