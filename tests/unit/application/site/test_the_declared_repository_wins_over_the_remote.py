"""The repository every link goes to: the one the project declares, else its ``origin``.

BDL-076 B4 (``beadloom-ujzb.8``). The card's source link came from the ``origin``
remote and the links in the project's own text from ``site.repo_url``, so a
project whose remote was a mirror, a fork or a CI clone linked its cards and its
About page to two different repositories. The declared address wins: it is the
project's own statement, checked by ``config-check`` for a credential, a query
and a fragment, while the remote is whatever this clone was made from and, for
an SSH remote of a forge served under a path prefix, cannot name the web address
at all. The revision is the commit the site was generated from, in both cases.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.application.site.forge_routes import KNOWN_FORGES
from beadloom.application.site.repository_link import repository_of
from tests.support.committed_project import commit_project

if TYPE_CHECKING:
    from pathlib import Path

_DECLARED = "https://git.acme.example/gitlab/platform/shop"
_FORGES = {"git.acme.example": KNOWN_FORGES["gitlab"]}


def _repository(tmp_path: Path, remote: str | None) -> tuple[Path, str]:
    root = tmp_path / "shop"
    root.mkdir()
    (root / "README.md").write_text("# Shop\n", encoding="utf-8")
    return root, commit_project(root, origin=remote)


def test_a_declared_repository_wins_over_a_remote_that_differs(tmp_path: Path) -> None:
    root, ref = _repository(tmp_path, "git@git.acme.example:platform/shop.git")

    repository = repository_of(root, declared_url=_DECLARED, forges=_FORGES)

    assert repository.url == _DECLARED
    assert repository.source_url("src") == f"{_DECLARED}/-/tree/{ref}/src"


def test_a_declared_repository_links_without_any_remote(tmp_path: Path) -> None:
    root, ref = _repository(tmp_path, None)

    repository = repository_of(root, declared_url=_DECLARED, forges=_FORGES)

    assert repository.file_url("LICENSE") == f"{_DECLARED}/-/blob/{ref}/LICENSE"


def test_without_a_declaration_the_remote_is_read_as_before(tmp_path: Path) -> None:
    root, ref = _repository(tmp_path, "git@github.com:team/shop.git")

    repository = repository_of(root)

    assert repository.url == "https://github.com/team/shop"
    assert repository.source_url("src") == f"https://github.com/team/shop/tree/{ref}/src"


def test_the_declared_forges_apply_to_the_remote_as_well(tmp_path: Path) -> None:
    root, ref = _repository(tmp_path, "ssh://git@git.acme.example:2222/platform/shop.git")

    repository = repository_of(root, forges=_FORGES)

    web = "https://git.acme.example/platform/shop"
    assert repository.source_url("src") == f"{web}/-/tree/{ref}/src"


def test_outside_git_a_declared_repository_has_no_revision_to_link_a_path_at(
    tmp_path: Path,
) -> None:
    root = tmp_path / "shop"
    root.mkdir()

    repository = repository_of(root, declared_url=_DECLARED, forges=_FORGES)

    assert repository.url == _DECLARED
    assert repository.ref == ""
    assert repository.source_url("src") == ""
    assert repository.file_url("LICENSE") == ""
