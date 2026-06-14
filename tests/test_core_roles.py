"""Structural / guard tests for the CORE role files (BDL-052 Slice 2 / BEAD-05).

The four role files under ``.claude/agents/`` are markdown, not code — so we
test their STRUCTURE deterministically (no LLM, no network):

- Each role's ``## CORE`` block carries the required universal sections
  (asserted by concept/key-phrase presence, robust to exact wording).
- CORE is **stack/tool-neutral**: the text before the ``<!-- overlay:python``
  marker must not name Python/tool specifics (``ruff``/``mypy``/``pytest``/…).
  This is the property S3 relies on to split the overlay — it is pinned here.
- A ``## STACK`` section exists and carries the Python specifics (the
  ``<!-- overlay:python`` marker plus the Python idioms live there, not in CORE).
- Vendoring drift-guard: each ``.claude/agents/<role>.md`` is byte-identical to
  its ``onboarding/templates/agentic_flow/agents/<role>.md.txt`` (the scaffold
  always ships the live flow).
- Annotation discipline lives in the **dev** CORE specifically (the dev emits
  ``# beadloom:`` annotations by construction).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from beadloom.onboarding.agentic_flow_setup import AGENT_FILES, vendored_flow_root

REPO_ROOT = Path(__file__).resolve().parents[1]
AGENTS_DIR = REPO_ROOT / ".claude" / "agents"

# The marker BEAD-04 used to delimit CORE (above) from the Python STACK (below).
OVERLAY_MARKER = "<!-- overlay:python"

# Tokens that betray a Python/tool-specific leak. If any of these appear in the
# CORE block (above the overlay marker), the CORE is no longer stack-neutral and
# S3's overlay split would carry repo-specifics into the universal section.
STACK_LEAK_TOKENS: tuple[str, ...] = (
    "ruff",
    "mypy",
    "pytest",
    "pathlib",
    "yaml",
    "sqlite",
    ".claude",
    "cursor",
    "uv run",
)


def _role_text(role: str) -> str:
    return (AGENTS_DIR / f"{role}.md").read_text(encoding="utf-8")


def _split_core_stack(text: str) -> tuple[str, str]:
    """Return (core_text, stack_text) split on the overlay marker.

    ``core`` is everything before the marker; ``stack`` is the marker onward
    (empty if the role has no stack overlay)."""
    idx = text.find(OVERLAY_MARKER)
    if idx == -1:
        return text, ""
    return text[:idx], text[idx:]


def _core_text(role: str) -> str:
    return _split_core_stack(_role_text(role))[0]


def _assert_has_all(haystack: str, phrases: tuple[str, ...], *, label: str) -> None:
    """Assert every phrase (case-insensitive substring) is present."""
    lowered = haystack.lower()
    missing = [p for p in phrases if p.lower() not in lowered]
    assert not missing, f"{label}: missing concept(s) {missing}"


# --------------------------------------------------------------------------- #
# Shared structural invariants (parametrized over all four roles)
# --------------------------------------------------------------------------- #


class TestRoleFileStructure:
    @pytest.mark.parametrize("role", AGENT_FILES)
    def test_role_file_exists(self, role: str) -> None:
        assert (AGENTS_DIR / f"{role}.md").is_file(), role

    @pytest.mark.parametrize("role", AGENT_FILES)
    def test_has_core_section_heading(self, role: str) -> None:
        text = _role_text(role)
        assert re.search(r"^##\s+CORE\b", text, re.MULTILINE), f"{role}: no '## CORE'"

    @pytest.mark.parametrize("role", AGENT_FILES)
    def test_has_single_overlay_marker(self, role: str) -> None:
        # Exactly one overlay marker delimits CORE from STACK (S3 split point).
        assert _role_text(role).count(OVERLAY_MARKER) == 1, role

    @pytest.mark.parametrize("role", AGENT_FILES)
    def test_has_stack_section_heading(self, role: str) -> None:
        _, stack = _split_core_stack(_role_text(role))
        assert re.search(r"^##\s+STACK\b", stack, re.MULTILINE), f"{role}: no STACK"


# --------------------------------------------------------------------------- #
# CORE neutrality — the property S3 relies on (pinned)
# --------------------------------------------------------------------------- #


class TestCoreIsStackNeutral:
    @pytest.mark.parametrize("role", AGENT_FILES)
    @pytest.mark.parametrize("token", STACK_LEAK_TOKENS)
    def test_core_has_no_stack_or_tool_token(self, role: str, token: str) -> None:
        core = _core_text(role).lower()
        assert token not in core, (
            f"{role} CORE leaks stack/tool token {token!r} — "
            "CORE must stay tool/stack-neutral so S3 can split overlays cleanly"
        )

    @pytest.mark.parametrize("role", AGENT_FILES)
    def test_stack_section_carries_python_specifics(self, role: str) -> None:
        # The Python specifics must live in STACK, not CORE — assert the STACK
        # block actually mentions Python (so the overlay is non-empty/real).
        _, stack = _split_core_stack(_role_text(role))
        assert "python" in stack.lower(), f"{role}: STACK does not mention Python"

    @pytest.mark.parametrize(
        ("role", "token"),
        [
            ("dev", "ruff"),
            ("dev", "mypy"),
            ("test", "pytest"),
            ("review", "mypy"),
            ("tech-writer", "sync-update"),
        ],
    )
    def test_stack_section_holds_the_tooling(self, role: str, token: str) -> None:
        # Sanity counterpart: the tool token DOES live in STACK (it was moved
        # there, not deleted) — proves the CORE-neutrality test isn't vacuous.
        _, stack = _split_core_stack(_role_text(role))
        assert token.lower() in stack.lower(), f"{role}: STACK missing {token!r}"


# --------------------------------------------------------------------------- #
# Per-role CORE required sections
# --------------------------------------------------------------------------- #


class TestDevCoreSections:
    def test_dev_core_has_required_concepts(self) -> None:
        core = _core_text("dev")
        _assert_has_all(
            core,
            (
                "TDD",  # TDD workflow
                "architecture",  # architecture discovery
                "boundary",  # DDD / boundary
                "Clean Code",  # clean code
                "naming",  # naming principles
                "Gate",  # validation / Gate loop
                "API CHANGE",  # API-CHANGE log
            ),
            label="dev CORE",
        )

    def test_dev_core_mentions_tdd_red_green_refactor(self) -> None:
        core = _core_text("dev").lower()
        assert "red" in core and "green" in core and "refactor" in core

    def test_dev_core_has_architecture_discovery(self) -> None:
        # "discover, don't assume" — discovery via the graph, not hardcoded.
        core = _core_text("dev").lower()
        assert "discover" in core
        assert "beadloom" in core  # uses the graph tooling to discover

    def test_dev_core_has_annotation_discipline_section(self) -> None:
        # Focused: the dev CORE must teach emitting the graph annotations.
        core = _core_text("dev")
        assert "Annotation discipline" in core
        _assert_has_all(
            core,
            ("# beadloom:domain", "# beadloom:feature", "# beadloom:component"),
            label="dev annotation discipline",
        )

    def test_dev_core_has_api_change_log_handoff(self) -> None:
        core = _core_text("dev")
        assert "API CHANGE" in core
        # It is a hand-off signal to the downstream roles.
        lowered = core.lower()
        assert "review" in lowered and "tech-writer" in lowered


class TestTestCoreSections:
    def test_test_core_has_required_concepts(self) -> None:
        core = _core_text("test")
        _assert_has_all(
            core,
            (
                "Arrange",  # AAA
                "edge",  # edge-case checklist
                "Mock",  # mocking principles
                "80%",  # coverage floor
            ),
            label="test CORE",
        )

    def test_test_core_aaa_is_arrange_act_assert(self) -> None:
        core = _core_text("test").lower()
        assert "arrange" in core and "act" in core and "assert" in core

    def test_test_core_edge_case_checklist_covers_key_cases(self) -> None:
        core = _core_text("test").lower()
        # A real checklist: empty/None, cycles, orphaned refs.
        _assert_has_all(
            core, ("none", "empty", "cycle", "orphan"), label="test edge cases"
        )

    def test_test_core_mocks_at_boundaries_not_private(self) -> None:
        core = _core_text("test").lower()
        assert "boundar" in core  # mock at boundaries
        assert "private" in core  # not private attributes


class TestReviewCoreSections:
    def test_review_core_has_all_checklists(self) -> None:
        core = _core_text("review")
        _assert_has_all(
            core,
            (
                "Readability",
                "Architecture",
                "Typing",
                "Error handling",
                "Security",
                "Testing",
                "Doc freshness",
            ),
            label="review CORE checklists",
        )

    def test_review_core_has_severity_levels(self) -> None:
        core = _core_text("review")
        _assert_has_all(
            core,
            ("Severity", "Critical", "Major", "Minor"),
            label="review severity",
        )

    def test_review_core_has_feedback_format(self) -> None:
        core = _core_text("review").lower()
        # File+line · Issue · Recommendation shape.
        assert "line" in core
        assert "recommendation" in core


class TestTechWriterCoreSections:
    def test_tw_core_has_two_source_staleness(self) -> None:
        core = _core_text("tech-writer")
        _assert_has_all(
            core,
            ("two", "staleness", "API CHANGE"),
            label="tech-writer two-source",
        )

    def test_tw_core_has_update_workflow_steps(self) -> None:
        core = _core_text("tech-writer").lower()
        # analyze → delta → update → reset-baseline.
        _assert_has_all(
            core,
            ("analyze", "delta", "update", "baseline"),
            label="tech-writer update workflow",
        )

    def test_tw_core_has_parallel_execution(self) -> None:
        core = _core_text("tech-writer").lower()
        assert "parallel" in core

    def test_tw_core_has_anti_patterns(self) -> None:
        core = _core_text("tech-writer").lower()
        assert "anti-pattern" in core


# --------------------------------------------------------------------------- #
# Vendoring drift-guard (byte-identical to the packaged templates)
# --------------------------------------------------------------------------- #


class TestVendoringDriftGuard:
    @pytest.mark.parametrize("role", AGENT_FILES)
    def test_live_role_byte_identical_to_vendored_template(self, role: str) -> None:
        live = (AGENTS_DIR / f"{role}.md").read_text(encoding="utf-8")
        vendored = (vendored_flow_root() / "agents" / f"{role}.md.txt").read_text(
            encoding="utf-8"
        )
        assert live == vendored, (
            f"{role}: .claude/agents/{role}.md drifted from the vendored "
            f"template {role}.md.txt — re-run sync-agentic-flow"
        )
