"""`write_whole` puts a report on a descriptor whole, whatever its blocking mode.

BDL-083 S1e2 (``beadloom-jwfc``, BDL-UX #226). Measured at 12c35cf3 (Darwin arm64,
CPython 3.13.7): ``beadloom ci`` wrote its report with one ``click.echo``, and on a pipe
set non-blocking whose reader started late it raised ``BlockingIOError`` after 83518 of
229492 bytes. The writer under test waits for the reader instead: the descriptor is set
blocking for the write and put back as it was, and an ``EAGAIN`` that arrives anyway is
retried once the descriptor can take more, so nothing is dropped or written twice.
"""

from __future__ import annotations

import contextlib
import fcntl
import io
import os
import resource
from typing import TYPE_CHECKING

from beadloom.infrastructure import console_streams
from beadloom.infrastructure.console_streams import write_whole
from tests.support.late_reader import read_late

if TYPE_CHECKING:
    from collections.abc import Iterator

    import pytest

#: The largest default pipe capacity among the rooms this suite runs in (Linux, 64 KiB).
_PIPE_CAPACITY = 64 * 1024

#: A report several times the largest pipe capacity of the rooms this suite runs in.
_REPORT = "\n".join(f"  - finding {n:05d}: " + "x" * 90 for n in range(6000))


#: The first descriptor `select(2)` cannot take on Linux: `FD_SETSIZE` is 1024 there, and
#: CPython refuses a descriptor at or above it with `ValueError` (the same on Darwin).
_FD_SETSIZE = 1024

#: Room above :data:`_FD_SETSIZE` for the soft descriptor limit, so a high descriptor fits.
_LIMIT_HEADROOM = 64


def _text_stream(write_end: int, *, encoding: str = "utf-8") -> io.TextIOWrapper:
    """A text stream over *write_end* that does not close it, as ``sys.stdout`` is."""
    return open(write_end, "w", encoding=encoding, errors="backslashreplace", closefd=False)


def test_the_report_is_larger_than_any_pipe_the_suite_runs_in() -> None:
    assert len(_REPORT.encode()) > 4 * _PIPE_CAPACITY


def test_a_late_reader_receives_the_whole_report_through_a_non_blocking_pipe() -> None:
    def _write(write_end: int) -> None:
        with _text_stream(write_end) as stream:
            write_whole(_REPORT, stream)

    read = read_late(_write)
    assert read.text == _REPORT + "\n"


def test_the_descriptor_is_non_blocking_again_after_the_write() -> None:
    def _write(write_end: int) -> None:
        with _text_stream(write_end) as stream:
            write_whole("one line", stream)

    assert read_late(_write).nonblocking_after is True


def test_a_blocking_descriptor_stays_blocking() -> None:
    read_end, write_end = os.pipe()
    try:
        with _text_stream(write_end) as stream:
            write_whole("one line", stream)
        assert os.get_blocking(write_end) is True
        assert os.read(read_end, 64) == b"one line\n"
    finally:
        os.close(read_end)
        os.close(write_end)


