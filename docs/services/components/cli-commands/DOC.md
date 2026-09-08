# CLI Commands (component)

The Click command groups the CLI service is assembled from.

**Source:** `src/beadloom/services/commands/`

**Dependencies:** `click`, `rich`, the `application` layer, and — through
`_root` — nothing above it.

---

## Overview

`services/cli.py` used to be one module holding every command. BDL-059 S4 split
it by responsibility: each module here owns one nameable group of commands and
registers them onto the shared `main` Click group defined in `_root.py`.
`beadloom.services.cli` imports the modules to wire them, so
`from beadloom.services.cli import main` still resolves to the same object it
always did.

The node's `source` is the **directory**, not a file. A component whose source
is a package `__init__.py` records that file as its whole surface, and every
symbol reader then sees an empty façade (BDL-UX #157). Pointing at the directory
keeps all seventeen modules inside the node for `module-coverage` and for the
symbol counts.

## Presentation only

These modules parse arguments, call one application or domain entry point, and
render. No command holds a query or a decision: `status` renders what
`application.status.gather_status` read, `guard` renders what
`application.guards.invocation.run_invocation` decided, `review-brief` renders
what `application.review_brief` assembled. A command that starts computing an
answer belongs in the layer below, and `architecture-layers` (severity `error`)
is what holds that line.

## The modules

| Module | Commands |
|---|---|
| `_root.py` | the shared `main` group and the missing-parser warning helper — no command of its own. The summary `beadloom --help` prints is `help=_HELP`, derived from the package docstring rather than written as the group's own docstring: it was a third hand-written copy of the product description and shipped the 1.x sentence through both 3.0 patch releases (BDL-UX #211) |
| `query.py` | `ctx`, `graph`, `why`, `search`, `prime` |
| `index_ops.py` | `reindex`, `doctor`, `diff`, `link` |
| `status.py` | `status` |
| `docsync.py` | `sync-check`, `sync-update`, `install-hooks`, `active-sync` |
| `federation.py` | `export`, `federate`, `lint`, `ci` |
| `docs.py` | `docs generate`, `docs polish`, `docs site`, `docs audit`, `docs quality`, `docs spaces` |
| `setup.py` | `setup-mcp`, `setup-rules`, `setup-ai-techwriter`, `setup-agentic-flow`, `setup-branch-protection`, `config-check`, `mcp-serve`, `init` |
| `dashboard.py` | `tui`, `ui`, `watch` |
| `snapshot.py` | `snapshot save`, `snapshot list`, `snapshot compare` |
| `guard.py` | `guard` |
| `waves.py` | `waves` |
| `review_brief.py` | `review-brief` |
| `impact.py` | `impact`, `axes`, `scope-check` |
| `mutation.py` | `mutation` |
| `rooms.py` | `rooms` |
| `typed_surface.py` | `typed-surface` |
| `bd_calls.py` | `bd-calls` |

`config-check` prints two derivations beside the drift list, because neither has a Gate
step of its own: the declared mutation scope (`check_mutation_scope`, warn-only — Beadloom
owns no runner to hang a step on) and, whenever a project declares at least one duty, the
population `role_duties.duty_report()` could not inspect. The second prints on the clean path
as well as the blocking one: a check that speaks only when it finds something hands the reader
a clean list, and a clean list is trusted and stopped at. It stays silent for a project that
declares no duty, where there is no verdict to qualify.

The duty block also names the corpus it read — the COMPOSITION this flow would write, not the
role files on disk — and counts the adapters that exist there, printing `NOTHING TO CHECK`
when none do. Until BDL-068 S4's fix bead a project that had never run `setup-agentic-flow`
was told a duty was checked over ten composed artifacts with no blocking drift, which is true
of the composition and says nothing about a corpus no role could receive (BDL-UX #241). The
exit code is unchanged: an unscaffolded project is not in drift.

`guard.py` renders the binding surface above the firing rows, in three sentences rather than
two. `NOT CHECKED` when a source could not be read, `NOTHING TO CHECK` when both were read and
the granted tools include no write path, and the fraction otherwise — `0 of 0 write path(s)
bound` was printed for the middle case and read as full coverage (BDL-UX #239). A `read from:`
line names the artifacts on disk the answer was derived from, which is the same sentence
`config-check`'s duty block prints about its own corpus and for the same reason: the two
commands answer neighbouring questions of different things, and a reader who cannot tell which
one is in front of them has two reports that look like they agree.

`mutation.py` renders what `application.mutation_scope` decided: the score a run produced
over the scope `.beadloom/flow.yml` declared. It reads the counters a runner wrote and
names none — Beadloom owns no mutation runner, so the module knows counter NAMES and not a
tool (BDL-068 S3.1). It prints the ROOM on every report, including the one carrying no run
at all: such a report exits 1, so it is a verdict, and it named no room until BDL-068 S3.3
(BDL-UX #181).

`waves.py` gathers what the graph cannot see and renders what `application.waves` decided, at every wave size. It reads four things at the services edge and hands them over as a `WaveEnvironment`: what differs from `HEAD`, what the installed pre-commit hook judges, how many doc pairs are already stale, and every instruction of the landing lock in the composed flow artifacts. The last population is DERIVED rather than listed, by `bd_seam.population.flow_artifacts` -- the agent directories come from `TOOL_AGENT_DIRS`, the slash commands from `COMMAND_FILES` and the project layer from `.beadloom/flow` -- so a tool added to the flow is read by the same act. The instructions are parsed by the seam's one grammar (`text_invocations`) and judged by `application.waves.landing`, which since BDL-068 S5 carries no grammar of its own. The composed file on disk is read rather than the composition, because what decides an agent's behaviour is the file it is handed: a template fixed and never recomposed leaves the instruction wrong and the check red, which is the correct verdict. Each
wave prints its beads, the `gate_owner` that measures the combined tree, and the clean room
each bead owes — `room-<bead-id>`, also under `rooms` in `--json`. Before BDL-068 S4 the gate
owner and the shared media were printed only for a wave of more than one bead, so the
instrument spoke where a coordinator was already thinking about concurrency and was silent
where it was not (BDL-UX #228); the room is named after the bead because two agents once each
built one at a shared scratchpad path and one measured over the other's files (BDL-UX #235).

It also gathers the work item's `## Axes` at this edge, beside the three machine-observed
media and for the same reason — the application layer keeps taking its input as data — and
prints what every bead's declared `refs:` was held against: the work item, the document, how
many nodes it approves, how many declared refs agree, how many the derivation did not reach
and how many axis rows name no node. That block is printed for a clean plan too, because the
counts are how a reader tells a plan whose declarations agreed from one whose declarations
nothing could be compared against (BDL-UX #232).

`rooms.py` renders what `application.rooms` derived: the room this run is in, the rooms the
project declares — interpreters from its packaging metadata, legs from its CI workflows — and
the ones the run did not enter (BDL-068 S3.2). `--dimension <axis>` prints one axis, one value
per line, which is the form a completion checklist loops over instead of a spelled-out list
that goes stale. It exits 2 when the named axis is carried by no declared room, and names the
axes that exist: an empty answer would read as "this project has no such axis", which is the
clean list an agent trusts and stops at.

`typed_surface.py` renders what `application.typed_surface` derived: the files this project
declares type-checked, read from its own `[tool.mypy]` (BDL-068 S4, BDL-UX #231). `--filter`
takes staged paths on standard input and prints the ones inside the surface, led by the same
`# ` verdict marker `scope-check --porcelain` uses, so the pre-commit hook splits a verdict from
a payload on one shape. The verdict has three sentences and not two, because a surface that could
not be derived, a surface with nothing staged inside it and a surface with files to check are
three different facts: the pre-commit hook used to hand `mypy` every staged `.py` under `src/`
or `tests/`, which is 970 errors in 90 files on this repository and not one of them a violation
of a declared standard. The hook then reached that derivation through the same two directory
names until `beadloom-0mdo.42` (BDL-UX #240) — so on a flat-layout project, where the package
sits at the repository root, the filter admitted no package file and the leg's three sentences
were unreachable. `staged_py` now selects by suffix, and each leg narrows that population by its
own declaration.

`docsync.py` also holds the two hook TEMPLATES, and since BDL-068 S5 the coherence block in
them takes no staging decision for the committer. `active-sync --stage` re-stages the corrected
content of the paths a commit already carries and prints the ones it withheld; the block runs no
`git add` of its own and selects those lines with `grep`, deliberately not with the
`sed -n 's/^# //p'` shape the verdict legs beside it use — that shape is the verdict/payload
split and giving it a second meaning is how two protocols stop being checkable together. The
hook body is reachable as `pre_commit_hook_body(blocking=...)` so a test asserts the promise over
the text that is actually installed rather than over a copy of it (BDL-UX #207).

The command's own report prints one echo per population and never one echo for two. `_echo_unresolved`
names the rows it could not map onto a bead, `_echo_named_by_an_unresolved_row` the beads whose row it
read and could not resolve, and `_echo_unlisted` the beads no row names at all. The middle one was
missing until the S5 review measured its absence: nearly half the beads reported as carried by no row
had a row `_echo_unresolved` had printed two lines above, so one run made two statements about the same
row. The counts, and the run they were taken on, are in the
[`active-table` component doc](../../../domains/application/components/active-table/DOC.md).

`impact.py` holds three commands over one subject and not three subjects: `impact` derives a
work item's axes from the source and renders the `## Axes` section, `axes` reads a section
back and generates the bead's `refs:` from it, and `scope-check` (BDL-068 S1.6) compares the
paths a commit stages against the section the work item declared. One document, written by
the first, read by the second and enforced by the third. `scope-check` exits 2 when a path
falls outside and 0 otherwise, and a run that could not find a branch, a work item, an index
or a section prints its reason rather than a clean sheet. `--porcelain` LEADS with that line,
marked `# ` and on standard output, whether the run compared anything or not: the reason used
to go to standard error alone, and the pre-commit hook reads the command as `2>/dev/null`, so
a clean run and an unattributable one were the same empty string there and the gate printed
the same nothing for both (`beadloom-0mdo.32`, the residue of `beadloom-mr2l.81`). A finding
line opens with a project-relative path, so the marker separates the two without either side
parsing the other.

The pre-commit hook `install-hooks` writes calls it with `--porcelain`; it WARNS in both hook
modes, including the blocking one. Measured over the eleven commits of `features/BDL-068`
before the reader was written — 52 paths, of which 11 have an owner in the graph and 41 have none, 0 findings — the
false-positive rate is zero, and that is still not enough to block on: only two of those
commits touched an owned path at all, and one work item in 64 carries a `## Axes` section
today, so a check that blocked would meet a repository that cannot satisfy it and be answered
with `--no-verify`.

Every module carries `# beadloom:component=cli-commands`, so a module added here
without one is reported by `module-coverage` rather than joining the graph
silently.

## The one command that ends in a verdict

`init` renders its summary and then runs one more application call before it returns: the
Gate's `lint_step` over the graph it has just written, exiting 1 when the graph fails the
rules on disk (BDL-067, closing BDL-UX #192). The check stays
in the application layer and this module only calls it and renders its findings, so the rule
above holds — but the exit code is a decision this command makes, and every branch that writes
a file under `.beadloom/_graph/` makes it: `--yes` in any mode, `--bootstrap`, `--import`, and
the default interactive wizard.

The enumeration is over branches that WRITE rather than over branches that bootstrap, since
BDL-067 `.17`. Until then the guard was `"bootstrap" in result` and `--import` was carved out
on a stated reason — it re-indexed nothing, so there was no index of its own output to judge —
while `--yes --mode import` was carved out on another: both headlines opened with *the graph
this command just wrote*, and that run wrote no bootstrap graph and no rules. Both reasons
held only until the next `init` on the same tree. The wizard's re-init does not delete
`.beadloom/`, so an `imported.yml` from an earlier run survived into a later bootstrap that
wrote `domain-needs-parent` and met the unparented nodes — reported by a run that had written
neither them nor `import_docs` (the review of `.16`, major 2). The `--import` branch now
re-indexes what it wrote before judging it, which removes the reason rather than the check.

Stated because it is the limit of that change: judging every writing run does not make the
import-only run report its own orphans. On a virgin tree it writes no `rules.yml`, so
`lint_step` evaluates nothing and passes honestly. What the change buys is that no branch is
excluded by an accident of another module, and that the run which does meet the rule describes
it truthfully.

The wizard was added in BDL-067 `.6` — the verdict shipped at two call sites because the
covering tests counted the two **bindings** of `bootstrap_project` rather than the branches,
and the wizard shares the `--yes` binding. It is skipped on exactly one path, the wizard's
`edit` review answer, where the graph has just been handed to the user to edit and nothing has
re-indexed.

Whether a verdict is owed is asked of the TREE, not of the branch, since BDL-067 `.21`: the
verdict returns without linting when nothing under `.beadloom/_graph/` changed between the
start of the run and the verdict, using the digest it already takes to answer whose failure it
is. That replaced a branch answering the same question by its position in the source, which is
how the wizard's `cancel` answer came to write `services.yml` and `rules.yml` — both are
written before "Proceed with this graph?" is asked — and then exit 0 through `sys.exit(0)`
with no verdict at all (the review of `.20`, major 2). `init` now contains no `sys.exit`, so
the cancelled result reaches the same guard as every other wizard answer, and the wizard's
OTHER cancelled answer, the re-init prompt asked before any writer runs, is correctly left
unjudged: reporting there would name an existing tree's failures under a withdrawal line
stating that a scaffold was written.

Each evaluated-rule line names the rule, the violating node, and the graph file that node was
written into, read off `.beadloom/_graph/*.yml` rather than off any writer's return value. It
named `services.yml` by habit until BDL-067 `.14`, and the review of `.13` measured the cost:
the failing node was `payments`, written by the import step into `imported.yml`, and the
adopter was sent to two files that do not contain it. The `node` key the line reads comes from
the shared finding shape; before `.14` the node was named only inside the English of `why`.
The line that pre-empts the adopter's next command states the step's name and its summary —
`` `beadloom ci` will fail its lint step: <summary>`` — rather than quoting a rendering of it.
`ci` picks `rich` only on a TTY and `github` otherwise, and the github renderer builds its own
step line instead of calling `gate_step_line`, so quoting `gate_step_line` was wrong in exactly
the scripted context `--yes` serves: one non-TTY shell had `init` promise
`[FAIL] lint: 2 error(s), 0 warning(s)` where `ci` printed
`::notice::lint FAIL: 2 error(s), 0 warning(s)` (the review of `.16`, the minor). The name and
the summary are the two fields every renderer reads off the step, so a sentence built from them
survives all three and any renderer added later.

Two shapes of failure are rendered separately. Rules that were evaluated and failed are named
as rules; a `rules.yml` the loader refuses is rendered as the loader's complaint, because the
finding the Gate raises there carries the step's own name (`lint`) in `rule` and the reason in
`why` — printing the name told an adopter with a hand-edited rules file that a rule called
`lint` had failed.

The evaluated-rule report also names **whose** the failure is, from two facts about the tree
rather than from one boolean about a writer's return value. `init` samples
`.beadloom/_graph/` before any writer runs (`_graph_sample`) and again at verdict time, at two
grains at once: the FILE grain (`_graph_files_now`, a digest of each file's bytes) and the NODE
grain (`_graph_nodes_now`, a digest of each node as written, keyed by ref_id). The headline's two
halves and the sentence under them are then chosen from `(this run wrote the failing node, this
run wrote rules.yml)` through `_GRAPH_HALF`, `_RULES_HALF` and `_ATTRIBUTION` — tables over the
full product, so a corner cannot be left unwritten. Only the corner where both are this run's
calls the red a defect in Beadloom's bootstrap and asks for a report. The other three name what
was already there and ask for nothing.

Each of those three denials is made at the grain its own half of the key is read at, which is
what keeps it checkable against the tree: the two corners chosen by the NODE deny writing the
node, and the corner chosen by `rules.yml` denies writing that file. Both node-chosen sentences
said `graph file(s)` until BDL-067 `.27` — `.24` moved the key to the node and left the words
behind, so the claim no longer followed from what selected it. MEASURED by the review of `.26`,
twice: a run that rewrote an inherited graph file in order to annotate the failing node's
sibling then told the adopter it had not written that file, while `git diff` showed it modified.

The two grains answer different questions and neither can answer the other's, which is why they
are sampled together in one place rather than separately. The FILE grain answers the verdict's
precondition — did this run change the adopter's tree at all — and the `rules.yml` half, since a
rules file holds no nodes and the file is its grain. The NODE grain answers whether this run
produced the node that fails, and it took that half over in BDL-067 `.24`, by the decision of the
review of `.23` (major 4). Read at the file grain, that half said yes whenever any writer touched
the file the failing node happened to sit in — and `generate_skeletons` touches inherited files by
default, since it writes a README for every node in the tree that has none and patches `docs:`
back into that node's file. So a node no writer in this run produced, sharing a file with a node
that gained a `docs:` field, was announced as *the graph this command just wrote* and the adopter
was asked to file a bug report about it, on the common path.

`created or changed` rather than `created`: a node this run rewrote into failing — a `kind` or
`source` change on a ref_id that was already there — stays ours, so the instrument's error
direction is not "hide our own defect".

MEASURED at `.24`, and stated because the decision predicted otherwise: the finer grain does not
move the case where the annotated node IS the failing node. `generate_skeletons` writes the
`docs:` field into that node's own entry, so the node is one this run changed at either grain, and
`init --bootstrap` over an inherited undocumented orphan still asks for a bug report. What the
finer grain does move is the case where the annotated node and the failing node are different
nodes in one file, which is the ordinary shape of an inherited graph file. Both are pinned in
`tests/test_init_report_says_whose_failure_it_is.py`.

Until BDL-067 `.17` a single boolean about `rules.yml` chose both sentences, and there was no
counterpart for the node: a run that bootstrapped over an inherited `imported.yml` said *the
graph this command just wrote* about nodes it had not written and asked the adopter to file a
bug against `import_docs`, which had not run (the review of `.16`, major 2). The digest is read
off the directory rather than off any writer's return value for the same reason
`_graph_file_of_each_node` reads the files: the point is to cover writers this module does not
know about, and `init` gained a second one four waves into this epic. Its two limitations are
stated in the docstring. A file rewritten byte-for-byte with what was already there reads as one
this run did not write — and in that case both answers name the same rules and the same nodes. A
file that cannot be read is left out of the digest rather than digested, so a file unreadable
before the run and readable after it reads as one this run wrote. `.6` established the rules half and applied it to the unloadable-rules branch alone,
which is how the evaluated-rules branch went on blaming Beadloom for a hand-written
`service-needs-parent` until `.9` — measured by the review of `.8` on a scratch TypeScript
project.

`WITHDRAWN_COMPLETION_CLAIM` is printed by the verdict itself, so no branch can decline it.
Every branch has announced a scaffold by the time the verdict runs: the wizard's
`Initialization complete!` and `Next steps:`, `--bootstrap`'s four check marks, `--yes`'s
`Initialized beadloom (mode: ...)` and summary, `--import`'s `Classified N documents`. Until
BDL-067 `.17` it was a `claim_to_withdraw` argument that one of the call sites passed, under a
docstring asserting that the `--bootstrap` branch took its verdict first and never made the
claim — it makes it, four check marks and then the error with no withdrawal, measured by the
review of `.16` (major 3). That false sentence is why the omission read as a decision for two
waves. The line is printed here rather than inside `interactive_init`, which would put a
services-layer decision in the onboarding domain.

That one line precedes **both** report shapes, so it states only what is true of both: the
check did not pass. Until BDL-067 `.12` it read `it does not pass the rules it is checked
against:` and opened the unloadable-rules report, whose next two lines say the graph was not
checked and that no rule was evaluated — the review of `.11` measured the contradiction on two
different unloadable files, so it was the branch and not one parse error. The colon went with
the claim: it promised the list of failing rules that `_report_rules_the_graph_fails` prints
and this branch does not. A second withdrawal string for the second shape was rejected for the
reason `RULES_CONFIG_ERROR` is shared at all — two strings to keep in step is how they drift.
The assertions that hold this are stated over the line as printed rather than over the
constant, so a second string added later is judged by the same claim.

## Related

- `cli` — the registration shell this component is wired into
  ([docs/services/cli.md](../../cli.md))
- `guard-probes`, `bd-seam` — the other two `services`-layer components

`bd_calls.py` renders the derived `bd` call-site population that `bd_seam` computes. BDL-068's
CONTEXT Q4 decided the shape: an External `bd` finding is answered by deriving our own call
sites and stating what each assumes about the answer, never by a wrapper, because a wrapper is
a second thing to keep in step with upstream and a derived population fails on a call site
added later. `beadloom bd-calls` prints the population by channel, the verdict counts, the
selected sites and the regions the derivation did not reach; `--assumption` and `--unsettled`
narrow it, `--json` emits the same facts as data, and `--strict` turns an unsettled site into
exit 1. The default is exit 0 over unsettled sites, because most of them are instructions to a
person and the fix for an instruction is a role duty rather than an exit code. `--assumption`
with a name the derivation does not judge exits 2 rather than printing an empty list, which
would read as "no site makes that assumption". Measured on this repository: 278 sites, 12 in
Python, 264 in instructing artifacts and 2 in `.git/hooks/`.
