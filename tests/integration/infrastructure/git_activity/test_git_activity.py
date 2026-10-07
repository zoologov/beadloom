"""Tests for beadloom.infrastructure.git_activity — Git history analysis."""

from __future__ import annotations

import subprocess
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from beadloom.infrastructure.git_activity import (
    GitActivity,
    analyze_git_activity,
)

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def git_repo(tmp_path: Path) -> Path:
    """Create a real temporary git repository with commits."""
    subprocess.run(
        ["git", "init"],  # noqa: S607
        cwd=str(tmp_path),
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],  # noqa: S607
        cwd=str(tmp_path),
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],  # noqa: S607
        cwd=str(tmp_path),
        capture_output=True,
        check=True,
    )
    return tmp_path


def _make_commit(
    repo: Path,
    file_path: str,
    content: str,
    message: str,
    *,
    author: str = "Test User",
    email: str = "test@example.com",
) -> None:
    """Create a file and commit it in the given repo."""
    full_path = repo / file_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content)
    subprocess.run(  # noqa: S603
        ["git", "add", file_path],  # noqa: S607
        cwd=str(repo),
        capture_output=True,
        check=True,
    )
    subprocess.run(  # noqa: S603
        ["git", "commit", "-m", message, "--author", f"{author} <{email}>"],  # noqa: S607
        cwd=str(repo),
        capture_output=True,
        check=True,
    )


# ---------------------------------------------------------------------------
# Sample git log output for mocking
# ---------------------------------------------------------------------------

def _rel_date(days_ago: int) -> str:
    """ISO 8601 timestamp ``days_ago`` days before now (UTC).

    Used to build deterministic git-log samples whose 30d/90d windows
    are stable regardless of the run date (see BDL-036 / issue #98).
    """
    dt = datetime.now(tz=timezone.utc) - timedelta(days=days_ago)
    return dt.strftime("%Y-%m-%dT%H:%M:%S+00:00")


def _numstat_log(commits: list[tuple[str, str, str, list[tuple[str, int]]]]) -> str:
    """``git log --format=<RS>%H<US>%cI<US>%aN --numstat -z`` output for *commits*.

    Each commit is ``(hash, date, author, [(path, changed lines), ...])``; the
    lines are written as added, none deleted.
    """
    out: list[str] = []
    for commit_hash, date, author, files in commits:
        entries = "".join(f"{lines}\t0\t{path}\0" for path, lines in files)
        out.append(f"\x1e{commit_hash}\x1f{date}\x1f{author}\0\n{entries}")
    return "".join(out)


# Sample git-log output with RELATIVE dates so window classification is
# deterministic. Four commits land inside the 30-day window; one (mno345)
# lands in the 30-90 day window.
#
# Commit -> touched nodes -> windows:
#   abc123 (Alice):   src/auth -> auth        | 30d + 90d
#   def456 (Bob):     src/auth -> auth        | 30d + 90d
#   ghi789 (Alice):   src/core -> core        | 30d + 90d
#   jkl012 (Charlie): src/auth, src/core      | 30d + 90d
#   mno345 (Alice):   src/core -> core        | 90d only (45 days ago)
#
# Resulting counts: auth 30d=3 / 90d=3, 9 lines in 30d ; core 30d=2 / 90d=3,
# 5 lines in 30d and 25 in 90d.
_SAMPLE_GIT_LOG = _numstat_log(
    [
        ("abc123", _rel_date(2), "Alice", [("src/auth/login.py", 3), ("src/auth/utils.py", 2)]),
        ("def456", _rel_date(3), "Bob", [("src/auth/login.py", 1)]),
        ("ghi789", _rel_date(4), "Alice", [("src/core/engine.py", 4)]),
        ("jkl012", _rel_date(5), "Charlie", [("src/auth/utils.py", 3), ("src/core/engine.py", 1)]),
        ("mno345", _rel_date(45), "Alice", [("src/core/engine.py", 20)]),
    ]
)


# ---------------------------------------------------------------------------
# Unit tests (mocked subprocess)
# ---------------------------------------------------------------------------


