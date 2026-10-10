"""The release harness's own logic: what it accepts, how it reports, and which exit it returns.

The harness itself installs an artifact and runs it on a throwaway project, which takes
minutes and a network. These tests stop short of that: they exercise the parts that decide
what a run SAYS — the artifact argument and the extra it is installed with, the exit code a
report maps to, that a step which fails after the checks have started leaves the checks that
ran in the report, that a check the run was not equipped to make is named rather than counted,
and the verdict each check reaches from what a child printed or wrote, in the shape 9.0.0
leaves and in the shape 8.0.0 leaves.

The file sits under ``tests/self_check/`` because the harness is this repository's release
tooling rather than product code, so no graph node owns it.
"""

from __future__ import annotations

import json
import os
import stat
import sys
from typing import TYPE_CHECKING

import pytest

import beadloom
from tests.release import verify_the_release as harness
from tests.release.verify_the_release import (
    Artifact,
    CannotRunError,
    Done,
    Report,
    Room,
    check_activity,
    check_built_portal,
    check_fsd_lint,
    check_fsd_scaffold,
    check_scaffold_surfaces,
    check_shallow_history,
    check_site_alias,
    check_versions,
    find_npm,
    install_spec,
    parse_artifact,
)
from tests.support.fsd_tree import FSD_TREE

if TYPE_CHECKING:
    from pathlib import Path

_RELEASE = "9.0.0"


def _report(*outcomes: tuple[str, str]) -> Report:
    """A report holding one check per ``(kind, status)`` pair, in order."""
    report = Report(artifact=f"beadloom=={_RELEASE}", release=_RELEASE)
    for number, (kind, status) in enumerate(outcomes):
        report.checks.append(harness.Check(f"check {number}", kind, status, "detail"))
    return report


class TestTheArtifactArgument:
    def test_an_exact_pin_names_its_version(self) -> None:
        assert parse_artifact("beadloom==9.0.0") == Artifact(
            "beadloom==9.0.0", "9.0.0", is_wheel=False
        )

    def test_a_wheel_names_the_version_in_its_file_name(self, tmp_path: Path) -> None:
        wheel = tmp_path / "beadloom-9.0.0-py3-none-any.whl"
        wheel.write_bytes(b"")

        artifact = parse_artifact(str(wheel))

        assert (artifact.claimed_version, artifact.is_wheel) == ("9.0.0", True)

    @pytest.mark.parametrize("argument", ["beadloom>=7", "beadloom", "other==9.0.0"])
    def test_anything_but_an_exact_pin_or_a_wheel_cannot_run(self, argument: str) -> None:
        with pytest.raises(CannotRunError) as raised:
            parse_artifact(argument)

        assert raised.value.exit_code == 2

    def test_a_wheel_path_with_no_file_cannot_run(self, tmp_path: Path) -> None:
        with pytest.raises(CannotRunError, match="no wheel"):
            parse_artifact(str(tmp_path / "beadloom-9.0.0-py3-none-any.whl"))

    def test_a_pin_is_installed_with_the_languages_extra(self) -> None:
        spec = install_spec(Artifact("beadloom==9.0.0", "9.0.0", is_wheel=False))

        assert spec == "beadloom[languages]==9.0.0"

    def test_a_wheel_is_installed_with_the_languages_extra(self, tmp_path: Path) -> None:
        wheel = tmp_path / "beadloom-9.0.0-py3-none-any.whl"

        spec = install_spec(Artifact(str(wheel), "9.0.0", is_wheel=True))

        assert spec == f"{wheel}[languages]"

    def test_the_default_release_is_the_version_this_tree_declares(self) -> None:
        assert beadloom.__version__ == harness.DEFAULT_RELEASE


