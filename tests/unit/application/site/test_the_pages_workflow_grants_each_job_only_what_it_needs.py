"""The Pages workflow grants each job what it needs, runs on one branch and pins every action.

BDL-076 ``beadloom-ujzb.20`` (R2 finding F10). The workflow ``docs site
--pages-workflow`` writes had four weaknesses, each read from its template:

- ``pages: write`` and ``id-token: write`` were granted to the whole workflow,
  so the build job - which runs ``pip install`` and ``npm ci``, third-party
  install scripts - held an OIDC token and Pages write. Only ``deploy`` needs
  them; ``build`` reads the repository and the Pages site.
- ``on: push`` had no branch filter, so every push to every branch started a
  run, and a TAG named like the default branch passed the job's condition,
  because ``github.ref_name`` is a tag's name too.
- Actions were pinned by major tag, which their owner can move.
- Values were JSON-quoted, which keeps YAML's structure but not an Actions
  expression: ``${{ ... }}`` in a base or a directory would be evaluated.

The branch the push trigger names is the one the project's own git records as
its remote's default (``origin/HEAD``), read when the file is written; no branch
is named when git records none, and the job's condition stays exact either way.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from typing import TYPE_CHECKING, Any

import pytest
import yaml

from beadloom.application.site.pages_workflow import (
    PAGES_WORKFLOW_PATH,
    PagesWorkflowError,
    default_branch_of,
    render_pages_workflow,
    site_dir_of,
    write_pages_workflow,
)
from beadloom.application.site.site_config import read_site_config

if TYPE_CHECKING:
    from pathlib import Path

_VERSION = "7.1.0"
_GUARD = "github.ref_type == 'branch' && github.ref_name == github.event.repository.default_branch"
_PINNED = re.compile(r"^[\w.-]+/[\w.-]+@[0-9a-f]{40}$")
_VERSION_COMMENT = re.compile(r"@[0-9a-f]{40} # v\d+\.\d+\.\d+$")


def _render(**overrides: str) -> str:
    values = {
        "base": "/orders/",
        "site_dir": "site",
        "node_major": "22",
        "version": _VERSION,
        "branch": "main",
    }
    values.update(overrides)
    return render_pages_workflow(**values)


def _parsed(text: str) -> dict[Any, Any]:
    data = yaml.safe_load(text)
    assert isinstance(data, dict)
    return data


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)  # noqa: S603, S607


def _repository(tmp_path: Path, default: str | None) -> Path:
    """A project whose git records *default* as its remote's default branch (none for None)."""
    root = tmp_path / "project"
    root.mkdir()
    _git(root, "init", "-q", "-b", "work")
    identity = ("-c", "user.name=t", "-c", "user.email=t@e")
    _git(root, *identity, "commit", "-q", "--allow-empty", "-m", ".")
    if default is not None:
        _git(root, "update-ref", f"refs/remotes/origin/{default}", "HEAD")
        _git(root, "symbolic-ref", "refs/remotes/origin/HEAD", f"refs/remotes/origin/{default}")
    return root


class TestPermissions:
    def test_the_workflow_grants_nothing_a_job_does_not_declare(self) -> None:
        assert _parsed(_render())["permissions"] == {}

    def test_the_build_job_only_reads(self) -> None:
        build = _parsed(_render())["jobs"]["build"]
        assert build["permissions"] == {"contents": "read", "pages": "read"}

    def test_only_the_deploy_job_writes_pages_and_mints_a_token(self) -> None:
        deploy = _parsed(_render())["jobs"]["deploy"]
        assert deploy["permissions"] == {"pages": "write", "id-token": "write"}


