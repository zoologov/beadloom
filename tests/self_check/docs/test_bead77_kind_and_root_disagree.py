"""Self-checks of this repository's documents and published site (BDL-074 A3).

Moved out of ``tests/test_bead77_kind_and_root_disagree.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

from itertools import combinations

from beadloom.application.doc_spaces import (
    check_spaces,
)
from beadloom.infrastructure.doc_roots import (
    SPACE_WORKING,
    SPACES,
    resolve_doc_spaces,
)
from tests.support.doc_root_populations import (
    found_by_any_root,
    populations_by_space,
)
from tests.support.repository_root import REPO_ROOT


class TestTheHoleIsInvisibleOnThisRepositoryAndOnAnAdopter:
    """TRUE HERE IS NOT TRUE, in both directions.

    Beadloom's own stems happen to agree with its own roots, which is exactly why
    three rounds of review counted the population correctly and none of them saw
    this. The repository leg proves the fix is silent here; the adopter leg
    proves it is not silent on a project that is not us.
    """

    def test_this_repository_places_every_document_a_root_found(self) -> None:
        spaces = resolve_doc_spaces(REPO_ROOT)
        populations = populations_by_space(REPO_ROOT, spaces)
        populations[SPACE_WORKING] = len(spaces.working_documents(REPO_ROOT))

        assert sum(populations.values()) == len(found_by_any_root(REPO_ROOT, spaces))

    def test_this_repository_reports_no_disagreement(self) -> None:
        """Zero here, and zero is the honest number rather than a silence."""
        spaces = resolve_doc_spaces(REPO_ROOT)

        assert spaces.classify(REPO_ROOT).outside_declared_root == ()

    def test_no_two_spaces_of_this_repository_hold_the_same_document(self) -> None:
        """A document counted twice adds up as well as a document counted once.

        The sum above is one equation with two unknowns and cannot tell a double
        count from a drop, so the partition is stated as two claims rather than
        one. Verified red by making ``classify`` append each path to the WORKING
        bucket as well as to its own.
        """
        classified = resolve_doc_spaces(REPO_ROOT).classify(REPO_ROOT)
        buckets = {space: set(classified.by_space[space]) for space in SPACES}

        shared = {
            f"{left}+{right}": sorted(str(p) for p in buckets[left] & buckets[right])
            for left, right in combinations(SPACES, 2)
            if buckets[left] & buckets[right]
        }

        assert shared == {}

    def test_no_space_this_repository_declares_is_empty(self) -> None:
        """The floor the three deleted literals were also holding, without them.

        `203`, `116` and `58` pinned an exact size, and every move in them since
        they were written was a document this project added on purpose. What
        they could actually CATCH was a space collapsing — a root that stopped
        matching, a kind list withdrawn — and that is a relation, so it is
        stated as one. Verified red by withdrawing the WORKING kind list, which
        is the whole of that space's declaration.
        """
        classified = resolve_doc_spaces(REPO_ROOT).classify(REPO_ROOT)

        empty = [space for space in SPACES if not classified.by_space[space]]

        assert empty == []


class TestADeclaredKindIsNotShadowedByADefaultList:
    """Kind precedence is a decision with a reason, not a reporting order reused.

    ``space_of_kind`` walked ``SPACES``, whose own docstring says it is "every
    space, in the order a report reads best". One constant asked to mean two
    things, which is `.74`'s ``not_verified`` one module over: the AS-IS DEFAULT
    kind list silently beat a project's explicit WORKING declaration.
    """

    def test_this_repository_declares_no_kind_in_two_spaces(self) -> None:
        """The precedence question asked of this repository, instead of counted.

        This case asserted ``populations[SPACE_TO_BE] == 203``,
        ``populations[SPACE_AS_IS] == 116`` and
        ``len(spaces.working_documents(REPO_ROOT)) == 58``, under forty lines of
        comment recording every increment, because each bead that added a
        planning document or a node document had to find and bump one of them.
        That is `beadloom-mr2l.72`'s class in its sharpest form: a fact about
        this repository's own documents, maintained by hand, in a file the bead
        that moves it has no other reason to touch. Measured on this tree at
        `9d0c02a`: planting one feature directory holding a BRIEF and an ACTIVE
        plus one node SPEC reddened exactly two cases in the whole suite,
        holding four literals between them.

        WHAT THE COUNTS WERE NOT. This class is about kind precedence, and its
        claim is that ``space_of_kind`` cannot be decided by the order ``SPACES``
        is walked in. The counts stated a CONSEQUENCE of that for one tree at one
        moment. The condition itself is that no kind is claimed by two spaces,
        and it is checkable directly on the resolved declaration — including on
        a future configuration of this repository that creates the case by
        declaring a kind twice, which is the only way this can now go red.

        WHERE THE POPULATION CLAIMS WENT.
        `TestTheHoleIsInvisibleOnThisRepositoryAndOnAnAdopter` states them as
        relations: the populations sum to what the roots found, no two spaces
        share a document, and no declared space is empty.
        """
        spaces = resolve_doc_spaces(REPO_ROOT)

        declaring: dict[str, list[str]] = {}
        for space in SPACES:
            for kind in spaces.kinds.get(space, ()):
                declaring.setdefault(kind.upper(), []).append(space)

        claimed_twice = {k: v for k, v in declaring.items() if len(v) > 1}
        resolved = {kind: spaces.space_of_kind(kind) for kind in declaring}

        assert claimed_twice == {}
        assert resolved == {kind: declared[0] for kind, declared in declaring.items()}


class TestTheTwoReadingsOfExemptAreNamedApart:
    """Two adjacent lines of one run said 0 and 55 about "exempt"."""

    def test_the_command_makes_no_pair_claim_it_did_not_measure(self) -> None:
        """``docs spaces`` runs no freshness check, so it states no pair count.

        Saying nothing about a number you did not compute is the difference
        between a report and a guess; the gate, which HAS the number, prints it.
        """
        report = check_spaces(
            REPO_ROOT,
            spaces=resolve_doc_spaces(REPO_ROOT),
            known_refs=frozenset(),
            documented_refs=frozenset(),
            declared_doc_paths=frozenset(),
            beads_by_epic={},
        )

        assert report.pairs_excused is None
