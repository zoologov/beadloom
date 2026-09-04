"""The probes' text is decoded by a stated codec, not by the image's locale (BDL-061.37).

The defect family this module exists for is the one BDL-061.36 named and could
not fix in its own scope: a refusal, or a handler, that is correct only under the
environment its author happened to run. Both subprocess probes ran with
``text=True``, which decodes with ``locale.getpreferredencoding(False)`` — the
*ambient* codec — and both handlers enumerated exception classes that do not
include the one a decode failure raises (``UnicodeDecodeError`` is a
``ValueError``: neither an ``OSError`` nor a ``subprocess.SubprocessError``).

Direction of the failure, which is why it is P0 rather than cosmetic: the
invocation boundary turns the escaping exception into an ``error`` verdict at
exit 2 and **blocks the edit**, where the designed answer for "the probe cannot
answer" is ``skip`` with a stated reason. The guard neither lies nor crashes — it
blocks work for a reason that is not the real one.

Two dimensions, and they need different instruments, so both are here:

* **Bytes that are not text at all** — reproducible on this machine, through the
  real ``git`` and through a real child process on ``PATH``. Measured: with
  ``text=True`` under this UTF-8 macOS, ``git branch --show-current`` on a HEAD
  pointing at ``refs/heads/features/<0xff>-bad`` raises
  ``UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff in position 9``.
* **An ambient codec that is not UTF-8** — NOT reproducible on this machine, and
  that is the point. Measured here: ``LC_ALL=C PYTHONUTF8=0
  PYTHONCOERCECLOCALE=0`` still reports preferred encoding ``utf-8`` (PEP
  538/540 coercion), and patching ``locale.getpreferredencoding`` does **not**
  reach ``TextIOWrapper``, which resolves the locale codec below Python. So the
  dimension is *constructed* rather than arranged: :class:`tests.ambient_codec.AmbientTextMode`
  re-implements CPython's documented text-mode rule ("decoded using
  ``locale.getpreferredencoding(False)`` unless ``encoding`` is given") with the
  ambient codec as a parameter. Concluding the defect is absent because this
  machine cannot produce it is exactly the inference that put .36's two defects
  into CI.

Standing rule 4 is respected rather than argued around: the ambient-codec rows
run against a double and therefore prove the double's contract, so every claim
they make is also made against the real ``git`` binary and a real child process
in :class:`TestBytesThatAreNotTextAtAll`.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from typing import TYPE_CHECKING

import pytest

from beadloom.application.guards.evaluation import evaluate_guard
from beadloom.application.guards.models import GuardOutcome
from beadloom.services import bd_seam, guard_probes
from beadloom.services.bd_seam import BdUnavailableError, run_bd
from beadloom.services.guard_probes import build_probes
from tests.ambient_codec import under_ambient_codec
from tests.filesystem_names import as_the_process_receives

if TYPE_CHECKING:
    from pathlib import Path

#: A branch name that is valid UTF-8 and not ASCII — the case an ambient
#: non-UTF-8 codec silently corrupts (latin-1) or refuses (ascii).
CYRILLIC_BRANCH = "features/тест"

#: A byte that is not valid UTF-8 in any position. git accepts it in a ref name;
#: APFS refuses it in a *filename*, which is why the tests below write it into
#: the contents of ``.git/HEAD`` (via ``git symbolic-ref``) rather than creating
#: a loose ref file — the ref store, not the filesystem, is what git prints from.
UNDECODABLE = b"\xff"

_BAD_BRANCH_BYTES = b"features/" + UNDECODABLE + b"-bad"
_BAD_BRANCH_STR = _BAD_BRANCH_BYTES.decode("utf-8", "surrogateescape")

pytestmark = pytest.mark.skipif(
    sys.platform == "win32",
    reason="POSIX ref bytes and a shebang stub on PATH; the Windows story is untested (.36 #3)",
)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(  # noqa: S603 — fixed argv, no shell
        ["git", "-C", str(repo), *args],  # noqa: S607
        check=True,
        capture_output=True,
    )


@pytest.fixture()
def repo(tmp_path):
    """A real git repository with one commit, so HEAD can be pointed anywhere."""
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "t")
    _git(tmp_path, "commit", "-q", "--allow-empty", "-m", "root")
    return tmp_path


def _point_head_at(repo: Path, ref: bytes) -> None:
    """Write *ref* into ``.git/HEAD`` through git itself, bytes intact."""
    subprocess.run(  # noqa: S603 — fixed argv, no shell
        [b"git", b"-C", os.fsencode(repo), b"symbolic-ref", b"HEAD", ref],
        check=True,
        capture_output=True,
    )


def _stub_bd(tmp_path: Path, monkeypatch, stdout: bytes) -> Path:
    """Put a real executable named ``bd`` on PATH that writes *stdout* verbatim.

    A stub binary, but a real process, a real pipe and the real seam: what is
    under test is how *this* process decodes what comes back, which no in-process
    fake can exercise.
    """
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    script = bin_dir / "bd"
    script.write_bytes(
        b"#!" + os.fsencode(sys.executable) + b"\n"
        b"import sys\n"
        b"sys.stdout.buffer.write(" + repr(stdout).encode("ascii") + b")\n"
    )
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("PATH", str(bin_dir), prepend=os.pathsep)
    return script


def _bd_payload(title: bytes) -> bytes:
    """One claimed bead as bd prints it, with *title* spliced in as raw bytes."""
    return b'[{"id": "bd-1", "status": "in_progress", "title": "' + title + b'"}]'


class TestTheAmbientDecoderDoesNotDecideTheAnswer:
    """The image's locale codec must not change what the probe reports."""

    @pytest.mark.parametrize(
        "ambient",
        ["utf-8", "ascii", "latin-1"],
        ids=["a utf-8 image", "the C locale of most CI images", "an 8-bit legacy image"],
    )
    def test_a_non_ascii_branch_name_reads_the_same_under_every_ambient_codec(
        self, repo, monkeypatch, ambient
    ) -> None:
        """``ascii`` raised past the handler; ``latin-1`` returned a different branch.

        Both directions are wrong and neither is visible on a UTF-8 machine: the
        first blocks the edit with an ``error`` verdict, the second reports a
        branch name nobody has ever checked out (the latin-1 mojibake of it), which the
        trunk comparison then answers confidently.
        """
        # The branch is created from the BYTES a real caller sends, not from the
        # str: on an image whose filesystem encoding cannot spell the name, argv
        # would carry those bytes and arrive surrogate-escaped, while passing the
        # str raises before git is even spawned. The assertion below is unchanged
        # — what the probe must return is still the name as UTF-8 (BDL-061.42).
        branch = as_the_process_receives(CYRILLIC_BRANCH)
        _git(repo, "branch", branch)
        _git(repo, "checkout", "-q", branch)
        under_ambient_codec(monkeypatch, guard_probes, ambient)

        assert build_probes(repo).workspace.current_branch() == CYRILLIC_BRANCH

    @pytest.mark.parametrize("ambient", ["utf-8", "ascii", "latin-1"])
    def test_a_non_ascii_bead_title_reads_the_same_under_every_ambient_codec(
        self, tmp_path, monkeypatch, ambient
    ) -> None:
        (tmp_path / ".beads").mkdir()
        _stub_bd(tmp_path, monkeypatch, _bd_payload("работа".encode()))
        under_ambient_codec(monkeypatch, bd_seam.client, ambient)

        claimed = build_probes(tmp_path).tracker.claimed_beads()

        assert claimed is not None, "the tracker answered; a skip here would be a false one"
        assert [(bead.id, bead.title) for bead in claimed] == [("bd-1", "работа")]


