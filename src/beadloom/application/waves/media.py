"""What a wave shares no matter how independent its beads' code is.

This module exists because of a measurement, not a theory. A wave shape derived
only from the graph answers one question — do these beads touch the same code —
and this project ran roughly twenty concurrent waves in one session in which
every failure that actually cost work came from a medium the graph knows nothing
about:

* the **working tree** is one tree, so a per-agent clean-room green is a claim
  about N files and not about the tree; four agents reported green while the
  combined tree was red, and nothing ran the combined tree until the coordinator
  did it last (BDL-UX #181);
* the **commit gate** is one hook, and it judged the whole tree, so one agent's
  commit was failed by a neighbour's in-progress work (BDL-UX #118);
* the **doc baseline** is per node, so one changed file marks every pair its node
  owns and the wave's doc pass is handed pairs nobody can revise (BDL-UX #182,
  and the same mechanism at integration time, #133);
* the **tracker id space** allocates at creation while our convention writes the
  id beforehand, so a concurrent wave produces a well-formed, accepted, wrong
  dependency edge (BDL-UX #171).

So the media are STATED by every wave that runs more than one bead, each with the
evidence it comes from. A shape that quietly claimed independence in these four
would be exactly the advisory answer this command exists to replace.
"""

# beadloom:feature=wave-plan

from __future__ import annotations

from beadloom.application.waves.models import SharedMedium

MEDIUM_WORKING_TREE = "working-tree"
MEDIUM_COMMIT_GATE = "commit-gate"
MEDIUM_DOC_BASELINE = "doc-baseline"
MEDIUM_TRACKER_IDS = "tracker-ids"

#: Stated in the order a wave meets them: it edits, it commits, it documents, and
#: it files follow-up work.
SHARED_MEDIA: tuple[SharedMedium, ...] = (
    SharedMedium(
        name=MEDIUM_WORKING_TREE,
        statement=(
            "One tree. An agent's green is green in a clean room over its own "
            "files, which is a different claim from green on the tree — report "
            "them in different words, and let the wave's gate owner measure the "
            "tree."
        ),
        evidence="BDL-UX #181",
    ),
    SharedMedium(
        name=MEDIUM_COMMIT_GATE,
        statement=(
            "One pre-commit hook. A commit is judged over the paths it stages, "
            "and the hook states how much of the tree it therefore did not "
            "judge; the push gate judges the whole tree."
        ),
        evidence="BDL-UX #118",
    ),
    SharedMedium(
        name=MEDIUM_DOC_BASELINE,
        statement=(
            "One doc-freshness baseline, hashed per node. One bead's changed "
            "file marks every pair its node owns, including a neighbour's — so "
            "a wave's doc pass is handed pairs it cannot revise, and bulk "
            "re-attestation is the only move the tool offers."
        ),
        evidence="BDL-UX #182, #133",
    ),
    SharedMedium(
        name=MEDIUM_TRACKER_IDS,
        statement=(
            "One id space, allocated at creation. Do not write a bead's number "
            "into its own title, and verify every dependency edge against the "
            "titles the tracker echoes rather than against the ids you intended."
        ),
        evidence="BDL-UX #171",
    ),
)


def media_for(wave_size: int) -> tuple[SharedMedium, ...]:
    """The media a wave of *wave_size* beads shares.

    A wave of one shares nothing with anybody: its clean room IS the tree, its
    commit is the only commit, and no neighbour can move its baseline. Saying so
    keeps the list a statement about concurrency rather than a banner.
    """
    return SHARED_MEDIA if wave_size > 1 else ()
