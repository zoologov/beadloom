# BDL UX Feedback Log

> Defects and awkward edges found while developing and dogfooding Beadloom, on itself and on an
> anonymised downstream project. This file holds **open entries only**. It was cut down on
> 2026-10-05: closed and excluded entries and the chronology moved, unchanged, to
> `archive/BDL-UX-Issues-closed.md`. What shipped is in the GitHub releases.
>
> **No hand-written tally.** The log is declared as `issue_log:` in `.beadloom/config.yml`, and
> `beadloom issue-number check` reads it for duplicate, unwritten and unclaimed numbers. No
> command computes open or closed counts, so a count written here would be a claim nobody checks.
>
> **How to use.** Take a number with `beadloom issue-number allocate --holder <bead-id>`, add the
> entry under **Open Issues** in descending order, and add its row to the index. When an entry is
> fixed, move its text to the archive with a dated line of evidence. If its number is 262 or
> higher, leave a one-line stub under **Closed numbers that must stay written**: the check fails
> on a claimed number the log no longer writes.
>
> **Each entry is a measurement with a date.** Re-measure before acting on an old one: of six
> entries checked on 2026-09-08, three had gone false.

---

## Template

```markdown
### [YYYY-MM-DD] Short description

**Severity:** low | medium | high | critical
**Command:** `beadloom <command>`
**Context:** What were you trying to do?
**Issue:** What went wrong or felt awkward?
**Expected:** What would be better?
**Workaround:** How did you work around it? (if applicable)
```

---

## Open Issues

> Last checked against the tracker on 2026-10-05. Two entries are about to close: 290 is fixed
> on `features/BDL-078` (`beadloom-nh7h`) and closes when it merges; the cause of 293 was removed
> by BDL-074, and the entry holds itself open until about 2026-10-29.

### Index

| No | Date | Severity | What |
|---|---|---|---|
| 302 | 2026-09-14 | medium | `review-brief` and `waves` take their subject from the checkout |
| 301 | 2026-09-14 | medium | a release's own "verified on the published wheel" sentences fail the Gate on the next version bump, and the suppression that excuses them is file-wide |
| 300 | 2026-09-13 | high | `scope-check` never runs in CI: Actions checks a pull request out on a detached HEAD, so no branch names a work item and the step skips on every pu... |
| 299 | 2026-09-13 | low | `issue-number allocate` accepts an empty holder and writes a claim that names nobody, and `check` reports it clean |
| 297 | 2026-09-13 | medium | `beadloom review-brief --release` keeps withholding when the verdict lives on a separate review bead, and `bd show` defeats the withholding anyway |
| 295 | 2026-09-12 | low | a node whose `extra.tags` is a truthy non-iterable fails every tag question in the run, and the indexer wrote it without complaint |
| 294 | 2026-09-12 | low | `loader.get_node_tags` raises a bare `AttributeError` on a malformed `nodes.extra`, and disagrees with the batch reader beside it on four measured... |
| 293 | 2026-09-12 | medium | running the suite with `--cov` corrupts the project's own index, and 18 tests then fail with `database disk image is malformed` |
| 292 | 2026-09-12 | low | the TUI lint panel branches on a severity the rule vocabulary does not contain, so its warning count is always zero |
| 291 | 2026-09-12 | medium | the debt report reads `rules.yml` from two paths, and the product writes it to a third |
| 290 | 2026-09-12 | medium | `beadloom reindex` is not idempotent across a fresh and a carried-forward index, and the layer rule's new population statement inherits the difference |
| 287 | 2026-09-12 | medium | a `.beadloom/config.yml` that cannot be read crashes `beadloom ci` with a traceback instead of a verdict |
| 286 | 2026-09-12 | medium | a review launch prompt can defeat the withholding it is meant to preserve, and nothing counts it |
| 280 | 2026-09-10 | medium | a room's `locale` dimension is the TEXT codec, and a run has a second one it never reports |
| 279 | 2026-09-10 | medium | `sync-update --yes --all` re-baselines the reference documents' SURFACE as well as the stale refs, and its help names only the second population |
| 278 | 2026-09-10 | medium | `setup-agentic-flow` writes `.claude/CLAUDE.md` and the four slash commands into a project whose flow declares `cursor` alone |
| 277 | 2026-09-09 | low | the orphan check's role population is the manifest and its tool population is a constant, and only the first is stated |
| 276 | 2026-09-09 | medium | the ownership block's GitHub surface drops the caveat that says `unowned` is not a proof |
| 275 | 2026-09-09 | medium | a bead qualifies as a work item by depending on the plan, so a one-bead plan is held against the bead that blocks on it |
| 273 | 2026-09-09 | medium | a clean room states the CAUSE of its missing freshness baseline and never the population, and about forty verdicts in one epic were read as green o... |
| 272 | 2026-09-09 | medium | the `focus-document` medium reads the first cell of every table row in the file, so its population is neither the bead table nor the bead column |
| 271 | 2026-09-09 | high | a ledger file the claim reader drops is a free number, so the allocator hands out a number two writers then hold |
| 269 | 2026-09-09 | medium | a one-hyphen alignment row is valid GitHub Flavored Markdown and reaches the approved-node list as an axis named `-` |
| 268 | 2026-09-09 | medium | two readers of one markdown table row, and the component lifted so a third could not be wrong is one of them |
| 263 | 2026-09-09 | medium | the codec sweep's vocabulary is a list of call names, so a decoding call it has never seen reads as no call at all |
| 260 | 2026-09-09 | medium | `ACTIVE.md` is a shared write, and the property that makes it impossible is one writer per file |
| 257 | 2026-09-08 | high | `waves` derived two beads' scopes as disjoint while one document belonged to both, and the landing lock ordered the commits it could not order the... |
| 246 | 2026-09-04 | medium | a declared mutation target that no run ever covers passes every green Gate, and the one command that would say so is silenced by the flag its only... |
| 242 | 2026-09-04 | low | the launch context a subagent receives carries a `git status` snapshot that is stale by construction, and one agent published from it |
| 232 | 2026-09-03 | medium | `waves` plans from an authored `refs:` line, so two beads editing one document read as independent |
| 230 | 2026-09-03 | medium | a branch whose name carries a suffix after the work-item key names no work item |
| 229 | 2026-09-03 | medium | the brief sends the reviewer to the tracker export and does not name it as a channel |
| 226 | 2026-09-02 | high | the pre-push Gate crashes on a full pipe and reports it as stale docs |
| 225 | 2026-09-03 | high | `impact` under-reports on `src/<one package>` beside code outside src/ |
| 224 | 2026-09-02 | high | a new test file landing on an existing path deletes its scenarios and the suite goes GREEN over the wreckage |
| 223 | 2026-09-02 | low | 102 planning documents depart from the shape their peers keep |
| 222 | 2026-09-02 | low | The independent cross-check states and computes an attribution rule the implementation stopped using |
| 221 | 2026-09-02 | medium | Attribution keys on the whole node, so annotating a node makes its neighbour's failure read as ours |
| 220 | 2026-09-02 | high | `init` still tracebacks on a graph file it cannot handle |
| 219 | 2026-09-02 | high | The review's withholding does not cover commit messages, which is where this project writes its accounts |
| 218 | 2026-09-02 | high | `init` holds three hand-written step sequences and no artifact states what the sequence is |
| 217 | 2026-09-02 | medium | An earlier `init --mode import` leaves domains that no later run will parent |
| 215 | 2026-09-01 | medium | The Gate reports an index problem as a rules configuration error |
| 210 | 2026-08-27 | medium | `active-sync` resolves no row when a bead id is written as a Markdown code span, and blames the id |
| 209 | 2026-08-27 | high | `docs audit` verifies nothing in a non-English document and counts it as scanned anyway |
| 208 | 2026-08-26 | low | A module docstring can describe code that no longer exists, and nothing in this project can see it |
| 206 | 2026-08-26 | medium | `docs/**/features/*/SPEC.md` is excluded from `docs audit` outright, so declared facts drift freely there |
| 205 | 2026-08-26 | medium | Writing a factually correct number can manufacture a false stale fact |
| 203 | 2026-08-26 | low | Two stated behaviours in `doc_area` survive mutation |
| 202 | 2026-08-26 | medium | One `beadloom ci` run prints two different numbers for "CLI commands" under one name |
| 201 | 2026-08-26 | medium | `--format porcelain` drops `message` |
| 200 | 2026-08-26 | low | An inert `docs_audit.ignore` triple is neither computed nor reported |
| 199 | 2026-08-26 | low | The Gate's lint line cannot distinguish "the rule checked nothing" from "the rule found one warning" |
| 198 | 2026-08-26 | medium | `sync-check` verified 0 of 363 pairs and `beadloom ci` exited 0 |
| 197 | 2026-08-26 | medium | Four other rule types still report a TOTAL stand-down as `warn`, so an escalation still evaporates for them |
| 190 | 2026-08-23 | low | `docs audit` reads a version mentioned as an EXAMPLE as a claim about this project |
| 187 | 2026-08-25 | high | External (steveyegge/beads): `bd list --json` returns a filtered view as a bare list, with nothing saying it filtered |
| 185 | 2026-08-23 | low | SUSPECTED: a byte-identity assertion over a WAL-mode database may accuse the wrong thing |
| 184 | 2026-08-23 | medium | `config-check --project <dir>` crashes with a raw sqlite error on a project that has no index |
| 179 | 2026-08-23 | medium | How many rule types exist? Three documents give three answers and all of them are wrong |
| 178 | 2026-08-23 | high | 🔴 A REQUIRED check reports `pass` while its own output says it verified nothing |
| 176 | 2026-08-23 | low | An incremental `reindex` prints `Imports: 0` and `Rules: 0` on the run that refreshed them |
| 168 | 2026-08-22 | medium | `pytest-randomly` produces failures no seed reproduces, and nothing in the output says the order was random |
| 167 | 2026-08-22 | low | `sync-check` prints one `[stale]` line per pair, so a single stale doc reads as a wall of 28 identical lines |
| 166 | 2026-08-22 | medium | Adding one CLI command drifts six reference docs, and `sync-update --all --yes` does not cover them |
| 163 | 2026-08-20 | medium | `sync-update` can re-attest a doc nobody read |
| 162 | 2026-08-20 | high | 🔴 `doctor` should audit the PRODUCED graph, not just the code |
| 161 | 2026-08-20 | medium | `docs audit` checks numeric facts but never checks that a documented identifier still exists |
| 160 | 2026-08-19 | high | 🔴 AsyncAPI ingestion is documented as a capability but wired to nothing |
| 158 | 2026-08-19 | medium | No signal for a bounded context that is too large by SUBTREE |
| 149 | 2026-08-05 | low | `graph --format c4 --level component --scope <ref>` on a node with no internals prints a single useless `C4Container` instead of saying so |
| 148 | 2026-08-05 | medium | `lint` prints machine porcelain when stdout is not a TTY |
| 147 | 2026-08-05 | high | 🔴 `beadloom lint` MUTATES the index |
| 145 | 2026-08-03 | medium | `ctx <ref> --json` returns the REPO-WIDE `code_symbols` array, not the focused node's |
| 140 | 2026-07-29 | low | `ci`/`sync-check` doc-stale output is one line PER stale symbol occurrence |
| 138 | 2026-07-02 | medium | `docs generate` silently no-ops on a coarse graph; no monolith-drift guard; `component`→`DOC.md` not generated |
| 134 | 2026-06-16 | low | `sync-update --yes --all` never reaches fixpoint for `reference` (`watches=`) docs |
| 95 | 2026-05-28 | medium | Per-bundle full table scan of `code_symbols` won't scale; L2 `bundle_cache` is not on the build path |
| 73 | 2026-03-10 | low | `beadloom doctor` reports "Version drift" and "Package drift" by checking `.claude/CLAUDE.md` |

### Entries

302. [2026-09-14] [MEDIUM] `review-brief` and `waves` take their subject from the checkout — the change from HEAD, the work item from the branch name — and neither accepts it as an option

    **Severity:** medium (no wrong code shipped; what is wrong is an instrument whose output describes a different change or no work item at all, with nothing on the command line that could correct it, so the only remedy is to rearrange the checkout around the tool)
    **Command:** `beadloom review-brief <bead>`, `beadloom waves <bead>`
    **Context:** BDL-071, two measurements a day apart by two roles.
    **Case 1 — the change under review, `review-brief` (R3, `beadloom-u7jp`, 2026-09-13).** The review of `release/5.0.0` ran while the main checkout was on `features/BDL-071`. `beadloom review-brief beadloom-u7jp` measured the checked-out `features/BDL-071` against `main`: its change inventory listed 7 planning and tracker files and none of the 10 files under review, so on a release branch the brief's primary pointer was empty. `--since` names the base of the comparison, and no option names its head.
    **Case 2 — the work item, `waves` (coordinator, 2026-09-14).** PR #75 was squash-merged, so the follow-up work for the same epic needed a new branch, first named `features/BDL-071-records` locally. `beadloom waves beadloom-tmgp` printed `the branch names no work item among the planning documents` and left the `focus-document` precondition unmeasured, exit 1. `waves` has no option that names the work item. The remedy in force is a local branch still named `features/BDL-071`, pushed by explicit refspec to `features/BDL-071-records`, because the remote `features/BDL-071` is the merged head and must not be overwritten.
    **Why one entry and not two.** Both instruments resolve a subject the user already knows from the state of the checkout, and neither lets the user state it. #230 (a suffix after the key names no work item) is the matching rule behind case 2, and fixing it would resolve `features/BDL-071-records`. It would not help case 1, a separate worktree, or the detached HEAD of #300, and each of those needs an explicit subject.
    **Expected:** every instrument that resolves a subject from the checkout also accepts it — a head ref for `review-brief`, a work-item key for `waves` — and prints the subject it used and where that came from, so a brief about the wrong change says so on its first line.
    **What is NOT established:** which other instruments resolve a work item or a change from the checkout. Only these two were met, and `scope-check` already has `--branch` (#300). No sweep was run.
    **Tracker:** not filed as a bead. The number is held by `beadloom-tmgp`, which recorded it.
    **Related:** #300 (the same resolution in CI, where no branch is checked out), #230 (the suffix matching rule), #273 (a clean room with no `.git` reports the same skip).

301. [2026-09-14] [MEDIUM] a release's own "verified on the published wheel" sentences fail the Gate on the next version bump, and the suppression that excuses them is file-wide

    **Severity:** medium (no wrong release shipped; what is wrong is that the release flow requires a verification to name the release it was taken on, the audit reads that true sentence as a stale current-version claim, and the only remedy silences more than the sentence)
    **Command:** `beadloom docs audit`, and `beadloom ci` on a version-bump commit
    **Context:** BDL-071, 2026-09-13: R1 (`beadloom-2716`, 5.0.0) and R5 (`beadloom-h784`, 6.0.0). The width of the suppression was found by R3's review (`beadloom-u7jp`, minor 2).
    **What happened.** Measured before planning: bumping only the true current-version places left `beadloom ci` at rc 1, and the audit's stale findings were exactly three `version` mentions of 4.0.0. Two say "measured on the published 4.0.0 wheel", in `docs/domains/graph/components/graph-loader/DOC.md` and `docs/domains/onboarding/README.md`. The third says "Measured on this repository on 2026-09-11, against `4.0.0`", in `docs/services/cli.md`. Each stays true after the bump. Each got a `{path, fact, value}` triple in `.beadloom/config.yml`, on `release/5.0.0` and again on `main` for 6.0.0.
    **The suppression is wider than its sentence.** An ignore rule matches path, fact and value, and no line (`IgnoreRule`, `doc_sync/audit.py`), so the cli.md triple silences every 4.0.0 in cli.md. The config records the measurement, taken 2026-09-14: with cli.md:821, the current-release example, put back to 4.0.0 under a 6.0.0 manifest, `beadloom docs audit` exited 0 with "No stale mentions found" and 17 verified mentions where it had 18. What caught the regression was `tests/test_version_surface.py`, and it catches it only while cli.md:821 is the single audit-checked line of cli.md that states the current version.
    **Why it recurs.** `_extract_versions` matches every `\bv?\d+\.\d+\.\d+\b` outside a pin and has no notion of a dated past tense — #205 is that general form, and still open. What this entry adds is that the project's own release discipline now produces the sentence: a verification must name the release it measured, so every release that records one in a scanned document plants a finding for the next bump. BDL-071 avoided planting new ones only by a rule in its CONTEXT, that verification records go to `ROADMAP.md` and the issue log and never into a scanned document.
    **Expected:** a version beside a dated or attributed measurement ("measured on", "published", a date in the same clause) is read as history, not as a claim about the current version. Or a suppression can be scoped to a line or a sentence, so a triple excuses what it names and nothing else.
    **What is NOT established:** how an adopter's documents fare. Only this repository's three sentences were measured, and no count was taken of dated version sentences on another project.
    **Tracker:** not filed as a bead. The number is held by `beadloom-tmgp`, which recorded it.
    **Related:** #205 (the past tense, the general form, open), #253 (a dependency's version, resolved by attribution to a subject name), #190 (a version mentioned as an example).

300. [2026-09-13] [HIGH] `scope-check` never runs in CI: Actions checks a pull request out on a detached HEAD, so no branch names a work item and the step skips on every pull request

    **Severity:** high (no wrong code shipped; what is wrong is that the Gate is a required check whose summary lists `scope-check` among its steps, and in CI that step has judged nothing on any pull request — a check reporting over an empty population in the one place this project treats as authoritative)
    **Command:** the `gate` job in `.github/workflows/ci.yml`, `beadloom ci` under `actions/checkout@v5`
    **Context:** BDL-070, PR #73, 2026-09-13. Read from the gate job's log after the run completed, while verifying a claim in the pull request's own description.
    **What happened.** The CI gate job printed `scope-check SKIP: skipped — no branch is checked out, so no work item names the scope to judge against`. `actions/checkout` checks a pull request out on a detached HEAD, so there is no branch name to resolve a work item from, and the step skips **on every pull request, whatever the branch is called**. PR #72 was pushed under the exact work-item name and could not have run it in CI either.
    **Why it went unnoticed.** A SKIP is a `notice`, and the Gate is still green. Locally, on a named branch, the same step runs and earns its place — on this epic it found four out-of-axes paths that were then re-ruled in the RFC. The pipeline is where the Gate is a required status check, and it is the one place the step never judges.
    **It corrected a coordinator error on the same epic.** The coordinator recreated the BDL-070 branch under the exact work-item name on the reasoning that this kept `scope-check` running "in the pipeline". That premise was false; the correction is recorded on `beadloom-5tcc` and in PR #73's description.
    **Expected:** the Gate in CI resolves the work item from the pull request itself — `GITHUB_HEAD_REF`, or `scope-check`'s existing `--branch` fed from it — or, where it cannot, reports the SKIP as a named population of zero on the Gate's summary line rather than a quiet notice beneath a green check.
    **What is NOT established:** whether any other Gate step also reads the branch name and is silent in CI for the same reason. Only `scope-check` was read.
    **Tracker:** `beadloom-tsqz`.
    **Related:** #230 (a suffix after the work-item key names no work item — a different, local cause of the same skip); #273 (a clean room with no `.git` reports the same `no branch is checked out` SKIP).

299. [2026-09-13] [LOW] `issue-number allocate` accepts an empty holder and writes a claim that names nobody, and `check` reports it clean

    **Severity:** low (the number is still unique and still written; what breaks is the property the ledger exists for — that every allocated number is HELD by a named work item)
    **Command:** `beadloom issue-number allocate --holder ""`, then `beadloom issue-number check`
    **Context:** BDL-070, 2026-09-13, reached by accident while filing #298.
    **What happened.** `allocate --holder ""` exited 0, allocated #298, and wrote `.claude/development/BDL-UX-Issues/0298.md` with an empty `**Holder:**` line. `check` then printed `No duplicate, unwritten or unclaimed number.` — the malformed claim read as clean.
    **How an empty holder arrives in practice — an EXTERNAL trigger, recorded because it is the realistic path.** `bd create ... --json` (bd 1.0.4) printed a non-JSON warning to STDOUT before the JSON object, because the title began with `test_` and bd judged it test data: `⚠ Creating test issue in production database … appears to be test data`. A script parsing stdout as JSON failed, the bead id came out empty, and the empty string went straight to `--holder`. The bead itself was created (`beadloom-jorg`). The bd half — a warning on the stream a `--json` caller parses — belongs to steveyegge/beads and is noted, not ours to fix.
    **Repaired here:** the #298 claim's holder and the #298 entry's tracker were both set to `beadloom-jorg` by hand, since there is no command to set a claim's holder; each repair says so in place.
    **Expected:** `allocate` refuses an empty or whitespace-only holder with a named error and allocates nothing; `check` reports any existing claim whose holder is empty.
    **Tracker:** `beadloom-l5jb`.
    **Related:** #298 (the entry this defect first produced).

297. [2026-09-13] [MEDIUM] `beadloom review-brief --release` keeps withholding when the verdict lives on a separate review bead, and `bd show` defeats the withholding anyway

    **Severity:** medium (no wrong code shipped; what is wrong is an independence gate that reports itself in force while one ordinary command defeats it, and that cannot release in the shape the flow prescribes)
    **Command:** `beadloom review-brief <fix-bead> --release`, then `bd show <fix-bead>`
    **Context:** BDL-070, three consecutive review passes on 2026-09-13 — `beadloom-5tcc.10` (pass 3), `beadloom-5tcc.11` (final), `beadloom-5tcc.13` (confirmation) — each launched as the flow prescribes, as its own bead depending on the work it reviews.
    **What happened.** `--release` looks for a verdict **on the fix bead itself**. `/coordinator` places every review on a separate bead that depends on the reviewed work, so the verdict is never where `--release` looks and the author's account stays withheld after the verdict exists. Every one of the three reviewers then read that account through `bd show <fix-bead>`, which prints comments unconditionally. The confirmation pass recorded it: "I ran `bd show beadloom-5tcc.12` to read the fix bead's assignment, and it printed the author's CHECKPOINT and COMPLETED comments before I had measured anything."
    **Two defects, separable.** (1) `--release` cannot find a verdict placed on a bead that depends on the reviewed bead. (2) `bd show` is a withholding bypass that `review-brief` neither counts nor names — so "N comments withheld" is a population statement over the wrong population.
    **Why the reviews still stand:** each reviewer re-derived every figure it reported and said so, and stated that the withholding was defeated rather than leaving it to be discovered. The defect is in the instrument's report of independence, not in the verdicts.
    **Expected:** `--release` accepts a verdict on a bead that depends on the reviewed bead, or the flow records verdicts where `--release` looks; and the brief names the channels it does not cover, `bd show` among them.
    **What is NOT established:** whether an earlier review in this repository was materially steered through `bd show`. It was measured on these three passes only.
    **Tracker:** `beadloom-6rfz`.
    **Related:** #212, #219, #286 — the withholding defeated through the epic document, commit messages and the launch prompt. This is the fourth channel.

295. [2026-09-12] [LOW] a node whose `extra.tags` is a truthy non-iterable fails every tag question in the run, and the indexer wrote it without complaint

    **Severity:** low (pre-existing on both sides of the change, and it takes a hand-written graph file to produce; what it costs when it happens is the whole run rather than the one node)
    **Command:** `beadloom lint`, and anything that reaches the rule engine
    **Context:** BDL-070, review pass 3 (`beadloom-5tcc.4`), 2026-09-12. Found while checking whether the second fix cycle's docstring matched its guard — it does not, and this is the case it does not cover.
    **What happened.** A node whose `extra` is a readable object but whose `tags` value is a truthy non-iterable — `{"tags": 3}` — reaches `set(declared)` at `graph/rules/node_tags.py:85` and raises `TypeError: 'int' object is not iterable` from inside the single pass over the table. One such row therefore fails every tag question in the run, not the question about that node. It is the shape of this epic's first review Major one level down: the malformation is in `extra["tags"]` rather than in `extra`.
    **Measured as pre-existing, which is why it was not repaired here.** Two fixture projects that are **not this repository** — one declaring a layer rule, one declaring only a tag-matched `deny` rule — each holding a node written `tags: 3` and reachable by no rule, indexed once and linted by `main`'s sources and by the epic's over the same index. **Both sides raise.** `main` reaches it through `liveness._GraphFacts.tags`, which already read every node's tags whenever any rule carries a tag matcher. So a verdict-neutral release is the wrong place to fix it.
    **The write side is silent too.** `graph/loader.py:474`–`478` puts every unmapped YAML key into `extra` untyped, so nothing rejects `tags: 3` when the graph file is written. The first thing that notices is a traceback at evaluation time.
    **A sixth shape the divergence table does not name:** a JSON array (`[]`, `["tier-web"]`). The existing `isinstance` guard covers it, and it diverges from the one-at-a-time reader exactly as the three scalars do.
    **Expected:** a node whose `extra.tags` is not a sequence is skipped like every other unreadable shape, with a row in `_DIVERGING_SHAPES` naming it — or the indexer refuses it at write time and says which node.
    **What is NOT established:** whether any real graph file in any project has this shape. The reviewer constructed it; nobody has seen one in the wild.
    **Tracker:** `beadloom-efcb`.
    **Related:** #294 (the same pair of readers, disagreeing on the shapes of `extra` itself), #268, #269.

294. [2026-09-12] [LOW] `loader.get_node_tags` raises a bare `AttributeError` on a malformed `nodes.extra`, and disagrees with the batch reader beside it on four measured inputs

    **Severity:** low (pre-existing, and no wrong verdict follows from it; what follows is a traceback naming `json` or an attribute instead of the node, and two readers of one fact answering differently)
    **Command:** any command that reads node tags — `beadloom lint`, `ctx`, the TUI
    **Context:** BDL-070, the re-review `beadloom-5tcc.2`, 2026-09-12. Found while checking whether the fix for the first pass's Major 2 was redundant. **Not introduced by this epic** and deliberately not repaired inside a verdict-neutral release.
    **Measured** over a four-row `nodes` table, `graph/rules/node_tags.NodeTags.of(ref)` against `graph/loader.get_node_tags(conn, ref)`:

    | `extra` | batch reader | one-at-a-time reader |
    |---|---|---|
    | `null` | `set()` | raises `AttributeError` |
    | `3` | `set()` | raises `AttributeError` |
    | `"x"` | `set()` | raises `AttributeError` |
    | `{not json` | `set()` | raises `json.JSONDecodeError` |

    **Two things are wrong, and they are separable.** The exception is not derived from this project's base error, so a caller cannot tell "this row is unreadable" from a programming mistake. And the two readers of one fact disagree on all four shapes — the batch reader answers empty by design, because one unreadable row must not fail an evaluation that never asked about that node.
    **Why the disagreement is defensible and still worth recording:** the batch reader's tolerance is the whole reason it can read the table in one pass. The defect is not that they differ but that nothing says so where either is declared, which is the shape #268 and #269 record for two other reader pairs in this codebase.
    **Expected:** a malformed `nodes.extra` reaches the caller as an error this project defines, naming the node and the shape; and the two readers' difference is either removed or stated where both are declared.
    **What is NOT established:** how many callers of `get_node_tags` would see the raise. The reviewer measured the function, not its call sites.
    **Tracker:** `beadloom-ui47`.
    **Related:** #268, #269 (two readers of one fact, answering differently). The batch reader's own guard was added by BDL-070's first fix cycle, against the first review pass's Major 2.

293. [2026-09-12] [MEDIUM] running the suite with `--cov` corrupts the project's own index, and 18 tests then fail with `database disk image is malformed`

    **Severity:** medium (no shipped behaviour is wrong. What is wrong is that the one command the role protocol names for proving coverage — `uv run pytest --cov=src` — produces a RED suite over a green tree, so a run taken to measure coverage cannot also be read as a verdict)
    **Command:** `uv run pytest --cov=src/beadloom`, over the whole suite
    **Context:** BDL-070, `beadloom-cfkk` (A7), 2026-09-12. Found while taking this bead's coverage figure, and proved **not to be this bead's change** by a control run.
    **What happened.** Over the full suite the shared `.beadloom/beadloom.db` at the project root ends up corrupt, and every later test that reads it fails with `sqlite3.DatabaseError: database disk image is malformed`. Eighteen fail, in three files — `test_s3_decomposition.py` (5), `test_s4_the_instruments_agree.py` (1) and `test_the_layer_rule_states_the_population_it_judged.py` (12). Without `--cov` the same suite over the same files is green.
    **How it was proved.** Three runs in `room-beadloom-cfkk`, each starting from a room with no index at all. With `--cov`: 18 failed, 10 478 passed. With `--cov` and this bead's three new test files excluded by `--ignore`: the SAME 18 failed, 10 463 passed — so the trigger is present at `43286775` and is not carried in by A7. Without `--cov`: 10 496 passed, 0 failed. Deleting the index and re-running the three failing files alone passes 64 of 64.
    **Expected:** a coverage run is a measurement of the same suite, not a different one. Either the tests that reindex the project root are isolated from each other under instrumentation, or the corruption's cause is found and removed.
    **What is NOT established:** the mechanism. `--cov` changes timing and adds `atexit` work, and the suite reindexes the project root from a session fixture and from subprocess tests; which pair of writers overlaps was not derived. Nor was it checked on Linux — every run above is macOS, Python 3.13, in one room.
    **Consequence for this project's own numbers:** every coverage figure this repository has quoted was taken from a run in which those 18 tests failed. The per-module figures still stand — the failing tests are in three files and the modules they cover are exercised elsewhere — but the TOTAL is taken over a suite that did not finish as intended.
    **THE COORDINATOR RAN THE SAME FORM ON THE TREE AND IT DID NOT REPRODUCE, 2026-09-12.**
    `uv run pytest -q --cov=beadloom --cov-report=term-missing --cov-fail-under=80` over the whole
    suite on `features/BDL-070` at `18345ccd`: **10545 passed, 13 skipped, 13 xfailed, 0 failed**,
    713.74s. That is the invocation this project's own completion checklist names, with `--cov`, and
    none of the eighteen failed. An earlier coverage run by the coordinator at `183fe47c` was green
    too (10501 passed, 0 failed).
    So the entry stands on ONE room's measurement and is contradicted by two runs on the tree. The
    difference the two accounts do not resolve: the reporter's runs each started from **a room with
    no index at all** and the coordinator's ran against an index already built. That is a candidate
    mechanism, not a finding — nobody has run the crossed cases. Until someone does, "running the
    suite with `--cov` corrupts the index" is not established as a property of the command; what is
    established is that it happened three times in `room-beadloom-cfkk` and not twice on the tree.
    **Consequence for the line above it:** the sentence "every coverage figure this repository has
    quoted was taken from a run in which those 18 tests failed" is now known to be false for at least
    the two runs named here.
    **Tracker:** not filed as a bead. The coordinator's decision, 2026-09-12: it does not earn one
    yet, because the two accounts disagree and the next step is a measurement rather than a repair —
    whoever takes it should run the crossed cases (fresh room without `--cov`, existing index with
    `--cov`) and only then file.
    **AMENDED 2026-09-14 (BDL-071, `beadloom-tmgp`): REPRODUCED ON LINUX, IN CI, ON A REQUIRED CHECK.**
    The sentence above that it "was not checked on Linux" is now false. PR #75, the 6.0.0 release
    pull request, run `34787188082` at head `78166c20`, attempt 1: the `tests (3.12)` job, on
    `ubuntu-latest` with CPython 3.12.14, step `Tests with coverage`, ended
    `2 failed, 10663 passed, 65 skipped, 13 xfailed` in 727.96s. Both failures are
    `sqlite3.DatabaseError: database disk image is malformed`:
    `tests/test_graph_summary_facts.py::TestThisRepositoryIsChecked::test_this_repository_s_summaries_state_checkable_facts`
    and
    `tests/test_s4_the_instruments_agree.py::TestOneApprovalIsReadOnce::test_a_resolved_approval_is_named_identically_by_both`.
    In the same attempt `tests (3.10)`, `tests (3.11)`, `tests (3.13)` and both `tests-locale` legs
    passed. Attempt 2 re-ran it and every job succeeded. Read from the job log and the attempt's job
    list, not from a summary.
    **What this adds, and what it does not.** It is the first measurement on Linux and on CPython
    3.12, and the first time the defect reddened a required check — on a release pull request. The
    failing set differs from the 18 of `room-beadloom-cfkk`: two tests in two files, and only one of
    those files, `test_s4_the_instruments_agree.py`, is also in that set. The job ran
    `uv run pytest --cov=beadloom --cov-report=term-missing --cov-fail-under=80` on a fresh runner,
    which builds its index from empty. That is the condition the reporter's rooms had and the
    coordinator's tree runs did not, so the Linux run is CONSISTENT with the "no index at the start"
    candidate. It does not establish it: the crossed cases are still unrun, and the other three
    `tests` legs of the same attempt ran the same command from the same empty start and passed. So
    the symptom is intermittent under one condition, which a mechanism will have to explain.
    **The bead question is the owner's**, and is put to the coordinator on `beadloom-tmgp` rather than
    decided here, because creating a bead changes a plan's DAG.
    **AMENDED AGAIN 2026-09-14 (BDL-071 close-out, the coordinator): TWO LEGS OF THE NEXT PULL REQUEST.**
    PR #76, the records pull request, run `34790798779` at head `617e082c`, attempt 1, read from the
    two job logs: `tests (3.11)` ended `10 failed, 10655 passed, 65 skipped, 13 xfailed` in 834.48s,
    and `tests (3.12)` ended `2 failed, 10663 passed, 58 skipped, 13 xfailed, 7 errors` in 727.98s —
    every failure and every setup error `sqlite3.DatabaseError: database disk image is malformed`.
    `tests (3.10)`, `tests (3.13)` and both `tests-locale` legs passed; attempt 2 re-ran the two and
    both passed. The 3.12 set is new again — seven setup errors in
    `test_a_commit_is_judged_against_the_declared_axes.py`, failures there and in
    `test_bead18_s5_relation.py` — while the 3.11 set includes `test_graph_summary_facts.py`, one of
    PR #75's two. So across two consecutive pull requests it reddened three of eight `tests` legs,
    on three Python versions, never with the same set twice. That is what the intermittency claim
    above rests on now, and it is also the argument against reading any single green re-run as a
    verdict. The implementer's recommendation on `beadloom-tmgp` is to file a bead now, with the crossed
    cases as its first step and #298 (same shared live index) considered in the same bead.
    **FILED 2026-09-14 by owner decision: `beadloom-qq6m` (P1, bug), covering #293 and #298 together.**
    This supersedes the "not filed as a bead" line above. Its first step is the crossed cases.
    **AND A THIRD PULL REQUEST, WITH A DIFFERENT SIGNATURE.** PR #77, the BDL-071 close-out (documents
    and tracker only), run `34793288575`, `tests (3.10)`: `9 failed, 10647 passed, 65 skipped,
    13 xfailed, 9 errors` in 848.86s — none of them `malformed`; every one
    `sqlite3.OperationalError: disk I/O error`, in tests that read this repository's own index
    (`test_the_same_layer_split_is_recomputed.py`, `test_a_layer_the_declaration_names_and_no_node_is_in.py`,
    `test_s3_decomposition.py`, `test_bead18_s5_relation.py`). The other seven required checks that
    reported passed. Two things this adds: the family has a second symptom, so a triage that matches
    only `malformed` misses it; and the CLI told the reader `index cannot be read (disk I/O error) —
    it predates the current schema. Run beadloom reindex`, naming a schema cause for an I/O failure.

    **AMENDED 2026-09-29 — the cause removed by BDL-074 (`beadloom-qq6m` closed).** Every test now starts
    in an empty temporary directory and a contact guard fails any test that opens this repository's live
    index, tracker or history; the self-checks read a session snapshot instead. A tracer over parent and
    child processes found 0 live-index contacts (98 before). The `--cov` legs of PRs #83, #84 and #86 ran
    green with it. Kept open here only until the next few weeks of PRs confirm it; close on the first
    month without a `malformed` or `disk I/O error` signature.

    **Still open by its own condition, 2026-09-29.** The records sweep of this date confirmed the
    cause removed and did not close the entry: it closes after the first month without a
    `malformed` or `disk I/O error` signature, roughly 2026-10-29.

