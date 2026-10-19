# beadloom:domain=application
# beadloom:component=landing-slot
"""Who holds the landing slot in a tracker's records, and whether a push lands its own hold.

**The measurement this module reads by**, taken on bd 1.0.4 in an isolated ``bd init`` rig
on 2026-10-19 (BDL-083 S2g, ``beadloom-89gm``). After ``bd merge-slot acquire --holder
rig-0y0`` the slot's record — in ``bd export`` and in ``bd list --all --json`` alike —
reads ``status: in_progress``, ``metadata: {holder: rig-0y0}`` and ``labels: [gt:slot]``.
After ``bd merge-slot release --holder rig-0y0`` the ``holder`` key is gone and the status
is ``open``. Closing the holder's bead changes nothing on the slot: bd keeps a closed
bead's hold, and refuses the next ``acquire`` naming it.

**Why that matters (BDL-UX #354, RFC D12).** The slot is tracker state, and the tracker
travels between clones as the export ``.beads/issues.jsonl``. What the trunk says about
the slot is therefore whatever the last landed export says. The first outside adopter's
second clone followed the composed instruction — acquire before the commit, release
after — and pushed between the two: the release reached no merged commit, and every
later clone imported a slot held by a closed bead. bd's own refusal offers ``--wait``, a
queue nothing drains, and a closed bead cannot be waited on.

**Two readers of one answer.** :func:`slot_hold` reads who holds the slot from tracker
records, in the one shape both bd answers share. ``beadloom waves`` reads it from
``bd list --all`` to name the release a stale hold needs before a wave starts.
:func:`check_push` reads it from the export inside the commit being pushed, beside the
``Bead:`` trailers of the commits the push carries, so the pre-push hook can refuse a
push that would land its own bead's hold.

What this module deliberately does not judge: a hold by a bead the push does not carry.
That hold is a neighbour's, and its own landing exports its release; the verdict names
it and passes.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from beadloom.application.doc_spaces import TRACKER_EXPORT, records_from_jsonl
from beadloom.application.gate_ownership import BEAD_TRAILER
from beadloom.doc_sync.git_baseline import commits_in, ref_exists, short_commit, text_at

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence
    from pathlib import Path

__all__ = [
    "LANDING_SEQUENCE",
    "SLOT_LABEL",
    "STATUS_CLOSED",
    "VERDICT_CLEAN",
    "VERDICT_LEAD",
    "VERDICT_NOT_CHECKED",
    "VERDICT_REFUSED",
    "LandingVerdict",
    "PushedRef",
    "SlotHold",
    "check_push",
    "judge_landing",
    "pushed_refs",
    "release_command",
    "slot_hold",
]

#: The label bd 1.0.4 gives the slot's record. The record is found by it rather than by
#: its id, because the id carries the project's prefix (``beadloom-merge-slot``).
SLOT_LABEL = "gt:slot"

#: The key of the slot record's ``metadata`` that names its holder while it is held.
_HOLDER_KEY = "holder"

#: The tracker status of a bead that has been closed — a holder nobody can wait on.
STATUS_CLOSED = "closed"

#: The order a landing takes, spelled once: the composed landing fragments state it, the
#: hook's refusal names it, and the tests read it off both.
LANDING_SEQUENCE = "acquire -> commit -> release -> export -> the export landed -> push"

#: The lead of the verdict line ``beadloom landing-check`` prints first, which the
#: pre-push hook greps for. A run that printed no such line is a check that did not run.
VERDICT_LEAD = "Landing lock: "
VERDICT_REFUSED = "REFUSED"
VERDICT_CLEAN = "clean"
VERDICT_NOT_CHECKED = "NOT CHECKED"

#: An object id of zeros: git's way of saying a side of a pushed ref does not exist.
_NO_OBJECT = re.compile(r"0+")

#: The fields of one line git writes to a pre-push hook.
_PUSH_LINE_FIELDS = 4


@dataclass(frozen=True)
class SlotHold:
    """The landing slot a tracker's records hold, and who holds it.

    ``slot`` is the slot record's id, ``None`` when the records hold no slot at all —
    a different fact from a free slot. ``holder`` is ``None`` when the slot is free.
    ``holder_status`` is the status the same records give the holder's bead, ``None``
    when they hold no record by that id (a holder that names no bead).
    """

    slot: str | None
    holder: str | None
    holder_status: str | None

    @property
    def held(self) -> bool:
        """Whether somebody holds the slot."""
        return self.holder is not None

    @property
    def stale(self) -> bool:
        """Whether the slot is held by a bead the tracker lists as closed."""
        return self.held and self.holder_status == STATUS_CLOSED


def slot_hold(records: Iterable[Mapping[str, object]]) -> SlotHold:
    """Who holds the landing slot in *records* — an export's rows or ``bd list``'s."""
    rows = tuple(records)
    slot = next((row for row in rows if _is_slot(row)), None)
    if slot is None:
        return SlotHold(slot=None, holder=None, holder_status=None)
    holder = _holder_of(slot)
    status = next(
        (str(row.get("status")) for row in rows if holder and row.get("id") == holder),
        None,
    )
    return SlotHold(slot=str(slot.get("id")), holder=holder, holder_status=status)


def _is_slot(row: Mapping[str, object]) -> bool:
    labels = row.get("labels")
    return isinstance(labels, list) and SLOT_LABEL in labels


def _holder_of(slot: Mapping[str, object]) -> str | None:
    """The holder the slot record's ``metadata`` names, when it names one."""
    metadata = slot.get("metadata")
    if isinstance(metadata, str):
        # bd keeps metadata as a JSON column; an answer that hands it over as text
        # still names the same holder.
        try:
            metadata = json.loads(metadata)
        except json.JSONDecodeError:
            return None
    if not isinstance(metadata, dict):
        return None
    holder = metadata.get(_HOLDER_KEY)
    return holder if isinstance(holder, str) and holder else None


