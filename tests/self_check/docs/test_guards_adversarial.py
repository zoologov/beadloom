"""Self-checks of this repository's documents and published site (BDL-074 A3).

Moved out of ``tests/test_guards_adversarial.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

from pathlib import Path

from beadloom.application.guards.paths import (
    NATIVE_PATHS,
    POSIX_PATHS,
    WINDOWS_PATHS,
    rejection_reason,
)

_SPEC = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "domains"
    / "application"
    / "features"
    / "flow-guards"
    / "SPEC.md"
)


class TestTheAcceptedShapeAgreesWithTheSpec:
    """What the SPEC says is accepted must not be refused, and vice versa.

    The SPEC sentence under test (``flow-guards/SPEC.md``, "The accepted shape"):
    a well-formed edit target is a non-empty string with no C0 control character
    and no ``DEL``, no directory separator this platform does not use, no leading
    ``~``, no component this platform's own name layer would rewrite, and
    encodable for this filesystem.

    Two of those clauses are platform-conditional since beadloom-0mdo.33, so the
    rows below assert the answer for THIS platform and
    :mod:`tests.test_windows_dimension` asserts the other platform's by passing
    its flavour in. The two files divide the same sentence, they do not repeat it.
    """

    def test_every_clause_of_the_spec_sentence_is_enforced_by_the_code(self) -> None:
        """The SPEC's shape sentence and ``rejection_reason`` must not drift apart.

        F6 was the SPEC quoting a matcher the code does not emit. This is the
        same pairing for the sentence that now decides what a guard will look at:
        each clause the document states is exercised against a string that
        breaks only that clause.
        """
        sentence = " ".join(_SPEC.read_text(encoding="utf-8").split())
        clauses = {
            "no C0 control character and no `DEL`": ("a\x01b", NATIVE_PATHS),
            "contains no directory separator this platform does not use": (
                "a\\b",
                POSIX_PATHS,
            ),
            "does not begin with `~`": ("~a", NATIVE_PATHS),
            "contains no component this platform's own name layer would rewrite": (
                "docs/CON.md",
                WINDOWS_PATHS,
            ),
            "can be encoded for this filesystem": ("a\ud800b", NATIVE_PATHS),
        }

        for clause, (breaker, flavour) in clauses.items():
            assert clause in sentence, f"the SPEC no longer states: {clause}"
            assert rejection_reason(breaker, flavour=flavour) != "", (
                f"unenforced clause: {clause}"
            )


class TestAnEmptyTargetIsAbsentAndTheSpecNowSaysSo:
    """CLOSED by BDL-061.29, in the document — which is where the defect was.

    The SPEC's shape sentence opened with "a non-empty string", so by the
    document an empty target was an ``error``; the code classified it
    :attr:`PathScope.ABSENT` and the guard ran normally, naming the missing path
    in ``not_covered``. The code had the better behaviour ("no path supplied" is
    not "a malformed path"), so the SPEC was corrected to it — F6's class.

    A whitespace-only target is no longer absent, because nothing is stripped
    before the judgement: ``'   '`` names a file called three spaces and
    ``'\\t'`` carries a control character.
    """

    def test_the_spec_no_longer_calls_an_empty_target_malformed(self) -> None:
        """The two artifacts are read together, so they cannot drift apart again.

        Whitespace-normalised before the search, as its sibling row below already
        is: the document wraps at 95 columns, so a sentence that keeps saying the
        same thing can move a line break into the middle of the phrase. That is a
        false red about the prose rather than a finding about the code, and it
        cost one on beadloom-0mdo.33.
        """
        spec = " ".join(_SPEC.read_text(encoding="utf-8").split())

        assert "absent or empty target is not a refusal" in spec
