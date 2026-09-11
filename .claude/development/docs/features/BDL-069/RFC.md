# RFC: BDL-069 — The checks an adopter meets first, and the populations they run over

> **Status:** Approved
> **Created:** 2026-09-10

---

## Overview

Four defects, one shape: a check reports on a population that is empty, partial, or unnamed.
Two of them are reached by the first two commands an outside user runs, and they are what
stands between this project and the outside validation it is ready for.

## Motivation

### Problem

Stated with its measurements in the PRD. In one line each:

- `init` writes documents that fail the freshness rule `init` installs, and the remediation the
  failure prints re-baselines hashes while the reason is about content;
- `init` writes two nodes with one `ref_id`, the loader keeps one, the discarded one carries
  the adopter's source, and the resulting green comes from the loss;
- the project's version is stated in nine places and checked by three instruments over disjoint
  populations, two places by nothing;
- nothing compares the declared README pair.

### Solution

Four independent changes, sharing one principle already shipped in 4.0.0: **a check states the
population it ran over**. Three of the four are about making an existing check name what it did
not cover; one adds a check that does not exist.

## Technical Context

### Constraints

- **`beadloom impact` reads Python.** Four of the nine version-stating surfaces come back
  `unreadable-target` — `.beadloom/_graph/beadloom.yml`, `docs/services/cli.md`,
  `CHANGELOG.md`, `.claude/development/ROADMAP.md` — and `.claude/CLAUDE.md` was not run for
  the same reason. The version work cannot be built on `impact`; it needs its own reader.
- **`.beadloom/_graph/` has seven readers, not one.** `graph_files.each_graph_file` is declared
  as the single policy, and a grep found six other bodies reading the directory directly:
  `graph/loader.py:186,283`, `graph/diff.py:220`, `reindex/change_detection.py:89`,
  `reindex/indexing.py:62`, `services/commands/index_ops.py:235`,
  `services/commands/setup.py:967`. Reporting a duplicate `ref_id` in one place will not reach
  the readers that do not go through the policy. **This is a grep result and not a derivation**
  — `beadloom impact` produced no axis naming the split, and the RFC says so rather than
  presenting it as derived.
- **Six writers into that directory, two of which emit node dicts** — `bootstrap.py:94,119,140,175`
  and `doc_classify.py:135`. The count matches what BDL-067 measured; it was re-measured rather
  than repeated.
- **A room is not a checkout.** Any test for the `init` path has to build a project that is not
  this repository; this repository's own arrangement hides both adopter defects, which is why
  they were found on the published wheel and not here.
- Stack and quality standards are this project's own, copied into CONTEXT rather than restated
  here.

### Affected Areas

The twelve nodes ruled in scope, from the axes below: `doc-generator`, `ci-gate`, `sync-check`,
`agent-prime`, `graph-loader`, `graph-files`, `docs-audit`, `doc-sync`, `doctor`, `rule-engine`,
`markdown-tables`, `issue-numbers`, `cli-commands`, and — re-ruled as the work landed — `reindex`,
`graph-diff` and `onboarding`. Sixteen.

## Axes

> **Derived by:** `beadloom impact` over eighteen targets in four Explore runs, one run per
> defect; every target is named in the per-run blocks below
> **Seed:** multiple, and they differ per run — `write_yaml_atomic`, `each_graph_file`,
> `read_declared_docs`, `flow_signature`, `persist_flow_config`, `update_node_in_yaml` under
> rule `reaches-an-effect-sink`, and `none` for nine of the eighteen targets, whose axes are
> therefore unresolved rather than empty. One line cannot carry four runs; the per-run blocks
> below carry them and this line says so rather than averaging them.
> **Unresolved:** per run, in the blocks below. Across all four: no module failed to parse, and
> five surfaces came back `unreadable-target` because `beadloom impact` reads Python —
> `.beadloom/_graph/beadloom.yml`, `docs/services/cli.md`, `CHANGELOG.md`,
> `.claude/development/ROADMAP.md`, and `README.ru.md`.

