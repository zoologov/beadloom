"""Steps for `services/cli-commands/the_gate_through_a_pipe_that_will_not_wait.feature`.

BDL-083 S1e2 (``beadloom-jwfc``, BDL-UX #226). Every scenario runs the real ``beadloom
ci`` in a process of its own, because the defect is in how that process writes to the
descriptor it was handed, and an in-process runner hands it no descriptor at all. The
process is a short script that injects the scenario's faults the way
`a_step_that_raises.feature` does, by replacing the step function the Gate calls, and
then enters the real command line. The tracker adapter answers that no bead is claimed,
so a run neither needs a beads database nor reads the author's tracker.

The pipe is the room the defect was measured in: non-blocking, read by
:mod:`tests.support.late_reader` only once its writer has been made to wait.
"""

from __future__ import annotations

import subprocess
import sys
from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, scenarios, then, when

from beadloom.application.reindex import reindex
from beadloom.onboarding.scanner import generate_agents_md
from tests.support.committed_project import commit_project
from tests.support.hook_runner import install_hooks, tools
from tests.support.late_reader import run_read_late

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../../../services/cli-commands/the_gate_through_a_pipe_that_will_not_wait.feature")

#: How many findings the doctor step is made to report: about 140 bytes of report each,
#: so the report is several times the largest pipe capacity the suite runs in (64 KiB).
_FINDINGS = 3000

#: The script standing in for the ``beadloom`` console script. It is the real command
#: line with the scenario's faults injected; the two values are filled per scenario.
_ENTRY = """
import sys

from beadloom.application import gate
from beadloom.application.gate_step import GateStep
from beadloom.services import guard_probes

guard_probes.BdWorkTracker.claimed_beads = lambda _self: ()
FINDINGS = {findings}
CRASH = {crash}


def _doctor(_project_root):
    findings = [
        {{
            "kind": "doctor",
            "rule": "injected",
            "severity": "error",
            "locations": [{{"file": f"src/module_{{n:05d}}.py", "line": 1}}],
            "why": "an injected finding, one of many, so that the report outgrows a pipe",
            "remediation": "nothing to fix: the finding is the scenario's",
        }}
        for n in range(FINDINGS)
    ]
    return GateStep(name="doctor", passed=False, findings=findings,
                    summary=f"{{len(findings)}} finding(s)")


def _raise(*_args, **_kwargs):
    raise LookupError("injected fault")


if FINDINGS:
    gate._step_doctor = _doctor
if CRASH:
    gate._step_docs_audit = _raise

from beadloom.services.cli import main

main(prog_name="beadloom")
"""


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    """One mutable bag the steps share, kept explicit rather than global."""
    return {"workdir": tmp_path, "root": None, "path": "", "findings": 0, "crash": False}


def _entry(world: dict[str, Any]) -> Path:
    """The stand-in for the console script, written with this scenario's faults."""
    entry = world["workdir"] / "beadloom_entry.py"
    text = _ENTRY.format(findings=world["findings"], crash=world["crash"])
    entry.write_text(text, encoding="utf-8")
    return entry


def _environment(world: dict[str, Any], path: str) -> dict[str, str]:
    return {"PATH": path, "HOME": str(world["root"])}


@given("a project on which every gate step passes")
def _a_clean_project(world: dict[str, Any]) -> None:
    root = world["workdir"] / "repo"
    (root / ".beadloom" / "_graph").mkdir(parents=True)
    generate_agents_md(root)
    reindex(root)
    commit_project(root)
    world["root"] = root


@given("its doctor step reports more findings than a pipe holds")
def _a_big_report(world: dict[str, Any]) -> None:
    world["findings"] = _FINDINGS


@given("the docs-audit step raises an unexpected exception")
def _docs_audit_raises(world: dict[str, Any]) -> None:
    world["crash"] = True


@given("the composed hooks installed in it")
def _hooks(world: dict[str, Any]) -> None:
    install_hooks(world["root"])


def _gate_argv(world: dict[str, Any]) -> list[str]:
    return [sys.executable, str(_entry(world)), "ci", "--format", "rich"]


def _to_a_file(world: dict[str, Any]) -> bytes:
    """What the same run writes when its output is a regular file, which never waits."""
    report = world["workdir"] / "report.txt"
    with report.open("wb") as sink:
        subprocess.run(  # noqa: S603 - this interpreter, running the scenario's entry
            _gate_argv(world),
            cwd=world["root"],
            env=_environment(world, world["path"]),
            stdin=subprocess.DEVNULL,
            stdout=sink,
            stderr=sink,
            check=False,
        )
    return report.read_bytes()


@when("the gate runs with its output on a non-blocking pipe whose reader starts late")
def _gate_on_the_pipe(world: dict[str, Any]) -> None:
    world["path"] = tools(world["workdir"])
    world["rc"], world["read"] = run_read_late(
        _gate_argv(world), cwd=world["root"], env=_environment(world, world["path"])
    )
    world["baseline"] = _to_a_file(world)


@when("the pre-push hook runs with its output on a non-blocking pipe whose reader starts late")
def _hook_on_the_pipe(world: dict[str, Any]) -> None:
    entry = _entry(world)
    shim = f'exec "{sys.executable}" "{entry}" "$@"'
    world["path"] = tools(world["workdir"], shims={"beadloom": shim})
    hook = str(world["root"] / ".git" / "hooks" / "pre-push")
    world["rc"], world["read"] = run_read_late(
        ["/bin/sh", hook], cwd=world["root"], env=_environment(world, world["path"])
    )
    world["baseline"] = _to_a_file(world)


def _received(world: dict[str, Any]) -> str:
    return str(world["read"].text)


@then("the gate exits 1")
def _gate_exits_one(world: dict[str, Any]) -> None:
    assert world["rc"] == 1, _received(world)[-2000:]


@then("the hook exits non-zero")
def _hook_exits_non_zero(world: dict[str, Any]) -> None:
    assert world["rc"] != 0, _received(world)[-2000:]


@then("the reader receives every byte the gate writes to a file")
def _whole(world: dict[str, Any]) -> None:
    received, baseline = world["read"].received, world["baseline"]
    assert len(baseline) > 4 * 64 * 1024, "the scenario needs a report bigger than a pipe"
    assert b"BlockingIOError" not in received, received[-2000:]
    assert baseline in received, (len(received), len(baseline), received[-2000:])


@then("the pipe is non-blocking again when the gate is done")
def _mode_put_back(world: dict[str, Any]) -> None:
    assert world["read"].nonblocking_after is True


@then("the hook says the Gate blocked this push and names the verdict")
def _blocked(world: dict[str, Any]) -> None:
    assert "Beadloom Gate blocked this push: FAIL — gate blocked" in _received(world)


@then("the hook says a step crashed and that what it checks was not checked")
def _crashed(world: dict[str, Any]) -> None:
    said = _received(world)
    assert "Beadloom Gate blocked this push: FAIL — 1 step(s) crashed: docs-audit" in said
    assert "checked nothing" in said, said[-2000:]


@then("the hook does not say the findings above name their fixes")
def _no_fixes_claim(world: dict[str, Any]) -> None:
    assert "The findings above name their fixes" not in _received(world)
