# beadloom:domain=application
# beadloom:component=gate-ownership
"""Who owns what a gate run found: the bead whose commits changed the finding's files.

**The defect this closes, twice.** BDL-068 S6 added the report because a red that
nobody owns trains its reader to discount the next one: every gate owner of two
waves had to be told by the coordinator, by hand, that the red on the branch was
not theirs. The report it added attributed a finding to every claimed bead whose
``refs:`` declared the node that covers the finding's path — and the first outside
adopter measured what that says (BDL-UX #329): in a wave of two beads each was told
it owned the same nine findings, all of them the first bead's work, and a second
work item's bead was told it owned 36 findings on files it never touched, because
its ``refs:`` named the node that covers the frontend's source whole. A node that
covers a directory says what a bead may touch, never what it touched.

**So ownership is read from the commits (RFC D3).** A finding is owned by a bead
claimed now whose commits on the branch changed a file the finding is about. The
commits are the ones ``HEAD`` holds against the base the scope check compares
against, so a commit already on the trunk is nobody's work in flight.

**A commit is a bead's by its trailer, and by nothing else (RFC D10).** It belongs to
a bead when its message carries the git trailer ``Bead: <bead-id>``, read as git
reads trailers: the message's final paragraph only, the key in any case. Until the
owner's ruling of 2026-10-19 any mention of the id bound the commit, and on
BDL-083's own branch at 996781dd that bound 17 (bead, commit) pairs where 4 were declared: a
landing-lock note ("released from beadloom-7pd6") and a test bead naming what it
measured each made their files another bead's. A commit with no trailer is
nobody's, which is the honest reading of a branch written before the rule.

**The files a finding is about.** The files its locations name, with a document
named in the documentation root's frame re-rooted onto the project's; a stale or
missing pair locates its code file as well as its document. A finding that locates
no file and names a node is about the files that node owns — by most-specific
ownership, so a node never answers for a nested node's files. The bead's ``refs:``
do not attribute anything: the declaration grammar reads node ids and no file
path, and a node is the directory-sized claim the defect was made of.

**Two verdicts, and the reason is on every one.** ``owned`` names the beads.
``unattributed`` says no claimed bead's commits changed the files the finding is
about, or that the finding is about no file at all — the honest answer, and never
"owned by the neighbour whose node covers the directory". A tracker that cannot
answer, a project with no index and a git that cannot list the branch's commits
are a :attr:`GateOwnership.reason` on the whole report rather than a page of
``unattributed``: telling every gate owner "not yours" when nobody was asked would
be the false green this epic exists to remove.

It is not a step: it has no status, and the exit code is the one the steps produced.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from beadloom.doc_sync.git_baseline import changed_paths, commits_since
from beadloom.infrastructure.db import open_db_readonly
from beadloom.infrastructure.doc_roots import resolve_docs_dir
from beadloom.infrastructure.repository import get_owned_code_files

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Sequence
    from pathlib import Path

    from beadloom.application.guards.contract import ClaimedBead, WorkTracker
    from beadloom.doc_sync.git_baseline import BranchCommit

#: A finding in the gate's shared shape. Spelled here rather than imported from
#: :mod:`beadloom.application.gate`, which imports this module.
Finding = dict[str, object]

#: A claimed bead's commits changed a file the finding is about.
OWNED = "owned"

#: No claimed bead's commits changed a file the finding is about, or it is about none.
UNATTRIBUTED = "unattributed"

#: The git trailer that binds a commit to a bead (RFC D10): ``Bead: <bead-id>``.
BEAD_TRAILER = "Bead"

#: The rule every surface prints beside the owners, so a reader can tell what an
#: attribution is a claim about.
ATTRIBUTION_RULE = f"by the files the commits carrying `{BEAD_TRAILER}: <id>` changed"

#: The clause beside each owner, RFC D3's wording.
OWNED_CLAUSE = "by the files its commits changed"

#: The tracker did not answer, so no claim was read at all.
NO_TRACKER = (
    "the work tracker could not be reached, so no finding of this run was held against a claim"
)

#: There is no index, so no finding could be resolved to the files it is about.
NO_INDEX = (
    "the project has no index, so no finding could be resolved to the files it is "
    "about — run `beadloom reindex`"
)

#: Git could not list the branch's commits; formatted with the base it was asked about.
NO_HISTORY = (
    "git could not list the commits this branch holds against {base}, so no finding "
    "could be held against a bead's commits"
)

#: Why a finding that locates no file and names no node cannot be attributed.
_NO_FILE = "it locates no file and names no node"

#: How many beads a line spells out before it counts the rest.
_NAMED_LIMIT = 5


@dataclass(frozen=True)
class FindingOwner:
    """One finding, the beads whose commits changed its files, and why."""

    rule: str
    verdict: str
    node: str | None = None
    beads: tuple[str, ...] = ()
    where: str = ""
    """The file that decided the verdict, or why no file could."""

    files: tuple[str, ...] = ()
    """The project-relative files the finding was held against; empty when it is about none."""

    uncommitted: bool = False
    """Unattributed, and the working tree changes a file it is about that no commit holds."""


@dataclass(frozen=True)
class BeadCommits:
    """A claimed bead, how many commits on the branch carry it, and the paths they changed."""

    bead_id: str
    commits: int
    paths: frozenset[str]


@dataclass(frozen=True)
class GateOwnership:
    """What a gate run found, held against the commits of the beads claimed while it ran."""

    owners: tuple[FindingOwner, ...] = ()
    """One entry per finding, in the run's finding order."""

    claimed: tuple[str, ...] = ()
    """The bead ids the tracker reported claimed, in sorted order."""

    claims: tuple[BeadCommits, ...] = ()
    """Each claimed bead's commits on the branch, in sorted bead order."""

    base: str | None = None
    """The ref the branch's commits were listed against."""

    reason: str | None = None
    """Present exactly when nothing was attributed, and never with owners."""

    @property
    def owned(self) -> tuple[FindingOwner, ...]:
        """Findings a claimed bead's commits explain."""
        return tuple(o for o in self.owners if o.verdict == OWNED)

    @property
    def unattributed(self) -> tuple[FindingOwner, ...]:
        """Findings no claimed bead's commits explain."""
        return tuple(o for o in self.owners if o.verdict == UNATTRIBUTED)

    @property
    def none_owned(self) -> bool:
        """True when findings were attributed and not one of them is owned.

        False when there was nothing to attribute or nobody was asked, because
        neither of those is the sentence "none of this red is a running bead's".
        """
        return bool(self.owners) and not self.owned

    def by_bead(self) -> tuple[tuple[str, int], ...]:
        """Each owning bead and how many findings it owns, most first."""
        counts: dict[str, int] = {}
        for owner in self.owned:
            for bead in owner.beads:
                counts[bead] = counts.get(bead, 0) + 1
        return tuple(sorted(counts.items(), key=lambda item: (-item[1], item[0])))

    def owning_nothing(self) -> tuple[BeadCommits, ...]:
        """The claimed beads that own no finding of this run."""
        owning = {bead for bead, _count in self.by_bead()}
        return tuple(claim for claim in self.claims if claim.bead_id not in owning)


