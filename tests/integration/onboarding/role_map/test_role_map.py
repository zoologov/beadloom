"""Boundary guards for `onboarding.role_map` (BDL-068 S6, BDL-UX #252).

`tests/acceptance/features/role_map.feature` holds the behaviour. These are the
shapes the derivation must NOT read as roles, and each one is a decision the
module's docstring states rather than a case that happened to work: a check over
a spelling is a check five other spellings walk past, and a check that reads
ordinary prose as a designation turns an adopter's green project red.

Every assertion here is about the PROJECT layer's fragment, filtered by source,
so a change to the shipped `CLAUDE.md` core cannot make one of them pass or fail
for a reason it is not about.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.onboarding.flow_config import (
    SUPPORTED_TOOLS,
    FlowConfig,
    FlowConfigError,
)
from beadloom.onboarding.role_composer import ROLE_NAMES
from beadloom.onboarding.role_map import (
    _MAP_ARTIFACTS,
    RoleMapReport,
    role_map_report,
)

if TYPE_CHECKING:
    from pathlib import Path

_FLOW_YML = """\
tools:
- claude
architecture:
- ddd
stack:
- python
"""

_PROJECT_LAYER = ".beadloom/flow"


def _project(tmp_path: Path, body: str) -> Path:
    (tmp_path / ".beadloom").mkdir()
    (tmp_path / ".beadloom" / "flow.yml").write_text(_FLOW_YML, encoding="utf-8")
    fragment = tmp_path / ".beadloom" / "flow" / "claude"
    fragment.mkdir(parents=True)
    (fragment / "CLAUDE.md").write_text(body, encoding="utf-8")
    return tmp_path


def _own(report: RoleMapReport) -> list[tuple[str, ...]]:
    """The names of every reference the project layer's own fragment produced."""
    return [
        reference.names
        for reference in report.references
        if _PROJECT_LAYER in reference.source
    ]


def _own_unjudged(report: RoleMapReport) -> list[tuple[str, ...]]:
    return [entry.roles for entry in report.not_judged if _PROJECT_LAYER in entry.source]


def test_a_bare_comma_list_containing_a_role_word_is_not_a_roster(tmp_path: Path) -> None:
    """`Types: feat, fix, refactor, docs, test, chore` is a commit-type list.

    It names `test`, and reading it as a roster would report every other role as
    omitted from a line about commit messages. The backtick requirement on the
    comma form is what separates the two, and this is the sentence it was
    calibrated against — it is in the shipped `CLAUDE.md` today.
    """
    body = "\nTypes: feat, fix, refactor, docs, test, chore\n"
    report = role_map_report(_project(tmp_path, body))
    assert _own(report) == []


def test_a_subagent_list_does_not_swallow_the_argument_after_it(tmp_path: Path) -> None:
    """`run_in_background` is not a role, and a comma-joined run would say it is.

    Measured on the shipped map's own line: `Agent(subagent_type="dev"|"test",
    run_in_background=True)`. Allowing `,` to join the run captures `run` — the
    name stops at `_`, which is not a name character — and reports it `unbacked`
    at `error`.
    """
    body = '\nLaunch it with `Agent(subagent_type="dev"|"test", run_in_background=True)`.\n'
    report = role_map_report(_project(tmp_path, body))
    assert _own(report) == [("dev", "test")]
    assert [f.role for f in report.findings if f.kind == "unbacked"] == []


def test_a_role_placeholder_designates_nothing(tmp_path: Path) -> None:
    """`.claude/agents/<role>.md` is an instruction, not a role named `role`."""
    report = role_map_report(_project(tmp_path, "\nFollow `.claude/agents/<role>.md` directly.\n"))
    assert _own(report) == []


def test_a_wave_order_is_not_judged_rather_than_reported(tmp_path: Path) -> None:
    """An arrow run names four roles and must not be required to name five.

    `Explore` runs before a work item has a type, so it is not a wave. The line
    is reported as not judged, which says the derivation saw it and declined,
    rather than as a finding or as nothing at all.
    """
    report = role_map_report(_project(tmp_path, "\nWaves: dev → test → review → tech-writer.\n"))
    assert _own(report) == []
    assert _own_unjudged(report) == [("dev", "review", "tech-writer", "test")]


def test_an_inferred_roster_never_reports_an_unbacked_name(tmp_path: Path) -> None:
    """``we deploy to `dev`, `staging``` is about environments, not roles.

    The run is recognised as a roster only once it names two composed roles, and
    even then its other tokens are ordinary words. Reporting `staging` would put
    a release-introduced `error` into an adopter's own prose, which is the one
    outcome CONTEXT's upgrade constraint forbids.
    """
    body = "\nWe deploy to `dev`, `test`, `staging`.\n"
    report = role_map_report(_project(tmp_path, body))
    assert _own(report) == [("dev", "test", "staging")]
    assert [f.role for f in report.findings if f.kind == "unbacked"] == []
    partial = [f for f in report.findings if f.kind == "partial"]
    assert {f.severity for f in partial} == {"warn"}


