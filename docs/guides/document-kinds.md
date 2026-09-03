# Document Kinds, Documentation Spaces and the Writing Standard

<!-- beadloom:watches=cli,flow.yml -->

Every document this project holds sits in one of **three spaces** — TO-BE, AS-IS or WORKING —
and the choice of those three names over TODO and DONE is the decision every mechanism below
follows from. Read that section first. The rest of the guide is what it makes possible.

This guide has three parts: the spaces and the relation between them, the **architecture
documents** that are held against code, and the **planning documents** that are held against
the writing standard. Each part says what its check can and cannot decide.

---

## The three spaces

### The decision: nothing changes status

| Space | Kinds (default) | What the document is | Held against |
|-------|-----------------|----------------------|--------------|
| **TO-BE** | `PRD`, `RFC`, `BRIEF`, `CONTEXT`, `PLAN` | what the system is to become | nothing directly — see the relation below |
| **AS-IS** | `SPEC`, `DOC`, `README` | what the system is | the code, by `sync-check` |
| **WORKING** | `ACTIVE` | progress within a bead — neither intent nor reality | nothing; exempt from freshness by declaration |

The names are deliberately not TODO and DONE, and the reason is that **nothing here changes
status**. A PRD is not a task that becomes done. It stays the record of what was intended, and
what happens when the work lands is that a **different** artifact — the AS-IS document — is
written or updated to describe the new reality.

That is why the checkable claim is a **relation between two artifacts** rather than a flag on
one. A flag has nothing to be verified against: `status: done` in a PRD is true because
somebody typed it, and no later change to the code can make it false. A relation can be
checked, because both of its ends exist on disk and in the graph: *this epic recorded intent,
its beads closed, and the node it named still has no document describing what was built*. That
sentence is either true or false of the tree in front of you, and `beadloom docs spaces`
decides it.

### What each space is for

```bash
beadloom docs spaces            # the report, every denominator beside every count
beadloom docs spaces --json     # machine-readable
beadloom docs spaces --strict   # exit 1 when anything is reported
beadloom search "sequencing principles" --kind to_be
```

TO-BE documents are indexed **in place** rather than copied, so `beadloom search --kind to_be`
searches the planning tree without the flow's scaffold becoming a second source of truth. AS-IS
documents are the ones `sync-check` pairs with code — that pairing is what "as-is" means
operationally. WORKING documents are excused from freshness, which is a declaration and never
an inference from a missing pair (see below).

Measured on this repository, 2026-08-26 during BDL-062: `to_be 194`, `as_is 100`,
`working 56` documents. All three are moving denominators — this feature's own PRD, RFC,
CONTEXT and PLAN moved TO-BE by four, and its ACTIVE.md moved WORKING by one — so re-run
`beadloom docs spaces` rather than quoting the numbers.

### Kind wins over root, and a disagreement is a finding

A document is placed by two signals: its **kind** (the file stem — `PRD.md` is a `PRD`, matched
case-insensitively, so `prd.md` answers the same) and the **root** globs its path falls under.
When the two disagree, **kind wins**. That is load-bearing rather than arbitrary: `ACTIVE.md`
lives inside the TO-BE tree, so a root-first answer would classify every WORKING document as
intent and the freshness exemption would excuse nothing.

Kind winning leaves an obvious hole — a document whose kind sends it to a space whose declared
roots do not reach it. It used to fall out of every count: not in a population, not in an epic
list, and nothing said so. The rule now is one sentence and it is an invariant, not a patch:

> `sum(populations) == |files any declared root matched|` — every document a declared root found
> is placed in exactly one space, and a document whose kind and root disagree is **counted in the
> space its kind chose and reported** as `document_outside_declared_root`.

