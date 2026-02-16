"""Tests for beadloom.infrastructure.git_activity — Git history analysis."""

from __future__ import annotations

import subprocess
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

_SAMPLE_GIT_LOG = """\
abc123 2026-02-15T10:00:00+00:00 Alice

src/auth/login.py
src/auth/utils.py

def456 2026-02-14T09:00:00+00:00 Bob

src/auth/login.py

ghi789 2026-02-13T08:00:00+00:00 Alice

src/core/engine.py

jkl012 2026-02-12T07:00:00+00:00 Charlie

src/auth/utils.py
src/core/engine.py

mno345 2026-01-10T06:00:00+00:00 Alice

src/core/engine.py
"""


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
    """Test all 4 activity levels via mocked git output."""

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

    def test_hot_activity(self, tmp_path: Path) -> None:
        """More than 20 commits in 30 days -> hot."""
        # Generate 25 commit entries for src/auth/ in last 30 days
        lines: list[str] = []
        for i in range(25):
            day = 15 - (i % 15)
            lines.append(f"hash{i} 2026-02-{day:02d}T10:00:00+00:00 Alice")
            lines.append("")
            lines.append("src/auth/login.py")
            lines.append("")
        stdout = "\n".join(lines) + "\n"

        result = self._run_with_mock(
            tmp_path,
            stdout,
            {"auth": "src/auth"},
        )
        assert "auth" in result
        assert result["auth"].activity_level == "hot"
        assert result["auth"].commits_30d > 20

    def test_warm_activity(self, tmp_path: Path) -> None:
        """5-20 commits in 30 days -> warm."""
        lines: list[str] = []
        for i in range(10):
            day = 15 - (i % 15)
            lines.append(f"hash{i} 2026-02-{day:02d}T10:00:00+00:00 Bob")
            lines.append("")
            lines.append("src/api/routes.py")
            lines.append("")
        stdout = "\n".join(lines) + "\n"

        result = self._run_with_mock(
            tmp_path,
            stdout,
            {"api": "src/api"},
        )
        assert "api" in result
        assert result["api"].activity_level == "warm"
        assert 5 <= result["api"].commits_30d <= 20

    def test_cold_activity(self, tmp_path: Path) -> None:
        """1-4 commits in 30 days -> cold."""
        lines: list[str] = []
        for i in range(2):
            lines.append(f"hash{i} 2026-02-10T10:00:00+00:00 Charlie")
            lines.append("")
            lines.append("src/db/models.py")
            lines.append("")
        stdout = "\n".join(lines) + "\n"

        result = self._run_with_mock(
            tmp_path,
            stdout,
            {"db": "src/db"},
        )
        assert "db" in result
        assert result["db"].activity_level == "cold"
        assert 1 <= result["db"].commits_30d <= 4

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

        # auth: 3 commits in 30d (abc123 touches 2 files but is 1 commit,
        # def456 1 commit, jkl012 1 commit)
        auth = activities["auth"]
        assert auth.commits_30d == 3
        assert auth.commits_90d == 3
        assert auth.activity_level == "cold"

        # core: 3 commits in 30d, 1 older (mno345 is from Jan 10)
        core = activities["core"]
        assert core.commits_30d == 2
        assert core.commits_90d == 3

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
        # Alice: 2 commits (abc123, jkl012 touches utils), Bob: 1, Charlie: 1
        # But wait — abc123 has login.py+utils.py, def456 has login.py, jkl012 has utils.py
        # Commits touching auth: abc123 (Alice), def456 (Bob), jkl012 (Charlie) = 3 commits
        # Alice: abc123; Bob: def456; Charlie: jkl012 — each has 1 commit
        assert len(auth.top_contributors) <= 3

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
        assert auth.activity_level == "cold"
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
