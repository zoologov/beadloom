"""Self-checks of this repository's documents and published site (BDL-074 A3).

Moved out of ``tests/test_guard_hook_adapter.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

from tests.support.repository_root import REPO_ROOT


class TestTheMatcherIsTheOnlyRouterAndItLivesInTheHarness:
    """Independent re-verification (BDL-061.26) of the SPEC's event-routing claim.

        SPEC.md, after ``on:`` was deleted: "Which tool invocations count as an edit
        is decided entirely by the harness adapter — in Claude Code, the
        ``Edit|Write|NotebookEdit`` matcher in ``.claude/settings.json``".

        The first half is TRUE and asserted below: the routing decision exists only
        as a matcher string the scaffolder writes into the harness's settings, and no
        Beadloom code reads it back.

    The second half used to quote the wrong string — the three-tool spelling from
        *this* repo's hand-written ``.claude/settings.json`` (review .3, m5, still
        open) rather than the four the scaffolder writes. The SPEC now quotes the
        constant, and the test below asserts the two agree rather than asserting a
        literal, so they cannot drift apart again in silence.
    """

    def test_the_spec_quotes_the_matcher_the_scaffolder_actually_emits(self) -> None:
        """F6: the SPEC quoted the three-tool spelling this repo happens to use.

        The sentence a reader consults to learn what an adopter gets described the
        dogfood instead of the product. Asserted against the constant rather than
        against a literal, so the pair cannot drift apart again silently.
        """

        from beadloom.onboarding.guard_hooks import EDIT_MATCHER

        spec = (
            REPO_ROOT
            / "docs"
            / "domains"
            / "application"
            / "features"
            / "flow-guards"
            / "SPEC.md"
        ).read_text(encoding="utf-8")

        assert f"`{EDIT_MATCHER}` matcher" in spec