def release_command(holder: str) -> str:
    """The one release that frees *holder*'s hold — the only release form bd verifies."""
    return f"bd merge-slot release --holder {holder}"


@dataclass(frozen=True)
class PushedRef:
    """One ref of a push, as git hands it to a pre-push hook."""

    local_ref: str
    local_oid: str
    remote_ref: str
    remote_oid: str

    @property
    def deletes(self) -> bool:
        """Whether the push deletes the remote ref — it then lands no commit."""
        return _NO_OBJECT.fullmatch(self.local_oid) is not None

    @property
    def creates(self) -> bool:
        """Whether the remote holds no such ref yet."""
        return _NO_OBJECT.fullmatch(self.remote_oid) is not None


def pushed_refs(text: str) -> tuple[PushedRef, ...]:
    """The refs a pre-push hook's input names, one per line.

    Raises :class:`ValueError` on a line git would not write: a push whose refs cannot
    be read is a push nobody judged, and skipping the line would judge a smaller one.
    """
    refs: list[PushedRef] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        fields = line.split()
        if len(fields) != _PUSH_LINE_FIELDS:
            msg = f"not a pre-push input line (four fields expected): {line!r}"
            raise ValueError(msg)
        refs.append(PushedRef(*fields))
    return tuple(refs)


@dataclass(frozen=True)
class LandingVerdict:
    """What the landing check says about a push: its status and the lines it prints."""

    status: str
    lines: tuple[str, ...]


def _verdict(status: str, reason: str, *more: str) -> LandingVerdict:
    return LandingVerdict(status, (f"{VERDICT_LEAD}{status} -- {reason}", *more))


