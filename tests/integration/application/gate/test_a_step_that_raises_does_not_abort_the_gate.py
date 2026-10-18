"""A gate step that raises is reported as ERROR, and every other step still reports.

BDL-083 S1e (``beadloom-ba9w.13``, BDL-UX #318; RFC D1). ``run_ci_gate`` called its
steps in a row with no boundary, so an exception in one ended the run: the steps after
it never ran and the caller received a traceback instead of a verdict. The docstring
promised the Gate never short-circuits, and that was true of a step that FAILED only.

The fault is injected in each step in turn by replacing the function the orchestrator
calls. The step names are read from a clean run of the same project rather than spelled
here, so a leg added later is covered without editing this file — except for the
function that produces it, which the completeness test below asks for by name.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from beadloom.application import gate
from beadloom.application.gate import GateResult, GateStep, run_ci_gate
from beadloom.application.reindex import reindex
from beadloom.onboarding.scanner import generate_agents_md

if TYPE_CHECKING:
    from pathlib import Path

#: Every step function the orchestrator calls, and the step name it reports under.
STEP_FUNCTIONS: dict[str, str] = {
    "_step_reindex": "reindex",
    "lint_step": "lint",
    "_step_sync_check": "sync-check",
    "_step_docs_audit": "docs-audit",
    "_step_docs_quality": "docs-quality",
    "_step_issue_numbers": "issue-log",
    "step_readme_pair": "readme-pair",
    "_step_doc_spaces": "doc-spaces",
    "_step_scope_check": "scope-check",
    "_step_config_check": "config-check",
    "_step_doctor": "doctor",
    "_step_federate": "federate",
}


def _export(repo: str) -> dict[str, object]:
    """A satellite export with no break, so the federate step runs and passes."""
    return {
        "schema_version": 1,
        "repo": repo,
        "exported_at": "2026-06-01T00:00:00+00:00",
        "nodes": [{"ref_id": "svc", "kind": "service", "name": repo}],
        "edges": [],
        "contracts": [],
        "lifecycle": {},
    }


@pytest.fixture()
def project(tmp_path: Path) -> tuple[Path, list[Path]]:
    """A project every step passes on, and two exports so the federate step runs."""
    root = tmp_path / "project"
    (root / ".beadloom" / "_graph").mkdir(parents=True)
    generate_agents_md(root)
    reindex(root)
    exports = []
    for repo in ("alpha", "beta"):
        path = tmp_path / f"{repo}.json"
        path.write_text(json.dumps(_export(repo)), encoding="utf-8")
        exports.append(path)
    return root, exports


def _run(project: tuple[Path, list[Path]]) -> GateResult:
    root, exports = project
    return run_ci_gate(root, fail_on=None, hub_exports=exports, no_reindex=False)


def _raises(*_args: object, **_kwargs: object) -> GateStep:
    raise LookupError("injected fault")


def test_the_clean_project_passes_every_step(project: tuple[Path, list[Path]]) -> None:
    """The fixture's own baseline: without it a crashed step could hide in a red run."""
    result = _run(project)
    assert result.ok, [gate.gate_step_line(s) for s in result.steps if not s.passed]
    assert [s.name for s in result.steps] == list(STEP_FUNCTIONS.values())
    assert result.crashed == []


def test_every_step_function_the_orchestrator_names_is_listed_here() -> None:
    """A step added to the orchestrator without a row here would never be broken by a test."""
    import inspect

    source = inspect.getsource(gate.run_ci_gate)
    called = {
        name
        for name in dir(gate)
        if name.startswith(("_step_", "step_")) or name == "lint_step"
    }
    in_orchestrator = {name for name in called if f"{name}(" in source}
    assert in_orchestrator == set(STEP_FUNCTIONS)


@pytest.mark.parametrize(("function", "step_name"), sorted(STEP_FUNCTIONS.items()))
def test_a_step_that_raises_reads_error_and_the_rest_report(
    project: tuple[Path, list[Path]],
    monkeypatch: pytest.MonkeyPatch,
    function: str,
    step_name: str,
) -> None:
    monkeypatch.setattr(gate, function, _raises)

    result = _run(project)

    assert [s.name for s in result.steps] == list(STEP_FUNCTIONS.values())
    crashed = next(s for s in result.steps if s.name == step_name)
    assert crashed.status == "ERROR"
    assert crashed.passed is False
    assert crashed.error is not None
    assert "LookupError" in crashed.error
    assert "injected fault" in crashed.error
    others = [s for s in result.steps if s.name != step_name]
    assert all(s.status != "ERROR" for s in others)
    assert result.ok is False
    assert [s.name for s in result.crashed] == [step_name]


def test_the_crashed_step_carries_one_error_finding_naming_the_step(
    project: tuple[Path, list[Path]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The finding is what the MCP tool and the GitHub annotations carry to a reader."""
    monkeypatch.setattr(gate, "_step_doctor", _raises)

    step = next(s for s in _run(project).steps if s.name == "doctor")

    assert len(step.findings) == 1
    finding = step.findings[0]
    assert finding["severity"] == "error"
    assert finding["rule"] == "doctor"
    assert "doctor" in str(finding["why"])
    assert "LookupError" in str(finding["why"])
    assert gate.gate_step_line(step) == "[ERROR] doctor: crashed — LookupError: injected fault"


def test_two_crashed_steps_are_both_counted(
    project: tuple[Path, list[Path]], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(gate, "lint_step", _raises)
    monkeypatch.setattr(gate, "_step_doctor", _raises)

    result = _run(project)

    assert [s.name for s in result.crashed] == ["lint", "doctor"]
    assert gate.crashed_clause(result.steps) == "2 step(s) crashed: lint, doctor"


def test_no_crash_means_no_clause(project: tuple[Path, list[Path]]) -> None:
    assert gate.crashed_clause(_run(project).steps) == ""


def test_an_interrupt_is_not_swallowed(
    project: tuple[Path, list[Path]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A user's Ctrl-C ends the run; the boundary is for defects, not for the operator."""

    def _interrupt(*_args: object, **_kwargs: object) -> GateStep:
        raise KeyboardInterrupt

    monkeypatch.setattr(gate, "_step_docs_audit", _interrupt)

    with pytest.raises(KeyboardInterrupt):
        _run(project)


def test_a_step_that_fails_is_still_fail_and_not_error() -> None:
    """ERROR is the step that raised. A step that ran and found a fault stays FAIL."""
    assert GateStep("lint", passed=False).status == "FAIL"
    assert GateStep("lint", passed=False, error="LookupError: x").status == "ERROR"
    assert GateStep("lint", skipped=True, passed=False, error="LookupError: x").status == "ERROR"