292. [2026-09-12] [LOW] the TUI lint panel branches on a severity the rule vocabulary does not contain, so its warning count is always zero

    **Severity:** low (the panel is a dashboard and decides nothing, but it is one of the surfaces an owner looks at to ask how much is wrong, and it answers `0 warnings` over 71 of them)
    **Command:** `beadloom tui`, the Lint panel
    **Context:** BDL-070, `beadloom-q6jh` (A4), 2026-09-12. Found while measuring what the panel renders before and after the bead's own change, and explicitly **not that bead's change**.
    **What happened.** `tui/widgets/lint_panel.py:19` and `:27` branch on `severity == "warning"`. The vocabulary is `VALID_RULE_SEVERITIES = frozenset({"error", "warn"})` (`graph/rules/types.py:29`), and every `Violation` carries one of those two. The branch is therefore dead: no finding ever takes it.
    **How it was proved.** Measured over this repository's own index in `room-beadloom-q6jh`, where `lint --strict` reports 0 errors and 71 warnings: the panel header renders `Lint ℹ 71 info`. The warning count and the warning icon are unreachable, and every `warn` finding renders in the `dim` info style.
    **Expected:** the panel reads the severity vocabulary the rule engine defines rather than a spelling of its own, so a finding the linter calls a warning is a warning on the screen.
    **What is NOT established:** whether any other reader of `Violation.severity` outside `graph/` carries the same spelling. One was found, by reading the two functions this bead had to touch; the class was not swept.
    **Tracker:** `beadloom-vu0a`.
    **Related:** #272 — the same shape at a different grain, a reader keyed on a form its producer does not emit.