class TestTheBranch:
    def test_a_push_starts_it_only_on_the_branch_it_was_written_for(self) -> None:
        triggers = _parsed(_render(branch="trunk"))[True]
        assert triggers["push"] == {"branches": ["trunk"]}
        assert "workflow_dispatch" in triggers

    def test_with_no_known_default_branch_no_branch_is_named(self) -> None:
        text = _render(branch="")
        assert _parsed(text)[True]["push"] is None
        assert "branches:" not in text

    @pytest.mark.parametrize("branch", ["main", ""])
    def test_the_build_runs_only_on_a_branch_that_is_the_default(self, branch: str) -> None:
        """A tag named like the default branch has that ``ref_name``, and ``ref_type`` tag."""
        assert _parsed(_render(branch=branch))["jobs"]["build"]["if"] == _GUARD

    def test_the_default_branch_is_the_one_git_records_for_the_remote(
        self, tmp_path: Path
    ) -> None:
        assert default_branch_of(_repository(tmp_path, "trunk")) == "trunk"

    def test_no_default_branch_is_guessed_when_git_records_none(self, tmp_path: Path) -> None:
        assert default_branch_of(_repository(tmp_path, None)) == ""

    def test_no_default_branch_outside_git(self, tmp_path: Path) -> None:
        assert default_branch_of(tmp_path) == ""

    def test_the_written_workflow_names_the_projects_branch(self, tmp_path: Path) -> None:
        root = _repository(tmp_path, "trunk")
        report = write_pages_workflow(root, out_dir=root / "site", base="/", version=_VERSION)
        assert report.branch == "trunk"
        written = _parsed((root / PAGES_WORKFLOW_PATH).read_text(encoding="utf-8"))
        assert written[True]["push"] == {"branches": ["trunk"]}


class TestPinnedActions:
    def test_every_action_is_pinned_by_a_full_commit_sha(self) -> None:
        workflow = _parsed(_render())
        uses = [
            str(step["uses"])
            for job in workflow["jobs"].values()
            for step in job["steps"]
            if "uses" in step
        ]
        assert len(uses) == 6
        assert [use for use in uses if not _PINNED.match(use)] == []

    def test_every_pin_names_the_release_it_is(self) -> None:
        lines = [line for line in _render().splitlines() if "uses:" in line]
        assert [line for line in lines if not _VERSION_COMMENT.search(line)] == []


class TestExpressions:
    @pytest.mark.parametrize(
        ("value", "named"),
        [
            ({"base": "/${{ github.token }}/"}, "site.base"),
            ({"site_dir": "site-${{ secrets.X }}"}, "--out"),
            ({"branch": "${{ github.token }}"}, "default branch"),
        ],
    )
    def test_an_actions_expression_in_a_value_is_refused_by_name(
        self, value: dict[str, str], named: str
    ) -> None:
        with pytest.raises(PagesWorkflowError, match=re.escape(named)):
            _render(**value)

    def test_an_out_directory_holding_an_expression_is_refused_before_anything_is_written(
        self, tmp_path: Path
    ) -> None:
        with pytest.raises(PagesWorkflowError, match="--out"):
            site_dir_of(tmp_path, tmp_path / "${{ github.token }}")

    def test_a_base_holding_an_expression_is_refused_where_it_was_written(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "orders"
        (root / ".beadloom").mkdir(parents=True)
        (root / ".beadloom" / "config.yml").write_text(
            "site:\n  base: '/${{ github.token }}/'\n", encoding="utf-8"
        )
        config, refusals = read_site_config(root)
        assert [refusal.where for refusal in refusals] == ["site.base"]
        assert "expression" in refusals[0].why
        assert config.base == "/"


@pytest.mark.skipif(shutil.which("actionlint") is None, reason="actionlint is not installed")
@pytest.mark.parametrize("branch", ["main", ""])
def test_actionlint_finds_nothing_in_the_workflow(tmp_path: Path, branch: str) -> None:
    target = tmp_path / ".github" / "workflows" / "portal.yml"
    target.parent.mkdir(parents=True)
    target.write_text(_render(branch=branch), encoding="utf-8")
    result = subprocess.run(  # noqa: S603 - the actionlint on PATH, over a file this test wrote
        ["actionlint", "-no-color", str(target)],  # noqa: S607
        capture_output=True,
        encoding="utf-8",
        check=False,
    )
    assert (result.returncode, result.stdout) == (0, "")
