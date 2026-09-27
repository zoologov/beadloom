"""Self-checks of this repository's agent roles, hooks, tracker and commits (BDL-074 A3).

Moved out of ``tests/test_role_configurator_hardening.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from beadloom.onboarding.flow_config import (
    load_flow_config,
)
from beadloom.onboarding.role_composer import (
    ROLE_NAMES,
    compose_role,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


class TestBeadloomSelfConsistency:
    def test_own_flow_is_claude_ddd_python(self) -> None:
        cfg = load_flow_config(REPO_ROOT)
        assert cfg.tools == ("claude",)
        assert cfg.architecture == "ddd"
        assert cfg.stack == ("python",)

    @pytest.mark.parametrize("role", ROLE_NAMES)
    def test_live_adapter_has_expected_markers(self, role: str) -> None:
        live = (REPO_ROOT / ".claude" / "agents" / f"{role}.md").read_text(
            encoding="utf-8"
        )
        # ddd architecture + python stack overlays present; FSD/vuejs absent.
        assert "overlay:ddd" in live
        assert "overlay:python" in live
        assert "overlay:fsd" not in live
        assert "Domain-Driven Design" in live

    @pytest.mark.parametrize("role", ROLE_NAMES)
    def test_live_adapter_byte_equals_compose(self, role: str) -> None:
        live = (REPO_ROOT / ".claude" / "agents" / f"{role}.md").read_text(
            encoding="utf-8"
        )
        assert live == compose_role(role, architecture="ddd", stack=["python"])
