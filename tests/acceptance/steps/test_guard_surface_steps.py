"""Step implementations for `features/guard_surface.feature` (BDL-UX #170).

Against the real matcher constant, the real evaluator and the real surface
builder. A hand-built matcher string would prove the fixture, and the whole
finding is that the SHIPPED matcher and the shipped report disagreed with the
promise, so every assertion here reads the artifact the flow emits.

The module is named ``test_*`` so default pytest collection picks the scenarios
up — the acceptance suite runs inside ``uv run pytest``, not beside it.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, scenarios, then, when

from beadloom.application.guards.contract import ClaimedBead, GuardProbes
from beadloom.application.guards.evaluation import evaluate_guard
from beadloom.application.guards.firing import FIRINGS_RELPATH
from beadloom.application.guards.hook_payload import shell_command_context
from beadloom.application.guards.invocation import GuardInvocation, run_invocation
from beadloom.application.guards.models import GuardOutcome
from beadloom.application.guards.surface import build_surface
from beadloom.onboarding.guard_hooks import (
    EDIT_MATCHER,
    HOOK_EVENT,
    SETTINGS_RELPATH,
    hook_command,
)
from beadloom.onboarding.role_adapters import TOOL_AGENT_DIRS

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../features/guard_surface.feature")

_GUARD = "bead-claimed"

#: A command whose write is performed by an interpreter reading a heredoc —
#: the exact shape #170 was found on, and one no derivation can resolve.
_OPAQUE = "python3 - <<'EOF'\nopen('src/app.py', 'w').write('x')\nEOF"


class _Claimed:
    def claimed_beads(self) -> tuple[ClaimedBead, ...]:
        return (ClaimedBead(id="beadloom-0mdo.31", title="the binding's surface"),)


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    return {"root": tmp_path}


def _evaluate(world: dict[str, Any], command: str) -> None:
    """Through the door the harness's command line goes through, not around it."""
    world["verdict"] = evaluate_guard(
        _GUARD,
        project_root=world["root"],
        context={"tool": "Bash", **shell_command_context(command)},
        probes=GuardProbes(tracker=_Claimed()),
    )


