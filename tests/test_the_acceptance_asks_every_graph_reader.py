"""The acceptance scenario's reader population equals the derived one.

BDL-069 acceptance (`beadloom-956f`). The scenario
`A graph file carrying one ref_id twice is reported by every reader of the
directory` asks a list of readers held in its own probe module, and a list held in
one place is a list that goes stale in the other. `beadloom-4ad3` derived the
population by experiment and :mod:`tests.support.graph_directory_readers` holds
that derivation; this module is the join between the two.

**Why the scenario keeps a list of its own.** The scenario asks each reader
through a probe (:mod:`tests.support.duplicate_ref_id_probes`), and the probe
list is what the scenario claims to cover. Deriving it from the population would
make the claim agree with itself. So the two lists stay two, and this test is
what stops them drifting apart: an eighth reader added to the derivation fails
here, by name, before it can be silently left out of the claim.

Until BDL-074 B1 the probes also had to live in the step module, because
`tests/integration/graph/scenarios/test_bead14_s4_binding.py` copied `tests/acceptance/` out alone
and the `tests` package was not importable there. The copy now carries `tests/support/`
beside it, so the probes live with the other shared helpers.
"""

from __future__ import annotations

from tests.support.duplicate_ref_id_probes import PROBES
from tests.support.graph_directory_readers import (
    BYTE_READERS,
    NODE_READERS,
    THE_READERS,
)


class TestTheTwoListsAreOneList:
    """One population, named in two files, and neither is allowed to move alone."""

    def test_the_scenario_asks_exactly_the_readers_the_derivation_names(self) -> None:
        asked = set(PROBES)
        derived = {reader.name for reader in THE_READERS}

        assert asked == derived, {
            "asked by the scenario and not derived": sorted(asked - derived),
            "derived and not asked by the scenario": sorted(derived - asked),
        }

    def test_the_population_is_not_all_of_one_kind(self) -> None:
        """Anti-vacuity: a derivation that had collapsed to one kind would still match.

        The scenario's claim is that the readers which reduce report and the rest
        have nothing to drop, so it says nothing at all if every reader turns out
        to be on one side. The split is `beadloom-4ad3`'s measurement: five read
        the directory for nodes, two read it for bytes.
        """
        assert len(NODE_READERS) == 5, [reader.name for reader in NODE_READERS]
        assert len(BYTE_READERS) == 2, [reader.name for reader in BYTE_READERS]
