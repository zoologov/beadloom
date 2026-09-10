# PRD: BDL-069 — The checks an adopter meets first, and the populations they run over

> **Status:** Approved
> **Created:** 2026-09-10

---

## Problem

Four defects, measured on the **published 4.0.0 wheel** against projects that are not this
repository. Two of them are in the first two commands an outside user runs.

**1. A virgin `init` leaves the Gate red, and the remediation it prints cannot clear it**
(BDL-UX #282, `beadloom-4fdn`). On a two-package `src/` project:

    beadloom init --yes --mode bootstrap   rc 0   Graph: 3 nodes, 2 edges
    beadloom ci                            rc 1   sync-check FAIL: 4 stale doc(s)
                                                  missing modules: core

`init` writes README skeletons that fail the freshness rule `init` also installs — the skeleton
never names the module, and the modules are already in the index the same command built. The
failure then prints `run beadloom sync-update <ref>`; that command exits 0, reports the pairs
re-attested, and the verdict does not move, because `sync-update` re-baselines hashes while
`missing_modules` is a claim about content. Naming the module by hand clears it in thirty
seconds and is undiscoverable from the message.

**2. `init` writes two nodes with one `ref_id`, and the dropped node makes the Gate falsely
green** (BDL-UX #214, `beadloom-5cpe`). On the ordinary single-package `src/` layout, where the
package is named after the project:

    beadloom init --yes --mode bootstrap   ->  "Graph: 2 nodes"
    beadloom status                        ->  "Nodes: 1"

The node discarded is the `domain` that carries the adopter's source. Nothing reports it —
not `status`, not `doctor`, not `beadloom ci`, which exits 0. And the green is produced by the
loss: `domain-needs-parent` reports `matches none of the 1 nodes in the graph … counted as
evaluated but checks nothing`. Rename the root by hand so both survive, and the same Gate turns
red.

**3. The project's own version is stated in nine places, checked by three instruments over
disjoint populations, two of them checked by nothing** (BDL-UX #281). The list was derived by
hand first and was wrong by two: `docs audit` found a line in `docs/services/cli.md` that its
author had already looked at and classified as an example rather than a claim, and grepping for
its twin found the same sentence in a document no check reads.

**4. Nothing checks that `README.md` and `README.ru.md` correspond** (`beadloom-y8mi`). Both
files were reviewed, approved and pushed; a structural comparison then found a paragraph
present in Russian and absent in English. Both read correctly on their own, which is what makes
the class invisible to reading.

**What the four have in common.** Every one is a check whose population is empty, partial, or
unnamed — the class this project spent BDL-068 removing, still reachable through the commands
an adopter runs first.

## Impact

**Who is affected.** Anyone installing Beadloom for the first time. Defects 1 and 2 are hit by
the ordinary Python layouts — one package named after the project, or several under `src/` —
and neither depends on anything unusual about the project.

**Why it matters now.** The owner is about to hand Beadloom to a team for outside validation.
A team of five meeting a red Gate on their second command, following the printed instruction,
being told it succeeded and staying red, will conclude the tool does not work. That conclusion
would be reasonable.

**What happens if we do not fix it.** The trial returns feedback about the first five minutes
instead of about the thing being trialled. Defect 2 is worse than a bad first impression: an
adopter on the single-package layout carries a graph that silently lacks the node holding
their code, and every check over it reports green.

## Goals

- [ ] A virgin `init` on a two-package `src/` project is followed by `beadloom ci` rc 0, with
      no hand editing.
- [ ] A virgin `init` on a single-package `src/` project whose package is named after it
      produces a graph in which `beadloom status` counts every node `init` reported writing.
- [ ] No check prints a remediation that cannot clear the reason it was printed for.
- [ ] A graph file carrying a duplicate `ref_id` is reported rather than silently reduced,
      through every reader of `.beadloom/_graph/` — measured at seven, of which one is the
      declared policy.
- [ ] One command names every place this project states its own version, what checks each,
      and which are checked by nothing.
- [ ] A check compares the declared README pair and names its own population — how many blocks
      it compared, and which pairs of files it holds.

## Non-goals

- Making `beadloom impact` read YAML or Markdown. It reads Python by design and says so; four
  of the nine version-stating surfaces are `unreadable-target` to it, and that is a fact the
  solution has to work around rather than a defect to fix here.
- Rewriting `sync-update`'s scope. BDL-UX #279 is open about what `--all` re-baselines; this
  epic changes what the *failure message* claims, not what the command does.
- Any change to the `domain-needs-parent` rule itself. It behaved correctly in both defects —
  it fired when the node existed and reported an empty population when it did not.
- Translating the README pair automatically, or checking their prose. Only the shape is
  comparable across two languages; anything else would be a check that has to be switched off.

## User Stories

### US-1: The first five minutes end green
**As** someone installing Beadloom on a project for the first time, **I want** `init` followed
by `beadloom ci` to be green, **so that** I can tell my own project's problems from the tool's.

**Acceptance criteria** (each references a scenario in `tests/acceptance/features/`):
- [ ] Scenario: `A virgin init on a multi-package layout is followed by a green gate`
- [ ] Scenario: `A virgin init on a single-package layout keeps every node it reported writing`

### US-2: A remediation that is printed can be followed
**As** an adopter reading a failure, **I want** the command the failure names to change the
verdict, **so that** following the instruction is not a way to stay stuck.

**Acceptance criteria**:
- [ ] Scenario: `A staleness reason that re-attesting cannot clear says so in its remediation`

### US-3: A dropped node is reported
**As** anyone whose graph is read, **I want** two nodes sharing one `ref_id` to be reported
rather than silently reduced to one, **so that** a count I was given can be trusted.

**Acceptance criteria**:
- [ ] Scenario: `A graph file carrying one ref_id twice is reported by every reader of the directory`

### US-4: The version's homes are derivable
**As** whoever cuts the next release, **I want** one command to name every place this project
states its version and what checks each, **so that** the list is derived rather than recalled.

**Acceptance criteria**:
- [ ] Scenario: `The version report names each place, its checker, and the places nothing checks`

### US-5: The README pair is compared
**As** the owner of a two-language README, **I want** a check that the two correspond
structurally, **so that** a paragraph present in one and absent in the other is found by
something other than luck.

**Acceptance criteria**:
- [ ] Scenario: `A declared document pair whose block sequences differ is reported with the population compared`

## Acceptance Criteria (overall)

Behaviour-bearing criteria are scenarios; the suite holds their text and this list references
them by name. `beadloom lint` reports a referenced scenario the suite does not contain.

- [ ] Scenario: `A virgin init on a multi-package layout is followed by a green gate`
- [ ] Scenario: `A virgin init on a single-package layout keeps every node it reported writing`
- [ ] Scenario: `A staleness reason that re-attesting cannot clear says so in its remediation`
- [ ] Scenario: `A graph file carrying one ref_id twice is reported by every reader of the directory`
- [ ] Scenario: `The version report names each place, its checker, and the places nothing checks`
- [ ] Scenario: `A declared document pair whose block sequences differ is reported with the population compared`

**Non-behavioural criteria** stay checkboxes and are labelled, so the absence of a scenario is
a stated decision rather than a gap:

- [ ] The temporary sentence in both READMEs — "the first `beadloom ci` is worth reading rather
      than assuming green" — is removed once US-1 holds — non-behavioural: it is prose about a
      defect, and its removal is observable only by reading the file.
- [ ] BDL-UX #282 and #214 are moved to `Closed Issues` **after** being re-run against current
      behaviour, per that section's own standard — non-behavioural: the log is a record, and no
      check reads it.
- [ ] A stale line names the pair it is about — **measured after this document was approved,
      and the criterion above it was wrong.** The line is not printed twice: a pair is a
      document AND a code file, so two files in a package give two pairs over one README.
      `--json` distinguishes them by `code_path`; the text line drops that field, so two
      different pairs render identically. `4 stale doc(s)` is also wrong wording — two
      documents, four pairs. Non-behavioural only in that the fix is a rendering change; the
      finding itself is behavioural and is US-2's neighbour.
