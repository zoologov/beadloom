# Beadloom Roadmap

> **Current version: 3.0.2** (PyPI, verified on the downloaded wheel 2026-08-30).
> Rewritten 2026-08-31. The previous revision was headed *post-v2.0.0* and had not
> been touched through two major releases: it still listed BDL-061 as unstarted
> P0 work after it shipped as 3.0.0, and named BDL-062 through BDL-066 nowhere.
>
> Pure debt and bugs live in `BDL-UX-Issues.md`. This file answers one question:
> what to do next, and why that and not something else.

---

## Shipped

| Release | What it delivered |
|---|---|
| **v2.0.0** (06-14) | trunk-based, consolidated CI, "governs itself" (component kind + `module-coverage=error`), the configurable tool-agnostic agentic doc-flow + pre-push Gate |
| **v2.1.0** (06-15) | `docs audit` out of experimental and into the Gate; the `reference` doc kind; README positioning |
| **BDL-059** (06-17) | cohesion-driven code-health paydown, six behaviour-preserving slices, no version bump |
| **v2.2.0** (08-20) | interactive architecture and landscape views; typed GraphQL Tier-A; AMQP JSON-Schema bodies; four defects in how the graph was BUILT, fixed at the root (`depends_on` 14 → 156); migration to mcp 2.0 |
| **v3.0.0** (08-26) | **MAJOR.** Flow guards as data with a verdict on every invocation; the false-green residue removed; `CLAUDE.md` composed with a project layer that survives upgrades; executable `@bead:`/`@node:` scenarios; three document spaces; `waves` / `review-brief` / `sync-check --staged` |
| **v3.0.1** (08-27) | `graph_summary_facts` and `doc_area_coherence`; the audit's three populations; **the audit stopped declaring two facts about Beadloom as facts about the adopter's project**; 14 graph corrections; the package description |
| **v3.0.2** (08-27) | the description was fixed in two copies of five — the check read the two it compared and printed the word for all of them |

---

## What is being worked on now

### P0 — the flow cannot see a change's axes, and cannot re-plan when they turn out larger

**Not yet a bead. Needs `/task-init`.** Ranked above the two items below it: this one produces
the work the others check.

**Measured on BDL-067, 2026-08-31 to 2026-09-02.** One bug — "the bootstrap writes a domain with
no `part_of` edge" — became 28 beads, 37 commits and nine review passes. At `5f46c4f`, the last
commit before the documentation wave: 50 files, +12227 / -133 lines. Majors per review pass ran
2, 1, 1, 3, 4, 3, 5, 2, 2 — the count did not decay with the passes. The defect was never one
missing edge: it was a class, *a statement scoped to one shape while a neighbouring shape
exists*, and eight instances of it are named. A comment counting monkeypatch bindings and calling
them branches. A message blaming Beadloom for the adopter's own rules. A withdrawal bound to one
branch of three. A quoted line matching one renderer of three. A post-condition stated per writer
over two writers. A wizard answer that writes two files and leaves through `sys.exit` above the
verdict. An attribution sentence still saying `graph file(s)` after its key had moved to the
NODE. And a reader detector asking for one spelling — `glob` with the literal `"*.yml"` plus
`yaml.safe_load` by name — where five bodies that read the directory spell it otherwise. A ninth
was a document rather than code: one of two twin files carried the superseded detector sentence
after the other was corrected, found by the ninth review and closed in the documentation wave.

Three gaps in the flow produced that, and each is fixable:

**No artifact names the axes a change ranges over.** `/task-init` routed this as `bug`, whose
simplified flow is BRIEF + ACTIVE with no RFC, and the BRIEF template has no section for blast
radius. The question — how many writers of graph nodes, how many branches of `init`, how many
modes, how many renderers — was first asked in fix cycle four, by a bead told to sweep, and
answered in **one pass**: six writers into `.beadloom/_graph/`, two of which create nodes. Asked at
intake, the first dev bead would have been written over both writers and the fourth review pass
would not have existed.