| Axis | Node | Sites | In scope | Why |
|------|------|-------|----------|-----|
| co-writers | doc-generator | 2 — `src/beadloom/onboarding/doc_generator.py:28` | yes | writes the skeleton that fails the rule, and reaches the graph directory |
| co-writers | doc-sync | 1 — `src/beadloom/doc_sync/surface.py:199` | yes | holds the freshness surface and the version subjects |
| co-writers | agent-prime | 4 — `src/beadloom/onboarding/scanner/bootstrap.py:36` | yes | one of the two bodies that emit node dicts |
| co-writers | graph-loader | 1 — `src/beadloom/graph/loader.py:171` | yes | the reduction happens here and is not reported |
| callers | ci-gate | 1 — `src/beadloom/application/gate.py:349` | yes | builds the remediation at `gate.py:1211`; hosts the new leg |
| callers | sync-check | 3 — `src/beadloom/doc_sync/engine.py:1491` | yes | `missing_modules` is decided here |
| callers | cli-commands | 6 — `src/beadloom/services/commands/docsync.py:67` | yes | `sync-update` must report what it did not clear (Q1) |
| callers | graph-files | 1 — `src/beadloom/onboarding/graph_files.py:72` | yes | the declared policy, and it reaches one reader of seven |
| callers | docs-audit | 1 — `src/beadloom/doc_sync/audit.py:606` | yes | one of the three checkers of the version |
| callers | doctor | 2 — `src/beadloom/application/doctor.py:188` | yes | the second checker, over `CLAUDE.md` |
| callers | rule-engine | 5 — `src/beadloom/graph/rules/__init__.py:171` | yes | the third, `summary_facts` over the graph node |
| callers | markdown-tables | 4 — `src/beadloom/doc_sync/tables.py` | yes | already reads a document as blocks; the comparison reuses it |
| callers | issue-numbers | 2 — `src/beadloom/doc_sync/issue_numbers.py:100` | yes | the precedent for an opt-in pair declared in config |
| callers | mcp-server | 1–4 | no | caller of the surfaces; blast radius, not a defect site |
| callers | reindex | 1–4 | **yes** | **re-ruled after wave 1.** `reindex/indexing.py` parses nodes, so routing it through the policy was BEAD-05's own assignment. Ruled `no` at planning as blast radius; that was wrong, and `scope-check` is what said so |
| callers | graph-diff | 1–2 | **yes** | **re-ruled after wave 1**, for the same reason as `reindex`. It reads at a git ref AND parses what it reads, so it is inside the policy's real population |
| callers | tui | 1 | no | display only |
| callers | application | 1 | no | consumes the subject vocabulary for another question |
| callers | bd-seam | 5 | no | consumes the subject vocabulary for another question |
| callers | doc-spaces | 1 | no | consumes the subject vocabulary for another question |
| callers | flow-suppression | 2 | no | consumes the subject vocabulary for another question |
| callers | onboarding | 2 | **yes** | **re-ruled after `qylh` landed.** The skeleton text lives in `onboarding/templates/docs/core/{domain,service,feature}.md.txt`, not only in `doc_generator.py`; naming the modules meant editing the templates. Ruled `no` at planning because the node surfaced as a reader of the manifest; it is also the owner of the templates the fix had to reach |
| callers | declared-scope | 1 | no | consumes `summary_facts` for another question |
| callers | scope-check | 1 | no | consumes `summary_facts` for another question |
| callers | axes-section | 1 | no | caller of the block reader; constrains its signature |
| callers | planning-report | 1 | no | caller of the block reader |
| callers | doc-quality | 2 | no | caller of the block reader |
| callers | work-item-routing | 1 | no | caller of the block reader |
| callers | flow-guards | 4 | no | gate blast radius |
| callers | wave-plan | 1–2 | no | gate blast radius |
| co-writers | graph-layout | 1 | no | writes the directory but emits no nodes |
| co-writers | agentic-flow-setup | 1 | no | writes the directory but emits no nodes |
| callers | doc-shape | 3 | no | reads sections, not blocks — a different granularity |
| callers | graph | 1 | no | reader downstream of the loss |

**Two rows were re-ruled on 2026-09-11, after wave 1 landed.** `reindex` and `graph-diff`
were ruled out of scope at planning as blast radius — readers downstream of the defect that
would inherit the fix. BEAD-05's measurement showed both parse nodes, which put them inside
the policy's real population and made touching them the assignment rather than an overrun.
`beadloom ci`'s `scope-check` leg reported the disagreement between the approved axes and
what landed, which is the leg working. The ruling is corrected here rather than quietly,
and the count of nodes in scope moves from thirteen to fifteen.