class TestBytesThatAreNotTextAtAll:
    """Real binaries, real bytes: the half of the defect this machine can produce."""

    def test_a_branch_name_that_is_not_utf8_is_reported_not_raised(self, repo) -> None:
        """Measured before the fix: ``UnicodeDecodeError`` escapes the handler.

        The name round-trips to the exact bytes git holds, which is the property
        that matters: ``surrogateescape`` is injective, so two branches that
        differ still differ after decoding and no comparison the guard performs
        can be given a wrong answer by an undecodable byte.
        """
        _point_head_at(repo, b"refs/heads/" + _BAD_BRANCH_BYTES)

        branch = build_probes(repo).workspace.current_branch()

        assert branch is not None
        assert branch.encode("utf-8", "surrogateescape") == _BAD_BRANCH_BYTES

    def test_such_a_branch_evaluates_to_a_verdict_a_terminal_can_print(self, repo) -> None:
        """The escaped bytes reach a message, so the message must stay printable.

        ``working-branch`` interpolates the name with ``!r``; ``repr`` escapes a
        lone surrogate to ``\\udcff``, so the verdict encodes on an ASCII-only
        stdout instead of raising ``UnicodeEncodeError`` where .31's "the render
        cannot choose the exit code" would have to save it.
        """
        _point_head_at(repo, b"refs/heads/" + _BAD_BRANCH_BYTES)

        verdict = evaluate_guard("working-branch", project_root=repo, probes=build_probes(repo))

        assert verdict.outcome is GuardOutcome.PASS
        assert verdict.why.encode("ascii")

    def test_a_bead_title_that_is_not_utf8_does_not_disable_the_claim_guard(
        self, tmp_path, monkeypatch
    ) -> None:
        """Display text must not switch a gate off.

        With ``errors="strict"`` one stray byte in one bead's title makes the
        tracker unanswerable and the guard skips for the whole project — an
        exemption nobody declared. The ids are what the check reads, and they
        survive verbatim.
        """
        (tmp_path / ".beads").mkdir()
        _stub_bd(tmp_path, monkeypatch, _bd_payload(b"a title with a " + UNDECODABLE + b" byte"))

        claimed = build_probes(tmp_path).tracker.claimed_beads()

        assert claimed is not None, "one bad display byte must not unplug the guard"
        assert [bead.id for bead in claimed] == ["bd-1"]


