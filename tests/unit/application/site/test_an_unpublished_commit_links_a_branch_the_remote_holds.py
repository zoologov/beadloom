"""Which revision a portal built from an unpublished commit links: the edges of the rule.

BDL-080 S4c (``beadloom-e1xo``), BDL-UX #307. The scenarios in
``the_source_link_of_an_unpublished_commit.feature`` hold the order (upstream, the
branch of the same name, the default branch, the commit); these hold what does not
count as a stand-in, and the routes a branch is linked by on every known forge.
"""

from __future__ import annotations

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


def test_a_commit_any_remote_branch_holds_is_pushed(repository: Path) -> None:
    _git(repository, "update-ref", "refs/remotes/fork/topic", "HEAD")
    commit = _head(repository)
    assert source_ref_of(repository, commit) == SourceRef(commit, commit, pushed=True)


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