**A third row was re-ruled on 2026-09-11, when `qylh` landed.** `onboarding` had surfaced in the
axes as a reader of the manifest and was ruled out; the skeleton text `qylh` had to change lives
in that node's templates. Three re-rulings in one epic, all in the same direction — nodes marked
blast radius that turned out to be work sites — is itself worth recording: the planning ruling
read each node by the axis it FIRST appeared under, and a node that appears as a caller can also
own the thing the fix must reach.

The rows above are the **node level**. The per-function `branches` rows of the eighteen
sections are omitted for length and are reproducible verbatim by re-running the commands each
block below names — that omission is a decision, and it is stated rather than silent.

### BDL-UX #282 — the skeletons and the remediation

> **Derived by:** `beadloom impact generate_skeletons`, `check_doc_coverage`, `sync_update`,
> `_sync_finding` over `src/beadloom`
> **Seed:** `each_graph_file` (`reads-a-yaml-directory`), `write_yaml_atomic` and
> `flow_signature` (`serialises-yaml`), `read_declared_docs` (`reads-a-yaml-directory`), under
> rule `reaches-an-effect-sink`
> **Unresolved:** across the four runs — 9, 15, 43 and 75 unresolved names by kind
> (`unresolved-terminator-name`, `name-defined-more-than-once`, `dynamic-dispatch`). No module
> failed to parse. The defect's third observation — each stale pair reported twice — was given
> no target of its own, so **no section covers it**.

| Axis | Node | Sites | In scope | Why |
|------|------|-------|----------|-----|
| co-writers | doc-generator | 2 — `src/beadloom/onboarding/doc_generator.py:28` | yes | writes the skeleton that fails the rule |
| co-writers | doc-sync | 1 — `src/beadloom/doc_sync/surface.py:199` | yes | holds the freshness surface the skeleton is judged against |
| callers | ci-gate | 1 — `src/beadloom/application/gate.py:349` | yes | builds the remediation string at `gate.py:1211` |
| branches | sync-check | `check_doc_coverage`, `_missing_side`, `_unchecked_reason` in `doc_sync/engine.py` | yes | `missing_modules` is decided here and must say what clears it |
| co-writers | agent-prime | 4 — `src/beadloom/onboarding/scanner/bootstrap.py:36` | no | writes the graph, not the documents; covered under #214 |
| callers | cli-commands | 6 — `src/beadloom/services/commands/docsync.py:67` | yes | Q1 decided: `sync-update` reports over the population it attested and says nothing about the one it left stale |
| callers | mcp-server, tui, doctor, graph-diff, reindex, application | 1–4 each | no | callers of the freshness surface; blast radius, not defect sites |

### BDL-UX #214 — one ref_id, two nodes

> **Derived by:** `beadloom impact` over `scanner/bootstrap.py`, `graph/loader.py`,
> `scanner/doc_classify.py`, `onboarding/graph_files.py`, `reindex/indexing.py`,
> `reindex/change_detection.py`, `graph/diff.py`, `commands/index_ops.py`, `_graph_files_now`
> **Seed:** `write_yaml_atomic`, `each_graph_file`, `read_declared_docs`, `flow_signature`,
> `persist_flow_config`, `update_node_in_yaml`, under rule `reaches-an-effect-sink`
> **Unresolved:** 20, 9, 5, 2, 12, 5, 6, 15 and 48 names by kind across the nine runs. **No
> surface failed to parse and none was unreachable**; `impact` exited 0 on all nine and on three
> further targets probed for reachability that produced no section.

| Axis | Node | Sites | In scope | Why |
|------|------|-------|----------|-----|
| co-writers | agent-prime | 4 — `src/beadloom/onboarding/scanner/bootstrap.py:36` | yes | one of the two bodies that emit node dicts |
| co-writers | graph-loader | 1 — `src/beadloom/graph/loader.py:171` | yes | the reduction happens here and is not reported |
| callers | graph-files | 1 — `src/beadloom/onboarding/graph_files.py:72` | yes | the declared policy; where a report belongs, and it reaches only one of seven readers |
| co-writers | doc-generator | 1 — `src/beadloom/onboarding/doc_generator.py:513` | yes | `doc_classify.py:135` is the second node emitter and reaches the directory through this node |
| callers | rule-engine | 11 — `src/beadloom/graph/rules/evaluators.py:85` | no | consumes the loaded graph; it reported the empty population correctly |
| co-writers | graph-layout, agentic-flow-setup | 1 each | no | write the directory but emit no nodes |
| callers | reindex, mcp-server, graph-diff, wave-plan, cli-commands, graph | 1–4 each | no | readers downstream of the loss; they inherit the fix |

