# Issue Numbers

The issue log's numbers: the two populations the log states, the next number allocated by an
exclusive create, and the three legs over what one filesystem cannot span.

**Source:** `src/beadloom/doc_sync/issue_numbers.py`

---

## Specification

### Purpose

A numbered issue log is a single markdown file every writer appends to, and the number a writer
takes is the one they read off the end of it. On this repository that produced five collisions:
BDL-UX #187 (two entries numbered 187, ambiguous for fifteen days across a CHANGELOG, a ROADMAP,
eight test files and thirty-six tracker records), #211, #253 (two agents in one slice, hours
apart, whose ambiguity reached committed artifacts), and two more within one hour on 2026-09-09
— a number another bead already held, and a number that never reached the file at all.

The number is therefore **allocated**, not read.

### Why an allocator rather than a check

The choice was settled by measurement rather than by preference. The coordinator ran a whole-log
duplicate check on the morning of 2026-09-09 and found exactly one duplicate; the fifth collision
happened four hours later anyway. A check reports after the fact, and two writers filing
concurrently cannot grep each other.

The check ships **beside** the allocator and not instead of it, because the allocator's guarantee
has a boundary: see *What the allocation cannot span* below.

### What "atomically" means over a markdown file in git

It is neither git's guarantee nor the log's. Allocation is `os.open(O_CREAT | O_EXCL)` of one
claim file per number in a ledger **directory**. POSIX makes that create-or-fail indivisible, so
of two writers computing the same next number exactly one creates the name and the other retries
at the next one. Git never enters it — two writers commit two different files, which is a merge
with nothing to resolve.

The claim file is one file per incident deliberately. `beadloom-l9ee` reached the same shape from
the other direction: the property that makes the collision impossible is **one writer per file**,
not generation, and a shared append-only log is the same defect under another filename. This
module takes that layout at the boundary rather than migrating entries already written — the
claim file is where an incident's body grows if the log becomes a composed view of the ledger.

### What the allocation cannot span

| Boundary | What happens | What covers it |
|----------|--------------|----------------|
| One filesystem | POSIX and NTFS make the exclusive create indivisible; over NFSv2 it is emulated | nothing here — a project on NFSv2 keeps the check as its only guarantee |
| One clone | two writers in two checkouts each allocate against their own ledger and both can take one number | `duplicate-number`, which reads the merged log |
| A writer who does not use it | the log is hand-appended past the ledger's floor | `unclaimed-number` |

### The three legs

| Leg | Fires when | The instance it is filed for |
|-----|------------|------------------------------|
| `duplicate-number` | one number is defined by more than one entry | #187 and #253 |
| `unwritten-claim` | a number is claimed and no entry in the log defines it | #260 — a number in a bead title with nothing in the file |
| `unclaimed-number` | an entry at or above the ledger's floor holds a number no claim holds | the allocator was bypassed |

### The floor is derived, never authored

The floor is the lowest number the ledger holds. A project that adopts the allocator is judged
from its first allocation onwards, and its history is not retro-required to have been allocated.
A hand-written floor would be the literal `beadloom-mr2l.72` was filed about — a fact about the
log kept somewhere other than the log.

Before the first allocation the ledger has no floor, so two of the three legs enter no number at
all. The report says so through `not_verified` rather than reading as clean.

### The two populations, and why they are separate

| Population | What it is | What it decides |
|------------|------------|-----------------|
| `defined` | a line-start ordered-list number outside a fenced code block | the `duplicate-number` leg |
| `mentioned` | any `#N` token anywhere in the log | the allocator's floor, so a number is never handed out twice |

This log states several numbers only in a consolidated closed-entry heading
(`### Import extraction depth — #159`). Such a number is not an entry and does not enter the
duplicate leg, and it does enter `mentioned`, so the allocator never reissues it. A number below
the highest that neither population holds is reported as **unaccounted for, not free**.

### What it cannot decide

The entry grammar is the one this log is written in and no other. A project whose entries are
`### #7 — title` states its numbers in a shape this reader does not accept, and it will report
zero entries rather than guessing — which is why the report carries the entry count beside its
verdict, and why the suite asserts that count is non-trivial on this repository.

### Opting in

The log is declared in `.beadloom/config.yml`:

```yaml
issue_log:
  path: .claude/development/BDL-UX-Issues.md
  ledger: .claude/development/BDL-UX-Issues
```

A project that declares no `issue_log:` block is not judged: the Gate step is a named skip and
`beadloom issue-number allocate` refuses and names the key. The upgrade that ships this step
turns nobody's green tree red.

### Surfaces

| Surface | Behaviour |
|---------|-----------|
| `beadloom issue-number allocate --holder <bead-id>` | takes the next number, writes the claim, prints it; exit 2 when the project declares no log |
| `beadloom issue-number check` | the three legs; exit 1 on a finding |
| `beadloom ci`, step `issue-log` | the same run, and it **blocks** — unlike its `docs-quality` neighbour, because a duplicate number is a reference that resolves to two entries and to neither, and every leg's repair fits in the same commit |