**Nothing re-plans a work item whose type stops being true.** By the second fix cycle this was
not a bug, and 23 beads lived under a document that still describes one missing edge. At the
fourth review pass the approved BRIEF's own acceptance criterion was **measured false** for
`--mode both`, and nothing re-opened the document for approval.

**Nothing turns a repeated defect into a sweep.** The rule *second instance of a class → the next
bead's deliverable is the sweep, not the fix* was applied first in cycle three and paid
immediately; the consolidation in cycle five is what finally moved the review count down with a
diagnosis attached rather than by luck.

**The tool: `beadloom impact`.** `why` answers dependencies between graph nodes. Nothing answers
*who else writes this file, who else calls this function, how many branches does this command
have, how many ways does it terminate*. Those three questions are what the whole epic turned out
to be. `beadloom waves` already does the analogous job for a set of beads, so the shape is known.

**The constraint that decides whether this helps or harms: `impact` is NOT `why` at a new name.**
`why` walks `part_of` / `depends_on` between graph nodes, and **not one axis this epic needed is a
fact of the graph** — which functions write into `.beadloom/_graph/`, how many branches `init` has
and how many ways it terminates, how many modes and renderers, which functions parse YAML and under
what policy. Every one of those lives *inside* a single node. An `impact` built as a graph walk
would answer confidently and miss all of them, which is a green describing the checker's ignorance —
the class this project exists to remove, shipped as a feature. **Axes come from the source (AST);
the graph supplies the boundary** — which domain a found call site belongs to, and therefore when a
change crosses out of one. That boundary is what made BDL-UX #220 legible at all: its readers sit in
four different domains, and without the graph that finding is a flat list of files.

**Three working prototypes already exist, written as tests inside BDL-067**, which is most of why
this is cheaper than it looks: `tests/test_init_branches_that_reach_the_bootstrap.py` (30 cases)
derives `init`'s writing branches from `init`'s own source; `tests/test_one_parent_post_condition_over_every_writer.py`
(25) derives the graph writers by shape; `tests/test_graph_files_are_read_under_one_policy.py` (15)
derives the readers as a shape — *lists a directory and parses YAML* — over six listing verbs and
six loaders, with five evasion spellings measured and closed. Lifting those out of the suite into a
command is the bulk of the work.

**The role: `Explore` given a protocol, positioned inside `/task-init` as step 0.5.** It is the
only role in this flow with no file in `.claude/agents/`, and the one time this epic used it, it
returned an excellent trace of the defect and nothing about axes — because nobody had written
down what its deliverable is. A role exists so the coordinator's prompt stops mattering, and this
one has no such guarantee today. The coordinator cannot produce the artifact itself at any point,
now or later: it is barred from reading source by the context boundary.

Three conditions on that role, because this project has shipped a duty without a check before —
BDL-061 S4 put mutation testing into every role core and no runner with it, and four beads in
BDL-067 then reported four different hand methods as prose:

- it runs **inside** `/task-init`, before the type is chosen, because the axis count is what says
  whether a work item is a bug;
- its deliverable is a fixed `## Axes` section — writers, callers, branches, modes, renderers,
  with paths and lines, derived from source — not a narrative;
- an absent or empty `## Axes` section is a `docs quality` finding, the way `missing_sections`
  already reports a document missing a section its peers carry.