The history is why the invariant is stated rather than the counts. The population failed three
times before it held: the first denominator silently dropped 34 epics by requiring a *Related
Files* heading (`beadloom-mr2l.17`); four directories then fell out for carrying no
`CONTEXT.md`/`BRIEF.md` (`beadloom-mr2l.18`, widened by `.73`); and a reviewer who planted a
`README.md`-only planning directory found a third route out (`beadloom-mr2l.19`, closed by
`.77`). Three separate counts, each corrected and each still wrong. What holds now is the
invariant, pinned by a test on this repository and on the TypeScript fixture in
`tests/adopter_project.py`.

The finding is reported **once per kind** with a count, up to five example paths and the roots
that failed to reach them: sixty directories following one convention are one decision to make,
not sixty lines to read. A space that declares **no** root has said nothing about where its
documents live and therefore contradicts nothing — which is why this repository's 56
`ACTIVE.md` files are silent and `documents_outside_declared_root` reads empty here.

Roots have their own precedence for the case where two of them name one file, and it points the
same way for a different reason: **WORKING is consulted first**, because its shipped root list
is empty, so the only way a document lands there by root is a project *declaring* it — while
the AS-IS default is the catch-all `docs/**/*.md`. If the catch-all won, a declaration written
in the file we tell a project to edit would be silently inert.

### Configuring the spaces

Nothing above is hardcoded. A project declares its own layout under `doc_roots` in
`.beadloom/config.yml`. Every part is optional, and the shipped defaults apply to whatever is
left out.

```yaml
docs_dir: docs                       # the directory sync-check pairs with code

doc_roots:
  to_be:
    roots:
      - "docs/planning/*/*.md"
    kinds: [PRD, RFC, BRIEF, CONTEXT, PLAN]
    intent_documents: [CONTEXT.md, BRIEF.md]   # where an epic declares its related nodes
  as_is:
    roots: ["docs/**/*.md", "*.md"]
    kinds: [SPEC, DOC, README]
  working:
    kinds: [ACTIVE]
    exempt_from_freshness: true
    reason: "why these documents are not held against the code"
```

`intent_documents` is configuration for the same reason every root around it is: an adopter
whose planning document is named otherwise would lose 100% of its epics and read a plausible `0 of 0`. `docs_dir` matters here because a `sync_state` row spells its document relative to the
docs directory while every root glob is written relative to the project — one file, two
spellings, and a WORKING root declared in the second spelling used to have no effect on
freshness at all (`beadloom-mr2l.75`).

Full reference: the [Doc Roots
component](../domains/infrastructure/components/doc-roots/DOC.md) for the vocabulary, and the
[Doc Spaces component](../domains/application/components/doc-spaces/DOC.md) for the relation.

### The relation: intent that never reached reality

`beadloom docs spaces` reports an epic when three things are all true: it recorded intent, its
work finished, and the node it named has no AS-IS document.

1. The epic's intent document (`CONTEXT.md`, then `BRIEF.md`) names graph nodes in its
   **Related Files** section. Only that section is read, because it is a *declaration*. An
   earlier version matched every backticked token anywhere in the epic's documents. Run over
   60 epics, it attributed the node `status` to nine epics that merely used the English word,
   and it was thrown away rather than tuned.
2. The tracker says at least one of the epic's beads is closed.
3. The declared node's `docs:` list is checked against the AS-IS space.

The first finding this relation produced on this repository is the clearest statement of what
it is for. BDL-061 named `cli-commands` in its CONTEXT's *Related Files*, the epic had more than
sixty closed beads, and `cli-commands` was a real declared node in `.beadloom/_graph/services.yml`
with **no `docs:` entry at all** — the `cli` service beside it declared `docs/services/cli.md`
while the component holding every command implementation declared nothing:

```
[warn] .claude/development/docs/features/BDL-061/CONTEXT.md:125 (intent_without_as_is)
       epic BDL-061 declares the node `cli-commands` and has closed beads, but `cli-commands`
       has no AS-IS document
```

**No other check could have seen it.** `lint` judges import boundaries and module coverage — it
asks whether modules reach nodes, not whether nodes reach documents. `sync-check` compares
*pairs*, so a node that declares no document contributes no pair, and a document that does not
exist cannot go stale. The absence is invisible to both by construction, which is the whole
reason the relation exists.