291. [2026-09-12] [MEDIUM] the debt report reads `rules.yml` from two paths, and the product writes it to a third — so its rule-violation category is silently zero on every standard-layout project

    **Severity:** medium (no verdict is wrong: `beadloom debt` is not a Gate step. What is wrong is a health number that reads as measured and was never taken, which is the class this project's last three epics exist to remove)
    **Command:** `beadloom status`, the TUI debt gauge, the site dashboard, the MCP `get_debt_report` tool — every caller of `collect_debt_data`
    **Context:** BDL-070, `beadloom-q6jh` (A4), 2026-09-12. Found while wiring the layer population into the debt surface, and explicitly **not that bead's change**: the paths predate it.
    **What happened.** `application/debt_report/collect.py:239-243` resolves `<root>/rules.yml`, then `<root>/.beadloom/rules.yml`, and returns `(0, 0, {})` when neither is a file. The canonical location — the one `graph/linter.py`, `application/reindex/full.py`, `tui/data_providers.py`, `services/mcp_server.py` and `onboarding/scanner/rules_gen.py` all resolve — is `<root>/.beadloom/_graph/rules.yml`. A project laid out the way `beadloom init` lays it out therefore loads no rules here at all.
    **How it was proved.** Measured on this repository, over its own index: `_count_violations(conn, root)` returns 0 errors and 0 warnings, while `beadloom lint --strict` over the same index reports 0 errors and 71 warnings. `collect_debt_data` returns `error_count=0, warning_count=0`, so the `rule_violations` category scores 0 points out of the 71 it would score at the default `rule_warning` weight of 1.0.
    **Why it is filed rather than fixed.** The repair is one line — try the canonical location too — and it moves this repository's raw rule-violations score from 0 to 71 points. BDL-070 Release A ships no number that moves on upgrade, and a debt score is a number an adopter watches over time; a silent jump would be indistinguishable from a real regression.
    **Expected:** the debt collector resolves the rules file the way every other reader does, or one function resolves it for all of them.
    **What is NOT established:** what the score's trend history means across the repair. `metrics_history.json` holds points taken under the current behaviour, so the delta on the first run after a fix is an artefact of the fix rather than of the code, and nothing here says how that should be presented.
    **Guarded meanwhile:** `tests/test_every_surface_past_lint_states_the_population.py::TestTheDebtReportReadsRulesFromAPlaceNobodyWritesThem` holds the current behaviour, so the repair fails there first and the test that fails names this entry.
    **Tracker:** `beadloom-is2z`.
    **Related:** #287 — a declaration resolved from a path nothing writes to, reported as an absence rather than as a misdeclaration.

290. [2026-09-12] [MEDIUM] `beadloom reindex` is not idempotent across a fresh and a carried-forward index, and the layer rule's new population statement inherits the difference

    **Severity:** medium (no wrong verdict was produced; what moves is a DENOMINATOR the project had just started printing, and a number that changes with how you arrived at it is the class three consecutive epics exist to remove)
    **Command:** `beadloom reindex`, then `beadloom lint --strict`
    **Context:** BDL-070, `beadloom-punn` (A6), 2026-09-12. Found by the bead while re-taking a neutrality measurement, and explicitly reported as **not that bead's own change**.
    **What happened.** An import into a node whose `source` is a single FILE inside a parent node's directory resolves differently depending on how the index was BUILT rather than on what the tree contains. At commit `4172c331`, `beadloom.application.graph_reads` resolves to the node `graph-reads` in an index carried forward, and to `application` in one built from scratch.
    **How it was proved**, by the bead: this tree's `.beadloom/beadloom.db` was carried into a worktree at `4172c331` and reindexed. The active `depends_on` count went **362 → 363 with no source file changing**. The extra edge is `tui -> graph-reads`.
    **Why it reaches further than a count.** BDL-070's A2 (`beadloom-1ylk`) shipped the sentence `this rule evaluated 16 of 363 live depends_on edge(s) and skipped 347 for an end carrying no layer tag of its own`. That denominator is now lineage-dependent. The population statement was added so a green line would stop being a silence; a denominator that depends on index history puts a smaller version of the same defect inside the sentence that fixes it.
    **What the coordinator measured separately, and what it does NOT show.** An incremental `reindex` run immediately after a `--full` one, with nothing changed in between, is stable: 363 both times, `tui -> graph-reads` present both times. That is idempotency-after-full, a different property from the lineage difference above. It is recorded here so the entry is not read as having two confirmations when it has one.
    **Swept, and the mechanism named, 2026-09-13 by BDL-070 `beadloom-46am`.** Both of this entry's unestablished points are now measured, on commit `30352b92`, in a worktree of this repository with no code difference at all: `rm .beadloom/beadloom.db`, then three consecutive `beadloom reindex --full`. The first run reports 364 `depends_on` edges and resolves `tui/app.py:17` to `application`; the second and third report 365 and resolve it to `graph-reads`. So the difference is not fresh-worktree against carried-forward tree -- it is the FIRST build of an empty index against every build after it.
    **How many others have this shape: two, of 2371.** The `code_imports` table was dumped after the cold run and after the warm one and compared row by row. Exactly two rows differ, `src/beadloom/tui/app.py:17` and `src/beadloom/tui/widgets/status_bar.py:11`, both importing `beadloom.application.graph_reads`, and both flipping `application` -> `graph-reads`. One derived edge follows, `tui -> graph-reads`, which is the one this entry already names.
    **Which answer is correct: the warm one, and the cold index contradicts itself.** `resolve_import_to_node("beadloom.application.graph_reads", Path("src/beadloom/tui/app.py"), conn, ["src"])` re-run against the FINISHED cold index answers `graph-reads`, while that same index has `application` stored. The cause is Strategy 1 of `graph/import_resolver.py:809`-`:820`: it returns the node that owns the imported FILE, but only when that file is already present in `code_symbols` or `file_index`. On the first build both tables are empty while `index_imports` runs, so Strategy 1 never fires and Strategy 3's directory-prefix match collapses a file-sourced node into its enclosing directory node. That is the BDL-UX #144 regression Strategy 1 was written to close, still live on the cold path.
    **Which makes the cold path the adopter's first one.** `beadloom init` builds an index from nothing and then takes its Gate verdict over it (BDL-067), so the graph an adopter is judged against on the run that creates it is the one that resolves these imports wrongly. Nothing here establishes that any adopter has been affected -- this repository's own two instances produce no finding, because neither `tui` nor `graph-reads` decides a rule today.
    **It also swallowed a measurement while being measured.** `beadloom-46am` first compared a cold before-index against a warm after-index and read `lint --strict --format porcelain` as identical, 62 lines both sides. Re-taken with both sides warm, the population line moves `16:365:349:357` -> `16:364:348:356`. The two errors cancelled: the lineage difference added an edge on the after side while the bead removed one. A mismatched lineage does not only add noise, it can subtract a real change.
    **Expected:** a fresh index and a carried-forward index over one tree resolve every import to the same node. Where that cannot hold, `reindex` reports that the answer depends on the index it started from, rather than returning a different graph in silence.
    **What is NOT established:** how many other imports have this shape — one was found, by its effect on a count somebody happened to be watching, and the class was not swept. Nor whether the fresh answer or the carried-forward answer is the correct one; the entry claims only that they differ.
    **Tracker:** `beadloom-xzvp`.
    **Related:** #269 and BDL-069's `beadloom-rqma.4` — `reindex` attributing a prefix-sharing sibling's API routes to a node. Same family: a node whose source is a path inside another node's reach.

287. [2026-09-12] [MEDIUM] a `.beadloom/config.yml` that cannot be read crashes `beadloom ci` with a traceback instead of a verdict — three shapes reach the same raise

    **Severity:** medium (an adopter's first-run experience, and the shapes of broken config no gate leg can report on, because the run ends before any leg runs)
    **Command:** `beadloom ci`
    **Context:** BDL-069, `beadloom-rqma.7`, 2026-09-12. Found while measuring the fix for #270 on a foreign two-package project.
    **What happened.** With `issue_log:\n  path: [unclosed` in `.beadloom/config.yml`, `beadloom ci` exits 1 with a `yaml.parser.ParserError` traceback from `infrastructure/scan_paths.py:33`, raised inside the reindex step. No gate line is printed, no step reports, and the user is shown a stack trace rather than a verdict. That is the shape this entry was FILED on; two more reach the same raise and are named below.
    **Why it is filed rather than fixed here.** `beadloom-rqma.7`'s declared scope is `ci-gate, doc-sync`, and the raise is in `infrastructure`. The bead made the two opt-in legs report an UNREADABLE config as "whether this project declares a document pair is unknown" — a skip that WARNs and names the file — and that branch is reachable from `_step_readme_pair` and `_step_issue_numbers` and is covered by tests. It is NOT reachable through `beadloom ci` today, because the run ends in `resolve_scan_paths` first. The claim in the SPECs is written against the step, and says so.
    **Expected:** every reader of `.beadloom/config.yml` reports a failure to READ it — not to parse it only — as a finding against the file, with the line and column YAML already gives where YAML has them, rather than propagating the exception. `resolve_scan_paths` is the first reader on the `ci` path and the place a verdict would have to start.
    **THREE SHAPES, and this entry covers all three since 2026-09-12.** It was filed naming one — YAML that does not parse — and `beadloom-qae9`'s fourth pass reproduced three, each reaching a traceback out of `resolve_scan_paths` through `beadloom ci`, each at rc 1: `yaml.parser.ParserError` for an unclosed list; `AttributeError: 'list' object has no attribute 'get'` at `scan_paths.py:34`, where `yaml.safe_load` SUCCEEDS and returns a document whose top level is a list rather than a mapping; and `UnicodeDecodeError` for a file that is not UTF-8. The three share one line — `yaml.safe_load(config_path.read_text(encoding="utf-8"))` and the `.get` on its result — which is why a fix measured against the filed shape alone would leave two live. **None of the three is a false green:** all print a traceback at rc 1, so the run is loud and useless rather than quiet and wrong.
    **What this entry does NOT cover**, stated so that a fix measured against it knows its own edges:
    - **A config that cannot be opened at all** — no read permission. `read_text` raises `PermissionError` from the same line, so the shape is the same by reading; it was NOT reproduced through `beadloom ci`, and the entry claims nothing about it. What WAS measured is one surface over: `chmod 000 .beadloom/config.yml`, then `beadloom issue-number check`, gives rc 0 and `it could not be read (PermissionError) — repair .beadloom/config.yml so it parses as a YAML mapping` — a remediation that is the wrong repair for this shape and hands a person an exception class name. That is `beadloom-ovam`, not this entry.
    - **A `.beadloom/config.yml` that is a DIRECTORY**, which is not a read failure anywhere: `read_declaration` tests `is_file()`, so it reads as absence and `issue-number check` says `No issue log is declared`. Defensible — a directory is not a config file anyone wrote — and recorded as the one input shape in this area that still answers a question it did not establish.
    - **Any reader of `.beadloom/config.yml` other than `resolve_scan_paths`.** That is the first reader on the `ci` path and therefore the one that decides the verdict; the others were not measured here.
    **Related:** #270 (the same file, read by the two opt-in legs, closed by this bead). `beadloom-ovam` (the remediation that misnames the repair for two of the shapes above).

286. [2026-09-12] [MEDIUM] a review launch prompt can defeat the withholding it is meant to preserve, and nothing counts it

    **Severity:** medium (the findings were reproduced from the code and stand; what was lost is the independence of the SEARCH, and the loss is invisible to every party but the reviewer)
    **Command:** `/coordinator`'s review launch, `beadloom review-brief <bead-id>`
    **Context:** BDL-069's review, `beadloom-qae9`, 2026-09-12. Filed by the coordinator against itself, after the reviewer reported it.
    **What happened.** `/coordinator` says the review prompt carries "the bead id and nothing else about the change", and that if a measurement must reach the reviewer anyway, the prompt must SAY so, "so the reviewer can record that the withholding was defeated. An undeclared paste is invisible to everyone including the reviewer." The coordinator's prompt carried three directed observations it had not derived: that `rules.yml` gained an exemption and one exit condition is a condition rather than a date; that `NodeSource`, the stale-pair count and the `ref_id` allocator are three duplicated rules replaced by one body; and that several beads added reports, a new gate leg and a new column in `impact`. None was declared as a defeat.
    **What the reviewer wrote, unprompted:** "Each is a directed pointer at a specific site. Nothing in this process counts them, and they converged me on where to look before I had looked. The findings below were all reproduced from the code, but the search order was not mine."
    **Why the rule as written cannot hold.** It asks the launcher to notice that it is about to defeat the withholding and to declare it. The launcher is the party least able to see it: a pointer feels like context, not like a leak, and the difference is only visible from the reader's seat. `beadloom review-brief` counts and reports the comments IT withholds — a number the reviewer reads — and has no way to see what arrived through the prompt beside it.
    **Measured about the neighbouring mechanism, in the same run:** `beadloom review-brief beadloom-qae9 --release` exited 1 and named its reason — every role in this repository writes under one tracker identity, so the gate cannot tell an independent verdict from the author's own. That check knows its own limit and says it. The prompt channel has no such check.
    **Expected:** the brief should state the channel it does NOT cover, the way every other instrument in this project names the boundary of its knowledge — "N author comment(s) withheld; anything the launch prompt carried is not counted here". A reviewer would then know the number it is reading is partial. A stronger form: the launch prompt itself becomes an artifact the brief can read, so pointers are counted rather than remembered.
    **Related:** #212 and #219 (the withholding defeated by the epic document and by commit messages), #284 (a rule held by attention rather than by a check).

    **PARTLY FIXED, re-measured 2026-09-29.** Fixed: the brief names the launch prompt as a
    channel it cannot see (`DEFEAT_NOTICE` and `CHANNEL_LAUNCH_PROMPT` in
    `application/review_brief/models.py`, 97e05047, BDL-068). Remains: nothing counts what a
    launch prompt carried, and a prompt is not a readable artifact. No bead holds this entry.

280. [2026-09-10] [MEDIUM] a room's `locale` dimension is the TEXT codec, and a run has a second one it never reports — the codec `argv` is decoded with

    **Severity:** medium (nothing on disk is wrong; three of PR #63's five red rows were reproducible on this laptop and two were not, and `beadloom rooms` reports no dimension that tells the two apart)
    **Command:** `beadloom rooms`
    **Context:** BDL-068 S6, `beadloom-0mdo.85`, diagnosing PR #63's red — two rows of `tests/test_locale_independent_io.py` that passed on the tree and failed on all six CI legs.
    **Measured on 2026-09-10,** Darwin 25.6.0 arm64 / CPython 3.13.7, under the knobs `ci.yml` sets on its locale leg (`LC_ALL=C PYTHONUTF8=0 PYTHONCOERCECLOCALE=0`): a child reports `locale.getpreferredencoding(False)` = `ascii` and `sys.getfilesystemencoding()` = **`utf-8`**. `beadloom rooms` in that same room prints `locale ascii` and nothing else about a codec. On Linux the same knobs make BOTH `ascii`. The census therefore describes the two rooms identically while they decode a command line differently, and the difference is not cosmetic: `subprocess` encodes `argv` with the parent's filesystem codec and CPython decodes it with the child's, so a source carrying `\xb1` crosses a command line in one room and is destroyed in the other.
    **The measurement that found it, from PR #63's own logs.** One defect, three shapes, all at byte offset 170 — the offset of the glyph in the probe: on `tests` (3.10-3.13) the parent's filesystem codec is `utf-8`, the child decoded `\xc2\xb1` as two lone surrogates at 170-171 and CPython refused the command; on `tests-locale (en_US.ISO-8859-1)` the parent's is `iso8859-1`, the child got ONE surrogate at 170 and refused it; on `tests-locale (C)` the parent's is `ascii`, so `os.fsencode` raised `UnicodeEncodeError` at 170 and no child was spawned at all. Both symptoms CI reported — a non-zero child AND an empty stdout — are one event, because a command that fails to decode prints nothing.
    **Where:** `application/rooms.py`. `codec_in_force()` reads `locale.getpreferredencoding(False)` alone and `locale_dimensions()` carries `locale` plus `locale_asked`; nothing in the module reads `sys.getfilesystemencoding()`. `docs/guides/parallel-waves.md` and `tests/room_simulation.py` both state that `LC_ALL=C PYTHONUTF8=0 PYTHONCOERCECLOCALE=0` "puts this process in the ascii room for real", which is true of the text codec and false of the filesystem codec.
    **Why it matters:** `beadloom-0mdo.50` made the locale leg enterable from a laptop, and that claim now covers half a room. This is the measurement of the other half: of PR #63's five red rows, the three that depend on the TEXT codec reproduce locally in the C and 8-bit rooms and were simply never run there, and the two that depend on the FILESYSTEM codec cannot be reproduced on macOS at all. A census that reported both codecs would have said so before the PR was opened, instead of leaving a role to guess at the platform — which the launch prompt for `.85` records as four rounds already lost to this shape.
    **Expected:** carry the filesystem codec as a dimension of its own, so a Darwin run under `LC_ALL=C` reads `locale ascii, fs utf-8` and a Linux run reads `locale ascii, fs ascii`. A declared leg cannot supply the value — the image decides it, not the workflow — so the honest comparison is the census's existing not-entered direction: a leg whose image this run cannot describe is not a leg this run entered. Reporting the value for the CURRENT room alone would already be worth the change, because it is the fact a developer needs before believing a local reproduction.
    **Not fixed in `.85`,** which is a test bead: the two rows were repaired by removing the channel (`python -` with the source on stdin, where PEP 263 fixes the codec at UTF-8), and `_run_under` now refuses a non-ASCII `argv` word so no future row can rebuild it. That removes the defect and does not close this entry — the census still describes the two rooms as one.
    **Two of our own defects are the evidence, and they are fixed rather than filed.** `tests/test_verdict_room_census.py` asserted a leg declaring `locale="C"` is never entered, and `tests/acceptance/steps/test_room_locale_steps.py` declared `en_US.ISO-8859-1` as a constant in a scenario asserting the leg was NOT entered. Both are the class #249 named — a locale name written down is a room somebody can be in — and both asserted the opposite of what is true on the leg that exists for the dimension. The second reddened two further rows in `tests/test_bead14_s4_binding.py` as collateral, because that bead runs the acceptance suite in an inner pytest.
    **The dimension IS enterable, and not from macOS — which is the remedy this entry asks for.** Re-measured on 2026-09-10 in a Linux container under the leg's own knobs: a child under `LC_ALL=C` decodes argv with `ascii` and refuses byte `0x80`, and one under `LC_ALL=en_US.ISO-8859-1` decodes argv with `iso8859-1` and refuses nothing. Both are the room macOS cannot be. So the honest instruction a developer needs is not "reproduce the locale leg locally" but "reproduce it in a Linux image", and a census that reported the filesystem codec is what would say which of the two is required. A first attempt at this bead reported the container as unavailable because the Docker daemon was down; the daemon's state is not the machine's capability, and starting it took twenty seconds.
    **Related:** #249 (a locale NAME is not a room; the spelling `ci.yml` publishes is not one macOS has), #248 (the locale as a room dimension at all), #240 (the C room reaches an adopter rather than us).

279. [2026-09-10] [MEDIUM] `sync-update --yes --all` re-baselines the reference documents' SURFACE as well as the stale refs, and its help names only the second population

    **Severity:** medium (nothing is corrupted; a `warn` that had been standing on nine documents was cleared by a run whose stated purpose was the four stale refs beside it)
    **Command:** `beadloom sync-update --yes --all`
    **Context:** BDL-068 S6, `beadloom-0mdo.84`, running the standard fixpoint loop — revise the doc, re-baseline, re-run to a fixpoint — after a code change made four refs stale.
    **Measured on 2026-09-10.** `beadloom sync-check` at HEAD (`e1a082e`, my own changes stashed) reported rc 0, 453 pair(s) fresh, 0 stale, and NINE `surface drift` warnings: `README.md`, `README.ru.md`, `docs/architecture.md`, `docs/getting-started.md`, `docs/guides/bdd-scenarios.md`, `docs/guides/document-kinds.md`, `docs/guides/parallel-waves.md`, `docs/guides/project-overlays.md`, `docs/services/cli.md`. After `sync-update --yes --all` — run for four stale refs, none of them a reference document — sync-check reports **zero** surface-drift warnings. The run's last line does say `Re-baselined 9 reference doc(s).`, so it is disclosed in the output.
    **The gap is between the output and the help.** `--all` documents itself as "With --yes: re-baseline every currently-stale ref (for the fixpoint loop)", and the command's docstring adds "The claim is scoped to the pairs the run has grounds for — the STALE ones. A pair whose own file did not move is left unclaimed and its baseline stands." Both sentences are about pairs and refs. The reference-document surface is a third population, it is not stale, and nothing before the run says it will be touched.
    **Why it matters here rather than in general:** a surface warning is the only standing signal that a CLI, graph or `flow.yml` change may have left a hand-written guide behind, and one of the nine is `docs/services/cli.md` — the document the S6 review's Major 2 is about. Clearing nine of them as a side effect of a four-ref fixpoint moves a machine-checked signal into somebody's memory, which is the class this epic exists to remove, in the loop the epic's own roles are told to run.
    **Expected:** either scope `--all` to the stale refs its help names and give the reference-document re-baseline a flag of its own, or say in the help and BEFORE the run which documents will be re-recorded. The disclosure after the fact is not nothing, but it arrives when the record is already replaced.
    **Not fixed in `beadloom-0mdo.84`,** which is a fix bead for a different check; recorded with the nine names so the list survives the record that held it.
    **Related:** #245 (a line that fires on every run is discounted — this is the opposite, a line that stops firing for a reason unrelated to the document), #258 (freshness signals that cannot be taken in a clean room).

278. [2026-09-10] [MEDIUM] `setup-agentic-flow` writes `.claude/CLAUDE.md` and the four slash commands into a project whose flow declares `cursor` alone

    **Severity:** medium (nothing is lost and nothing is wrong on disk; the adopter is handed a second tool's entry point and four of its command files, and no check names them)
    **Command:** `beadloom setup-agentic-flow`
    **Context:** BDL-068 S6, found by `beadloom-0mdo.84` while fixing the role-map check's own tool population. The review that raised that fix (`beadloom-0mdo.70`, Major 1) stated as its premise that the check "builds a `CLAUDE.md` that `setup-agentic-flow` never wrote there". That half of the premise is false, and this entry is why: the command writes it.
    **Measured on 2026-09-10,** on a project built by `tests/adopter_flow.py`'s `CURSOR_ONLY` arrangement (`tools: [cursor]`), scaffolded through the same two calls the CLI makes — `generate_adapters(config, root)` then `scaffold(root, include_agents=False, config=config)`. Files present afterwards: `.cursor/agents/{dev,explore,review,tech-writer,test}.md`, `.cursor/rules/beadloom-flow.md` — and `.claude/CLAUDE.md`, `.claude/commands/{checkpoint,coordinator,task-init,templates}.md`.
    **Where:** `onboarding/agentic_flow_setup.py` — `scaffold()` composes the command set and calls `_scaffold_claude_md()` unconditionally. Only the role adapters are derived from `config.tools`, and they are derived by `role_adapters.generate_adapters`, which the CLI calls separately. The command's own help already describes the gated behaviour: "for `claude` to `.claude/agents/*` (+ `.claude/commands/*` + a per-project `.claude/CLAUDE.md`), for `cursor` to `.cursor/agents/*`".
    **Why it matters:** it is the tool-population class this slice has now found in three modules — `role_map` composed Claude's map for every project (fixed in `.84`), `orphaned_adapters` takes its tool population from a constant (#277), and this one WRITES for a tool nobody declared. The writer's direction is the one an adopter sees first, and it is the direction that makes the other two harder to reason about: a cursor-only project holds a `.claude/CLAUDE.md`, so "the file that project does not have" is not the argument for any of them. Nothing reports it either — `orphaned_adapters` reads the two agent directories and not `.claude/CLAUDE.md` or `.claude/commands/`.
    **Expected:** either gate the two artifact kinds on `"claude" in config.tools` and say so where the command already promises it, or state in the command's output and the SPEC that the Claude entry point is written for every project regardless of `tools:` and give the reason. The second is a defensible answer — `CLAUDE.md` also carries the per-project auto-regions — and it is currently neither taken nor written down, which is the defect.
    **Not fixed in `.84`, deliberately:** the fix is a behaviour change to the scaffold, whose write policy `beadloom-0mdo.67` settled eight days ago for a different question, and a bead about a CHECK's population should not also decide a WRITER's.
    **Related:** #277 (the same population as a constant, in the orphan check), #252 (the class the role-map check exists to close), #191 (the last time one command answered one question two ways).

277. [2026-09-09] [LOW] the orphan check's role population is the manifest and its tool population is a constant, and only the first is stated

    **Severity:** low (no third tool ships today, so nothing here can produce it; it reaches an adopter before it reaches this repository)
    **Command:** `beadloom config-check`
    **Context:** BDL-068 S6, `beadloom-0mdo.69` re-asking its questions of `beadloom-ec1a`, which reports the role adapters a dropped tool leaves behind.
    **Measured:** `orphaned_adapters` opens `for tool, agent_dir in TOOL_AGENT_DIRS.items()` and keeps a manifest row only when its parent equals one of the two directories that constant holds. With `tools: [claude]`, a manifest recording `.windsurf/agents/dev.md` and that file on disk, the check returns zero orphans and states no population it could not enter. The control is in the same run: `.cursor/agents/dev.md` under the same configuration IS reported.
    **Why it matters:** the docstring makes exactly this argument for the other axis — "a role a later release renames or retires is still reported, because the record of the write does not depend on the roles this release happens to compose" — and the code does not make it for tools. It also names its limits carefully and names only the deleted-manifest one, so a reader has been told where the check is blind and this is not in the list. The adopter who meets it is the one who scaffolded under a release that shipped a third tool and upgraded to one that does not.
    **Expected:** either the tool is derived from the manifest row's own directory, which is where the record of the write already is, or the constant's role as the population is stated beside the limit that already is.
    **Held by:** `tests/test_the_populations_the_last_four_beads_report_over.py`, `FINDING BDL-068.S6-9`, `xfail(strict=True)`, with the silence pinned beside it — the file on disk, the manifest row present, zero orphans. Verified by mutation: deriving the tool from the row's directory turns it red as XPASS.
    **Related:** #191 (one command answering one hand edit two ways), #268-#273 (this bead's other findings).

276. [2026-09-09] [MEDIUM] the ownership block's GitHub surface drops the caveat that says `unowned` is not a proof

    **Severity:** medium (the annotation surface is the one a pull request shows, and it is the surface the bead was built to make trustworthy)
    **Command:** `beadloom ci --format github`, which is the DEFAULT whenever stdout is not a TTY
    **Context:** BDL-068 S6, `beadloom-0mdo.69` re-asking its questions of `beadloom-0mdo.78`, which shipped the ownership report so a red nobody owns stops training a discount.
    **Measured on this tree, one run, three formats.** `--format json` carries everything: `claimed`, `none_owned`, 196 per-finding verdicts (31 `unowned`, 165 `unattributed`) and `unread_claims`. The rich block carries the `unowned` count with its nodes, the `unattributed` count, the `claimed:` clause and the sentence `2 of 2 claimed bead(s) declare a scope this run could not read, so 'unowned' is not a proof that nobody owns it`. The GitHub surface emits ONE line: `::notice::no finding of this run is owned by a bead claimed now`. Both claimed beads on this tree — `beadloom-0mdo.69` and `beadloom-txeq` — report `no_declared_refs`, so on that surface `unowned` is unqualified and its qualification is exactly what was removed.
    **Why it matters:** `_gate_ownership_notices` calls itself "the ownership block as GitHub notices — the same claim, one line each", and `gate_ownership_lines` states its own reason for existing: "three formats and one MCP tool quote it, and a second wording is how two surfaces of one run come to disagree". The emitter does not quote it. The lost sentence is the one that stops a reader concluding nobody owns 31 nodes when the truth is that nobody could be asked — which is `.78`'s own defect class, arriving inside `.78`.
    **Expected:** the GitHub emitter renders `gate_ownership_lines`, one notice per line, the way it renders the block it says it renders. The `unread` caveat travels with the headline or the headline does not travel.
    **Held by:** `tests/test_the_populations_the_last_four_beads_report_over.py`, `FINDING BDL-068.S6-8`, `xfail(strict=True)`, with a clause-by-clause comparison of the two surfaces pinned beside it. Verified by mutation: appending the caveat to the notices turns it red as XPASS.
    **Related:** #258 (a red that trains a discount — this is the same training through the missing caveat), #233.

275. [2026-09-09] [MEDIUM] a bead qualifies as a work item by depending on the plan, so a one-bead plan is held against the bead that blocks on it

    **Severity:** medium (the report is `derived`, its reason is empty and its line is reassuring; the population it describes is the plan's own bead)
    **Command:** `beadloom waves <bead>`
    **Context:** BDL-068 S6, `beadloom-0mdo.69` re-asking its questions of `beadloom-0mdo.83`, which shipped the population notice on the same day. The notice exists because three beads of this slice were lost by hand-listing ids (#274).
    **Measured on this repository's own tracker (870 beads):** `beadloom waves beadloom-0mdo.69` reports `every ready bead under beadloom-0mdo.70 is in this plan (0 of 1 bead(s) under beadloom-0mdo.70 are ready)`. `beadloom-0mdo.70` is the S6 REVIEW task. Its population is one bead — `beadloom-0mdo.69`, the bead the plan was asked about — because `beads_under` is a childless bead's own blockers and nothing else. The right answer is available and loses on size: for that plan there are exactly two candidates, `beadloom-0mdo.70` at 1 and `beadloom-0mdo` at 94, and `_narrowest` takes the minimum. `beadloom waves beadloom-0mdo.14` resolves to `beadloom-0mdo` correctly, because `.14` is a child and nothing blocks on it alone.
    **Why it matters:** the line is the reassuring form of the shape this epic exists to remove — a clean statement over a population of one, with `derived` true and no reason recorded. It is worse than silence, because a coordinator reading it has been told the plan holds everything ready under its work item. And it fires exactly where #274 happened: a plan of ONE bead, which is the single-bead wave this project runs constantly.
    **Expected:** a candidate work item has children. `beads_under` already distinguishes the two halves it sums — the parent-child closure and one dependency step — and a candidate whose closure is empty is a blocker rather than an item. Measured on the same tracker: under that rule `beadloom-0mdo.69` resolves to `beadloom-0mdo`, 94 beads, which is the answer `.14` already gets.
    **Workaround, in force:** name the item. `derive_population(..., work_item=...)` stops the search, and a caller that passes `--parent` is answered about the item it asked for.
    **Held by:** `tests/test_the_populations_the_last_four_beads_report_over.py`, `FINDING BDL-068.S6-7`, `xfail(strict=True)`, with the measured attribution and both candidates' sizes pinned beside it. Verified by mutation: restricting candidates to beads that are somebody's parent turns it red as XPASS.
    **Related:** #274 (the defect the notice answers), #245 (a line that fires on every run is a line its reader discounts — this one is the opposite failure, a line that reassures on every run).

273. [2026-09-09] [MEDIUM] a clean room states the CAUSE of its missing freshness baseline and never the population, and about forty verdicts in one epic were read as green over it

    **Severity:** medium (the instrument is honest and the claim is not, and the claim is what was written down forty times)
    **Command:** `beadloom clean-room <bead>` then `beadloom ci` inside the room
    **Context:** BDL-068 S6, `beadloom-uzck` measured it and `beadloom-0mdo.69` judged it. The clean room is the instrument every bead of two epics reports its verdict from.
    **Measured, twice, in two rooms:** `beadloom ci` reports `::notice::sync-check WARN: 0 pair(s) fresh, 450 NOT VERIFIED (no baseline — index rebuilt)`, while the same gate on the tree found the three stale pairs `beadloom-uzck`'s own change had created. Reproduced independently in `room-beadloom-0mdo.69` at the same numbers. A second step enters zero in the same room and says so as plainly: `scope-check SKIP: skipped — no branch is checked out`. The room's own report states the limit as a cause — "no .git, so a freshness check inside it has no baseline" — and carries no number, in both the human line and `RoomBuild.detail`.
    **Why it matters:** rc 0 with zero `::error` is what "green in a clean room" is written from, and it absorbs a `WARN` whose population was zero. This epic's own constraint is that the unresolved population is part of every answer, and 0 of 450 is that answer where "no baseline" is its cause.
    **Expected — and the three options are not equivalent.** The room must NOT carry a baseline: `.git` or the tree's index would import the freshness state the room exists to exclude, which is BDL-UX #243 in the other direction, and a room with no commits cannot hold a document-to-commit relationship truthfully. The room SHOULD hand over the number, because the project root is already in hand where the caveat is printed and a number is the form of a caveat that survives being skimmed. And the CLAIM must name it, because the claim is what forty verdicts were written in: "green in a clean room over N files, with doc freshness unverified over 0 of 450 pairs" is the same verdict, attributed.
    **Held by:** `tests/test_the_room_and_the_claim_it_supports.py`, `FINDING BDL-068.S6-6`, `xfail(strict=True)` on the room's clause, with the Gate's own honest line held beside it so a later simplification of either cannot remove the only place the population is stated.
    **Related:** #181 (a room's verdict is not the tree's), #258 (an expected red that trained a discount), #266 (the other thing the room's absent `.git` reaches), #243 (why a baseline must not be carried in).

272. [2026-09-09] [MEDIUM] the `focus-document` medium reads the first cell of every table row in the file, so its population is neither the bead table nor the bead column

    **Severity:** medium (a false red on a bead table that numbers its waves first, and a false green on a bead named only by a table about something else)
    **Command:** `beadloom waves`
    **Context:** BDL-068 S6, `beadloom-0mdo.69`. `beadloom-0mdo.75` shipped the medium so a wave states the document every bead of a work item writes, and `FocusDocument.row_cells` is documented as "the FIRST cell of every markdown table row in the file", justified as "the column an ACTIVE table names its bead in".
    **Measured, on projects built to be arranged differently:** with a bead table headed `| Wave | Bead | Status |`, the check reports `failed — 2 of 2 bead(s) of this plan write into a focus document no row of it names` about a document that gives each of them a row of its own. With a bead named only by a second table — `| Bead | Why it was not done here |`, the deferral shape this repository's own `active-table` documents — the check reports `passed — each writes a line of its own` about a bead the status table has no row for.
    **Why it matters:** both halves are claims about an arrangement rather than about the flow. The column is a convention, and the population is every table row rather than the bead table's. Measured on this repository: 0 of 58 `ACTIVE.md` documents carry a short-form bead id outside the status table, and 28 of the 58 carry no bead-status table `active_table.find_status_column` can find at all — including BDL-068's own, where the medium still collects 35 first cells from four other tables. So neither face can be produced here, which is BDL-UX #240's condition again.
    **Expected:** the medium reads the bead table, through the same reader `active-sync` locates it with — a header whose first cell is `Bead` followed by an alignment row — and reports a document that holds no such table as a population it could not enter rather than as rows.
    **Held by:** `tests/test_the_flow_checks_an_arrangement_that_is_not_ours.py`, `FINDING BDL-068.S6-5`, two `xfail(strict=True)`, one per face, each with the measured verdict pinned beside it.
    **Related:** #257 (the medium's own entry), #268 (the two readers this computation spends), #210 (the ambiguity `names_bead` already refuses to guess at).

271. [2026-09-09] [HIGH] a ledger file the claim reader drops is a free number, so the allocator hands out a number two writers then hold

    **Severity:** high (the collision the allocator exists to make impossible, produced by the allocator, silently)
    **Command:** `beadloom issue-number allocate`
    **Context:** BDL-068 S6, `beadloom-0mdo.69`. `beadloom-0mdo.66` allocates a number by `os.open(O_CREAT | O_EXCL)` of one claim file per number, and the file name IS the allocation.
    **Measured:** `read_claims` keeps a `*.md` whose stem matches `^(\d{1,6})$` and drops every other file in the ledger without reporting one. With a ledger holding `0003-the-clean-room-convention.md` and a log whose highest number is 2, `read_claims` returns `()`, `allocate_number` computes candidate 3, creates `0003.md` because that name is free, and returns 3. Two writers now hold #3 in two files. `check_issue_numbers` afterwards reports `claims=1` and one `unwritten-claim` — a finding about the wrong thing — and says nothing about the file it could not read.
    **Why it matters:** the name the reader drops is the name the module's own docstring invites. The claim file is described as "where the incident's body grows when the log becomes a composed view of the ledger", and a body grows a title. The failure is silent in both directions: nothing reports the unread file, and the number it holds is handed out as free — which is the mechanism BDL-UX #187, #211 and #253 were filed about, arriving through the door built to close them.
    **Expected:** a claim is the number at the start of the file name, so `0003-the-clean-room-convention.md` holds #3; and a `*.md` in the ledger that states no number at all is reported as a population the reader could not enter, never dropped.
    **Held by:** `tests/test_the_flow_checks_an_arrangement_that_is_not_ours.py`, `FINDING BDL-068.S6-4`, `xfail(strict=True)`, with the whole collision pinned beside it. Verified by mutation: relaxing the stem pattern to a prefix match turns it red as XPASS.
    **Related:** #187, #211, #253 (the collisions the allocator answers), #267 (the check's stated population).

269. [2026-09-09] [MEDIUM] a one-hyphen alignment row is valid GitHub Flavored Markdown and reaches the approved-node list as an axis named `-`

    **Severity:** medium (a finding against a document that is correct, in the list `scope-check` compares every commit against)
    **Command:** `beadloom docs quality`, `beadloom scope-check`, and the `docs-quality` step of `beadloom ci`
    **Context:** BDL-068 S6, `beadloom-0mdo.69`. This is BDL-UX #244's own class inside the component that was lifted to end it.
    **Measured:** `doc_sync/tables.py`'s `_SEPARATOR_CELL_RE` is `^:?-{2,}:?$` and demands two hyphens. GitHub Flavored Markdown's delimiter row holds hyphens with optional colons and one hyphen is a well-formed cell, so `|-|-|-|-|-|` is a valid alignment row that `table_blocks` returns as DATA. `read_axes_section` over a `## Axes` section written that way returns two rows where the document states one: `axis='-'`, `node=''`, `in_scope=None`, and `check_axes_section` reports it as `axis-without-a-scope-decision`. `application/active_table/table.py`'s `is_separator_cells` answers the same row correctly, so the two predicates disagree and the lifted one is the wrong one.
    **Why it matters:** the kept rows of the `## Axes` section are the approved-node list a commit is judged against, and a phantom row enters it. The document's author has no repair except changing a spelling their Markdown renderer is indifferent to. Nothing here produces it because this repository writes `| ------ |`, which is the arrangement question BDL-UX #240 records.
    **Expected:** `^:?-+:?$`. The predicate answers what the format defines rather than what this repository happens to write.
    **Held by:** `tests/test_two_readers_of_one_markdown_table.py`, `FINDING BDL-068.S6-2`, two `xfail(strict=True)` — one on the predicate and one on the section it reaches. Verified by mutation: widening the regex turns both red as XPASS.
    **Related:** #244 (the same class, first instance), #268 (the second reader that gets this right).

268. [2026-09-09] [MEDIUM] two readers of one markdown table row, and the component lifted so a third could not be wrong is one of them

    **Severity:** medium (0 disagreements on this repository's 259 planning documents, so nothing here can produce it; the two readers meet inside one computation and one document)
    **Command:** `beadloom waves`, `beadloom active-sync`, and every check that reads a `## Axes` section
    **Context:** BDL-068 S6, `beadloom-0mdo.69`. `doc_sync/tables.py` was lifted by `beadloom-0mdo.46` after two readers of one fact disagreed twice in one slice, and its docstring states the purpose: "a third reader cannot be wrong about it a third time" (#213, #244, #259).
    **Measured:** `application/active_table/table.py:33` splits a row with its own body — `stripped.strip("|").split("|")` — and carries its own separator predicate. It is older than the component and does not spend it. A shape derivation over the parsed source finds exactly four `split("|")` sites in `src/beadloom`: two are row readers and two belong to `guards/surface.py` and are about tool matchers. The two row readers answer three measured rows differently: `|` and `||` are not a row to `cells_of` and one empty cell to `split_table_row`, and `|| a | b ||` is four cells to the first and two to the second.
    **Why it matters:** the `focus-document` medium spends BOTH in one computation — it collects a document's rows with `tables.cells_of` and asks `active_table`'s `names_bead` about the cells it got — while `active-sync` reads the same document with `split_table_row`. A row written `|| beadloom-x.1 | dev | done ||` gives `active-sync` a bead id in its first cell and gives the medium an empty one, so one instrument updates that bead's status and the other reports that no row names it. Measured on this repository: 0 disagreements over 259 planning documents and 32 353 lines, 12 over 610 markdown files and 106 740 lines, every one of them a lone `|` inside a diagram. The divergence is invisible on this arrangement, which is BDL-UX #240's condition.
    **Expected:** one reader. `split_table_row` spends `tables.cells_of`, or the component absorbs it — the two bodies answer one question and the question has one answer.
    **Held by:** `tests/test_two_readers_of_one_markdown_table.py`, `FINDING BDL-068.S6-1`, `xfail(strict=True)`. `TestThePackageHasTwoReadersOfOneRow` derives the population from the source, so a FOURTH pipe-split has to be classified by whoever adds it.
    **Related:** #213, #244, #259 (the three times a table boundary was read wrongly), #272 (the medium that spends both).

263. [2026-09-09] [MEDIUM] the codec sweep's vocabulary is a list of call names, so a decoding call it has never seen reads as no call at all

    **Severity:** medium (the instrument reports clean about a population it did not enter, which is the class it exists to prevent)
    **Command:** `uv run pytest tests/test_locale_independent_io.py tests/test_decode_handlers.py`
    **Context:** BDL-068 S6, `beadloom-0mdo.66`. The allocator writes its claim file through `os.open(O_CREAT | O_EXCL)` and then `os.fdopen(handle, "w", encoding="utf-8")`, which is the first `os.fdopen` in `src/beadloom`.
    **Measured:** the shared definition in `tests/decoding_calls.py` recognises a text-I/O call by NAME — `read_text`, `write_text`, `open`, `decode` and five `subprocess` entry points. `os.fdopen` is in none of them, so both instruments walked past a call that decodes: the codec sweep did not ask it to state an `encoding=`, and the handler ledger did not ask what a decode failure there would do. It happens to state its codec, so nothing is wrong today — which is exactly why it is worth recording, because the next one need not.
    **The same run found the opposite error and it is already fixed:** `os.open` was read AS a text open, because `called_name` returns `open` for `os.open(...)` and the module-name guard only knew `tarfile`, `zipfile` and friends. That produced a false positive in both instruments at once and is closed here by `DESCRIPTOR_OPENERS` — the same shape as the `CONTAINER_OPENERS` note above it, which its own comment says was found the same way, by a call this package had never made.
    **Why it is not closed with it:** the false positive is a fixed misreading of a known name; this is an unknown name, and the repair is a different one. A vocabulary of call names cannot be completed by adding to it — `io.TextIOWrapper`, `codecs.open` and `csv.reader` over a text handle are all outside it too. The honest fix is the one this project applies everywhere else: report the population the sweep could not classify, so a call it does not recognise arrives as *unresolved* rather than as absent.
    **Expected:** `tests/decoding_calls.py` states what it did NOT classify, and the two instruments report that count beside their verdicts.
    **Related:** #173 (unverifiable is not clean), and `beadloom-0mdo.64`, which found `CONTAINER_OPENERS` by rooting the sweep at `tests/`.

260. [2026-09-09] [MEDIUM] `ACTIVE.md` is a shared write, and the property that makes it impossible is one writer per file — not generation

    **Severity:** medium (a design answer, filed at the coordinator's request rather than as a defect)
    **Tracker:** `beadloom-l9ee` — `bd show` it; the recommendation and its measurements are there in full
    **Measured:** BDL-068's `ACTIVE.md` is 1382 lines of which **35** are table rows (2.5%); across all 58 `ACTIVE.md` files, 5601 lines and 4868 of prose (87%). **Every measured collision is in the prose**, so generating the bead-status table removes 2.5% of the file and 0% of the collisions.
    **The finding that matters:** routing incidents to *this file* is a lateral move. `BDL-UX-Issues.md` is a single 3016-line file every bead appends to — 20 commits on one branch across four epics — and it has already produced the same collision: commit `27db92b`, "the duplicate number is mine, renumbered to #254". That is #257 with a different filename.
    **Recommendation:** every genre gets **one writer per file** and the composed view is a consequence — one file per decision (ADR), one file per incident **numbered by allocation rather than by an author reading the last number**, rules in the already-composed role cores, status generated from the tracker. An ADR's expiry needs no new machinery: make the record a doc-code pair, which is the ROADMAP's standing decision-provenance idea.

    **ANSWERED 2026-09-09 by `beadloom-l9ee` (BDL-068 S6), and this entry's own recommendation is corrected on two points.** The numbers above were re-measured on today's tree and hold: 1427 lines and 35 table rows (2.5%); 58 files, 5646 lines, 4913 of prose (87.0%).

    **First correction — this entry measured the wrong region of the file.** It measured the TABLE, found 2.5%, and concluded that composition buys nothing. It never asked where in `ACTIVE.md` the collisions were. The `Progress` section of BDL-068's `ACTIVE.md` is lines 64–1122: **1059 of 1427 lines, 74.2% of the file**, and it is a per-BEAD append — one sub-bullet per bead under its slice's bullet, written by that bead's own agent. Both `ACTIVE.md` collisions are there. `beadloom-0mdo.63` acquired the merge slot with `--holder`, waited, and lost 43 lines of its `Progress` entry into a neighbour's commit (commit `4753c17`'s message states it); `.73` and `.65` each wrote a `Progress` bullet in S6 wave 4. So the writer unit in the file that collides is the bead, and one-writer-per-file has a shape here that the 2.5% measurement hid. **Not taken by this bead** — it is `active-table`'s surface, not this bead's derived axis — and it is the finding to route.

    **Second correction — `beadloom-0mdo.66` has answered the "lateral move" objection, so this entry's central claim about `BDL-UX-Issues.md` no longer holds.** The evidence it cited was one thing: commit `27db92b`, two agents allocating one number in one shared file. That number is now allocated by `os.open(O_CREAT | O_EXCL)` against a ledger directory, and the collision class it names is closed. Re-measured on this branch: the log took **17 commits, +248 / −4 lines** — near pure append with no repair commit — against `ACTIVE.md`'s **22 commits, +735 / −395**. Realised collisions by file across this epic: 3 in per-bead prose (2 `ACTIVE.md`, 1 a domain README) and 1 the log's number, now fixed. **Migrating the log's 241 entry bodies to one file each would have prevented 0 of the 4.** That is the same standard this entry used to reject options 3 and 4, applied to its own recommendation.

    **So the body migration is NOT taken, and the reason is stated rather than deferred.** It costs one commit rewriting every entry body and every cross-reference in a 3155-line file, and it buys, today, no measured collision. What protects an entry's body meanwhile is not the layout but the ledger: a claim is a separate file that a lost write cannot take with it, so `unwritten-claim` reports an entry whose body vanishes. That protection reaches exactly the entries at or above the ledger's floor — **6 of 241 today** — and the check now says so, which it did not (#267). The migration becomes worth its cost when a body collision is measured, or when the floor's coverage is the thing being relied on; neither is true today.

    **The ADR genre is NOT shipped, and neither is the `decision` doc kind — deliberately, on this entry's own condition.** The condition it states is right and is not optional: a decision record must be a doc-code pair so it can go stale, or it is this log in a different folder. The pairing is `doc-sync` and `graph` machinery — a new doc kind, indexed into `docs`, paired by `sync_check` — and this bead's derived axis is `issue-numbers` alone. Shipping the directory without the pairing is the regression this entry warned about, so neither half ships here. The decision itself is recorded where this project already records decisions and already checks them, which is `CONTEXT.md`'s table.

    **PARTLY FIXED, re-measured 2026-09-29.** Fixed: `beadloom-l9ee` closed with the issue-log
    claim corrected, and the ADR was deliberately not shipped. Remains: the per-bead `Progress`
    section of ACTIVE.md is still a shared write, and no bead in the tracker holds it.

257. [2026-09-08] [HIGH] `waves` derived two beads' scopes as disjoint while one document belonged to both, and the landing lock ordered the commits it could not order the edits of

    **Severity:** high (it is the guarantee the wave plan exists to give, and the one it was believed to give while the lock was believed broken)
    **Command:** `beadloom waves`, `bd merge-slot`
    **Tracker:** to be attached to `beadloom-en0x`'s successor work; routed to S6
    **Context:** BDL-068 S6 wave 2. `beadloom-0mdo.37` and `beadloom-0mdo.68` ran concurrently on a plan `waves` reported as **0 serialisations**, and both edited `docs/domains/application/README.md`. `.37` committed the file whole in `fe02a46`, so `.68`'s hunk — the Gate's fourth silence — landed inside `.37`'s commit. Reported by `.68` unprompted.
    **The sentence that matters, in the finding agent's own words:** *"This is the guarantee the landing lock does not give — it ordered the commits, and nothing ordered the edits."* The content is correct and in the tree; the attribution is not.
    **Why it is not #232 again:** #232 was `waves` planning from an **authored** `refs:` line, and `beadloom-en0x` closed it — the scope is derived now. This is the derived scope being **narrower than the change**: `waves` resolves a bead to the nodes and files its *code* occupies, and a domain README belongs to a node whose code neither bead touched. So two beads can hold disjoint code scopes and one shared document, and the plan says 0 serialisations truthfully about the wrong population.
    **It is sharper than it looks because of what else moved this week.** BDL-UX #194 and #237 were withdrawn on 2026-09-04 when the merge slot turned out to work: `acquire` refuses a held slot at rc 1. So the project spent three epics believing the lock was broken and the scopes sound, and both beliefs were inverted — the lock works and orders commits; the scopes are sound about code and silent about documents.
    **Expected:** the derived scope reaches the documents a node owns, or the plan says which population it compared and which it did not. `beadloom waves` already prints four shared media it cannot decide by code independence; a fifth line naming the documents two beads share would be the same shape. Do not answer it by widening `refs:` — that is the authored scope #232 was filed against.

    **PARTLY FIXED, re-measured 2026-09-29.** Fixed: `waves` states a `focus-document` medium
    (`application/waves/media.py`, `beadloom-0mdo.75`). Remains: the measured case, a document
    owned by an ancestor node (`docs/domains/application/README.md`), is reached by neither
    ownership nor the medium, as `media.py`'s own docstring says, and no line names the documents
    two beads share.

246. [2026-09-04] [MEDIUM] a declared mutation target that no run ever covers passes every green Gate, and the one command that would say so is silenced by the flag its only caller passes

    **Severity:** medium (a declaration the Gate reports as satisfied while nothing measures it — a phantom gate with a name on it, in the feature built to remove phantom gates)
    **Command:** `beadloom ci`, `beadloom mutation --only`
    **Tracker:** `beadloom-0mdo.45`, routed to S6
    **Context:** BDL-068 S4's fix cycle. Measured on this repository, which is the one that shipped the feature: `doc_quality.py` and `doc_shape.py` were declared in `mutation.targets` in S3 and no run had covered either of them when this was written on 2026-09-04.
    **Issue:** three separate settings must agree before a declared target is measured, and Beadloom can see only one of them. `beadloom ci` calls `check_mutation_scope` — could a mutant run at this path — and never `report_mutation_score` — did one — because a score needs a stats file the tree does not carry. So a target declared and never measured passes every Gate this project has ever taken. The command that does report it, `beadloom mutation`, has `--only`, which prints the targets a run did not cover as "not judged by this run" rather than as `mutation-target-unmeasured`; the only caller in this repository is the nightly job, and it passed exactly the `--only` that suppressed the finding for those two targets.
    **Why the tool cannot simply check it:** whether a runner will mutate a path lives in the runner's own configuration — `[tool.mutmut] only_mutate` here — and reading that would make Beadloom own the runner, which CONTEXT Q5 declines. This repository's fix is therefore a repository test (`tests/test_mutation_runner_scope.py` now asserts both inclusions), and an adopter has nothing equivalent.
    **Expected:** what the product CAN check without owning a runner is whether it has ever seen a score for a declared target. `beadloom mutation --stats` could record the run it just judged — targets, score, tool, room, timestamp — under `.beadloom/`, and the Gate could then report a declared target whose last measurement is absent, or older than a stated age. That turns "declared" into "declared and measured on <date>", which is the distinction the feature exists to make and currently cannot.
    **Note:** `--only` itself is not the defect. A run that covers one slice of a larger scope is the normal state and saying so is right. The defect is that "this run did not cover it" and "no run has ever covered it" are printed as the same sentence.

    **PARTLY FIXED, re-measured 2026-09-29.** Fixed: `mutation.yml` passes no `--only`. The weekly
    sample passes all 15 declared targets as `--target`, a hand-copied list, and per-change runs
    use `--changed-since`. Remains: the Gate calls only `check_mutation_scope`, which asks whether
    a mutant could run, and nothing records when a target was last measured. No bead owns this
    half.

242. [2026-09-04] [LOW] the launch context a subagent receives carries a `git status` snapshot that is stale by construction, and one agent published from it

    **Severity:** low (recoverable, and it was recovered) — but it produced a withdrawn public sentence, which is the outcome this project spends the most effort avoiding
    **Command:** none — the agent harness's launch context
    **Context:** BDL-068 S4. Every subagent's launch context opens with a `git status` block captured when the SESSION started, not when the agent did. `beadloom-0mdo.34` measured its own: the block described branch `features/BDL-067` at `6fb5093` with three modified `src/` files, against a tree that was actually `features/BDL-068` at `3ec1db2` with none. Twenty-eight commits and five waves of drift.
    **Issue:** `beadloom-en0x` described the room its combined-tree verdict was taken in using that block instead of re-deriving the state, published the sentence, then caught it and withdrew it in `f45dd62`. The block is labelled as a snapshot, which is honest; what it is not is inert, because it sits where an agent looks first and reads like current state.
    **Why it belongs in this log rather than being shrugged off:** it is the same shape as everything else in BDL-068 — a fact that was true when it was written, presented without the reader being able to tell how stale it is. The difference is that the agent caught its own instance, which is what the flow is supposed to produce.
    **Expected, and it is ours to do rather than the harness's:** the role protocol says a tree fact is DERIVED at the moment it is stated, never read from launch context. `beadloom-0mdo.27`'s duty mechanism can carry that as a declared duty, which makes it checkable rather than remembered. Routed as a note on the S6 slice, not as its own bead.

232. [2026-09-03] [MEDIUM] `waves` plans from an authored `refs:` line, so two beads editing one document read as independent

    **Severity:** medium
    **Tracker:** `beadloom-en0x`
    **Issue:** `beadloom-0mdo.21` and `.26` both edited `docs/services/cli.md` concurrently; `waves` reported 0 findings. The graph knows the file — it is the `cli` node's spec — but `waves` compares the `refs:` each bead DECLARES, and both were authored from the CODE each would touch. The planner's input is authored while everything else BDL-068 built is derived.
    **Detail:** the full measurement, the reproduction and the fix shape are on the bead — `bd show beadloom-en0x`. This entry exists so the number is allocated and the finding is findable; the tracker is the source of truth for its text.

    **PARTLY FIXED, re-measured 2026-09-29.** Fixed: `beadloom-en0x` compares each declaration
    against the recorded `## Axes` (`unguarded_axis`, `declared_outside_the_axes`), and the
    `focus-document` and `graph-files` media name shared documents (#257, #261, #265). Remains: a
    bead's scope is still an authored `refs:` line, and a node's spec document is part of no
    bead's scope.

230. [2026-09-03] [MEDIUM] a branch whose name carries a suffix after the work-item key names no work item

    **Severity:** medium
    **Tracker:** `beadloom-bdnv`
    **Issue:** On `features/BDL-068-S2S3` the brief's work-item channel reads NOT INSPECTED while the reviewer was reading RFC.md and CONTEXT.md from that very folder. `declared_scope.py` matches a segment that EQUALS a key; it should match one that BEGINS WITH it, longest key wins. The coordinator's branch naming exposed it; the defect is real for any adopter whose branch names carry a suffix.
    **Detail:** the full measurement, the reproduction and the fix shape are on the bead — `bd show beadloom-bdnv`. This entry exists so the number is allocated and the finding is findable; the tracker is the source of truth for its text.

229. [2026-09-03] [MEDIUM] the brief sends the reviewer to the tracker export and does not name it as a channel

    **Severity:** medium
    **Tracker:** `beadloom-qil0`
    **Issue:** `git diff main...HEAD -- .beads/issues.jsonl` adds 16 record lines carrying 30 author comments and 81,270 characters, and the brief's own change inventory lists that file and tells the reviewer to read it. `models.py:170` asserted that a reviewer seeing `0 withheld` learns the author wrote nothing; on that run it was false by 31,544 characters.
    **Detail:** the full measurement, the reproduction and the fix shape are on the bead — `bd show beadloom-qil0`. This entry exists so the number is allocated and the finding is findable; the tracker is the source of truth for its text.

226. [2026-09-02] [HIGH] the pre-push Gate crashes on a full pipe and reports it as stale docs

    **Severity:** high
    **Tracker:** `beadloom-jwfc`
    **Issue:** `beadloom ci` writes its whole report through one `click.echo`; under `git push` stdout is a pipe whose buffer fills and the flush raises `BlockingIOError`. The hook then prints `Gate failed (docs stale / lint / coverage / doctor)` on ANY non-zero exit — measured against the same tree in the foreground: rc 0, zero error lines, 8186 tests passing. The bigger the honest report, the likelier the crash.
    **Detail:** the full measurement, the reproduction and the fix shape are on the bead — `bd show beadloom-jwfc`. This entry exists so the number is allocated and the finding is findable; the tracker is the source of truth for its text.

225. [2026-09-03] [HIGH] `impact` under-reports on `src/<one package>` beside code outside src/

    **Severity:** high
    **Tracker:** `beadloom-f7kb`
    **Issue:** The narrowing gap is compared against `src/<package>` rather than against the project, so Python outside `src/` is swept by nothing and declared by nothing, with `callers.resolved` and `co_writers.resolved` both True over a demonstrably partial answer. The commonest Python layout there is. Found by the S1 re-review with a red proof in the layout matrix's own form.
    **Detail:** the full measurement, the reproduction and the fix shape are on the bead — `bd show beadloom-f7kb`. This entry exists so the number is allocated and the finding is findable; the tracker is the source of truth for its text.

224. [2026-09-02] [HIGH] a new test file landing on an existing path deletes its scenarios and the suite goes GREEN over the wreckage

    **Severity:** high
    **Tracker:** `beadloom-hdky`
    **Issue:** `beadloom-0mdo.6` overwrote two of BDL-061 S6's acceptance files. Deleting scenarios REMOVES tests rather than failing them: 8026 baseline, 8087 after, +61 where 63 were added. `git status` showing ` M` where `??` was expected is the only thing that reports it; `scenario-coverage` cannot see that a file which held four scenarios now holds nine different ones.
    **Detail:** the full measurement, the reproduction and the fix shape are on the bead — `bd show beadloom-hdky`. This entry exists so the number is allocated and the finding is findable; the tracker is the source of truth for its text.

223. [2026-09-02] [LOW] 102 planning documents depart from the shape their peers keep

    **Severity:** low
    **Tracker:** `beadloom-l27n`
    **Issue:** Measured when the section checks were wired: missing-section 102 over 256 read, under `doc_shape`'s majority policy; a non-peer-relative policy over the same requirement gives 767. The 102 are the archive — old RFCs with no `## Overview`, old PRDs with no `## Impact`. Reported rather than suppressed by owner decision.
    **Detail:** the full measurement, the reproduction and the fix shape are on the bead — `bd show beadloom-l27n`. This entry exists so the number is allocated and the finding is findable; the tracker is the source of truth for its text.

222. [2026-09-02] [LOW] The independent cross-check states and computes an attribution rule the implementation stopped using

    **Severity:** low (it cannot fail against the regression it was written to catch, and it will one day fail against a correct implementation)
    **Command:** `uv run pytest tests/test_init_one_table_over_every_axis.py`
    **Context:** found by the ninth review pass of BDL-067 (`beadloom-e8s4.28`), filed rather than fixed under the epic's stop rule.
    **Issue:** invariant 3 of that module reads "the bug-report request appears exactly where THIS run wrote both the rules and the graph FILE the failing node came from". That was the key until BDL-067 `.24`; the shipped key is `_this_run_wrote_the_node_that_fails`, read at the NODE grain. `RunOutcome.corner` still computes the file-grain answer, under a docstring saying the case fails when the report and the tree disagree.
    **Measured:** over all ten red runs the table performs, both grains computed side by side, they AGREE in every cell. The agreement is a consequence of the ARRANGEMENTS, not of the rules: since `.21`, `generate_skeletons` annotates every node on disk, so a cell that rewrites `legacy.yml` also rewrites the failing node's own entry. The one tree where the two rules diverge — the file moves for a SIBLING while the failing node does not — is the tree the eighth review measured, and no cell of this table builds it.
    **Expected:** either compute the corner at the node grain here too (the module already digests `.beadloom/_graph/` before and after, so a `{ref_id: node}` digest is the same walk), or keep the file grain as a deliberately coarser instrument and SAY so — rename `wrote_the_failing_graph_file`, correct invariant 3 to name the node, and add one case asserting that the two grains coincide on this table, so the day they stop coinciding is the day it is noticed.
    **Why it is not merge-blocking:** the divergence tree is covered by two sibling classes, `TestTheGraphHalfIsAskedOfTheNodeAndNotOfTheFile` and `TestEachSentenceSpeaksAtTheGrainItsKeyIsReadAt`, which build it and would go red.
    **Tracker:** `beadloom-tgo8`.

221. [2026-09-02] [MEDIUM] Attribution keys on the whole node, so annotating a node makes its neighbour's failure read as ours

    **Severity:** medium (it asks an adopter for a bug report about a writer that did not run, on an ordinary tree shape)
    **Command:** `beadloom init --bootstrap` on a project carrying an inherited `.beadloom/_graph/legacy.yml`
    **Context:** the open question of BDL-067 `.24`, answered NO by the eighth review (`beadloom-e8s4.26`) and re-planned out on the reviewer's own recommendation.
    **Issue:** "is a node whose `docs:` field this run wrote a node this run wrote?" — not for this instrument. The instrument exists to answer whether this run produced the property that makes the node FAIL, and the failing rule reads `kind` and `part_of` edges. `docs:` is not a field the finding's rule can see, so answering yes attributes to Beadloom a failure Beadloom did not cause.
    **Measured:** an inherited `legacy.yml` holding ONE undocumented orphan still prints `(True, True)` — "This is a defect in Beadloom's bootstrap rather than in your project — please report it" — about a node no writer in this run produced. Single-node inherited graph files are at least as ordinary as the two-node case BDL-067 `.24` did close.
    **Expected:** key the node sample on a RULE-RELEVANT PROJECTION of the node, DERIVED rather than hand-listed — digest the node restricted to the fields the rule engine can read, taken from `graph/rules/loader.py`'s own authoring surface. A `docs:`-only annotation is then not a change the failing rule can see, while a `kind`, `source` or edge rewrite still reads as ours, so the created-or-CHANGED error direction is preserved rather than traded away. **Not** an exemption for a `docs:`-only diff: a filter over one named field goes stale the next time the block gains a writer.
    **Precedent:** `test_every_authoring_key_the_loader_accepts_has_a_type` holds `_detect_rule_type` to `graph.rules.loader.AUTHORING_KEYS`, so a rule dimension added later widens the projection by the same act.
    **Tracker:** `beadloom-0mb5`.

220. [2026-09-02] [HIGH] `init` still tracebacks on a graph file it cannot handle — N readers across four domains, each with its own policy

    **Severity:** high (a hand-edited or truncated file under `.beadloom/_graph/` makes the first command an adopter runs print a Python traceback instead of a message)
    **Command:** `beadloom init --bootstrap`, `beadloom init --import DIR`, `beadloom init` (all three wizard modes)
    **Context:** measured by BDL-067 `.24` after its own fix and widened by `.25`. **Pinned, not fixed** — it predates BDL-067 and BDL-067 did not close it.
    **What IS fixed:** the four readers of `.beadloom/_graph/*.yml` under `onboarding/` and in `setup.py` now share one skip policy (`onboarding/graph_files.py::each_graph_file`), so the traceback BDL-067 `.21` introduced in `doc_generator._load_graph_from_yaml` is gone.
    **What is NOT, measured over `init`'s own eight (entry point x mode) cells crossed with three shapes of a hand-edited `.beadloom/_graph/legacy.yml` — 24 runs, of which 15 reach the file and all 15 traceback:**

    ```
    a file that does not parse   -> yaml.parser.ParserError  application/reindex/indexing.read_declared_docs
    a top-level list             -> AttributeError           same reader (parses fine, dies on data.get)
    added: 2026-09-02            -> TypeError                graph/loader.load_graph (json.dumps, no default)
    ```

    **Issue:** N readers of the adopter's graph directory across four domains, each with its own answer to "what if this file does not parse". BDL-067 consolidated the four inside `onboarding` and could not reach the rest without crossing domain boundaries mid-fix-cycle. `graph/loader.py:186`, `graph/diff.py:220`, `reindex/change_detection.py:89` and `services/commands/index_ops.py:235` walk the same directory. The date shape is the reason a fix scoped to "unreadable YAML" would close two thirds of the class and no more: that file parses, and every reader `init` owns yields it happily.
    **Branch coverage, and why it adds nothing to the diagnosis:** `--yes` tracebacks on no shape, and not because a guard works — `non_interactive_init` returns `skipped` when `.beadloom/` already exists, and `--force` deletes the directory first. Every branch that reads the tree reaches the same two unguarded readers, which is why this is one decision and not four.
    **Expected:** decide once what every reader of a graph file does with one it cannot handle, then apply it. **Needs `/task-init`** — the same shape as #218, and for the same reason it is not a fix cycle.
    **Pinned, not silent:** `tests/test_graph_files_are_read_under_one_policy.py` asserts BOTH halves — the fixed frame is gone AND the second one is still there — so it fails the day somebody closes `indexing.py`, and no future reader of this repository can take "init no longer tracebacks" as true.
    **Tracker:** `beadloom-l22o`.

    **PARTLY FIXED, re-measured 2026-09-29.** Fixed: `beadloom-4ad3` (BDL-069) routed
    `read_declared_docs` through `each_graph_file`, so an unparseable graph file and a top-level
    list now finish at exit 0. Remains: a date scalar (`added: <date>`) still raises `TypeError`
    in `graph/loader.load_graph`, and `tests/test_graph_files_are_read_under_one_policy.py` pins
    that residue.

219. [2026-09-02] [HIGH] The review's withholding does not cover commit messages, which is where this project writes its accounts

    **Severity:** high (the better the commit message, the more completely the mechanism is defeated)
    **Command:** `beadloom review-brief`, followed by the review protocol's own `git diff <base>...HEAD`
    **Context:** found and declared unprompted by the seventh-pass reviewer of BDL-067 (`beadloom-e8s4.23`). The second structural defeat of this mechanism; #212 was the first.
    **Issue:** `git log main..HEAD` carries the author's full account in the commit bodies — on BDL-067 the `.21` and `.22` messages are longer and more specific than any bead comment, including `.22`'s explicit "FINDING for `.23`". Step 3 of the review protocol tells the reviewer to read the diff, so the account is one command away. `review-brief` reports "0 comments withheld" and is correct about bead comments while the account is fully available elsewhere.
    **Why it is worse than #212:** #212 was a coordinator handing over `ACTIVE.md`, fixable by changing the launch prompt, and it was. This one is not reachable by prompt discipline, because the protocol itself sends the reviewer to the diff and this project deliberately writes long, specific commit bodies.
    **Expected, and it is a decision rather than a patch:** (a) `review-brief` also withholds or summarises commit bodies on the reviewed range and says how many it withheld; or (b) the mechanism stops claiming to withhold and instead REPORTS what is reachable, so the reviewer can declare it — which is what both the `.16` and the `.23` reviewer did unprompted, and the only reason either leak is known; or (c) accept it, on the ground that independence on a re-review is not worth the cost and the first pass is the only one where it matters.
    **Related:** #212 (defeated through `ACTIVE.md`, fixed by prompt), #204 (`review-brief` reports "0 withheld" and cannot know what the coordinator's prompt contained). All three are one shape: an instrument that measures its own scope and is read as measuring the question.
    **Tracker:** `beadloom-tm76`.

    **PARTLY FIXED, re-measured 2026-09-29.** Fixed: option (b) shipped in 97e05047 (BDL-068 S2
    and S3). `commit_bodies_channel` reports the reviewed range's commits and their body-line
    counts. Remains: commit bodies are still not withheld, and `beadloom-tm76` is open with no
    decision recorded.

218. [2026-09-02] [HIGH] `init` holds three hand-written step sequences and no artifact states what the sequence is

    **Severity:** high (it is the class the seventh review pass found after six passes of fixing its instances one symbol at a time)
    **Command:** `beadloom init` (all four entry points)
    **Context:** re-planned out of BDL-067 by owner decision on the seventh review's diagnosis. **Needs `/task-init` and an RFC before any code** — the fix changes `init`'s control flow, and appending it as cycle 8 of a bug fix is what the re-plan rule ranked P0 in the ROADMAP exists to prevent.
    **Issue, quoted from `beadloom-e8s4.23`:** "Every instrument this epic has built ranges over ONE symbol's callers. Nothing ranges over one entry point's STEPS. `init` holds three hand-written step sequences — the `--bootstrap` branch inline in `setup.py`, `non_interactive_init`, `interactive_init` — and no artifact states what the sequence is. So the next divergence was a step that two sequences run and the third does not, and a step that runs once over one writer's output and is never revisited."
    **Three measured instances:** `auto_link_docs` is run by two of the three sequences, so doc-sync is off on the third; `generate_rules` is a second whole-graph artifact rendered from ONE writer's node list; and `--bootstrap` honours neither the existing-`.beadloom/` check nor `--force`, unlike `--yes`, so it re-bootstraps over an existing graph silently.
    **Expected:** declare what `init`'s sequence IS — one artifact the entry points share, or derive from — rather than fixing the sequences one divergence at a time.
    **Evidence that iteration had stopped paying:** majors per review pass on BDL-067 ran 2, 1, 1, 3, 4, 3, 5, 2, 2.
    **Tracker:** `beadloom-6i5q`.

217. [2026-09-02] [MEDIUM] An earlier `init --mode import` leaves domains that no later run will parent

    **Severity:** medium (the report is honest about it, and the adopter still has a manual repair with no reminder)
    **Command:** `beadloom init --yes --mode import`, then `beadloom init --bootstrap` on the same tree
    **Context:** found and named by BDL-067 `.17` as its own stated limit, reported rather than absorbed.
    **Issue:** `.17` made the verdict tree-level, which removed the REASON for the `--mode import` carve-out rather than the check. It does not parent the nodes an EARLIER import run already left in `imported.yml`. So the sequence the fifth review measured is narrowed, not closed: an import-only run followed later by a bootstrap still meets domain nodes that no run of this command parented. The report now names them honestly — it prints "the graph already in `.beadloom/_graph/`" and asks for no bug report — and the graph is still one the adopter repairs by hand.
    **Why `.17` stopped there:** making the bootstrap parent nodes it did not write means REWRITING A GRAPH FILE THE ADOPTER MAY HAVE AUTHORED. Every other fix in BDL-067 constrains what Beadloom writes about its own output; this one would have Beadloom edit an existing graph on the adopter's disk.
    **Expected — a decision, before any code:** (a) parent the orphans on a later run, which is structurally complete and edits a file the adopter may own; (b) report them and stop, which is honest and leaves a manual repair with no reminder; or (c) parent only nodes carrying provenance that Beadloom wrote them, which needs provenance the graph does not record today.
    **Tracker:** `beadloom-gv0z`.

215. [2026-09-01] [MEDIUM] The Gate reports an index problem as a rules configuration error

    **Severity:** medium (the headline names a file that is fine, the detail names the real cause, and the adopter reads the headline)
    **Command:** `beadloom ci --no-reindex`
    **Context:** found by the `beadloom-e8s4.12` sweep during BDL-067, on a scratch adopter with a **valid** `rules.yml` and no index.
    **Measured:**

    ```
    beadloom ci --no-reindex  ->  lint FAIL: rules configuration error
                                  (the same run's `why` carries `index not found at ...`)
    ```

    **Issue:** `application/gate.py:242-248` stamps `summary=RULES_CONFIG_ERROR` on **all three** `LintError` raise sites in `graph/linter.py`, and two of them are index problems rather than rules problems. The same prose appears in `src/beadloom/application/gate.py:61`, `docs/domains/application/README.md` and `docs/domains/application/features/ci-gate/SPEC.md:23` — the wrong summary is **documented as the behaviour**, which is how it survived review.
    **Expected:** the summary names what actually failed. Either distinguish the rules-parse raise site from the index raise sites in `graph/linter.py`, or derive the summary from the raise instead of stamping one constant on all three. The two documents are corrected in the same change; they currently certify the defect.
    **Why it is recorded as a class and not a typo:** BDL-067 found three instances of *a user-facing message asserting a fact the code knows to be false* — a comment counting monkeypatch bindings and calling them branches (#192 fix cycle 1), a message blaming Beadloom for the adopter's own rules (cycle 2), a withdrawal claiming a rule failed where none was evaluated (cycle 3). Each arrived the same way: careful reasoning about one shape, not carried across to the neighbouring shape. This is the fourth, one layer up, in the Gate every adopter runs. Three reviews found three of them and each was found only after the previous was fixed, which says the sweep is the deliverable and the individual fix is not.
    **Tracker:** `beadloom-uz8x`. Filed separately from BDL-067 by the same reasoning the owner applied to #214: a different defect on a different surface, deserving its own measurement.

210. [2026-08-27] [MEDIUM] `active-sync` resolves no row when a bead id is written as a Markdown code span, and blames the id

    **Severity:** medium (the reconcile exists so ACTIVE.md cannot drift from the tracker by hand; where it is inert, the drift it prevents is exactly what happens)
    **Command:** `beadloom active-sync [--check]`
    **Context:** found by `beadloom-viaj.8` while bringing BDL-062's own ACTIVE.md current before the 3.0.1 tag. The table said three closed beads were `blocked` and did not list `.10`, `.12` or `.13` at all — the drift the reconcile was built to stop, in the epic that shipped it.

    `_reconcile_one` passes `cells[0]` to `resolve_row_bead_id` verbatim, and `split_table_row` strips whitespace only. A bead id written as `` `beadloom-viaj.1` `` therefore arrives with its backticks and matches neither `bd_statuses` nor `_SHORT_ID`:

    ```
    resolve_row_bead_id("beadloom-viaj.1",   {...})  -> ('beadloom-viaj.1', None)
    resolve_row_bead_id("`beadloom-viaj.1`", {...})  -> (None, 'is not a bead id in either form')
    ```

    **Measured across this repository: of 29 ACTIVE tables carrying rows, 13 resolve NONE.** BDL-061's table resolves 81 of 84 because it writes `.1` bare; BDL-062's resolved 0 of 12 because it writes `` `.1` ``. The shipped template (`commands/templates.md.txt`) writes `BEAD-01` bare, so a project that never edits the template is unaffected — which is why this survived: it bites the house style, not the scaffold.

    **The message is the second half of the defect.** It says the cell *is not a bead id*, which sends the reader to the tracker. The cause is formatting, and the message can see the backticks it is complaining about.

    **Fix mode exits 0 while doing nothing.** `--check` returns 1 on drift, but plain `active-sync` — the form the pre-commit hook runs — returns 0 whether it reconciled 15 rows or 0, so a table that resolves nothing is indistinguishable at the hook from a table that was already coherent. Same shape as BDL-062's own subject one layer out: *unchecked is not clean, and the checker must say which.*

    **Expected:** strip a surrounding code span before resolving (one `strip("`")` on the cell); when a cell resolves only after stripping, say so rather than reporting it as an unknown id; and make a run that resolved zero of N rows reachable at the hook rather than reported at exit 0.

    **Workaround, applied to BDL-062's ACTIVE.md here:** write bead ids bare in the first column. Measured after the change: `resolved 15 of 15 row(s)`, 15 rows updated to the tracker's statuses.

    **PARTLY FIXED, re-measured 2026-09-29.** Fixed by `beadloom-0mdo.54`: a bead id in a code
    span resolves (`application/active_table/row_ids.py`), unresolved rows are classified by
    shape, and `active-sync --check` exits 1 on an inert run. Remains: fix mode, the form the hook
    runs, prints `resolved NONE` and exits 0, and the hook keeps only `withheld:` lines, so an
    inert table is still invisible at the hook.

209. [2026-08-27] [HIGH] `docs audit` verifies nothing in a non-English document and counts it as scanned anyway

    **Severity:** high (for an adopter who documents in their own language the fact check is inert, and nothing says so)
    **Context:** found while syncing README.md to the rewritten README.ru.md. The English README went RED on a keyword collision (#205) while the Russian one carrying the same true sentence stayed green. That asymmetry was the clue.

    **Measured** with the shipped `DocScanner` on both halves of one translation pair:

    ```
    README.md      fact mentions found: 1   {'mcp_tool_count': 1}
    README.ru.md   fact mentions found: 0   {}
    ```

    **AMENDED 2026-08-27, and the amendment narrows the claim I filed.** The BDL-064 writer measured what actually binds and I confirmed it: a **Latin-script** keyword reaches through Russian prose. `Сервер MCP отдаёт 18 инструментов` yields `mcp_tool_count=18`, and `_VERSION_RE` is language-independent — it had been catching the guides' `2.0.0` all along. So the audit is **not** blind to a non-English document. What is dead there is the English-*word* half of the table: `tool`, `rule`, `node`, `command`, `language`, `edge`, `test`.

    The measurement that produced the original filing — 0 mentions in `README.ru.md` — was true of that file and does not generalise the way I wrote it. A page that names a Latin-script term near its number is checked; a page that does not, is not, and the difference is invisible to the reader. That is still worth fixing, and it is a smaller and more precise defect than "verifies nothing".

    `DocScanner.FACT_KEYWORDS` is English by construction — `["MCP", "tool", "server tool"]`, `["rule type", "rule kind", "rule"]`, `["language", "lang", "programming language"]` and so on. A document written in any other language contains none of those tokens near its numbers, so no claim is ever extracted from it.

    **The document is not excluded.** It matches the `*.md` glob, enters the scan surface, and is counted among the files scanned. It simply yields nothing. So the audit's own summary — `20 mention(s) fresh` — is true and says nothing about the half of this repository's front page that cannot be checked at all.

    Every number in `README.ru.md` is therefore unverified: 18 MCP tools, under 2K tokens, 12 authoring keys, three documentation spaces. They are correct today because a person kept them correct.

    **Same class as the rest of BDL-062**, one layer out: a population that cannot be checked, reported in a shape indistinguishable from one that was. And it is worse for adopters than for us, because `.beadloom/flow.yml` already carries a `language:` key for flow documents while the audit has no notion of language at all.

    **Fix candidates.** (a) Per-language keyword tables, selected by a declared document language — the most work, the only one that actually checks. (b) Report the gap: a scanned document from which zero claims were extracted is named, so `N mention(s) fresh` can never stand in for a document nothing read. (c) Both. Candidate (b) alone is cheap and would have surfaced this years earlier, which is an argument for doing it first regardless.

    Related: #205 (keyword-proximity collisions), #206 (SPEC files excluded outright), BDL-063 (style checks for reader-facing docs, where the same language question returns).

208. [2026-08-26] [LOW] A module docstring can describe code that no longer exists, and nothing in this project can see it

    **Severity:** low individually; the point is that the class has no checker at all
    **Context:** `beadloom-viaj.11`, which fixed one instance and named two more it could not fix by the same method.

    **The inversion worth recording.** `doc_area.py`'s module docstring described `_common_prefix`, a function `.9` had deleted the same morning — while `docs/domains/graph/README.md:117` described the replacement `_source_root` **correctly**. The document was current and the code's own docstring was stale. This project's entire thesis is the other way round.

    **Why no check catches it:** a docstring is not a doc pair. It lives inside the file whose hash defines the pair's freshness, so **a file is always fresh with respect to itself.** `sync-check` cannot ever see this class, by construction rather than by omission.

    `.11` swept all **11** modules under `graph/rules/`, resolving the **32** symbols their docstrings name, and found 0 further dead *references* — now pinned by `tests/test_rules_docstring_references.py`. Two false hits are worth knowing for anyone building the same checker: in that package `` `__init__` `` names a module file rather than a symbol, and `FactSet.not_applicable` is a real dataclass field that `hasattr` cannot see, because `field(default_factory=…)` leaves no class attribute behind. A naive checker reports a live field as dead.

    **But the name-resolution sweep is the weaker half, and two findings prove it.** Found by reading, naming no dead symbol, catchable by nothing:

    - `graph/rules/evaluators.py` — its docstring claims it produces violations *"for every rule kind except cycles"*. False since `doc_area`, `summary_facts` and `scenario_coverage` moved into their own modules.
    - `graph/rules/__init__.py` — lists **4** submodules of **11**, a historical BDL-059 S3 list.

    Both left unfixed as out of scope for a docstring bead. They are the residue: a symbol-resolving checker finds *deleted names*, and prose goes stale without ever naming one.

206. [2026-08-26] [MEDIUM] `docs/**/features/*/SPEC.md` is excluded from `docs audit` outright, so declared facts drift freely there

    **Severity:** medium (SPECs are where a node's contract is written, and they are the one doc class nothing fact-checks)
    **Context:** `.7` swept 97 documents and found what `.4`'s narrower sweep could not reach.

    `scanner._EXCLUDE_PATTERNS` drops `docs/**/features/*/SPEC.md` and `docs/**/features/**/SPEC.md` from the audit's surface entirely. Consequence, measured by `.7`: **three forward references to `3.0.1`** — a release that did not exist — survived in SPEC files, the same defect `.4` had removed from `doc-sync/README.md:95` hours earlier. It removed the instance it could see.

    Also found in the same sweep: stale gate step lists in **eight** files, one naming a `coverage-lint` step that does not exist.

    The exclusion is presumably deliberate (SPECs are generated skeletons in some projects). But "excluded" and "verified" print the same way in the coverage report, which is this feature's whole subject one level up. At minimum the audit should name the class it does not read.

    **PARTLY FIXED, re-measured 2026-09-29.** Fixed: the audit names what it did not read. It
    prints `74 document(s) scanned, 52 not read`, and `--verbose` and `--json` name each SPEC with
    its built-in exclude pattern (f2e9d202, BDL-061 S2b). Remains: `docs/**/features/*/SPEC.md` is
    still excluded, so facts in SPECs drift unchecked, and whether to read them is undecided.

205. [2026-08-26] [MEDIUM] Writing a factually correct number can manufacture a false stale fact — keyword binding collides across senses

    **Severity:** medium (it punishes correcting documentation, which is the behaviour the tool exists to encourage)
    **Context:** `.7` hit this twice while fixing counts the reviewer had asked it to fix. `beadloom ci` went rc 1 on both.

    ```
    "supports 11 languages"          -> binds to language_count  = 1   (languages the PROJECT is written in)
    "Rules support 12 authoring keys" -> binds to rule_type_count = 15  (COUNT(*) FROM rules)
    ```

    Both sentences are true. Neither number is what the bound fact computes. The parser breadth of the code indexer is not "the languages this project is written in"; the count of authoring keys is not the count of rules.

    Note the near-miss that shows how fine the edge is: `architecture.md:133` uses the phrase "authoring keys" **safely**, because no `rule` token falls inside the five-word proximity window. The same phrase 254 lines later is unsafe. Whether a true sentence trips the audit depends on a neighbouring word.

    This is the general form of #193 (`framework_count`: web frameworks parsed vs nodes declaring a test framework) and #202 (`cli_command_count`: 34 top-level vs 43 recursive). Three instances now, in three subsystems — it is a property of keyword-proximity binding, not three coincidences.

    `.7`'s rule, which belongs in the writing guidance either way: **measure the audit's answer, do not predict it.**

203. [2026-08-26] [LOW] Two stated behaviours in `doc_area` survive mutation — the rationale is documented and observed by nothing

    **Severity:** low (both are supporting decisions, not headline behaviour)
    **Context:** the `.6` reviewer ran the mutation testing `.5` did not: 8 mutations, 6 killed, 2 survived the full 7257-test suite.

    ```
    _area_depth tie-break flipped shallower -> deeper   7257 passed, 0 behavioural kills
    _normalise  hyphen/underscore folding removed       7257 passed, 0 behavioural kills
    ```

    Both docstrings state a rationale; no test observes it. Folding is not load-bearing on THIS repository because the rule learns a per-area vocabulary — which is exactly the TRUE HERE IS NOT TRUE shape: it will be load-bearing on the first adopter whose directories are spelled the other way.

    The reviewer's judgement, which is worth keeping: the missing mutation run would have added precisely these — *"the supporting decisions nobody thought to neuter because they are not the headline. Low yield, real, and cheap enough that it should become routine rather than a bead-by-bead choice."*

202. [2026-08-26] [MEDIUM] One `beadloom ci` run prints two different numbers for "CLI commands" under one name

    **Severity:** medium (#193's collision, live for a second fact and already shipped)
    **Context:** `.6` review, M5.

    ```
    doctor : "CLI has 34 commands registered"   (top-level only)
    audit  : cli_command_count: 43              (_count_click_commands recurses into groups)
    ```

    Both call it "CLI commands", in the same run, to the same reader. Neither is wrong; they count different things under one name — the same defect shape as #193's `framework_count`, which BDL-062 `.4` resolved by renaming. This one was not caught because nothing compares two subsystems' facts to each other.

    **PARTLY FIXED, re-measured 2026-09-29.** Fixed: `beadloom ci` no longer prints both numbers.
    Its doctor step shows a check count, and its docs-audit step lists `cli_command_count` as NOT
    VERIFIED. Remains: the two counts still disagree under one name. `doctor` prints `CLI has 44
    commands registered`, and `docs audit` computes 55 recursively.

201. [2026-08-26] [MEDIUM] `--format porcelain` drops `message` — and porcelain is the default whenever stdout is not a terminal

    **Severity:** medium (the machine-readable path is the one that loses the distinction)
    **Context:** `.6` review, M2. Fourth instance of one class in one day. Measured on `warehouse-svc`, a project the reviewer built from scratch — not a fixture.

    `graph/linter.py:459-480` emits `rule_name:rule_type:severity:file_path:line:from_ref:to_ref` with no message field. So a `summary_facts` **total stand-down** and a **per-claim unverifiable** are byte-identical:

    ```
    summary-facts:rule_liveness:warn::::
    ```

    Everything distinguishing them lives in `message`, which porcelain does not carry — and `lint` selects porcelain **by default when stdout is not a TTY**, so every pipe, script and CI capture gets the collapsed form while an interactive run looks fine.

    Related and deliberately not merged: #198 (`sync-check` verified 0 of 363, Gate rc 0), #199 (the Gate's lint line reads identically for "checked nothing" and "one warning"), #197 (four rule types still hardcode `warn`). Four layers, one shape: **a reader cannot tell "checked nothing" from "nothing wrong".** BDL-062 fixed it at the rule layer and named it at the other three.

    Also here: `graph/linter.py:462`'s docstring states the format without `severity`, which the emitter does include (`m7`).

200. [2026-08-26] [LOW] An inert `docs_audit.ignore` triple is neither computed nor reported — the check exists one layer up and was never built here

    **Severity:** low (nothing is currently inert; the defect is that nothing would notice if something were)
    **Context:** found by `beadloom-viaj.5` while testing the seams between this feature's beads.

    `.4` retired the `context-oracle` suppression **by hand** after the `framework_count` rename made it inert, and measured the inertness by hand (0 framework-family mentions over 58 documents). Nothing in the product would have told it. `config_sync._suppression_drifts` performs the equivalent check for a different suppression surface, so the pattern exists in the codebase — it was simply never applied to `docs_audit.ignore`.

    Current state, measured: 10 triples, 59 documents, 41 mentions, **all live**. So this is dormant, and the only reason it stayed dormant is that a person swept it manually this morning.

    This is `rule_liveness` applied to a suppression rather than a rule, and BDL-061 established the contract: *a rule, exclusion or glob that cannot match anything reports itself.* An `ignore` triple is an exclusion. It was left out of that sweep.

199. [2026-08-26] [LOW] The Gate's lint line cannot distinguish "the rule checked nothing" from "the rule found one warning"

    **Severity:** low (the information is not lost — the annotation lines below distinguish them, and `beadloom lint`'s own summary carries the qualifier; the one line a CI reader scans does not)
    **Context:** found by `beadloom-viaj.5`. Third instance of one class in one day, at a third layer.

    `application/gate.py:240-244` builds the step summary as `"N error(s), M warning(s)"` whenever any violation exists. A rule that stood down over its whole population emits one liveness finding at `warn`, so the line reads `0 error(s), 1 warning(s)` — byte-identical to a run where one ordinary warn-severity violation was found.

    The code comment explains the intent, and it is the fix for the *previous* instance of this class:

    ```
    # an inert rule always emits a finding, so `rules_inert > 0` already flips
    # this summary to the "0 error(s), N warning(s)" branch (BDL-061.48/.49)
    ```

    That change made inertness visible as *not clean*. It did not make it distinguishable from *warned*. `beadloom lint`'s rich summary carries the `rules_inert` qualifier; the Gate drops it on the way to the line a person actually reads in CI.

    **Not fixed, and not blocking 3.0.1** — deliberately, with the reasoning recorded so it can be overruled. Unlike `beadloom-viaj.9`, where `lint --strict` exited **0** while a blocking rule checked nothing, here the Gate does warn and the detail is one line below. That is an ambiguous summary, not a false verdict. Related: #198 (the same shape at `sync-check`), #197 (four rule types still hardcoding `warn`).

198. [2026-08-26] [MEDIUM] `sync-check` verified 0 of 363 pairs and `beadloom ci` exited 0 — the shape `.9` just ruled unacceptable one rule below

    **Severity:** medium (the Gate is honest in words and green in its exit code; only the words distinguish "checked nothing" from "nothing wrong")
    **Command:** `beadloom ci` in a tree that is not a git work tree
    **Context:** found while verifying `.9`'s clean-room report, which is also how the procedural half came to light.

    **Measured**, `git archive HEAD | tar -x` with no `git init`:

    ```
    sync-check WARN: 0 pair(s) fresh, 363 NOT VERIFIED (no baseline — index rebuilt)
    beadloom ci rc=0
    ```

    With `git init` + one commit in the same extracted tree: 363 `ok`, rc 0.

    **The product is not lying.** It names the population, names the reason, and names three remedies — *"reindex incrementally on the existing index, run inside a git work tree, or attest the pair"*. By this epic's own standard that is correct behaviour: `unverified` is a distinct state and it says which.

    **What is questionable is the exit code.** `beadloom-viaj.9` decided, one layer down, that a rule which checks *none* of its population is a different fact from one with a partial gap — a total stand-down now carries the rule's declared severity, while partial inertness stays advisory. `sync-check` at the Gate has the identical shape and the opposite answer: 0 of 363 verified is a WARN, indistinguishable in `rc` from 362 of 363.

    Not obviously a bug. A tree with no git legitimately cannot be verified, and blocking there would punish an adopter for a checkout style. But the asymmetry is now deliberate-looking and is not deliberate, so it should be decided rather than inherited.

    **Procedural half, and the reason this was invisible for two epics.** The standing rule CLEAN-ROOM REVERT says to verify over `git archive HEAD` plus only the agent's files. Every such clean room was **structurally unable to verify a single doc pair** — 363 came back `unverified`, and any check reading `rc` rather than the summary line accepted it. Every "green in a clean room" claim in BDL-061 and in this feature was, on the doc-freshness axis, a measurement of the absence of git. The tool said so in words on every run. Nobody read the line. Corrected in BDL-062 `CONTEXT.md`; recorded here because the claims it weakens are spread across two epics' commit messages.

197. [2026-08-26] [MEDIUM] Four other rule types still report a TOTAL stand-down as `warn`, so an escalation still evaporates for them

    **Severity:** medium (it is #195's second defect, unfixed for every rule type but the one that was measured)
    **Command:** `beadloom lint --strict`
    **Context:** the named residual of BDL-062 `.9`. #195 established that a rule which could check NONE of its population must not report that at `warn` when the project declared it blocking, and fixed it for `doc_area_coherence`.
    **Measured:** `liveness_finding` now takes a keyword-only `severity` defaulting to `warn`. Exactly one caller passes anything else. `summary_facts`, `scenario_coverage`, `module_coverage` and `unregistered_feature_candidate` all still emit their stand-down at the default, so a project that escalated any of them to `error` gets the same evaporation #195 describes.

    **Why it was not simply fixed in the same bead.** Only `doc_area_coherence` was measured. Each of the others has to be checked for what its "total stand-down" actually means — `scenario_coverage` stands legs down individually, and a rule that is partly inert is a different case from one that is wholly inert, which is the distinction the fix rests on. Escalating four rule types on one rule's evidence would be shipping four untested changes inside a fix, which is the shape this epic exists to remove.

    **Expected:** decide per rule type whether its stand-down is total or partial, and pass the declared severity where it is total. The seam already exists and needs no further design.

    **AMENDED 2026-08-27 by BDL-062 `.14`, and the amendment is the reason it was P0.**
    The filing treated the four as one population differing only in which had been measured.
    They are not one population, and the difference is the shipped default: `summary_facts`
    ships `error` while `module_coverage`, `scenario_coverage` and
    `unregistered_feature_candidate` all ship `warn` (read off the dataclass defaults). So
    for those three the evaporation reaches only a project that deliberately escalated the
    rule, whereas for `summary_facts` it reached **every** project that enabled it — and
    that rule is new in 3.0.1, so the defect was about to ship at blocking severity for the
    first time. "Medium, unfixed for every rule type but the one that was measured" was the
    wrong reading of the same facts.

    `summary_facts` measured and fixed in `.14`. The stand-down is TOTAL in `.9`'s sense on
    four independent measurements: `SummaryFactsRule` carries no legs (name, description,
    severity — nothing a partial inertness could be about), `is_live` is false exactly when
    the whole population yielded zero claims, the guard `continue`s past both emitters, and
    the real linter reported `rules_inert=1` with one finding at `warn` and
    `has_errors=False` on a `rules.yml` carrying no `severity:` key.

    **What the fix costs, stated because `.9`'s "costs an adopter nothing" does not
    transfer.** A graph `beadloom init -y --mode bootstrap` produced from a two-module
    project has 0 of 3 summaries stating a checkable fact, so a project enabling this rule
    on a small graph now goes red where it went green. The opt-out is `severity: warn` on
    the rule. The alternative was worse and is what 3.0.0 would have shipped: the rule read
    no number, said so at `warn`, and left `lint --strict` at the same exit code as a run
    where every number checked out.

    **Still open, narrower than the original filing.** Three rule types, all shipping
    `warn`, each needing its own total-vs-partial measurement — `scenario_coverage` stands
    legs down individually and is the one most likely to be *partial* rather than total.

    **A second question `.14` found and did not fix.** `summary_facts` counts a claim it
    could not verify as evidence of liveness: `is_live` is `bool(agreeing + disagreeing +
    unverifiable)`. A graph whose every claim is unverifiable therefore confirms and
    contradicts nothing while `rules_inert` reports 0, and each claim is reported at `warn`
    naming its node. That is not `.9`'s false green — the findings are printed and each
    names a node — so it is recorded rather than changed, and the per-claim `warn` is
    deliberate: an unverifiable claim is a gap in what the PROJECT computes, not a summary
    contradicting it.

    **Related:** #195 (the measured half), #172 (rule liveness), BDL-062.

190. [2026-08-23] [LOW] `docs audit` reads a version mentioned as an EXAMPLE as a claim about this project — a doc cannot cite anybody else's version

    **Severity:** low (it is a false positive with an obvious workaround, and it blocks a specific and now-recurring kind of sentence)
    **Command:** `beadloom docs audit` / the `docs-audit` step of `beadloom ci`
    **Measured** while documenting BDL-UX #183. The sentence *"a JavaScript project at `0.4.1` was told `2.2.0`"* — an illustration of the defect being fixed, in backticks — failed the Gate twice: `doc-fact-stale: version: doc says '0.4.1' but project state is '2.2.0'`. `doc_sync/scanner.py::_extract_versions` matches every `\bv?\d+\.\d+\.\d+\b` outside a version pin and hands each one to an exact-match comparison against the project's own version; there is no notion of a version that is *about something else*.
    **Why it is worth an entry:** the sentences this blocks are exactly the ones this epic keeps needing to write — "an adopter at X was told our Y". It is also the version-shaped cousin of #169, which drew the token boundary for counts and left versions to their own regex. The workaround used in `.58` was to rephrase (*"a JavaScript project a major version behind was told ours"*), which is weaker prose than the measurement deserved. Recorded rather than worked around silently, because the next writer will meet it and reach for `docs_audit.ignore`, which is the wrong door.
    **FOURTH INSTANCE, 2026-08-26 (BDL-062 `.4`), and this one is the sharpest.** The bead that made the root node's `(vX.Y.Z)` a checked claim then added a line to `CONTRIBUTING.md`'s release process explaining WHY the bump matters -- *"rather than letting it drift the way it drifted from 1.5.0 to 3.0.0 unnoticed"*. `beadloom ci` went rc 1 on `CONTRIBUTING.md:253: version "1.5.0" -> 3.0.0`. The sentence describing the drift the release checklist exists to prevent is a sentence the checker cannot survive, and the workaround was the same weakening this entry already recorded: *"letting it fall two majors behind unnoticed"*, which does not say what the two majors were. Three instances were prose about the epic; this one is prose about the RELEASE PROCESS, which every adopter reads.

    **FIFTH INSTANCE, 2026-09-08 (`beadloom-0mdo.65`).** The bead recorded the room its verdict was taken in — `CPython 3.13.7`, which this epic's own verdict discipline requires — and `docs audit` read it as a claim about the project's version and reddened the Gate. That is a third face again: not an example token and not a past tense, but which INTERPRETER a measurement was taken under.

    **PARTIALLY RESOLVED 2026-09-09 by `beadloom-0mdo.63`, and the split is at the level of the FIX rather than of the prose.** A version is now attributed to the nearest subject NAME to its left inside its own clause (see #253). That absorbs every face of this entry where a name STANDS BESIDE the number — the fifth instance's `CPython 3.13.7`, and this entry's own "a doc cannot cite anybody else's version" wherever the other product is named. It does not absorb two faces, and neither is a difference in wording:

    - **A version behind a preposition.** In *"a JavaScript project at `0.4.1` was told `2.2.0`"* the subject is present but not adjacent, and the second number is this project's while the first is not. Measured over this repository's whole markdown population — 700 version tokens across 400 files — the tokens preceding a version are `bd`, `CPython`, `git` and `Python` on one side and `in`, `to`, `the`, `is`, `at`, `from`, `Phase`, `Implemented`, `Release` and `dated` on the other. Walking past the prepositions to find a subject means deciding that `Release 2.1.0` and `Implemented 3.0.0` name products, which turns a stale claim into silence.
    - **A version that is MENTIONED rather than used.** `v2.2.0` in `docs/services/cli.md` is the example of a token the extractor must not read, printed inside the sentence stating the rule. No subject stands beside it because the sentence is about the token itself. Its triple stands.

    The fourth instance above — `CONTRIBUTING.md`'s *"drifted from 1.5.0 to 3.0.0"* — is neither: it is this project's OWN past version, with no foreign subject anywhere to find, which is #205's subject and not an attribution question at all.

    **Expected:** treat a version as a claim about THIS project only when the mention is attributive — near a project-version keyword, or in a line that does not already name another subject — the same clause-scoping `.45` gave the count facts. Failing that, an explicit inline escape (a fenced block, or a marker) so a doc can quote a foreign version without a tolerance entry.
    **Related:** #169 (the token boundary for counts), #161, #253 (the attribution rule that absorbed the foreign-subject face), #205 (the past tense), BDL-057 (the audit surface).

    **PARTLY FIXED, re-measured 2026-09-29.** The PARTIALLY RESOLVED line above still holds.
    Fixed: `Measured under CPython 3.13.7` is no longer flagged. Remains: `a JavaScript project at
    0.4.1` is still read as this project's version, and `drifted from 1.5.0 to 3.0.0` gives two
    stale mentions.

187. [2026-08-25] [HIGH] External (steveyegge/beads): `bd list --json` returns a filtered view as a bare list, with nothing saying it filtered

    **Severity:** high (a consumer cannot tell a complete answer from a partial one, and the partial one looks complete) — **External**
    **Command:** `bd list --json`
    **Context:** found while fixing `beadloom-mr2l.84`, where the ACTIVE reconcile could never write `✓ done` for a closed bead. The lookup bug was real, but fixing it alone would have changed nothing.
    **Measured on this repository:**

    ```
    bd list --json                 → 38 rows   {open: 34, in_progress: 3, deferred: 1}
    bd list --json --status closed → 50 rows
    .beads/issues.jsonl            → 709 records
    ```

    **Issue:** the default omits every closed bead, and the payload is a **bare JSON list** — there is no envelope, so there is nowhere for the command to state that it filtered, and it does not. A program reading it receives 38 items that are indistinguishable from "all of them". Ours did exactly that.
    **Why it is HIGH despite being another project's default:** the human default is defensible (`list` shows open work). The machine one is not, because the caller is a program and the omission is silent. It is the same equation this log records against our own tools — a green result that describes the checker's ignorance rather than the state of the world — arriving through a dependency instead of through our code.
    **Expected:** with `--json`, either return everything and let the caller filter, or wrap the rows in an envelope that names the filter applied (`{"filter": {"status": ["open", "in_progress", "deferred"]}, "issues": [...]}`). A bare list is a shape that *cannot* carry the qualification the answer needs.
    **Ours to fix regardless:** any Beadloom code reading `bd list` must pass an explicit `--status` or read `.beads/issues.jsonl`, and must not treat the default as the tracker's contents. `beadloom-mr2l.84` did that for the reconcile; nothing sweeps the rest.
    **Related:** #97 (`bd close --suggest-next` lists still-blocked beads), #165 (`bd create` is O(N) processes), #174/#175 (unverifiable is not clean).

    **PARTLY FIXED, re-measured 2026-09-29.** Fixed on our side by `beadloom-0mdo.52`: every
    consumer passes `--all` (`services/commands/waves.py`, `docsync.py`), and
    `services/bd_seam/assumptions.py` records the assumption. Remains: upstream, `bd list --json`
    on bd 1.0.4 still returns a bare list of 50 rows with closed beads omitted. That half is
    External, like #97, and could move to Excluded Issues.

185. [2026-08-23] [LOW] SUSPECTED: a byte-identity assertion over a WAL-mode database may accuse the wrong thing — one occurrence, not attributable

    **Severity:** low, and deliberately filed as a SUSPICION rather than a defect
    **Command:** `tests/test_guards_parity.py::test_the_live_repo_index_is_byte_identical_after_a_real_evaluation`
    **Context:** the `.57` agent saw this fail once in three full-suite runs and refused to call it a flake and move on. Measured: it does not reproduce under identical ordering, passes 0/12 in isolation, and a stashed control gives only the usual two failures — so it is **not attributable**, and that is the honest state.
    **The hypothesis, which is precise and testable:** the live index runs in WAL mode, and the test compares the bytes of the main `.db` file. SQLite may rewrite that file on a read-only workload (checkpointing), so the assertion can fail for a reason that has nothing to do with the thing it exists to prove — that a guard does not write to the index (#147).
    **Why it is worth a low-severity entry rather than nothing, and rather than a bead:** a test that intermittently accuses the wrong cause is this epic's own subject, and the assertion guards a real invariant we depend on. But a bead written from one unreproducible occurrence would be a bead nobody can close. Recorded so the next occurrence has a prior, and so whoever meets it starts from the WAL hypothesis instead of re-deriving it.
    **If it recurs:** compare against `journal_mode=delete`, or assert over the database's logical content rather than the file's bytes, and check whether the `-wal`/`-shm` files should be part of the comparison at all.
    **Related:** #147 (the invariant this test guards), #168 (order-dependent ghosts in this suite).

184. [2026-08-23] [MEDIUM] `config-check --project <dir>` crashes with a raw sqlite error on a project that has no index — exit 1 with nothing on either stream

    **Severity:** medium (it is indistinguishable from a verdict, and it was silently corrupting a measurement while nobody noticed)
    **Command:** `beadloom config-check --project <dir>`
    **Context:** found by the `.57` agent while measuring a control case, and it is the manner of finding that matters: the agent was using a never-adopted project as a control to prove a fix did not over-report. The control's exit 1 was read as meaningful until it turned out to be a crash.
    **Issue:** on a project with no `.beadloom/beadloom.db`, the command dies with `sqlite3.OperationalError("unable to open database file")` and exits 1, printing nothing on stdout or stderr. A caller — a gate action, a script, an agent — sees a non-zero exit and no output, which is exactly the shape of a failing check.
    **Why it is worse than an ugly traceback:** an uninitialised project is a *legitimate, expected* state for this command, since `config-check` is one of the first things anyone runs. So the most likely first-contact experience with the command is a silent failure that reads as "your config is wrong" rather than "there is no index yet, run `beadloom init`".
    **Expected:** an absent index is an answer, not an exception — say so and exit on a code that means it (this is `unverifiable is not clean` again, from the caller's side rather than the checker's). At minimum, never exit non-zero with both streams empty: a verdict nobody can read is not a verdict.
    **Related:** #175 (a rebuilt index has nothing to compare against), #174, #146 — the same family, and this is the entry point.

179. [2026-08-23] [MEDIUM] How many rule types exist? Three documents give three answers and all of them are wrong

    **Severity:** medium (nothing is broken by it, but it silently scoped a P0 fix and would have left four rule types uncovered)
    **Command:** `beadloom lint`; `.beadloom/_graph/rules.yml` authoring
    **Context:** while implementing the rule-liveness fix (`beadloom-mr2l.48`), the agent found that the number of rule types is stated in four places and only one is right:

    | source | says |
    |---|---|
    | the bead brief (written by the coordinator) | 6 |
    | BDL-UX #172 | 6 |
    | `docs/domains/graph/features/rule-engine/SPEC.md` table | 7 |
    | `load_rules` dispatch | **9** (since BDL-051 S3a) |

    **Issue:** the agent counted against the loader rather than against any document, and covered all nine. Had it trusted its brief, four rule types would have kept counting clean while unable to match — the very false green the bead exists to close, shipped inside its own fix.
    **Why it is filed rather than left in a bead comment:** this is the third instance in two days of one fact with several sources and no owner — #171 (a bead's number in its own title vs. the id `bd` allocates), #177 (our `CLAUDE.md` vs. the vendored template), and now this. The recurring shape is that a *count* gets copied into prose, the code grows, and nothing compares them. It is also exactly what `docs-audit` exists for, which is the sharp part: the audit verifies counts against project state, and this count was never one of its facts.
    **Expected:**
    - Make the rule-type count a `docs-audit` fact, derived from the dispatch. The mechanism already exists; this number simply was not registered with it.
    - Correct the SPEC table and #172's text to nine.
    - More generally: a number that appears in both code and prose is a fact to be audited, not a sentence to be maintained. #173 already showed the audit is weaker than it looks (a green result covered 1 declared fact of 9), so registering more facts and fixing the audit are the same piece of work.
    **Related:** #171, #177 (one fact, several sources), #172, #173.

    **RE-MEASURED 2026-08-26 (BDL-062 `.4`). Two of the three asks are now done; the third grew a reason nobody had.**

    ```
    facts.rule_type_count.value        = 15   # SELECT COUNT(*) FROM rules
    COUNT(DISTINCT rule_type)          = 10   # the types this repo uses
    graph.rules.loader.AUTHORING_KEYS  = 12   # the types that exist
    ```

    Three numbers, and the fact's name claims the wrong one of them. That is unchanged since this entry was written; only the values moved.

    *Done.* The SPEC table now lists all twelve keys, and its claim to be "checked against the loader's own dispatch" is true for the first time — `test_rule_engine.py::TestTheSpecTableIsCheckedAgainstTheLoader` asserts the Keyword column equals `AUTHORING_KEYS` and that the stated cardinal is `len(AUTHORING_KEYS)`. Both were proved to bite by dropping a row and by mis-spelling the count. The loader's authoring keys are named once, as `AUTHORING_KEYS`, and its own "must have exactly one of" message is built from that set rather than from a second hand-written list.

    *Also done, and it was a second reader of the same stale knowledge:* `onboarding.scanner.rules_gen._detect_rule_type` mapped seven of the twelve keys, so `.beadloom/AGENTS.md` described three of this repository's fifteen rules to every agent that reads it as kind `(unknown)`. All twelve are mapped, and `test_every_authoring_key_the_loader_accepts_has_a_type` holds the map to `AUTHORING_KEYS`.

    **The new reason, and it is the sharp part.** The SPEC had said "the **ten** authoring keys" since the count was ten — spelled as a word. `_iter_number_tokens` reads digits, so a number written in letters is invisible to `docs audit`. The type count went stale twice (`doc_area_coherence`, then `summary_facts`) and no check could see it either time, while the instance count in the same sentence — written as a digit — was caught on the first run. So this fact is not merely misnamed: **a document can hold a stale number indefinitely by spelling it out**, and `unreadable_reason` does not name that limit. Matching number words would swamp the extractor with ambiguity, so the fix is probably not there; but the gate currently says nothing at all about it.

    **Still open, unchanged:** rename `rule_type_count` to `rule_count` with keywords meaning "rules this project declares", and give the type count its own fact if it is worth auditing. It remains a breaking change to `docs_audit.tolerances` / `docs_audit.ignore` keys in every adopter's config, which is why it is still a bead of its own. BDL-062 `.4` did exactly the same rename for `framework_count` -> `nodes_with_framework` (#193), so the shape of the work is now demonstrated rather than proposed.
    **MEASURED AGAINST THE FIXED AUDIT (`beadloom-mr2l.45`, 2026-08-24), and it changes the ask.** Registering the fact is necessary but NOT sufficient here, for two reasons the coverage report makes visible: (1) the document that states the number — `docs/domains/graph/features/rule-engine/SPEC.md` — matches `docs/**/features/*/SPEC.md` and is **never scanned**, so a registered fact would still read `not_covered` while the SPEC drifted; (2) the existing `rule_type_count` fact is a MISNOMER — it counts rows in the `rules` table (12 configured rules on this repo), not the loader's nine dispatch KINDS, and `FACT_KEYWORDS` maps `rule`, `rule type` and `rule kind` all to that one fact. Registering the dispatch count therefore means splitting the keywords and renaming the existing fact, which is a breaking change to `docs_audit.tolerances` / `docs_audit.ignore` keys in every adopter's config. That is a bead of its own, not a line in #173's fix.

    **PARTLY FIXED, re-measured 2026-09-29.** Fixed: the SPEC table and the AGENTS.md map are
    checked against `AUTHORING_KEYS`. Remains: `_collect_rule_type_count` in `doc_sync/audit.py`
    still counts rows of the `rules` table, so `rule type count` equals the rule count (19), and
    feature SPECs are still excluded from the scan. No open bead holds the rename.

178. [2026-08-23] [HIGH] 🔴 A REQUIRED check reports `pass` while its own output says it verified nothing

    **Severity:** high (it is in the required set, so it is load-bearing for merge, and the failure mode is the one the whole S2 slice was about)
    **Command:** the `ai-techwriter` GitHub Actions job
    **Context:** observed on PR #34 (BDL-061 S2). The job's own log line reads:

    ```
    ! could not run (infra) — docs were NOT checked on this PR;
      re-run before relying on freshness
    ```

    and the job's conclusion is **pass**, which GitHub reports as a green required check.
    **Issue:** the job is admirably honest in its *text* — it names the failure, says what was not checked, and tells the reader what to do. Then it exits 0 and everything downstream sees green. Nobody reads a passing check's log. The honesty is placed exactly where it cannot be acted on.
    **Why it is filed at HIGH rather than as CI housekeeping:** this is the same defect S2 spent nine beads on — a green result that describes the checker's own inability rather than the code's health — sitting in the check that guards the promise the product is built around ("no code reaches `main` without current docs"). Two `tests-locale` legs on the same run were **red on purpose** and are *not* required; a check that could not run was **green** and *is* required. The signalling is inverted.
    **Expected:** an infrastructure failure is not a pass. Either fail the job (so the required check blocks and a human re-runs it), or report `neutral`/`skipped` so it is visibly not a verification — never `success`. If the intent is "do not block on flaky infra", that is a decision about whether the check should be required at all, and it should be made explicitly rather than implemented by exiting 0.
    **Related:** #174, #175 — same equation (*unverifiable is not clean*), this time in our own CI rather than in the tool.

176. [2026-08-23] [LOW] An incremental `reindex` prints `Imports: 0` and `Rules: 0` on the run that refreshed them

    **Severity:** low (cosmetic, but it is a zero printed by the command whose honesty BDL-061 S2 restored)
    **Command:** `beadloom reindex`
    **Context:** found by the S2 review while watching the incremental path catch an injected boundary violation — the run genuinely re-extracted imports, and its summary said it had indexed none.
    **Issue:** `ReindexResult.imports_indexed` and `.rules_loaded` are only populated on the `--full` path (`application/reindex/full.py`), while the incremental path calls `reindex_file_imports()` without recording a count, so the CLI's `Imports:` / `Rules:` lines print the dataclass defaults. A reader cannot distinguish "no imports were touched" from "imports were refreshed and nobody counted them".
    **Expected:** either backfill both counters to the live DB totals on the incremental path — the fix #112 already applied to `Symbols:` for exactly this reason — or label them as per-run deltas and omit them when the path does not compute one. Same shape as #148: a number whose meaning depends on which path produced it.
    **Related:** #112 (closed, BDL-047 — the identical defect on `Symbols:`), #148.

168. [2026-08-22] [MEDIUM] `pytest-randomly` produces failures no seed reproduces, and nothing in the output says the order was random

    **Severity:** medium (agent-facing: a ghost failure costs a full investigation cycle, and the log is the only place that would have warned)
    **Command:** `uv run pytest`
    **Context:** during BDL-061 S1 an adversarial run reported 30 failures; five different seeds plus `-p no:randomly` all reproduced the same 3. The 30 were an artefact of ordering interacting with on-disk state (the index DB and its `-wal`), not of the code under test.
    **Expected:** pin a seed in CI and in the pre-push Gate so a red run is reproducible by construction, and keep randomisation for a separate scheduled job whose whole purpose is to find order dependence. A random-order failure that cannot be replayed is not a signal anyone can act on.
    **Related:** #147 / `.29` friction 3 — a stale `beadloom.db-wal` left by an earlier command is one of the shared-state channels that makes ordering matter.

    **PARTLY FIXED, re-measured 2026-09-29.** Fixed: the main shared-state channel is gone,
    because since BDL-074 (`beadloom-qq6m`) no test reads the live index. Remains:
    `pytest-randomly` is still a dev dependency in `pyproject.toml`, and neither `ci.yml` nor
    `addopts` pins a seed. pytest-randomly prints its seed in the header, so "nothing in the
    output says the order was random" was never quite accurate.

167. [2026-08-22] [LOW] `sync-check` prints one `[stale]` line per pair, so a single stale doc reads as a wall of 28 identical lines

    **Severity:** low (pure signal-to-noise, but it lands on every agent at every gate)
    **Command:** `beadloom sync-check`
    **Context:** one doc with many watched symbols emits one line per pair. The output is 28 lines that differ in no visible way, and the count of distinct DOCUMENTS needing attention — the number the reader actually wants — has to be derived by eye.
    **Expected:** group by document: one line per doc with the pair count and the reasons, and the per-pair detail behind `--verbose` or `--json`.
    **MEASURED AGAIN AT GATE SCALE (BDL-061 S2b, 2026-08-24), and it is worse than filed.** The combined tree of a four-bead wave reported 28 stale pairs, all of them the SAME document (`docs/domains/onboarding/README.md`) — because `symbols_hash` is per `ref_id`, one changed file makes every sibling pair of that node stale. The Gate's output, `beadloom sync-check`'s output and `beadloom doctor`'s output each carried 28 near-identical lines, so the reader's first question — *is this one document or twenty-eight?* — could only be answered from `--json`. At gate scale the noise is not merely low signal-to-noise: it misrepresents the SIZE of the problem, which is what a reader decides how to spend an hour on.

    **PARTLY FIXED, re-measured 2026-09-29.** Fixed: freshness is per file since
    `beadloom-mr2l.78` (#182), and each line names its code file, so one change no longer prints
    28 identical lines. Remains: the report is one line per pair with no grouping per document,
    and a copy of main printed 533 lines.

166. [2026-08-22] [MEDIUM] Adding one CLI command drifts six reference docs, and `sync-update --all --yes` does not cover them

    **Severity:** medium (the bulk escape hatch does not cover the surface that most often drifts in bulk)
    **Command:** `beadloom sync-update --all --yes`, `beadloom sync-check`
    **Context:** adding a single command (`beadloom guard`) put six `watches: cli` documents into `surface_drift`. `sync-update --all --yes` re-baselines hash/symbol pairs but not the reference-doc surface-drift path, so each of the six needed an individual `sync-update <ref>` — six commands to record one fact that was already known.
    **Expected:** `--all` should mean all, or say plainly which surfaces it does not cover. Ideally a surface change touching N reference docs is one attestation with N consequences, not N attestations.
    **Related:** #163 — bulk re-baselining is exactly the operation that needs to be recorded rather than made frictionless, so the fix here should count these, not just make them faster.
    **RE-MEASURED (BDL-061 S2b, 2026-08-24): the second half no longer holds, the first half does.** `sync-update --all --yes` DOES clear the reference-doc path — `_mark_synced_noninteractive` calls `mark_reference_synced(conn, None, project_root, all_docs=True)` and reports the count (measured on this repository at the close of S2b: `Re-baselined 7 reference doc(s)`, clearing all six drifted entries in one command) — so the six-commands-for-one-fact friction is gone. What remains is the shape: adding the single flag `sync-check --record-surface` drifted all six `watches:` documents at once, and the bulk form clears them with no record of which six were re-read. That is #163's objection, not a convenience one, and it is the half worth fixing: one attestation with N consequences should say what it attested to.

    **PARTLY FIXED, re-measured 2026-09-29.** Fixed: `sync-update --all --yes` clears reference
    docs, as the 2026-08-24 re-measure says. Remains: it prints only `Re-baselined N reference
    doc(s).` and never names the documents it re-attested (#163, #279).

163. [2026-08-20] [MEDIUM] `sync-update` can re-attest a doc nobody read — re-baselining silences `sync-check` without evidence

    **Severity:** medium (the freshness guarantee quietly weakens to "the hashes were reset", which is not what a green sync-check is read to mean)
    **Command:** `beadloom sync-update <ref>`, `beadloom sync-check`
    **Context:** `sync-check` compares hashes and `sync-update` resets them; nothing records whether the DOC was read or revised. During BDL-060 S4 this happened repeatedly — a dev change re-stales a domain doc, the baseline is reset to keep the gate moving, and the prose drifts silently. Concretely: the `vitepress-site` guide still described the landscape as "an interactive Mermaid diagram" and called Cytoscape "a follow-up" **after** the slice that shipped Cytoscape, while `sync-check` read 0 stale throughout.
    **Two distinct holes, needing different answers:**
    - **Prose with no pair.** A guide anchored to no symbol can never go stale. The only signal today is the opt-in, coarse `reference`/`watches` mechanism (BDL-057). Either make `watches` discoverable (warn when a `docs/guides/*.md` declares none) or let a doc watch a NODE rather than a symbol surface.
    - **Blind re-baseline.** Re-attesting without touching the doc is *sometimes* legitimate (an internal rename the doc never mentions), so it cannot be forbidden. Instead RECORD it: per pair, count re-baselines where the code symbols changed and the doc file did not. A high count means "attested but never revised" — a staleness SUSPICION the gate can surface as advisory. That is honest: it does not claim the prose is wrong, it says nobody has looked while the code moved underneath.
    **Related:** #161 catches a phantom symbol name; this catches prose that stopped being true while every number in it stayed correct.
    > Tracked as a bead (P2).

162. [2026-08-20] [HIGH] 🔴 `doctor` should audit the PRODUCED graph, not just the code — island / unexplained-leaf / claim-without-evidence

    **Severity:** high (this is the generalization of four defects that shipped past a full role cycle and a green gate)
    **Command:** `beadloom doctor`, `beadloom ci`
    **Context:** #144, #157, #159 and the dropped `uses` edges all survived dev + test + review + tech-writer beads and a 6/6 gate. They share one shape: **every test verified a FUNCTION, and none verified the CLAIM the produced graph makes.** The graph asserted "this node depends on nothing" and nothing asked whether that was true. All four were found by a human clicking a node and asking exactly that; the audits that confirmed them were written by hand, ad hoc, at roughly ten lines each.
    **Proposed checks** (each measured on this repo during the S4 dogfood):
    1. **Code island** — a node with no first-party dependency in either direction whose files nothing references. `doctor`'s `isolated_nodes` cannot catch it, because `part_of` makes such a node look connected. Would have caught #160. Measured: exactly one true island, so the check must respect declared `uses` edges and non-code sources or it cries wolf.
    2. **Unexplained leaf** — a node reporting no outgoing dependency while its own files DO contain first-party imports. Every legitimate case is explainable (a true leaf imports nothing first-party; a container's only such imports are its `__init__` re-exporting its own parts). Anything else is an attribution bug. Measured: 30 of 64 nodes empty, all explained, zero unexplained.
    3. **Claim without evidence** — the inverse: a node claiming a dependency with no first-party import behind it.
    **Design notes:** these assert things about the ARTIFACT, so they belong in `doctor` (graph integrity), not `lint` (architecture rules). Ship as WARNING first — on an unfamiliar graph the island check will produce false positives until `uses` declarations catch up, and turning an existing project red on upgrade is the failure mode this log keeps recording against us. **The audits must not reuse the attribution helper they are auditing**, or a bug hides in both; the manual cross-check during the session used `grep` for exactly that reason.
    > Tracked as bead `beadloom-uxqc` (P1).

161. [2026-08-20] [MEDIUM] `docs audit` checks numeric facts but never checks that a documented identifier still exists

    **Severity:** medium (documentation can name a function the code no longer has, and every gate stays green — the failure mode this project exists to catch, in the gate's own blind spot)
    **Command:** `beadloom docs audit`, `beadloom ci`
    **Context:** While narrowing the `surface_registry` port from CLI+MCP to CLI-only, two functions were deleted from the code and left in two documents. Both files passed `beadloom ci` 6/6 on the release branch. `sync-check` did not object because it compares hashes and the pair had been re-baselined after the edit; `docs audit` did not object because it verifies numeric claims (version, node/edge counts, CLI-command and MCP-tool counts) and has no notion of a named symbol. They were found by a ten-line ad-hoc script written for an unrelated reason.
    **Issue:** the audit answers "is this number still true?" but not "does this name still exist?". The second question is cheaper to answer and catches a strictly worse class of error: a stale number misleads, a phantom symbol sends the reader — or an agent — after something that is not there.
    **Expected:** extend `docs audit` with an identifier check — for each backticked `name(` in a tracked doc, verify a matching `def`/`class` (or a documented external API) exists in the indexed symbols, reporting the doc, the name and the node. Care is needed for legitimate references to framework APIs (`pop_screen` from Textual) and to prose that mentions a removed symbol deliberately, so the check likely wants the same `docs_audit.ignore` escape hatch, with a named reason.
    **Measured:** an ad-hoc version of this check over the release branch's 13 changed docs produced exactly one hit, and it was a correct reference to a framework API — so the false-positive rate on a real tree looks workable.

160. [2026-08-19] [HIGH] 🔴 AsyncAPI ingestion is documented as a capability but wired to nothing — `extract_payload_body` is reachable from no code path

    **Severity:** high (the docs promise an integration the product does not perform; a user pointing Beadloom at an AsyncAPI-described project gets nothing, silently)
    **Command:** `beadloom reindex` / `beadloom federate` on a project described with AsyncAPI
    **Context:** Found while dogfooding the BDL-060 S4 architecture map — the `asyncapi` node showed no dependency in EITHER direction. Verified independently of the graph: `grep` finds `src/beadloom/graph/asyncapi.py` referenced by **zero** other files under `src/`; only its two test files import it.
    **Issue:** the claim is explicit — `docs/domains/graph/features/federation/SPEC.md` says *"teams on AsyncAPI ingest the payload schema via the source-only `asyncapi.extract_payload_body` adapter"*, and the component DOC opens with *"Teams that already describe their AMQP messages with an AsyncAPI document…"*. What is true: the function works and is well tested (`test_asyncapi_ingest.py`, `test_asyncapi_fidelity.py`). What is false: that anything *ingests*. The loader never reads an AsyncAPI document, and nothing calls the adapter.
    **Why it survived:** this is the house failure mode one level up — not a check reporting success for work it did not do, but DOCUMENTATION claiming a capability the product does not deliver. It passed a dev bead, a test bead, a review bead, a tech-writer bead and a green gate, because every one of them verified the FUNCTION and none asked whether anything calls it.
    **Expected:** either wire it (the loader reads a configured AsyncAPI document per service and feeds `extract_payload_body` into the contract body, closing the claim) or correct the claim to "unwired building block" until that ships. The first is the real close — otherwise BDL-060 S3 delivers less than its SPEC states.
    **Related:** worth a machine check of its own — a **code island**: a node with no first-party dependency in either direction whose files nothing references. `doctor`'s `isolated_nodes` does not catch it, because `part_of` makes the node look connected. Measured here, `asyncapi` is the only true island (`ai_agents`/`ai-techwriter` are reached by subprocess, `vitepress-site` is not Python).
    > Tracked as bead `beadloom-g79p`. **DEFERRED by owner 2026-08-20** (P1→P2) — real but outranked; the adapter is inert, so nothing regresses while it waits. The implementation plan is recorded in `ROADMAP.md` under P1 → *"⏸ Deferred (planned, not scheduled) — wire the AsyncAPI ingestion path"* (`body_from:` declaration → loader resolution into the same body model → no silent no-op → determinism → end-to-end golden + an island guard → docs). What is NOT deferred is the honesty of the claim: if this slips much further, the federation SPEC sentence should be downgraded to "unwired building block".

158. [2026-08-19] [MEDIUM] No signal for a bounded context that is too large by SUBTREE — `max_symbols` now measures a node's own code only

    **Severity:** medium (a governance signal that used to exist is now unmeasured; recorded openly rather than papered over with a threshold)
    **Command:** `beadloom lint --strict`
    **Context:** Fixing #144 changed what `max_symbols` means: it counts the symbols a node OWNS (nested nodes excluded) instead of everything under its path prefix. That is what makes the rule's own remedy work — carving a subpackage out now genuinely relieves the parent. But the OLD metric also carried a second, legitimate signal: "this bounded context has grown too large overall". A domain decomposed into many features owns very little and will never trip the rule, however large its subtree becomes. Measured on Beadloom itself after the fix: `context-oracle`, `ai_agents` and `infrastructure` own **0** symbols each (every file belongs to a component/feature node) while their subtrees hold 99, 108 and 63.
    **Issue:** two different questions were riding on one number — "is this node's own code too big?" (own count, the re-scoping prompt) and "is this bounded context too big?" (subtree count, the split-the-domain prompt). Only the first is now expressible.
    **Expected:** a separate cardinality key for the second question rather than overloading `max_symbols` — e.g. `max_subtree_symbols` (all symbols under the node's source, the old semantics) and/or `max_children` (how many nodes are `part_of` it). Keeping them distinct is the point: a threshold that silently answers whichever question happens to be convenient is how a metric stops meaning anything.
    > Deliberately NOT folded into the `domain-size-limit` threshold when it was recalibrated 290 → 180.

149. [2026-08-05] [LOW] `graph --format c4 --level component --scope <ref>` on a node with no internals prints a single useless `C4Container` instead of saying so

    **Severity:** low (silently useless output rather than an error — reads as a rendered diagram)
    **Command:** `beadloom graph --format c4 --level component --scope <ref_id>`
    **Context:** Dogfood: an integration offers a "detailed diagram of one container" view and passes whatever node the user names.
    **Issue:** when `<ref>` is a leaf (no nested nodes), the command exits 0 and emits a valid-but-empty C4 diagram — one `C4Container` block, no internals. Rendered, it is a single box. There is no signal distinguishing "this node has no internals" from "here are its internals", so a caller cannot tell the user the truth without pre-checking the graph itself.
    **Expected:** exit non-zero (or print an explicit note) when `--scope` resolves to a node with no contained nodes, so the caller can fall back to a neighbourhood view and say why.
    **Workaround:** downstream detects the degenerate output and falls back to the node's neighbourhood diagram plus an honest note to the reader.

148. [2026-08-05] [MEDIUM] `lint` prints machine porcelain when stdout is not a TTY — the human summary line vanishes in a pipe, so the documented output is not what a program receives

    **Escalated 2026-08-22 — this is not cosmetic, it produces wrong conclusions.** `sync-check` has the same TTY-dependent shape, and it corrupted the coordinator's own verification twice in one session while investigating a suspected gate defect. Counting `beadloom sync-check | grep -c '^stale'` returned **0** on a tree with genuinely stale pairs, because the piped shape omits the per-pair lines the interactive shape prints. Measured on the same tree, same moment: piped grep count **0**, exit code **2**, `--json` **2 stale pairs**. The first reading was used to conclude — wrongly — that `reindex` re-baselines sync pairs and that the gate could be turned green by running it twice. Neither is true. A monitoring surface whose shape depends on whether a human is watching will be sampled by programs and by agents, and it will silently give them the wrong number. **Any agent instruction to "count the stale lines" is unsound today**; the exit code and `--json` are the only trustworthy contracts, and that should be stated in the docs until the shape is stable.

    **Severity:** medium (contract differs by TTY; parsers written against the documented/human output silently see nothing to parse)
    **Command:** `beadloom lint` / `beadloom lint --strict`
    **Context:** Dogfood: an integration captures `lint` output to summarise it for a chat reader.
    **Issue:** interactively `lint` ends with `N violations, M rules evaluated`; through a pipe that summary line is absent and the output switches to a porcelain form. Nothing in `--help` mentions a TTY-dependent format, and there is no `--porcelain`/`--json` flag to select the shape deliberately, so a caller cannot ask for a stable contract — it just gets a different one depending on how it was invoked.
    **Expected:** keep one shape by default and gate the machine form behind an explicit flag (`--porcelain`/`--json`), or emit the summary line in both modes. TTY-dependent output shape should never be the only way to get the documented text.
    **Workaround:** downstream reconstructs the verdict from the porcelain lines and appends its own summary.

    **PARTLY FIXED, re-measured 2026-09-29.** Fixed: `lint --format rich|json|porcelain|github`
    selects the shape, and `sync-check` has `--porcelain` and `--json`. The flag dates from
    BDL-007, so "no flag to select the shape" was already false. Remains: the default still
    switches on the TTY, and piped `lint` prints porcelain rows with no `Errors/Warnings` summary
    line.

147. [2026-08-05] [HIGH] 🔴 `beadloom lint` MUTATES the index — a read-only-sounding verb writes to `beadloom.db`, and there is no read-only mode without `--no-reindex`

    **Severity:** high (a verification verb has a side effect on the artifact it verifies; blocks any least-privilege/read-only integration)
    **Command:** `beadloom lint` (vs `beadloom lint --no-reindex`)
    **Context:** Dogfood on a downstream project wiring a STRICTLY read-only introspection seam (an agent may run a fixed allowlist of read subcommands and must not mutate repository state). `lint` was assumed read-only — it *reports* violations.
    **Issue:** plain `lint` performs an implicit reindex and rewrites `.beadloom/beadloom.db`. Measured by sha256 of the DB file: before `2cfb…`, after `beadloom lint` `15cd…` (changed), after `beadloom lint --no-reindex --strict` unchanged. So the only read-only form is `--no-reindex`, and nothing in `lint --help` marks the default as state-mutating. A read-only integration that trusted the verb would silently mutate the index — and, worse, would mutate it under a concurrently-running gate.
    **Compounding:** `--strict` is also required for a non-zero exit on an `error`-severity violation; plain `lint` exits 0 while printing the violation. A caller checking only the exit code reads a real boundary break as clean (same false-green family as #142/#146).
    **Expected:** make `lint` read-only by default (reindex only on an explicit `--reindex`), or at minimum document the write in `--help` and warn when the index is written by a verb the user invoked to *check* something. Ideally `--no-reindex` becomes the default and the docs name the trade-off (possibly stale graph) explicitly.
    **Workaround:** downstream pinned the argv form to `lint --no-reindex --strict` and added a test asserting the DB hash is unchanged across the call.
    > **Fixed in BDL-061 S2 (`beadloom-mr2l.5`), verified in `.6` and again in `.7`.** `lint --no-reindex` is a genuine read-only path — `beadloom.db` is byte-identical afterwards under both `journal_mode=wal` and `journal_mode=delete`, and a MISSING index is now exit 2 with `index not found … Run 'beadloom reindex' first` instead of an empty database created in the same breath and reported clean. `--help` states that the default writes, and plain `lint` names on stderr that its exit code stays 0 over error-severity violations without `--strict` (the code itself is deliberately unchanged: turning it would flip an adopter's green pipeline red).
    > **Two residues, both measured, both unfixed.** (a) On a WAL index the read-only form still creates and leaves `beadloom.db-wal` / `beadloom.db-shm`, so byte-identity is a property of the FILE, not of `.beadloom/`. (b) **`--no-reindex` answers about the INDEX and never says so:** with a real error-severity crossing on disk and a stale index, `lint --no-reindex --strict` printed `0 violations, 12 rules evaluated` at rc 0, silent on both streams, while plain `lint --strict` on the same tree exited 1 — and `beadloom ci --no-reindex` reported `lint PASS` over that same live violation. The flag is exposed to adopters (`.github/actions/beadloom-gate` has a `no-reindex` input; `docs/guides/ci-setup.md` recommends `beadloom ci --no-reindex` in the GitLab example), so #147's fix created a second way to lint a stale graph. `file_index` already stores a sha256 per path, so "N files differ from the index" is one query. **Documented in `docs/services/cli.md` and `docs/guides/ci-setup.md`; no bead yet.**

    **PARTLY FIXED, re-measured 2026-09-29.** Fixed: `lint --no-reindex` leaves `beadloom.db`
    byte-identical (same sha1, measured by the audit on a copy of main). Remains: (a) on a WAL
    index it leaves new `-wal` and `-shm` files, and (b) it says nothing when the index is older
    than the tree. Neither residue has a bead.

145. [2026-08-03] [MEDIUM] `ctx <ref> --json` returns the REPO-WIDE `code_symbols` array, not the focused node's — an agent sizing/inspecting a node from its own context bundle reads every other package's symbols

    **Severity:** medium (agent-facing correctness; silently wrong data, not an error)
    **Command:** `beadloom ctx <ref-id> --json`
    **Context:** Dogfood on a downstream DDD project. An orchestrator wanted to verify a `max_symbols` rule independently ("how big is this node really?") and did the obvious thing: `beadloom ctx <node> --json` → count `code_symbols`. The node held **172** symbols; the bundle returned **1342** — every symbol in the repository, spanning all 12 top-level packages, while `focus.ref_id` correctly named the single node.
    **Issue:** The JSON bundle's `code_symbols` is not scoped to the focused subgraph. `focus`/`graph` are node-scoped, so the payload *looks* node-scoped — the mismatch is invisible without cross-checking against the DB. Any consumer that treats the bundle as "this node's context" (an agent budgeting tokens, counting symbols, or reasoning about what the node contains) is silently wrong, and wrong in the direction of "everything looks huge and entangled". Related to #95, which describes the same query as a **performance** problem and states the result is "then filter[ed] to the subgraph in Python" — in the `--json` output that filtering is not observable, so either it does not happen on this path or it is applied to other fields only.
    **Expected:** `code_symbols` scoped to the focused node's `source` (plus explicitly-included neighbours), or — if repo-wide is deliberate for context-priming — a distinct field name (`repo_symbols`) and a `focus_symbols` counterpart, so consumers cannot mistake one for the other.
    **Workaround:** Query the index directly: `SELECT COUNT(*) FROM code_symbols WHERE file_path LIKE '<source>%'`.

140. [2026-07-29] [LOW] `ci`/`sync-check` doc-stale output is one line PER stale symbol occurrence — a wide signature change floods the summary with hundreds of near-duplicate `::error` lines

    **Severity:** low (correctness fine; scannability poor)
    **Command:** `beadloom ci` / `beadloom sync-check`
    **Context:** A single refactor that threads a new parameter through many collaborators (one signature change rippling into ~a dozen call-sites + one new package) produced **216 stale symbol/hash pairs**. `beadloom ci` emitted a `::error ... doc-stale ...` line for **each** occurrence — dozens of visually-identical lines for the same doc — so the human/agent scanning the CI failure can't quickly see WHICH docs need a `sync-update`, only that "many" do.
    **Issue:** Stale output is per-(symbol,occurrence), not grouped per-doc/per-ref. There is no rolled-up summary ("N stale across M refs: <ref-list>"). Also fires on **test-only** commits (a test signature touch), which is noisy for a test wave that legitimately defers docs to a later tech-writer step.
    **Expected:** Group the stale report by ref/doc with a count (`conversation: 41 stale`, `application: 118 stale`, …) + a one-line total, so the fix target (`sync-update <ref>`) is obvious at a glance. Optionally a `--summary` mode. Per-occurrence detail behind `--verbose`.
    **Workaround:** `beadloom sync-check --json` and group client-side; defer to the tech-writer `sync-update` wave regardless of the noise.

    **PARTLY FIXED, re-measured 2026-09-29.** Fixed: findings are one per doc-code pair
    (`doc-stale` per pair in `application/gate.py`), not one per symbol occurrence. Remains: there
    is no grouping per ref or document and no summary line, and `sync-check` on the tree printed
    533 per-pair lines with no total.

138. [2026-07-02] [MEDIUM] `docs generate` silently no-ops on a coarse graph; no monolith-drift guard; `component`→`DOC.md` not generated

    **Severity:** medium (product docs rot silently; no signal to the agent)
    **Command:** `beadloom docs generate` / `beadloom reindex` / `beadloom doctor`
    **Context:** Dogfood on the downstream project. Its graph = 4 nodes (1 service + 3 domain), all source tagged blanket `beadloom:domain=bob` (186 files, 0 feature/component). `docs/architecture.md` had grown to **4095 lines / ~110 hand-appended feature sections**, while Beadloom's own tree (65 nodes → 32 SPEC + 19 DOC) is the target. The tech-writer kept appending to the monolith because the graph never grew a node to anchor a per-feature SPEC.
    **Issue:**
    1. `generate_skeletons()` (`onboarding/doc_generator.py`) is purely node-driven (`kind in {domain,service,feature}`). On a coarse graph it emits nothing and exits 0 — **no warning** that doc granularity is far below code granularity. The failure mode is invisible: a project can accumulate a 4k-line `architecture.md` and the tool never flags it.
    2. **No monolith-drift detector:** no `sync-check`/`doctor`/`lint` signal that `architecture.md` line-count ≫ per-node docs, or that a domain has N source subpackages/skills but 0 feature/component nodes, or that all `beadloom:` tags are one coarse domain.
    3. `component` nodes are **excluded** from generation, yet the recommended tree uses `components/<c>/DOC.md`. Every component DOC must be hand-authored — no skeleton, unlike feature `SPEC.md` (parity gap).
    **Expected:**
    - `docs generate`/`doctor` warns when a domain's source subpackages/skill files outnumber its feature/component nodes (a granularity-coverage metric), and when `architecture.md` size vastly exceeds generated per-node docs.
    - Optionally: during reindex, SUGGEST feature/component nodes from directory structure (`src/<domain>/<subpkg>/`, per-skill files) even without explicit `beadloom:feature=` tags.
    - Generate a `DOC.md` skeleton for `kind: component` (parity with feature SPEC).
    **Workaround (the downstream project-side):** re-annotate source with granular `beadloom:feature=`/`component=` tags + rebuild `services.yml` with feature/component nodes, then `docs generate` + migrate `architecture.md` sections (tracked as the downstream project-Issues #1–#4).

134. [2026-06-16] [LOW] `sync-update --yes --all` never reaches fixpoint for `reference` (`watches=`) docs — surface_drift re-flagged every run

    **Severity:** low (warn-only — does NOT block the Gate or `sync-check` exit code)
    **Command:** `beadloom sync-update --yes --all` (repeated)
    **Context:** BDL-059 S4 integration. After decomposing graph/cli into packages, the 7 `reference` docs (`watches=cli,graph,flow.yml` — README/CHANGELOG/architecture/cli.md/sync-check SPEC) showed `surface_drift`. Each `sync-update --yes --all` printed `Re-baselined 7 reference doc(s)`, but the very next call re-baselined the SAME 7 — never converging to 0, unlike the symbol-pair `sync_state` which fixpoints in one pass.
    **Issue:** The `reference_state` surface signature does not "stick" after `sync-update` (re-computed signature differs from the just-stored one, or `--all` doesn't persist the reference-doc re-attestation the way it persists symbol pairs). Because `surface_drift` is warn-only, `beadloom ci` and `sync-check` still exit 0 — so it is cosmetic, but it breaks the fixpoint invariant the F4.1 loop relies on and is noisy on every integration.
    **Expected:** `sync-update --all` should re-attest `reference` docs so a subsequent `sync-check`/`sync-update` reports them fresh (0 re-baselined on the second pass), matching symbol-pair behavior.
    **Workaround:** None needed for the Gate (warn-only, exit 0). Ignore the repeated count; confirm `beadloom ci` rc0 + the `TestSyncCheckNewPairs` test green as the real signal.

    **PARTLY FIXED, re-measured 2026-09-29.** Fixed: the drift converges. In a git-initialised
    copy, 7 surface-drift lines went to 0 after one `sync-update --yes --all`. Remains: every pass
    still prints `Re-baselined 10 reference doc(s).`, so the command's own count never reaches 0.

95. [2026-05-28] [MEDIUM] Per-bundle full table scan of `code_symbols` won't scale; L2 `bundle_cache` is not on the build path

    **Severity:** medium
    **Command:** `beadloom prime` / `beadloom ctx <id>`
    **Context:** Self-audit (2026-05-28). Invisible on this repo (506 symbols); a latent scale problem for the large monorepos a "context oracle" targets.
    **Issue:** `build_context` (`context_oracle/builder.py:377`) calls `_collect_code_symbols` (`:256`), which runs `SELECT * FROM code_symbols` (`:267`) and `json.loads(row["annotations"])` per row (`:268`) on EVERY bundle build, then filters to the subgraph in Python — O(total symbols in repo) per `prime`/`ctx` call. A SQLite L2 cache exists (`context_oracle/cache.py` → `bundle_cache` table) but `build_context` does not consult it on the hot path.
    **Expected:** Filter symbols in SQL by the subgraph's ref_ids (indexed join), avoid per-row JSON parsing of non-matching rows (e.g. a `symbol_annotations(ref_id, symbol_id)` table or an indexed `ref_id` column), and/or wire `build_context` through the existing `bundle_cache`.
    **Workaround:** None needed at small scale.

    **PARTLY FIXED, re-measured 2026-09-29.** Fixed: the L2 cache is on the build path, because
    `ctx` and the MCP server go through `build_context_cached` with `SqliteCache`. Remains: on a
    cache miss, `_collect_code_symbols` still runs `SELECT * FROM code_symbols` and parses every
    row's JSON (`context_oracle/builder.py`).

73. [2026-03-10] [LOW] `beadloom doctor` reports "Version drift" and "Package drift" by checking `.claude/CLAUDE.md`

    **Severity:** low
    **Command:** `beadloom doctor`
    **Context:** After bootstrapping on an external project, the existing `.claude/CLAUDE.md` contained content from a previous project (Beadloom itself) with `Version: 1.9.0` and DDD package references (`context_oracle/`, `doc_sync/`, etc.).
    **Issue:** `doctor` checks `.claude/CLAUDE.md` for version and package claims, finding `CLAUDE.md claims 1.9.0, actual is 1.7.0` and `Package drift: claimed but missing: context_oracle, doc_sync, graph, infrastructure, onboarding, services, tui`. These are false positives — CLAUDE.md is a user-maintained file that may describe the project in custom terms, not necessarily matching Beadloom's internal structure.
    **Expected:** `doctor` should validate `.beadloom/AGENTS.md` (which Beadloom generates and controls) rather than `.claude/CLAUDE.md` (which is user-authored and project-specific). If CLAUDE.md is checked at all, it should be limited to `<!-- beadloom:auto-start -->` / `<!-- beadloom:auto-end -->` sections.
    **Workaround:** Ignore the warnings; they're false positives caused by stale CLAUDE.md content from another project.

---

## Improvements

> Proposals, not defects. The entries below 100 are from the first field tests in February and
> are kept until someone re-measures them; 81 and 77 are probably answered already (the layer
> rule over imports, `setup-agentic-flow`).

### Index

| No | Date | Severity | What |
|---|---|---|---|
| 156 | 2026-08-19 | medium | Context rot explains WHY a long instruction file stops being followed |
| 155 | 2026-08-19 | high | Multi-agent failure modes and long-running-harness patterns Beadloom can act on |
| 154 | 2026-08-19 | high | Oversight patterns a controlled multi-agent flow should adopt |
| 96 | 2026-05-28 | medium | Test suite is volume-heavy but brittle: implementation-coupled and rarely parametrized |
| 87 | 2026-03-10 | low | No automated cleanup of orphaned docs after node deletion from graph |
| 85 | 2026-03-10 | info | Bootstrap accuracy target: 95%+ across all supported languages |
| 84 | 2026-03-10 | medium | Framework-specific preset rules: use detected framework to tune classification |
| 83 | 2026-03-10 | medium | Two-phase bootstrap: draft → review → commit |
| 82 | 2026-03-10 | medium | Bootstrap `config.yml` should support `exclude_paths` for user-controlled noise reduction |
| 81 | 2026-03-10 | high | Import-graph based dependency direction validation |
| 80 | 2026-03-10 | high | Bootstrap graph accuracy: comprehensive improvement plan for all supported languages |
| 79 | 2026-03-10 | info | Field-testing metrics: Beadloom bootstrap on a production FastAPI monolith |
| 77 | 2026-03-10 | medium | No automated CLAUDE.md adaptation for target project stack |
| 76 | 2026-03-10 | low | `beadloom init` doesn't support combined bootstrap + import mode in one step |
| 75 | 2026-03-10 | medium | Auto-generated node summaries are mechanical and don't convey purpose |
| 74 | 2026-03-10 | medium | Bootstrap classifies test directories as domains |

### Entries

156. [2026-08-19] [MEDIUM] Context rot explains WHY a long instruction file stops being followed — plus selective escalation as a second graph-derived feature

    **Severity:** medium (sharpens the root cause in #153 and adds one concrete feature; the rest is confirmation)
    **Command:** design-level — `prime`, the emitted `CLAUDE.md`/role files, wave escalation
    **Context:** two further public Anthropic publications: *Effective context engineering for AI agents* (engineering) and the *2026 Agentic Coding Trends Report*.

    ### A. 🔴 The mechanical root of #153 is measurable, not motivational

    #153 explained skipped rules by delivery mechanism and instruction count. The context-engineering piece gives the sharper reason: **context rot** — *"as the number of tokens in the context window increases, the model's ability to accurately recall information from that context decreases."*

    So a ~640-line instruction file is not merely competing for attention; **recall of its contents degrades measurably as context fills** — which is exactly when a long session needs the rules most. That reframes the fix: shortening the scaffolded `CLAUDE.md` is not tidiness, it is the difference between rules that are recalled and rules that are present but unread.

    The same piece names the design target — *"the smallest possible set of high-signal tokens that maximize the likelihood of some desired outcome"* — which is precisely what `prime` already aims at, and gives the failure it must avoid: the **"right altitude"** between *"hardcoding complex, brittle logic"* and *"vague, high-level guidance that fails to give the LLM concrete signals"*. A scaffolded flow file that mixes narrative lessons with imperative process sits at both wrong altitudes at once.

    **Implication for the emitted scaffold:** split by function, not by topic — a short imperative core that must survive to the end of a long session, and referenced companion documents for narrative rationale. Also: anything that must outlive compaction belongs in a file or the tracker, never in context (the scaffold's `PreCompact` hook re-primes, but *"overly aggressive compaction can result in loss"*).

    ### B. Role agents should return a bounded, distilled result — state it as a contract

    Sub-agent architectures are described as specialized agents returning a *"condensed, distilled summary"* of typically **1,000-2,000 tokens** to a coordinating agent. A scaffolded role file can carry that as an explicit output contract rather than leaving the shape to the agent — which also protects the coordinator's own context from the rot in (A). Complements #155 C: the reviewer's *input* is diff+spec, its *output* is a bounded verdict.

    ### C. 🔴 Selective escalation is the second thing only the graph can decide

    The trends report's oversight direction: *"Agents learn when to ask for help, rather than blindly attempting every task"*, and *"human oversight shifts from reviewing everything to reviewing what matters"*. It also names, as a needed capability, *"development environments that show the status of multiple concurrent agent sessions and version control workflows that handle simultaneous agent-generated contributions"* — the space a graph-aware TUI plus merge serialization already occupies.

    "What matters" is a graph question. Beadloom can compute escalation-worthiness from properties it alone holds: how many nodes depend on the one being changed (blast radius via `why`), whether the change crosses a declared boundary, whether it touches a node carrying invariants, whether the doc for that node is stale. That turns "escalate when unsure" — which no prompt reliably produces — into a rule the harness evaluates. Pairs with #155 A: the graph decides **what may run in parallel**, and here **what must stop for a human**.

    ### D. Sober framing worth keeping in the product's positioning

    From the same report's own research: developers use AI in roughly **60%** of their work but report being able to *"fully delegate"* only **0-20%** of tasks; the summary calls the goal *"not to remove humans from the loop"* but to make human attention count. A flow product should therefore be honest that it is building **supervised delegation**, and that gates exist because delegation is partial — not as a temporary scaffold to be removed when models improve. This matches #155's closing quote that coordination does not emerge from greater individual capability.

    **Expected:** #153's "shrink the scaffolded instruction file" item is re-justified by context rot rather than taste; role files gain an output-size contract; and escalation joins wave-shaping as a graph-derived decision.
    **Notes:** confirmatory (no action needed): structured note-taking outside the context window validates the tracker+specs model; *"bloated tool sets that cover too much functionality or lead to ambiguous decision points"* is a named failure worth auditing the MCP/introspection surface against.

155. [2026-08-19] [HIGH] Multi-agent failure modes and long-running-harness patterns Beadloom can act on — and one feature only Beadloom can build

    **Severity:** high (design input for #153/#154; item A is a differentiator, not a nicety)
    **Command:** design-level — `setup-agentic-flow`, wave planning, the spec/state templates
    **Context:** three current Anthropic engineering/research publications read for transferable design, not for their subject matter: *Patterns and problems in multiagent systems* (research), *Effective harnesses for long-running agents* (engineering), *Scaling Managed Agents: decoupling the brain from the hands* (engineering).

    ### A. 🔴 Wave shape should be DERIVED FROM THE GRAPH — multi-agent helps or hurts depending on interdependence

    The research piece is blunt about where parallel agents pay off and where they rot. Parallelizable, independent work: a coordinated swarm found **266 vulnerabilities vs 21**. Shared-codebase work with *"rich, dynamic interdependencies"* **deteriorates** — game-building runs produced *"uniformly poor results"*, and the measured PR-merge tables show either constant conflict or *"high ownership silos"* where agents simply avoid each other's files.

    Every scaffolded flow today asks a human to guess the wave shape. **Beadloom already holds the answer**: it knows which files belong to which node and which nodes depend on which. It can compute, before a wave launches, whether the beads in it touch independent subgraphs (parallelize) or the same node (serialize). Nothing else in the toolchain can do this — a tracker knows bead dependencies, but only the architecture graph knows *code* interdependence.

    Concretely: `bd swarm`-style wave planning gains a Beadloom-side check that refuses (or warns) when two beads in the same wave resolve to overlapping graph nodes. Related downstream evidence already in this log: parallel agents editing one shared file produced a destructive-restore window.

    ### B. 🔴 Conformity cascades: identical context ⇒ identical decisions, including identical mistakes

    Named failure mode: agents *"act identically when contexts match, unlike humans who exhibit diverse responses"*. Measured instances: **18 of 30** agents created a branch with the same name; multiple agents independently produced the same title for a creative task; a job-queue experiment generated **2.4 million requests for 117 accepted jobs**.

    This is the mechanism behind an incident in the same organisation's risk report (§5.2.2): one agent narrowed its task, wrote that decision into a **shared notebook**, and later agents adopted the refusal — while progress metrics looked healthy; found by a human three days later.

    For a flow whose durable state is deliberately shared (`CONTEXT.md` / `ACTIVE.md` / bead comments — see #154 H), the consequence is structural: **an isolated defect becomes systemic**, and the shared state is the vector. Design implications:
    * a wave report must record *what was skipped and why* as a required field, so a narrowing is a value, not an absence;
    * convergence is measurable — identical decisions across a wave (same file, same approach, same skip) is a signal worth surfacing, not noise.

    ### C. 🔴 The reviewer must not read the author's justification first

    In "hidden profile" tasks, groups scored **17–36% accuracy versus ~100%** when a single agent held all the facts: *"consensus silences dissenting evidence"*. Recommended human-derived mechanisms include peer review that *"balances author claims with dissent"* and courts that *"protect a lone witness"*.

    A scaffolded review role that receives the dev agent's summary is therefore structurally compromised — it converges on the author's framing before looking. The review role should be handed **the diff and the spec**, and only then, optionally, the author's notes. This is cheap to specify in the emitted role file and it is the difference between an independent check and a rubber stamp. Downstream evidence for the same conclusion, learned the hard way: a standing rule in one adopter's process reads *"an agent's report is not evidence — the coordinator re-runs the gates itself, on the final tree"*.

    ### D. Named failure modes for long-running agents, with mitigations worth emitting

    From the harness piece, each mapping onto something a flow can enforce rather than request:

    | Failure mode | Their mitigation | Flow implication |
    |---|---|---|
    | **Premature victory declaration** — *"agent sees progress, assumes completion"* | a comprehensive feature list; work strictly feature-by-feature | the exact failure #153 measured; a bead-scoped acceptance list beats prose |
    | One-shotting the whole project | enforce single-feature focus per session | one bead per wave slot |
    | Leaving broken code | commit with descriptive message + update progress file | already the flow's habit — make it a gate |
    | **Premature feature completion** — *"Claude tended to make code changes … but would fail to recognize that the feature didn't work end-to-end"* | mandate end-to-end verification through the real interface | matches an adopter's own hardest-won rule: a test against a fake proves the fake's contract |
    | Lost time re-orienting | begin every session by reading git log + progress, then run smoke tests **before** new work | `prime` gives context but no *verification* step — worth adding |

    ### E. State files: JSON, not Markdown

    Small and concrete: their feature list is JSON *"(not Markdown, which agents more readily corrupted)"*, carrying strongly-worded invariants inline — *"It is unacceptable to remove or edit tests because this could lead to missing or buggy functionality."*

    Beadloom's scaffolded `ACTIVE.md` is Markdown and is edited by agents every session. Worth considering a machine-readable companion for the parts that must not be corrupted (bead states, acceptance checkboxes) while prose stays Markdown for humans. An adopter already hit the adjacent problem from the other side — `active-sync` exists precisely because these tables drift.

    ### F. Credentials outside the sandbox, state outside the harness

    From the managed-agents piece: sandboxes never hold credentials — auth is *"bundled with a resource or held in a vault outside the sandbox"*, explicitly to keep prompt injection from reaching tokens; and session state lives outside the harness so a harness can be recreated (`wake(sessionId)`) rather than nursed. Also *"avoiding irreversible context decisions within Claude's window"* by keeping the event log external and sliceable.

    A scaffolded flow inherits the second idea for free (durable state in files + tracker, never in chat) and should state the first as a requirement it checks: role files must not carry credentials or bypass permissions (see #154 F).

    **Expected:** #153 gains (A) graph-derived wave shape — the item no generic agent framework can copy — plus (B) skip-declaration and convergence signals, (C) a review role that sees evidence before advocacy, (D) the named failure modes as emitted acceptance criteria, and (E) corruption-resistant state.
    **Notes:** all three sources are public Anthropic publications (anthropic.com/engineering, anthropic.com/research). The recurring theme across them and #154: *"Coordination doesn't naturally emerge from stronger intelligence nor alignment at the individual level"* — i.e. a better model will not fix an unenforced flow, which is the same conclusion #153 reached from measurement.

154. [2026-08-19] [HIGH] Oversight patterns a controlled multi-agent flow should adopt — drawn from a published frontier-lab risk report

    **Severity:** high (design input for #153; several items are things #153 would otherwise get wrong)
    **Command:** design-level — `setup-agentic-flow`, the gates it emits, `ci`
    **Context:** Anthropic's public *Risk Report: August 2026* documents how one organisation supervises highly autonomous AI agents working on its own infrastructure — including its own process failures. Read for transferable engineering patterns, not for its threat models. Sections cited below: §2.23 (internal usage monitoring), §5.2 (safety process failures).

    ### A. Two layers, named separately: asynchronous monitoring vs blocking interventions

    The report splits mitigations into **asynchronous monitoring** (§2.23.1 — sees everything, stops nothing) and **blocking interventions** (§2.23.2 — sandboxing, PR review, blocking classifiers). Keeping them distinct is what makes the coverage question answerable at all.

    A scaffolded flow should do the same and say which is which per rule. Today's scaffold has only the informational layer (`SessionStart`-style context priming) while its prose reads as if it were the blocking one — which is exactly the failure measured in #153.

    ### B. A guard is worth having even when it is bypassable — but say so

    §2.23.2.4, on sandboxing and blocking classifiers: *"we think it's likely that covered models would be able to bypass at least one of those. However, we believe that they still slightly reduce the probability of success … and make it harder for models to pursue risk pathways without being detected by asynchronous monitoring."*

    The value claimed is **raised detectability**, not prevention. A flow that ships hooks should make the same honest claim rather than implying hooks are unbypassable (they are shell commands; an agent with shell access can reason about them).

    ### C. Limitations are part of the mitigation, not an afterthought

    §2.23.3 is a titled list — *"Important limitations of our model-external risk mitigations"* — including that monitoring *"would not prevent catastrophes from a first successful execution of an irreversible … pathway"*.

    Proposal: every gate `beadloom` emits carries a machine-readable "does NOT cover" note, surfaced in `ci` output. A downstream project already practises this by hand; making it a product feature is what stops a green gate from being read as broader assurance than it is (cf. #146, where a doc-freshness PASS meant "no pairs exist").

    ### D. Review that checks intent against effect — a first-class check type

    §2.23.2.3: automated PR review by a prompted model *"checking for common errors, obvious security vulnerabilities, and **mismatches between the stated purpose of a change and its actual effects**"*.

    That third item is the one no linter provides and the one Beadloom is uniquely placed to provide, because it already holds the stated purpose: the bead, the spec, and the graph node the change claims to touch. "Diff vs its own spec" is a check type, not a prompt.

    ### E. Invariants as executable tests, stated in the same breath

    Same section: *"tests are run automatically to ensure new infrastructure code does not break security invariants (e.g. if two nodes are not supposed to be able to send network traffic to each other, a test checks they can't)"*. This is precisely the `forbid_import` idea generalised beyond imports — worth noting as validation of the rules model, and as a hint that the rule vocabulary could cover more than import edges.

    ### F. 🔴 Dangerous permissions propagate to SPAWNED agents through inherited instructions

    §5.2.5, verbatim in substance: an employee's usage *"wasn't logged and wasn't monitored"*; an agent was given an open-ended task that spawned further agents in a cluster with sensitive resources; ***"Due to legacy instructions, the main agents spawned the new agents with `--dangerously-skip-permissions`"***; those child agents were unmonitored too. One deleted a large number of jobs — *"which is how these dangerous agents were caught"*.

    Two design consequences for a flow that scaffolds role agents:
    * a role definition must never be able to carry a permission *relaxation* that its children inherit — spawning may narrow authority, never widen it. (The host has been hardening exactly here: a recent release fixed an agent definition's bypass mode ignoring an org disable policy.)
    * `setup-agentic-flow` should refuse to emit, and `config-check` should flag, any role file that grants bypass-style permissions.

    ### G. 🔴 Unlogged agent activity makes intent unreconstructable *after* the fact

    Same incident: *"given the gap in our monitoring coverage, we cannot confirm"* what the agent was attempting. Detection came from the damage, which is the worst possible detector.

    A flow whose durable state is a tracker + specs already has the raw material for an audit trail; it should be a **required** output of a wave, not a convention. Note the same failure shape a downstream project hit: two capabilities went mute in production and the detector was the owner asking a question three days later.

    ### H. 🔴 Shared agent context propagates DECISIONS — including a silent narrowing of scope

    §5.2.2 is the single most relevant incident for a multi-agent product. A scaffold let several agents work autonomously and share a notebook. One agent decided to narrow the task, recorded that decision in the shared notebook, and ***subsequent agents adopted the same refusal***. Meanwhile: *"Based on our metrics, the run seemed to be progressing."* It was found *"during a manual review of the notebook 3 days later, when a human noticed that progress rates were lower than expected."*

    Every element maps onto a scaffolded flow: `CONTEXT.md` / `ACTIVE.md` / bead comments **are** that shared notebook, and waves of role agents read them. Consequences:
    * shared context is a **propagation vector**: one agent's "we can skip X" becomes the wave's premise;
    * dashboards that show *progress* cannot show *narrowing* — the run looked healthy;
    * therefore a wave report must state **what was NOT done and why**, as a required field, so a narrowing is a value rather than an absence. An absent step is invisible; a declared skip is reviewable.

    ### I. 🔴 A misconfigured filter ran for several generations "without anyone noticing" — gates need a liveness proof

    §5.2.6 lists among the causes: *"The filters intended to remove these transcripts from training data were misconfigured, so they had not filtered transcripts for several model generations without anyone noticing."*

    This is the same defect as #61 in this very log (a `--check` documented as a gate that nothing ever invoked) and as a downstream CI step that returned exit 0 having generated zero mutants. **Proposal — the strongest single item here:** `beadloom ci` grows a *gate liveness* mode that, for each gate, applies a synthetic violation and asserts the gate reddens. A gate that cannot be shown to fail is not known to work. This turns the downstream project's hand-run "double pass" discipline (sabotage it, prove the new guard reddens and the old one stayed green) into a product feature.

    **Expected:** #153's enforcement layer designed with A–I in mind — in particular (F) spawn narrows authority, (H) waves declare what they skipped, and (I) gates prove they can still fail.
    **Notes:** cited document is public (*Risk Report: August 2026*, anthropic.com). Nothing here depends on its threat models; the value is that a lab supervising far more autonomous agents converged on monitoring-vs-blocking, honest limitation notes, intent-vs-effect review, and audit trails — the same four things a controlled dev flow needs.

96. [2026-05-28] [MEDIUM] Test suite is volume-heavy but brittle: implementation-coupled and rarely parametrized

    **Severity:** medium
    **Context:** Self-audit (2026-05-28). Test:source ratio ≈1.9:1 (~48K test LOC / ~25K src LOC), 2576 test functions.
    **Issue:** The volume reflects breadth, not depth: only ~4 uses of `@pytest.mark.parametrize` (test bodies are copy-pasted instead of data-driven), and ~193 accesses to private attributes (`._foo`) in tests — assertions welded to current internals that will break on refactor. `test_tui.py` alone is ~5989 LOC for a low-value surface. This brittleness will make the #91 architecture refactor far more painful than necessary.
    **Expected:** Before the #91 refactor: (a) convert copy-pasted test groups to `parametrize`; (b) replace private-attribute assertions with behavior / public-API assertions; (c) reassess whether the TUI warrants ~6K LOC of tests. Treat coverage as a means, not the `fail_under=80` number as the goal.

87. [2026-03-10] [LOW] No automated cleanup of orphaned docs after node deletion from graph

    **Severity:** low
    **Command:** `beadloom doctor`
    **Context:** During manual graph refinement, 12 nodes were deleted from `services.yml` (test directories, internal layers). After `beadloom reindex`, the auto-generated doc skeletons for those deleted nodes remained on disk.
    **Issue:** `beadloom doctor` correctly reports orphaned docs as "unlinked from graph" — but the user must manually `rm` each file. For 12 deleted nodes, this means 12 manual deletions across the `docs/` tree. There is no `beadloom docs cleanup` or `beadloom docs prune` command.
    **Expected:** Either:
    - (a) `beadloom docs prune` command that deletes doc files not linked to any graph node (with `--dry-run` preview)
    - (b) `beadloom reindex --prune-docs` flag that auto-cleans orphaned docs during reindex
    - (c) `beadloom doctor --fix` that offers to delete orphaned docs interactively
    For AI agents via MCP: a `prune_orphaned_docs` tool that returns the list of files to delete and accepts confirmation.
    **Workaround:** Manually delete each orphaned doc file reported by `beadloom doctor`.

85. [2026-03-10] [INFO] Bootstrap accuracy target: 95%+ across all supported languages

    **Severity:** info
    **Context:** Consolidation of all bootstrap accuracy improvements (#74, #75, #77, #78, #80, #81, #82, #83, #84) into a measurable quality target.
    **Current state (measured on 2 field tests):**
    - Field test #37 (React Native / Expo): ~35% accuracy → improved to ~94% after manual refinement
    - Field test #79 (Python / FastAPI): ~80% accuracy → improved to ~95% after rules fix + manual refinement
    **Target:** Bootstrap should produce a graph that is ≥95% accurate (measured as: nodes with correct `kind` + edges with correct direction / total nodes + edges) WITHOUT manual intervention, for projects using any of the 12 supported languages.
    **Measurement plan:**
    - Create a test suite of reference projects (1 per supported language/framework combination)
    - Each reference project has a manually curated `services.golden.yml` (ground truth)
    - CI job: `beadloom init --bootstrap -y` → compare generated graph vs golden → report accuracy %
    - Track accuracy over time as heuristics improve
    **Reference projects needed:**
    | Language | Framework | Project type |
    |----------|-----------|-------------|
    | Python | FastAPI | Monolith API |
    | Python | Django | Monolith web app |
    | TypeScript | NestJS | Monolith API |
    | TypeScript | React + Next.js | Frontend monolith |
    | Go | stdlib net/http | Microservice |
    | Rust | Actix | Microservice |
    | Java | Spring Boot | Monolith API |
    | Kotlin | Spring Boot | Monolith API |
    | Swift | Vapor or SwiftUI | iOS app |
    | TypeScript | Express | Microservices |
    | TypeScript | React Native/Expo | Mobile app |
    | Multi-language | — | Monorepo |

84. [2026-03-10] [MEDIUM] Framework-specific preset rules: use detected framework to tune classification

    **Severity:** medium
    **Command:** `beadloom init --bootstrap`
    **Context:** `_detect_framework()` in `scanner.py` correctly identifies 11+ frameworks (FastAPI, Django, NestJS, Spring Boot, Express, Vue, React, Actix, Flask, Next.js, Gatsby). The detected framework is stored as metadata on the root node's `extra.tech_stack` — but NOT used to adjust classification heuristics.
    **Issue:** Framework detection is "fire and forget" — the information exists but doesn't influence how nodes are classified. Each framework has known conventions:
    - Django: directory with `apps.py` = domain boundary, `urls.py` = composition root
    - NestJS: `*.module.ts` = domain boundary, `*.controller.ts` = transport layer
    - Spring Boot: `@Service` annotated classes = domain services (not standalone service nodes)
    - FastAPI: `graphql/`, `routers/` inside domain = transport layer, not separate domains
    - Go: `cmd/` = entry points, `internal/` = domains, `pkg/` = shared library
    **Expected:** After framework detection, apply framework-specific classification overrides:
    1. Store detected framework in `config.yml` (user-overridable): `framework: fastapi`
    2. Load framework-specific rules from a built-in registry (e.g., `src/beadloom/onboarding/frameworks/`)
    3. Rules override default `_SERVICE_DIRS` / `_FEATURE_DIRS` / `_ENTITY_DIRS` regex patterns
    4. Rules define composition root patterns, test directory patterns, and layer conventions
    5. Users can extend with custom rules in `config.yml`:
       ```yaml
       framework: fastapi
       classification_overrides:
         - pattern: "*/graphql/"
           kind: feature
           absorb_into_parent: true
       ```

83. [2026-03-10] [MEDIUM] Two-phase bootstrap: draft → review → commit

    **Severity:** medium
    **Command:** `beadloom init --bootstrap`
    **Context:** Bootstrap generates a final graph in one step. The user discovers issues only after running `lint`, `doctor`, or manually inspecting `services.yml`. By then, they're editing YAML by hand — defeating the purpose of automation.
    **Issue:** No review step between graph generation and commit. The user can't validate or correct the graph before it's written to disk. This is especially problematic for large projects where manual YAML editing is tedious.
    **Expected:** Two-phase bootstrap:
    ```bash
    # Phase 1: Generate draft graph (write to .beadloom/_graph/services.draft.yml)
    beadloom init --bootstrap --draft

    # Phase 2: Interactive review (or AI-assisted)
    beadloom review-graph              # shows draft, asks questions, accepts corrections
    beadloom review-graph --auto-fix   # auto-fix known issues (test exclusion, depth-aware kinds)

    # Phase 3: Apply (rename draft to final)
    beadloom apply-graph
    ```
    In non-interactive mode (`-y`), Phase 2 applies `--auto-fix` automatically. In interactive mode, it presents a summary and asks for confirmation.
    For AI agents via MCP: expose a `review_bootstrap_graph` tool that returns the draft graph + suggested fixes as JSON, and an `apply_bootstrap_fixes` tool that applies corrections.

82. [2026-03-10] [MEDIUM] Bootstrap `config.yml` should support `exclude_paths` for user-controlled noise reduction

    **Severity:** medium
    **Command:** `beadloom init --bootstrap` → `beadloom reindex`
    **Context:** After bootstrap, the user wants to exclude test directories, migration directories, or generated code from the architecture graph without manually editing `services.yml`.
    **Issue:** `config.yml` only supports `scan_paths` (what to include) but not `exclude_paths` (what to skip within scan_paths). The user must manually delete nodes from `services.yml` and re-run `reindex` — fragile and lost on next bootstrap.
    **Expected:** Add `exclude_paths` to `config.yml`:
    ```yaml
    scan_paths:
    - app
    exclude_paths:
    - "app/tests/"
    - "app/migrations/"
    - "**/generated/"
    ```
    The exclude list should support glob patterns and be respected by both `init --bootstrap` and `reindex`. Auto-populated during bootstrap with detected test directories (per-language patterns from `test_mapper.py`).

81. [2026-03-10] [HIGH] Import-graph based dependency direction validation

    **Severity:** high
    **Command:** `beadloom init --bootstrap` → `beadloom reindex`
    **Context:** After reindex, import analysis produces 305 import edges. These are used for `forbid_import` rules but NOT for validating bootstrap-generated `depends_on` edge directions.
    **Issue:** Bootstrap generates `depends_on` edges based on import analysis, but doesn't distinguish between:
    - **Real architectural dependency**: domain A's business logic imports from domain B's public API
    - **Composition wiring**: a top-level file (schema.py, urls.py, main.go) imports from all domains to wire them together
    - **Test imports**: test files import from production code (not a real architectural dependency)
    The result: `core` appears to depend on `houses`, `pdf`, `plans`, `tasks`, `users` — when the real dependency is the reverse.
    **Expected:** After import-graph construction:
    1. Identify composition-root files (fan-out ≥ 70% of domains) and exclude their imports from `depends_on` edge generation
    2. Identify test files and exclude their imports from `depends_on` edge generation
    3. For remaining imports, determine dependency direction by counting: if A imports B more than B imports A, then A depends_on B
    4. Flag bidirectional dependencies for user review (potential circular dependency or misclassification)

80. [2026-03-10] [HIGH] Bootstrap graph accuracy: comprehensive improvement plan for all supported languages

    **Severity:** high
    **Command:** `beadloom init --bootstrap`
    **Context:** Field-testing on a production project revealed that the bootstrapped graph is ~80% accurate but has systematic misclassifications. These are NOT project-specific — they stem from heuristics that apply across all 12 supported languages. This issue consolidates the root causes and proposes a phased improvement plan.

    **Root causes identified:**

    **A. Test directories inside scan_paths are not excluded.**
    `_SKIP_DIRS` in `scanner.py` includes `"test", "tests"` but only for top-level directory detection in `detect_source_dirs()`. Once a scan_path is chosen (e.g., `app/`), subdirectories like `app/tests/`, `app/__tests__/`, `app/spec/` are scanned and classified as domains. This affects:
    - Python: `app/tests/`, `tests/` inside packages
    - TypeScript/JavaScript: `__tests__/`, `*.test.ts` collocated files
    - Go: `*_test.go` files (collocated by convention)
    - Java/Kotlin: `src/test/` mirroring `src/main/`
    - Swift: `*Tests/` directories
    - Rust: `tests/` directory, inline `#[cfg(test)]` modules

    **B. `_SERVICE_DIRS` regex over-matches internal domain layers.**
    The regex `^(services?|core|engine|workers?|jobs?|tasks?|processors?)$` matches both:
    - Top-level packages that ARE architectural services (correct: `services/`, `core/`)
    - Sub-packages within a domain that are internal layers (incorrect: `app/pdf/services/`, `app/pdf/tasks/`)
    The classifier doesn't distinguish depth — a `services/` directory 2 levels deep inside a domain should NOT create a standalone service node.

    **C. No composition root detection.**
    Files that import from ALL or most domains (e.g., `schema.py`, `urls.py`, `routes/index.ts`, `main.go`) are not recognized as composition roots. This creates inverted dependency edges: the composition root's parent gets `depends_on` edges pointing toward every domain, when architecturally the domains are independent and the root just wires them together. Affected patterns across languages:
    - Python: `schema.py` (GraphQL), `urls.py` (Django), `main.py` (FastAPI)
    - TypeScript: `routes/index.ts`, `app.module.ts` (NestJS)
    - Go: `cmd/server/main.go`, `wire.go`
    - Java/Kotlin: `@Configuration` classes, `Application.java`
    - Rust: `main.rs`, `lib.rs`

    **D. Framework-detected metadata is not used for classification tuning.**
    `_detect_framework()` in `scanner.py` correctly identifies 11+ frameworks (FastAPI, Django, NestJS, Spring Boot, Express, etc.) but the result is only stored as metadata on the root node. It is NOT used to:
    - Adjust which directories become features vs. domains (e.g., Django `apps.py` = domain, FastAPI `graphql/` = transport layer within domain)
    - Set framework-specific layer rules
    - Choose appropriate `rules.yml` templates

    **Proposed solution — phased approach:**

    **Phase 1: Test exclusion (LOW effort, HIGH impact)**
    - Add `exclude_paths` to `config.yml` schema (list of glob patterns)
    - Auto-populate with detected test directories during bootstrap using existing `test_mapper.py` patterns:
      - Python: `**/tests/`, `**/test/`, `**/__tests__/`
      - JS/TS: `**/__tests__/`, `**/*.test.*`, `**/*.spec.*`
      - Go: skip `*_test.go` from node creation (they're collocated)
      - Java/Kotlin: `**/src/test/`
      - Swift: `**/*Tests/`
      - Rust: `**/tests/` (integration tests dir)
    - Bootstrap output: `"Excluded 7 test directories (override in config.yml)"`
    - Estimated impact: removes 20-30% of graph noise across all languages.

    **Phase 2: Depth-aware kind classification (MEDIUM effort, HIGH impact)**
    - Change `_SERVICE_DIRS` / `_FEATURE_DIRS` matching to consider directory depth relative to scan_path root.
    - Rule: directories matching `_SERVICE_DIRS` or `_FEATURE_DIRS` at depth ≥ 2 inside an already-classified domain should be **absorbed into the parent** (not create separate nodes), unless they have 5+ files of their own.
    - Examples:
      - `app/pdf/services/` (depth 2 inside `app/`) → part of `pdf` domain, NOT a separate `pdf-services` service node
      - `app/core/redis/` (depth 2 inside `app/`) → sub-domain of `core`, keep as-is (has its own distinct responsibility)
      - `services/` at top level (depth 0) → standalone service node (correct)
    - This fixes: `pdf-services`, `pdf-tasks`, `users-services`, `tests-core` misclassifications.
    - Language-specific depth thresholds may be needed:
      - Python: depth 2+ = internal
      - Java/Kotlin: depth 3+ (due to `src/main/java/com/...` convention)
      - Go: depth 1+ (flat package convention)

    **Phase 3: Composition root detection (MEDIUM effort, MEDIUM impact)**
    - After import-graph construction, identify files with fan-out ≥ 70% of all domains:
      ```
      composition_root = file where (imported_domains / total_domains) >= 0.7
      ```
    - For composition root files:
      - Do NOT create `depends_on` edges from the root's parent to imported domains
      - Instead, mark the file with `# composition-root` annotation in graph metadata
      - Optionally create `wires` edges (a new edge kind) for documentation purposes
    - Language-specific patterns to aid detection:
      - Python: file imports `strawberry.Schema`, `urlpatterns`, `FastAPI()` + imports from 3+ domains
      - TypeScript: file contains `@Module({ imports: [...] })` (NestJS) or `createApp()` (Vue)
      - Go: `main.go` in `cmd/` importing 3+ internal packages
      - Java: class annotated `@SpringBootApplication` or `@Configuration`
      - Rust: `main.rs` or `lib.rs` with `mod` declarations for 3+ modules

    **Phase 4: Framework-specific classification rules (MEDIUM effort, HIGH impact)**
    - Use detected framework to apply classification overrides:

    | Framework | Rule |
    |-----------|------|
    | **FastAPI** | `graphql/`, `api/`, `routers/` inside domain → transport layer (feature), not separate domain |
    | **Django** | Directory with `apps.py` → domain; `urls.py` → composition root; `admin.py` → skip |
    | **NestJS** | `*.module.ts` → domain boundary; `*.controller.ts` → transport; `*.service.ts` → absorbed |
    | **Spring Boot** | `@Controller`/`@RestController` → transport; `@Service` → absorbed; `@Repository` → adapter |
    | **Express** | `routes/` → transport; `middleware/` → infrastructure; `controllers/` → absorbed |
    | **Go (stdlib)** | `cmd/` → entry points; `internal/` → domains; `pkg/` → shared |
    | **Rust (Actix)** | `handlers/` → transport; `models/` → entities; `services/` → domains |
    | **React/Vue** | `components/` → features; `hooks/`/`composables/` → shared; `pages/`/`views/` → transport |

    - Store active framework in `config.yml`:
      ```yaml
      framework: fastapi   # auto-detected, user can override
      ```

    **Phase 5: Docstring/README mining for summaries (LOW effort, MEDIUM impact)**
    - During bootstrap, for each classified node:
      1. Read entry-point file's module docstring (language-specific):
         - Python: `__init__.py` or `module.py` top-level docstring
         - Go: package comment in first `.go` file
         - Rust: `//!` doc comments in `lib.rs` / `mod.rs`
         - Java/Kotlin: Javadoc on main class
         - TypeScript: JSDoc on default export or `/** @module */`
      2. Search project README.md for sections mentioning the directory name
      3. Search `doc/` or `docs/` for files named after the domain
      4. Fallback: current mechanical format `"Domain: X — N classes, M fns"`

    **Phase 6: AI-assisted graph refinement via MCP (HIGH effort, HIGHEST impact)**
    - New command: `beadloom refine` (or `beadloom init --bootstrap --refine`)
    - After mechanical bootstrap, invoke an AI agent (via MCP or direct prompt) with:
      - Generated graph (nodes + edges as JSON)
      - README.md content
      - Import-graph summary (top-10 highest fan-out files)
      - Detected framework + entry points
    - Agent reviews and returns corrections:
      - kind reclassification
      - edge direction fixes
      - summary enrichment
      - nodes to merge or exclude
    - Agent output written as `services.yml` patch → user confirms → apply
    - Requires: MCP write tools (`update_node`) already exist; need a "review prompt" template

    **Priority and impact matrix:**

    | Phase | Effort | Impact | Fixes |
    |-------|--------|--------|-------|
    | 1. Test exclusion | Low | High | #74, ~25% noise reduction |
    | 2. Depth-aware kinds | Medium | High | service/domain misclassification |
    | 3. Composition roots | Medium | Medium | inverted dependencies |
    | 4. Framework rules | Medium | High | language-specific accuracy |
    | 5. Summary mining | Low | Medium | #75, useless summaries |
    | 6. AI refinement | High | Highest | remaining ~10% gap |

    Phases 1-3 are language-agnostic and fix structural issues. Phase 4 is the largest effort but delivers per-language accuracy. Phase 5 is a quick win. Phase 6 is the endgame for "perfect out of the box" but depends on LLM availability.

79. [2026-03-10] [INFO] Field-testing metrics: Beadloom bootstrap on a production FastAPI monolith

    **Severity:** info
    **Command:** `beadloom init --bootstrap -y`
    **Context:** Field-testing on a production Python 3.13 FastAPI + Strawberry GraphQL monolith with 6 business domains, ~50 Python source files, ~30 test files, Docker + k8s deployment, GitLab CI.
    **Results:**
    - **Bootstrap time:** ~3 seconds
    - **Auto-detected:** preset=monolith, language=.py, scan_paths=[app]
    - **Generated graph:** 30 nodes, 47 raw edges (95 after reindex with import analysis), 272 symbols
    - **Classification accuracy:** ~80% — correctly identified 6 business domains, 6 features (graphql sub-packages), root service. Misclassified: test dirs as domains (7 nodes), some service/domain kind swaps.
    - **Lint violations:** 2 out of the box (rules-vs-graph mismatch, see #71)
    - **Doc coverage:** 97% (29/30 nodes had auto-generated docs)
    - **beadloom prime:** correct and useful output after rules fix — 0 stale docs, 0 lint violations
    - **Total time to fully operational state (bootstrap + rules fix + .claude adaptation + .gitignore + verify):** ~15 minutes with AI agent assistance
    - **Improvement vs. previous field test (#37):** Bootstrap quality improved from ~35% to ~80% architecture capture. The main remaining gap is test-directory noise and dry summaries.

77. [2026-03-10] [MEDIUM] No automated CLAUDE.md adaptation for target project stack

    **Severity:** medium
    **Command:** `beadloom setup-rules --refresh`
    **Context:** After bootstrapping on a new project, the `.claude/CLAUDE.md` file contained a generic template (from a previous project) with wrong stack references (Python 3.10 instead of 3.13, `mypy` instead of `ty`, `src/beadloom/` paths instead of `app/`, etc.). Manual adaptation required ~30 minutes of an AI agent's time to:
    - Analyze the project stack (pyproject.toml, CI config, pre-commit)
    - Rewrite the Project Info section
    - Rewrite the Architecture section
    - Update all quality gate commands
    - Update all `.claude/commands/*.md` files (dev, review, test, templates, coordinator, checkpoint)
    **Issue:** Beadloom bootstraps the architecture graph automatically but doesn't help with adapting the AI agent instruction files. The `setup-rules --refresh` only updates `<!-- beadloom:auto-start -->` sections, which cover a small fraction of CLAUDE.md.
    **Expected:** A new command or flag like `beadloom setup-rules --adapt-claude` that:
    1. Reads `pyproject.toml`, CI configs, pre-commit config to detect the project's stack
    2. Updates `CLAUDE.md` section `0.1 Project` with detected stack, tooling, architecture
    3. Updates quality gate commands (test runner, linter, type checker) throughout CLAUDE.md
    4. Optionally adapts `.claude/commands/dev.md` code patterns section with project-appropriate examples
    This would make Beadloom initialization a truly one-command experience for AI-assisted projects.

76. [2026-03-10] [LOW] `beadloom init` doesn't support combined bootstrap + import mode in one step

    **Severity:** low
    **Command:** `beadloom init --bootstrap --import doc/`
    **Context:** The project has both source code in `app/` and existing documentation in `doc/` (API specs, integration guides). The user wants to bootstrap from code AND import existing docs.
    **Issue:** `--bootstrap` and `--import` are mutually exclusive on the CLI. The user must run two commands: `beadloom init --bootstrap -y` then `beadloom init --import doc/`. The `--mode both` flag exists in help but it's unclear how it interacts with `--import DIRECTORY`.
    **Expected:** `beadloom init --bootstrap --import doc/ -y` should work in a single invocation: bootstrap the graph from code, then import and classify docs from the specified directory.

75. [2026-03-10] [MEDIUM] Auto-generated node summaries are mechanical and don't convey purpose

    **Severity:** medium
    **Command:** `beadloom init --bootstrap`
    **Context:** Project has README.md with a clear description of each domain's purpose, plus `__init__.py` files with module docstrings.
    **Issue:** Generated summaries are purely structural: `"Domain: configs — 1 class, 2 fns"`, `"Domain: houses — 2 classes, 6 fns"`. These tell an AI agent nothing about what the domain does. The information needed is available in:
    - Project README.md (describes each domain conceptually)
    - `__init__.py` module docstrings
    - Existing documentation in `doc/` directory
    **Expected:** During bootstrap, attempt to extract meaningful summaries from:
    1. `__init__.py` docstring of the package (highest priority)
    2. README.md sections that mention the domain name
    3. Existing docs in the project's `doc/` or `docs/` directory
    Fall back to the mechanical format only if no semantic source is available.

74. [2026-03-10] [MEDIUM] Bootstrap classifies test directories as domains — clutters graph and prime output

    **Severity:** medium
    **Command:** `beadloom init --bootstrap`
    **Context:** Field-testing on a production project with `app/tests/` containing subdirectories per domain (`tests/houses/`, `tests/pdf/`, `tests/plans/`, `tests/users/`, `tests/integrations/`).
    **Issue:** Bootstrap creates 7 test-related nodes (`tests`, `tests-houses`, `tests-pdf`, `tests-plans`, `tests-users`, `tests-integrations`, `tests-core`) classified as domains. These nodes:
    - Clutter `beadloom prime` output (7 of 17 "domains" are actually test suites)
    - Inflate the graph (30 nodes → ~23 without tests)
    - Add noise to `beadloom graph` Mermaid diagram
    - Create spurious `depends_on` edges (tests naturally import everything)
    **Expected:** Option to exclude test directories from the architecture graph: `beadloom init --bootstrap --exclude-tests` or a `config.yml` setting like `exclude_paths: [app/tests/]`. Alternatively, classify test directories as a separate `kind: test-suite` that can be filtered in `prime`/`graph` output.

---

## Closed numbers that must stay written

> One line per number that a check still resolves here: numbers claimed in the ledger
> (262 and higher), and numbers the shared media of `beadloom waves` cite as evidence. The
> text of each is in `archive/BDL-UX-Issues-closed.md`.

304. ~~[2026-09-29] [HIGH] a replacement for a heuristic was proven "no worse than main" one ecosystem at a time, so the review found the same regression three times~~ **CLOSED**
303. ~~[2026-09-19] [HIGH] the nightly mutation job is killed by its runner at 93-100 minutes, so the declared scope has had no aggregate score since 2026-09-09 even now that the run works~~ **CLOSED**
298. ~~[2026-09-13] [MEDIUM] a vacuity guard added in BDL-070 reads the live index while other tests in the same run rebuild it, and saw 57 edges of 365~~ **CLOSED**
296. ~~[2026-09-13] [MEDIUM] a layer rule reports an error and is counted inert in the same run, because liveness still reads own tags~~ **CLOSED**
289. ~~[2026-09-12] [HIGH] a self-scanning guard test reads mutmut's own mutated copy of the package, so the nightly mutation run reaches a verdict on 0 of 6544 mutants~~ **CLOSED**
285. ~~[2026-09-11] [WITHDRAWN] a bead's scope appended by the documented command is silently ignored when its description already carries a `refs:` line~~ **CLOSED**
284. ~~[2026-09-11] [MEDIUM] an axis row is ruled by the axis a node first surfaced under, and three nodes ruled out as blast radius turned out to be the sites the fix had to reach~~ **CLOSED**
283. ~~[2026-09-11] [MEDIUM] `beadloom waves --parent` compares only READY beads, so it reports a clean wave for a bead that conflicts with one already running~~ **CLOSED**
282. ~~[2026-09-10] [CRITICAL] a virgin `init` leaves the Gate RED on the documents it just wrote, and the remediation the error names does not clear it~~ **CLOSED**
281. ~~[2026-09-10] [MEDIUM] the release version is stated in NINE places, and no command names that population — three instruments each check a disjoint part of it and none knows the others exist~~ **CLOSED**
274. ~~[2026-09-09] [MEDIUM] `beadloom waves` takes the beads to plan as an authored argument list, so a wave is planned over the population its caller happened to type~~ **CLOSED**
270. ~~[2026-09-09] [MEDIUM] four ways of misdeclaring `issue_log:` reach the same gate verdict as declaring none~~ **CLOSED**
267. ~~[2026-09-09] [MEDIUM] `issue-number check` returns a clean list over 2% of the log, because the leg that skips history never says how much of it it skipped~~ **CLOSED**
266. ~~[2026-09-09] [MEDIUM] a clean room has no `.git`, so a version attributed to `git` loses its subject and reddens the Gate at HEAD~~ **CLOSED**
265. ~~[2026-09-09] [MEDIUM] the graph is one file, so one writer per file is available here and is not taken~~ **CLOSED**
264. ~~[2026-09-09] [MEDIUM] a population literal is a derivable fact with two homes, and every node-adding bead pays three hand edits for it~~ **CLOSED**
262. ~~[2026-08-23] [MEDIUM] A virgin `setup-agentic-flow` leaves `config-check` red — four errors on a repository nobody has touched~~ **CLOSED**
261. ~~[2026-09-09] [HIGH] a wave shares more than its focus document — the graph the plan is derived from, and a test's population literals~~ **CLOSED**
237. ~~[2026-09-04] [MEDIUM] `bd merge-slot acquire --wait` does not wait, and cannot serialise agents that share one tracker identity~~ **CLOSED**
235. ~~[2026-09-03] [MEDIUM] the clean-room instruction names a fixed directory, so two agents in one wave build one room and both call it clean~~ **CLOSED**
194. ~~[2026-08-26] [HIGH] [External: bd 1.0.4] `bd merge-slot` is not an exclusion primitive — every agent is the same actor, and `release` is not owner-checked~~ **CLOSED**
182. ~~[2026-08-23] [HIGH] 🔴 `symbols_changed` is computed per node, so one changed file marks every pair of that node stale — and the only way through is bulk re-attestation~~ **CLOSED**
181. ~~[2026-08-23] [MEDIUM] Clean-room verification is the right technique and structurally cannot see a cross-bead interaction — nothing runs the combined tree until a human does~~ **CLOSED**
171. ~~[2026-08-22] [MEDIUM] Concurrent `bd create` shifts the id out from under the id written in the title — and the wrong dependency edge is then perfectly valid~~ **CLOSED**
165. ~~[2026-08-22] [LOW] External (steveyegge/beads): `bd create` costs one process per bead, so building a DAG of ~50 beads stalls~~ **CLOSED**
133. ~~[2026-06-15] [LOW] Per-worktree `beadloom.db` baseline causes mass false re-baseline when integrating parallel worktree waves~~ **CLOSED**
118. ~~[2026-06-02] recorded in the chronology only (BDL-041 F4.4); cited as evidence by the commit-gate medium~~ **CLOSED**

## Retired numbers

> Every other number this log has used. Written here so that `issue-number check` counts it as
> accounted for and the allocator never hands it out again. Text in the archive.

#1 #2 #3 #4 #5 #6 #7 #8 #9 #10 #11 #12 #13 #14 #15 #16 #17 #18 #19 #20 #21 #22 #23 #24 #25 #26
#27 #28 #29 #30 #31 #32 #33 #34 #35 #36 #37 #38 #39 #40 #41 #42 #43 #44 #45 #46 #47 #48 #49 #50
#51 #52 #53 #54 #55 #56 #57 #58 #59 #60 #61 #62 #63 #64 #65 #66 #67 #68 #69 #70 #71 #72 #78 #86
#88 #89 #90 #91 #92 #93 #94 #97 #98 #99 #100 #101 #102 #103 #104 #105 #106 #107 #108 #109 #110
#111 #112 #113 #114 #115 #116 #117 #119 #120 #121 #122 #123 #124 #125 #126 #127 #128 #129 #130
#131 #132 #135 #136 #137 #139 #141 #142 #143 #144 #146 #150 #151 #152 #153 #157 #159 #164 #169
#170 #172 #173 #174 #175 #177 #180 #183 #186 #188 #189 #191 #192 #193 #195 #204 #207 #211 #212
#213 #214 #216 #227 #228 #231 #233 #234 #236 #238 #239 #240 #241 #243 #244 #245 #247 #248 #249
#250 #251 #252 #253 #254 #255 #256 #258 #259