def derive_gate_ownership(
    project_root: Path,
    *,
    findings: Sequence[Finding],
    tracker: WorkTracker,
    base: str | None = None,
) -> GateOwnership:
    """Attribute every finding of a run to the claimed beads whose commits explain it.

    *base* is the ref the branch's commits are listed against; ``None`` takes the
    one the scope check compares against (``scope_base``), so the older commits
    of a parent branch not yet merged are nobody's work in flight. The tracker is
    asked only when there is something to attribute: a report that shells out to
    ``bd`` on every push to say nothing is a cost with no reader.
    """
    if not findings:
        return GateOwnership()
    beads = tracker.claimed_beads()
    if beads is None:
        return GateOwnership(reason=NO_TRACKER)
    claimed = tuple(sorted(bead.id for bead in beads))
    if base is None:
        from beadloom.application.scope_base import scope_base

        base = scope_base(project_root).ref
    database = project_root / ".beadloom" / "beadloom.db"
    try:
        connection = open_db_readonly(database)
    except FileNotFoundError:
        return GateOwnership(claimed=claimed, base=base, reason=NO_INDEX)
    try:
        commits = commits_since(project_root, base, trailer=BEAD_TRAILER)
        if commits is None:
            return GateOwnership(claimed=claimed, base=base, reason=NO_HISTORY.format(base=base))
        claims = tuple(_commits_of(bead, commits) for bead in sorted(beads, key=_id))
        files = _FindingFiles(project_root, connection)
        tree = changed_paths(project_root) or frozenset()
        owners = tuple(_owner_of(f, files=files, claims=claims, tree=tree) for f in findings)
    finally:
        connection.close()
    return GateOwnership(owners=owners, claimed=claimed, claims=claims, base=base)


