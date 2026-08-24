"""BDD and mutation are duties of a role, not advice in an epic document.

BDL-061 S4 (`beadloom-mr2l.13`). The practice being ported from the downstream
project reached its agents through `CLAUDE.md` user-prose, so the role subagents'
own system prompts never carried it (BDL-UX #139). It belongs in the role cores,
where every composition puts it in front of the agent that has to do it.

The mutation duty is scoped honestly (Q5): Beadloom does not own a mutation
runner — owning one would break tool-agnosticism — so what ships is the duty, the
scope convention, and where the target must live. The checker for a declared
target outside the configured source paths is a separate bead, and the template
says so rather than implying a check that does not exist (NO CALLER, NO CAPABILITY).
"""

from __future__ import annotations

import pytest

from beadloom.graph.scenarios import (
    BEAD_TAG_PREFIX,
    DEFAULT_FEATURE_GLOB,
    DEFAULT_STEPS_DIRNAME,
    NODE_TAG_PREFIX,
)
from beadloom.onboarding.role_composer import ROLE_NAMES, compose_role


def _role(name: str) -> str:
    return compose_role(name, architecture="ddd", stack=("python",))


class TestTheDevCarriesTheBddDuty:
    def test_it_names_the_layout_and_both_tags(self) -> None:
        text = _role("dev")
        assert DEFAULT_FEATURE_GLOB.split("**")[0] in text
        assert DEFAULT_STEPS_DIRNAME in text
        assert BEAD_TAG_PREFIX in text
        assert NODE_TAG_PREFIX in text

    def test_it_names_the_feature_file_as_the_source_of_truth(self) -> None:
        """CONTEXT's load-bearing decision, in front of the role that acts on it."""
        text = _role("dev").lower()
        assert "source of truth" in text

    def test_non_behavioural_work_has_a_stated_way_out(self) -> None:
        text = _role("dev")
        assert "non_behavioural" in text
        assert "reason" in text

    def test_the_rule_that_reports_the_gap_is_named(self) -> None:
        assert "scenario-coverage" in _role("dev")


class TestTheTesterCarriesTheMutationDuty:
    def test_the_scope_is_stated_and_bounded(self) -> None:
        text = _role("test")
        assert "mutation" in text.lower()
        assert "pure domain" in text.lower()
        assert "pre-commit" in text

    def test_the_tool_is_the_projects_choice(self) -> None:
        """Q5: owning a runner would break tool-agnosticism, so the duty ships alone."""
        assert "does not ship a mutation runner" in _role("test")


class TestTheReviewerChecksItIsNotCeremony:
    def test_the_checklist_names_the_failure_mode(self) -> None:
        text = _role("review")
        assert "ceremony" in text.lower()
        assert "scenario" in text.lower()


class TestTheShippedTemplatesStateCriteriaAsScenarios:
    """`templates.md` is where an author meets the practice; the form ships with it."""

    def _templates(self) -> str:
        from beadloom.onboarding.composer import compose
        from beadloom.onboarding.flow_config import FlowConfig

        config = FlowConfig(tools=("claude",), architecture="ddd", stack=("python",))
        return compose("commands", "templates", config=config).text

    def test_the_prd_states_its_criteria_as_scenarios(self) -> None:
        text = self._templates()
        assert "Scenario:" in text
        assert BEAD_TAG_PREFIX in text
        assert NODE_TAG_PREFIX in text

    def test_the_brief_carries_the_non_behavioural_decision(self) -> None:
        text = self._templates()
        brief = text[text.index("## BRIEF.md") :]
        assert "Non-behavioural" in brief
        assert "reason" in brief.lower()

    def test_the_scenario_form_is_a_form_and_not_a_claim(self) -> None:
        """Every example sits in a fenced block, so the reference check skips it."""
        from beadloom.graph.scenarios import parse_scenario_references

        assert parse_scenario_references(self._templates(), path="templates.md") == ()


class TestEveryRoleStaysComposable:
    @pytest.mark.parametrize("role", ROLE_NAMES)
    def test_the_front_matter_still_leads_the_file(self, role: str) -> None:
        """A duty appended into the wrong place breaks the adapter's header."""
        assert _role(role).startswith("---\nname: ")
