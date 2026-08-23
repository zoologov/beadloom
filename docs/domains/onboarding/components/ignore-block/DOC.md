# Ignore Block (component)

Internal building block of the onboarding domain.

**Source:** `src/beadloom/onboarding/ignore_block.py`

---

## Overview

Names the derived state Beadloom writes into a project's `.beadloom/`, and appends it
once to that project's `.gitignore`. Before BDL-061.35 Beadloom wrote an ignore entry
**nowhere** — measured by grepping the whole of `src/` — so an adopter collected
untracked churn from the first `beadloom reindex` (the SQLite index) and again from the
first guarded edit (the guard firing record). Only this repository was clean, because
its `.gitignore` had been hand-edited.

The ignored set is measured rather than assumed: on this repository the only paths under
`.beadloom/` that git does not track are the `.db` family and `guard-firings.jsonl`.
Everything else there — the graph under `_graph/`, `flow.yml`, `config.yml`, the flow
overlay — is source and must stay committable, so the block never covers `.beadloom/`
wholesale.

## Public surface

- `ensure_ignore_block(project_root)` — append the block if it is not already there;
  returns an `IgnoreBlockResult` carrying `added` (the patterns written) and
  `skipped_reason` (why nothing was, when nothing was).
- `GENERATED_WORKING_SET` — the `IgnoreEntry(pattern, why)` list. A pattern without a
  reason is not representable in the tests that pin this: a bare pattern in someone
  else's ignore file is indistinguishable from a mistake.
- `BLOCK_MARKER`, `IGNORE_RELPATH` — the block's identity and location.

## Where the entry belongs, and why not in the guard scaffolder

The entry is a property of the directory Beadloom creates, not of any one feature, so
`bootstrap_project` writes it — the function that creates the working set — and
`beadloom setup-agentic-flow` repeats the identical whole-set call for a project
initialised by an older Beadloom.

Putting it in `scaffold_guard_hooks` instead would have made the flow guards a special
case while leaving the larger churn — the index — unignored, and it would have required
*editing* a block written earlier every time a feature was enabled. Writing the whole set
once, at the moment the set is created, is what lets nothing afterwards manage the file.

## Written once, never rewritten — which is what makes the override real

A run that finds `BLOCK_MARKER` does nothing at all. `.gitignore` is the project's file
and is edited constantly; the composed flow artifacts carry a manifest and a drift-guard
precisely because Beadloom owns them, and this file it does not own.

So the block is a **default**, and the override is to edit it: delete a line and it does
not come back. A configuration key would be the opposite trade — it would force the block
to become managed, so that flipping the key rewrote somebody's ignore file, which is the
behaviour being avoided. The cost of the choice is stated rather than hidden: a pattern
added by a later Beadloom release will not reach a project that already has the block,
which is why the block covers the whole working set from the first write.

Both writers report what they did (`✓ Ignored: N generated path(s) …` from `init`,
`Wrote .gitignore (…)` from `setup-agentic-flow`). Editing someone's `.gitignore`
silently would be its own surprise.

## Why the firing record is ignored by default

It is evidence about what the flow did, and a team could reasonably want it committed.
It is ignored anyway because it is **machine-local and append-only**: committing it makes
every guarded edit a working-tree change, and every branch a conflict on the same last
line. The reason is written into the block itself, not only here — the adopter meets the
line in their own file, not in our docs.

**What ignoring does not fix, stated in the block:** the record is not rotated and
`beadloom guard --liveness` parses it whole (review minor m7, filed as `beadloom-mr2l.56`). Ignoring it
keeps the growth out of git, not off the disk.

## Invariants

- **Never inside a block it did not write.** The marker means hands off.
- **Never a duplicate.** A pattern the project already declares is skipped, so a
  hand-edited `.gitignore` (this repository's, for one) gains only what it lacks.
- **Never a file for a VCS the project does not use.** With no enclosing git working tree
  nothing is written, and the reason is returned. The search walks upward, because a
  project root is often a package inside a repository.
- **Never a rewrite of the project's own lines.** The block is appended; the preceding
  bytes are untouched.

## Collaborators

Called by `bootstrap_project` (`onboarding/scanner/bootstrap.py`, whose result carries
`ignore_added`) and by `beadloom setup-agentic-flow` (`services/commands/setup.py`). The
firing record it names is written by `application/guards/firing.py`.
