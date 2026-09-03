"""The shell derivation and the binding's surface (BDL-068 S4, BDL-UX #170).

Three subjects, in the order the finding names them: the write targets a command
line can be read to name, the verdict that says the reading is partial, and the
report that says how much of the write population the binding could see at all.

The derivation cases are written as SHAPES rather than spellings — ``>f``,
``> f`` and ``1> f`` are one shape, and a test per spelling would pass while the
next spelling walked past. The negative cases carry as much weight as the
positive ones: this module's contract is that an empty answer means "nothing was
derived", never "nothing is written".
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from beadloom.application.guards.contract import (
    ClaimedBead,
    GuardProbes,
    GuardRequest,
)
from beadloom.application.guards.evaluation import evaluate_guard
from beadloom.application.guards.hook_payload import (
    COMMAND_KEY,
    COMMAND_LIMIT,
    PATH_KEY,
    context_from_hook_payload,
)
from beadloom.application.guards.models import GuardOutcome
from beadloom.application.guards.paths import PathScope
from beadloom.application.guards.shell_targets import derive_write_targets
from beadloom.application.guards.surface import (
    READ_TOOLS,
    WRITE_TOOLS,
    build_surface,
)
from beadloom.onboarding.guard_hooks import (
    EDIT_MATCHER,
    HOOK_EVENT,
    SETTINGS_RELPATH,
    hook_command,
)
from beadloom.onboarding.role_adapters import TOOL_AGENT_DIRS
from beadloom.services.cli import main

_REPO_ROOT = Path(__file__).resolve().parent.parent


class _Claimed:
    def claimed_beads(self) -> tuple[ClaimedBead, ...]:
        return (ClaimedBead(id="beadloom-0mdo.31"),)


def _emit(root: Path, *, matcher: str | None, tools: str | None) -> None:
    """Write as much of the emitted binding as the case needs."""
    if matcher is not None:
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
                                    {
                                        "type": "command",
                                        "command": hook_command("bead-claimed"),
                                    }
                                ],
                            }
                        ]
                    }
                }
            ),
            encoding="utf-8",
        )
    if tools is not None:
        agents = root / TOOL_AGENT_DIRS["claude"]
        agents.mkdir(parents=True, exist_ok=True)
        (agents / "dev.md").write_text(
            f"---\nname: dev\ntools: {tools}\n---\n\nbody\n", encoding="utf-8"
        )


class TestOneShapeNotManySpellings:
    """Every spelling of a redirection is the same shape to the tokenizer."""

    @pytest.mark.parametrize(
        "command",
        [
            "echo hi > out.txt",
            "echo hi >out.txt",
            "echo hi 1> out.txt",
            "echo hi >> out.txt",
            "echo hi >| out.txt",
            "echo 'a  b' > out.txt",
            'echo "a b" >out.txt',
        ],
    )
    def test_every_redirection_spelling_names_the_same_file(
        self, command: str
    ) -> None:
        assert derive_write_targets(command).targets == ("out.txt",)

    def test_a_descriptor_duplication_names_no_file(self) -> None:
        """`2>&1` writes nothing — reading `1` as a path would invent a target."""
        assert derive_write_targets("printf x >> log 2>&1").targets == ("log",)

    def test_a_redirection_does_not_steal_a_command_s_operand(self) -> None:
        """In `cp a > log b`, `log` is the shell's and `b` is still cp's destination."""
        assert derive_write_targets("cp a > log b").targets == ("b", "log")


class TestTheDeclaredWriterShapes:
    @pytest.mark.parametrize(
        ("command", "expected"),
        [
            ("cat a | tee -a out.txt", ("out.txt",)),
            ("touch a.py b.py", ("a.py", "b.py")),
            ("truncate -s 0 log.txt", ("log.txt",)),
            ("touch -r ref.py a.py", ("a.py",)),
            ("sed -i 's/a/b/' docs/x.md", ("docs/x.md",)),
            ("sed -i '' -e 's/a/b/' docs/x.md", ("docs/x.md",)),
            ("sed -i.bak -e 's/a/b/' docs/x.md", ("docs/x.md",)),
            ("cp -f a b/c.py", ("b/c.py",)),
            ("mv a b/c.py", ("b/c.py",)),
            ("dd if=a of=b.img", ("b.img",)),
            ("/usr/bin/tee out.txt", ("out.txt",)),
        ],
    )
    def test_a_declared_writer_names_its_target(
        self, command: str, expected: tuple[str, ...]
    ) -> None:
        assert derive_write_targets(command).targets == expected

    def test_sed_without_in_place_edits_nothing(self) -> None:
        """`sed 's/a/b/' f` prints; reading `f` as a write would be a false target."""
        assert derive_write_targets("sed 's/a/b/' docs/x.md").targets == ()

    def test_a_copy_with_one_operand_names_no_destination(self) -> None:
        assert derive_write_targets("cp a").targets == ()

    def test_every_command_in_a_list_contributes(self) -> None:
        derived = derive_write_targets("echo a > x.txt && sed -i 's/a/b/' y.md")
        assert derived.targets == ("x.txt", "y.md")


class TestAnEmptyAnswerIsNotAClaim:
    def test_an_interpreter_reading_a_heredoc_derives_nothing(self) -> None:
        """The exact shape #170 was found on: the write is inside the program."""
        derived = derive_write_targets(
            "python3 - <<'EOF'\nopen('src/app.py', 'w').write('x')\nEOF"
        )
        assert derived.targets == ()
        assert derived.unreadable == ""

    def test_a_command_that_cannot_be_tokenized_says_so(self) -> None:
        """Distinct from deriving nothing: nothing could be READ, which is worse."""
        derived = derive_write_targets("echo 'unbalanced > out.txt")
        assert derived.targets == ()
        assert derived.unreadable

    def test_an_empty_command_derives_nothing_without_failing(self) -> None:
        assert derive_write_targets("   ") == derive_write_targets("")