That finding was answered in BDL-062: `cli-commands` was given a document, and so was `status`.
Measured on this repository, 2026-08-27, the relation reports no `intent_without_as_is` finding
and one of the second kind instead:

```
[warn] .claude/development/docs/features/BDL-030/CONTEXT.md:0 (epic_not_in_tracker)
       epic BDL-030 declares 1 node(s) and `bd list --all --json` has no record of it, so
       whether its work finished is unknown and its intent was held against nothing
```

The two findings are not variants of one another. The first says intent reached no document.
The second says the run could not tell whether the intent's work had finished, so the intent was
held against nothing at all — an epic the tracker export has lost is not an epic whose beads are
open, and reporting them alike would let a lost export read as work in progress.

### What the relation does not check, and says so

A count with no denominator beside it is the defect this epic exists to remove, so every epic
the relation could not decide is named rather than folded into a green number. Measured here on
the same run:

```
38 of 62 epic(s) have closed beads; 5 declare a node; 17 node declaration(s) held against AS-IS
NOT CHECKED: 57 epic(s) declare no node (4 carry no readable intent document)
NOT CHECKED: 24 epic(s) the tracker does not name
```

Read the shape rather than the numbers: every one of them moves with this repository's own
planning tree, and `beadloom docs spaces --json` prints the current values.

Each `NOT CHECKED` line is a different way of knowing nothing, and each has its own reason code
in `--json` under `unresolved_reasons`: `no_node_declared`, `no_intent_document`,
`unreadable_intent_document`. An epic a readable tracker simply does not name is separate
again (`epics_unknown_to_tracker`), because "the export never heard of this epic" and "its
beads are all open" are not the same state — they were one empty tuple until
`beadloom-mr2l.74`, and the first is not an honest skip. On this repository the second finding
on the run above is exactly that case: `BDL-030` declares a node and the tracker has no record
of it, so its intent was held against nothing.

A project with **no** TO-BE document at all is a NAMED skip that prints the roots it looked
under, including `no root declared`. It is never a pass.

### The WORKING exemption is a declaration

The WORKING space is exempt from `sync-check` freshness, and that exemption is a **declaration
in config**, never an inference from a missing pair — because deleting a pair must not make a
check quieter. A pair excused this way reports `exempt` with the declared reason in `details`.
It is counted in the `--json` summary and printed as `[exempt]` rather than `[ok]`.

Two things detect a wrong declaration:

- `working_exemption_inert` — a declared kind or a declared root that matched no document. It
  fires **per declared item**, so a `kinds: [ACTIVE, SPEC]` line whose `SPEC` half does nothing
  reports `SPEC` and stays quiet about `ACTIVE`. Asking the question of the declaration as a
  whole meant any single match silenced every other half of it.
- `working_declaration_contradicted` — a document the config declares ephemeral that the graph
  *also* declares as a node's documentation. Those two statements cannot both be right.

And the exemption covers freshness only: a pair whose document or code file is gone reads
`missing` before any exemption applies, so a WORKING declaration cannot make a deleted file
quieter than a present one.

Measured here: the shipped exemption reaches 56 documents and excuses **0** sync pairs, because
`ACTIVE.md` lives outside the docs directory the indexer walks, so none of those documents is a
sync pair at all. The gate prints both numbers apart — `56 WORKING document(s) in the exempt
space, 0 sync pair(s) excused` — because one word for two populations is how a reader takes the
first number as the number of excused pairs. `beadloom docs spaces` runs no freshness check and therefore
reports `pairs_excused: null` rather than `0`: **unknown is not zero**, in the tool's own
output.

### Two limits, stated rather than discovered