def judge_landing(hold: SlotHold, carried: frozenset[str], *, at: str) -> LandingVerdict:
    """Whether a push carrying the beads *carried* lands *hold*, the export's slot at *at*."""
    if hold.slot is None:
        return _verdict(VERDICT_CLEAN, f"the export at {at} holds no merge slot")
    if hold.holder is None:
        return _verdict(VERDICT_CLEAN, f"the export at {at} shows the merge slot free")
    if hold.holder not in carried:
        named = ", ".join(sorted(carried)) or "no bead"
        return _verdict(
            VERDICT_CLEAN,
            f"the export at {at} holds the merge slot for {hold.holder}, a bead this push "
            f"does not carry (it carries {named}); that hold is released by its own landing",
        )
    return _verdict(
        VERDICT_REFUSED,
        f"the export this push lands ({TRACKER_EXPORT} at {at}) holds the merge slot for "
        f"{hold.holder}, a bead this push carries.",
        f"Pushed as it is, the trunk exports the slot as held once {hold.holder} has "
        "landed, and the next clone's `bd merge-slot acquire` is refused naming a bead "
        "nobody can wait on (BDL-UX #354).",
        f"The landing sequence is {LANDING_SEQUENCE}:",
        f"  {release_command(hold.holder)}",
        f"  bd export -o {TRACKER_EXPORT}",
        f'  git commit -m "<subject>" -m "{BEAD_TRAILER}: {hold.holder}" -- {TRACKER_EXPORT}',
        "  git push",
    )


def check_push(project_root: Path, pushes: Sequence[PushedRef]) -> LandingVerdict:
    """Whether any ref of *pushes* lands an export that holds the slot for a bead it carries.

    The first refusal is the verdict, then the first ref git could not answer for; a push
    whose every ref is clean is clean, with each ref's reason beside the lead line.
    """
    landing = [ref for ref in pushes if not ref.deletes]
    if not landing:
        return _verdict(VERDICT_CLEAN, "this push lands no commit, so no export travels with it")
    verdicts = [_check_ref(project_root, ref) for ref in landing]
    for status in (VERDICT_REFUSED, VERDICT_NOT_CHECKED):
        found = next((v for v in verdicts if v.status == status), None)
        if found is not None:
            return found
    if len(verdicts) == 1:
        return verdicts[0]
    return _verdict(
        VERDICT_CLEAN,
        f"none of the {len(verdicts)} refs this push lands carries its own hold",
        *(f"  {v.lines[0].removeprefix(VERDICT_LEAD)}" for v in verdicts),
    )


def _check_ref(project_root: Path, ref: PushedRef) -> LandingVerdict:
    """The verdict for one pushed ref: the export at its tip against the beads it carries."""
    tip = ref.local_oid
    if not ref_exists(project_root, f"{tip}^{{commit}}"):
        return _verdict(VERDICT_NOT_CHECKED, f"git does not know the pushed commit {tip}")
    commits = commits_in(project_root, _carried_range(project_root, ref), trailer=BEAD_TRAILER)
    if commits is None:
        return _verdict(
            VERDICT_NOT_CHECKED, f"git could not list the commits {ref.local_ref} carries"
        )
    at = short_commit(project_root, tip) or tip
    export = text_at(project_root, tip, TRACKER_EXPORT)
    if export is None:
        return _verdict(
            VERDICT_CLEAN,
            f"the pushed commit {at} carries no {TRACKER_EXPORT}, so no slot travels with it",
        )
    carried = frozenset(value for commit in commits for value in commit.trailer_values)
    return judge_landing(slot_hold(records_from_jsonl(export)), carried, at=at)


def _carried_range(project_root: Path, ref: PushedRef) -> tuple[str, ...]:
    """The revisions a push of *ref* carries, said the way ``git log`` takes them.

    The remote's old tip when the remote holds the ref and this clone knows that commit;
    otherwise every commit no remote-tracking ref holds, which is what a new branch lands.
    """
    if not ref.creates and ref_exists(project_root, f"{ref.remote_oid}^{{commit}}"):
        return (f"{ref.remote_oid}..{ref.local_oid}",)
    return (ref.local_oid, "--not", "--remotes")
