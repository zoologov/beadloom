"""Self-checks of this repository's agent roles, hooks, tracker and commits (BDL-074 A3).

Moved out of ``tests/test_role_configurator.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

from beadloom.onboarding.flow_config import (
    load_flow_config,
)
from beadloom.onboarding.role_composer import (
    ROLE_NAMES,
    compose_all_roles,
)
from tests.support.repository_root import REPO_ROOT


class TestFlowConfigLoad:
    def test_beadloom_own_config_is_claude_ddd_python(self) -> None:
        cfg = load_flow_config(REPO_ROOT)
        assert cfg.tools == ("claude",)
        assert cfg.architecture == "ddd"
        assert cfg.stack == ("python",)


class TestDriftGuard:
    def test_live_claude_agents_reproduce_from_compose(self) -> None:
        # With this repository's project layer: that is what setup-agentic-flow
        # writes here, and what the live adapters must reproduce.
        composed = compose_all_roles(load_flow_config(REPO_ROOT), project_root=REPO_ROOT)
        for role in ROLE_NAMES:
            live = (REPO_ROOT / ".claude" / "agents" / f"{role}.md").read_text(
                encoding="utf-8"
            )
            assert live == composed[role], (
                f"{role}: .claude/agents/{role}.md drifted from "
                "compose_role(ddd, python) — re-run setup-agentic-flow"
            )