class TestTheVerdictSaysTheReadingIsPartial:
    def test_a_command_resolves_to_undetermined_and_to_no_relative_path(
        self, tmp_path: Path
    ) -> None:
        """`relative` is what exclusion matching is fed, so it must stay None."""
        request = GuardRequest(
            project_root=tmp_path, context={"command": "echo a > src/app.py"}
        )
        resolved = request.resolved_path
        assert resolved.scope is PathScope.UNDETERMINED
        assert resolved.relative is None
        assert resolved.derived == ("src/app.py",)

    def test_an_explicit_path_wins_over_a_command(self, tmp_path: Path) -> None:
        """A path is a statement about one file; a command line is a lower bound."""
        request = GuardRequest(
            project_root=tmp_path,
            context={"path": "src/real.py", "command": "echo a > src/other.py"},
        )
        assert request.resolved_path.scope is PathScope.INSIDE
        assert request.resolved_path.relative == "src/real.py"

    def test_a_pass_on_a_command_carries_the_note(self, tmp_path: Path) -> None:
        verdict = evaluate_guard(
            "bead-claimed",
            project_root=tmp_path,
            context={"tool": "Bash", "command": "make release"},
            probes=GuardProbes(tracker=_Claimed()),
        )
        assert verdict.outcome is GuardOutcome.PASS
        assert any("shell command" in note for note in verdict.not_covered)

    def test_an_unreadable_command_line_is_reported_in_the_note(
        self, tmp_path: Path
    ) -> None:
        verdict = evaluate_guard(
            "bead-claimed",
            project_root=tmp_path,
            context={"tool": "Bash", "command": "echo 'unbalanced"},
            probes=GuardProbes(tracker=_Claimed()),
        )
        assert any("could not be read" in note for note in verdict.not_covered)

    def test_a_derived_target_under_an_exclusion_is_still_guarded(
        self, tmp_path: Path
    ) -> None:
        """The lower bound must not grant an exemption the writer may step past."""
        (tmp_path / ".beadloom").mkdir()
        (tmp_path / ".beadloom" / "flow.yml").write_text(
            "guards:\n"
            "  bead-claimed:\n"
            "    exclusions:\n"
            "    - path: 'docs/**'\n"
            "      reason: generated prose is claimed by nobody\n"
            "      until: 2099-01-01\n",
            encoding="utf-8",
        )
        verdict = evaluate_guard(
            "bead-claimed",
            project_root=tmp_path,
            context={"command": "sed -i 's/a/b/' docs/x.md && python3 write_src.py"},
            probes=GuardProbes(tracker=_Claimed()),
        )
        assert verdict.outcome is not GuardOutcome.SKIP


class TestTheHarnessPayloadCarriesTheCommand:
    def test_a_shell_event_arrives_as_a_command_and_not_as_a_path(self) -> None:
        context = context_from_hook_payload(
            "claude-code",
            json.dumps(
                {
                    "hook_event_name": HOOK_EVENT,
                    "tool_name": "Bash",
                    "tool_input": {"command": "sed -i 's/a/b/' src/app.py"},
                }
            ),
        )
        assert context[COMMAND_KEY] == "sed -i 's/a/b/' src/app.py"
        assert PATH_KEY not in context

    def test_an_edit_event_still_arrives_as_a_path(self) -> None:
        context = context_from_hook_payload(
            "claude-code",
            json.dumps({"tool_name": "Edit", "tool_input": {"file_path": "a.py"}}),
        )
        assert context[PATH_KEY] == "a.py"
        assert COMMAND_KEY not in context

    def test_a_long_command_is_bounded_before_it_reaches_a_firing_record(
        self,
    ) -> None:
        """The value is model-supplied and is stored; it is bounded at the door."""
        command = "echo " + "x" * (COMMAND_LIMIT * 2)
        context = context_from_hook_payload(
            "claude-code", json.dumps({"tool_input": {"command": command}})
        )
        assert len(context[COMMAND_KEY]) == COMMAND_LIMIT