**The gate stays green on everything in this section.** `beadloom ci` runs `doc-spaces` as a
warn-only step: its `passed` is unconditionally true and every finding is a warning, so the
exit code does not move no matter what the relation reports. That is the epic's shipped-as-warn
constraint applied consistently — a new check that turns an adopter's green project red on
upgrade is a check that gets disabled — and it means the honest answer to "can an adopter get a
green gate they should not have" is **yes, with the objection printed**. The step reports
`WARN` rather than `PASS` whenever it could not decide, so a green gate line still
distinguishes *checked and clean* from *not checked*.

**A one-line WORKING root can take a whole project's freshness gate to warn-only, and the only
thing standing in the way is the default kind list.** Declaring

```yaml
doc_roots:
  working:
    roots: ["docs/**/*.md"]
    exempt_from_freshness: true
    reason: "..."
```

excuses every document under `docs/` whose kind is not `SPEC`, `DOC` or `README` — kind wins,
so those three stems stay in AS-IS and stay checked. A project whose documents are named
`architecture.md`, `getting-started.md` and `ci-setup.md` has no AS-IS stem anywhere, and that
single line excuses all of them. There is no guard here. The kind list is the whole of it.

**Honouring the declaration is the design, not the defect.** A project that writes a rule in
the file we tell it to edit must have that rule take effect, or the file is decoration. What
was broken, and is fixed, is that it took effect **silently**. Review `beadloom-mr2l.19`
measured the repaired behaviour in a clean room: with `working.roots: ["docs/**/*.md"]`
declared, 28 of 330 sync pairs go `exempt` and `docs spaces` names **6**
`working_declaration_contradicted` documents — exactly the 6 documents those 28 pairs belong
to. The coverage is complete rather than partial, and structurally so: a sync pair exists only
for a document the graph declares, and the contradiction fires on precisely the documents the
graph declares that the config calls ephemeral. Before that repair the same configuration
reported **0**.

So an adopter who reaches for this line gets what they asked for, and gets told — by name, in
`docs spaces`, and in the excused count and declared reason on the `sync-check` line — which
documents they just stopped checking.

### Adopting the spaces on a project that is not Beadloom

1. Run `beadloom docs spaces`. If it prints a NAMED skip, no TO-BE document matched — declare
   `doc_roots.to_be.roots` for where your planning documents live.
2. If it reports `document_outside_declared_root`, your stems and your roots disagree. The
   remedy the finding names is usually to declare the kind rather than to move the files: a
   project whose feature folders hold `README.md` should add `README` to `to_be.kinds`, and the
   finding goes quiet because the classification became right, not because it was suppressed.
3. If your intent document is not `CONTEXT.md` or `BRIEF.md`, declare
   `doc_roots.to_be.intent_documents`. Without it every epic reads unresolved.
4. Read the `NOT CHECKED` lines before the findings. On a first run they are usually larger
   than the finding count, and they are the honest measure of how much the relation could
   decide.

---

## The two families of checked document

Beadloom checks two families of document, and they are checked by different mechanisms for
different reasons. This part names both, says what each requires, and states what each check
can and cannot decide.

| Family | Written by | Checked by | Verdict |
|--------|-----------|------------|---------|
| **Architecture documents** — a README or SPEC per graph node | `beadloom docs generate`, then edited | `beadloom sync-check` (phase 5) | `incomplete`, `warn` |
| **Planning documents** — PRD, RFC, CONTEXT, PLAN, ACTIVE, BRIEF | the `/templates` document set | `beadloom docs quality` and the `docs-quality` gate step | `warn` |

Both ship as warnings. A new check that turns an adopter's green project red on upgrade is a
check that gets disabled, and a disabled check is worse than none.

---

## Architecture documents

### The kinds

Five templates ship as package data under `templates/docs/` and compose through the same
`core → architecture → stack → project` assembly the role files use:

| Doc kind | Written for | File |
|----------|-------------|------|
| `overview` | the project | `docs/architecture.md` |
| `domain` | a `domain` node | `docs/domains/<domain>/README.md` |
| `service` | a `service` node | `docs/services/<service>.md` |
| `feature` | a `feature` node | `docs/domains/<domain>/features/<feature>/SPEC.md` |
| `beadloom-readme` | the project | `.beadloom/README.md` |

