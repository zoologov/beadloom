"""Wherever `lint --help` calls a finding advisory, it states what bounds the exclusion.

BDL-070 `beadloom-5tcc.5`. `--fail-on-warn` does not exit 1 on the two BDL-070
advisories, and `LintResult.fails_on_warn` bounds that exclusion by severity:
``any(v.severity == "error" or not is_advisory(v))``. The exclusion stops at
``error``, so the flag stays a superset of `--strict` whatever severity an
advisory is ever emitted at. `tests/test_linter.py` holds that property in code.

Two copies of the exclusion are rendered into `beadloom lint --help` — the
`--fail-on-warn` option's help and the command docstring's exit-code paragraph —
and both stated the exclusion without its bound. Neither was false: both advisory
constructors hardcode ``severity="warn"`` today, and each module constructs
exactly one `Violation` (measured, `layer_reach.py:232`, `layer_declaration.py:111`).
The bound exists for the day that stops being true, and a help text is where a
reader learns the flag's meaning without the source in hand.

**Why this sweeps rather than naming the two copies.** A third copy is added the
same way the second was: by someone writing a sentence about the flag into
another option's help. The sweep holds one rule over every help text the `lint`
command renders — a text that calls a finding advisory carries `BOUND_CLAUSE`
verbatim — so a copy written later is red on the commit that adds it rather than
found by the next review pass.

**What it cannot catch.** A copy in some other command's help, and a copy that
states the bound in different words. The first is deliberate: `advisory` is used
across this CLI in an unrelated sense — `setup.py` calls a pre-commit gate
"advisory-strong" — so a CLI-wide sweep on the word would fire on text this rule
has nothing to say about. The second is why the clause is a verbatim constant:
one wording, held in one place, matching the sentence `docs/domains/graph/README.md`
already carries.
"""

from __future__ import annotations

import click
import pytest

from beadloom.services.commands.federation import lint

#: The half-sentence every `lint` help text stating the exclusion must carry.
#: It is the bound itself: the exclusion selects by rule type and stops at
#: ``error``, so the harsher flag can never read softer than `--strict` on one
#: run. Held here rather than imported from the CLI because an oracle that reads
#: the value it checks cannot catch that value being wrong.
BOUND_CLAUSE = (
    "An advisory emitted at error severity exits 1 under --fail-on-warn as it does under --strict."
)


def _help_texts() -> list[tuple[str, str]]:
    """Every help text the `lint` command renders, as (where, text) pairs."""
    texts = [("docstring", lint.help or "")]
    texts += [
        (f"--{p.name.replace('_', '-')}", p.help or "")
        for p in lint.params
        if isinstance(p, click.Option) and p.help
    ]
    return texts


def _normalized(text: str) -> str:
    """*text* with its line wrapping collapsed, as a reader of `--help` sees it."""
    return " ".join(text.split())


def _states_the_exclusion(text: str) -> bool:
    """Whether *text* tells the reader a finding is excluded for being advisory."""
    return "advisory" in text.lower()


#: Computed once, so the parametrize ids and the population test read one list.
HELP_TEXTS = _help_texts()


class TestEveryLintHelpTextThatCallsAFindingAdvisoryCarriesTheBound:
    """The sweep, and the two copies it was written for."""

    @pytest.mark.parametrize("where, text", HELP_TEXTS, ids=[where for where, _ in HELP_TEXTS])
    def test_a_help_text_stating_the_exclusion_states_its_bound(
        self, where: str, text: str
    ) -> None:
        # Arrange
        normalized = _normalized(text)
        # Act
        states_exclusion = _states_the_exclusion(normalized)
        # Assert
        if states_exclusion:
            assert BOUND_CLAUSE in normalized, (
                f"{where} calls a finding advisory without stating what bounds "
                f"the exclusion; add: {BOUND_CLAUSE}"
            )

    def test_the_sweep_reaches_both_copies_this_bead_was_filed_for(self) -> None:
        """The population itself: a sweep over an empty set is green and useless."""
        # Act
        stating = [w for w, t in HELP_TEXTS if _states_the_exclusion(_normalized(t))]
        # Assert
        assert sorted(stating) == ["--fail-on-warn", "docstring"]