class TestTheHandlerIsAsWideAsItsSentence:
    """"A probe that cannot answer returns ``None``" — for every way it cannot."""

    @pytest.mark.parametrize(
        ("label", "error"),
        [
            ("a decode failure", UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")),
            ("a wedged git", subprocess.TimeoutExpired(cmd="git", timeout=10)),
            ("a git nobody may execute", PermissionError(13, "Permission denied")),
            ("a class nobody has enumerated yet", LookupError("unknown codec")),
        ],
    )
    def test_a_git_that_cannot_answer_reports_no_branch(
        self, tmp_path, monkeypatch, label, error
    ) -> None:
        def explode(*_args, **_kwargs):
            raise error

        monkeypatch.setattr(guard_probes.subprocess, "run", explode)

        assert build_probes(tmp_path).workspace.current_branch() is None, label

    @pytest.mark.parametrize(
        ("label", "error"),
        [
            ("a decode failure", UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")),
            ("a wedged bd", subprocess.TimeoutExpired(cmd="bd", timeout=60)),
            ("a class nobody has enumerated yet", LookupError("unknown codec")),
        ],
    )
    def test_a_bd_that_cannot_answer_is_reported_as_unavailable(
        self, monkeypatch, label, error
    ) -> None:
        """The seam has one name for "bd could not answer", and every caller reads it.

        Before this bead it caught ``FileNotFoundError`` alone, so a wedged bd
        (60 s timeout) or an undecodable answer escaped the seam, escaped the
        probe — which catches only :class:`BdUnavailableError` — and reached the
        boundary as ``error``/exit 2: a blocked edit for a reason that is not the
        real one.
        """

        def explode(*_args, **_kwargs):
            raise error

        monkeypatch.setattr(bd_seam.client.subprocess, "run", explode)

        with pytest.raises(BdUnavailableError) as caught:
            run_bd(["list"], cwd=None)

        assert type(error).__name__ in str(caught.value), "the reason names what actually failed"
        assert caught.value.__cause__ is error, "and keeps the original for a traceback"

    def test_a_bd_on_path_that_cannot_be_executed_skips_the_guard(
        self, tmp_path, monkeypatch
    ) -> None:
        """A real, reachable, non-executable ``bd`` — no injection needed.

        ``PermissionError`` is an ``OSError`` and not a ``FileNotFoundError``, so
        before this bead it escaped the seam and blocked the edit at exit 2.

        PATH is *replaced*, not prepended: ``execvp`` remembers ``EACCES`` and
        keeps searching, so with the real bd still reachable this test passed
        before the fix — by running the real binary. Measured, and it is the same
        vacuous shape .36 called out in the loop test.
        """
        (tmp_path / ".beads").mkdir()
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        (bin_dir / "bd").write_text("#!/bin/sh\necho '[]'\n")  # deliberately not chmod +x
        monkeypatch.setenv("PATH", str(bin_dir))

        probes = build_probes(tmp_path)

        assert probes.tracker.claimed_beads() is None
        verdict = evaluate_guard("bead-claimed", project_root=tmp_path, probes=probes)
        assert verdict.outcome is GuardOutcome.SKIP
        assert verdict.why.strip()


class TestTheSeamStillAnswersWhenBdDoes:
    """The widened handler must not swallow a real answer (or a real non-zero exit)."""

    def test_a_stub_bd_that_exits_non_zero_is_a_result_not_an_unavailability(
        self, tmp_path, monkeypatch
    ) -> None:
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        script = bin_dir / "bd"
        script.write_text("#!/bin/sh\necho out\necho err >&2\nexit 3\n")
        script.chmod(script.stat().st_mode | stat.S_IXUSR)
        monkeypatch.setenv("PATH", str(bin_dir), prepend=os.pathsep)

        result = run_bd(["list"], cwd=str(tmp_path))

        assert (result.returncode, result.ok) == (3, False)
        assert result.stdout.strip() == "out"
        assert result.stderr.strip() == "err"

    def test_the_real_bd_is_still_read_the_same_way(self, tmp_path) -> None:
        """Rule 4: the stubs above prove the stub's contract, this one bd's."""
        try:
            version = run_bd(["--version"], cwd=str(tmp_path))
        except BdUnavailableError:
            pytest.skip("bd binary not installed")

        assert version.ok and version.stdout.strip()
        assert json.loads(json.dumps(version.stdout)) == version.stdout