`overview` and `beadloom-readme` describe the project rather than a node, so they have no sync
pair and their sections are not checked. The other three are bound to a node kind, which is what
makes a section check possible at all. A `component` node's `DOC.md` is authored rather than
generated — there is no `component` doc template — so a component document is checked for
freshness like any other pair and is outside the section check.

Until BDL-061 S4 every one of these was an f-string inside `doc_generator.py`. Two consequences
made the move worth doing: an adopter had **nothing to adapt** — the shape of their architecture
documentation was a Python literal in our package — and **nothing held the shape after
generation**, so a document could lose the sections it was born with and no check could see it.

### A project adds its own sections

```markdown
<!-- .beadloom/flow/docs/feature.md -->
## Runbook

How to operate this feature in production.
```

The fragment appends after the shipped template, exactly as `.beadloom/flow/roles/<role>.md`
appends to a role. **A section required is a section the composed template carries**: adding
`## Runbook` to the fragment makes `Runbook` a required section of every feature SPEC by the same
act. Nothing is declared twice, so nothing can disagree with itself.

A section that reaches the document through a placeholder — `## Public API`, rendered only for a
node that has public symbols — is conditional by construction and is never required of a node
that has none.

`docs` is the only artifact kind composed with `carries_suppressions=False`: a suppression notice
belongs in a role protocol an agent reads, not in the middle of somebody's architecture
documentation.

### The check is peer-relative

The finding this check exists to make is *this document departs from the shape its peers keep*.
So a required section counts as in use for a node kind only when a **majority** of that kind's
documents carry it. A minority — including none — reports the KIND once, with the ratio, because
the fix is then in the template rather than in every file.

Measured on this repository, 2026-08-27, with the requirements derived from the composed
templates (`Source`, `Dependencies` for every kind, plus `Features` for `domain` and `Parent` for
`feature`):

| Kind | In use | Not in use, reported once with its ratio |
|------|--------|------------------------------------------|
| domain | `Features` | `Source (0/7)`, `Dependencies (0/7)` |
| feature | — | `Source (5/42)`, `Dependencies (3/42)`, `Parent (4/42)` |
| service | — | `Source (0/4)`, `Dependencies (0/4)` |

One document is reported: `docs/domains/infrastructure/README.md` carries no heading naming
`Features`, and six of its seven peers do. The honest reading is that `infrastructure` has eight
components and no feature at all, so it announces its children under `## Components`. Renaming a
heading to satisfy a matcher would trade a true finding for a false green, so the row stands as
reported. Section matching is case-insensitive, whole-word and depth-independent, which is why
`## Features and components` counts and `## Featureset` does not.

## Planning documents

### The kinds and what each is for

| Kind | Used for | Ships with |
|------|----------|------------|
| `PRD` | epic, feature | Problem, Impact, Goals, Non-goals, User Stories, Acceptance Criteria |
| `RFC` | epic, feature | Overview, Motivation, Technical Context, Axes, Proposed Solution, Alternatives, Risks, Open Questions |
| `CONTEXT` | epic, feature | Goal, Key Constraints, Code Standards, Architectural Decisions, Related Files, Current Phase |
| `PLAN` | epic, feature | Epic Description, Dependency DAG, Beads, Bead Details |
| `BRIEF` | bug, task, chore | Problem, Solution, Axes, Beads, Acceptance Criteria, Non-behavioural declaration |
| `ACTIVE` | every type | Current Bead, Progress, Results, Notes |

The kind is the file's stem: `PRD.md` is a `PRD`. A project whose documents are named `prd.md`
gets `prd` as a kind of its own, which is honest — nothing was told the two are the same thing.

**Acceptance criteria in a PRD or a BRIEF reference scenarios by name.** The `.feature` file
holds the text; the document states the intent and points at it. See
[Executable Acceptance Scenarios](bdd-scenarios.md). A criterion no observer can see stays a
checkbox and is **labelled** as non-behavioural with a reason, so its absence from the suite is a
stated decision rather than a gap.