def _refuse_blocking_mode(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """Make every request to set a descriptor blocking a no-op; count the waits for room.

    Only the request for blocking mode is refused: the late reader's own request for
    non-blocking mode still lands, so the write end stays non-blocking for the whole
    write, as it does when another holder of the description flips it back. Refusing
    both requests leaves the pipe blocking, and the retry is then never reached.
    """
    real_set_blocking = os.set_blocking
    real_wait = console_streams._wait_for_room
    waits: list[int] = []

    def _set_blocking(fd: int, blocking: bool) -> None:
        if not blocking:
            real_set_blocking(fd, blocking)

    def _wait_for_room(fd: int) -> None:
        waits.append(fd)
        real_wait(fd)

    monkeypatch.setattr(console_streams.os, "set_blocking", _set_blocking)
    monkeypatch.setattr(console_streams, "_wait_for_room", _wait_for_room)
    return waits


def test_an_eagain_that_arrives_anyway_is_retried_and_nothing_is_written_twice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Another holder of the description can set it non-blocking again mid-write."""
    _refuse_blocking_mode(monkeypatch)

    def _write(write_end: int) -> None:
        with _text_stream(write_end) as stream:
            write_whole(_REPORT, stream)

    assert read_late(_write).text == _REPORT + "\n"


def test_an_eagain_that_arrives_anyway_waits_for_room_before_the_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The retry above is reached: the writer waited on the descriptor at least once."""
    waits = _refuse_blocking_mode(monkeypatch)

    def _write(write_end: int) -> None:
        with _text_stream(write_end) as stream:
            write_whole(_REPORT, stream)

    read_late(_write)

    assert waits, "the write end never refused a write, so no retry was exercised"


def test_a_descriptor_whose_mode_cannot_be_read_is_written_as_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A descriptor ``os.get_blocking`` cannot answer for is still written whole."""

    def _unreadable_mode(_fd: int) -> bool:
        raise OSError("mode unavailable")

    monkeypatch.setattr(console_streams.os, "get_blocking", _unreadable_mode)
    read_end, write_end = os.pipe()
    try:
        with _text_stream(write_end) as stream:
            write_whole("one line", stream)
        assert os.read(read_end, 64) == b"one line\n"
    finally:
        os.close(read_end)
        os.close(write_end)


def test_text_the_stream_had_buffered_goes_first() -> None:
    def _write(write_end: int) -> None:
        with _text_stream(write_end) as stream:
            stream.write("buffered before\n")
            write_whole(_REPORT, stream)

    assert read_late(_write).text == "buffered before\n" + _REPORT + "\n"


def test_the_stream_s_codec_and_handler_spell_the_bytes() -> None:
    def _write(write_end: int) -> None:
        with _text_stream(write_end, encoding="ascii") as stream:
            write_whole("PASS — gate clean", stream)

    assert read_late(_write).text == "PASS \\u2014 gate clean\n"


def test_a_stream_with_no_descriptor_gets_the_text_and_a_newline() -> None:
    stream = io.StringIO()
    write_whole("PASS — gate clean", stream)
    assert stream.getvalue() == "PASS — gate clean\n"


@contextlib.contextmanager
def _room_for_a_high_descriptor() -> Iterator[None]:
    """The soft ``RLIMIT_NOFILE`` above :data:`_FD_SETSIZE` for the duration, then as found."""
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    wanted = _FD_SETSIZE + _LIMIT_HEADROOM
    if soft >= wanted:
        yield
        return
    resource.setrlimit(resource.RLIMIT_NOFILE, (wanted, hard))
    try:
        yield
    finally:
        resource.setrlimit(resource.RLIMIT_NOFILE, (soft, hard))


def test_a_descriptor_above_what_select_can_take_receives_the_whole_report(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A wait for room on a descriptor at or above 1024 does not raise (PR #106, Linux).

    A long run holds many descriptors, so the one under ``sys.stdout`` can be numbered past
    what ``select`` takes: CI handed the writer 4066. ``F_DUPFD`` takes the lowest free
    descriptor at or above the floor, so the test never closes one somebody else holds,
    as ``dup2`` to a fixed number could. The duplicate shares the pipe's description, so
    the late reader's non-blocking mode is its mode, and refusing blocking mode makes the
    write reach the wait.
    """
    _refuse_blocking_mode(monkeypatch)

    def _write(write_end: int) -> None:
        high = fcntl.fcntl(write_end, fcntl.F_DUPFD, _FD_SETSIZE)
        try:
            assert high >= _FD_SETSIZE
            with _text_stream(high) as stream:
                write_whole(_REPORT, stream)
        finally:
            os.close(high)

    with _room_for_a_high_descriptor():
        assert read_late(_write).text == _REPORT + "\n"


def test_without_poll_the_writer_pauses_and_still_delivers_the_whole_report(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Windows has no ``poll`` and its ``select`` takes no pipe: a pause stands in for it."""
    _refuse_blocking_mode(monkeypatch)
    monkeypatch.delattr(console_streams.select, "poll")
    real_sleep = console_streams.time.sleep
    pauses: list[float] = []

    def _sleep(seconds: float) -> None:
        pauses.append(seconds)
        real_sleep(seconds)

    monkeypatch.setattr(console_streams.time, "sleep", _sleep)

    def _write(write_end: int) -> None:
        with _text_stream(write_end) as stream:
            write_whole(_REPORT, stream)

    assert read_late(_write).text == _REPORT + "\n"
    assert pauses, "the write end never refused a write, so no pause was exercised"