### BDL-UX #281 — the version's nine homes

> **Derived by:** `beadloom impact` over `__init__.py`, `doc_sync/version_subjects.py`,
> `doc_sync/audit.py`, `graph/rules/summary_facts.py`, `application/doctor.py`,
> `tests/test_integration_v1.py`
> **Seed:** `none` on every one of the six — no name these targets reach performs a declared
> effect under `reaches-an-effect-sink`, so every axis is **unresolved rather than empty**
> **Unresolved:** 1, 5, 15, 11, 11 and 7 by kind. Separately, **four of the nine
> version-stating surfaces are `unreadable-target`**: `.beadloom/_graph/beadloom.yml`,
> `docs/services/cli.md` (with `docs/getting-started.md` and the docs-audit SPEC in the same
> unreadable population), `CHANGELOG.md`, `.claude/development/ROADMAP.md`. `.claude/CLAUDE.md`
> was not run for the same reason.

| Axis | Node | Sites | In scope | Why |
|------|------|-------|----------|-----|
| callers | docs-audit | 1 — `src/beadloom/doc_sync/audit.py:606` | yes | one of the three checkers; its population is documents |
| callers | doc-sync | 1 — `src/beadloom/doc_sync/audit_self_surface.py:48` | yes | holds `version_subjects`, whose population the report must state |
| branches | doctor | `_extract_version_claim`, `_check_agent_instructions` (18 branches) | yes | the second checker, over `CLAUDE.md` |
| callers | rule-engine | 5 — `src/beadloom/graph/rules/__init__.py:171` | yes | the third, `summary_facts` over the graph node |
| callers | agent-prime | 8 — `src/beadloom/onboarding/scanner/project_facts.py:71` | no | reads the manifest for other facts; the source of truth is not in question |
| callers | bd-seam, doc-spaces, flow-suppression, onboarding, application, declared-scope, scope-check | 1–5 each | no | consume the subject vocabulary for other questions |

### `beadloom-y8mi` — the README pair

> **Derived by:** `beadloom impact` over `application/gate.py`, `doc_sync/issue_numbers.py`,
> `doc_sync/doc_shape.py`, `doc_sync/tables.py`
> **Seed:** `flow_signature` and `read_declared_docs` for the gate; `none` for the other three,
> so their axes are unresolved rather than empty
> **Unresolved:** 75, 2, 6 and 1 by kind. **The pair itself is not derivable**: `beadloom
> impact README.ru.md --section` over `.` reports `1 no-seed, 1 sweep-narrower-than-the-project,
> 1 unparsed-module, 1 unreadable-target` and states that this derivation reads Python source
> and could not read the file.

| Axis | Node | Sites | In scope | Why |
|------|------|-------|----------|-----|
| branches | ci-gate | `_step_issue_numbers` and its siblings in `application/gate.py` | yes | a new leg goes here, next to the opt-in leg it is modelled on |
| callers | markdown-tables | 4 — `src/beadloom/doc_sync/tables.py`, callers at `axes_section.py:156`, `doc_quality.py:369`, `work_item_routing.py:192`, `waves.py:319` | yes | already reads a document as blocks; the comparison must not become a fifth reader |
| branches | issue-numbers | `resolve_issue_log`, `CONFIG_KEY = "issue_log"` at `issue_numbers.py:100,282` | yes | the precedent for declaring an opt-in pair in `.beadloom/config.yml`, and the place a second config reader would appear |
| callers | doc-shape | 3 — `src/beadloom/doc_sync/engine.py:416` | no | reads sections, not blocks; a different granularity than the comparison needs |
| callers | axes-section, planning-report, doc-quality, work-item-routing | 1–2 each | no | callers of the block reader; they constrain its signature and are not changed |
| callers | flow-guards, wave-plan, mcp-server, cli-commands, reindex | 1–4 each | no | gate blast radius |