def _id(bead: ClaimedBead) -> str:
    return bead.id


def _commits_of(bead: ClaimedBead, commits: Sequence[BranchCommit]) -> BeadCommits:
    """The commits whose ``Bead:`` trailer names *bead*, and the paths they changed."""
    own = [commit for commit in commits if bead.id in commit.trailer_values]
    paths = frozenset(path for commit in own for path in commit.paths)
    return BeadCommits(bead_id=bead.id, commits=len(own), paths=paths)


class _FindingFiles:
    """The project-relative files a finding is about, read once per run from the index."""

    def __init__(self, project_root: Path, connection: sqlite3.Connection) -> None:
        self._connection = connection
        self._prefix = resolve_docs_dir(project_root).strip("/")
        rows = connection.execute(
            "SELECT path, ref_id FROM docs WHERE ref_id IS NOT NULL"
        ).fetchall()
        self._docs: dict[str, str] = {str(row["path"]): str(row["ref_id"]) for row in rows}
        self._node_files: dict[str, tuple[str, ...]] = {}

    def located(self, finding: Finding) -> tuple[str, ...]:
        """Every file the finding's locations name, in the project's frame."""
        locations = finding.get("locations")
        if not isinstance(locations, list):
            return ()
        files: list[str] = []
        for location in locations:
            file = location.get("file") if isinstance(location, dict) else None
            if isinstance(file, str) and file:
                path = self._project_path(file)
                if path not in files:
                    files.append(path)
        return tuple(files)

    def of_node(self, ref_id: str) -> tuple[str, ...]:
        """The code files *ref_id* owns and the documents declared for it."""
        if ref_id not in self._node_files:
            code = [path for path, _hash in get_owned_code_files(self._connection, ref_id)]
            docs = [self._docs_path(doc) for doc, ref in self._docs.items() if ref == ref_id]
            self._node_files[ref_id] = tuple(code + sorted(docs))
        return self._node_files[ref_id]

    def _project_path(self, file: str) -> str:
        """*file* re-rooted when it is a document named in the documentation root's frame.

        The sync steps locate a document as the ``docs`` table stores it, relative
        to the documentation root, while a commit names it relative to the project.
        """
        return self._docs_path(file) if file in self._docs else file

    def _docs_path(self, doc: str) -> str:
        return f"{self._prefix}/{doc}" if self._prefix else doc


def _owner_of(
    finding: Finding,
    *,
    files: _FindingFiles,
    claims: Sequence[BeadCommits],
    tree: frozenset[str],
) -> FindingOwner:
    """One finding, held against the paths each claimed bead's commits changed."""
    rule = str(finding.get("rule", ""))
    named = finding.get("node")
    node = named if isinstance(named, str) and named else None
    about = files.located(finding)
    subject = "the files it locates"
    if not about and node is not None:
        about = files.of_node(node)
        subject = f"the files {node} owns"
    if not about:
        why = _NO_FILE if node is None else f"{node} names no file a commit could have changed"
        return FindingOwner(rule=rule, verdict=UNATTRIBUTED, node=node, where=why)
    beads: list[str] = []
    decided = ""
    for claim in claims:
        touched = [path for path in about if path in claim.paths]
        if touched:
            beads.append(claim.bead_id)
            decided = decided or f"{touched[0]}, changed by its commits"
    if beads:
        return FindingOwner(
            rule=rule,
            verdict=OWNED,
            node=node,
            beads=tuple(beads),
            where=decided,
            files=about,
        )
    return FindingOwner(
        rule=rule,
        verdict=UNATTRIBUTED,
        node=node,
        where=f"no claimed bead's commits changed {subject}",
        files=about,
        uncommitted=any(path in tree for path in about),
    )