def test_a_punctuated_run_naming_one_role_is_not_a_roster(tmp_path: Path) -> None:
    """Two composed roles is the threshold, and one is below it.

    A single backticked pair is ordinary markdown. Recognising it would make
    every two-word list in every adopter's project layer a claim about roles.
    """
    report = role_map_report(_project(tmp_path, "\nWe deploy to `dev`, `staging`.\n"))
    assert _own(report) == []


def test_the_population_defaults_to_what_role_composer_derives(tmp_path: Path) -> None:
    """The seam is a seam, not a second home for the role list."""
    assert role_map_report(_project(tmp_path, "\n")).roles == ROLE_NAMES


def test_a_flow_config_that_will_not_load_is_refused_rather_than_guessed(
    tmp_path: Path,
) -> None:
    """A report against a guessed configuration is a verdict about another flow.

    An ABSENT `flow.yml` is a different case and is not refused here: it
    resolves by auto-detection, exactly as `duty_report` treats it, and the
    presence guard that keeps the finding out of `config-check` lives in
    `_role_map_drifts`. A file that exists and will not load is the one this
    module must not answer over, because the answer would describe a flow the
    project does not run.
    """
    (tmp_path / ".beadloom").mkdir()
    (tmp_path / ".beadloom" / "flow.yml").write_text(
        "architecture: [nonesuch]\n", encoding="utf-8"
    )
    with pytest.raises(FlowConfigError):
        role_map_report(tmp_path)


def test_every_finding_names_a_site_a_reader_can_open(tmp_path: Path) -> None:
    """A finding whose site is a fragment and a line, never the composed body.

    Scanning per fragment is what buys this. The composed `CLAUDE.md` is the
    concatenation of its layers, so a line number in it points at nothing an
    editor can be opened on.
    """
    body = '\nLaunch it with `Agent(subagent_type="scout")`.\n'
    report = role_map_report(_project(tmp_path, body))
    unbacked = [f for f in report.findings if f.kind == "unbacked" and f.role == "scout"]
    assert len(unbacked) == 1
    assert unbacked[0].sites[0].startswith(_PROJECT_LAYER)
    assert unbacked[0].sites[0].rsplit(":", 1)[1].isdigit()


def test_the_shipped_map_names_every_role_the_shipped_flow_composes(tmp_path: Path) -> None:
    """The instance BDL-UX #252 was filed about, guarded against the next role.

    A sixth role added to `templates/roles/core/` and to no roster in the map
    reddens this without anyone editing a list, which is the whole point of
    deriving the population instead of writing it down.
    """
    report = role_map_report(_project(tmp_path, "\n"))
    assert report.findings == ()
    assert report.rosters
    for roster in report.rosters:
        assert set(ROLE_NAMES) <= set(roster.names), (roster.source, roster.names)


# --- BDL-068 `.84`: the corpus is the declared tool set ----------------------
#
# Derivation guards, not examples. Each holds `_MAP_ARTIFACTS` against the tool
# population `flow.yml` validates against, so a release that adds a third tool
# is reported by one of them rather than by an adopter.


def test_every_declarable_tool_is_read_or_named_unreached(tmp_path: Path) -> None:
    """The partition, over the tools `flow.yml` accepts rather than a literal.

    A tool added to `SUPPORTED_TOOLS` with no row in `_MAP_ARTIFACTS` lands in
    `unreached` and is stated; the failure this forbids is the third outcome —
    a declared tool that is neither judged nor named.
    """
    root = _project(tmp_path, "\n")
    for tool in SUPPORTED_TOOLS:
        config = FlowConfig(tools=(tool,), architecture="ddd", stack=("python",))
        report = role_map_report(root, config)
        covered = [a.tool for a in report.artifacts] + [u.tool for u in report.unreached]
        assert covered == [tool], (tool, covered)


def test_the_artifact_table_names_no_tool_a_project_cannot_declare() -> None:
    """A row for a tool `flow.yml` rejects would be a corpus nothing can select."""
    assert set(_MAP_ARTIFACTS) <= set(SUPPORTED_TOOLS)


def test_a_tool_with_no_map_artifact_raises_nothing_and_judges_nothing(
    tmp_path: Path,
) -> None:
    """The unreached branch, reached through the seam `flow.yml` cannot express.

    The failure mode this forbids is a `KeyError` out of the lookup: a release
    that adds a tool to `SUPPORTED_TOOLS` and forgets the map row must degrade
    to a stated population, not to a traceback on the Gate surface.
    """
    root = _project(tmp_path, "\n")
    config = FlowConfig(tools=("windsurf",), architecture="ddd", stack=("python",))
    report = role_map_report(root, config)
    assert report.artifacts == ()
    assert report.findings == ()
    assert report.references == ()
    assert [entry.tool for entry in report.unreached] == ["windsurf"]


def test_a_finding_names_the_artifact_and_the_tool_it_is_about(tmp_path: Path) -> None:
    """Two maps in one run means a finding without its artifact is unactionable."""
    body = '\nLaunch it with `Agent(subagent_type="scout")`.\n'
    report = role_map_report(_project(tmp_path, body))
    for finding in report.findings:
        assert finding.tool == "claude"
        assert finding.artifact == ".claude/CLAUDE.md"
        assert finding.artifact in finding.why