### The eleven checks

The first five are the writing standard, and they read the CONTENT of a document.

| Check | Reports | Where it reads |
|-------|---------|----------------|
| `measurable-goal` | a goal statement with no number in it | the `## Goal` / `## Goals` section |
| `decision-reason` | a decision row whose reason cell is empty | any table with a Reason / Rationale / Why column |
| `risk-mitigation` | a risk row with no mitigation, or one naming no action | any table with a Mitigation column |
| `pending-in-approved` | a question still answered `Pending` | `## Open Questions`, in a document whose status is `Approved` or `Accepted` |
| `unfilled-placeholder` | a shipped template token nobody replaced | the whole document, outside fenced and inline code |

The next four arrived with BDL-068 S1.4 and read a document's SHAPE — whether the
sections its kind carries are there, and whether an `## Axes` section is complete.

| Check | Reports | Where it reads |
|-------|---------|----------------|
| `missing-section` | a section this kind's template carries AND a majority of its peers keep | every document of a kind `/templates` describes |
| `empty-section` | a required heading with nothing under it | the same, and not peer-relative |
| `axes-without-a-seed` | axes stated without naming the seed they were derived from | the `## Axes` section |
| `axis-without-a-scope-decision` | an axis row carrying the derivation's output and no decision | the same |

The last two arrived with BDL-068 S1.5 and take the work-item FOLDER as their
unit, because a route is a property of the item rather than of any one document.

| Check | Reports | Where it reads |
|-------|---------|----------------|
| `routed-without-axes` | a work item on the simplified route carrying no `## Axes` section anywhere | the folder |
| `route-not-supported-by-the-axes` | a work item on the simplified route whose kept axes name more than one graph node | the folder |

Only the simplified route (`bug`, `task`, `chore`) is judged by the last two. The
full route writes a PRD and an RFC and each passes an approval gate, so a
mis-route there meets a person. The simplified route writes one BRIEF and passes
one gate, on work already scoped. `routed-without-axes` is absolute rather than
peer-relative for a measured reason: at `2a5c0d1` `missing-section` reported
`BRIEF documents do not carry Axes (0/12)` against the KIND and nothing against
any document, which is the right treatment for a convention an archive never
adopted and the wrong one for the input to a decision.

```bash
beadloom docs quality                                  # the report, exit 0 with findings
beadloom docs quality --check pending-in-approved --json
beadloom docs quality --strict                         # exit 1 when anything is reported
```

Documents are found under `.claude/development/docs/features/*/*.md` by default; a project with
another layout declares its own globs under `doc_quality.paths` in `.beadloom/config.yml`. A run
that matches no document says so and names the globs it looked under, rather than printing a
clean bill of health over nothing.

### What the checks cannot decide

- **`measurable-goal` decides one named form, not measurability in general.** A goal is reported
  only when BOTH legs hold: its predicate is an unbounded improvement — `improve`, `enhance`,
  `establish`, `clean up`, or `make`/`keep` something *better / faster / simpler / intuitive* —
  and it names no witness. A witness is a quantity, a named artifact (an inline code span, a
  `--flag`, a file name, a `snake_case` identifier) or an observable outcome (`exits`, `fails`,
  `detects`, `renders`, `green`). This is the construction the three sibling checks already use:
  name the empty form, do not guess at the good one.
- **What it was, and why the number moved from 154 to 4.** As shipped the check looked for a
  digit and called its absence "no measurable clause" — a premise that is false, because an exit
  code, a named artifact and a binary capability are all measurable without a digit. It reported
  **154 of 235** goal statements here; review `beadloom-mr2l.15` sampled 18 of them and could
  defend **one**, and among the false positives was `beadloom lint --strict fails (non-zero)`,
  the exit-code form BDL-UX #148 exists to insist on. `beadloom-mr2l.70` re-scoped the criterion
  rather than paying the debt as written, because inserting numerals into 154 sentences that were
  already checkable teaches an author to write for the checker. The re-scoped criterion reports
  **4 of 232** on the same corpus, and all four are the standard's own example ("Make Beadloom
  enjoyable and intuitive"). The denominator fell by three for one unrelated reason: three
  statements the old population held were a markdown horizontal `---` closing a Goal section.
