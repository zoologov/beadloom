"""BDL-083 S2g (``beadloom-89gm``; BDL-UX #354, RFC D12): who holds the landing slot.

The slot is tracker state. Measured on bd 1.0.4 in an isolated ``bd init`` rig: after
``bd merge-slot acquire --holder rig-0y0`` the slot's record in ``bd export`` and in
``bd list --all --json`` reads ``status: in_progress``, ``metadata.holder: rig-0y0`` and
``labels: [gt:slot]``; after ``release --holder rig-0y0`` the holder key is gone and the
status is ``open``. The records below are those two shapes, byte for byte apart from the
timestamps, so the reader is held against what bd writes rather than against a guess.
"""

from __future__ import annotations

import json

import pytest

from beadloom.application.doc_spaces import records_from_jsonl
from beadloom.application.landing_slot import (
    SlotHold,
    pushed_refs,
    release_command,
    slot_hold,
)

_HELD = {
    "_type": "issue",
    "id": "rig-merge-slot",
    "title": "Merge Slot",
    "status": "in_progress",
    "issue_type": "task",
    "metadata": {"holder": "rig-0y0"},
    "labels": ["gt:slot"],
}
_RELEASED = {
    "_type": "issue",
    "id": "rig-merge-slot",
    "title": "Merge Slot",
    "status": "open",
    "issue_type": "task",
    "labels": ["gt:slot"],
}
_WAITERS_ONLY = {
    **_RELEASED,
    "metadata": {"waiters": ["v.zoologov", "coordinator"]},
}


def _bead(bead_id: str, status: str) -> dict[str, object]:
    return {"_type": "issue", "id": bead_id, "title": bead_id, "status": status}


def _jsonl(*records: dict[str, object]) -> str:
    return "".join(json.dumps(record, separators=(",", ":")) + "\n" for record in records)


class TestTheRecordsOfAnExport:
    def test_every_line_that_is_an_object_is_a_record(self) -> None:
        text = _jsonl(_bead("rig-1", "open"), _HELD)
        assert [r["id"] for r in records_from_jsonl(text)] == ["rig-1", "rig-merge-slot"]

    def test_a_blank_or_unreadable_line_is_skipped_and_the_rest_are_read(self) -> None:
        text = "\n{not json\n" + _jsonl(_bead("rig-1", "open")) + "[1, 2]\n"
        assert [r["id"] for r in records_from_jsonl(text)] == ["rig-1"]


class TestSlotHold:
    def test_a_held_slot_names_its_holder_and_the_holder_s_status(self) -> None:
        hold = slot_hold(records_from_jsonl(_jsonl(_bead("rig-0y0", "closed"), _HELD)))
        assert hold == SlotHold(slot="rig-merge-slot", holder="rig-0y0", holder_status="closed")
        assert hold.held
        assert hold.stale

    def test_a_hold_by_a_bead_in_progress_is_not_stale(self) -> None:
        hold = slot_hold(records_from_jsonl(_jsonl(_HELD, _bead("rig-0y0", "in_progress"))))
        assert hold.held
        assert not hold.stale

    def test_a_released_slot_has_no_holder(self) -> None:
        hold = slot_hold(records_from_jsonl(_jsonl(_bead("rig-0y0", "closed"), _RELEASED)))
        assert hold == SlotHold(slot="rig-merge-slot", holder=None, holder_status=None)
        assert not hold.held
        assert not hold.stale

    def test_waiters_are_not_a_holder(self) -> None:
        assert not slot_hold(records_from_jsonl(_jsonl(_WAITERS_ONLY))).held

    def test_a_tracker_with_no_slot_says_so_rather_than_reporting_a_free_one(self) -> None:
        hold = slot_hold(records_from_jsonl(_jsonl(_bead("rig-1", "open"))))
        assert hold.slot is None
        assert not hold.held

    def test_a_holder_that_names_no_record_has_no_status_and_is_not_called_stale(self) -> None:
        hold = slot_hold(records_from_jsonl(_jsonl(_HELD)))
        assert hold.holder == "rig-0y0"
        assert hold.holder_status is None
        assert not hold.stale

    def test_the_slot_is_found_by_its_label_and_not_by_its_id(self) -> None:
        renamed = {**_HELD, "id": "other-name"}
        assert slot_hold(records_from_jsonl(_jsonl(renamed))).slot == "other-name"
        unlabelled = {k: v for k, v in _HELD.items() if k != "labels"}
        assert slot_hold(records_from_jsonl(_jsonl(unlabelled))).slot is None


def test_the_release_names_its_holder() -> None:
    assert release_command("rig-0y0") == "bd merge-slot release --holder rig-0y0"


class TestPushedRefs:
    _ZERO = "0" * 40

    def test_each_line_git_hands_a_pre_push_hook_is_one_ref(self) -> None:
        text = f"refs/heads/f {'a' * 40} refs/heads/f {'b' * 40}\n"
        (ref,) = pushed_refs(text)
        assert ref.local_oid == "a" * 40
        assert ref.remote_oid == "b" * 40
        assert not ref.deletes
        assert not ref.creates

    def test_a_new_branch_and_a_deletion_are_told_apart(self) -> None:
        text = (
            f"refs/heads/new {'a' * 40} refs/heads/new {self._ZERO}\n"
            f"(delete) {self._ZERO} refs/heads/old {'b' * 40}\n"
        )
        new, gone = pushed_refs(text)
        assert new.creates
        assert not new.deletes
        assert gone.deletes

    def test_no_line_is_no_ref(self) -> None:
        assert pushed_refs("") == ()

    def test_a_line_git_would_not_write_is_refused_rather_than_skipped(self) -> None:
        with pytest.raises(ValueError, match="pre-push"):
            pushed_refs("refs/heads/f only-two\n")