def ownership_sentences(ownership: GateOwnership) -> list[str]:
    """The ownership block's sentences, once, for every surface that prints it.

    Beside the model rather than in a renderer, for the reason
    :func:`beadloom.application.gate_coverage.gate_coverage_lines` is: three formats
    and one MCP tool quote it, and a second wording is how two surfaces of one run
    come to disagree.
    """
    if ownership.reason is not None:
        return [ownership.reason]
    if not ownership.owners:
        return []
    sentences = [f"attributed {ATTRIBUTION_RULE}, over {ownership.base}..HEAD"]
    sentences.extend(
        f"owned by {bead}: {count} finding(s), {OWNED_CLAUSE}"
        for bead, count in ownership.by_bead()
    )
    sentences.extend(_owning_nothing(claim, ownership) for claim in ownership.owning_nothing())
    if ownership.unattributed:
        sentences.append(_unattributed_sentence(ownership.unattributed, ownership))
    if ownership.none_owned:
        sentences.append(
            f"no finding of this run is owned by a bead claimed now ({_claimed_clause(ownership)})"
        )
    return sentences


def gate_ownership_lines(ownership: GateOwnership) -> list[str]:
    """The human report's block: who owns what this run found, and by which rule."""
    sentences = ownership_sentences(ownership)
    if not sentences:
        return []
    return ["Findings by owner:", *(f"  {sentence}" for sentence in sentences)]


def ownership_payload(ownership: GateOwnership) -> dict[str, object]:
    """The block as structured data, for the JSON report and the MCP tool alike."""
    return {
        "reason": ownership.reason,
        "rule": ATTRIBUTION_RULE,
        "base": ownership.base,
        "claimed": list(ownership.claimed),
        "none_owned": ownership.none_owned,
        "claims": [
            {"bead": claim.bead_id, "commits": claim.commits} for claim in ownership.claims
        ],
        "findings": [
            {
                "rule": owner.rule,
                "verdict": owner.verdict,
                "node": owner.node,
                "beads": list(owner.beads),
                "where": owner.where,
                "files": list(owner.files),
                "uncommitted": owner.uncommitted,
            }
            for owner in ownership.owners
        ],
    }


def _owning_nothing(claim: BeadCommits, ownership: GateOwnership) -> str:
    """Why a claimed bead owns nothing: no commit carries it, or its commits explain none."""
    if claim.commits == 0:
        return (
            f"{claim.bead_id} owns no finding: no commit on {ownership.base}..HEAD carries "
            f"`{BEAD_TRAILER}: {claim.bead_id}`"
        )
    return (
        f"{claim.bead_id} owns no finding: its {claim.commits} commit(s) changed none "
        "of the files these findings are about"
    )


def _unattributed_sentence(unattributed: Sequence[FindingOwner], ownership: GateOwnership) -> str:
    """The unattributed count, with the two qualifications a reader acts on."""
    uncommitted = sum(1 for owner in unattributed if owner.uncommitted)
    fileless = sum(1 for owner in unattributed if not owner.files)
    clauses = []
    if uncommitted:
        clauses.append(f"{uncommitted} on files the working tree changes and no commit holds yet")
    if fileless:
        clauses.append(f"{fileless} about no file a commit could have changed")
    qualified = f" ({'; '.join(clauses)})" if clauses else ""
    return (
        f"{UNATTRIBUTED}: {len(unattributed)} finding(s) no claimed bead's commits on "
        f"{ownership.base}..HEAD explain{qualified}"
    )


def _claimed_clause(ownership: GateOwnership) -> str:
    """Which claims the report was actually held against."""
    if not ownership.claimed:
        return "no bead is claimed"
    named = ", ".join(ownership.claimed[:_NAMED_LIMIT])
    if len(ownership.claimed) > _NAMED_LIMIT:
        named += f" and {len(ownership.claimed) - _NAMED_LIMIT} more"
    return f"claimed: {named}"