class TestTheExitCode:
    @pytest.mark.parametrize(
        ("outcomes", "expected"),
        [
            ((("version", "PASS"), ("behaviour", "PASS")), 0),
            ((("version", "PASS"), ("behaviour", "FAIL")), 4),
            ((("version", "PASS"), ("behaviour", "NOT RUN")), 4),
            ((("version", "FAIL"), ("behaviour", "FAIL")), 3),
            ((("version", "PASS"), ("behaviour", "CANNOT RUN")), 2),
            ((("version", "PASS"), ("behaviour", "FAIL"), ("behaviour", "CANNOT RUN")), 4),
            ((("version", "PASS"), ("behaviour", "CANNOT RUN"), ("behaviour", "NOT RUN")), 2),
            ((("version", "FAIL"), ("behaviour", "CANNOT RUN")), 3),
            ((("version", "PASS"), ("behaviour", "SKIPPED")), 0),
            ((("version", "PASS"), ("behaviour", "SKIPPED"), ("behaviour", "FAIL")), 4),
            ((("version", "PASS"), ("behaviour", "SKIPPED"), ("behaviour", "CANNOT RUN")), 2),
        ],
    )
    def test_the_exit_follows_the_most_telling_outcome(
        self, outcomes: tuple[tuple[str, str], ...], expected: int
    ) -> None:
        assert _report(*outcomes).exit_code() == expected

    def test_the_first_failure_is_the_earliest_check_that_did_not_pass(self) -> None:
        report = _report(("version", "PASS"), ("behaviour", "CANNOT RUN"), ("version", "FAIL"))

        first = report.first_failure()

        assert first is not None
        assert first.name == "check 1"

    def test_a_skipped_check_is_not_the_first_failure(self) -> None:
        report = _report(("version", "PASS"), ("behaviour", "SKIPPED"), ("behaviour", "FAIL"))

        first = report.first_failure()

        assert first is not None
        assert first.name == "check 2"


class _CloneFails(Room):
    """A room whose every git command fails, as a clone does on a broken file:// URL."""

    def git(self, project: Path, *args: str, when: int | None = None) -> harness.Done:
        raise CannotRunError(f"git {' '.join(args)} exited 128: fatal: repository not found")


