"""Self-checks of this repository's documents and published site (BDL-074 A3).

Moved out of ``tests/integration/graph/scenarios/test_reference_leg_syntax.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

from beadloom.graph.scenarios import (
    ScenarioReference,
    load_references,
    parse_scenario_references,
)
from tests.support.repository_root import REPO_ROOT

SHIPPED_REFERENCE_GLOBS = (
    ".claude/development/docs/features/**/PRD.md",
    ".claude/development/docs/features/**/BRIEF.md",
)


def _documents_this_project_ships() -> list[str]:
    """Every file the shipped globs match, globbed here and not asked of the loader.

    The loader's own iteration is what the cases below are about, so the list
    they judge it against is recomputed from the globs — the shape
    `test_a_kind_and_root_disagreement_is_reported._found_by_any_root` uses one module over,
    and for the same reason: a reader that agrees with itself proves nothing
    about whether it lost a file.

    Spelled project-relative and sorted as text, because that is the spelling
    the loader reports and `Path` orders `BDL-025` before `BDL-025-UX` where
    text orders them the other way.
    """
    return sorted(
        {
            path.relative_to(REPO_ROOT).as_posix()
            for glob in SHIPPED_REFERENCE_GLOBS
            for path in REPO_ROOT.glob(glob)
            if path.is_file()
        }
    )


class TestNoDocumentThisProjectShipsIsLostOrUnreadable:
    """The corpus leg states the loader's accounting instead of counting it.

    It carried ``len(found.references) == 50`` — 33 when the false-positive
    removal shipped, 36 with BDL-067, 50 with BDL-068 — and that literal is a
    copy of a fact this project can derive. `409e977` added the epic's own PRD
    with 14 references and left the literal at 36, so the suite was red between
    that commit and the next person to run it. That is `beadloom-mr2l.72`'s
    class: a fact with two homes is a fact that can disagree.

    WHICH HALF IS DERIVED, because the two are not the same thing
    (`beadloom-0mdo.47`, argued at length in
    `tests/test_a_commit_is_judged_against_the_declared_axes.py`). Deriving the
    check's INPUT from the document is legitimate; deriving its OUTPUT is the
    tautology. These cases derive the INPUT — which documents this project ships
    — and make no claim about parsing: the per-document expectation calls
    ``parse_scenario_references``, the same parser the loader calls, so a parser
    bug is invisible here by construction and belongs to the synthetic cases
    above, where an expectation can be written down. What is checked is the
    LOADER's accounting: a document the globs matched and the reader silently
    dropped is reported by nothing else in this file, and it is the hole `.19`
    found one module over in ``documents_in``.
    """

    def test_the_loader_reads_every_document_the_globs_match(self) -> None:
        """The document accounting, which is the half a reference count cannot hold.

        MEASURED, and it changed this bead's design. The first version of this
        case asserted only the references and was verified NOT red against a
        loader that skips its first matched document — because that document is
        `BDL-006/PRD.md`, one of the 53 shipped PRDs and BRIEFs that state no
        scenario at all. An assertion that cannot fail is worse than the literal
        it replaced, so ``ReferenceSet.documents`` was added and this is the
        claim that bites.
        """
        found = load_references(REPO_ROOT, SHIPPED_REFERENCE_GLOBS)

        assert sorted(found.documents) == _documents_this_project_ships()

    def test_the_loader_loses_no_reference_a_shipped_document_states(self) -> None:
        """The loader's references are the union of the per-document parse.

        Verified red by making ``load_references`` skip a document that states a
        scenario, and by making a shipped PRD undecodable.
        """
        found = load_references(REPO_ROOT, SHIPPED_REFERENCE_GLOBS)

        expected: set[ScenarioReference] = set()
        for relative in _documents_this_project_ships():
            text = (REPO_ROOT / relative).read_text(encoding="utf-8")
            expected |= set(parse_scenario_references(text, path=relative))

        assert set(found.references) == expected

    def test_no_shipped_document_is_unreadable_and_no_glob_is_dead(self) -> None:
        """Both reports are empty on this repository, and both can fill up."""
        found = load_references(REPO_ROOT, SHIPPED_REFERENCE_GLOBS)

        assert found.unreadable == ()
        assert found.dead_globs == ()

    def test_the_shipped_corpus_states_scenarios_at_all(self) -> None:
        """Without this, the union above is two empty sets agreeing.

        Measured on this tree at `9d0c02a`: 56 documents match and 3 of them
        carry every reference — `BDL-061/PRD.md` 33, `BDL-068/PRD.md` 14 and
        `BDL-067/BRIEF.md` 3. A per-document floor would therefore be false on
        53 of 56, and this is the honest floor instead.
        """
        found = load_references(REPO_ROOT, SHIPPED_REFERENCE_GLOBS)
        shipped = set(_documents_this_project_ships())

        assert shipped != set()
        assert found.references != ()
        assert {reference.path for reference in found.references} <= shipped
