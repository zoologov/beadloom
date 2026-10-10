"""Which revision a portal built from an unpublished commit links: the edges of the rule.

BDL-080 S4c (``beadloom-e1xo``), BDL-UX #307. The scenarios in
``the_source_link_of_an_unpublished_commit.feature`` hold the order (upstream, the
branch of the same name, the default branch, the commit); these hold what does not
count as a stand-in, and the routes a branch is linked by on every known forge.
"""

from __future__ import annotations

import logging
import subprocess
from typing import TYPE_CHECKING

import pytest

from beadloom.application.site.forge_routes import KNOWN_FORGES, Forge, on_branch
from beadloom.application.site.source_ref import SourceRef, source_ref_of, unpublished_warning

if TYPE_CHECKING:
    from pathlib import Path

    from beadloom.application.site.forge_routes import Route

_IDENTITY = ("-c", "user.name=Shop Team", "-c", "user.email=team@example.invalid")


def _git(cwd: Path, *args: str) -> str:
    result = subprocess.run(  # noqa: S603 - fixed git arguments written by this test
        ["git", *args],  # noqa: S607 - the git on PATH, as the generator reads it
        cwd=cwd,
        capture_output=True,
        encoding="utf-8",
        check=True,
    )
    return result.stdout.strip()


@pytest.fixture()
def repository(tmp_path: Path) -> Path:
    """A repository on ``work`` with two commits; ``origin/main`` holds the first."""
    _git(tmp_path, "init", "-q", "-b", "work")
    _git(tmp_path, "remote", "add", "origin", "https://github.com/team/shop.git")
    _git(tmp_path, *_IDENTITY, "commit", "-q", "--allow-empty", "-m", "first")
    _git(tmp_path, "update-ref", "refs/remotes/origin/main", "HEAD")
    _git(tmp_path, *_IDENTITY, "commit", "-q", "--allow-empty", "-m", "second")
    _git(tmp_path, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")
    return tmp_path


def _head(root: Path) -> str:
    return _git(root, "rev-parse", "HEAD")


def test_a_detached_head_links_the_default_branch(repository: Path) -> None:
    _git(repository, "checkout", "-q", "--detach")
    commit = _head(repository)
    assert source_ref_of(repository, commit) == SourceRef(commit, "main", pushed=False)


def test_a_local_upstream_is_not_a_branch_the_remote_holds(repository: Path) -> None:
    _git(repository, "branch", "-q", "local-base", "HEAD~1")
    _git(repository, "branch", "-q", "--set-upstream-to=local-base", "work")
    commit = _head(repository)
    assert source_ref_of(repository, commit).linked == "main"


def test_an_upstream_this_clone_no_longer_holds_does_not_stand_in(repository: Path) -> None:
    _git(repository, "config", "branch.work.remote", "origin")
    _git(repository, "config", "branch.work.merge", "refs/heads/gone")
    commit = _head(repository)
    assert source_ref_of(repository, commit).linked == "main"


def test_a_commit_a_branch_of_origin_holds_is_pushed(repository: Path) -> None:
    _git(repository, "update-ref", "refs/remotes/origin/topic", "HEAD")
    commit = _head(repository)
    assert source_ref_of(repository, commit) == SourceRef(commit, commit, pushed=True)


def test_a_commit_only_another_remote_holds_is_not_pushed(repository: Path) -> None:
    # The links name origin's address, where a commit only a fork holds is a 404.
    _git(repository, "update-ref", "refs/remotes/fork/topic", "HEAD")
    commit = _head(repository)
    assert source_ref_of(repository, commit) == SourceRef(commit, "main", pushed=False)


def test_an_upstream_on_another_remote_does_not_stand_in(repository: Path) -> None:
    # The reviewer's probe (beadloom-xkrn M1): `git push -u fork topic`, then one more
    # commit. origin has no branch "topic", so a link naming it is the 404 again.
    _git(repository, "remote", "add", "fork", "https://github.com/someone/shop.git")
    _git(repository, "update-ref", "refs/remotes/fork/topic", "HEAD~1")
    _git(repository, "config", "branch.work.remote", "fork")
    _git(repository, "config", "branch.work.merge", "refs/heads/topic")
    commit = _head(repository)
    assert source_ref_of(repository, commit) == SourceRef(commit, "main", pushed=False)


def test_an_upstream_on_another_remote_gives_way_to_origins_branch_of_the_same_name(
    repository: Path,
) -> None:
    _git(repository, "remote", "add", "fork", "https://github.com/someone/shop.git")
    _git(repository, "update-ref", "refs/remotes/fork/topic", "HEAD~1")
    _git(repository, "update-ref", "refs/remotes/origin/work", "HEAD~1")
    _git(repository, "config", "branch.work.remote", "fork")
    _git(repository, "config", "branch.work.merge", "refs/heads/topic")
    commit = _head(repository)
    assert source_ref_of(repository, commit).linked == "work"


@pytest.mark.parametrize(
    ("kind", "route", "link"),
    [
        ("github", "raw", "https://forge.example/o/r/raw/main/a.py"),
        ("gitlab", "blob", "https://forge.example/o/r/-/blob/main/a.py"),
        ("bitbucket", "raw", "https://forge.example/o/r/raw/main/a.py"),
        ("gitea", "tree", "https://forge.example/o/r/src/branch/main/a.py"),
        ("gitea", "raw", "https://forge.example/o/r/raw/branch/main/a.py"),
        ("azure", "blob", "https://forge.example/o/r?path=/a.py&version=GBmain"),
    ],
)
def test_a_branch_is_linked_by_the_route_its_forge_serves_a_branch_under(
    kind: str, route: Route, link: str
) -> None:
    forge = on_branch(KNOWN_FORGES[kind])
    assert forge.link(route, "https://forge.example/o/r", "main", "a.py") == link


def test_azure_reads_a_file_of_a_branch_as_a_branch() -> None:
    forge = on_branch(KNOWN_FORGES["azure"])
    raw = forge.link("raw", "https://dev.azure.com/o/p/_git/r", "main", "a.py")
    assert "versionDescriptor.version=main&versionDescriptor.versionType=branch" in raw


def test_a_declared_template_gets_the_branch_in_its_ref() -> None:
    forge = Forge(kind="", tree="{url}/view/{ref}/{path}", blob="", raw="")
    assert on_branch(forge) is forge


def test_a_pushed_commit_and_no_commit_get_no_warning() -> None:
    assert unpublished_warning(None) is None
    assert unpublished_warning(SourceRef("a" * 40, "a" * 40, pushed=True)) is None


def test_the_upstream_of_the_branch_built_from_stands_in_while_another_branch_has_its_own(
    repository: Path,
) -> None:
    _git(repository, "update-ref", "refs/remotes/origin/release", "HEAD~1")
    _git(repository, "update-ref", "refs/remotes/origin/another", "HEAD~1")
    _git(repository, "branch", "-q", "a-side", "HEAD~1")
    _git(repository, "branch", "-q", "--set-upstream-to=origin/another", "a-side")
    _git(repository, "branch", "-q", "--set-upstream-to=origin/release", "work")
    commit = _head(repository)

    assert source_ref_of(repository, commit) == SourceRef(commit, "release", pushed=False)


def test_without_git_the_links_keep_the_commit_and_the_debug_log_says_why(
    repository: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    commit = _head(repository)
    monkeypatch.setenv("PATH", str(repository / "no-git-here"))
    caplog.set_level(logging.DEBUG, logger="beadloom.application.site.source_ref")

    found = source_ref_of(repository, commit)

    assert found == SourceRef(commit, commit, pushed=True)
    messages = [record.getMessage() for record in caplog.records]
    assert len(messages) == 1
    assert messages[0].startswith("git is not available to read the remote branches: ")
    assert "git" in messages[0].removeprefix("git is not available to read the remote branches: ")


def test_the_warning_on_a_branch_says_where_the_links_point_and_how_to_link_the_commit() -> None:
    warning = unpublished_warning(SourceRef("0123456789abcdef" * 2, "main", pushed=False))

    assert warning == (
        "Warning: the portal was built from 0123456789ab, which is on no branch of origin, "
        "so its source links point at main instead; a path that exists only in that commit "
        "is not there. Push the commit and run `beadloom docs site` again for links to it."
    )


def test_the_warning_without_a_stand_in_says_the_links_stay_dead_and_how_to_name_one() -> None:
    commit = "0123456789abcdef" * 2
    warning = unpublished_warning(SourceRef(commit, commit, pushed=False))

    assert warning == (
        "Warning: the portal was built from 0123456789ab, which is on no branch of origin, "
        "and no branch of origin stands in for it, so its source links point at "
        "0123456789ab and stay dead until it is pushed. Push it, or record origin's default "
        "branch with `git remote set-head origin --auto`, and run `beadloom docs site` again."
    )