class TestAStepThatFailsAfterTheChecksStarted:
    def test_a_failed_clone_is_recorded_and_raises_nothing(self, tmp_path: Path) -> None:
        report = _report(("version", "PASS"))

        check_shallow_history(_CloneFails(tmp_path, None), tmp_path / "quayside", report)

        shallow = report.checks[-1]
        assert (shallow.name.split(":")[0], shallow.status) == ("shallow history", "CANNOT RUN")
        assert "repository not found" in shallow.detail
        assert report.exit_code() == 2

    def test_the_report_of_what_ran_is_printed_and_the_run_exits_2(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        wheel = tmp_path / "beadloom-9.0.0-py3-none-any.whl"
        wheel.write_bytes(b"")
        record = tmp_path / "record.json"

        def ran_the_versions(room: Room, artifact: Artifact, report: Report) -> None:
            report.record("version: beadloom --version", "version", passed=True, detail="9.0.0")

        def project_cannot_be_committed(room: Room, report: Report) -> None:
            raise CannotRunError("git commit exited 128: fatal: unable to write")

        monkeypatch.setattr(harness, "prepare", lambda *_args: None)
        monkeypatch.setattr(harness, "check_versions", ran_the_versions)
        monkeypatch.setattr(harness, "check_languages", lambda *_args: None)
        monkeypatch.setattr(harness, "check_project", project_cannot_be_committed)
        monkeypatch.setattr(harness, "check_fsd_project", lambda *_args: None)

        code = harness.main([str(wheel), "--record-json", str(record)])

        printed = capsys.readouterr().out
        assert code == 2
        assert "PASS     version: beadloom --version" in printed
        assert "CANNOT RUN" in printed
        assert "unable to write" in printed
        assert '"exit": 2' in record.read_text(encoding="utf-8")


#: The checks of the adopter project, by the stage each check's name begins with.
_PROJECT_STAGES = (
    "init",
    "reindex",
    "site alias",
    "activity",
    "shallow history",
    "portal scaffold",
    "portal steiger",
    "portal brand",
    "portal footer",
    "portal build",
    "portal assets",
    "portal lint:fsd",
    "pages workflow",
)

#: The checks of the Feature-Sliced project, by the stage each check's name begins with.
_FSD_STAGES = ("fsd init", "fsd preset", "fsd rules", "fsd steiger", "fsd lint")


def _verify(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, fsd_project: bool = False
) -> Report:
    """A run whose environment is taken as prepared and whose version checks hold.

    The Feature-Sliced project is left out unless *fsd_project* asks for it, so a test of
    the adopter project's stages runs no child of the other project.
    """

    def ran_the_versions(room: Room, artifact: Artifact, report: Report) -> None:
        report.record("version: beadloom --version", "version", passed=True, detail="9.0.0")

    monkeypatch.setattr(harness, "prepare", lambda *_args: None)
    monkeypatch.setattr(harness, "check_versions", ran_the_versions)
    monkeypatch.setattr(harness, "check_languages", lambda *_args: None)
    if not fsd_project:
        monkeypatch.setattr(harness, "check_fsd_project", lambda *_args: None)
    return harness.verify(
        Artifact("beadloom==9.0.0", "9.0.0", is_wheel=False),
        release=_RELEASE,
        python="3.12",
        node_bin=None,
        workdir=tmp_path,
    )


def _status_of(report: Report, stages: tuple[str, ...] = _PROJECT_STAGES) -> dict[str, str]:
    """Each of *stages* mapped to the status of the check that names it."""
    return {
        stage: next(
            (
                check.status
                for check in report.checks
                if check.name == stage or check.name.startswith(f"{stage}:")
            ),
            "ABSENT",
        )
        for stage in stages
    }


class TestAProjectStepThatCannotRunListsTheChecksItStopped:
    def test_a_project_that_cannot_be_written_lists_every_project_check(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def cannot_write(room: Room, root: Path, now: int) -> None:
            raise CannotRunError("git init exited 128: fatal: cannot mkdir")

        monkeypatch.setattr(harness, "write_project", cannot_write)

        report = _verify(tmp_path, monkeypatch)

        assert set(_status_of(report).values()) == {"NOT RUN"}
        assert report.exit_code() == 2

    def test_a_commit_that_fails_after_init_lists_the_checks_after_it(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        class _InitHoldsCommitFails(_CloneFails):
            def beadloom(self, project: Path, *args: str) -> Done:
                return Done(0, "", "")

        monkeypatch.setattr(harness, "Room", _InitHoldsCommitFails)
        monkeypatch.setattr(harness, "write_project", lambda *_args: None)
        monkeypatch.setattr(harness, "declare_portal", lambda *_args: None)

        report = _verify(tmp_path, monkeypatch)

        statuses = _status_of(report)
        assert statuses.pop("init") == "PASS"
        assert set(statuses.values()) == {"NOT RUN"}
        assert report.exit_code() == 2

    def test_a_feature_sliced_project_that_cannot_be_written_lists_every_fsd_check(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def cannot_write(room: Room, root: Path) -> None:
            raise CannotRunError("git init exited 128: fatal: cannot mkdir")

        monkeypatch.setattr(harness, "check_project", lambda *_args: None)
        monkeypatch.setattr(harness, "write_fsd_project", cannot_write)

        report = _verify(tmp_path, monkeypatch, fsd_project=True)

        assert set(_status_of(report, _FSD_STAGES).values()) == {"NOT RUN"}
        assert report.exit_code() == 2


class _PrintsNoJson(Room):
    """A room whose every child exits 0 and prints text that is not JSON."""

    def run(self, command: list[str], cwd: Path, env: dict[str, str] | None = None) -> Done:
        if command[-1] == "--version":
            return Done(0, "beadloom, version 9.0.0\n", "")
        if command[0].endswith("python") and "_graph" in command[-1]:
            return Done(0, '{"src/quayside/dock": "quayside-dock"}', "")
        return Done(0, "Warning: the index is older than the graph\n", "")


class TestAChildThatPrintsNoJson:
    def test_the_version_probe_is_a_failed_check_that_quotes_the_text(
        self, tmp_path: Path
    ) -> None:
        report = _report()

        check_versions(_PrintsNoJson(tmp_path, None), Artifact("x", "9.0.0", False), report)

        probed = [check for check in report.checks if "__version__" in check.name]
        assert [check.status for check in probed] == ["FAIL"]
        assert "the index is older than the graph" in probed[0].detail

    def test_ctx_json_is_a_failed_activity_check_that_quotes_the_text(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(harness, "_CHANGED_IN_90_DAYS", "src/quayside/dock")
        monkeypatch.setattr(harness, "_UNTOUCHED", "src/quayside/dock")
        report = _report()

        check_activity(_PrintsNoJson(tmp_path, None), tmp_path, report)

        activity = report.checks[-1]
        assert activity.status == "FAIL"
        assert "the index is older than the graph" in activity.detail

    def test_a_graph_probe_that_prints_no_json_is_a_failed_activity_check(
        self, tmp_path: Path
    ) -> None:
        class _GraphProbeFails(_PrintsNoJson):
            def run(
                self, command: list[str], cwd: Path, env: dict[str, str] | None = None
            ) -> Done:
                return Done(0, "ModuleNotFoundError: No module named 'yaml'\n", "")

        report = _report()

        check_activity(_GraphProbeFails(tmp_path, None), tmp_path, report)

        activity = report.checks[-1]
        assert activity.status == "FAIL"
        assert "No module named 'yaml'" in activity.detail


def _stage_statuses(report: Report) -> dict[str, str]:
    """Each check's stage (its name up to the colon) mapped to its status."""
    return {check.name.split(":")[0]: check.status for check in report.checks}


class TestWhatARunDidNotRun:
    """A check the run was not equipped to make is named under the verdict, not hidden."""

    _REASON = "no node on PATH; pass --node-bin with a Node 22+ bin directory"

    def _run_without_node(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, record: Path
    ) -> int:
        wheel = tmp_path / "beadloom-9.0.0-py3-none-any.whl"
        wheel.write_bytes(b"")

        def ran_the_versions(room: Room, artifact: Artifact, report: Report) -> None:
            report.record("version: beadloom --version", "version", passed=True, detail="9.0.0")

        def built_no_portal(room: Room, report: Report) -> None:
            report.record("init: beadloom init --yes exits 0", "behaviour", passed=True, detail="")
            report.skipped(
                "portal build: npm ci and npm run docs:build", "behaviour", self._REASON
            )
            report.skipped("portal lint:fsd: npm run lint:fsd passes", "behaviour", self._REASON)

        monkeypatch.setattr(harness, "prepare", lambda *_args: None)
        monkeypatch.setattr(harness, "check_versions", ran_the_versions)
        monkeypatch.setattr(harness, "check_languages", lambda *_args: None)
        monkeypatch.setattr(harness, "check_project", built_no_portal)
        monkeypatch.setattr(harness, "check_fsd_project", lambda *_args: None)
        return harness.main([str(wheel), "--record-json", str(record)])

    def test_the_summary_names_the_checks_it_did_not_run_and_why(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        self._run_without_node(tmp_path, monkeypatch, tmp_path / "record.json")

        printed = capsys.readouterr().out
        not_run = [line for line in printed.splitlines() if line.startswith("Not run by this run")]
        assert not_run == [f"Not run by this run: portal build, portal lint:fsd ({self._REASON})"]

    def test_the_verdict_counts_only_the_checks_that_ran(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        code = self._run_without_node(tmp_path, monkeypatch, tmp_path / "record.json")

        printed = capsys.readouterr().out
        assert (code, "VERDICT: 2 of 2 checks that ran hold (exit 0)" in printed) == (0, True)

    def test_the_record_names_every_check_its_status_and_the_ones_skipped(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        record = tmp_path / "record.json"

        self._run_without_node(tmp_path, monkeypatch, record)

        payload = json.loads(record.read_text(encoding="utf-8"))
        assert (
            [(check["name"].split(":")[0], check["status"]) for check in payload["checks"]],
            payload["skipped"],
            payload["exit"],
        ) == (
            [
                ("version", "PASS"),
                ("init", "PASS"),
                ("portal build", "SKIPPED"),
                ("portal lint", "SKIPPED"),
            ],
            [
                "portal build: npm ci and npm run docs:build",
                "portal lint:fsd: npm run lint:fsd passes",
            ],
            0,
        )


def _executable(directory: Path, name: str) -> None:
    """An executable file *name* in *directory*, for ``shutil.which`` to find."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _node_room(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    node: str | None,
    npm: bool,
    asked: bool,
) -> Room:
    """A room whose only tools are the *node* (its ``--version``) and *npm* asked for.

    When *asked*, they sit in the directory ``--node-bin`` names and ``PATH`` holds nothing;
    otherwise they are on ``PATH`` and no ``--node-bin`` is given.
    """
    tools = tmp_path / "tools"
    tools.mkdir()
    if node is not None:
        _executable(tools, "node")
    if npm:
        _executable(tools, "npm")
    monkeypatch.setenv("PATH", str(tmp_path / "nothing" if asked else tools))

    class _Node(Room):
        def run(self, command: list[str], cwd: Path, env: dict[str, str] | None = None) -> Done:
            return Done(0, f"{node}\n", "")

    return _Node(tmp_path / "work", tools if asked else None)


class TestTheNodeThePortalBuildRunsUnder:
    @pytest.mark.parametrize(
        ("node", "npm", "reason"),
        [
            ("v18.20.8", True, "older than 22"),
            (None, True, "no node on PATH"),
            ("v22.9.0", False, "no npm"),
        ],
    )
    def test_without_node_bin_an_unusable_node_skips_the_npm_checks_and_says_why(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        node: str | None,
        npm: bool,
        reason: str,
    ) -> None:
        room = _node_room(tmp_path, monkeypatch, node=node, npm=npm, asked=False)

        _described, skip = find_npm(room, asked=False)

        assert reason in skip

    def test_without_node_bin_a_node_22_and_npm_on_path_run_the_npm_checks(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        room = _node_room(tmp_path, monkeypatch, node="v22.9.0", npm=True, asked=False)

        described, skip = find_npm(room, asked=False)

        assert (described.split()[0], skip) == ("v22.9.0", "")

    @pytest.mark.parametrize(
        ("node", "npm"), [("v18.20.8", True), (None, True), ("v22.9.0", False)]
    )
    def test_a_node_bin_that_holds_no_usable_node_cannot_run(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        node: str | None,
        npm: bool,
    ) -> None:
        room = _node_room(tmp_path, monkeypatch, node=node, npm=npm, asked=True)

        with pytest.raises(CannotRunError) as raised:
            find_npm(room, asked=True)

        assert raised.value.exit_code == 2


#: Every file a 9.0.0 portal scaffold holds that the surfaces checks read.
_SURFACE_FILES = (
    "steiger.config.js",
    *harness.BRAND_FILES,
    f"{harness.FOOTER_WIDGET}/index.js",
)


def _scaffold(root: Path, *, omit: str = "", scripts: dict[str, str] | None = None) -> Path:
    """A portal scaffold under *root* holding every surface but *omit*, with *scripts*."""
    site = root / "site"
    site.mkdir()
    for relative in _SURFACE_FILES:
        if relative != omit:
            (site / relative).parent.mkdir(parents=True, exist_ok=True)
            (site / relative).write_text("x", encoding="utf-8")
    shipped = {"docs:build": "vitepress build", "lint:fsd": "steiger .vitepress/theme"}
    (site / "package.json").write_text(
        json.dumps({"scripts": shipped if scripts is None else scripts}), encoding="utf-8"
    )
    return site


class TestThePortalScaffoldSurfaces:
    def test_a_scaffold_holding_every_surface_passes_the_three_checks(
        self, tmp_path: Path
    ) -> None:
        report = _report()

        check_scaffold_surfaces(_scaffold(tmp_path), report)

        assert _stage_statuses(report) == {
            "portal steiger": "PASS",
            "portal brand": "PASS",
            "portal footer": "PASS",
        }

    @pytest.mark.parametrize(
        ("omit", "stage"),
        [
            ("steiger.config.js", "portal steiger"),
            ("public/brand/beadloom-icon.svg", "portal brand"),
            ("public/brand/beadloom-favicon.svg", "portal brand"),
            ("public/brand/beadloom-favicon.png", "portal brand"),
            ("public/brand/beadloom-favicon-dark.png", "portal brand"),
            (".vitepress/theme/widgets/powered-by/index.js", "portal footer"),
        ],
    )
    def test_an_absent_surface_fails_its_check_and_names_the_file(
        self, tmp_path: Path, omit: str, stage: str
    ) -> None:
        report = _report()

        check_scaffold_surfaces(_scaffold(tmp_path, omit=omit), report)

        failed = [check for check in report.checks if check.status == "FAIL"]
        assert [(check.name.split(":")[0], omit in check.detail) for check in failed] == [
            (stage, True)
        ]

    def test_a_package_json_without_the_lint_fsd_script_fails_the_steiger_check(
        self, tmp_path: Path
    ) -> None:
        report = _report()

        check_scaffold_surfaces(_scaffold(tmp_path, scripts={"docs:build": "x"}), report)

        assert _stage_statuses(report)["portal steiger"] == "FAIL"


def _built(root: Path, *, omit: str = "", page: str = "") -> Path:
    """A built portal under *root*: the brand files but *omit*, and an index page."""
    site = root / "site"
    dist = site / ".vitepress" / "dist"
    (dist / "brand").mkdir(parents=True)
    for relative in harness.BRAND_FILES:
        name = relative.rsplit("/", 1)[-1]
        if name != omit:
            (dist / "brand" / name).write_text("x", encoding="utf-8")
    shipped = (
        '<link rel="icon" href="/quayside/brand/beadloom-favicon.svg">'
        "<footer>Powered by Beadloom</footer>"
    )
    (dist / "index.html").write_text(page or shipped, encoding="utf-8")
    return site


class TestTheBuiltPortal:
    def test_a_built_portal_serving_the_brand_and_the_footer_passes(self, tmp_path: Path) -> None:
        report = _report()

        check_built_portal(_built(tmp_path), report)

        assert [check.status for check in report.checks] == ["PASS"]

    @pytest.mark.parametrize(
        ("omit", "page", "named"),
        [
            ("beadloom-favicon-dark.png", "", "beadloom-favicon-dark.png"),
            ("", "<footer>Powered by Beadloom</footer>", "favicon link"),
            ("", '<link rel="icon" href="/brand/beadloom-favicon.svg">', "Powered by Beadloom"),
        ],
    )
    def test_a_built_portal_missing_a_piece_fails_and_names_it(
        self, tmp_path: Path, omit: str, page: str, named: str
    ) -> None:
        report = _report()

        check_built_portal(_built(tmp_path, omit=omit, page=page), report)

        assert [(check.status, named in check.detail) for check in report.checks] == [
            ("FAIL", True)
        ]


def _ctx_room(tmp_path: Path, printed: str) -> Room:
    """A room whose every ``beadloom`` prints *printed* and exits 0."""

    class _Ctx(Room):
        def beadloom(self, project: Path, *args: str) -> Done:
            return Done(0, printed, "")

    return _Ctx(tmp_path, None)


_INFO_LINE = (
    "  [info] Node 'quayside-portal' declares kind 'site', read as 'service' (an accepted alias)"
)


class TestTheSiteAlias:
    @pytest.mark.parametrize(("kind", "status"), [("service", "PASS"), ("site", "FAIL")])
    def test_ctx_json_must_read_the_site_node_as_a_service(
        self, tmp_path: Path, kind: str, status: str
    ) -> None:
        room = _ctx_room(tmp_path, json.dumps({"focus": {"kind": kind}}))
        report = _report()

        check_site_alias(room, tmp_path, _INFO_LINE, report)

        ctx = [check for check in report.checks if "ctx --json" in check.name]
        assert [(check.status, repr(kind) in check.detail) for check in ctx] == [(status, True)]

    @pytest.mark.parametrize(
        ("reindexed", "status"), [(_INFO_LINE, "PASS"), ("Reindexed 12 nodes", "FAIL")]
    )
    def test_the_reindex_must_print_the_alias_info_line(
        self, tmp_path: Path, reindexed: str, status: str
    ) -> None:
        room = _ctx_room(tmp_path, json.dumps({"focus": {"kind": "service"}}))
        report = _report()

        check_site_alias(room, tmp_path, reindexed, report)

        info = [check.status for check in report.checks if "[info]" in check.name]
        assert info == [status]

    def test_ctx_that_prints_no_json_fails_and_quotes_it(self, tmp_path: Path) -> None:
        room = _ctx_room(tmp_path, "Error: no node 'quayside-portal'\n")
        report = _report()

        check_site_alias(room, tmp_path, _INFO_LINE, report)

        ctx = [check for check in report.checks if "ctx --json" in check.name]
        assert [(check.status, "no node 'quayside-portal'" in check.detail) for check in ctx] == [
            ("FAIL", True)
        ]


class _DevPython(Room):
    """A room whose environment's python is this suite's interpreter, which carries PyYAML."""

    def run(self, command: list[str], cwd: Path, env: dict[str, str] | None = None) -> Done:
        if command[0] == str(self.bin / "python"):
            command = [sys.executable, *command[1:]]
        return super().run(command, cwd, {**os.environ} if env is None else env)


def _fsd_project(
    root: Path, *, preset: str, rules: tuple[str, ...], scripts: dict[str, str]
) -> Path:
    """What ``init`` leaves in a Feature-Sliced project: its config, rules and package.json."""
    graph = root / ".beadloom" / "_graph"
    graph.mkdir(parents=True)
    (root / ".beadloom" / "config.yml").write_text(f"preset: {preset}\n", encoding="utf-8")
    listed = "".join(f"  - name: {name}\n    severity: error\n" for name in rules)
    (graph / "rules.yml").write_text(f"version: 3\nrules:\n{listed}", encoding="utf-8")
    (root / "package.json").write_text(json.dumps({"scripts": scripts}), encoding="utf-8")
    return root


class TestTheFeatureSlicedProject:
    def test_what_9_0_0_init_writes_passes_the_preset_rules_and_steiger_checks(
        self, tmp_path: Path
    ) -> None:
        project = _fsd_project(
            tmp_path,
            preset="fsd",
            rules=harness.FSD_RULES,
            scripts={"dev": "vite", "lint:fsd": "steiger ./src"},
        )
        report = _report()

        check_fsd_scaffold(_DevPython(tmp_path, None), project, report)

        assert _stage_statuses(report) == {
            "fsd preset": "PASS",
            "fsd rules": "PASS",
            "fsd steiger": "PASS",
        }

    def test_what_8_0_0_init_writes_fails_all_three(self, tmp_path: Path) -> None:
        project = _fsd_project(
            tmp_path,
            preset="monolith",
            rules=("domain-needs-parent", "feature-needs-parent"),
            scripts={"dev": "vite"},
        )
        report = _report()

        check_fsd_scaffold(_DevPython(tmp_path, None), project, report)

        assert set(_stage_statuses(report).values()) == {"FAIL"}

    def test_a_rule_set_missing_one_names_the_missing_rule(self, tmp_path: Path) -> None:
        project = _fsd_project(
            tmp_path,
            preset="fsd",
            rules=tuple(name for name in harness.FSD_RULES if name != "fsd-slice-shape"),
            scripts={"lint:fsd": "steiger ./src"},
        )
        report = _report()

        check_fsd_scaffold(_DevPython(tmp_path, None), project, report)

        rules = [check for check in report.checks if check.name.startswith("fsd rules")]
        assert [(check.status, "fsd-slice-shape" in check.detail) for check in rules] == [
            ("FAIL", True)
        ]

    @pytest.mark.parametrize(
        ("returncode", "output", "status"),
        [
            (1, "Error: your code does not pass the rules\n  fsd-layers: features-cart\n", "PASS"),
            (0, "Graph: 21 nodes, 31 edges (preset: monolith)\n", "FAIL"),
            (2, "Error: No such option: --yes\n", "FAIL"),
        ],
    )
    def test_init_must_exit_1_naming_the_planted_crossing(
        self, tmp_path: Path, returncode: int, output: str, status: str
    ) -> None:
        class _Init(Room):
            def beadloom(self, project: Path, *args: str) -> Done:
                return Done(returncode, output, "")

        report = _report()

        harness.check_fsd_init(_Init(tmp_path, None), tmp_path, report)

        assert [check.status for check in report.checks] == [status]


def _lint_room(tmp_path: Path, returncode: int, printed: str) -> Room:
    class _Lint(Room):
        def beadloom(self, project: Path, *args: str) -> Done:
            return Done(returncode, printed, "")

    return _Lint(tmp_path, None)


def _violation(rule: str, source: str | None, target: str | None) -> dict[str, object]:
    return {
        "rule_name": rule,
        "severity": "error",
        "from_ref_id": source,
        "to_ref_id": target,
    }


class TestTheFeatureSlicedLint:
    @pytest.mark.parametrize(
        ("returncode", "violations", "status"),
        [
            (1, [_violation("fsd-layers", "features-cart", "features-auth")], "PASS"),
            (0, [], "FAIL"),
            (1, [_violation("fsd-public-api", "widgets-header", "features-auth")], "FAIL"),
            (0, [_violation("fsd-layers", "features-cart", "features-auth")], "FAIL"),
        ],
    )
    def test_lint_strict_must_exit_1_on_the_planted_cross_import(
        self,
        tmp_path: Path,
        returncode: int,
        violations: list[dict[str, object]],
        status: str,
    ) -> None:
        room = _lint_room(tmp_path, returncode, json.dumps({"violations": violations}))
        report = _report()

        check_fsd_lint(room, tmp_path, report)

        assert [check.status for check in report.checks] == [status]

    def test_lint_that_prints_no_json_fails_and_quotes_it(self, tmp_path: Path) -> None:
        room = _lint_room(tmp_path, 2, "Error: No such option: --format\n")
        report = _report()

        check_fsd_lint(room, tmp_path, report)

        assert [(c.status, "No such option" in c.detail) for c in report.checks] == [
            ("FAIL", True)
        ]


class TestTheFeatureSlicedTree:
    def test_the_harness_measures_the_tree_the_suite_measures_the_preset_on(self) -> None:
        assert harness.FSD_PROJECT_FILES == FSD_TREE


def _scaffolded_room(tmp_path: Path, *, npm_fails: str = "") -> Room:
    """A room whose ``docs site`` leaves a complete 9.0.0 scaffold and whose npm step
    *npm_fails* (``"ci"``, ``"run"``, or none) exits 1."""
    project = tmp_path / "quayside"
    project.mkdir()
    site = _scaffold(project)
    (site / ".vitepress").mkdir(exist_ok=True)
    (site / "e2e").mkdir()

    class _Scaffolded(Room):
        def beadloom(self, project: Path, *args: str) -> Done:
            return Done(0, "Generated 236 files\n", "")

        def run(self, command: list[str], cwd: Path, env: dict[str, str] | None = None) -> Done:
            failed = command[0] == "npm" and command[1] == npm_fails
            return Done(1 if failed else 0, "", 'npm error Missing script: "x"\n')

    return _Scaffolded(tmp_path, None)


class TestThePortalNpmSteps:
    def test_a_room_with_no_usable_node_skips_the_three_npm_checks_with_its_reason(
        self, tmp_path: Path
    ) -> None:
        room = _scaffolded_room(tmp_path)
        room.npm_skip = "no node on PATH"
        report = _report()

        harness.check_portal(room, tmp_path / "quayside", report)

        assert [
            (check.name.split(":")[0], check.detail)
            for check in report.checks
            if check.status == "SKIPPED"
        ] == [
            ("portal build", "no node on PATH"),
            ("portal assets", "no node on PATH"),
            ("portal lint", "no node on PATH"),
        ]

    def test_a_failed_npm_ci_fails_the_build_and_runs_neither_check_after_it(
        self, tmp_path: Path
    ) -> None:
        report = _report()

        harness.check_portal(
            _scaffolded_room(tmp_path, npm_fails="ci"), tmp_path / "quayside", report
        )

        assert {
            stage: status
            for stage, status in _stage_statuses(report).items()
            if stage in {"portal build", "portal assets", "portal lint"}
        } == {"portal build": "FAIL", "portal assets": "NOT RUN", "portal lint": "NOT RUN"}