## Proposed Solution

### Approach

Four slices, ordered by what blocks the outside trial. S1 and S2 are the adopter blockers and
are independent of each other. S3 and S4 are this repository's own records and can land after.

**S1 — the first five minutes end green.** The skeleton `init` writes names the modules it
already knows: they are in the index the same command built, and `_symbols_for_node` in
`doc_generator.py` already reads them for other sections. The alternative — attesting the pair
at write time — is rejected below.

Separately, `missing_modules` gains a remediation that can be followed. The rule is: a
staleness reason that re-attesting cannot clear must not print a re-attest command. That is a
property of the reason, not of `sync-update`, so it is decided where the reason is decided
(`doc_sync/engine.py`) and rendered where the string is built (`gate.py:1211`).

**Q1 decided: `sync-update` also reports what it did not clear.** Not its scope — that is
BDL-UX #279 and stays out — but one line naming the pairs it left stale and why attesting could
not move them. The evidence is first-hand: a run of `sync-update --yes --all` during this
epic's own scoping returned rc 0 and `Marked 2 ref(s) synced (4 pair(s) total)`, and the
operator believed the defect fixed. A command that reports over the population it attested and
is silent about the one it left is the epic's own class, in the epic's own remediation path.

**Q3 decided by measurement, and it is not the defect the PRD first named.** The stale line is
not printed twice. A pair is a document AND a code file, so two files in a package give two
pairs over one README; `sync-check --json` distinguishes them by `code_path` and the text line
drops exactly that field, so two different pairs render identically. Measured on the two-package
project: four pair entries, four distinct `code_path` values, one `doc_path` per pair of them.
The summary wording is wrong in the same place — `4 stale doc(s)` over two documents. The fix is
to print what distinguishes the rows and to count pairs as pairs.

**S2 — a duplicate `ref_id` is reported.** Two halves, and both are needed:
- the WRITER stops producing the collision — a root node and the sole package cannot take one
  `ref_id`;
- the LOADER reports the reduction instead of performing it silently. Because the directory has
  seven readers and only one goes through the declared policy, the report belongs where the
  parse happens (`parse_graph_file` / `load_graph` in `graph/loader.py`), which every reader
  reaches, rather than in `each_graph_file`, which only one does.

**Q2 decided, and the question as first posed was wrong.** It offered two answers — route the
six through the policy, or admit the policy is one reader of seven — and both assume the six are
reading the graph AS A GRAPH. They may not be: `reindex/change_detection.py` hashes files,
`graph/diff.py` reads content at a git ref. For those, `each_graph_file` is inapplicable by
nature rather than by oversight. So the first task of S2 measures what each of the six does with
what it reads. A reader that parses nodes is routed through the policy; a reader that does not
is outside the policy's real population, and then the policy's own sentence — "the one policy
every reader of this directory holds" — is the thing that is wrong and gets narrowed. Either
outcome changes something: the code, or the claim about it. This stays inside S2 and does not
become a slice.

**S3 — the version's homes are one command.** A new reader, because `impact` cannot see YAML or
Markdown. It takes the source of truth from the manifest and finds the literal elsewhere,
reporting for each place what checks it — and, for the two nothing checks, saying so. The
existing `version_subjects` is not extended: its population is documents by design, and
widening it would put the graph YAML and the test literals into a vocabulary about prose.

**S4 — the README pair is compared.** A Gate leg over a pair declared in `.beadloom/config.yml`,
modelled on `issue_log:` — skipped with a reason when nothing is declared, so no adopter goes
red on a rule that is ours. The comparison reuses `doc_sync/tables.py`, which already reads a
document as blocks.

### Changes