**Advice is not a gate, and this project has three measured proofs of it.** A section the Gate can
see missing is the cheap half. The half that makes `impact` an instrument rather than a
recommendation is the second check: **a change that touches a call site outside the declared axes is
a finding.** The machinery exists — `sync-check --staged` and the commit-scoped hook already judge a
commit by its paths. Without it, the axes are a prompt input, and this repository has watched a
prompt input be ignored or routed around three times: the mutation duty shipped into every role core
with no runner (BDL-061 S4), the review's withholding defeated through `ACTIVE.md` (#212) and then
through commit bodies (#219). Each was correct as written and none of them held.

**Recall over precision, and the tool must name what it could not determine.** A narrowing tool that
errs small is more dangerous than no tool. Today an agent that does not know the boundary reads
widely and sometimes stumbles onto the neighbouring shape — that is how several of BDL-067's
findings surfaced. Given a declared axes list, it will trust it and stop, so the failure mode
inverts from ignorance to false confidence. The derivation must therefore report the population it
could not resolve — an unparseable module, a dynamic dispatch, a call through a variable — as part
of the answer rather than omitting it. `rule_liveness` and BDL-UX #215 are the same lesson already
paid for here: an instrument that measures its own scope and reads as answering the question.

**Validate it against BDL-067 before building it.** The three AST derivations already exist. Run
them retroactively against the tree as it stood at the first dev bead on 2026-08-31 and ask one
question: would they have listed **both** writers of graph nodes and **three** entry points of
`init`? If yes, the feature is justified by a measurement rather than by an argument. If no, that is
known in an hour instead of a sprint. This project asks that of every claim it reviews; the claim
that this feature would have prevented BDL-067 is currently unmeasured, and it is the whole case
for ranking it first.

**Done when** a work item cannot reach its first dev bead without an `## Axes` section the Gate
can see, a second ISSUES verdict on one work item forces a recorded re-plan rather than another
fix cycle, and `beadloom impact` answers the three questions above from the source rather than
from a human's recollection.

### P0 — nothing can check the mutation duty this project ships

**Not yet a bead. Needs `/task-init`.** Ranked first: the item below it is in flight and
closing, this one has not started.

BDL-061 S4 (`beadloom-mr2l.13`) put a mutation-testing **duty** into every composed role
core, on the stated ground that owning a runner would break tool-agnosticism. So the
convention shipped and the enforcement did not. Nothing in this repository can tell a
performed mutation check from a sentence claiming one.

**The case is measured, this week, on this branch.** BDL-067 ran five review passes over
`init`. In the fourth, `beadloom init --yes --mode both` exited 0 over a graph that
`lint --strict` then failed on three counts — #192's own signature, still live — while
**112 tests across the epic's seven files passed and none of them could see it**. Four
beads in that epic each reported doing "mutation checking", by four different hand methods,
and every result exists only as prose in a bead comment. One of those beads, sent to audit
another, found that a reported "all 20 assertions red before the fix" was eleven guards
that cannot fail.

A suite that cannot fail is the thing this project exists to detect, and it is currently
detected by a person reading bead comments.

**The tool is decided: `mutmut`.** Researched 2026-09-01 against `cosmic-ray`,
`pytest-gremlins`, `poodle`, `mutatest`, `MutPy` and `mutahunter`. The deciding property is
per-mutant test selection from coverage, which only `mutmut` and `pytest-gremlins` have:
mutation cost is mutants × time-per-run, and on a 215-second suite over `graph/rules/`
(4 465 code lines, order 2 000–4 000 mutants) selection is what separates ninety minutes
from a week. `cosmic-ray` runs the configured `test-command` for every mutant and answers
cost with horizontal distribution — which this project already declined once, when
`beadloom-mr2l.64` withdrew `tests-windows` over runner minutes. `pytest-gremlins` is
architecturally the most advanced of the four and far too young for a gate (51 stars,
v1.9.0), and its published benchmark is a synthetic project on which its sequential mode is
slower than `mutmut`.

Worth recording because it nearly propagated: three separate sources justify themselves by
calling `mutmut` unmaintained — including a peer-reviewed paper stating "last commits 2–6
years ago" and "460K downloads, far exceeding alternatives". `mutmut` released 3.7.0 on
2026-07-31 and takes 4.4M downloads a month; 460K is `cosmic-ray`'s own figure. The claim
reads as a measurement and is not one.

**First slice: `graph/rules/` only.** Eleven modules, the rule evaluation and liveness
logic. It is where a false green costs most — if `evaluators.py` lets a violation through,
the whole Gate is theatre — and it is deterministic branch-and-comparison code, which is
what the standard operator set is strongest against. Explicitly out of scope: `services/`,
`tui/`, `ai_agents/`, `infrastructure/`, and message-rendering code anywhere. BDL-067 found
four defects in user-facing message text; mutation would have caught none of them, because
one string substituted for another is equivalent almost always.

**Two conditions that would overturn this**, stated now so the decision can be lost rather
than defended: the first slice producing incomplete results from `mutmut` — the one
reproduced finding against it in the literature — or `pytest-gremlins` publishing a
reproducible benchmark on a real codebase.

**Done when** a mutation score is produced by a command in CI rather than asserted in a
bead comment, and a declared mutation target outside the configured source paths is
reported rather than silently scoring zero.

### P0 — A virgin `beadloom init` leaves the Gate red — CLOSED on the branch, not yet merged

**`beadloom-e8s4` · BDL-UX #192 · the adopter-facing blocker.**

`beadloom init --yes --mode bootstrap` exited 0 and then failed its own `beadloom ci`
on `domain-needs-parent` — a rule the same command wrote one step earlier. The
bootstrap wrote a domain with no `part_of` edge.

It was not new and it had never been measured, because everything measured here runs
on a repository whose graph has been hand-authored since BDL-008. It was found by
verifying the 3.0.0 wheel against a project that is not us.

**Why it outranked everything below:** Beadloom is about to be installed on a
microservice landscape and on a second private project by people who did not
write it. The first command they ran left the Gate red.

**State on `features/BDL-067`.** Both halves shipped. The INSTANCE: both writers of
graph nodes hold one post-condition and one function that computes the edges they are
short of, so no domain is written without a `part_of` edge. The CLASS: every entry
point of `init` that writes a file under `.beadloom/_graph/` re-indexes and then runs
the Gate's own `lint_step` over the project, and exits 1 rather than reporting success
over a graph that fails the rules beside it. Measured over eight (entry point x mode)
cells derived from `init`'s own source — four entry points (`--yes`, `--bootstrap`,
`--import`, the wizard) and three modes — on fixtures that are not this repository.
Two paths take no verdict and both are stated: a run that changed nothing under
`.beadloom/_graph/`, and the wizard's `edit` answer, which hands the graph over to be
edited by hand.