class TestTheSurfaceIsDerivedFromTheEmittedArtifacts:
    def test_a_catch_all_matcher_binds_every_granted_tool(self, tmp_path: Path) -> None:
        _emit(tmp_path, matcher="*", tools="Read, Write, Bash")
        surface = build_surface(tmp_path)
        assert surface.unseen == ()
        assert surface.covered == (2, 2)

    def test_a_second_matcher_entry_widens_the_surface(self, tmp_path: Path) -> None:
        """The answer is the file on disk, so a hand-added entry counts too."""
        _emit(tmp_path, matcher="Edit", tools="Edit, Bash")
        settings = tmp_path / SETTINGS_RELPATH
        data = json.loads(settings.read_text(encoding="utf-8"))
        data["hooks"][HOOK_EVENT].append(
            {"matcher": "Bash", "hooks": [{"type": "command", "command": "x"}]}
        )
        settings.write_text(json.dumps(data), encoding="utf-8")
        assert build_surface(tmp_path).unseen == ()

    def test_a_matcher_naming_a_tool_no_role_is_granted_reports_itself(
        self, tmp_path: Path
    ) -> None:
        _emit(tmp_path, matcher="Edit|NotebookEdit", tools="Edit")
        assert build_surface(tmp_path).named_but_not_granted == ("NotebookEdit",)

    def test_settings_that_register_no_hook_event_are_unresolved(
        self, tmp_path: Path
    ) -> None:
        settings = tmp_path / SETTINGS_RELPATH
        settings.parent.mkdir(parents=True)
        settings.write_text(json.dumps({"hooks": {}}), encoding="utf-8")
        _emit(tmp_path, matcher=None, tools="Edit")
        surface = build_surface(tmp_path)
        assert surface.covered is None
        assert any(HOOK_EVENT in item for item in surface.unresolved)

    def test_unparsable_settings_are_unresolved_rather_than_empty(
        self, tmp_path: Path
    ) -> None:
        settings = tmp_path / SETTINGS_RELPATH
        settings.parent.mkdir(parents=True)
        settings.write_text("{ not json", encoding="utf-8")
        _emit(tmp_path, matcher=None, tools="Edit")
        assert build_surface(tmp_path).covered is None

    def test_settings_with_a_non_utf8_byte_are_unresolved_not_a_traceback(
        self, tmp_path: Path
    ) -> None:
        settings = tmp_path / SETTINGS_RELPATH
        settings.parent.mkdir(parents=True)
        settings.write_bytes(b'{"hooks": {"PreToolUse": []}}\xff')
        _emit(tmp_path, matcher=None, tools="Edit")
        assert build_surface(tmp_path).covered is None

    def test_missing_role_adapters_are_unresolved_rather_than_no_write_paths(
        self, tmp_path: Path
    ) -> None:
        """The failure this whole bead is about: an empty population reads as 100%."""
        _emit(tmp_path, matcher=EDIT_MATCHER, tools=None)
        surface = build_surface(tmp_path)
        assert surface.covered is None
        assert surface.write_paths == ()

    def test_a_role_file_without_front_matter_grants_nothing(
        self, tmp_path: Path
    ) -> None:
        _emit(tmp_path, matcher=EDIT_MATCHER, tools="Edit")
        agents = tmp_path / TOOL_AGENT_DIRS["claude"]
        (agents / "loose.md").write_text("no front matter here\n", encoding="utf-8")
        assert build_surface(tmp_path).covered == (1, 1)

    def test_every_role_granting_a_tool_is_named(self, tmp_path: Path) -> None:
        _emit(tmp_path, matcher=EDIT_MATCHER, tools="Bash")
        agents = tmp_path / TOOL_AGENT_DIRS["claude"]
        (agents / "test.md").write_text(
            "---\nname: test\ntools: Bash\n---\n\nbody\n", encoding="utf-8"
        )
        row = next(row for row in build_surface(tmp_path).tools if row.tool == "Bash")
        assert row.granted_by == (".claude/agents/dev.md", ".claude/agents/test.md")

    def test_the_classification_declares_no_tool_twice(self) -> None:
        assert not WRITE_TOOLS & READ_TOOLS


class TestThisRepositoryRunsWhatItShips:
    """The live dogfood assertion — the same class as the live-matcher check."""

    def test_the_binding_sees_every_write_path_this_repository_grants(self) -> None:
        surface = build_surface(_REPO_ROOT)
        assert surface.unresolved == (), surface.to_dict()
        assert surface.unseen == (), surface.to_dict()
        assert surface.unclassified == (), surface.to_dict()
        assert surface.covered == (3, 3), surface.to_dict()

    def test_the_report_names_the_surface_before_the_guard_rows(self) -> None:
        result = CliRunner().invoke(
            main, ["guard", "--liveness", "--project", str(_REPO_ROOT)]
        )
        assert result.exit_code == 0, result.output
        first = result.output.splitlines()[0]
        assert first.startswith("surface (claude): 3 of 3 write path(s) bound"), first

    def test_the_json_report_answers_both_questions(self) -> None:
        result = CliRunner().invoke(
            main, ["guard", "--liveness", "--json", "--project", str(_REPO_ROOT)]
        )
        payload = json.loads(result.stdout)
        assert payload["surface"]["covered"] == [3, 3]
        assert payload["guards"]