| File / Module | Change |
|---------------|--------|
| `src/beadloom/onboarding/doc_generator.py` | the skeleton names the node's modules, read from the index the same run built |
| `src/beadloom/doc_sync/engine.py` | a staleness reason carries whether re-attesting can clear it |
| `src/beadloom/application/gate.py` | the `doc-stale` remediation is chosen from that flag; the stale line names the pair's `code_path`; the summary counts pairs, not documents; a new `readme-pair` leg |
| `src/beadloom/services/commands/docsync.py` | `sync-update` names the pairs it left stale and why attesting cannot move them (Q1) |
| `src/beadloom/onboarding/scanner/bootstrap.py` | a root node and the sole package cannot take one `ref_id` |
| `src/beadloom/onboarding/scanner/doc_classify.py` | the second node emitter, held to the same rule |
| `src/beadloom/graph/loader.py` | a duplicate `ref_id` is reported at parse, reaching every reader |
| `src/beadloom/onboarding/graph_files.py` | the policy states that it is one of seven readers, or the split is closed |
| `src/beadloom/doc_sync/version_surface.py` (new) | every place this project states its version, what checks each, which are checked by nothing |
| `src/beadloom/services/commands/version_surface.py` (new) | the command over it |
| `src/beadloom/doc_sync/document_pairs.py` (new) | the declared pair and the block comparison, over `doc_sync/tables.py` |
| `.beadloom/config.yml` | this repository declares its own README pair |

### API Changes

- **`beadloom version-surface`** — Q4 decided, by symmetry with the shipped `typed-surface`:
  the surface a project declares typed, and the surface on which it states its version, are
  the same shape of question and now the same shape of name.
- A new `beadloom ci` leg, `readme-pair`, which **skips with a reason** unless a pair is
  declared. No adopter's Gate changes verdict on upgrade.
- `graph/loader.py` gains a reported finding where it previously reduced silently. Anything
  counting nodes will see the same count; anything reading the report sees a new line.

## Alternatives Considered

### Option A: attest the doc pair at `init` time instead of naming the modules
Rejected. It makes the first `ci` green by asserting freshness nobody checked — the false-green
shape this project removed in BDL-061. The skeleton would still not describe the code.

### Option B: put the duplicate report in `each_graph_file`
Rejected on the measurement. Six of the seven readers do not go through it, so the report would
cover one reader and read as covering the directory. Filed instead as the question of whether
the split should be closed at all (Q2).

### Option C: extend `version_subjects` to cover the graph YAML and the tests
Rejected. Its population is documents and its purpose is attributing a version token to a
SUBJECT. The nine places are a different question — where does this project state its own
version — and merging them would give one module two populations and no way to report either.

### Option D: compare the README pair as text with a diff
Rejected. The files are in two languages; only the shape is comparable. A text comparison would
be a check that has to be switched off, which is the thing this epic is about.

## Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| The skeleton fix makes `init` green on our shapes and not on an adopter's | Med | High | every S1 and S2 test builds a project that is NOT this repository, on both layouts, and the acceptance runs against the built wheel |
| Reporting a duplicate `ref_id` reddens a graph somebody already ships | Low | High | it is a report at parse, not a refusal; the verdict it feeds is decided in S2 and stated in the PLAN |
| The new Gate leg reddens adopters | Low | High | the leg skips with a reason unless a pair is declared, exactly as `issue-log` does |
| Measuring the six direct readers shows most of them DO parse nodes, and routing them grows S2 | Med | Med | the measurement is S2's first task and its result is a stated decision either way; if routing is large it becomes a bead, not a redesign |
| The pair-rendering fix changes output that something parses | Low | Med | the text form is for humans and `--json` already carries `code_path`; the JSON shape does not change |

## Open Questions

| # | Question | Decision |
|---|----------|----------|
| Q1 | Should `sync-update` itself say that it re-baselines hashes and cannot clear a content reason? | **Decided 2026-09-10: yes, output only.** Its scope stays out (BDL-UX #279). `cli-commands` returns to scope for that one line |
| Q2 | Should the seven direct readers of `.beadloom/_graph/` be brought through `each_graph_file`, or should the policy state that it is one reader of seven? | **Decided 2026-09-10: neither as posed.** Both answers assumed all six read the graph as a graph, and at least two do not. S2's first task measures what each reads for; routing follows for those that parse nodes, and the policy's sentence is narrowed for those that do not. Stays one slice |
| Q3 | Is the double-reported stale pair one defect or a rendering artefact? | **Decided 2026-09-10 by measurement: neither.** There are four genuine pairs — a pair is a document AND a code file — and the text line drops the `code_path` that tells them apart. `--json` already carries it. The summary's `stale doc(s)` should read `pair(s)` |
| Q4 | What is the command in S3 called? | **Decided 2026-09-10: `beadloom version-surface`**, by symmetry with the shipped `typed-surface` |
