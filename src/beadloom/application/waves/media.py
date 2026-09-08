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
  dependency edge (BDL-UX #171);
* the **landing order** is one branch, and the lock every launch prompt mandates
  before a commit grants nothing in the form this project instructs it — one
  tracker actor for every role, a release nobody checks, and a ``--wait`` that
  queues and returns (BDL-UX #194, #237).

So the media are STATED by every wave, at every size, each with the evidence it
comes from. A shape that quietly claimed independence in these five would be
exactly the advisory answer this command exists to replace.

**Why every size, when the first version said a wave of one shares nothing**
(BDL-UX #228). ``wave_size`` is the width of a wave in ONE plan, and a plan is
one slice of one epic. It is therefore not a statement about solitude, and this
module already knew that: :func:`~beadloom.application.waves.media_checks`
fails the working tree on paths that differ from ``HEAD`` and are owned by **no
bead in the plan** — work that arrived from outside it. Measured against the
consequence: roughly twenty single-bead waves ran across two epics, and in every
one of them the discipline travelled by the coordinator's launch prompt, because
the instrument said ``not_applicable`` exactly where the coordinator was not
already thinking about concurrency.

**The scratchpad is a shared medium and is deliberately not one of these.** Two
concurrent agents each built a clean room at the same session-scratchpad path,
and one measurement was taken over its neighbour's untracked files while looking
exactly like a correct clean room (BDL-UX #235). It is not enumerated here
because a medium in this module is one with a plan-time precondition a command
can OBSERVE — git, the installed hook, the doc index, the bead records — and a
session scratchpad has none: its path exists only inside a running agent
session, the same reason a launch prompt is ``not_inspected`` rather than a
finding in :mod:`beadloom.onboarding.role_duties`. Adding it would buy a fifth
verdict that is permanently ``unmeasured`` (a finding on every plan) or
permanently true (a check that cannot fail), and this epic forbids both. What is
observable is the REMEDY, so the remedy is what ships: :func:`room_for` names
the room a bead owes, the working-tree statement carries it, and the role cores
carry the same spelling.
"""

# beadloom:feature=wave-plan

from __future__ import annotations

from beadloom.application.waves.models import SharedMedium

MEDIUM_WORKING_TREE = "working-tree"
MEDIUM_COMMIT_GATE = "commit-gate"
MEDIUM_DOC_BASELINE = "doc-baseline"
MEDIUM_TRACKER_IDS = "tracker-ids"
MEDIUM_LANDING_ORDER = "landing-order"

#: The prefix a clean room's directory carries, so the room names its owner.
#: A constant because the role cores promise this exact spelling and a test
#: binds the two — a rename here reddens the prose that offers it.
ROOM_PREFIX = "room-"

#: Stated in the order a wave meets them: it edits, its commit is judged, it
#: lands, it documents, and it files follow-up work.
SHARED_MEDIA: tuple[SharedMedium, ...] = (
    SharedMedium(
        name=MEDIUM_WORKING_TREE,
        statement=(
            "One tree. An agent's green is green in a clean room over its own "
            "files, which is a different claim from green on the tree — report "
            "them in different words, and let the wave's gate owner measure the "
            f"tree. Build the room at `{ROOM_PREFIX}<bead-id>`, never at a "
            "shared path: a room whose name cannot say whose it is is a shared "
            "directory with a reassuring name."
        ),
        evidence="BDL-UX #181, #235",
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
        name=MEDIUM_LANDING_ORDER,
        statement=(
            "One branch, landed into one commit at a time. What keeps two "
            "agents out of one FILE is the disjoint scopes this plan derived, "
            "and nothing else — every concurrent wave this project has run was "
            "serialised by that and by the file sets happening to be disjoint. "
            "`bd merge-slot` keeps two commits from interleaving, and only in "
            "the form that grants it: `acquire --holder <bead-id>`, where a "
            "non-zero exit means you do NOT hold the slot, and `release "
            "--holder <bead-id>`, which is the only release bd checks. The "
            "default holder is the tracker actor, one identity for every role, "
            "and `--wait` appends you to a queue nothing drains and returns "
            "without waiting."
        ),
        evidence="BDL-UX #194, #237",
    ),
    SharedMedium(
        name=MEDIUM_DOC_BASELINE,
        statement=(
            "One doc-freshness baseline, in one git-ignored index. The freshness "
            "fact is recorded per FILE, so a bead's change no longer marks the "
            "pairs its node's other files own — but an attestation still "
            "re-baselines every pair of the ref it names, so attest by ref and "
            "never with `--all` while a neighbour is editing."
        ),
        evidence="BDL-UX #163, #182, #133",
    ),
    SharedMedium(
        name=MEDIUM_TRACKER_IDS,
        statement=(
            "One id space, allocated at creation. Do not write a bead's number "
            "into its own title, and verify every dependency edge against the "
            "titles the tracker echoes rather than against the ids you intended. "
            "A creation of more than one bead goes through ONE plan, whose edges "
            "name plan-local keys — on that path no id is authored, so there is "
            "nothing to diverge; a `dep add` wired by hand is where the echo is "
            "the only check, and the bulk `--file` form of it prints a count and "
            "no titles at all."
        ),
        evidence="BDL-UX #171, #165",
    ),
)


def room_for(bead_id: str) -> str:
    """The clean room *bead_id* owes — a directory nobody else will build.

    The one mechanical half of the working-tree medium. A wave states the room
    for each of its beads whatever its size, so a solo bead is told the same
    thing a concurrent one is: the measurement it reports is a measurement of
    this directory, and of nothing its neighbour left in a shared one.
    """
    return f"{ROOM_PREFIX}{bead_id}"
