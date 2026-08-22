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
