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
* the **focus document** is one file per work item that every one of its beads
  writes and no bead's code owns, so a plan that resolves a bead to the nodes and
  files its CODE occupies reports ``0 serialisations`` truthfully about the wrong
  population (BDL-UX #257). Confirmed four times in one slice, the last of them
  by an agent that did everything right: it took the landing lock in the form
  that grants it, waited, and its 43-line entry still landed inside a
  neighbour's commit — because the lock orders the COMMITS and the edit had
  already happened;
* the **graph files** are this plan's own input, and a bead that adds a node
  writes them. Measured by `beadloom-0mdo.59` in the same slice: four artifacts
  were shared by three beads whose code scopes are disjoint, and
  ``.beadloom/_graph/services.yml`` was one of them. The self-reference is
  stated rather than left for a reader to find — a derivation cannot describe
  its own input by asking it, because the node a bead is about to add is not in
  the graph the plan read (BDL-UX #261).

**Why the focus document is a medium and not a serialisation** (BDL-UX #257).
It cannot be one: ``docs.ref_id`` holds at most one node per document, and
:func:`~beadloom.application.waves.independence.conflict_between` already
serialises on ``shared_node`` whenever two scopes' refs intersect — so two beads
that reach a document comparison have disjoint refs, and disjoint refs give
disjoint owned documents by construction. Measured on this repository: a
``shared_document`` reason derived from document OWNERSHIP produces no
serialisation ``shared_node`` does not already produce, which is a check that
cannot fail. And it could not reach the measured case regardless: BDL-068's
ACTIVE.md is in the docs table nowhere, and the wave-2 collision was over
``docs/domains/application/README.md``, owned by ``application`` — an ancestor of
one of the two scopes and of neither.

**Why the graph files are a medium and not a serialisation either** (BDL-UX
#261). The entry sketched one: a bead's scope reaching the graph FILE its
declared nodes are defined in. Measured on this repository before it was built,
one file holds every one of this project's 100 nodes, so that reason fires on
EVERY pair and collapses every wave to a wave of one — BDL-UX #245's failure
mode — against a real write rate of 8 of the 55 commits this epic's branch
carries. It would also miss the
case it was drawn from, because both beads that collided were ADDING nodes and a
node being added is in no graph the plan can read. The condition under which it
becomes worth building is a graph split across files, and
``TestTheGraphFileCannotSerialiseWithoutNoise`` is that condition as a red test.

**And the population is still wider than these seven.** Two of `beadloom-0mdo.59`'s
four artifacts are answered here and two are not.
``tests/test_bead77_kind_and_root_disagree.py`` carries hand-maintained
population literals any node-adding bead must bump: one derivable fact with two
homes, whose answer is to remove the copy rather than to serialise around it.
``docs/services/components/cli-commands/DOC.md`` is owned by node
``cli-commands``, whose source covers both colliding beads' files and which
neither declared — so ``shared_node`` would have fired had either declared it,
and the plan already reports the gap as ``unguarded_axis``. Neither is absorbed
here; both are filed, with their paths.

So the media are STATED by every wave, at every size, each with the evidence it
comes from. A shape that quietly claimed independence in these seven would be
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
finding in :mod:`beadloom.onboarding.role_duties`. Adding it would buy a further
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
MEDIUM_FOCUS_DOCUMENT = "focus-document"
MEDIUM_GRAPH_FILES = "graph-files"

#: The prefix a clean room's directory carries, so the room names its owner.
#: A constant because the role cores promise this exact spelling and a test
#: binds the two — a rename here reddens the prose that offers it.
ROOM_PREFIX = "room-"

#: Stated in the order a wave meets them: it is derived from the graph before it
#: exists, then it edits, its commit is judged, it lands, it records where it got
#: to, it documents, and it files follow-up work.
SHARED_MEDIA: tuple[SharedMedium, ...] = (
    SharedMedium(
        name=MEDIUM_GRAPH_FILES,
        statement=(
            "One graph, in files no bead's code owns and every bead that adds, "
            "renames or moves a node writes — and it is what this plan derived "
            "every serialisation above FROM. A derivation cannot describe its "
            "own input by asking it: the node a bead is about to add is not in "
            "the graph this plan read, so two beads that each add one hold "
            "disjoint scopes here and write the same file. Stage that file by "
            "path with your own commit, reindex before you trust a plan you "
            "computed while a neighbour was editing it, and take a graph "
            "conflict as a re-plan rather than a merge."
        ),
        evidence="BDL-UX #261",
    ),
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
        name=MEDIUM_FOCUS_DOCUMENT,
        statement=(
            "One focus document per work item, written by every bead of it and "
            "owned by no bead's code. `/task-init` routes every work-item type "
            "through a document both of its flows write, so a wave shares one "
            "whatever this plan says — and this plan says nothing, because it "
            "resolves a bead to the nodes and files its CODE occupies and no "
            "node owns that document. Write only the row that names your bead, "
            "stage that file by path with your own commit, and never commit it "
            "whole: a hunk written by one bead and committed by another is "
            "correct in the tree and wrong in the history, which is a defect "
            "whose only symptom is a wrong author. Taking the landing lock does "
            "not prevent it, measured: a bead that acquired the slot in the form "
            "that grants it, and waited, still had 43 lines of its entry "
            "committed by a neighbour — the lock orders the commits and the edit "
            "had already happened."
        ),
        evidence="BDL-UX #257",
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