- **The limit, measured: precision was bought with recall.** Of the 150 statements the re-scope
  newly accepts, **27 name no witness either** — they are accepted because their predicate is not
  an unbounded improvement, and about those this check now decides nothing. A goal it accepts is
  not thereby proved measurable. The `docs-quality` gate line prints the finding count and not
  those 27, so read this limit from here or from the
  [Doc Quality SPEC](../domains/doc-sync/features/doc-quality/SPEC.md) rather than from the gate.
- **All four remaining findings are in closed epics**, whose goals cannot be made measurable
  retroactively without rewriting the record of what was intended. That is why
  `beadloom-mr2l.71` exists — a historical exclusion for documents whose work is finished — and
  not a rewrite.
- **A reason is checked for EXISTENCE.** The standard also asks that a reason explain *why*
  rather than restate the decision. No checker decides that.
- **A mitigation is judged against a named set of empty ones** — `monitor`, `monitor it`, `watch
  closely`, `TBD`, `n/a`, a bare dash — matched as the whole cell. *Monitor the queue depth and
  page above 80%* is a mitigation; *monitor it* is not. Whether a stated mitigation would work is
  not decidable.
- **A Draft may have Pending questions.** Only an agreed status is held to the rule. Reporting a
  draft's open questions trains an author to ignore the check.
- **A `Pending` outside `## Open Questions` is not a finding.** A PLAN's bead table marks
  unstarted beads `Pending`; that is a status, not an undecided design.

### The report says what it did not judge

Two denominators, because one of them structurally cannot see the other's blind spot.

`QualityReport.applicable` counts, per check, how much there was to read, and
`checks_that_read_nothing` names any check that found nothing at all anywhere. That is a global
OR over the corpus: it goes silent the moment one document carries one row, so it can detect a
check that is blind everywhere and not one that is blind on an entire document kind.

`QualityReport.by_kind` therefore states what each kind contributed, and `kinds_that_read_nothing`
names the kinds no **content** check enters. The judgement is made over the four checks that read
items — a goal, a decision row, a risk row, an open question — because `unfilled-placeholder`
counts documents *opened* and would report every kind as read.

Measured on this repository, 2026-08-27, over 248 planning documents:

| Check | Findings | Read |
|-------|----------|------|
| `measurable-goal` | 4 | 238 goal statements |
| `decision-reason` | 0 | 272 decision rows |
| `risk-mitigation` | 0 | 138 risk rows |
| `pending-in-approved` | 2 | 69 open-question rows |
| `unfilled-placeholder` | 0 | 248 documents |

| Kind | Documents | goals | decision rows | risk rows | open questions |
|------|-----------|-------|---------------|-----------|----------------|
| ACTIVE | 56 | 1 | 10 | 0 | 0 |
| CONTEXT | 47 | 31 | 214 | 0 | 0 |
| RFC | 46 | 0 | 41 | 121 | 65 |
| PLAN | 43 | 0 | 0 | 0 | 0 |
| PRD | 42 | 206 | 7 | 17 | 4 |
| BRIEF | 11 | 0 | 0 | 0 | 0 |
| SUMMARY | 3 | 0 | 0 | 0 | 0 |

**The corpus includes the documents that publish these numbers.** These counts are measured over
this repository's own planning documents, so writing a decision row into a CONTEXT moves the
`decision-reason` denominator by one. Re-measure with `beadloom docs quality --json` rather than
quoting a table; what is durable here is the SHAPE of the report — findings over a stated
population, per check and per kind — not any particular row.