**What this epic did NOT close, ranked below as its own item:** `init` still ends in a
Python traceback on a graph file it cannot handle (BDL-UX #220, `beadloom-l22o`), and
still writes two nodes under one `ref_id` on the classic Python `src/<project>/`
layout (BDL-UX #214, `beadloom-7c6k`). Nine review passes were needed to get here, and
eight of the defects they found were one sentence true of one shape while a
neighbouring shape existed — which is the argument for the axes artifact ranked above
this item, not a separate observation.

### P1 — BDL-066: agent behaviour observability, trace and result

Docs drafted 2026-08-31, `Status: Draft`, beads not created.
`.claude/development/docs/features/BDL-066/`.

The owner sees the conversation with the coordinator and nothing of what the
coordinator tells its subagents. On 2026-08-27 a brief carried five constraints,
one of which locked the headings of a document the owner had spent a day
arranging to have rewritten. It lived entirely inside a prompt he never saw.

Seven slices. **S0 needs no event store at all** — it reads the tracker and asks
whether a wave passed through separate roles, which is the check that would have
caught a session on another project silently dropping to single-agent mode where
the reviewer was the author.

Everything here raises detectability and none of it prevents. Any shipped text
claiming otherwise is a defect.

### P2 — Qwen as the writer of Russian documentation, and the style guide

Two beads, one thread.

**`beadloom-cxal` · BDL-063 — speech style guide for all four roles.** Shipped as
data, not prose in a role file, because it must reach a Claude adapter, a Goose
recipe and a machine check. Configurable per project. Target 3.1.0: editing a
CORE role template changes what `setup-agentic-flow` composes in every adopter's
repository.

**BDL-065 — Goose+Qwen as the tech-writer role, local and optional.** The mechanism is a
**role runtime**: `flow.yml` names which executor runs a role, defaulting to the harness. Measured
2026-08-31: Qwen rewrote all 14 sections of the multi-agent guide and the owner
judged the result clearly better — "небо и земля". Two findings from that run
belong in the bead: the endpoint drops long generations unless `stream: true`,
and invariants have to be pinned by the harness rather than by the prompt (a free
prompt renamed all 14 headings, which was wanted, and lost a code block in one
section, which was not).

Not yet a bead of its own beyond the guide work. **Needs `/task-init`.**

### P3 — BDL-060 S5/S6: federation

Nine open beads, all P2, untouched since August.

**S5** — live cross-repo `ctx`: an agent on service A sees `@repo-B:CONTRACT`.
The F1 honesty debt: the claimed metric is not actually met, cross-repo identity
lives only in `export`/`federate` and not in bundles.

**S6** — `unverified` lifecycle, the undeclared sweep, review-gated bootstrap.

Federation is the stated top priority of the product vision and it has not moved
in three weeks. Either it becomes active work or this ranking is wrong. Recorded
so the contradiction is visible rather than quiet.

---

## Tech debt — BDL-061 tails, closed in the tracker on 2026-08-31

BDL-061 shipped as 3.0.0. Sixteen of its beads were unfinished work rather than
residue — four were checked and three were still live — so they were closed with
the record kept here and the detail readable through `bd show <id>`.

| Bead | What is left |
|---|---|
| `mr2l.41` | three more ambient-decode sites, plus an MCP test runner with no timeout |
| `mr2l.51` | three modules past 1000 lines with several responsibilities each |
| `mr2l.52` | read-only `lint` never says the index is older than the tree |
| `mr2l.53` | `rule_type_count` is registered and verified, but still counts rules while its name says rule types |
| `mr2l.60` | **P1 bug** — the backslash refusal makes the flow guard refuse every edit on Windows, and its stated reason is false there |
| `mr2l.61` | fifteen tests skip on Linux that do not skip on macOS |
| `mr2l.67` | the decode sweep: 29 narrow handlers, 49 unguarded decoding reads |
| `mr2l.69` | the shared writing standard names `beadloom lint` where the checks live in `docs quality` |
| `mr2l.71` | a closed epic's goal cannot be made measurable retroactively |
| `mr2l.72` | ROADMAP and issue-log document KINDS, with counts the tool computes rather than a human tallies. **A concrete instance found on 2026-08-31:** `tests/test_bead77_kind_and_root_disagree.py` pins the TO-BE population as a literal and has been hand-edited once per feature — 190, then 194, then 198. Every feature that writes a PRD reddens CI until someone updates the number by hand |
| `mr2l.81` | the commit gate cannot see a neighbour's hunk inside a file the committer touched |
| `mr2l.82` | the commit-scoped hook type-checks a surface the project never declared typed |
| `mr2l.88` | an ignore block keeps the pre-rotation pattern |
| `mr2l.89` | MCP `mark_synced` still attests a whole ref, one layer above the CLI fix |
| `mr2l.91` | the UX log has two issues numbered 187 — both still present |
| `mr2l.92` | the guard read-only test accuses the guard when `bd` flushes its own export |

**One of them is about this document.** `mr2l.72` would make a ROADMAP and an
issue log first-class kinds whose counts the tool computes. Until it lands, this
file stays current only by hand — which is exactly how it fell two majors behind.

**And a finding from the cleanup itself.** `mr2l.19` and `mr2l.20` are closed.
`.20`'s deliverable was *"ROADMAP/BDL-UX restructured"* and it was not, and `.19`
reviewed it against the criterion *"our ROADMAP and issue log validate as
instances"* and passed. Two beads closed over a deliverable that visibly does not
exist. Recorded rather than reopened, because the work is being done here.

---

## Standing debt outside the epics

| Bead | What |
|---|---|
| `beadloom-iur5` | **P1** — the vendored agents snapshot is the #177 loop, one direction short of closed |
| `beadloom-uxqc` | **P1** — `doctor` should audit the PRODUCED graph, not just the code: islands, unexplained nodes |
| `beadloom-9glj` | `sync-update` can re-attest a doc nobody read |
| `beadloom-431c` | `docs audit` checks numbers but never that a documented identifier still exists |
| `beadloom-1d70` | no signal for a bounded context too large by SUBTREE |
| `beadloom-2qwb` | centralize remaining inline node-reads |
| `beadloom-g0c5` | `test_tui.py` connection leak during textual GC |
| `beadloom-ec1a` | `config-check` does not flag ORPHANED tool adapters |
| `beadloom-l2f2` | the beads git-hook prints a remediation command that does not exist |

Two findings were checked on 2026-08-31 and are **still live**: BDL-UX **#147**
(`beadloom lint` mutates the index — a read-only-sounding verb writes to the
database) and **#160** (AsyncAPI extraction has zero callers outside its own
module, while the federation SPEC states teams on AsyncAPI ingest through it).

---

## Vision and the rule that ranks this list

Beadloom is an honest, effective tool. Market reach and outside adoption are not
goals. Two uses rank everything:

- **Solo multi-agent flow** — Claude Code + Beadloom + Beads + GitHub. Building
  large projects alone with an AI fleet.
- **A team of solos** — each member runs that flow on their own service, all
  federated into one landscape.

Every P0/P1 item must serve one of them. Items serving only adoption or market
are demoted and flagged off-north-star.

**Sequencing principles that still hold:** one end-to-end thread at a time, made
honest before the next · honest is not complete, and dogfood is acceptance · a
published lie is worse than a missing feature · intent-vs-reality is the moat,
context bundles are commoditising · federation multiplies dishonesty by N repos,
so single-repo honesty is a prerequisite · CI is the only true enforcement point ·
top-tier models, no tiering by role.

---

## Backlog — deferred, not ranked in the list above (serves "b")

- **Ownership from CODEOWNERS + drift-check.** `owner`/`team` derived from CODEOWNERS/git-blame (not a rotting `catalog-info.yaml`); owner-vs-reality detection. Answers "who to call when a contract breaks." _REVIEW-2 §6.2._
- **PR-bot / GitHub App.** Inline comment: "edge X→Y violates a layer rule" / "contract Z became BREAKING for @backend". Pairs with F4.1. _REVIEW-2 §5, REVIEW §6.3._
- **REST/OpenAPI contract source.** The most-requested deferred contract type. _F1 §8, STRATEGY-3 F2._
- **Federation-MCP server.** Neighbouring-service/contract context to an agent via MCP. _REVIEW-2 §5._
- **Blast radius:** `beadloom why <contract> --landscape` — who breaks across all repos. _REVIEW-2 §5._
- **Arch/governance scorecard.** Per-service readiness from existing inputs (lint/debt/doc-freshness/verdicts/cycles). Do NOT pull in Sonar/PagerDuty/SLO. _REVIEW-2 §6.2._
- **Architecture drift over time (decay report)** on top of snapshot+metrics_history. _REVIEW-2 §5._
- **Auto-bootstrap graph from code (finish the WIP)** — hybrid "inferred + intent layer", tied to `unverified`. _REVIEW-2 §5._
- **Schema-migration framework (versioned)** — currently ad-hoc bumps. _STRATEGY-2 Ph15.2._

---

## Off-north-star — raise only on a concrete need

> Serve adoption/market or hygiene, not (a)/(b) directly. Raise only if a concrete need appears.

- **Import intent from import-linter/ArchUnit/dependency-cruiser** (lower the manual-YAML barrier). _REVIEW §6.6._
- **Guides & demos** (onboarding/multi-agent/keep-docs-alive + demo). _STRATEGY-1/2 Ph7._
- **Semantic search** (sqlite-vec/fastembed) — only at scale (1000+ nodes). _STRATEGY-2 Ph14._
- **Semantic docs audit** — the `docs audit` detector is still English-keyword-proximity based (`doc_sync/audit.py`), so it mislabels numbers semantically (e.g. "12 supported languages" → `language_count`; the `.ru` "14 инструментов" → `cli_command_count`). BDL-057 shipped a *workaround*, not a fix: `docs_audit.ignore` triples + per-fact tolerances in `.beadloom/config.yml` (**6 suppressions**, measured 2026-08-31 — the figure this document carried, 15, was hand-written and wrong, which is the argument for `mr2l.72`) silence specific instances.

  Three measured instances make the shape concrete: **#205** — a factually *correct* number binds to a fact computing something else ("supports 11 languages" → `language_count`, which is the number of languages the project is *written in*, 1); **#206** — `docs/**/features/*/SPEC.md` is excluded from the audit outright, so three references to a release that did not exist survived there; **#209** — the English-*word* half of the keyword table is dead in a non-English document, while Latin-script tokens and the version regex still bind, so one page is checked and its neighbour is not with nothing distinguishing them. A true fix needs semantic classification. _STRATEGY-2 Ph14.8; workaround landed BDL-057._
- **Misc (market/hygiene/on-demand):** publish GH Action to marketplace · VS Code extension · gRPC/AsyncAPI/proto sources · monorepo workspace · richer-viz beyond P1 · TUI graph view / ASCII graph · plugin system · daemon · pre-commit-framework hook · Bitbucket recipes · property-based tests · perf benchmarks · re-export resolution · CLI "did-you-mean" · code similarity · data-ownership/ER · cross-system user-flow · per-system C4 decomposition · remote graph refs / full federation protocol.

---

## Historical — the BDL-059 debt registry (June 2026, all shipped)

> Kept as the record of what that epic closed. It is not forward-looking work and it is
> duplicated in `BDL-UX-Issues.md`. Nothing here needs doing.

> Pure debt/bugs live in BDL-UX-Issues.md. **The whole Code + Tests block below is ✅ RESOLVED by BDL-059 (#20–#25, 2026-06-17)** — it was the "close the growth-gating debt before the next product step" epic. Kept here (struck through) as the registry of what shipped.

**Code (REVIEW-2 §2) — ✅ RESOLVED (BDL-059):**
- ~~**[HIGH] Repository layer + connection context-managers.**~~ **DONE (S2, #22)** — `infrastructure/repository.py` (typed reads, 16× `SELECT … FROM nodes` centralized) + `infrastructure/db.py::connection()` CM; `tui/` re-layered through `application/graph_reads.py` (no raw SQLite in presentation). _Closes BDL-UX #122._
- ~~**[HIGH] N+1 in `doc_sync/engine.py` `check_source_coverage`** + non-indexable `LIKE`.~~ **DONE (S2, #22)** — set-based prefetch + indexable `json_each`; golden parity. _Closes #123._
- ~~**[MEDIUM] Cycle detection — no global visited, O(n) `neighbor in path`.**~~ **DONE (S3, #23)** — WHITE/GREY/BLACK + path-as-set in `graph/rules/cycles.py`; golden byte-parity. _Closes #124._
- ~~**[MEDIUM] Split god-domain `graph/` (federation + rules).**~~ **DONE (S3, #23)** — `graph/rules/` + `graph/federation/` packages by cohesion. The graph `domain-size-limit` warning resolved by recalibrating the limit 200→280 (documented; an in-domain split can't lower the count — recalibration, not gaming). _Closes #125._
- ~~**[MEDIUM] God-functions (`cli:status` → application, scanner/reindex).**~~ **DONE (S4, #24)** — `cli:status`→`application/status.py`; `cli`/`scanner`/`reindex`/`debt_report`/`site_dashboard` monoliths → cohesive packages. _Closes #126._
- ~~**[LOW] `Any` concentration in onboarding; exception swallowing.**~~ **DONE (S5, #25 + earlier BDL-047)** — onboarding `TypedDict` (`scanner/types.py`); `git_activity` except narrowed. _Closes #127._
- ~~**[P2-debt] Context cache not wired into `build_context`.**~~ **DONE (S5, #25)** — `build_context` routes through `SqliteCache` (transparent). _Closes #128._

**Tests (REVIEW-2 §3 / REVIEW §4.3) — ✅ RESOLVED (BDL-059 S1, #21):** `pytest-randomly` added (exposed + fixed latent live-DB order-dependence via the session `live_repo_reindexed` fixture); conftest yield/finally db fixtures (ResourceWarnings); grammar-guard test (FAILS-not-skips when grammars absent, gated in CI); tests decoupled from production internals. _Closes #129._

**Docs (REVIEW-2 §4) — ✅ RESOLVED (BDL-057 + v2.1.0 release).** The rule-type
dataclass-name contradiction (#130) was fixed by the BDL-057 SPEC-fill (`architecture.md`
now uses the real YAML keys, matching the dispatch); the v2.1.0 release fixed the remaining
nits (#131): the non-existent `--non-interactive` flag in `getting-started.md`, the DDD
domain-count miscount in `architecture.md`, and the `CONTRIBUTING.md` `your-org` placeholder +
missing release-process section. The class of *fact* staleness is now caught by `docs audit`
in the Gate (so these can't silently rot again); the *classifier* weakness remains the P3
"Semantic docs audit" item above.

---

## Won't do (anti-scope)

- Built-in LLM / bundled weights (F4.1 = external model only).
- **Model tiering** — the same job on a cheaper model, to save cost. Principle 10:
  quality across every role is the goal, and downgrading risks drift and coverage gaps.
  Still live and now **checkable**: every role file declares `model: opus`, the launch
  can override it, and nothing compares the two. BDL-066 turns that into a check.

  **Not the same thing as a role runtime.** Tiering is *the same requirement, a cheaper
  model*. A role runtime is *a different requirement, a different executor* — declared in
  `flow.yml` and verified, not chosen silently to save money:

  ```yaml
  roles:
    tech-writer:
      runtime: goose        # default: the harness itself
  ```

  The Russian documentation case is the first instance: Qwen was chosen because its
  Russian is better for this audience, measured by the owner over three sections and
  then the whole guide, and it costs more attention rather than less.
- Live web app / SaaS hub (the portal is static, CI-generated; federation is a pull-based CI pattern).
- Plugin marketplace.
- DSL/OPA-Rego rules; autofix patches; Slack/Discord; a separate cross-reference report (covered by `why`).
- **Backstage replacement** — instead, **feed Backstage** (emit `catalog-info.yaml`).
- Full bootstrap-accuracy upfront; C# (no dogfood); pattern detection (LLMs do it better); dependency-weight analysis.

---

## Close formally — done, kept as the record

All three were verified complete on 2026-08-31 and need no further action.

- **`sync-update --auto` + `llm:` config** — built then removed in v0.6, replaced by
  agent-native MCP write tools. No occurrence remains in `docs/` or `src/`.
- **`init --scope`** — specified but never built, and the decision was not to build it.
  No occurrence remains outside the unrelated `graph --scope` flag.
- **`BACKLOG.md`** — superseded by this file. The file is gone.