def _emit_binding(root: Path, *, matcher: str, tools: str) -> None:
    """Write the two artifacts the flow emits that the surface is derived from."""
    settings = root / SETTINGS_RELPATH
    settings.parent.mkdir(parents=True, exist_ok=True)
    settings.write_text(
        json.dumps(
            {
                "hooks": {
                    HOOK_EVENT: [
                        {
                            "matcher": matcher,
                            "hooks": [
                                {"type": "command", "command": hook_command(_GUARD)}
                            ],
                        }
                    ]
                }
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    agents = root / TOOL_AGENT_DIRS["claude"]
    agents.mkdir(parents=True, exist_ok=True)
    (agents / "dev.md").write_text(
        f"---\nname: dev\ndescription: a role\ntools: {tools}\nmodel: opus\n---\n\nbody\n",
        encoding="utf-8",
    )


@given("the harness binding this project emits")
def _the_emitted_binding(world: dict[str, Any]) -> None:
    world["matcher"] = EDIT_MATCHER


@then("the shell tool is one of the tools the binding fires on")
def _shell_is_bound(world: dict[str, Any]) -> None:
    assert "Bash" in world["matcher"].split("|"), world["matcher"]


@given("a bead is claimed")
def _a_bead_is_claimed(world: dict[str, Any]) -> None:
    world["claimed"] = True


@given("a bead is claimed and every path under docs is excluded")
def _claimed_and_docs_excluded(world: dict[str, Any]) -> None:
    root: Path = world["root"]
    (root / ".beadloom").mkdir(parents=True, exist_ok=True)
    (root / ".beadloom" / "flow.yml").write_text(
        "guards:\n"
        f"  {_GUARD}:\n"
        "    strictness: {default: warn}\n"
        "    exclusions:\n"
        "    - path: 'docs/**'\n"
        "      reason: generated prose is not work anyone claims\n"
        "      until: 2099-01-01\n",
        encoding="utf-8",
    )


@when("the guard is asked about a shell command whose writes cannot be determined")
def _ask_opaque(world: dict[str, Any]) -> None:
    _evaluate(world, _OPAQUE)


@when("the guard is asked about a shell command that redirects into a file")
def _ask_redirect(world: dict[str, Any]) -> None:
    _evaluate(world, "echo hi > src/app.py")


@when("the guard is asked about a shell command that redirects into a file under docs")
def _ask_redirect_docs(world: dict[str, Any]) -> None:
    _evaluate(world, "echo hi > docs/generated.md")


@then("the verdict states that the command's write set was not determined")
def _says_undetermined(world: dict[str, Any]) -> None:
    verdict = world["verdict"]
    assert verdict.outcome is GuardOutcome.PASS, verdict.outcome
    notes = " ".join(verdict.not_covered)
    assert "shell command" in notes, notes
    assert "derived" in notes, notes
    assert "not decidable" in notes, notes


@then("the verdict names that file as a write target it could see")
def _names_the_target(world: dict[str, Any]) -> None:
    notes = " ".join(world["verdict"].not_covered)
    assert "src/app.py" in notes, notes


@then("the guard is not skipped as excluded")
def _not_skipped(world: dict[str, Any]) -> None:
    verdict = world["verdict"]
    assert verdict.outcome is not GuardOutcome.SKIP, verdict.to_dict()


@given("a project whose roles are granted the shell tool and whose matcher omits it")
def _binding_with_a_gap(world: dict[str, Any]) -> None:
    _emit_binding(
        world["root"], matcher="Edit|Write", tools="Read, Write, Edit, Bash, Grep"
    )


@given("a project whose roles are granted a tool this report cannot classify")
def _binding_with_an_unknown_tool(world: dict[str, Any]) -> None:
    _emit_binding(
        world["root"],
        matcher="Edit|Write|Bash",
        tools="Read, Write, Edit, Bash, Grep, Telekinesis",
    )


@given("a project with no emitted harness settings")
def _no_binding(world: dict[str, Any]) -> None:
    return


@when("the binding surface is reported")
def _report_surface(world: dict[str, Any]) -> None:
    world["surface"] = build_surface(world["root"])


@then("the shell tool is reported as a write path the binding cannot see")
def _bash_unseen(world: dict[str, Any]) -> None:
    surface = world["surface"]
    assert "Bash" in surface.unseen, surface.to_dict()
    assert surface.covered == (2, 3), surface.to_dict()


@then("that tool is reported as unclassified rather than as a non-writer")
def _unknown_tool_reported(world: dict[str, Any]) -> None:
    surface = world["surface"]
    assert "Telekinesis" in surface.unclassified, surface.to_dict()
    assert "Telekinesis" not in surface.unseen, surface.to_dict()


@then("the report states why the binding could not be read")
def _unresolved_stated(world: dict[str, Any]) -> None:
    unresolved = " ".join(world["surface"].unresolved)
    assert SETTINGS_RELPATH.as_posix() in unresolved, unresolved


@then("it claims no coverage fraction")
def _no_fraction(world: dict[str, Any]) -> None:
    assert world["surface"].covered is None, world["surface"].to_dict()


@given("a project whose roles are granted only tools that write no file")
def _binding_with_no_write_path(world: dict[str, Any]) -> None:
    _emit_binding(world["root"], matcher=EDIT_MATCHER, tools="Read, Grep")


@then("the report states that there was nothing to check")
def _nothing_to_check(world: dict[str, Any]) -> None:
    surface = world["surface"]
    assert surface.nothing_to_check is True, surface.to_dict()
    assert "NOTHING TO CHECK" in surface.describe(), surface.describe()


@then("it does not say that a source could not be read")
def _not_unresolved(world: dict[str, Any]) -> None:
    assert world["surface"].unresolved == (), world["surface"].to_dict()


@then("the report names the artifacts on disk it was derived from")
def _names_its_sources(world: dict[str, Any]) -> None:
    read_from = world["surface"].to_dict()["read_from"]
    assert isinstance(read_from, str), read_from
    assert SETTINGS_RELPATH.as_posix() in read_from, read_from
    assert TOOL_AGENT_DIRS["claude"].as_posix() in read_from, read_from
    assert "ON DISK" in read_from, read_from


#: A command line of the shape the review's finding is about: an environment
#: assignment carrying a credential, a program, an operand, and a redirection
#: into a file. Every part but the last is what the record must not keep.
_SECRET = "ghp_00000000000000000000000000000000"  # noqa: S105 — a shape, not a token
_WITH_A_SECRET = f"GITHUB_TOKEN={_SECRET} gh api repos/acme/private > out/report.json"


class _Bash:
    """The shell payload the harness sends, as the harness sends it."""

    def __init__(self, command: str) -> None:
        self.command = command

    def __call__(self) -> bytes:
        payload = {
            "hook_event_name": HOOK_EVENT,
            "tool_name": "Bash",
            "tool_input": {"command": self.command},
        }
        return json.dumps(payload).encode("utf-8")


@when("the harness reports a shell command that carries a secret and writes a file")
def _harness_reports_a_secret_command(world: dict[str, Any]) -> None:
    root: Path = world["root"]
    (root / ".beadloom").mkdir(parents=True, exist_ok=True)
    result = run_invocation(
        GuardInvocation(
            name=_GUARD,
            declared_project=root,
            harness="claude-code",
            read_payload=_Bash(_WITH_A_SECRET),
            probes_for=lambda _root: GuardProbes(tracker=_Claimed()),
        )
    )
    assert result.recorded, result.not_recorded_because
    world["record"] = (root / FIRINGS_RELPATH).read_text(encoding="utf-8")


@then("the firing record names the file the command writes and the program it ran")
def _record_names_the_write_and_the_program(world: dict[str, Any]) -> None:
    context = json.loads(world["record"].splitlines()[-1])["context"]
    assert context["command_writes"] == "out/report.json", context
    assert context["command_name"] == "gh", context


@then("no part of the command line is in the firing record")
def _record_holds_no_command_line(world: dict[str, Any]) -> None:
    record = world["record"]
    for fragment in (_SECRET, "GITHUB_TOKEN", "repos/acme/private", "api"):
        assert fragment not in record, fragment
