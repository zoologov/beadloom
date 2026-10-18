"""`write_whole` puts a report on a descriptor whole, whatever its blocking mode.

BDL-083 S1e2 (``beadloom-jwfc``, BDL-UX #226). Measured at 12c35cf3 (Darwin arm64,
CPython 3.13.7): ``beadloom ci`` wrote its report with one ``click.echo``, and on a pipe
set non-blocking whose reader started late it raised ``BlockingIOError`` after 83518 of
229492 bytes. The writer under test waits for the reader instead: the descriptor is set
blocking for the write and put back as it was, and an ``EAGAIN`` that arrives anyway is
retried once the descriptor can take more, so nothing is dropped or written twice.
"""

from __future__ import annotations

import io
import os
from typing import TYPE_CHECKING

from beadloom.infrastructure import console_streams
from beadloom.infrastructure.console_streams import write_whole
from tests.support.late_reader import read_late

if TYPE_CHECKING:
    import pytest

#: The largest default pipe capacity among the rooms this suite runs in (Linux, 64 KiB).
_PIPE_CAPACITY = 64 * 1024

#: A report several times the largest pipe capacity of the rooms this suite runs in.
_REPORT = "\n".join(f"  - finding {n:05d}: " + "x" * 90 for n in range(6000))


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
    """Make every request to set a descriptor blocking a no-op; count ``select`` waits.

    Only the request for blocking mode is refused: the late reader's own request for
    non-blocking mode still lands, so the write end stays non-blocking for the whole
    write, as it does when another holder of the description flips it back. Refusing
    both requests leaves the pipe blocking, and the retry is then never reached.
    """
    real_set_blocking = os.set_blocking
    real_select = console_streams.select.select
    waits: list[int] = []

    def _set_blocking(fd: int, blocking: bool) -> None:
        if not blocking:
            real_set_blocking(fd, blocking)

    def _select(
        rlist: list[int], wlist: list[int], xlist: list[int]
    ) -> tuple[list[int], list[int], list[int]]:
        waits.append(1)
        return real_select(rlist, wlist, xlist)

    monkeypatch.setattr(console_streams.os, "set_blocking", _set_blocking)
    monkeypatch.setattr(console_streams.select, "select", _select)
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
