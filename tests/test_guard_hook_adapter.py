"""The emitted Claude Code hook adapter carries NO logic — it calls the CLI (BDL-061 S1)."""

from __future__ import annotations

import json
import stat

from beadloom.onboarding.guard_hooks import (
    GUARD_HOOK_RELPATH,
    SETTINGS_RELPATH,
    scaffold_guard_hooks,
)

GUARDS = ("bead-claimed", "working-branch")


def _script_logic_lines(text: str) -> list[str]:
    """Every line that is neither the shebang, a comment, nor blank."""
    return [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


class TestHookScript:
    def test_the_adapter_is_a_single_exec_of_the_beadloom_cli(self, tmp_path) -> None:
        scaffold_guard_hooks(tmp_path, guard_names=GUARDS)
        text = (tmp_path / GUARD_HOOK_RELPATH).read_text(encoding="utf-8")
        assert _script_logic_lines(text) == ['exec beadloom guard "$1" --hook claude-code']

    def test_the_adapter_is_executable(self, tmp_path) -> None:
        scaffold_guard_hooks(tmp_path, guard_names=GUARDS)
        mode = (tmp_path / GUARD_HOOK_RELPATH).stat().st_mode
        assert mode & stat.S_IXUSR


class TestSettingsWiring:
    def test_every_guard_is_registered_as_a_pretooluse_hook(self, tmp_path) -> None:
        result = scaffold_guard_hooks(tmp_path, guard_names=GUARDS)
        settings = json.loads((tmp_path / SETTINGS_RELPATH).read_text(encoding="utf-8"))
        commands = [
            hook["command"]
            for entry in settings["hooks"]["PreToolUse"]
            for hook in entry["hooks"]
        ]
        for name in GUARDS:
            assert any(command.endswith(f"beadloom-guard.sh {name}") for command in commands)
        assert sorted(result.guards_registered) == sorted(GUARDS)

    def test_rerunning_does_not_duplicate_entries(self, tmp_path) -> None:
        scaffold_guard_hooks(tmp_path, guard_names=GUARDS)
        scaffold_guard_hooks(tmp_path, guard_names=GUARDS)
        settings = json.loads((tmp_path / SETTINGS_RELPATH).read_text(encoding="utf-8"))
        assert len(settings["hooks"]["PreToolUse"]) == len(GUARDS)

    def test_existing_settings_are_preserved(self, tmp_path) -> None:
        path = tmp_path / SETTINGS_RELPATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"permissions": {"allow": ["Bash(ls:*)"]}}))
        scaffold_guard_hooks(tmp_path, guard_names=GUARDS)
        settings = json.loads(path.read_text(encoding="utf-8"))
        assert settings["permissions"] == {"allow": ["Bash(ls:*)"]}
        assert settings["hooks"]["PreToolUse"]

    def test_unreadable_settings_are_reported_never_clobbered(self, tmp_path) -> None:
        path = tmp_path / SETTINGS_RELPATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{ not json")
        result = scaffold_guard_hooks(tmp_path, guard_names=GUARDS)
        assert path.read_text(encoding="utf-8") == "{ not json"
        assert result.settings_skipped_reason
        assert not result.guards_registered

    def test_a_foreign_hook_entry_survives(self, tmp_path) -> None:
        path = tmp_path / SETTINGS_RELPATH
        path.parent.mkdir(parents=True, exist_ok=True)
        foreign = {
            "hooks": {
                "PreToolUse": [
                    {"matcher": "Bash", "hooks": [{"type": "command", "command": "echo hi"}]}
                ]
            }
        }
        path.write_text(json.dumps(foreign))
        scaffold_guard_hooks(tmp_path, guard_names=GUARDS)
        settings = json.loads(path.read_text(encoding="utf-8"))
        commands = [
            hook["command"]
            for entry in settings["hooks"]["PreToolUse"]
            for hook in entry["hooks"]
        ]
        assert "echo hi" in commands


def test_setup_agentic_flow_emits_the_hooks_for_every_shipped_guard(tmp_path) -> None:
    """Standing rule 8: an emitted script nothing invokes is not a capability."""
    from click.testing import CliRunner

    from beadloom.application.guards.checks import GUARD_NAMES
    from beadloom.services.cli import main

    (tmp_path / ".beadloom").mkdir()
    (tmp_path / ".beadloom" / "flow.yml").write_text(
        "tools: [claude]\narchitecture: [ddd]\nstack: [python]\n"
    )
    result = CliRunner().invoke(main, ["setup-agentic-flow", "--project", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert (tmp_path / GUARD_HOOK_RELPATH).is_file()
    settings = json.loads((tmp_path / SETTINGS_RELPATH).read_text(encoding="utf-8"))
    commands = [
        hook["command"]
        for entry in settings["hooks"]["PreToolUse"]
        for hook in entry["hooks"]
    ]
    for name in GUARD_NAMES:
        assert any(command.endswith(f"beadloom-guard.sh {name}") for command in commands)


class TestSettingsOfTheWrongShapeAreNeverRewritten:
    """"Report and leave alone" must hold for readable-but-unexpected JSON too.

    A scaffolder that eats an adopter's configuration is not worth the hook it
    installs, and readable-but-wrong is the shape a hand-edited file actually
    takes — a plain-JSON parse failure is the easy case.
    """

    @staticmethod
    def _write(root, payload: object) -> str:
        path = root / SETTINGS_RELPATH
        path.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(payload)
        path.write_text(text, encoding="utf-8")
        return text

    def test_a_hooks_key_that_is_not_an_object_is_reported_and_left_untouched(
        self, tmp_path
    ) -> None:
        original = self._write(tmp_path, {"hooks": "PreToolUse"})

        result = scaffold_guard_hooks(tmp_path, guard_names=GUARDS)

        assert result.guards_registered == []
        assert "not an object" in result.settings_skipped_reason
        assert (tmp_path / SETTINGS_RELPATH).read_text(encoding="utf-8") == original

    def test_a_pretooluse_key_that_is_not_a_list_is_reported_and_left_untouched(
        self, tmp_path
    ) -> None:
        original = self._write(tmp_path, {"hooks": {"PreToolUse": {"matcher": "Edit"}}})

        result = scaffold_guard_hooks(tmp_path, guard_names=GUARDS)

        assert result.guards_registered == []
        assert "not a list" in result.settings_skipped_reason
        assert (tmp_path / SETTINGS_RELPATH).read_text(encoding="utf-8") == original

    def test_a_settings_file_that_is_a_json_array_is_reported_and_left_untouched(
        self, tmp_path
    ) -> None:
        original = self._write(tmp_path, ["not", "an", "object"])

        result = scaffold_guard_hooks(tmp_path, guard_names=GUARDS)

        assert result.guards_registered == []
        assert result.settings_skipped_reason
        assert (tmp_path / SETTINGS_RELPATH).read_text(encoding="utf-8") == original

    def test_malformed_entries_beside_a_valid_one_do_not_stop_registration(
        self, tmp_path
    ) -> None:
        """A foreign entry Beadloom cannot read is skipped, not treated as ours."""
        self._write(
            tmp_path,
            {"hooks": {"PreToolUse": ["a bare string", {"hooks": ["not an object"]}]}},
        )

        result = scaffold_guard_hooks(tmp_path, guard_names=GUARDS)

        assert sorted(result.guards_registered) == sorted(GUARDS)
        entries = json.loads((tmp_path / SETTINGS_RELPATH).read_text(encoding="utf-8"))
        assert entries["hooks"]["PreToolUse"][0] == "a bare string"

    def test_scaffolding_no_guards_writes_nothing_at_all(self, tmp_path) -> None:
        """An empty registry must not leave an adapter script that guards nothing."""
        result = scaffold_guard_hooks(tmp_path, guard_names=[])

        assert result.script is None
        assert list(tmp_path.iterdir()) == []


class TestTheMatcherIsTheOnlyRouterAndItLivesInTheHarness:
    """Independent re-verification (BDL-061.26) of the SPEC's event-routing claim.

    SPEC.md, after ``on:`` was deleted: "Which tool invocations count as an edit
    is decided entirely by the harness adapter — in Claude Code, the
    ``Edit|Write|NotebookEdit`` matcher in ``.claude/settings.json``".

    The first half is TRUE and asserted below: the routing decision exists only
    as a matcher string the scaffolder writes into the harness's settings, and no
    Beadloom code reads it back.

    The second half quotes the wrong string. The scaffolder emits
    ``Edit|Write|MultiEdit|NotebookEdit``; the three-tool spelling is what *this*
    repo's hand-written ``.claude/settings.json`` carries (review .3, m5 — still
    open). So the SPEC describes the dogfood rather than the product, on the one
    sentence a reader consults to learn what an adopter gets.
    """

    def test_the_routing_decision_exists_only_in_the_harness_settings(
        self, tmp_path
    ) -> None:
        scaffold_guard_hooks(tmp_path, guard_names=GUARDS)
        settings = json.loads((tmp_path / SETTINGS_RELPATH).read_text(encoding="utf-8"))

        matchers = {entry["matcher"] for entry in settings["hooks"]["PreToolUse"]}

        assert matchers == {"Edit|Write|MultiEdit|NotebookEdit"}
        # Nothing in the emitted adapter narrows or re-decides it.
        script = (tmp_path / GUARD_HOOK_RELPATH).read_text(encoding="utf-8")
        for tool in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
            assert tool not in _script_logic_lines(script)[0]

    def test_the_spec_quotes_a_matcher_the_scaffolder_does_not_emit(self) -> None:
        """RECORDED GAP: correcting either side reddens this, which is the point."""
        from pathlib import Path

        from beadloom.onboarding.guard_hooks import EDIT_MATCHER

        spec = (
            Path(__file__).resolve().parent.parent
            / "docs"
            / "domains"
            / "application"
            / "features"
            / "flow-guards"
            / "SPEC.md"
        ).read_text(encoding="utf-8")

        assert EDIT_MATCHER == "Edit|Write|MultiEdit|NotebookEdit"
        assert "`Edit|Write|NotebookEdit` matcher" in spec
        assert EDIT_MATCHER not in spec
