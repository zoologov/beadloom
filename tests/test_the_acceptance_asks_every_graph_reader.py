"""The acceptance scenario's reader population equals the derived one.

BDL-069 acceptance (`beadloom-956f`). The scenario
`A graph file carrying one ref_id twice is reported by every reader of the
directory` asks a list of readers held in its own step module, and a list held in
one place is a list that goes stale in the other. `beadloom-4ad3` derived the
population by experiment and
:mod:`tests.test_what_each_reader_of_the_graph_directory_reads_for` holds that
derivation; this module is the join between the two.

**Why the scenario does not import the derivation directly.**
`tests/test_bead14_s4_binding.py` copies `tests/acceptance/` out of the
repository and runs it standalone to prove a broken step binding reddens the
suite. In that copy the `tests` package is not importable, so an import inside a
step module turns a sabotage of a different file's binding into a collection
failure of this one — the shape `test_bootstrap_self_consistency_steps` records
for its own fixtures. The list therefore travels with the scenario, and this test
is what stops the two drifting apart: an eighth reader added to the derivation
fails here, by name, before it can be silently left out of the claim.
"""

from __future__ import annotations

from tests.acceptance.steps.test_duplicate_ref_id_every_reader_steps import PROBES
from tests.test_what_each_reader_of_the_graph_directory_reads_for import (
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
