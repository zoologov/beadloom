# Config Declarations (component)

Internal building block of the doc-sync domain.

**Source:** `src/beadloom/doc_sync/declarations.py`

---

## Overview

What a project declared under one `.beadloom/config.yml` key, and what about that declaration was
unusable. One module, because two Gate legs were answering the question separately and both
reached the same wrong answer.

Two legs are opt-in: `issue-log` reads `issue_log:` and `readme-pair` reads `document_pairs:`.
Each read the key, refused anything it could not use, and returned "nothing declared". The refusal
went to `logging`, which the Gate does not render. So a project that had written the block and
mistyped one key was told it had written no block at all, and the leg it had switched on never
ran.

Measured at HEAD on a foreign two-package project, `beadloom ci` after each edit to
`.beadloom/config.yml`:

| Case | Declaration | Verdict before |
|------|-------------|----------------|
| A | `source: README.ru.md` + `follower: README.md` | PASS: 1 pair(s) held, 6 block(s) compared |
| B | `source: README.ru.md` alone | SKIP: no document pair is declared |
| C | `source:` + `followr: README.md` | SKIP: no document pair is declared |
| D | `source: ../README.ru.md` + `follower:` | SKIP: no document pair is declared |
| E | `document_pairs: README.md` (a scalar) | SKIP: no document pair is declared |
| F | `source: NOPE.ru.md` + `follower: README.md` | FAIL, UNREADABLE: NOPE.ru.md |

B through E were byte-identical to the line a project that declares nothing gets, and the gate
exited 0 on all four. F is the case the leg got right and is the model the other four were brought
to: the declaration pointed at nothing and the verdict said so, by name. The same four shapes
under `issue_log:` were BDL-UX #270, pinned as an `xfail` since BDL-068 S6 and closed here for
the Gate leg. Its two command surfaces read `issue_log:` through their own resolver and kept the
old answer for one more bead; `beadloom-rqma.8` moved them here too, which is what made the entry
closeable. A module that exists so one rule has one home is worth only as much as the number of
callers that reach it.

## The four states

| State | What it means | What a caller concludes |
|-------|---------------|-------------------------|
| `ABSENT` | no config file, or no such key in it | the project opted out and is not judged |
| `EMPTY` | the key is there with nothing under it | a block holding nothing declares nothing |
| `PRESENT` | the key is there and holds something | the project opted in, whatever the shape |
| `UNREADABLE` | the config file could not be read or parsed | whether the project opted in is unknown |

`EMPTY` is kept apart from `ABSENT` although every caller so far draws the same conclusion from
both. They are different acts, and a config that already reads `document_pairs:` with nothing
under it must not turn red on the upgrade that ships a leg.

`UNREADABLE` is the state that cannot be folded into either neighbour. Reporting it as absence
tells an adopter they opted out; reporting it as a broken declaration reddens a project that may
never have written the key. Each leg's Gate step renders it as a skip that WARNs and names the
file.

**And that is a claim about the step, not about `beadloom ci`.** Measured on a foreign project on
2026-09-12, a `.beadloom/config.yml` with a YAML syntax error ends the run in
`infrastructure/scan_paths.py` during the reindex step, with a traceback and no gate line at all,
so neither leg is reached. The state is reachable from `_step_readme_pair` and
`_step_issue_numbers` and is covered there by tests. The crash is BDL-UX #287, filed rather than
fixed here: the raise is in `infrastructure`, outside this bead's declared scope. Folding
`UNREADABLE` into `ABSENT` because nothing reaches it today would re-create the defect this
component exists to remove on the day #287 is closed.

## A refusal names the entry, not the file

```python
Refusal(
    where="document_pairs[1]",
    why="it has no `follower:` key; it has `source:`, `followr:`",
    remediation="give the entry `source:` and `follower:`, each a path relative to the project root",
)
```

`where` is the entry in the config's own terms, so a reader can go to the line. `why` lists the
keys the entry **does** carry: a missing key and a misspelled one are the same absence to the code
and not at all the same thing to the person who wrote the config, and the list of siblings tells
them apart without this component guessing at spellings.

One refusal per unusable **entry**, never one per problem. The count a verdict prints is how many
declarations could not be used, and an entry that is wrong in two ways is still one entry — `fold`
joins both reasons onto one refusal so a reader repairing it sees everything wrong in one run.

## Nothing here decides a verdict

The refusals travel back to the caller's report, and the caller's Gate step renders them. A module
that both finds a problem and decides what it costs carries two responsibilities, and one of them
is invisible to tests of the other. What the Gate does with a refusal is in
`application/gate.py`: `readme-pair` folds it into the leg's own summary, because some entries of
a `document_pairs:` block can be usable while others are not, and `issue-log` reports the whole
block as one unusable declaration, because it is one.

## Surfaces

| Surface | Behaviour |
|---------|-----------|
| `read_declaration(project_root, key)` | one key's value and its state, or the refusal that says why neither could be read |
| `entries_of(declaration, shape)` | a list-shaped block's entries, or one refusal about the shape it has instead |
| `mapping_of(declaration, shape)` | a mapping-shaped block, or one refusal about the shape it has instead |
| `string_field(entry, field, where, needs)` | a required string key, or the refusal that lists the keys the entry does carry |
| `inside_project(project_root, declared, where, field)` | a declared path resolved under the root, or the refusal that it escapes it |
| `fold(where, refusals)` | every problem with one entry, as one refusal |
| `describe_value(value)` | what a wrongly-shaped value is, in words a config author recognises |
