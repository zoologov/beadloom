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

### And the floor's cost is stated, not only its rule

Skipping history is right; being silent about how much history was skipped is not. Measured on
this repository on 2026-09-09, the verdict read `240 entr(ies), 5 claim(s), floor 262` and then
`No duplicate, unwritten or unclaimed number` — a clean list over the five entries
`unclaimed-number` entered, under a header naming 240 (BDL-UX #267). The all-or-nothing case had
words and the partial one had none, and the partial case is the one every adopter is in from
their first allocation onwards.

`IssueNumberReport.entries_below_floor` is that population. The command prints
`235 of 241 entr(ies) are below floor 262: unclaimed-number did not enter them, and no claim
holds their numbers`; the Gate line carries the same fact as `PARTLY CHECKED`. Neither is a
finding — an unreached population is coverage, and reporting it as a finding would redden every
project that adopts the allocator with a log already written. The clause is emitted only when
there is something to qualify, because a summary that qualifies every log is one a reader stops
reading.

The count stays `0` when there is no floor at all. `not_verified` is that case's one home, and
two statements of one fact are two things that can disagree.

This is also what decides how much of the log the ledger PROTECTS, which is the question
`beadloom-l9ee` weighed when it declined to move the log's entry bodies into one file each. A
claim is a separate file that a lost write cannot take with it, so an entry whose body vanishes
is reported by `unwritten-claim` — for the entries at or above the floor, and for no others.

### The two populations, and why they are separate

| Population | What it is | What it decides |
|------------|------------|-----------------|
| `defined` | a line-start ordered-list number outside a fenced code block | the `duplicate-number` leg |
| `mentioned` | any `#N` token anywhere in the log | the allocator's floor, so a number is never handed out twice |

This log states several numbers only in a consolidated closed-entry heading
(`### Import extraction depth — #159`). Such a number is not an entry and does not enter the
duplicate leg, and it does enter `mentioned`, so the allocator never reissues it. A number below
the highest that neither population holds is reported as **unaccounted for, not free**, and it
is NAMED rather than counted: a count is not something a reader can go and look for. The naming
is bounded, so an adopter with a hundred gaps gets a line they can read.

Quoting such a number in the log's own prose moves it into `mentioned` and silences its own
report, because the check's corpus is the log that contains the entry describing the check. That
self-reference errs safely for the allocator — a number quoted anywhere is never handed out
again — and unsafely for this leg, which is one reason the leg reports rather than blocks.

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

A project that declares the block and mistypes a key is a different project, and gets a different
verdict. Four ways of misdeclaring `issue_log:` used to reach the skip above word for word — the
refusal went to `logging`, which the Gate does not render — so a project that had opted in was
told it had opted out and the three legs never ran. That was BDL-UX #270, pinned as an `xfail`
since BDL-068 S6. The step now fails and says `0 leg(s) run; 1 entr(ies) declared, 1 unusable:
issue_log (it has no `ledger:` key; it has `path:`, `ledgr:`)`. Reading the declaration is
`doc-sync/components/config-declarations`.

**#270 is one defect on three surfaces, and it was closed in two acts.** `beadloom-rqma.7` moved
the Gate leg onto the shared reader and the two commands were left on the old one, so a project
that misspelled `ledger:` was still told it had declared nothing by `issue-number allocate` — the
surface the table below lists first — while the Gate beside it named the key. `beadloom-rqma.8`
moved both commands onto the same reader, and `beadloom-rqma.9` closed the third state on
`check`. Every surface of this feature now tells the three states apart — a log declared, no log
declared, and a config that could not be read so the key's presence is unknown — and none of them
reports one as another. That is the property the entry was about and not the leg the first fix
happened to be measured on.

What each surface DOES about the answer still differs, deliberately. `allocate` cannot hand out a
number against a log it never found, so an unknown costs it exit 2 with the refusal's own words.
`check` and the Gate step report the unknown without blocking, because neither of them was asked
to write anything.

A config file that could not be read is the one case that does not redden. It says nothing about
whether the key is there at all, so the Gate step skips, WARNs and names the file rather than
judging a project that may never have written the key, and `check` says, at exit 0, that whether
the project declares a log is unknown and prints the refusal beneath it. `check` printed the
opt-out's sentence here — `No issue log is declared — no leg ran.`, byte for byte, at exit 0 —
until `beadloom-rqma.9`: a positive assertion about a declaration nobody read, reached by two
shapes, a config that does not parse and a config whose top level is a list.

**Why `check` reports this at exit 0.** The code answers "did a leg find something?", and when the
config could not be read no leg ran and no log was opened, so a non-zero code would be a claim
about a log nobody saw. Exit 2 is unavailable for a second reason: its documented meaning is "the
project declares no `issue_log:` block", which is the assertion this state does not have. What
separates it from a clean run is the verdict's own words and, for a machine, `"undetermined": true`
in the `--json` payload beside a `"declared"` of `null` rather than `false`.

That holds of the Gate STEP, which is where it is tested, and it does not reach a person who runs
`beadloom ci`: the run ends in `infrastructure/scan_paths.py` on a YAML syntax error before any
leg is built — BDL-UX #287. So on a project whose config does not parse, `issue-number check` is
the only one of the three surfaces that reports this state to the person who typed a command.

Measured on 2026-09-12 on a foreign project, through a clean room's own interpreter, for both
shapes. Config unreadable: `check` exit 0 and "Whether this project declares an issue log is
unknown", `allocate` exit 2 with the parse failure. `issue_log:` declared with `ledger:` written
`ledgr:`: `check` exit 1 and `1 entr(ies) declared, 1 unusable`. Nothing declared: `check` exit 0
and "No issue log is declared", `allocate` exit 2 with the same sentence. Three states, three
answers, on each surface.

### Surfaces

| Surface | Behaviour |
|---------|-----------|
| `beadloom issue-number allocate --holder <bead-id>` | takes the next number, writes the claim, prints it; exit 2 when the project declares no log, and exit 2 with the refusal's own words — the entry, the key it lacks and the keys it has — when the project declared one this reader could not use, or wrote a config that could not be read at all |
| `beadloom issue-number check` | the three legs; exit 1 on a finding, exit 1 with the refusal when the project declared a block this reader could not use — where the leg findings are empty and the exit code is the declaration's — exit 0 saying the declaration is unknown when the config itself could not be read, and exit 0 when the project declared no log |
| `beadloom ci`, step `issue-log` | the same run, and it **blocks** — unlike its `docs-quality` neighbour, because a duplicate number is a reference that resolves to two entries and to neither, and every leg's repair fits in the same commit |