**57 of 248 documents (23%) are in a kind no content check enters** — BRIEF, PLAN and SUMMARY —
while `checks_that_read_nothing` read `()` throughout. The three zero rows above are a genuinely
checked green: each of `decision-reason`, `risk-mitigation` and `unfilled-placeholder` was shown
to fire on a real document of this repository under a single reverse-editable edit, so they are
green because there is nothing to report and not because nothing was read.

**Why the three kinds read zero is template construction, and the decision is open.** The shipped
BRIEF template carries no Goal section, no Reason column, no Risks and no Open Questions — and
BRIEF is the kind every `bug`, `task` and `chore` uses. PLAN's criteria live in a "Done when"
list rather than in a Goal section. Whether to give those templates the rows, or to state that
they are outside these four checks, is a product decision with a migration behind it and it has
not been taken. What has changed is that the state is printed by `docs quality` and by the gate
step rather than inferred by a reviewer.

### A document nobody could read is named

A planning document is a UTF-8 contract: Beadloom chooses the codec and decodes explicitly. A
document the globs matched and the checks could not decode is **counted**, carries a named
`unreadable` finding with its reason, and is excluded from the denominators of the kind it
belongs to. Counting a file nobody read as a file carrying nothing would turn an encoding
accident into evidence about a project's templates.

`beadloom docs quality` prints one line per unreadable document; the `docs-quality` gate step
prints `UNREADABLE: N` and reports `WARN`. Until BDL-061.66 that channel was populated and
surfaced nowhere, and before that one undecodable document took the whole `beadloom ci` gate down
with a traceback.

## What the gate does with all of this

`beadloom ci` runs `docs-quality` as its fifth step. It never blocks: `passed` is unconditionally
true and every finding is a warning. It reports **WARN** rather than PASS when any of three
things is true — a check read nothing anywhere, a document kind no content check enters, or a
document nobody could decode. On this repository, measured 2026-08-27:

```
docs-quality WARN | 248 document(s) read; measurable-goal 4, pending-in-approved 2;
                    NO CHECK READS: BRIEF, PLAN, SUMMARY
```

`beadloom ci` runs `doc-spaces` as its sixth step, on the same terms: warn-only, and `WARN`
rather than `PASS` whenever it could not decide.

`sync-check` reports the architecture-document side as `incomplete` rows, which are printed by
name and never block. Both `incomplete` and `exempt` were once absent from the `--json` summary,
so `ok + stale + missing + unverified` did not sum to `total` and a machine consumer reading only
the summary saw neither. `beadloom-mr2l.76` closed that: the summary now carries `exempt` and
`incomplete`, and the verdicts sum to the total as
`ok + stale + missing + unverified + exempt + incomplete`. `unchecked` stays outside that sum on
purpose — it counts NODES that contribute no pair at all, a different population from the pairs
the verdicts describe.

## Related

- [Doc Roots component](../domains/infrastructure/components/doc-roots/DOC.md) — the space
  vocabulary, the `doc_roots` config keys and the two precedence constants.
- [Doc Spaces component](../domains/application/components/doc-spaces/DOC.md) — the TO-BE → AS-IS
  relation, the finding constants and the `docs spaces --json` shape.
- [Sync Check SPEC](../domains/doc-sync/features/sync-check/SPEC.md) — the six verdicts,
  including `exempt`, and where the freshness baseline lives.
- [Doc Templates SPEC](../domains/onboarding/features/doc-templates/SPEC.md) — the composition,
  the placeholder syntax and how required sections are derived.
- [Doc Shape SPEC](../domains/doc-sync/features/doc-shape/SPEC.md) — the majority rule and the
  `incomplete` status.
- [Doc Quality SPEC](../domains/doc-sync/features/doc-quality/SPEC.md) — the five checks, the
  placeholder vocabulary and the per-kind report.
- [Executable Acceptance Scenarios](bdd-scenarios.md) — the criteria these documents reference.
- [Project Overlays](project-overlays.md) — `.beadloom/flow/`, suppressions and the mutation
  scope.
