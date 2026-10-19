# Landing Slot (component)

Who holds the landing slot in a tracker's records, and whether a push lands an export holding
it for a bead the push carries.

**Source:** `src/beadloom/application/landing_slot.py`

---

## Overview

The landing lock is bd's merge slot, and the slot is tracker state. bd exports the tracker
into `.beads/issues.jsonl`, and every other clone reads the slot from the export the trunk
carries, so what the trunk says about the slot is what the last landed export says.

BDL-UX #354 is what that costs when a landing ends in the wrong order. The first outside
adopter's second clone followed the composed instruction of 9.0.0 — acquire before the
commit, release after — and pushed between the two. The export inside the pushed commit
still held the slot for the bead it landed, the merge request merged that commit, and the
release reached no merged commit. Every later clone imported a slot held by a closed bead,
and its `bd merge-slot acquire` was refused with `Slot held by: <bead>`. bd's refusal offers
`--wait`, a queue nothing drains, and a closed bead cannot be waited on.

So a landing runs acquire → commit → release → export → the export landed → push (RFC D12),
and this component holds the two answers that make the order checkable.

## The slot in a tracker's records

`slot_hold(records)` reads who holds the slot from tracker records. Measured on bd 1.0.4 in
an isolated `bd init` rig: after `bd merge-slot acquire --holder rig-0y0` the slot's record —
in `bd export` and in `bd list --all --json` alike — reads `status: in_progress`,
`metadata: {holder: rig-0y0}` and `labels: [gt:slot]`. After `release --holder rig-0y0` the
`holder` key is gone and the status is `open`. Closing the holder's bead changes nothing on
the slot.

- The slot record is found by its label `gt:slot`, never by its id, because the id carries
  the project's prefix.
- `SlotHold.slot` is `None` when the records hold no slot at all, which is a different fact
  from a free slot.
- `SlotHold.holder_status` is the status the same records give the holder's bead, and
  `None` when they hold no record by that id.
- `SlotHold.stale` is true for a slot held by a bead the tracker lists as `closed`, and only
  for that.

The records come from `doc_spaces.records_from_jsonl`, the one reader of an export's lines
for the working-tree file and for the export inside a commit.

## A push that lands its own hold

`check_push(project_root, pushes)` judges a push as git hands it to a pre-push hook, one
`PushedRef` per line of `<local ref> <local oid> <remote ref> <remote oid>`
(`pushed_refs(text)` reads them, and raises on a line git would not write):

- The beads a ref carries are the `Bead:` trailers of the commits it pushes, read by git
  through `doc_sync.git_baseline.commits_in`: `<remote oid>..<local oid>` when the remote
  holds the ref and this clone knows that commit, otherwise `<local oid> --not --remotes`.
  A bead id mentioned anywhere else in a message carries nothing (RFC D10).
- The export is the one at the pushed commit, `git show <local oid>:.beads/issues.jsonl`
  through `git_baseline.text_at`, never the working-tree file: bd rewrites that file after
  every command, and #354's release reached the working tree and no commit.
- The verdict is `REFUSED` when that export holds the slot for a bead the push carries. Its
  lines name the release, `bd export -o .beads/issues.jsonl`, the commit that lands the
  export by path, and the sequence.
- It is `clean` when the export holds no slot, shows it free, holds it for a bead the push
  does not carry (a neighbour's hold, which its own landing releases — the verdict names
  the holder), or when the pushed commit carries no export. A deletion lands no commit.
- It is `NOT CHECKED` when git does not know the pushed commit or cannot list what it
  carries. A push nobody could judge is not reported as a clean one.

## Where it surfaces

- `beadloom landing-check` prints the verdict, led by `Landing lock: `, and exits 0, 1 or 2
  (clean, refused, not checked). `--stdin` reads git's pre-push input; without it `HEAD` is
  judged as a branch no remote holds yet.
- The pre-push hook `install-hooks` writes runs `beadloom landing-check --stdin` before the
  Gate. A refusal prints the verdict's lines and exits 1; a run with no verdict line, or one
  that could not judge the push, prints `NOT CHECKED` and the Gate runs as before.
- `beadloom waves` reads the slot from the same `bd list --all --json` answer its census
  reads. A slot held by a closed bead fails the `landing-order` medium, and the detail names
  the one remedy, `bd merge-slot release --holder <closed-bead>`.
- The composed landing fragment of every role, the coordinator's checklist and the core's
  merge-slot line state the sequence.

The scenarios are in
`tests/acceptance/services/cli-commands/the_release_lands_before_the_push.feature` and
`tests/acceptance/application/wave-plan/landing_lock.feature`.

## What it does not judge

- A slot held by a holder that names no bead in the records — an actor name, a bead of
  another tracker. Its status is unknown, so it is not called stale.
- A neighbour who acquires between a release and its export. That hold appears in the
  export as the neighbour's, and the neighbour's own landing exports its release.
- A push made with `--no-verify`, or from a clone without the hook installed.

## Related

- `wave-plan` — the `landing-order` medium that names the stale holder's release.
- `cli-commands` — `landing-check` and the pre-push hook text.
- `sync-check` — `git_baseline`, the one reader of git the commits and the export are read
  through.
- `doc-spaces` — `records_from_jsonl`, the one reader of an export's lines.
- `gate-ownership` — `BEAD_TRAILER`, the trailer that binds a commit to a bead.
