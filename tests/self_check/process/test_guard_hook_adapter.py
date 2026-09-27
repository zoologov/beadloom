"""Self-checks of this repository's agent roles, hooks, tracker and commits (BDL-074 A3).

Moved out of ``tests/integration/onboarding/guard_hooks/test_guard_hook_adapter.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

import json
import stat

from beadloom.onboarding.guard_hooks import (
    GUARD_HOOK_RELPATH,
    SETTINGS_RELPATH,
    scaffold_guard_hooks,
)
from tests.support.repository_root import REPO_ROOT as _REPO_ROOT

#: This repository, used where the claim under test is about the dogfood itself.


class TestThisRepositoryRunsWhatItShips:
    """n1 (BDL-061.35): the dogfood must exercise the artifact adopters get.

    Until this bead, `.claude/settings.json` here registered the DIRECT CLI command
    while `scaffold_guard_hooks` emitted `.claude/hooks/beadloom-guard.sh` — so the
    shipped adapter had never run in this repository, and five review cycles read
    "dogfooded" as evidence about a path no adopter uses. That is the stated reason
    BDL-UX #170's narrower binding went unnoticed. These tests pin the repair to the
    scaffolder's own output rather than to literals, so the two cannot drift again.
    """

    @staticmethod
    def _live_commands() -> list[str]:
        settings = json.loads((_REPO_ROOT / SETTINGS_RELPATH).read_text(encoding="utf-8"))
        return [
            hook["command"] for entry in settings["hooks"]["PreToolUse"] for hook in entry["hooks"]
        ]

    def test_every_shipped_guard_is_bound_through_the_emitted_adapter(self) -> None:
        from beadloom.application.guards.checks import GUARD_NAMES
        from beadloom.onboarding.guard_hooks import hook_command

        commands = self._live_commands()
        for name in GUARD_NAMES:
            assert hook_command(name) in commands, name

    def test_no_guard_is_bound_by_the_direct_command_instead(self) -> None:
        assert [c for c in self._live_commands() if c.startswith("beadloom guard")] == []

    def test_the_committed_adapter_is_byte_identical_to_the_emitted_one(self, tmp_path) -> None:
        from beadloom.application.guards.checks import GUARD_NAMES

        scaffold_guard_hooks(tmp_path, guard_names=GUARD_NAMES)
        assert (_REPO_ROOT / GUARD_HOOK_RELPATH).read_bytes() == (
            tmp_path / GUARD_HOOK_RELPATH
        ).read_bytes()

    def test_the_committed_adapter_is_executable(self) -> None:
        """A non-executable adapter fires nothing, and the failure is silent."""
        assert (_REPO_ROOT / GUARD_HOOK_RELPATH).stat().st_mode & stat.S_IXUSR

    def test_the_live_matcher_is_the_one_the_scaffolder_emits(self) -> None:
        from beadloom.onboarding.guard_hooks import EDIT_MATCHER, hook_command

        settings = json.loads((_REPO_ROOT / SETTINGS_RELPATH).read_text(encoding="utf-8"))
        ours = [
            entry
            for entry in settings["hooks"]["PreToolUse"]
            if any(
                hook["command"].endswith(".sh bead-claimed")
                or hook["command"] == hook_command("working-branch")
                for hook in entry["hooks"]
            )
        ]
        assert ours
        assert {entry["matcher"] for entry in ours} == {EDIT_MATCHER}