class TestGitActivityDataclass:
    def test_frozen(self) -> None:
        activity = GitActivity(
            commits_30d=10,
            commits_90d=30,
            last_commit_date="2026-02-15",
            top_contributors=["alice"],
            activity_level="warm",
        )
        with pytest.raises(AttributeError):
            activity.commits_30d = 5  # type: ignore[misc]

    def test_fields(self) -> None:
        activity = GitActivity(
            commits_30d=25,
            commits_90d=80,
            last_commit_date="2026-02-15",
            top_contributors=["alice", "bob", "charlie"],
            activity_level="hot",
        )
        assert activity.commits_30d == 25
        assert activity.commits_90d == 80
        assert activity.last_commit_date == "2026-02-15"
        assert activity.top_contributors == ["alice", "bob", "charlie"]
        assert activity.activity_level == "hot"


class TestActivityLevels:
    """The log format and the levels it yields, via mocked git output.

    The relative level rule itself is pinned in ``test_activity_by_changed_lines.py``.
    """

    def _run_with_mock(
        self,
        tmp_path: Path,
        stdout: str,
        source_dirs: dict[str, str],
    ) -> dict[str, GitActivity]:
        result = subprocess.CompletedProcess(args=[], returncode=0, stdout=stdout, stderr="")
        with patch(
            "beadloom.infrastructure.git_activity.subprocess.run",
            return_value=result,
        ):
            return analyze_git_activity(tmp_path, source_dirs)

    def test_a_binary_entry_is_a_change_of_zero_lines(self, tmp_path: Path) -> None:
        """``numstat`` reads ``-`` for a binary file: a commit, no lines."""
        stdout = f"\x1ebin1\x1f{_rel_date(1)}\x1fAlice\0\n-\t-\tsrc/db/blob.bin\0"
        result = self._run_with_mock(tmp_path, stdout, {"db": "src/db"})
        assert (result["db"].commits_30d, result["db"].lines_30d) == (1, 0)
        assert result["db"].activity_level == "cool"

    def test_a_rename_entry_counts_at_the_new_path(self, tmp_path: Path) -> None:
        """A rename leaves the path empty and names the old and new paths after it."""
        stdout = (
            f"\x1emv1\x1f{_rel_date(1)}\x1fAlice\0\n"
            "2\t1\t\0src/old/x.py\0src/new/x.py\0"
        )
        result = self._run_with_mock(tmp_path, stdout, {"old": "src/old", "new": "src/new"})
        assert result["new"].lines_30d == 3
        assert result["old"].lines_30d == 0
        assert result["old"].commits_30d == result["new"].commits_30d == 1

    def test_a_record_that_does_not_parse_is_skipped(self, tmp_path: Path) -> None:
        """A header without its three fields, or with no date, is not a commit."""
        stdout = (
            "\x1enot-a-header\0\n1\t0\tsrc/db/x.py\0"
            "\x1eh1\x1fnot-a-date\x1fAlice\0\n1\t0\tsrc/db/x.py\0"
            f"\x1eh2\x1f{_rel_date(1)}\x1fAlice\0\ngarbage\0"
        )
        result = self._run_with_mock(tmp_path, stdout, {"db": "src/db"})
        assert (result["db"].commits_30d, result["db"].lines_30d) == (0, 0)

    def test_a_utc_z_date_is_read(self, tmp_path: Path) -> None:
        """A committer date ending in ``Z`` is read on Python 3.10 as well."""
        when = (datetime.now(tz=timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        stdout = _numstat_log([("z1", when, "Alice", [("src/db/x.py", 2)])])
        result = self._run_with_mock(tmp_path, stdout, {"db": "src/db"})
        assert result["db"].lines_30d == 2

    def test_dormant_activity(self, tmp_path: Path) -> None:
        """0 commits in 90 days -> dormant."""
        result = self._run_with_mock(
            tmp_path,
            "",  # empty git log
            {"legacy": "src/legacy"},
        )
        assert "legacy" in result
        assert result["legacy"].activity_level == "dormant"
        assert result["legacy"].commits_30d == 0
        assert result["legacy"].commits_90d == 0

    def test_dormant_with_old_commits_only(self, tmp_path: Path) -> None:
        """Commits exist but none in 30d, and 0 in 90d window -> dormant.

        Since git log --since='90 days ago' returns nothing for truly old
        commits, dormant means 0 in the 90-day window.
        """
        result = self._run_with_mock(
            tmp_path,
            "",
            {"old_module": "src/old_module"},
        )
        assert "old_module" in result
        assert result["old_module"].activity_level == "dormant"


class TestGracefulDegradation:
    def test_not_a_git_repo(self, tmp_path: Path) -> None:
        """Non-git directory returns empty dict."""
        result = analyze_git_activity(
            tmp_path,
            {"auth": "src/auth"},
        )
        assert result == {}

    def test_git_not_available(self, tmp_path: Path) -> None:
        """When git is not installed, return empty dict."""
        with patch(
            "beadloom.infrastructure.git_activity.subprocess.run",
            side_effect=FileNotFoundError("git not found"),
        ):
            result = analyze_git_activity(
                tmp_path,
                {"auth": "src/auth"},
            )
        assert result == {}

    def test_git_command_fails(self, tmp_path: Path) -> None:
        """When git command returns non-zero, return empty dict."""
        failed = subprocess.CompletedProcess(
            args=[], returncode=128, stdout="", stderr="fatal: not a git repository"
        )
        with patch(
            "beadloom.infrastructure.git_activity.subprocess.run",
            return_value=failed,
        ):
            result = analyze_git_activity(
                tmp_path,
                {"auth": "src/auth"},
            )
        assert result == {}

    def test_git_permission_denied(self, tmp_path: Path) -> None:
        """A PermissionError (OSError subclass) degrades to empty dict."""
        with patch(
            "beadloom.infrastructure.git_activity.subprocess.run",
            side_effect=PermissionError("permission denied"),
        ):
            result = analyze_git_activity(tmp_path, {"auth": "src/auth"})
        assert result == {}

    def test_git_invalid_cwd(self, tmp_path: Path) -> None:
        """A NotADirectoryError (OSError subclass) degrades to empty dict."""
        with patch(
            "beadloom.infrastructure.git_activity.subprocess.run",
            side_effect=NotADirectoryError("bad cwd"),
        ):
            result = analyze_git_activity(tmp_path, {"auth": "src/auth"})
        assert result == {}

    def test_git_subprocess_error(self, tmp_path: Path) -> None:
        """A generic SubprocessError degrades to empty dict."""
        with patch(
            "beadloom.infrastructure.git_activity.subprocess.run",
            side_effect=subprocess.SubprocessError("boom"),
        ):
            result = analyze_git_activity(tmp_path, {"auth": "src/auth"})
        assert result == {}

    def test_git_timeout_expired(self, tmp_path: Path) -> None:
        """TimeoutExpired (SubprocessError subclass) degrades to empty dict.

        The git call uses ``timeout=30``; this proves the narrowed except
        (``OSError, subprocess.SubprocessError``) still catches the timeout
        path the way the prior explicit ``TimeoutExpired`` clause did.
        """
        with patch(
            "beadloom.infrastructure.git_activity.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="git log", timeout=30),
        ):
            result = analyze_git_activity(tmp_path, {"auth": "src/auth"})
        assert result == {}

    def test_git_oserror_base(self, tmp_path: Path) -> None:
        """A bare OSError (the narrowed base) degrades to empty dict."""
        with patch(
            "beadloom.infrastructure.git_activity.subprocess.run",
            side_effect=OSError("generic io failure"),
        ):
            result = analyze_git_activity(tmp_path, {"auth": "src/auth"})
        assert result == {}


class TestMultipleSourceDirs:
    def test_maps_files_to_correct_nodes(self, tmp_path: Path) -> None:
        """Files are correctly mapped to the closest source directory."""
        result = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=_SAMPLE_GIT_LOG,
            stderr="",
        )
        with patch(
            "beadloom.infrastructure.git_activity.subprocess.run",
            return_value=result,
        ):
            activities = analyze_git_activity(
                tmp_path,
                {
                    "auth": "src/auth",
                    "core": "src/core",
                },
            )

        assert "auth" in activities
        assert "core" in activities

        # auth: 3 commits, all within 30d (abc123 touches 2 files but is 1
        # commit, def456 1 commit, jkl012 1 commit) -> 30d=3, 90d=3.
        auth = activities["auth"]
        assert auth.commits_30d == 3
        assert auth.commits_90d == 3
        assert (auth.lines_30d, auth.lines_90d) == (9, 9)
        # Two nodes changed in 30 days: the busier (auth, 9 lines) is hot.
        assert auth.activity_level == "hot"

        # core: 3 commits total (ghi789, jkl012, mno345). Two are within 30d
        # (ghi789, jkl012); mno345 is 45 days ago -> 90d only.
        core = activities["core"]
        assert core.commits_30d == 2
        assert core.commits_90d == 3
        assert (core.lines_30d, core.lines_90d) == (5, 25)
        assert core.activity_level == "cool"

    def test_top_contributors(self, tmp_path: Path) -> None:
        """Top contributors are correctly ranked by commit count."""
        result = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=_SAMPLE_GIT_LOG,
            stderr="",
        )
        with patch(
            "beadloom.infrastructure.git_activity.subprocess.run",
            return_value=result,
        ):
            activities = analyze_git_activity(
                tmp_path,
                {"auth": "src/auth"},
            )

        auth = activities["auth"]
        # Commits touching src/auth: abc123 (Alice), def456 (Bob),
        # jkl012 (Charlie) — each author has exactly 1 auth commit.
        assert len(auth.top_contributors) <= 3
        assert set(auth.top_contributors) == {"Alice", "Bob", "Charlie"}

    def test_empty_source_dirs(self, tmp_path: Path) -> None:
        """Empty source_dirs returns empty dict without calling git."""
        result = analyze_git_activity(tmp_path, {})
        assert result == {}


