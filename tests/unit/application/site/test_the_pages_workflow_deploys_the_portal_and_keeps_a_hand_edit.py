"""`docs site --pages-workflow`: a GitHub Pages workflow written for the project's portal.

BDL-076 B2 (``beadloom-qki6``). An adopter's portal is written by ``docs site``;
publishing it takes a workflow that installs the same beadloom, regenerates the
portal, builds it with the Node the scaffold declares and deploys it under the
base the project declares. The workflow is the project's file once written, so
it carries the scaffold's generated marker and a hand edit is never overwritten.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest
import yaml

from beadloom.application.site.pages_workflow import (
    PAGES_WORKFLOW_PATH,
    PagesWorkflowError,
    node_major_of,
    render_pages_workflow,
    site_dir_of,
    write_pages_workflow,
)
from beadloom.application.site.scaffold import read_marker, shipped_files

if TYPE_CHECKING:
    from pathlib import Path

_VERSION = "7.1.0"


def _package_json(engines_node: str) -> str:
    return json.dumps({"name": "portal", "engines": {"node": engines_node}}, indent=2) + "\n"


def _scaffold(tmp_path: Path, engines_node: str = ">=20") -> Path:
    source = tmp_path / "scaffold"
    source.mkdir()
    (source / "package.json").write_text(_package_json(engines_node), encoding="utf-8")
    return source


def _parsed(text: str) -> dict[Any, Any]:
    data = yaml.safe_load(text)
    assert isinstance(data, dict)
    return data


def _steps(workflow: dict[Any, Any], job: str) -> list[dict[str, Any]]:
    steps = workflow["jobs"][job]["steps"]
    assert isinstance(steps, list)
    return steps


def _step_using(workflow: dict[Any, Any], job: str, action: str) -> dict[str, Any]:
    matches = [s for s in _steps(workflow, job) if str(s.get("uses", "")).startswith(action)]
    assert len(matches) == 1, action
    return matches[0]


def _runs(workflow: dict[Any, Any], job: str) -> list[str]:
    return [str(step["run"]) for step in _steps(workflow, job) if "run" in step]


class TestTheNodeMajor:
    @pytest.mark.parametrize(
        ("engines_node", "major"),
        [
            (">=20", "20"),
            (">= 22.3.0", "22"),
            ("^20.11", "20"),
            ("~22", "22"),
            ("20.x", "20"),
            (">=20 <23", "20"),
        ],
    )
    def test_the_lowest_major_the_range_admits(self, engines_node: str, major: str) -> None:
        assert node_major_of(engines_node) == major

    @pytest.mark.parametrize("engines_node", ["*", "", "<22", "latest"])
    def test_a_range_with_no_lowest_major_is_refused(self, engines_node: str) -> None:
        with pytest.raises(PagesWorkflowError, match=r"engines\.node"):
            node_major_of(engines_node)


class TestTheSiteDirectory:
    def test_the_output_directory_relative_to_the_project(self, tmp_path: Path) -> None:
        assert site_dir_of(tmp_path, tmp_path / "docs" / "portal") == "docs/portal"

    def test_an_output_directory_outside_the_project_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(PagesWorkflowError, match="inside the project"):
            site_dir_of(tmp_path / "project", tmp_path / "elsewhere")

    def test_the_project_root_itself_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(PagesWorkflowError, match="inside the project"):
            site_dir_of(tmp_path, tmp_path)


class TestTheWorkflowBody:
    def _workflow(self, **overrides: str) -> dict[Any, Any]:
        values = {"base": "/orders/", "site_dir": "site", "node_major": "20", "version": _VERSION}
        values.update(overrides)
        return _parsed(render_pages_workflow(**values))

    def test_it_parses_as_yaml_with_a_build_and_a_deploy_job(self) -> None:
        workflow = self._workflow()
        assert set(workflow["jobs"]) == {"build", "deploy"}
        assert workflow["jobs"]["deploy"]["needs"] == "build"

    def test_it_deploys_from_the_default_branch_and_on_demand(self) -> None:
        workflow = self._workflow()
        # PyYAML reads the bare key `on` as the boolean true; GitHub reads it as `on`.
        triggers = workflow[True]
        assert set(triggers) == {"push", "workflow_dispatch"}
        guard = workflow["jobs"]["build"]["if"]
        assert "github.event.repository.default_branch" in guard

    def test_it_names_the_base_the_portal_is_built_for(self) -> None:
        workflow = self._workflow(base="/orders/")
        assert workflow["jobs"]["build"]["env"]["PORTAL_BASE"] == "/orders/"
        check = next(run for run in _runs(workflow, "build") if "PORTAL_BASE" in run)
        assert "steps.pages.outputs.base_path" in json.dumps(_steps(workflow, "build"))
        assert "exit 1" in check

    def test_it_sets_up_the_node_major_it_is_given(self) -> None:
        workflow = self._workflow(node_major="22")
        node = _step_using(workflow, "build", "actions/setup-node@")
        assert str(node["with"]["node-version"]) == "22"

    def test_it_installs_the_beadloom_that_wrote_it(self) -> None:
        workflow = self._workflow(version="7.1.0")
        install = next(run for run in _runs(workflow, "build") if "pip install" in run)
        assert '"beadloom[languages]==7.1.0"' in install

    def test_it_regenerates_builds_and_uploads_the_site_directory(self) -> None:
        workflow = self._workflow(site_dir="docs/portal")
        runs = _runs(workflow, "build")
        assert runs.index("beadloom reindex") < runs.index("beadloom docs site --out docs/portal")
        dirs = {
            step["run"]: step.get("working-directory")
            for step in _steps(workflow, "build")
            if "run" in step
        }
        assert dirs["npm ci"] == "docs/portal"
        assert dirs["npm run docs:build"] == "docs/portal"
        upload = _step_using(workflow, "build", "actions/upload-pages-artifact@")
        assert upload["with"]["path"] == "docs/portal/.vitepress/dist"
        _step_using(workflow, "deploy", "actions/deploy-pages@")

    def test_it_names_no_project_of_its_own(self) -> None:
        text = render_pages_workflow(
            base="/orders/", site_dir="site", node_major="20", version=_VERSION
        )
        for token in ("/beadloom/", "zoologov", "github.com/"):
            assert token not in text


class TestWritingTheWorkflow:
    def _write(self, root: Path, source: Path, *, base: str = "/orders/") -> Any:
        return write_pages_workflow(
            root, out_dir=root / "site", base=base, version=_VERSION, source=source
        )

    def test_the_first_run_writes_it_with_the_generated_marker(self, tmp_path: Path) -> None:
        root = tmp_path / "project"
        root.mkdir()
        report = self._write(root, _scaffold(tmp_path, ">=22"))
        written = root / PAGES_WORKFLOW_PATH
        assert (report.outcome, report.path) == ("written", PAGES_WORKFLOW_PATH.as_posix())
        assert (report.base, report.node_major) == ("/orders/", "22")
        text = written.read_text(encoding="utf-8")
        marker = read_marker(text)
        assert marker is not None and marker.intact and marker.version == _VERSION
        assert (
            str(_step_using(_parsed(text), "build", "actions/setup-node@")["with"]["node-version"])
            == "22"
        )

    def test_a_second_run_leaves_it_as_it_is(self, tmp_path: Path) -> None:
        root = tmp_path / "project"
        root.mkdir()
        source = _scaffold(tmp_path)
        self._write(root, source)
        before = (root / PAGES_WORKFLOW_PATH).read_bytes()
        report = self._write(root, source)
        assert report.outcome == "unchanged"
        assert (root / PAGES_WORKFLOW_PATH).read_bytes() == before

    def test_a_changed_base_rewrites_a_workflow_nobody_edited(self, tmp_path: Path) -> None:
        root = tmp_path / "project"
        root.mkdir()
        source = _scaffold(tmp_path)
        self._write(root, source, base="/orders/")
        report = self._write(root, source, base="/stock/")
        assert report.outcome == "updated"
        text = (root / PAGES_WORKFLOW_PATH).read_text(encoding="utf-8")
        assert _parsed(text)["jobs"]["build"]["env"]["PORTAL_BASE"] == "/stock/"

    def test_a_hand_edited_workflow_is_kept_and_reported(self, tmp_path: Path) -> None:
        root = tmp_path / "project"
        root.mkdir()
        source = _scaffold(tmp_path)
        self._write(root, source)
        target = root / PAGES_WORKFLOW_PATH
        edited = target.read_text(encoding="utf-8").replace("ubuntu-latest", "self-hosted")
        target.write_text(edited, encoding="utf-8")
        report = self._write(root, source, base="/stock/")
        assert report.outcome == "kept"
        assert "edited by hand" in report.reason
        assert "--pages-workflow" in report.remediation
        assert target.read_text(encoding="utf-8") == edited

    def test_a_workflow_beadloom_did_not_write_is_kept(self, tmp_path: Path) -> None:
        root = tmp_path / "project"
        target = root / PAGES_WORKFLOW_PATH
        target.parent.mkdir(parents=True)
        own = "name: our own deploy\non: push\njobs: {}\n"
        target.write_text(own, encoding="utf-8")
        report = self._write(root, _scaffold(tmp_path))
        assert report.outcome == "kept"
        assert "no beadloom:generated marker" in report.reason
        assert target.read_text(encoding="utf-8") == own

    def test_the_installed_scaffold_names_the_node_major(self, tmp_path: Path) -> None:
        shipped = json.loads(shipped_files()["package.json"])
        report = write_pages_workflow(
            tmp_path, out_dir=tmp_path / "site", base="/", version=_VERSION
        )
        assert report.node_major == node_major_of(shipped["engines"]["node"])
