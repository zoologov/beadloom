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
`.beadloom/` that git does not track are the `.db` family and the firing record, matched by
the glob `.beadloom/guard-firings*.jsonl` so the generation it rotates into is covered beside
the active file. Everything else there — the graph under `_graph/`, `flow.yml`, `config.yml`,
the flow
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
- `undeclared_patterns(text)` / `ignore_block_findings(project_root)` — the generated
  patterns a file does not declare, each an `IgnoreFinding` carrying the `IgnoreEntry` itself
  plus the declared lines the pattern `supersedes`. `ensure_ignore_block` writes what the
  first of these returns, so the writer and the check cannot disagree about what is missing.

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

**The same cost falls on the `why` text, and there it is not cosmetic.** An entry's reason is
prose an adopter reads before deciding, so a project holding a block written before
`beadloom-0mdo.43` still carries the older invitation — the one that offered the audit trail
without naming its contents — over a `guard-firings.1.jsonl` that may still hold command lines
written before the reduction. Nothing here reaches either: this component does not rewrite a
block it finds, and `firing.py` does not rewrite a record already written. Since
`beadloom-0mdo.40` the PATTERN half of that cost is reported — see *Reported, never
rewritten* below — and the `why` half is not: the check compares patterns, so a stale reason
is still invisible.

Both writers report what they did (`✓ Ignored: N generated path(s) …` from `init`,
`Wrote .gitignore (…)` from `setup-agentic-flow`). Editing someone's `.gitignore`
silently would be its own surprise.

## Reported, never rewritten

`undeclared_patterns(text)` returns every pattern in `GENERATED_WORKING_SET` that a
`.gitignore`'s text does not declare, and `ignore_block_findings(project_root)` applies it to
a project. `config-check` turns each finding into a `warn` drift against `.gitignore`.

**The drift it exists for was this repository's own, and nobody found it.** Until
`beadloom-0mdo.39` this `.gitignore` carried the exact filename `.beadloom/guard-firings.jsonl`
while this module had emitted the glob `.beadloom/guard-firings*.jsonl` since rotation shipped.
The gap was invisible because the second file did not exist: widening the guard matcher to
`Bash` tripled the firings, the record rotated for the first time in this repository's history,
and `guard-firings.1.jsonl` appeared as untracked churn. An adopter is worse off than this
repository was, because the upgrade path writes no ignore block at all.

**What is compared is the patterns, not the block's bytes.** The reason comments are prose in a
file people edit, and a project that ignores the same paths under a heading it wrote itself is
correct — this repository is that project, and has no generated block at all. Comparing text
would report every such project on every run, which is how a check gets switched off wholesale.

**A finding names the line it supersedes** when the file declares something the current pattern
glob-matches, so the remediation reads "replace `.beadloom/guard-firings.jsonl` with
`.beadloom/guard-firings*.jsonl`" rather than "add a line". The relation is computed with
`fnmatchcase` against the emitted pattern, not looked up in a table of known renames — a table
is the second list this check exists to avoid.

**`warn`, and never `fixable`.** Warn because the file is the adopter's and the pattern set is
Beadloom's: a release that adds a pattern would otherwise turn every adopter's green project
red on upgrade. Not fixable because this module's published contract is that the block is
written once and never rewritten, there is no manifest that could prove a line is Beadloom's,
and the repair is a human's line in a human's file. That reason is this component's own and
settles nothing for the composed role adapters, whose ownership question is decided elsewhere.

**The two states it declines to judge** are the two `ensure_ignore_block` declines to write in:
a project outside a git working tree, and a project where Beadloom has generated nothing under
`.beadloom/` for an ignore file to name.

## Why the firing record is ignored by default

It is evidence about what the flow did, and a team could reasonably want it committed.
It is ignored anyway because it is **machine-local and append-only**: committing it makes
every guarded edit a working-tree change, and every branch a conflict on the same last
line. The reason is written into the block itself, not only here — the adopter meets the
line in their own file, not in our docs.

**The invitation names what the file holds**, since `beadloom-0mdo.43`. "A team that wants
the audit trail deletes this line, once" was written when the record held file paths;
binding the shell tool (BDL-UX #170) made it hold command lines as well, and following the
sentence unchanged would have committed an agent's shell history to git. Two things moved:
the record now carries a shell edit's program and derived write targets rather than its
command line (`application/guards/hook_payload.py`), and this entry's `why` states that,
so an adopter deciding to commit the file is deciding about the contents it actually has.

**What ignoring settles, and what settles the rest:** keeping a file out of git says nothing
about its size. Since `beadloom-mr2l.56` the size is bounded in the guard domain rather than
here — the record rolls over at 2000 firings — and this block's pattern is
`.beadloom/guard-firings*.jsonl` so the rotated generation is ignored beside the active one
rather than surfacing as untracked churn.

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