class TestEmptyGitLog:
    def test_empty_output(self, tmp_path: Path) -> None:
        """Empty git log output creates dormant activities for all nodes."""
        result = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        with patch(
            "beadloom.infrastructure.git_activity.subprocess.run",
            return_value=result,
        ):
            activities = analyze_git_activity(
                tmp_path,
                {"auth": "src/auth", "core": "src/core"},
            )

        assert len(activities) == 2
        for _ref_id, activity in activities.items():
            assert activity.commits_30d == 0
            assert activity.commits_90d == 0
            assert activity.activity_level == "dormant"
            assert activity.last_commit_date == ""
            assert activity.top_contributors == []


# ---------------------------------------------------------------------------
# Integration test with real git repo
# ---------------------------------------------------------------------------


class TestIntegrationRealGitRepo:
    def test_real_git_repo_analysis(self, git_repo: Path) -> None:
        """End-to-end test with a real temporary git repo."""
        # Create source structure
        src_dir = git_repo / "src" / "auth"
        src_dir.mkdir(parents=True)

        # Make several commits
        _make_commit(git_repo, "src/auth/login.py", "v1", "feat: add login")
        _make_commit(git_repo, "src/auth/login.py", "v2", "fix: login bug")
        _make_commit(
            git_repo,
            "src/auth/utils.py",
            "helpers",
            "feat: add auth utils",
            author="Other Dev",
            email="other@example.com",
        )

        result = analyze_git_activity(
            git_repo,
            {"auth": "src/auth"},
        )

        assert "auth" in result
        auth = result["auth"]
        assert auth.commits_30d == 3
        assert auth.commits_90d == 3
        # login.py: "v1" added (1), then replaced by "v2" (1 + 1); utils.py added (1).
        assert (auth.lines_30d, auth.lines_90d) == (4, 4)
        # The only node, and changed: the busiest node of the project is hot.
        assert auth.activity_level == "hot"
        assert auth.last_commit_date != ""
        assert len(auth.top_contributors) == 2
        # Test User has 2 commits, Other Dev has 1
        assert auth.top_contributors[0] == "Test User"

    def test_real_git_repo_multiple_dirs(self, git_repo: Path) -> None:
        """Test with multiple source directories in a real repo."""
        _make_commit(git_repo, "src/auth/login.py", "v1", "feat: auth")
        _make_commit(git_repo, "src/core/engine.py", "v1", "feat: core")
        _make_commit(git_repo, "src/core/engine.py", "v2", "fix: core bug")

        result = analyze_git_activity(
            git_repo,
            {"auth": "src/auth", "core": "src/core"},
        )

        assert "auth" in result
        assert "core" in result
        assert result["auth"].commits_30d == 1
        assert result["core"].commits_30d == 2

    def test_real_git_repo_no_matching_files(self, git_repo: Path) -> None:
        """Source dir exists but no commits match it."""
        _make_commit(git_repo, "other/file.py", "content", "feat: other")

        result = analyze_git_activity(
            git_repo,
            {"auth": "src/auth"},
        )

        assert "auth" in result
        assert result["auth"].commits_30d == 0
        assert result["auth"].activity_level == "dormant"
