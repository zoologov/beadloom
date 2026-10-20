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

> 326–350 filed 2026-10-18 from the first outside adopter's two-day log (an anonymised monorepo: Python backend under `backend/` with uv, FSD frontend, self-hosted GitLab CE), measured there on 2026-10-16/17 and the quoted source lines re-read here; intake bead `beadloom-71k0`.
> Re-measured 2026-10-20 on 9.0.0 (BDL-083 S3, the code of `main` at `41245dc7`): each open entry
> was re-run by its own command. 22 closed with dated evidence and #352 was archived as a
> duplicate of #292, all in `archive/BDL-UX-Issues-closed.md`. Every entry left here names its
> bead in the index, or waits on the owner's ruling listed in the BDL-083 PLAN, and carries
> `measured_on`. The evidence files are `docs/features/BDL-083/s3/S3a.md` to `S3f.md`; 358 to
> 365 were filed from what the measurement found.

### Index

| No | Date | Severity | What | Bead |
|---|---|---|---|---|
| 365 | 2026-10-20 | medium | a contract's unknown key (`body_from`) is indexed and exported without a word, so a producer that points at an AsyncAPI document federates `CONFIRMED` over a body nobody read | `beadloom-xvjf` |
| 364 | 2026-10-20 | low | `init --mode import` names the domains it imports after the document file (`readme`, `readme-domain`) instead of the directory the document describes | `beadloom-ix7o` |
| 363 | 2026-10-20 | medium | `init --bootstrap` exits 0 while it prints that `ci` will fail its lint step on the graph it leaves | `beadloom-dw74` |
| 362 | 2026-10-20 | medium | `doctor` reports no stale sync entry while `sync-check` on the same tree reports two stale pairs | `beadloom-r9t5` |
| 361 | 2026-10-20 | medium | `sync-check` is not idempotent after a code and document edit: the first run records the document edit and judges before it, so it reads a false stale that the second run clears | `beadloom-zl7e` |
| 360 | 2026-10-20 | medium | after the Gate's `reindex` step crashes, `sync-check` reads `PASS` over 0 pairs: a step whose input a crashed step did not produce reports a verdict over nothing | `beadloom-q2kh` |
| 359 | 2026-10-20 | medium | `clean-room --at` inside a foreign git work tree builds the room without a warning, and its "carries no .git" line is false of what git sees there | `beadloom-q5sg` |
| 358 | 2026-10-20 | medium | `ci`'s ownership block lists the merge-slot bead among the claimed beads while a neighbour holds the landing lock | `beadloom-of49` |
| 357 | 2026-10-19 | high | the hooks `install-hooks` writes never run on a repository `bd init` initialised: bd 1.0.4 sets `core.hooksPath=.beads/hooks` while `install-hooks` writes `.git/hooks`, so the pre-commit checks and the pre-push Gate are silent there and a push goes through with the hook installed | `beadloom-ba9w.23` |
| 356 | 2026-10-19 | high | `setup-agentic-flow --tool cursor` writes the five role files and a 17-line rules stub and no core, no project layer and no commands, so an agent on Cursor runs the flow with no DoD, no tracker discipline and no epic-closure duties; `setup-mcp` writes one machine's absolute path | `beadloom-ujm0` |
| 355 | 2026-10-19 | medium | the branch-to-work-item binding reads `features/<KEY>` exactly, so a work item that ships in several pull requests (one branch per slice, `features/BDL-083-S2`) loses its declared axes, its focus document and the scope check on every branch but the first | `beadloom-bdnv` |
| 353 | 2026-10-19 | high | on a Windows checkout the index stores paths with `\` while `source:` is written with `/`, and every `source:` match is a raw string compare: directory nodes read `no_indexed_code`, file nodes read stale, the declared surface reads 167 pairs of 347; `sync-surface.json` holds counts and no pair list, so the drop has no names | none — the owner rules |
| 351 | 2026-10-18 | medium | `init --yes` on a monorepo with `backend/` and `frontend/` under `scan_paths` writes nodes for the frontend only; the Python backend under its own `pyproject.toml` gets no node and no preset | `beadloom-cn29` |
| 350 | 2026-10-18 | low | `ctx --json` reports `framework: "jest"` for vitest spec files; the count is right and the name is wrong | `beadloom-ogku` |
| 349 | 2026-10-18 | low | a one-line edit in a spec file beside the code marks the node's document stale (`hash_changed`), and `sync-update --pair` re-attests 26 pairs to clear one test | `beadloom-fvi6` |
| 348 | 2026-10-18 | medium | incremental `reindex` creates no pair for a new spec file in a node's directory: `sync-check` says `untracked_files`, the hint sends the author to annotations, and only `reindex --full` clears it | `beadloom-js85` |
| 347 | 2026-10-18 | medium | `untracked_files` is reported for a file that has its own node: a nested node's `source:` inside the parent's directory marks all the parent's pairs stale | `beadloom-su66` |
| 346 | 2026-10-18 | medium | `symbols_changed` and `sibling_symbols_changed` survive the document edit they ask for: 62 pairs stay stale after the docs were updated, and the output does not say that only re-attestation clears them or which symbols changed | `beadloom-qvmp` |
| 345 | 2026-10-18 | low | docs-quality `section-not-in-use` reports an `Acceptance Criteria (overall)` section present in 0 of 1 PRD while the PRD holds it | `beadloom-2ryw` |
| 344 | 2026-10-18 | medium | `review-brief` for an epic's review bead prints `DECLARED SCOPE: none`, every file `OUTSIDE` and `0 document(s)` while the epic holds PRD, RFC and PLAN, over a base of 596 files against trunk | `beadloom-rehc` |
| 343 | 2026-10-18 | low | `snapshot compare` takes integers only, while `snapshot list` prints labels (`stage-1`, `wave-12`) | `beadloom-nbsf` |
| 342 | 2026-10-18 | medium | an annotated module pairs with the documents of two nodes: the annotation decides the pair, the enclosing `source:` directory keeps the ownership and the edges | `beadloom-kela` |
| 341 | 2026-10-18 | low | `forbid_import.from` is one fnmatch glob with no tag matcher: a layer-wide ban needs one rule per domain per library, and the inert copies are indistinguishable from a glob typo | `beadloom-rhfo` |
| 340 | 2026-10-18 | medium | the node matcher in `require` reads one `kind`; a list is not parsed, so `has_edge_to: {{ kind: [domain, feature, service] }}` cannot be written and the rule degrades to `has_edge_to: {{}}` | `beadloom-5v10` |
| 339 | 2026-10-18 | high | test-mirror resolution lets a deeper root with the same subpackage win: `backend/tests/unit/digest/test_sections.py` binds to `application/digest/sections.py`, not `digest/sections.py`, and nothing says two roots resolved | `beadloom-5xrz` |
| 338 | 2026-10-18 | medium | a spec file beside the code is indexed as code: its import becomes a `depends_on` edge, `fsd-layers` judges a test's import as the module's, and the graph cannot tell a test edge from a code edge | `beadloom-rq15` |
| 337 | 2026-10-18 | medium | a `@node:` tag in a `.feature` file outside the scenario rules' glob is read by nobody: `ctx` shows no scenario, and one steps file for all scenarios binds to one node | `beadloom-wk6l` |
| 336 | 2026-10-18 | low | `scope-check` reads only the table under `## Axes` with known axis names, so nodes the epic itself creates have no row form until the first wave lands and `impact` can see them | `beadloom-xe1f` |
| 325 | 2026-10-14 | high | a project root below the git root is not refused: `install-hooks` fails on a path, the hook bodies run without the project, and `sync-check --since` passes over two empty sides | `beadloom-o71o` |
| 324 | 2026-10-13 | low | the `init` wizard cancelled at the graph review re-indexes and takes the verdict, and does not print the line naming the code no installed parser read | `beadloom-1vy3` |
| 323 | 2026-10-13 | medium | an `@x` API inside a slice group has no form both linters accept: Beadloom reads `invoice/@x/receipt`, Steiger reads `invoice/@x/payment/receipt/index` | `beadloom-ben1` |
| 321 | 2026-10-11 | medium | the CI workflow holds a write token on every job, the self-hosted tech-writer job runs the PR branch's code with no same-repository condition, and fork runs need approval only from first-time contributors | `beadloom-dlb6` |
| 320 | 2026-10-11 | low | `bfs_subgraph` records an edge before the `max_nodes` check, so a bundle's edges can name a node its `nodes` does not hold | `beadloom-ba9w.15` |
| 319 | 2026-10-11 | medium | `ctx` has no token budget; chunks are capped by count, ordered by section type rather than by the focus node, and cut among ties in no promised order | `beadloom-ba9w.14` |
| 317 | 2026-10-11 | high | `ctx` surfaces 2 of the 17 rule types and the Markdown output none; its matcher reads `ref_id` and `kind` while the linter's reads `exclude`, `tag` and `tag_prefix` | `beadloom-ba9w.12` |
| 316 | 2026-10-11 | medium | a `## Axes` section written as `###` subsections reads as zero rows, and the commit gate then calls every owned path outside the approval | `beadloom-zuby` |
| 314 | 2026-10-10 | medium | `write_text_atomic` and `write_yaml_atomic` leave every file they write at mode 0600, so a 0644 file edited by `init` becomes owner-only and `rules.yml` is born unreadable to the group | `beadloom-ba9w.6` |
| 312 | 2026-10-10 | medium | a rule-level `scope:` is read only by `layers` rules and accepted without a word on every other rule type — a setting that looks configured and does nothing | `beadloom-ba9w.4` |
| 310 | 2026-10-10 | low | a verdict-room scenario assumes the run lacks the `search` extra, so `--all-extras` turns 8 tests red with one cause | `beadloom-ba9w.2` |
| 309 | 2026-10-10 | low | the reference-parser self-check hands gherkin's `TokenScanner` a path where it takes text, so it breaks on gherkin >= 30 | `beadloom-ba9w.3` |
| 308 | 2026-10-08 | medium | active-sync reconciles the bead table and leaves ACTIVE.md's header, 'Current bead' and checklist stale when the work item ships | `beadloom-cnty` |
| 302 | 2026-09-14 | medium | `review-brief` and `waves` take their subject from the checkout | `beadloom-ohu6` |
| 301 | 2026-09-14 | medium | a release's own "verified on the published wheel" sentences fail the Gate on the next version bump, and the suppression that excuses them is file-wide | `beadloom-y3qu` |
| 299 | 2026-09-13 | low | `issue-number allocate` accepts an empty holder and writes a claim that names nobody, and `check` reports it clean | `beadloom-l5jb` |
| 297 | 2026-09-13 | medium | `beadloom review-brief --release` keeps withholding when the verdict lives on a separate review bead, and `bd show` defeats the withholding anyway | `beadloom-6rfz` |
| 295 | 2026-09-12 | low | a node whose `extra.tags` is a truthy non-iterable fails every tag question in the run, and the indexer wrote it without complaint | `beadloom-efcb` |
| 294 | 2026-09-12 | low | `loader.get_node_tags` raises a bare `AttributeError` on a malformed `nodes.extra`, and disagrees with the batch reader beside it on four measured... | `beadloom-ui47` |
| 292 | 2026-09-12 | low | the TUI lint panel branches on a severity the rule vocabulary does not contain, so its warning count is always zero | `beadloom-vu0a` |
| 291 | 2026-09-12 | medium | the debt report reads `rules.yml` from two paths, and the product writes it to a third | `beadloom-is2z` |
| 287 | 2026-09-12 | medium | a `.beadloom/config.yml` that cannot be read crashes `beadloom ci` with a traceback instead of a verdict | `beadloom-f016` |
| 280 | 2026-09-10 | medium | a room's `locale` dimension is the TEXT codec, and a run has a second one it never reports | `beadloom-wrkj` |
| 279 | 2026-09-10 | medium | `sync-update --yes --all` re-baselines the reference documents' SURFACE as well as the stale refs, and its help names only the second population | `beadloom-4wps` |
| 278 | 2026-09-10 | medium | `setup-agentic-flow` writes `.claude/CLAUDE.md` and the four slash commands into a project whose flow declares `cursor` alone | `beadloom-nxiy` |
| 277 | 2026-09-09 | low | the orphan check's role population is the manifest and its tool population is a constant, and only the first is stated | `beadloom-94ow` |
| 275 | 2026-09-09 | medium | a bead qualifies as a work item by depending on the plan, so a one-bead plan is held against the bead that blocks on it | `beadloom-jd2g` |
| 273 | 2026-09-09 | medium | a clean room states the CAUSE of its missing freshness baseline and never the population, and about forty verdicts in one epic were read as green o... | `beadloom-3bzw` |
| 272 | 2026-09-09 | medium | the `focus-document` medium reads the first cell of every table row in the file, so its population is neither the bead table nor the bead column | `beadloom-v0z5` |
| 271 | 2026-09-09 | high | a ledger file the claim reader drops is a free number, so the allocator hands out a number two writers then hold | `beadloom-jkiy` |
| 269 | 2026-09-09 | medium | a one-hyphen alignment row is valid GitHub Flavored Markdown and reaches the approved-node list as an axis named `-` | `beadloom-5e8r` |
| 268 | 2026-09-09 | medium | two readers of one markdown table row, and the component lifted so a third could not be wrong is one of them | `beadloom-5e8r` |
| 263 | 2026-09-09 | medium | the codec sweep's vocabulary is a list of call names, so a decoding call it has never seen reads as no call at all | `beadloom-262q` |
| 260 | 2026-09-09 | medium | `ACTIVE.md` is a shared write, and the property that makes it impossible is one writer per file | `beadloom-76fp` |
| 257 | 2026-09-08 | high | `waves` derived two beads' scopes as disjoint while one document belonged to both, and the landing lock ordered the commits it could not order the... | `beadloom-velh` |
| 246 | 2026-09-04 | medium | a declared mutation target that no run ever covers passes every green Gate, and the one command that would say so is silenced by the flag its only... | `beadloom-58yp` |
| 242 | 2026-09-04 | low | the launch context a subagent receives carries a `git status` snapshot that is stale by construction, and one agent published from it | `beadloom-f3gl` |
| 232 | 2026-09-03 | medium | `waves` plans from an authored `refs:` line, so two beads editing one document read as independent | `beadloom-velh` |
| 230 | 2026-09-03 | medium | a branch whose name carries a suffix after the work-item key names no work item | `beadloom-bdnv` |
| 229 | 2026-09-03 | medium | the brief sends the reviewer to the tracker export and does not name it as a channel | `beadloom-qil0` |
| 225 | 2026-09-03 | high | `impact` under-reports on `src/<one package>` beside code outside src/ | `beadloom-f7kb` |
| 224 | 2026-09-02 | high | a new test file landing on an existing path deletes its scenarios and the suite goes GREEN over the wreckage | `beadloom-hdky` |
| 223 | 2026-09-02 | low | 102 planning documents depart from the shape their peers keep | `beadloom-l27n` |
| 222 | 2026-09-02 | low | The independent cross-check states and computes an attribution rule the implementation stopped using | `beadloom-tgo8` |
| 221 | 2026-09-02 | medium | Attribution keys on the whole node, so annotating a node makes its neighbour's failure read as ours | `beadloom-0mb5` |
| 220 | 2026-09-02 | high | `init` still tracebacks on a graph file it cannot handle | `beadloom-l22o` |
| 219 | 2026-09-02 | high | The review's withholding does not cover commit messages, which is where this project writes its accounts | `beadloom-tm76` |
| 218 | 2026-09-02 | high | `init` holds three hand-written step sequences and no artifact states what the sequence is | `beadloom-6i5q` |
| 217 | 2026-09-02 | medium | An earlier `init --mode import` leaves domains that no later run will parent | `beadloom-gv0z` |
| 215 | 2026-09-01 | medium | The Gate reports an index problem as a rules configuration error | `beadloom-uz8x` |
| 210 | 2026-08-27 | medium | `active-sync` resolves no row when a bead id is written as a Markdown code span, and blames the id | `beadloom-weh1` |
| 209 | 2026-08-27 | high | `docs audit` verifies nothing in a non-English document and counts it as scanned anyway | `beadloom-ajyq` |
| 208 | 2026-08-26 | low | A module docstring can describe code that no longer exists, and nothing in this project can see it | `beadloom-aiha` |
| 206 | 2026-08-26 | medium | `docs/**/features/*/SPEC.md` is excluded from `docs audit` outright, so declared facts drift freely there | `beadloom-ik18` |
| 205 | 2026-08-26 | medium | Writing a factually correct number can manufacture a false stale fact | `beadloom-y3qu` |
| 203 | 2026-08-26 | low | Two stated behaviours in `doc_area` survive mutation | `beadloom-oqo4` |
| 202 | 2026-08-26 | medium | One `beadloom ci` run prints two different numbers for "CLI commands" under one name | `beadloom-sgxz` |
| 201 | 2026-08-26 | medium | `--format porcelain` drops `message` | `beadloom-ksub` |
| 200 | 2026-08-26 | low | An inert `docs_audit.ignore` triple is neither computed nor reported | `beadloom-jogg` |
| 199 | 2026-08-26 | low | The Gate's lint line cannot distinguish "the rule checked nothing" from "the rule found one warning" | `beadloom-i3d5` |
| 198 | 2026-08-26 | medium | `sync-check` verified 0 of 363 pairs and `beadloom ci` exited 0 | none — Won't-fix candidate, the owner rules |
| 197 | 2026-08-26 | medium | Four other rule types still report a TOTAL stand-down as `warn`, so an escalation still evaporates for them | `beadloom-cdgn` |
| 190 | 2026-08-23 | low | `docs audit` reads a version mentioned as an EXAMPLE as a claim about this project | `beadloom-6nk6` |
| 187 | 2026-08-25 | high | External (steveyegge/beads): `bd list --json` returns a filtered view as a bare list, with nothing saying it filtered | none — Won't-fix candidate, the owner rules |
| 184 | 2026-08-23 | medium | `config-check --project <dir>` crashes with a raw sqlite error on a project that has no index | `beadloom-leio` |
| 179 | 2026-08-23 | medium | How many rule types exist? Three documents give three answers and all of them are wrong | `beadloom-i7m2` |
| 178 | 2026-08-23 | high | 🔴 A REQUIRED check reports `pass` while its own output says it verified nothing | none — Won't-fix candidate, the owner rules |
| 176 | 2026-08-23 | low | An incremental `reindex` prints `Imports: 0` and `Rules: 0` on the run that refreshed them | `beadloom-e5g0` |
| 168 | 2026-08-22 | medium | `pytest-randomly` produces failures no seed reproduces, and nothing in the output says the order was random | none — Won't-fix candidate, the owner rules |
| 167 | 2026-08-22 | low | `sync-check` prints one `[stale]` line per pair, so a single stale doc reads as a wall of 28 identical lines | `beadloom-7qo4` |
| 166 | 2026-08-22 | medium | Adding one CLI command drifts six reference docs, and `sync-update --all --yes` does not cover them | `beadloom-4wps` |
| 163 | 2026-08-20 | medium | `sync-update` can re-attest a doc nobody read | `beadloom-9glj` |
| 162 | 2026-08-20 | high | 🔴 `doctor` should audit the PRODUCED graph, not just the code | `beadloom-uxqc` |
| 161 | 2026-08-20 | medium | `docs audit` checks numeric facts but never checks that a documented identifier still exists | `beadloom-431c` |
| 160 | 2026-08-19 | high | 🔴 AsyncAPI ingestion is documented as a capability but wired to nothing | `beadloom-g79p` |
| 158 | 2026-08-19 | medium | No signal for a bounded context that is too large by SUBTREE | `beadloom-1d70` |
| 149 | 2026-08-05 | low | `graph --format c4 --level component --scope <ref>` on a node with no internals prints a single useless `C4Container` instead of saying so | `beadloom-qxp2` |
| 148 | 2026-08-05 | medium | `lint` prints machine porcelain when stdout is not a TTY | `beadloom-i8k1` |
| 147 | 2026-08-05 | high | 🔴 `beadloom lint` MUTATES the index | `beadloom-tlzl` |
| 145 | 2026-08-03 | medium | `ctx <ref> --json` returns the REPO-WIDE `code_symbols` array, not the focused node's | `beadloom-pprp` |
| 140 | 2026-07-29 | low | `ci`/`sync-check` doc-stale output is one line PER stale symbol occurrence | `beadloom-7qo4` |
| 138 | 2026-07-02 | medium | `docs generate` silently no-ops on a coarse graph; no monolith-drift guard; `component`→`DOC.md` not generated | `beadloom-uh5u` |
| 134 | 2026-06-16 | low | `sync-update --yes --all` never reaches fixpoint for `reference` (`watches=`) docs | `beadloom-4wps` |
| 95 | 2026-05-28 | medium | Per-bundle full table scan of `code_symbols` won't scale; L2 `bundle_cache` is not on the build path | `beadloom-ay6b` |
| 73 | 2026-03-10 | low | `beadloom doctor` reports "Version drift" and "Package drift" by checking `.claude/CLAUDE.md` | none — Won't-fix candidate, the owner rules |

### Entries

365. [2026-10-20] [MEDIUM] a contract's unknown key (`body_from`) is indexed and exported without a word, so a producer that points at an AsyncAPI document federates `CONFIRMED` over a body nobody read

    **Severity:** medium (an unknown key is the shape a planned feature's syntax takes before the feature exists, and accepting it silently turns a payload the author meant to declare into no payload at all; the federation verdict then reads green)
    **Command:** `beadloom reindex`, `beadloom export`, `beadloom federate --fail-on default <producer> <consumer>`
    **Context:** found 2026-10-20 on 9.0.0 (the code of `main` at `41245dc7`) by BDL-083 S3e (`beadloom-8pzg`) while measuring #160: a throwaway producer satellite declared an AMQP contract with `body_from: asyncapi.yaml` beside an AsyncAPI 2.6 document; a throwaway consumer declared a conflicting body inline.
    **Issue:** `reindex` exited 0 with no warning, `export` carried `"body_from": "asyncapi.yaml"` verbatim and no `body`, and `federate` reported `CONFIRMED: 1` (exit 0), while the same payload declared inline as `body:` on the producer made the pair `BREAKING` (exit 1). The contract loader accepts keys it does not read.
    **Expected:** an unknown contract key is a finding that names the key, the node and the keys the loader accepts, at `reindex` and in the Gate.
    **Workaround:** declare the payload inline as `body:`.
    **Bead:** `beadloom-xvjf` (found and filed on 2026-10-20 from BDL-083 S3e, `beadloom-8pzg`)
    **measured_on:** 2026-10-20 9.0.0

364. [2026-10-20] [LOW] `init --mode import` names the domains it imports after the document file (`readme`, `readme-domain`) instead of the directory the document describes

    **Severity:** low (the graph is usable and the names are wrong; every later reference, `refs:` line and SPEC path carries them)
    **Command:** `beadloom init --yes --mode import`
    **Context:** found 2026-10-20 on 9.0.0 (the code of `main` at `41245dc7`) by BDL-083 S3d (`beadloom-d9te`) while measuring #217, on a throwaway project with `src/{auth,billing}` and `docs/domains/{auth,billing}/README.md`.
    **Issue:** the run printed `Imported: 2 documents` and wrote the two domains as the nodes `readme` and `readme-domain`: the node id comes from the document's file stem, and two documents both named `README.md` are told apart by a suffix.
    **Expected:** an imported domain takes its id from the directory its document describes (`auth`, `billing`), and two candidates for one id are reported rather than suffixed.
    **Workaround:** rename the nodes in `.beadloom/_graph/imported.yml` by hand.
    **Bead:** `beadloom-ix7o` (found and filed on 2026-10-20 from BDL-083 S3d, `beadloom-d9te`)
    **measured_on:** 2026-10-20 9.0.0

363. [2026-10-20] [MEDIUM] `init --bootstrap` exits 0 while it prints that `ci` will fail its lint step on the graph it leaves

    **Severity:** medium (a script or an agent that reads the exit code takes a bootstrap whose own report says the Gate will be red as a success; the sentence is honest and the code is not)
    **Command:** `beadloom init --yes --mode import`, then `beadloom init --bootstrap`
    **Context:** found 2026-10-20 on 9.0.0 (the code of `main` at `41245dc7`) by BDL-083 S3d (`beadloom-d9te`) while measuring #217, on a throwaway project with two imported domain documents.
    **Issue:** the bootstrap printed `the graph already in .beadloom/_graph/ does not pass the rules this command wrote alongside it`, named both `domain-needs-parent` errors and `` `beadloom ci` will fail its lint step: 2 error(s), 0 warning(s) ``, and exited 0.
    **Expected:** the exit code agrees with the report: non-zero when the graph the command leaves fails the rules it wrote, or the exit 0 is a stated decision in the output and the onboarding SPEC. #217 holds the separate question of who parents the orphans.
    **Workaround:** read the output, not the exit code.
    **Bead:** `beadloom-dw74` (found and filed on 2026-10-20 from BDL-083 S3d, `beadloom-d9te`)
    **measured_on:** 2026-10-20 9.0.0

362. [2026-10-20] [MEDIUM] `doctor` reports no stale sync entry while `sync-check` on the same tree reports two stale pairs

    **Severity:** medium (two surfaces of one tool answer one question in opposite ways, and the reader cannot tell which population either counted)
    **Command:** `beadloom doctor`, `beadloom sync-check`
    **Context:** found 2026-10-20 on 9.0.0 (the code of `main` at `41245dc7`) by BDL-083 S3b (`beadloom-wvcc`) on one state of the monorepo fixture.
    **Issue:** `doctor` printed `[ok] No stale sync entries.` while `sync-check` printed two `untracked_files` pairs stale (rc 2): `doctor` reads the stored status, `sync-check` computes the reasons, and both call their population "stale".
    **Expected:** each surface names the population it counts, as `beadloom-r9t5` decides for the four populations called "stale docs"; a reason that only the computation knows is either reported by both or named as the difference.
    **Workaround:** trust `sync-check`, which the Gate runs.
    **Bead:** `beadloom-r9t5` (found and filed on 2026-10-20 from BDL-083 S3b, `beadloom-wvcc`)
    **measured_on:** 2026-10-20 9.0.0

361. [2026-10-20] [MEDIUM] `sync-check` is not idempotent after a code and document edit: the first run records the document edit and judges before it, so it reads a false stale that the second run clears

    **Severity:** medium (the Gate runs `sync-check` once, so the false stale is the verdict a push meets; the false-stale family of BDL-083 S4)
    **Command:** `beadloom reindex && beadloom sync-check && beadloom sync-check`
    **Context:** found 2026-10-20 on 9.0.0 (the code of `main` at `41245dc7`) by BDL-083 S3b (`beadloom-wvcc`) on the monorepo fixture: a code file and its node's document edited together, one `reindex`.
    **Issue:** the first `sync-check` printed two pairs `stale (hash_changed)`; the second, with nothing changed between them, printed them `ok`. The first run records the document edit (the two-phase block of `doc_sync/engine.py`) and judges before the record.
    **Expected:** one run judges after it records the document edit, so two consecutive runs over one tree give one answer.
    **Workaround:** run `sync-check` twice.
    **Bead:** `beadloom-zl7e` (found and filed on 2026-10-20 from BDL-083 S3b, `beadloom-wvcc`)
    **measured_on:** 2026-10-20 9.0.0

360. [2026-10-20] [MEDIUM] after the Gate's `reindex` step crashes, `sync-check` reads `PASS` over 0 pairs: a step whose input a crashed step did not produce reports a verdict over nothing

    **Severity:** medium (the run is red by the crash, so no push passes on it; the step line itself is a pass over an empty population, the class this project calls a gate that lies)
    **Command:** `beadloom ci` over a `.beadloom/config.yml` that cannot be read
    **Context:** found 2026-10-20 on 9.0.0 (the code of `main` at `41245dc7`) by BDL-083 S3a (`beadloom-k6f1`) while measuring #287, on three copies of the monorepo fixture: an unclosed flow sequence, a top level that is a list, a byte `0xe9`.
    **Issue:** in every shape the Gate printed `reindex ERROR: crashed` and then `::notice::sync-check PASS: 0 pair(s) fresh`; `ci` exited 1 because of the crash.
    **Expected:** a step that reads an index the `reindex` step failed to build reports `NOT CHECKED` naming the crashed step, and a pass over 0 pairs is never printed as `PASS`.
    **Workaround:** read the first `ERROR` line and ignore the steps after it.
    **Bead:** `beadloom-q2kh` (found and filed on 2026-10-20 from BDL-083 S3a, `beadloom-k6f1`)
    **measured_on:** 2026-10-20 9.0.0

359. [2026-10-20] [MEDIUM] `clean-room --at` inside a foreign git work tree builds the room without a warning, and its "carries no .git" line is false of what git sees there

    **Severity:** medium (a verdict taken in such a room is a verdict about the enclosing repository's git state; the six measure agents of BDL-083 S3 shared one scratchpad, and one room landed inside another agent's fixture)
    **Command:** `beadloom clean-room <bead-id> --at <a directory inside another repository's work tree> --carry ...`, then `beadloom ci` in the room
    **Context:** found 2026-10-20 on 9.0.0 (the code of `main` at `41245dc7`) by BDL-083 S3a (`beadloom-k6f1`): the session scratchpad held an older fixture repository at its top, and a room for #334 was built inside that work tree.
    **Issue:** the room was created without a word; `ci` in it read the nested-root refusal (`the git root is above the project root`), while the room's own report said `it carries no .git` — true of the room, false of what git resolves there. The command checks that it created the directory and not that no repository encloses it.
    **Expected:** `clean-room` refuses, or warns naming the enclosing work tree, when `--at` lies inside a git work tree, and the room's limits name what git resolves there.
    **Workaround:** build rooms under a directory that no repository encloses.
    **Bead:** `beadloom-q5sg` (found and filed on 2026-10-20 from BDL-083 S3a, `beadloom-k6f1`)
    **measured_on:** 2026-10-20 9.0.0

358. [2026-10-20] [MEDIUM] `ci`'s ownership block lists the merge-slot bead among the claimed beads while a neighbour holds the landing lock

    **Severity:** medium (the ownership report's population of claimed beads includes tracker state that is not work, so a reader counts one more claim than exists and sees a bead that can never own a finding)
    **Command:** `beadloom ci` (the ownership block) while another bead holds the merge slot
    **Context:** found 2026-10-20 on 9.0.0 (the code of `main` at `41245dc7`) by BDL-083 S3a (`beadloom-k6f1`) on this repository, while a neighbour of the wave held the landing lock.
    **Issue:** the block printed `beadloom-merge-slot owns no finding` among the claimed beads: the slot is kept by bd as a bead that is `in_progress` while held, and the ownership report takes every in-progress bead as a claim.
    **Expected:** the claimed-bead population excludes the merge-slot bead, or names it apart as the landing lock's record with its holder.
    **Workaround:** read the line as noise.
    **Bead:** `beadloom-of49` (found and filed on 2026-10-20 from BDL-083 S3a, `beadloom-k6f1`)
    **measured_on:** 2026-10-20 9.0.0

357. [2026-10-19] [HIGH] the hooks `install-hooks` writes never run on a repository `bd init` initialised: bd 1.0.4 sets `core.hooksPath=.beads/hooks` while `install-hooks` writes `.git/hooks`, so the pre-commit checks and the pre-push Gate are silent there and a push goes through with the hook installed

    **Severity:** high (every check the hooks carry — lint over staged paths, sync-check, the ACTIVE/tracker coherence, the landing-lock check, the pre-push Gate — is silent on the layout `bd init` produces, and nothing says so; the #326 class, a gate that does not fire)
    **Command:** `beadloom install-hooks`, `git push`, `beadloom doctor`
    **Context:** measured 2026-10-19 on a copy of the monorepo fixture with bd 1.0.4 while measuring #354 (S2g, `beadloom-89gm`): `bd init` had set `core.hooksPath=.beads/hooks`; `install-hooks` reported success and wrote `.git/hooks/pre-commit` and `.git/hooks/pre-push`; a push that the new landing check must refuse went through, because git ran the hooks under `.beads/hooks` and nothing there. This repository is safe only because it sets `core.hooksPath` back to `.git/hooks` by hand, a fact recorded nowhere a new clone reads.
    **Issue:** `install-hooks` writes where it assumes git looks instead of where git looks; `doctor` and `config-check` do not read `core.hooksPath`, so the installed-but-never-run state has no finding.
    **Expected:** `install-hooks` reads `core.hooksPath` and installs where git looks (chaining to an existing hook of bd's if one is there), or refuses by name with the setting and the two paths; `doctor` names a `core.hooksPath` that points away from the installed hooks; the pre-push liveness is measurable (a test over a repository whose `core.hooksPath` points elsewhere). Placed 2026-10-19 by the coordinator in BDL-083 as `beadloom-ba9w.23`, to be placed by S3's result.
    **Workaround:** `git config core.hooksPath .git/hooks` after `bd init`, or copy the hooks into `.beads/hooks`.
    **Bead:** `beadloom-ba9w.23` (re-measured live on 2026-10-20 by BDL-083 S3a, `beadloom-k6f1`)
    **measured_on:** 2026-10-20 9.0.0

356. [2026-10-19] [HIGH] `setup-agentic-flow --tool cursor` writes the five role files and a 17-line rules stub and no core, no project layer and no commands, so an agent on Cursor runs the flow with no DoD, no tracker discipline and no epic-closure duties; `setup-mcp` writes one machine's absolute path

    **Severity:** high (the adopter's second tool runs the composed flow with none of the rules the Gate's prose relies on; CI caught one formatting error, nothing caught the rest, and every finding below is one the flow was written to prevent)
    **Command:** `beadloom setup-agentic-flow` (manifest `flow-manifest.json`), `beadloom setup-mcp`, MCP `complete_bead`, `bd close`
    **Context:** measured 2026-10-19 on an anonymised adopter's monorepo (Python backend, Vue frontend, GitLab CI, trunk `master`) after a teammate on Cursor (Windows 10, PowerShell / Git bash) shipped two work items in one day, work item A (97 files, a new backend domain plus a frontend feature, two waves) and work item B (23 files, frontend only), both merged by the teammate as agreed with the owner. Audit sources: the exported tracker (`.beads/issues.jsonl`, 23 beads created that day), the planning documents of both items, the composed files, the CI pipelines, `./check.sh` on the merged trunk run by the owner (7 of 8 green, pytest 1400 passed, `beadloom ci` red in the owner's room and green in CI: see #353). Control case: the same teammate's morning bead, done under a hand-written task file that spelled out `./check.sh` and the COMPLETED format, carries a full COMPLETED with every rc and the room; the two afternoon items, done from the composed files alone, carry none. The agent does what it is shown.
    **What the manifest writes.** 16 files: for Claude Code `CLAUDE.md` (core, bd and Beadloom essentials, the project layer with the DoD, the STACK overlay), five roles and four commands (`task-init`, `coordinator`, `checkpoint`, `templates`); for Cursor the same five role files, byte-identical hashes, and `.cursor/rules/beadloom-flow.md` of 17 lines that says the roles exist and the Gate is the single source of truth. Grep of the Cursor role files: `check.sh` 0, `ISSUES.md` 0, `COMPLETED` 1 (tech-writer), `--claim` 1 (dev, test), `CHECKPOINT` 1 (dev). The composer's artifact kinds are `roles`, `commands`, `claude`, `docs`; a project fragment at `.beadloom/flow/roles/<role>.md` would have reached both tools' role files, but the adopter wrote the DoD into `.beadloom/flow/claude/CLAUDE.md`, the one kind with no Cursor counterpart, and nothing says which layer carries a rule to every tool. `.cursor/mcp.json` holds the owner's absolute path to the `beadloom` binary (`setup-mcp` writes `shutil.which("beadloom")`), the file is committed, so on the teammate's machine the MCP server cannot start from it.
    **What the flow then lost, item by item** (all measured on the merged trunk):
    1. DoD: the project's full check was never run for either item (no mention in documents, comments or issue entries); CI caught `ruff format` and nothing else was measured. COMPLETED comments with numbers on 2 of 23 beads (one of them the control case). Both review verdicts PASS with no tree measurement; item A's verdict says `review-brief unavailable (bd not on beadloom PATH in this shell)` and passes in prose. The mutation target list was extended to the new domain; the CI mutation job reports 21 survivors of 575, 6 of them in the new domain (an e-mail validator, two dataclass guards on each of two entities, a ranking builder), and nothing in the item names them, although the project layer rules a surviving domain mutant a test gap.
    2. Tracker discipline: 9 of 23 beads never started (`started_at` empty), item A's first wave carries no assignee, so `--claim` was not used; checkpoints on one bead; item A's second wave, six beads, created at 11:47 and closed at 11:57 one second apart with one identical `--reason`, after the code was done, so the refusing gate `complete_bead` was bypassed by plain `bd close`; descriptions 0–126 characters, the second-wave beads empty; the swarm molecule left open; the item B parent created twice (the agent closed the duplicate itself).
    3. Language: bead titles and item A's review verdict in English in a project whose layer rules Russian for every text; the rule lives only in the project layer Cursor never sees.
    4. Epic closure (the coordinator's duties in the project layer): item B's PRD/RFC/CONTEXT/PLAN left `Approved`; the issue entry the agent itself wrote ("closes on the landing commit") not archived; ROADMAP untouched, its "In progress" empty and its next item unrelated to either shipped item; `docs quality` reports item B's ACTIVE missing a template section; a hand-written `plan.json` for `bd create --graph` left in both document folders (the MCP `task_init` writes its plan to a temporary directory, so this one is the agent's, following the command text's relative `plan.json` from the document folder); the Windows surface drop and the `bd not on PATH` failure were written into bead comments and the project's own defect log, not into the Beadloom findings log the project layer names for findings about Beadloom.
    5. Room: the Windows-truncated surface (#353) was attested and committed as 183 pairs; CI then read `declared surface grew 183 → 375` and passed, the owner's room read 375 with 15 stale pairs under a dev build, and the release build had read 347 the day before: one trunk, three counts, and the committed one is the smallest. The new feature's operational settings were never provisioned on the host (the button ships live, the request answers 503): the PRD/RFC produced no provisioning bead and no role owns it.
    What went right: `## Axes` sections in both RFCs, `Tracker` cells filled with ids the tracker answered, graph and SPEC/DOC updated with sync-check green in CI, the export in every landing commit, an issue entry written to the template with a measurement, and the merge-slot ordering defect (#354) found and written into the adopter's handoff document.
    **Issue:** the Cursor adapter is parity in name only: the role files are shared, the layer that makes the roles a flow (claim, checkpoint, COMPLETED, close through the gate, DoD, language, closure duties) is composed for one tool, and every rule the Gate does not enforce is therefore absent on the other. The adopter closed the gap once with `check.sh` plus a hand-written task file, which is the measurement that the prose works when shown and that nothing else carries it.
    **Expected:** (a) `setup-agentic-flow --tool cursor` composes the same core, project layer and STACK overlay as `CLAUDE.md` into `.cursor/rules/` with `alwaysApply`, and the four commands as Cursor-readable rules; `config-check` reports a tool whose composition lacks a layer the other tool has, and the flow documentation says which layer (`roles`, `claude`, a future `cursor`) reaches which tool. (b) The DoD moves from prose into the gate: `complete_bead` today runs `beadloom ci` and the suite and closes on PASS, one bead per call, without asking for a COMPLETED comment, and a plain `bd close` is judged by nothing; `complete_bead` and `beadloom ci` refuse a closing bead with no COMPLETED comment carrying a measurement, a review bead with no verdict naming a tree measurement, and name a closed bead with no `started_at` or no comment as closed past the gate. (c) An epic-closure check: planning documents at `Done`, the item's issue entries archived, ROADMAP's in-progress section reconciled with the tracker, swarm molecules closed. (d) The language rule read by `docs quality` and by the tracker check (titles, comments). (e) `setup-mcp` writes a portable command (`beadloom mcp-serve` on PATH, or `uvx`), never one machine's absolute path. (f) One Beadloom command that runs the project's full check with per-command rc and a room line, so the adopter's `check.sh` is not needed. (g) the composed `task-init` text names an absolute path outside the document folder for the plan file, as the MCP `task_init` already does.
    **Workaround:** a hand-written task file per bead that spells out `./check.sh`, the COMPLETED format and the closure steps (the control case); or `.cursor/rules/` filled by hand from `.beadloom/flow/claude/CLAUDE.md`. Measured 2026-10-19 on this repository at `0f2fa2ec` (a 9.0.0 tree): all six claims hold, with two corrections — on a cursor-only project the core (439 lines) and the four commands ARE written, but under `.claude/` only, which no `.cursor/` file names, so Cursor reads the five roles and the 17-line stub, and the stub carries no `alwaysApply` front matter; `docs/guides/project-overlays.md` lists `.cursor/` for `roles` only but never says the other kinds skip Cursor, while `docs/guides/agentic-flow.md` claims parity. Two further defects: `init --bootstrap` writes the same absolute path into `.mcp.json`; `config-check` on a cursor-only project warns five times that `.claude/agents/<role>.md` is missing, a file `setup-agentic-flow` never writes for Cursor. Placed 2026-10-19 by the owner in BDL-083: (a), (e), (g) and the two further defects as S2 bead S2h `beadloom-ybxm` (RFC D13); (b) stays in the epic as `beadloom-ujm0`, a behaviour rule to agree before code, placed by S3's result; (c), (d) and (f) are features and are filed outside the epic by its non-goal as `beadloom-9yny`, `beadloom-vtul` and `beadloom-rkiu`.
    **Bead:** `beadloom-ujm0` (re-measured live on 2026-10-20 by BDL-083 S3d, `beadloom-d9te`; part (b). Parts (a), (e), (g) closed with `beadloom-ybxm`; (c), (d), (f) are the features `beadloom-9yny`, `beadloom-vtul`, `beadloom-rkiu` outside the epic; `beadloom-ba9w.26` and `beadloom-s9op` reproduce)
    **measured_on:** 2026-10-20 9.0.0

355. [2026-10-19] [MEDIUM] the branch-to-work-item binding reads `features/<KEY>` exactly, so a work item that ships in several pull requests (one branch per slice, `features/BDL-083-S2`) loses its declared axes, its focus document and the scope check on every branch but the first

    **Severity:** medium (the Gate's scope check, the `focus-document` medium of `waves` and the pre-commit axes judgement all read `NOT COMPARED` / `unmeasured` on such a branch, so a slice branch of a long epic runs with less measurement than its first branch, and nothing names the remedy)
    **Command:** `beadloom waves <six ready S2 bead ids>` on branch `features/BDL-083-S2` after S1 of BDL-083 merged from `features/BDL-083` (PR #106)
    **Context:** measured 2026-10-19 on `9b956965` by the coordinator of BDL-083 while activating S2. The plan printed `Declared axes: NOT COMPARED — the branch 'features/BDL-083-S2' names no work item among the planning documents` and `focus-document: unmeasured — the flow's routing and its planning documents were not read`; the same six beads on `features/BDL-083` were compared. BDL-083's PRD rules one PR per slice (ruling 1), and the flow's own trunk-based section says one PR per epic "or shippable slice", so a second branch for one work item is the flow's own case; the derivation that binds a branch to its documents reads the branch name as `features/<KEY>` and nothing else.
    **Issue:** two rules of the composed flow disagree — a work item may ship in several PRs, and a branch is bound to its work item only when it is named exactly `features/<KEY>` — and the second one wins silently: the measurements degrade and the plan says `NOT COMPARED` without saying why the branch did not bind or what name would.
    **Expected:** the binding reads the work-item key as a prefix of the branch name (`features/<KEY>` and `features/<KEY>-<anything>`), or the work item declares its branches in its ACTIVE/CONTEXT and the binding reads that; the plan's `NOT COMPARED` line names the branch shape it accepts. Workaround applied: the slice branch is named `features/BDL-083` again (the merged branch deleted first).
    **Bead:** `beadloom-bdnv` (re-measured live on 2026-10-20 by BDL-083 S3f, `beadloom-3jlv`)
    **measured_on:** 2026-10-20 9.0.0

353. [2026-10-19] [HIGH] on a Windows checkout the index stores paths with `\` while `source:` is written with `/`, and every `source:` match is a raw string compare: directory nodes read `no_indexed_code`, file nodes read stale, the declared surface reads 167 pairs of 347; `sync-surface.json` holds counts and no pair list, so the drop has no names

    **Severity:** high (a `sync-check` that pairs nothing with a directory node is a verdict over nothing, printed as a warning about the project; the Windows CI leg was withdrawn by owner decision, so no leg measures this class, and the first outside adopter's teammate runs Windows)
    **Command:** `beadloom sync-check` on a Windows checkout (Git Bash) of an outside monorepo (the first outside adopter: `backend/` with its own `pyproject.toml`, an FSD `frontend/`); compare `declared_pairs` in `.beadloom/sync-surface.json` between the macOS and the Windows checkout of one commit
    **Context:** reported 2026-10-19 by the adopter from a teammate's Windows checkout; read on `ac31da44` for BDL-083 by an explore pass of the coordinator. The warning "no indexed code under `backend/src/access/` … `frontend/src/`" names exactly the nodes whose `source:` is a directory; the 11 nodes reported stale are those whose `source:` is a file (`static.py`, `router.ts`, `client.ts`); the surface reads 167 pairs on Windows against 347 on macOS for the same commit. In the code: `application/reindex/change_detection.py:120` and `application/reindex/indexing.py:175, :248` write `str(Path.relative_to(project_root))` into `file_index.path` and `code_symbols.file_path` (backslashes on Windows); `graph/loader.py:174` keeps `source:` as written; `infrastructure/repository.py:612-618` (`_owned_file_clause`: `LIKE 'prefix%'` for a directory, `= ?` for a file), `repository.py:366-371` (`source_covers`: `startswith`) and `doc_sync/engine.py:230-243` (`_unchecked_reason` → `no_indexed_code`) compare the two as raw strings; no `\`→`/` normalisation on that path anywhere in `src/`; `doc_sync/surface_ledger.py:113-118` writes `declared_docs`, `declared_pairs`, `recorded_at` and nothing else. No test exercises the matching with backslash paths; `tests/test_ci_windows_dimension.py` records the withdrawn leg. Not traced here: why the file-source nodes come out as stale rather than unpaired (`path = ?` should miss the same way; the stale verdict likely comes from annotation-based pairs whose `code_symbols` paths are backslashed too), and whether the 167 surviving pairs are annotation-based or separator-free.
    **Issue:** two spellings of one path — the index writes the platform's separator, the graph writes POSIX — and the three matching sites compare them without a normalisation step, so on Windows a directory `source:` covers nothing and a file `source:` matches nothing; the surface ledger records how many pairs survived and not which, so a drop of 180 pairs is a number and not a list of names.
    **Expected:** indexed paths are stored as POSIX (`as_posix()`) at the three write sites and `source:` is normalised the same way at the three match sites, with one test that feeds backslash paths through `source_covers`, `_owned_file_clause` and `_unchecked_reason` and one that indexes a fixture under a simulated Windows separator; `sync-surface.json` carries the pair list (doc, file) beside the count so `sync-check` can name the pairs that a platform or a commit dropped. Placed 2026-10-19 by the owner in BDL-083 S2 as bead S2f (RFC D11); until it lands the Windows checkout's verdicts are not a measurement.
    **Bead:** none — the Windows half is not reproducible without a Windows room and the platform-free half (the pair list in `sync-surface.json`) is closed by S2f (`beadloom-27br`); put to the owner on 2026-10-20 (measured by BDL-083 S3a, `beadloom-k6f1`; PLAN.md, "S3 — rulings put to the owner")
    **measured_on:** 2026-10-20 9.0.0

351. [2026-10-18] [MEDIUM] `init --yes` on a monorepo with `backend/` and `frontend/` under `scan_paths` writes nodes for the frontend only; the Python backend under its own `pyproject.toml` gets no node and no preset

    **Severity:** medium (a first graph that omits one of the two projects is read as "the backend has no architecture", and every later `lint`, `ctx` and `sync-check` verdict on it is a verdict over nothing)
    **Command:** `beadloom init --yes` on `tests/fixtures/monorepo` (the monorepo fixture: `backend/pyproject.toml` + `uv.lock`, `frontend/` FSD, `.gitlab-ci.yml`)
    **Context:** measured 2026-10-18 on `14d89ecb` while building the fixture of BDL-083 S1g (`beadloom-483w`), Darwin arm64, Beadloom 9.0.0. `init --yes` wrote 7 nodes — `src`, `src-app`, `src-entities` and the rest, all under `frontend/src` — none under `backend/`, preset `monolith`, `scan_paths: [backend, frontend]`, no FSD rules. The fixture's `.beadloom/` was written by hand because of it. The same assumption as #332–#335: one project at the git root.
    **Issue:** the scanner finds the frontend's `src/` by its directory shape and finds no Python package because it looks for one at the root; a `pyproject.toml` below the root is not read as a distribution, so the preset and the rules are chosen from the frontend alone.
    **Expected:** `init` finds every `pyproject.toml` under `scan_paths` (the D6 rule of BDL-083), writes a node per found distribution's packages, and chooses the preset per project or names the mix; when it writes nodes for one of two found projects, its summary says which project got none.
    **Bead:** `beadloom-cn29` (re-measured live on 2026-10-20 by BDL-083 S3d, `beadloom-d9te`)
    **measured_on:** 2026-10-20 9.0.0

350. [2026-10-18] [LOW] `ctx --json` reports `framework: "jest"` for vitest spec files; the count is right and the name is wrong

    **Severity:** low (a wrong framework name in the context an agent reads; nothing else follows from it)
    **Command:** `beadloom ctx <frontend node> --json`
    **Context:** measured 2026-10-17 on an outside monorepo — the first adopter outside this repository: a Python backend under `backend/` (own `pyproject.toml` and `uv.lock`, run with uv), an FSD frontend under `frontend/`, a self-hosted GitLab CE pipeline, bd 1.0.4, Beadloom 9.0.0, Darwin arm64. Three new frontend nodes whose `*.spec.ts` files import `vitest`; `package.json` names no jest. `ctx --json` prints `"framework": "jest"` for all three with the right `test_count`.
    **Issue:** `context_oracle/test_layout.py:113` binds the `*.spec.*` / `*.test.*` patterns to the name `jest`, and nothing reads the imports or `package.json` to tell vitest from jest.
    **Expected:** the name comes from the test file's imports or the project's dependencies, or the field is omitted when only the pattern matched and the verdict says so.
    **Bead:** `beadloom-ogku` (re-measured live on 2026-10-20 by BDL-083 S3d, `beadloom-d9te`)
    **measured_on:** 2026-10-20 9.0.0

349. [2026-10-18] [LOW] a one-line edit in a spec file beside the code marks the node's document stale (`hash_changed`), and `sync-update --pair` re-attests 26 pairs to clear one test

    **Severity:** low (no wrong verdict about the code; a document is asked to attest a test it does not describe)
    **Command:** `beadloom sync-check`, `beadloom sync-update --pair`
    **Context:** measured 2026-10-17 on an outside monorepo — the first adopter outside this repository: a Python backend under `backend/` (own `pyproject.toml` and `uv.lock`, run with uv), an FSD frontend under `frontend/`, a self-hosted GitLab CE pipeline, bd 1.0.4, Beadloom 9.0.0, Darwin arm64, `tests.beside_code: true`. One expectation changed in `frontend/src/entities/<slice>/api/<name>.spec.ts`; the pair `<node>.md ↔ <name>.spec.ts` went `stale (hash_changed)`; `sync-update --pair` re-attested all 26 pairs of the node at once.
    **Issue:** a spec file inside a node's `source:` is paired with the node's document as if it were code, so every test edit demands a document attestation the document has nothing to say about. Sibling of #338 (the same indexing makes a test import a graph edge).
    **Expected:** test files pair under their own reason (or not at all) and `sync-update --pair` names the one pair it clears.
    **Bead:** `beadloom-fvi6` (re-measured live on 2026-10-20 by BDL-083 S3b, `beadloom-wvcc`)
    **measured_on:** 2026-10-20 9.0.0

348. [2026-10-18] [MEDIUM] incremental `reindex` creates no pair for a new spec file in a node's directory: `sync-check` says `untracked_files`, the hint sends the author to annotations, and only `reindex --full` clears it

    **Severity:** medium (a false stale with a hint that leads to source and document edits nobody needs)
    **Command:** `beadloom reindex && beadloom sync-check`, `beadloom sync-update --yes --pair`, `beadloom reindex --full`
    **Context:** measured 2026-10-17 on an outside monorepo — the first adopter outside this repository: a Python backend under `backend/` (own `pyproject.toml` and `uv.lock`, run with uv), an FSD frontend under `frontend/`, a self-hosted GitLab CE pipeline, bd 1.0.4, Beadloom 9.0.0, Darwin arm64. Two new spec files beside code under two frontend nodes, both nodes' documents already edited. `sync-check` rc 2, 16 pairs `stale`, reason `untracked_files: <new spec>`; the hint proposes a `# beadloom:<kind>=` annotation or a `beadloom:track` marker; `sync-update --yes --pair <doc>` answers that re-attestation does not clear `untracked_files`. `reindex --full` alone cleared it: 347 pairs fresh, rc 0, no annotation written.
    **Issue:** the file belongs to the node by `source:`; the incremental index did not open the pair, and the remedy the output names is the wrong one.
    **Expected:** incremental `reindex` opens pairs for new files under a node's directory; where it cannot, the `untracked_files` hint names `reindex --full` as the first outcome.
    **Workaround:** `beadloom reindex --full`.
    **Bead:** `beadloom-js85` (re-measured live on 2026-10-20 by BDL-083 S3b, `beadloom-wvcc`)
    **measured_on:** 2026-10-20 9.0.0

347. [2026-10-18] [MEDIUM] `untracked_files` is reported for a file that has its own node: a nested node's `source:` inside the parent's directory marks all the parent's pairs stale

    **Severity:** medium (a false stale on a document that did not change, about a file that has an owner)
    **Command:** `beadloom sync-check`
    **Context:** measured 2026-10-17 on an outside monorepo — the first adopter outside this repository: a Python backend under `backend/` (own `pyproject.toml` and `uv.lock`, run with uv), an FSD frontend under `frontend/`, a self-hosted GitLab CE pipeline, bd 1.0.4, Beadloom 9.0.0, Darwin arm64. New node `http-auth` with `source: backend/src/interface/http/routes/auth.py` and the annotation `component=http-auth` in the file; the directory `routes/` is the `source:` of the node `http-routes`. All six pairs of `http-routes` went `stale`, `reason: untracked_files`, `details: auth.py`. Naming `auth.py` in the parent's document does nothing: `doc_sync/engine.py` (`check_source_coverage`) credits only the parent's own pairs, the pairs of its `part_of` children, and a `<!-- beadloom:track=... -->` marker, and the output names neither.
    **Issue:** ownership by another node's `source:` or annotation does not count as coverage; the cause was found by reading the engine, not the output.
    **Expected:** a file owned by another node (by `source:` or by annotation) is not an untracked file of the directory's node; `details` names the owner and the two outcomes (`part_of` or `track`).
    **Workaround:** the `beadloom:track=<path>` marker in the parent's document.
    **Bead:** `beadloom-su66` (re-measured live on 2026-10-20 by BDL-083 S3b, `beadloom-wvcc`)
    **measured_on:** 2026-10-20 9.0.0

346. [2026-10-18] [MEDIUM] `symbols_changed` and `sibling_symbols_changed` survive the document edit they ask for: 62 pairs stay stale after the docs were updated, and the output does not say that only re-attestation clears them or which symbols changed

    **Severity:** medium (the shape of #182, closed 2026-08: the cause was narrowed, the remedy is still invisible from the output)
    **Command:** `beadloom reindex && beadloom sync-check`, `beadloom sync-update <ref> --yes`
    **Context:** measured 2026-10-16 on an outside monorepo — the first adopter outside this repository: a Python backend under `backend/` (own `pyproject.toml` and `uv.lock`, run with uv), an FSD frontend under `frontend/`, a self-hosted GitLab CE pipeline, bd 1.0.4, Beadloom 9.0.0, Darwin arm64. Code of six frontend nodes edited, their documents' Specification sections edited after that, then `reindex && sync-check`. Pairs with `hash_changed` became `ok`; 62 pairs with `symbols_changed` stayed `stale`, among them files that did not change (`sibling_symbols_changed` by node). Naming the new symbol in the document changed nothing. `sync-update <ref> --yes` per node cleared them.
    **Issue:** the output does not say that this reason is cleared only by attestation, nor which symbols changed, so the document's author cannot know what to describe or that describing it is not enough.
    **Expected:** for `symbols_changed` print the clearing action (`sync-update --yes` or `--pair`) and the symbols that changed.
    **Bead:** `beadloom-qvmp` (re-measured live on 2026-10-20 by BDL-083 S3b, `beadloom-wvcc`)
    **measured_on:** 2026-10-20 9.0.0

345. [2026-10-18] [LOW] docs-quality `section-not-in-use` reports an `Acceptance Criteria (overall)` section present in 0 of 1 PRD while the PRD holds it

    **Severity:** low (a wrong count in an advisory finding)
    **Command:** `beadloom docs quality` (through `beadloom ci`)
    **Context:** read by the adopter's reviewer on 2026-10-16 on an outside monorepo — the first adopter outside this repository: a Python backend under `backend/` (own `pyproject.toml` and `uv.lock`, run with uv), an FSD frontend under `frontend/`, a self-hosted GitLab CE pipeline, bd 1.0.4, Beadloom 9.0.0, Darwin arm64: the finding says the section is used by 0 of 1 PRD; the project's PRD carries the heading at line 113. Not re-measured here.
    **Issue:** either the heading match is stricter than the template's own text or the population counted is not the PRD that was read.
    **Expected:** the finding names the heading it looked for and the file it read, so a wrong count can be checked in seconds.
    **Bead:** `beadloom-2ryw` (re-measured live on 2026-10-20 by BDL-083 S3b, `beadloom-wvcc`)
    **measured_on:** 2026-10-20 9.0.0

344. [2026-10-18] [MEDIUM] `review-brief` for an epic's review bead prints `DECLARED SCOPE: none`, every file `OUTSIDE` and `0 document(s)` while the epic holds PRD, RFC and PLAN, over a base of 596 files against trunk

    **Severity:** medium (a review brief that declares nothing is a brief the reviewer has to rebuild by hand)
    **Command:** `beadloom review-brief <review bead of an epic>`
    **Context:** read by the adopter's reviewer on 2026-10-16 on an outside monorepo — the first adopter outside this repository: a Python backend under `backend/` (own `pyproject.toml` and `uv.lock`, run with uv), an FSD frontend under `frontend/`, a self-hosted GitLab CE pipeline, bd 1.0.4, Beadloom 9.0.0, Darwin arm64. The review bead carries no `refs:` of its own, the epic's documents are in the work item's folder, and the default base is the trunk branch, so the diff carries the previous stage's files too (see #330 for the same base in `scope-check`).
    **Issue:** the brief resolves scope from the bead alone and the base from trunk alone; a review bead of an epic has neither, and the brief does not say which of the two it lacked.
    **Expected:** the brief falls back to the work item's declared axes and documents when the bead declares none, takes the base from the branch's merge-base, and names both in its header.
    **Bead:** `beadloom-rehc` (re-measured live on 2026-10-20 by BDL-083 S3f, `beadloom-3jlv`)
    **measured_on:** 2026-10-20 9.0.0

343. [2026-10-18] [LOW] `snapshot compare` takes integers only, while `snapshot list` prints labels (`stage-1`, `wave-12`)

    **Severity:** low
    **Command:** `beadloom snapshot compare stage-1 wave-12`
    **Context:** read by the adopter's reviewer on 2026-10-16 on an outside monorepo — the first adopter outside this repository: a Python backend under `backend/` (own `pyproject.toml` and `uv.lock`, run with uv), an FSD frontend under `frontend/`, a self-hosted GitLab CE pipeline, bd 1.0.4, Beadloom 9.0.0, Darwin arm64: `'stage-1' is not a valid integer`. `services/commands/snapshot.py:100-101` declares both arguments `type=int`.
    **Issue:** the list surfaces a name the compare command refuses.
    **Expected:** `compare` accepts a label or a number, as `list` prints both.
    **Bead:** `beadloom-nbsf` (re-measured live on 2026-10-20 by BDL-083 S3e, `beadloom-8pzg`)
    **measured_on:** 2026-10-20 9.0.0

342. [2026-10-18] [MEDIUM] an annotated module pairs with the documents of two nodes: the annotation decides the pair, the enclosing `source:` directory keeps the ownership and the edges

    **Severity:** medium (two documents attest one module and the graph's edges go to the one the author did not name)
    **Command:** `beadloom sync-check`, `beadloom reindex`
    **Context:** measured 2026-10-16 on an outside monorepo — the first adopter outside this repository: a Python backend under `backend/` (own `pyproject.toml` and `uv.lock`, run with uv), an FSD frontend under `frontend/`, a self-hosted GitLab CE pipeline, bd 1.0.4, Beadloom 9.0.0, Darwin arm64. `# beadloom:component=http-app` on `interface/http/services.py` and `__main__.py`; the node `http-app` has `source: app.py`; the directory is the `source:` of `backend-interface`. Both modules pair with `http-app.md` and with the documents of `backend-interface`; `depends_on` edges to them land on `backend-interface`.
    **Issue:** the annotation resolves the document pair and not the owner, so the graph and the documents disagree about who the module belongs to.
    **Expected:** one owner per file, the annotation winning over the directory for pairs and edges alike, and `doctor` naming a file two nodes claim.
    **Bead:** `beadloom-kela` (re-measured live on 2026-10-20 by BDL-083 S3b, `beadloom-wvcc`)
    **measured_on:** 2026-10-20 9.0.0

341. [2026-10-18] [LOW] `forbid_import.from` is one fnmatch glob with no tag matcher: a layer-wide ban needs one rule per domain per library, and the inert copies are indistinguishable from a glob typo

    **Severity:** low (expressiveness; the adopter wrote ten rules where one would do)
    **Command:** `beadloom lint --strict` with `forbid_import` rules
    **Context:** measured 2026-10-16 on an outside monorepo — the first adopter outside this repository: a Python backend under `backend/` (own `pyproject.toml` and `uv.lock`, run with uv), an FSD frontend under `frontend/`, a self-hosted GitLab CE pipeline, bd 1.0.4, Beadloom 9.0.0, Darwin arm64. Moving `domain-no-io-imports-*` from one domain to two turned five rules into ten (`-<domain>-<library>`). `test_import_boundary` has `of: { tag: ... }`; `forbid_import` has no `from: { tag: ... }`, so "the `layer-domain` layer imports no httpx" cannot be one rule. The `*-os` copies are inert by `rule_liveness`, and that warning reads the same as a mistyped glob (see #328).
    **Expected:** `forbid_import.from` accepts the same matcher forms as `test_import_boundary.of`, a tag among them.
    **Bead:** `beadloom-rhfo` (re-measured live on 2026-10-20 by BDL-083 S3c, `beadloom-al1i`)
    **measured_on:** 2026-10-20 9.0.0

340. [2026-10-18] [MEDIUM] the node matcher in `require` reads one `kind`; a list is not parsed, so `has_edge_to: {{ kind: [domain, feature, service] }}` cannot be written and the rule degrades to `has_edge_to: {{}}`

    **Severity:** medium (a rule the author meant as "a component is `part_of` a domain, a feature or a service" is in force as "a component has some edge")
    **Command:** `beadloom lint --strict` with a `require` rule (`component-needs-parent`)
    **Context:** measured 2026-10-16 on an outside monorepo — the first adopter outside this repository: a Python backend under `backend/` (own `pyproject.toml` and `uv.lock`, run with uv), an FSD frontend under `frontend/`, a self-hosted GitLab CE pipeline, bd 1.0.4, Beadloom 9.0.0, Darwin arm64. `NodeMatcher` takes a single `kind`; the list form is not accepted, and the adopter wrote the weaker rule to keep the file loading.
    **Issue:** the rule language has no "one of these kinds", and the weaker rule it forces is silent about being weaker.
    **Expected:** `kind` accepts a list (any-of), or the loader refuses the list with a sentence instead of the author rewriting the rule.
    **Bead:** `beadloom-5v10` (re-measured live on 2026-10-20 by BDL-083 S3c, `beadloom-al1i`)
    **measured_on:** 2026-10-20 9.0.0

339. [2026-10-18] [HIGH] test-mirror resolution lets a deeper root with the same subpackage win: `backend/tests/unit/digest/test_sections.py` binds to `application/digest/sections.py`, not `digest/sections.py`, and nothing says two roots resolved

    **Severity:** high (a test bound to the wrong node without a warning; coverage, `ctx` and scenario verdicts all follow the binding)
    **Command:** `beadloom reindex`, `beadloom ctx <node> --json`
    **Context:** measured 2026-10-16 on an outside monorepo — the first adopter outside this repository: a Python backend under `backend/` (own `pyproject.toml` and `uv.lock`, run with uv), an FSD frontend under `frontend/`, a self-hosted GitLab CE pipeline, bd 1.0.4, Beadloom 9.0.0, Darwin arm64: a domain at `backend/src/digest/` and a feature at `backend/src/application/digest/`. Mirror roots are both `backend/src/` and every package under it; under the deeper root the directory `digest/` also holds code, `_resolve_in_root` returns `application/digest/sections.py`, and the deeper root wins. The same for `file_history/`.
    **Issue:** a directory with code satisfies the deeper root; the resolution that should need the module file to exist does not, and the two candidates are never reported.
    **Expected:** under a deeper root require the module file itself, not a directory that holds code; or report two resolutions of different depth and bind to none.
    **Workaround:** the folder form `tests/unit/digest/sections/test_*.py`: the directory `application/digest/sections/` does not exist and does not resolve.
    **Bead:** `beadloom-5xrz` (re-measured live on 2026-10-20 by BDL-083 S3d, `beadloom-d9te`)
    **measured_on:** 2026-10-20 9.0.0

338. [2026-10-18] [MEDIUM] a spec file beside the code is indexed as code: its import becomes a `depends_on` edge, `fsd-layers` judges a test's import as the module's, and the graph cannot tell a test edge from a code edge

    **Severity:** medium (a false edge at best; at worst a true layer violation in a test is fixed by hiding the import from the graph, and the graph then sees no edge at all)
    **Command:** `beadloom reindex`, `beadloom lint --strict`
    **Context:** measured 2026-10-16 on an outside monorepo — the first adopter outside this repository: a Python backend under `backend/` (own `pyproject.toml` and `uv.lock`, run with uv), an FSD frontend under `frontend/`, a self-hosted GitLab CE pipeline, bd 1.0.4, Beadloom 9.0.0, Darwin arm64, `tests.beside_code: true`. (1) `frontend/src/app/styles/base.spec.ts` imports an entity: the edge `app-styles → entities-<slice>` appeared and `fsd-layers` judged 58 edges instead of 57; the node document's "Depends on" describes a test. (2) In the second work item `KpiPanel.spec.ts` imported `@/app/styles` for a computed color: the edge `widgets-kpi-panel → app-styles` violated `fsd-layers` (error), `ci` rc 1 — a true finding Steiger reported as well. Fixed by loading the styles in `vitest.setup.ts` outside `scan_paths`, after which the graph sees no dependency of the test on `app-styles` at all.
    **Issue:** a test import and a code import are one kind of edge.
    **Expected:** edges carry whether their source is a test file; layer rules can exclude or include them explicitly; the node document lists test dependencies under their own heading.
    **Bead:** `beadloom-rq15` (re-measured live on 2026-10-20 by BDL-083 S3d, `beadloom-d9te`)
    **measured_on:** 2026-10-20 9.0.0

337. [2026-10-18] [MEDIUM] a `@node:` tag in a `.feature` file outside the scenario rules' glob is read by nobody: `ctx` shows no scenario, and one steps file for all scenarios binds to one node

    **Severity:** medium (the tag looks like a binding and nothing checks it)
    **Command:** `beadloom ctx <node> --json` after `@node:<node>` tags in `frontend/e2e/features/*.feature`
    **Context:** measured 2026-10-16 on an outside monorepo — the first adopter outside this repository: a Python backend under `backend/` (own `pyproject.toml` and `uv.lock`, run with uv), an FSD frontend under `frontend/`, a self-hosted GitLab CE pipeline, bd 1.0.4, Beadloom 9.0.0, Darwin arm64. `ctx` counts test files by `tests.patterns` under roots and beside code; the `@node:` tag is read only by `scenario-binding` and `scenario-coverage`, whose default glob is `tests/acceptance/features/**/*.feature`, and the project's features live elsewhere. To get the frontend e2e into `ctx` the adopter added the root `frontend/e2e`, a pattern `playwright: ["*.steps.ts"]` and `tests:` on the node; the steps file is one for all scenarios and binds to exactly one node, so the slice's `ctx` shows no e2e.
    **Issue:** the formula "tests bind three ways" promises the tag; outside the glob it is inert and unreported.
    **Expected:** `ctx` lists the scenarios tagged with the node on their own line, or `doctor` reports a `.feature` with `@node:` tags that no rule's glob reaches.
    **Bead:** `beadloom-wk6l` (re-measured live on 2026-10-20 by BDL-083 S3d, `beadloom-d9te`)
    **measured_on:** 2026-10-20 9.0.0

336. [2026-10-18] [LOW] `scope-check` reads only the table under `## Axes` with known axis names, so nodes the epic itself creates have no row form until the first wave lands and `impact` can see them

    **Severity:** low (the path to a green verdict exists and is not written anywhere)
    **Command:** `beadloom scope-check` in pre-commit after the first dev bead
    **Context:** measured 2026-10-16 on an outside monorepo — the first adopter outside this repository: a Python backend under `backend/` (own `pyproject.toml` and `uv.lock`, run with uv), an FSD frontend under `frontend/`, a self-hosted GitLab CE pipeline, bd 1.0.4, Beadloom 9.0.0, Darwin arm64. Rows kept in a separate table under their own heading were not read; only the `## Axes` table with the known axis names is. The adopter extended the main table with `branches` rows from `beadloom impact` over the new code after the first wave.
    **Expected:** the templates and `docs quality` say how a node the work item creates is declared in scope before it exists, or `scope-check` names the heading it read and the headings it ignored.
    **Bead:** `beadloom-xe1f` (re-measured live on 2026-10-20 by BDL-083 S3f, `beadloom-3jlv`)
    **measured_on:** 2026-10-20 9.0.0

325. [2026-10-14] [HIGH] a project root below the git root is not refused: `install-hooks` fails on a path, the hook bodies run without the project, and `sync-check --since` passes over two empty sides

    **Severity:** high (the owner's first team adoption was planned into a subfolder of a monorepo, with `.git` one level up; in that layout `sync-check --since` is green over every pair whatever changed, and nothing says so)
    **Command:** `beadloom init`, `beadloom doctor`, `beadloom install-hooks`, `beadloom sync-check --since <ref>`, `beadloom diff --since`, `beadloom review-brief`, `beadloom export`
    **Context:** read in the code at `c126ecff` on 2026-10-11, nothing run; filed during the ROADMAP re-rank of 2026-10-14. The project root is the current directory or `--project`, and no command searches upward for `.git`. With `.beadloom` in `frontend/` and `.git` above it: `install-hooks` builds `<project>/.git/hooks` (`services/commands/docsync.py:938`, the same in `services/commands/waves.py:288`) and fails — in a worktree too, since neither asks git for the real hooks path; the hook bodies git runs from the repository root call the commands without `--project`, so `scope-check` writes `NOT CHECKED`; `sync-check --since` reads `git show <ref>:<path>` with the path relative to the subfolder (`doc_sync/engine.py:879`, `:898`), both sides come back empty and every pair is called fresh — a false green; `diff --since` calls everything added for the same reason; `review-brief` mixes two path frames (git's and the project's); git activity on the dashboard reads as zero; `export` leaves `commit_sha` empty on purpose when the project root is not the repository root (`graph/federation/export.py:94`), so the portal's source links carry no revision either; the pages, tech-writer and room workflows are written under `<project>/.github/workflows`, which GitHub never reads. Covered by tests: the path translation in `git_baseline` and the empty commit in `export`. Nothing else is.
    **Issue:** half the tool degrades in a layout no command names as unsupported, and one of the degradations is a green verdict over an empty comparison. The owner's target topology (2026-10-12: every monorepo split into one repository per entity) makes the layout a transition-period case, so the fix is a refusal, not support.
    **Expected:** `init` and `doctor` say, in words and at a non-zero exit, that the git root is above the project root and that the project root must be the git root; `sync-check --since` refuses over a subfolder project instead of passing; the composed `CLAUDE.md` states the rule. The FSD-root-inside-the-repository key (a tree not under `src/`, the project root staying the git root) is a separate, optional stopgap, taken only if the frontend's split runs past about six months. Tracked by `beadloom-7pd6`.
    **Bead:** `beadloom-o71o` (re-measured live on 2026-10-20 by BDL-083 S3a, `beadloom-k6f1`)
    **measured_on:** 2026-10-20 9.0.0

323. [2026-10-13] [MEDIUM] an `@x` API inside a slice group has no form both linters accept: Beadloom reads `invoice/@x/receipt`, Steiger reads `invoice/@x/payment/receipt/index`

    **Severity:** medium (a spec-following project that groups its entities and runs both linters, as `init` sets it up to, is red on one of them whatever it names the file; the specification's text does not settle it)
    **Command:** `beadloom lint --strict` after `beadloom init --yes`; `npm run lint:fsd` (Steiger 0.7.0, `@feature-sliced/steiger-plugin` 0.8.0, recommended set)
    **Context:** S2T (`beadloom-q2el`) on `features/BDL-082` at `2dbd308b`, Darwin arm64, CPython 3.13.7, Node 22.9.0. The probe is the entities example of `/docs/reference/slice-groups` (`entities/payment/{invoice,receipt,transaction}`, `entities/user`, `entities/product`, each slice with `model/`, `ui/` and an index) with receipt importing invoice through an `@x` API. Three namings, measured: `invoice/@x/receipt.ts` — Beadloom rc 0, the edge marked `via: @x`; Steiger `fsd/forbidden-imports` error. `invoice/@x/payment-receipt.ts` — Beadloom 2 errors (`fsd-layers`, `fsd-public-api`); Steiger the same error. `invoice/@x/payment/receipt/index.ts` — Beadloom 2 errors; Steiger clean. Beadloom names the importer by its folder name (`graph/rules/cross_imports.py:19`, "`<target's folder>/@x/<importer's folder name>`"); Steiger's `isCrossImportPublicApi` (`@feature-sliced/filesystem`) compares against the slice name relative to the layer, `payment/receipt`, which only the index form under a nested folder can match. An `@x` from a grouped slice to an ungrouped one (`invoice/@x/user.ts` imported by `entities/user`) is clean under both. `/docs/reference/public-api` writes `entities/A/@x/B` with flat slices only, and `/docs/reference/slice-groups` does not mention `@x`. S1's `@x` (`beadloom-r15q`) and S2a's groups (`beadloom-6e2o`) each hold alone; this is where they meet.
    **Issue:** the rule-engine SPEC's table "Where Beadloom and Steiger differ" lists five measured differences and not this one, and no overlay says how a grouped slice names its `@x` API. An adopter who follows Steiger's form gets two Beadloom errors; one who follows Beadloom's gets a Steiger error.
    **Expected:** a form both accept. Beadloom reading `@x/<group>/<slice>` (a folder with its index, Steiger's form) as the grouped importer's API beside `@x/<slice>` makes one exist; failing that, the difference is a row of that table and a sentence of the dev and review overlays, with the measurement. Owner's call which.
    **Bead:** `beadloom-ben1` (re-measured live on 2026-10-20 by BDL-083 S3c, `beadloom-al1i`)
    **measured_on:** 2026-10-20 9.0.0

324. [2026-10-13] [LOW] the `init` wizard cancelled at the graph review re-indexes and takes the verdict, and does not print the line naming the code no installed parser read

    **Severity:** low (one sub-branch of the wizard; the next command the cancel message names, `beadloom reindex`, prints the line)
    **Command:** `beadloom init` (the wizard), answering `cancel` at "Proceed with this graph?"
    **Context:** S2T (`beadloom-q2el`) on `2dbd308b`, with the TypeScript grammar made absent at `code_indexer.get_lang_config` and the specification's group example (8 TypeScript files, one real crossing `register → login`). Answer `yes`: "Indexed 0 symbols, 0 imports" and "8 TypeScript files, no parser installed — install beadloom[languages]", rc 0. Answer `cancel`: the cancel message, the reindex `services/commands/setup.py` runs because a graph file was written, a verdict over that index, rc 0, and no line. The echo sits under `if "reindex" in result:` (`setup.py:1929-1930`), and the reindex the cancel branch triggers is the one `setup.py` runs itself, so `result` never records it. S2a (`beadloom-6e2o`) states that every branch of `init` prints the line.
    **Issue:** the cancel branch prints a green verdict over an index that read no code, with nothing saying why, which is the vacuous pass the line was added to explain.
    **Expected:** the line follows any reindex `init` ran, the one in `setup.py` included; a case in `tests/integration/services/commands/setup/test_the_init_wizard_names_the_code_it_could_not_read.py` for the `cancel` answer.
    **Bead:** `beadloom-1vy3` (re-measured live on 2026-10-20 by BDL-083 S3d, `beadloom-d9te`)
    **measured_on:** 2026-10-20 9.0.0

317. [2026-10-11] [HIGH] `ctx` surfaces 2 of the 17 rule types and the Markdown output none; its matcher reads `ref_id` and `kind` while the linter's reads `exclude`, `tag` and `tag_prefix`

    **Severity:** high (the product's main promise — the context names what the Gate will judge — is false for 15 of 17 rule types, silently; the class ROADMAP names)
    **Command:** `beadloom ctx <ref>`, `ctx --json`, MCP `get_context`, `beadloom prime`
    **Context:** an outside static audit (2026-10-11) read `context_oracle/builder.py` and named it; verified by file and line on `c126ecff`. `_collect_constraints` (`builder.py:340-350`) marks a rule relevant only when `rule_type` is `deny` (reads `from`/`to`) or `require` (reads `for`); the `rules` table holds 17 types (`application/reindex/rules_loader.py:76-250`; `AUTHORING_KEYS` in `graph/rules/loader.py:1229-1255`, "exactly one of" enforced at `:1375-1378`). `_matcher_applies` (`builder.py:294-315`) reads `ref_id` and `kind`; the linter's `NodeMatcher.matches` (`graph/rules/types.py:115-137`) reads `exclude`, `ref_id`, `kind`, `tag`, `tag_prefix`, and the evaluators pass the node's tags. All five fields are stored in `rule_json` (`rules_loader.py:23-39`), so the data is there and `ctx` does not read it. The default Markdown output, `_format_markdown` (`services/commands/query.py:54-202`), never renders `bundle["constraints"]`: even the two types reach a reader only through `--json` and MCP.
    **Issue:** three silences on one field. Fifteen rule types (`layers`, `slice_public_api`, `slice_shape`, `forbid`, `check`, every coverage and binding rule) never appear as a node's constraints, and nothing says the list is partial. A tag-only or `tag_prefix`-only matcher counts as applying to every node, an `exclude`d node still matches, `require.has_edge_to` and `deny.unless_edge` are not read — so the two types that are shown can be shown on the wrong nodes. The text output shows nothing at all. An agent reads a node's context, sees no rule, and meets the rule on the Gate. `README.ru.md:175` promises "действующие правила по узлу" (#322). The AGENTS.md generator fell behind the same key list the same way (#179: "seven of the twelve keys" mapped), and that was held by a test binding the generator to `AUTHORING_KEYS`; `ctx` has no such test.
    **Expected:** one derivation of "which rules apply to this node", used by the linter and the context builder — `NodeMatcher` plus a per-rule-type localisation; a rule type that cannot be localised to a node is listed under its own heading with the reason, so the list is complete or says where it is not; the Markdown output renders the constraints; a test holds both readers to `AUTHORING_KEYS`. For Debt to zero (`beadloom-ba9w.12`, P1); ranked after the Vue adoption with the rest, by the owner's order of 2026-10-11.
    **Bead:** `beadloom-ba9w.12` (re-measured live on 2026-10-20 by BDL-083 S3d, `beadloom-d9te`)
    **measured_on:** 2026-10-20 9.0.0

319. [2026-10-11] [MEDIUM] `ctx` has no token budget; chunks are capped by count, ordered by section type rather than by the focus node, and cut among ties in no promised order

    **Severity:** medium (the bundle is not sized by what a caller can carry, and two runs can differ)
    **Command:** `beadloom ctx <ref>`, `beadloom prime`
    **Context:** named by the outside audit of 2026-10-11; verified on `c126ecff`. `collect_chunks` (`context_oracle/builder.py:219-249`) caps rows with SQL `LIMIT ?` (`max_chunks`, default 10 at `:45`); chunk length is unbounded. `estimate_tokens` (`:23-29`, `len(text) // 4`) is never called in the builder; its callers are `application/status.py:57-66` and the TUI, which report a size. `ctx` takes `--depth`, `--max-nodes`, `--max-chunks` and no budget (`services/commands/query.py:261-263`). Ordering (`:237-246`) is `CASE c.section` (spec, invariants, constraints, api, tests, else) then `c.chunk_index`; the `WHERE` is `d.ref_id IN (...)` over the whole subgraph; nothing ranks by graph distance or by focus-node ownership; chunks of different documents tie on (section rank, `chunk_index`) and `LIMIT` cuts among them in an order SQLite does not promise.
    **Issue:** ten chunks can be ten lines or ten pages; a neighbour's documents can spend the limit before the focus node's own; the cut is not reproducible; "under 2K tokens" for `prime` is unmeasured on the path that produces it.
    **Expected:** an explicit budget in tokens, with the estimator named as an estimate; the focus node before its neighbours; constraints and freshness kept whole under any cut; a deterministic tie-breaker (ref_id, document path); and the bundle names what it left out so a caller can ask for it. For Debt to zero (`beadloom-ba9w.14`).
    **Bead:** `beadloom-ba9w.14` (re-measured live on 2026-10-20 by BDL-083 S3d, `beadloom-d9te`)
    **measured_on:** 2026-10-20 9.0.0

320. [2026-10-11] [LOW] `bfs_subgraph` records an edge before the `max_nodes` check, so a bundle's edges can name a node its `nodes` does not hold

    **Severity:** low (a consumer that reads the bundle as a closed subgraph gets an edge into nowhere; no reader is known to break today)
    **Command:** `beadloom ctx --json`, MCP `get_context`
    **Context:** named by the outside audit of 2026-10-11; verified on `c126ecff`. `context_oracle/builder.py:190-199` appends the edge at `:192-194` ("Record edge regardless of visit status") before `len(visited) >= max_nodes` at `:198`; a neighbour whose `nodes` row is missing (`nrow is None`, `:206`) keeps its edge too.
    **Issue:** the subgraph's contract is undefined — neither an induced subgraph nor one with marked boundary edges — and the cap is where the two readings part.
    **Expected:** choose and state the contract: drop the edge (induced), or carry it with a marker (`outside: true`) so the boundary is visible; a test holds it at the cap. For Debt to zero (`beadloom-ba9w.15`).
    **Bead:** `beadloom-ba9w.15` (re-measured live on 2026-10-20 by BDL-083 S3d, `beadloom-d9te`)
    **measured_on:** 2026-10-20 9.0.0

321. [2026-10-11] [MEDIUM] the CI workflow holds a write token on every job, the self-hosted tech-writer job runs the PR branch's code with no same-repository condition, and fork runs need approval only from first-time contributors

    **Severity:** medium (a trust boundary that is not stated; no exploit is claimed, and the mitigation GitHub applies to `pull_request` is in force)
    **Command:** `.github/workflows/ci.yml`; the repository's Actions settings
    **Context:** named by the outside audit of 2026-10-11; verified on `c126ecff` and the live settings. `ci.yml:42-44` grants `contents: write` and `pull-requests: write` at the workflow level and no job sets its own, so every job — including those running PR code on GitHub-hosted runners — holds the write token. Trigger `pull_request` (`:24-26`) plus `workflow_dispatch`; no `pull_request_target`. `ai-techwriter` is `runs-on: [self-hosted, ai-techwriter]` (`:448`), checks out `github.event.pull_request.head.ref` (`:455`) with `AI_TW_PAT || github.token` persisted (`:465`), then runs `uv sync`, `beadloom reindex` and `python -m beadloom.ai_agents.ai_techwriter` from that checkout with `QWEN_API_KEY`, `QWEN_BASE_URL` and `GH_TOKEN` in the environment (`:526-544`); no fork condition anywhere. Repository: public; `default_workflow_permissions: write`; fork-PR approval policy `first_time_contributors`. Mitigation in force: on `pull_request` GitHub withholds secrets from a fork's run and makes its token read-only — but the self-hosted runner still executes the PR's code on a persistent machine that holds the API key. Also: `ci.yml:124-127` says the two `tests-locale` check-runs are "NOT yet part of main's live branch protection (7 required contexts, not the 9)"; the live protection measured 2026-10-11 holds all nine, both locale legs included. The comment is stale, and the outside reader reported it as the state of the repository.
    **Issue:** the workflow's trust boundary exists only as GitHub's defaults, and one comment in it contradicts the measured protection. A returning outside contributor's fork PR runs unattended on the self-hosted machine.
    **Expected:** `permissions: contents: read` at the workflow level, write on the jobs that need it, named; `ai-techwriter` guarded by `github.event.pull_request.head.repo.full_name == github.repository`; the repository set to require approval for all outside collaborators; the publish token's scope reviewed; the stale comment replaced by the measured state with its date; one paragraph in the CI documentation stating what the workflow trusts and what it does not. An ephemeral runner is later. Standalone item `beadloom-dlb6` (P1), right after BDL-082 by the owner's decision of 2026-10-11.
    **Bead:** `beadloom-dlb6` (re-measured live on 2026-10-20 by BDL-083 S3a, `beadloom-k6f1`)
    **measured_on:** 2026-10-20 9.0.0

316. [2026-10-11] [MEDIUM] a `## Axes` section written as `###` subsections reads as zero rows, and the commit gate then calls every owned path outside the approval

    **Severity:** medium (an advisory that fires on every owned path is an advisory that gets ignored; the class of #178)
    **Command:** the pre-commit scope check (`beadloom.application.declared_scope.scope_check`), `beadloom docs quality`
    **Context:** BDL-082's S1a and S1b commits were warned `outside-the-declared-axes` for every `rule-engine` path, although the RFC's axes rule `rule-engine` in. Measured on `features/BDL-082` at `2ab2a56b`: the check reads `RFC.md` (the first file of the work item, in sorted order, that carries the heading), not `axes.md`. Its `## Axes` heading is followed by five tables, each under its own `### (a)` to `### (e)` subheading, one per derivation target. The section reader ends a section at the next heading of any level, so the `## Axes` body is one blank line: 0 rows, 0 kept nodes, 0 bounded contexts. Against `30605b71` all 14 owned paths of the branch are reported outside. `axes.md` reads the same way (0 rows).
    **Issue:** two silences. The reader cuts the section at a subheading and says nothing about the tables below it, and `docs quality` reports those tables only as `NOT CLASSIFIED ... judged by nothing`, with no `empty-section` finding on a heading that read as zero rows. The check's verdict line states the paths it judged and never that it judged them against an empty scope.
    **Expected:** a `## Axes` section reads the tables of its `###` subsections (the shape a work item with several derivation targets naturally takes), or a section that reads as zero rows is an `empty-section` finding and the scope check states "0 axes read" beside its verdict instead of reporting every path. `beadloom impact --section` writes one flat section, so the shape that trips this is hand-assembled. Found by S1T (`beadloom-wvzg`); for Debt to zero (`beadloom-ba9w`).
    **Bead:** `beadloom-zuby` (re-measured live on 2026-10-20 by BDL-083 S3f, `beadloom-3jlv`)
    **measured_on:** 2026-10-20 9.0.0

314. [2026-10-10] [MEDIUM] `write_text_atomic` and `write_yaml_atomic` leave every file they write at mode 0600

    **Severity:** medium (silent; a shared checkout or a CI cache loses group read on files Beadloom rewrote)
    **Command:** `beadloom init`, and every command that writes through `infrastructure/atomic_io.py`
    **Context:** BDL-080 S3f made `init` write an adopter's `package.json` atomically and measured the mode: 0644 became 0600; a `rules.yml` written by `init` is 0600 from birth. The temp file `mkstemp` creates is 0600 and the rename keeps it.
    **Issue:** the atomic writers never copy the target's mode (or apply the umask) onto the temp file before the rename, so the write silently changes permissions.
    **Expected:** an existing target keeps its mode; a new file gets `0666 & ~umask`. S3f restored `package.json`'s mode in `steiger_script` only; the fix belongs in `atomic_io.py` with a case per writer. Found by S3f (`beadloom-af99.14`); for Debt to zero (`beadloom-ba9w`).
    **Bead:** `beadloom-ba9w.6` (re-measured live on 2026-10-20 by BDL-083 S3d, `beadloom-d9te`)
    **measured_on:** 2026-10-20 9.0.0

312. [2026-10-10] [MEDIUM] a rule-level `scope:` is read only by `layers` rules and accepted without a word on every other rule type

    **Severity:** medium (a key the author believes narrows the rule has no effect, and nothing says so)
    **Command:** `beadloom lint`, `beadloom config-check`
    **Context:** BDL-080 S2d declared this repository's `slice_public_api` and `slice_shape` rules and tried `scope: vitepress-site` as the brief asked; `scope: no-such-node-anywhere` was accepted just the same, on every rule type but `layers`.
    **Issue:** the loader rejects unknown keys elsewhere but lets `scope:` through on rule types that never read it, so the rule looks narrowed and judges the whole graph.
    **Expected:** the loader refuses `scope:` on a rule type that does not read it (naming the types that do), or every tag-selected rule reads it; `config-check` names a rule carrying a key its type ignores. Found by S2d (`beadloom-af99.10`); for the rules epic (`beadloom-j4gi`) or Debt to zero (`beadloom-ba9w`).
    **Bead:** `beadloom-ba9w.4` (re-measured live on 2026-10-20 by BDL-083 S3c, `beadloom-al1i`)
    **measured_on:** 2026-10-20 9.0.0

310. [2026-10-10] [LOW] a verdict-room scenario assumes the run lacks the `search` extra, so `--all-extras` turns 8 tests red with one cause

    **Severity:** low (a false red for anyone who runs the suite with every extra; CI is unaffected because no leg installs `search`)
    **Command:** `uv run pytest tests/acceptance tests/integration tests/self_check` after `uv sync --all-extras`
    **Context:** S2T measured the full tree in a worktree synced with `--all-extras`. `tests/acceptance/application/verdict-room/room_extras.feature`, scenario "a leg installing different extras is not entered, and says which", expects the reason to name `search` as the missing extra; with the extra present the reason never names it.
    **Issue:** one scenario's assumption about the environment takes down `test_room_dependent_assertions` (5), the self_check shipped-suite test and `test_bead14_s4_binding::...reddens_the_run` (its sabotage control). It looked path-sensitive on 2026-10-09; it is extras-sensitive, measured under `/private/tmp` with CI's extras (passes) and under `$HOME` with all extras (fails).
    **Expected:** the scenario picks an extra the run provably lacks, or skips with the reason when every extra is installed. Found by S2T; for Debt to zero (`beadloom-ba9w`).
    **Bead:** `beadloom-ba9w.2` (re-measured live on 2026-10-20 by BDL-083 S3a, `beadloom-k6f1`)
    **measured_on:** 2026-10-20 9.0.0

309. [2026-10-10] [LOW] the reference-parser self-check hands gherkin's `TokenScanner` a path where it takes text, so it breaks on gherkin >= 30

    **Severity:** low (a test defect; the product does not use the reference parser)
    **Command:** `uv run pytest tests/unit/graph/scenarios/test_scenario_binding.py`
    **Context:** `test_our_own_suite_parses_the_way_the_reference_parser_reads_it` passes a file path to `TokenScanner`; gherkin-official 42 (pulled by pytest-bdd 9) takes the text. Seen in every clean room of BDL-080 (see #311); all 755 acceptance scenarios pass under 9.0.0 + 42.0.1.
    **Issue:** the test couples itself to a gherkin API that changed at 30, and the lock keeps it green only by chance of the pin.
    **Expected:** `TokenScanner(path.read_text(encoding="utf-8"))`, which works on 29 and 42. Found by S2T; for Debt to zero (`beadloom-ba9w`).
    **Bead:** `beadloom-ba9w.3` (re-measured live on 2026-10-20 by BDL-083 S3f, `beadloom-3jlv`)
    **measured_on:** 2026-10-20 9.0.0

308. [2026-10-08] [MEDIUM] active-sync reconciles the bead table and leaves ACTIVE.md's header, 'Current bead' and checklist stale when the work item ships

    **Severity:** medium (the document the owner reads as a work item's status says 'Development' after the item shipped)
    **Command:** the pre-commit `beadloom active-sync`
    **Context:** BDL-078 shipped on 2026-10-08; its ACTIVE.md table read done on every row, its header read 'Last updated: 2026-10-05, Phase: Development', its Current Bead named a bead, a Progress item was unticked. The owner: «Почему у нас BDL-078 файл Active не актуален и не закрыт? У нас же был механизм по ACTIVE.md, он не работает?»
    **Issue:** the mechanism reconciles the bead-status table only (BDL-053); the header, the Current Bead line and the checklist are prose it never reads, so a closed work item keeps a development-time header.
    **Expected:** when every bead incl. the parent is closed, active-sync sets the phase and date, rewrites the Bead line to 'none — shipped', and reports unticked Progress items; docs quality names an ACTIVE whose epic is closed but whose header is not. Tracked on `beadloom-cnty`.
    **Bead:** `beadloom-cnty` (re-measured live on 2026-10-20 by BDL-083 S3f, `beadloom-3jlv`)
    **measured_on:** 2026-10-20 9.0.0

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
    **Bead:** `beadloom-ohu6` (re-measured live on 2026-10-20 by BDL-083 S3f, `beadloom-3jlv`)
    **measured_on:** 2026-10-20 9.0.0

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
    **Bead:** `beadloom-y3qu` (re-measured live on 2026-10-20 by BDL-083 S3a, `beadloom-k6f1`)
    **measured_on:** 2026-10-20 9.0.0

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
    **Bead:** `beadloom-l5jb` (re-measured live on 2026-10-20 by BDL-083 S3f, `beadloom-3jlv`)
    **measured_on:** 2026-10-20 9.0.0

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
    **Bead:** `beadloom-6rfz` (re-measured live on 2026-10-20 by BDL-083 S3f, `beadloom-3jlv`; the owner's ruling is asked in PLAN.md, "S3 — rulings put to the owner")
    **measured_on:** 2026-10-20 9.0.0

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
    **Bead:** `beadloom-efcb` (re-measured live on 2026-10-20 by BDL-083 S3c, `beadloom-al1i`)
    **measured_on:** 2026-10-20 9.0.0

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
    **Bead:** `beadloom-ui47` (re-measured live on 2026-10-20 by BDL-083 S3c, `beadloom-al1i`)
    **measured_on:** 2026-10-20 9.0.0

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
    **Bead:** `beadloom-vu0a` (re-measured live on 2026-10-20 by BDL-083 S3c, `beadloom-al1i`)
    **measured_on:** 2026-10-20 9.0.0

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
    **Bead:** `beadloom-is2z` (re-measured live on 2026-10-20 by BDL-083 S3c, `beadloom-al1i`)
    **measured_on:** 2026-10-20 9.0.0

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
    **Bead:** `beadloom-f016` (re-measured live on 2026-10-20 by BDL-083 S3a, `beadloom-k6f1`)
    **measured_on:** 2026-10-20 9.0.0

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
    **Bead:** `beadloom-wrkj` (re-measured live on 2026-10-20 by BDL-083 S3a, `beadloom-k6f1`)
    **measured_on:** 2026-10-20 9.0.0

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
    **Bead:** `beadloom-4wps` (re-measured live on 2026-10-20 by BDL-083 S3b, `beadloom-wvcc`)
    **measured_on:** 2026-10-20 9.0.0

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
    **Bead:** `beadloom-nxiy` (re-measured live on 2026-10-20 by BDL-083 S3d, `beadloom-d9te`)
    **measured_on:** 2026-10-20 9.0.0

277. [2026-09-09] [LOW] the orphan check's role population is the manifest and its tool population is a constant, and only the first is stated

    **Severity:** low (no third tool ships today, so nothing here can produce it; it reaches an adopter before it reaches this repository)
    **Command:** `beadloom config-check`
    **Context:** BDL-068 S6, `beadloom-0mdo.69` re-asking its questions of `beadloom-ec1a`, which reports the role adapters a dropped tool leaves behind.
    **Measured:** `orphaned_adapters` opens `for tool, agent_dir in TOOL_AGENT_DIRS.items()` and keeps a manifest row only when its parent equals one of the two directories that constant holds. With `tools: [claude]`, a manifest recording `.windsurf/agents/dev.md` and that file on disk, the check returns zero orphans and states no population it could not enter. The control is in the same run: `.cursor/agents/dev.md` under the same configuration IS reported.
    **Why it matters:** the docstring makes exactly this argument for the other axis — "a role a later release renames or retires is still reported, because the record of the write does not depend on the roles this release happens to compose" — and the code does not make it for tools. It also names its limits carefully and names only the deleted-manifest one, so a reader has been told where the check is blind and this is not in the list. The adopter who meets it is the one who scaffolded under a release that shipped a third tool and upgraded to one that does not.
    **Expected:** either the tool is derived from the manifest row's own directory, which is where the record of the write already is, or the constant's role as the population is stated beside the limit that already is.
    **Held by:** `tests/test_the_populations_the_last_four_beads_report_over.py`, `FINDING BDL-068.S6-9`, `xfail(strict=True)`, with the silence pinned beside it — the file on disk, the manifest row present, zero orphans. Verified by mutation: deriving the tool from the row's directory turns it red as XPASS.
    **Related:** #191 (one command answering one hand edit two ways), #268-#273 (this bead's other findings).
    **Bead:** `beadloom-94ow` (re-measured live on 2026-10-20 by BDL-083 S3d, `beadloom-d9te`)
    **measured_on:** 2026-10-20 9.0.0

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
    **Bead:** `beadloom-jd2g` (re-measured live on 2026-10-20 by BDL-083 S3f, `beadloom-3jlv`)
    **measured_on:** 2026-10-20 9.0.0

273. [2026-09-09] [MEDIUM] a clean room states the CAUSE of its missing freshness baseline and never the population, and about forty verdicts in one epic were read as green over it

    **Severity:** medium (the instrument is honest and the claim is not, and the claim is what was written down forty times)
    **Command:** `beadloom clean-room <bead>` then `beadloom ci` inside the room
    **Context:** BDL-068 S6, `beadloom-uzck` measured it and `beadloom-0mdo.69` judged it. The clean room is the instrument every bead of two epics reports its verdict from.
    **Measured, twice, in two rooms:** `beadloom ci` reports `::notice::sync-check WARN: 0 pair(s) fresh, 450 NOT VERIFIED (no baseline — index rebuilt)`, while the same gate on the tree found the three stale pairs `beadloom-uzck`'s own change had created. Reproduced independently in `room-beadloom-0mdo.69` at the same numbers. A second step enters zero in the same room and says so as plainly: `scope-check SKIP: skipped — no branch is checked out`. The room's own report states the limit as a cause — "no .git, so a freshness check inside it has no baseline" — and carries no number, in both the human line and `RoomBuild.detail`.
    **Why it matters:** rc 0 with zero `::error` is what "green in a clean room" is written from, and it absorbs a `WARN` whose population was zero. This epic's own constraint is that the unresolved population is part of every answer, and 0 of 450 is that answer where "no baseline" is its cause.
    **Expected — and the three options are not equivalent.** The room must NOT carry a baseline: `.git` or the tree's index would import the freshness state the room exists to exclude, which is BDL-UX #243 in the other direction, and a room with no commits cannot hold a document-to-commit relationship truthfully. The room SHOULD hand over the number, because the project root is already in hand where the caveat is printed and a number is the form of a caveat that survives being skimmed. And the CLAIM must name it, because the claim is what forty verdicts were written in: "green in a clean room over N files, with doc freshness unverified over 0 of 450 pairs" is the same verdict, attributed.
    **Held by:** `tests/test_the_room_and_the_claim_it_supports.py`, `FINDING BDL-068.S6-6`, `xfail(strict=True)` on the room's clause, with the Gate's own honest line held beside it so a later simplification of either cannot remove the only place the population is stated.
    **Related:** #181 (a room's verdict is not the tree's), #258 (an expected red that trained a discount), #266 (the other thing the room's absent `.git` reaches), #243 (why a baseline must not be carried in).
    **Bead:** `beadloom-3bzw` (re-measured live on 2026-10-20 by BDL-083 S3a, `beadloom-k6f1`)
    **measured_on:** 2026-10-20 9.0.0

272. [2026-09-09] [MEDIUM] the `focus-document` medium reads the first cell of every table row in the file, so its population is neither the bead table nor the bead column

    **Severity:** medium (a false red on a bead table that numbers its waves first, and a false green on a bead named only by a table about something else)
    **Command:** `beadloom waves`
    **Context:** BDL-068 S6, `beadloom-0mdo.69`. `beadloom-0mdo.75` shipped the medium so a wave states the document every bead of a work item writes, and `FocusDocument.row_cells` is documented as "the FIRST cell of every markdown table row in the file", justified as "the column an ACTIVE table names its bead in".
    **Measured, on projects built to be arranged differently:** with a bead table headed `| Wave | Bead | Status |`, the check reports `failed — 2 of 2 bead(s) of this plan write into a focus document no row of it names` about a document that gives each of them a row of its own. With a bead named only by a second table — `| Bead | Why it was not done here |`, the deferral shape this repository's own `active-table` documents — the check reports `passed — each writes a line of its own` about a bead the status table has no row for.
    **Why it matters:** both halves are claims about an arrangement rather than about the flow. The column is a convention, and the population is every table row rather than the bead table's. Measured on this repository: 0 of 58 `ACTIVE.md` documents carry a short-form bead id outside the status table, and 28 of the 58 carry no bead-status table `active_table.find_status_column` can find at all — including BDL-068's own, where the medium still collects 35 first cells from four other tables. So neither face can be produced here, which is BDL-UX #240's condition again.
    **Expected:** the medium reads the bead table, through the same reader `active-sync` locates it with — a header whose first cell is `Bead` followed by an alignment row — and reports a document that holds no such table as a population it could not enter rather than as rows.
    **Held by:** `tests/test_the_flow_checks_an_arrangement_that_is_not_ours.py`, `FINDING BDL-068.S6-5`, two `xfail(strict=True)`, one per face, each with the measured verdict pinned beside it.
    **Related:** #257 (the medium's own entry), #268 (the two readers this computation spends), #210 (the ambiguity `names_bead` already refuses to guess at).
    **Bead:** `beadloom-v0z5` (re-measured live on 2026-10-20 by BDL-083 S3f, `beadloom-3jlv`)
    **measured_on:** 2026-10-20 9.0.0

271. [2026-09-09] [HIGH] a ledger file the claim reader drops is a free number, so the allocator hands out a number two writers then hold

    **Severity:** high (the collision the allocator exists to make impossible, produced by the allocator, silently)
    **Command:** `beadloom issue-number allocate`
    **Context:** BDL-068 S6, `beadloom-0mdo.69`. `beadloom-0mdo.66` allocates a number by `os.open(O_CREAT | O_EXCL)` of one claim file per number, and the file name IS the allocation.
    **Measured:** `read_claims` keeps a `*.md` whose stem matches `^(\d{1,6})$` and drops every other file in the ledger without reporting one. With a ledger holding `0003-the-clean-room-convention.md` and a log whose highest number is 2, `read_claims` returns `()`, `allocate_number` computes candidate 3, creates `0003.md` because that name is free, and returns 3. Two writers now hold #3 in two files. `check_issue_numbers` afterwards reports `claims=1` and one `unwritten-claim` — a finding about the wrong thing — and says nothing about the file it could not read.
    **Why it matters:** the name the reader drops is the name the module's own docstring invites. The claim file is described as "where the incident's body grows when the log becomes a composed view of the ledger", and a body grows a title. The failure is silent in both directions: nothing reports the unread file, and the number it holds is handed out as free — which is the mechanism BDL-UX #187, #211 and #253 were filed about, arriving through the door built to close them.
    **Expected:** a claim is the number at the start of the file name, so `0003-the-clean-room-convention.md` holds #3; and a `*.md` in the ledger that states no number at all is reported as a population the reader could not enter, never dropped.
    **Held by:** `tests/test_the_flow_checks_an_arrangement_that_is_not_ours.py`, `FINDING BDL-068.S6-4`, `xfail(strict=True)`, with the whole collision pinned beside it. Verified by mutation: relaxing the stem pattern to a prefix match turns it red as XPASS.
    **Related:** #187, #211, #253 (the collisions the allocator answers), #267 (the check's stated population).
    **Bead:** `beadloom-jkiy` (re-measured live on 2026-10-20 by BDL-083 S3f, `beadloom-3jlv`)
    **measured_on:** 2026-10-20 9.0.0

269. [2026-09-09] [MEDIUM] a one-hyphen alignment row is valid GitHub Flavored Markdown and reaches the approved-node list as an axis named `-`

    **Severity:** medium (a finding against a document that is correct, in the list `scope-check` compares every commit against)
    **Command:** `beadloom docs quality`, `beadloom scope-check`, and the `docs-quality` step of `beadloom ci`
    **Context:** BDL-068 S6, `beadloom-0mdo.69`. This is BDL-UX #244's own class inside the component that was lifted to end it.
    **Measured:** `doc_sync/tables.py`'s `_SEPARATOR_CELL_RE` is `^:?-{2,}:?$` and demands two hyphens. GitHub Flavored Markdown's delimiter row holds hyphens with optional colons and one hyphen is a well-formed cell, so `|-|-|-|-|-|` is a valid alignment row that `table_blocks` returns as DATA. `read_axes_section` over a `## Axes` section written that way returns two rows where the document states one: `axis='-'`, `node=''`, `in_scope=None`, and `check_axes_section` reports it as `axis-without-a-scope-decision`. `application/active_table/table.py`'s `is_separator_cells` answers the same row correctly, so the two predicates disagree and the lifted one is the wrong one.
    **Why it matters:** the kept rows of the `## Axes` section are the approved-node list a commit is judged against, and a phantom row enters it. The document's author has no repair except changing a spelling their Markdown renderer is indifferent to. Nothing here produces it because this repository writes `| ------ |`, which is the arrangement question BDL-UX #240 records.
    **Expected:** `^:?-+:?$`. The predicate answers what the format defines rather than what this repository happens to write.
    **Held by:** `tests/test_two_readers_of_one_markdown_table.py`, `FINDING BDL-068.S6-2`, two `xfail(strict=True)` — one on the predicate and one on the section it reaches. Verified by mutation: widening the regex turns both red as XPASS.
    **Related:** #244 (the same class, first instance), #268 (the second reader that gets this right).
    **Bead:** `beadloom-5e8r` (re-measured live on 2026-10-20 by BDL-083 S3f, `beadloom-3jlv`)
    **measured_on:** 2026-10-20 9.0.0

268. [2026-09-09] [MEDIUM] two readers of one markdown table row, and the component lifted so a third could not be wrong is one of them

    **Severity:** medium (0 disagreements on this repository's 259 planning documents, so nothing here can produce it; the two readers meet inside one computation and one document)
    **Command:** `beadloom waves`, `beadloom active-sync`, and every check that reads a `## Axes` section
    **Context:** BDL-068 S6, `beadloom-0mdo.69`. `doc_sync/tables.py` was lifted by `beadloom-0mdo.46` after two readers of one fact disagreed twice in one slice, and its docstring states the purpose: "a third reader cannot be wrong about it a third time" (#213, #244, #259).
    **Measured:** `application/active_table/table.py:33` splits a row with its own body — `stripped.strip("|").split("|")` — and carries its own separator predicate. It is older than the component and does not spend it. A shape derivation over the parsed source finds exactly four `split("|")` sites in `src/beadloom`: two are row readers and two belong to `guards/surface.py` and are about tool matchers. The two row readers answer three measured rows differently: `|` and `||` are not a row to `cells_of` and one empty cell to `split_table_row`, and `|| a | b ||` is four cells to the first and two to the second.
    **Why it matters:** the `focus-document` medium spends BOTH in one computation — it collects a document's rows with `tables.cells_of` and asks `active_table`'s `names_bead` about the cells it got — while `active-sync` reads the same document with `split_table_row`. A row written `|| beadloom-x.1 | dev | done ||` gives `active-sync` a bead id in its first cell and gives the medium an empty one, so one instrument updates that bead's status and the other reports that no row names it. Measured on this repository: 0 disagreements over 259 planning documents and 32 353 lines, 12 over 610 markdown files and 106 740 lines, every one of them a lone `|` inside a diagram. The divergence is invisible on this arrangement, which is BDL-UX #240's condition.
    **Expected:** one reader. `split_table_row` spends `tables.cells_of`, or the component absorbs it — the two bodies answer one question and the question has one answer.
    **Held by:** `tests/test_two_readers_of_one_markdown_table.py`, `FINDING BDL-068.S6-1`, `xfail(strict=True)`. `TestThePackageHasTwoReadersOfOneRow` derives the population from the source, so a FOURTH pipe-split has to be classified by whoever adds it.
    **Related:** #213, #244, #259 (the three times a table boundary was read wrongly), #272 (the medium that spends both).
    **Bead:** `beadloom-5e8r` (re-measured live on 2026-10-20 by BDL-083 S3f, `beadloom-3jlv`)
    **measured_on:** 2026-10-20 9.0.0

263. [2026-09-09] [MEDIUM] the codec sweep's vocabulary is a list of call names, so a decoding call it has never seen reads as no call at all

    **Severity:** medium (the instrument reports clean about a population it did not enter, which is the class it exists to prevent)
    **Command:** `uv run pytest tests/test_locale_independent_io.py tests/test_decode_handlers.py`
    **Context:** BDL-068 S6, `beadloom-0mdo.66`. The allocator writes its claim file through `os.open(O_CREAT | O_EXCL)` and then `os.fdopen(handle, "w", encoding="utf-8")`, which is the first `os.fdopen` in `src/beadloom`.
    **Measured:** the shared definition in `tests/decoding_calls.py` recognises a text-I/O call by NAME — `read_text`, `write_text`, `open`, `decode` and five `subprocess` entry points. `os.fdopen` is in none of them, so both instruments walked past a call that decodes: the codec sweep did not ask it to state an `encoding=`, and the handler ledger did not ask what a decode failure there would do. It happens to state its codec, so nothing is wrong today — which is exactly why it is worth recording, because the next one need not.
    **The same run found the opposite error and it is already fixed:** `os.open` was read AS a text open, because `called_name` returns `open` for `os.open(...)` and the module-name guard only knew `tarfile`, `zipfile` and friends. That produced a false positive in both instruments at once and is closed here by `DESCRIPTOR_OPENERS` — the same shape as the `CONTAINER_OPENERS` note above it, which its own comment says was found the same way, by a call this package had never made.
    **Why it is not closed with it:** the false positive is a fixed misreading of a known name; this is an unknown name, and the repair is a different one. A vocabulary of call names cannot be completed by adding to it — `io.TextIOWrapper`, `codecs.open` and `csv.reader` over a text handle are all outside it too. The honest fix is the one this project applies everywhere else: report the population the sweep could not classify, so a call it does not recognise arrives as *unresolved* rather than as absent.
    **Expected:** `tests/decoding_calls.py` states what it did NOT classify, and the two instruments report that count beside their verdicts.
    **Related:** #173 (unverifiable is not clean), and `beadloom-0mdo.64`, which found `CONTAINER_OPENERS` by rooting the sweep at `tests/`.
    **Bead:** `beadloom-262q` (re-measured live on 2026-10-20 by BDL-083 S3d, `beadloom-d9te`)
    **measured_on:** 2026-10-20 9.0.0

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
    **Bead:** `beadloom-76fp` (re-measured live on 2026-10-20 by BDL-083 S3f, `beadloom-3jlv`)
    **measured_on:** 2026-10-20 9.0.0

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
    **Bead:** `beadloom-velh` (re-measured live on 2026-10-20 by BDL-083 S3f, `beadloom-3jlv`)
    **measured_on:** 2026-10-20 9.0.0

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
    **Bead:** `beadloom-58yp` (re-measured live on 2026-10-20 by BDL-083 S3a, `beadloom-k6f1`)
    **measured_on:** 2026-10-20 9.0.0

242. [2026-09-04] [LOW] the launch context a subagent receives carries a `git status` snapshot that is stale by construction, and one agent published from it

    **Severity:** low (recoverable, and it was recovered) — but it produced a withdrawn public sentence, which is the outcome this project spends the most effort avoiding
    **Command:** none — the agent harness's launch context
    **Context:** BDL-068 S4. Every subagent's launch context opens with a `git status` block captured when the SESSION started, not when the agent did. `beadloom-0mdo.34` measured its own: the block described branch `features/BDL-067` at `6fb5093` with three modified `src/` files, against a tree that was actually `features/BDL-068` at `3ec1db2` with none. Twenty-eight commits and five waves of drift.
    **Issue:** `beadloom-en0x` described the room its combined-tree verdict was taken in using that block instead of re-deriving the state, published the sentence, then caught it and withdrew it in `f45dd62`. The block is labelled as a snapshot, which is honest; what it is not is inert, because it sits where an agent looks first and reads like current state.
    **Why it belongs in this log rather than being shrugged off:** it is the same shape as everything else in BDL-068 — a fact that was true when it was written, presented without the reader being able to tell how stale it is. The difference is that the agent caught its own instance, which is what the flow is supposed to produce.
    **Expected, and it is ours to do rather than the harness's:** the role protocol says a tree fact is DERIVED at the moment it is stated, never read from launch context. `beadloom-0mdo.27`'s duty mechanism can carry that as a declared duty, which makes it checkable rather than remembered. Routed as a note on the S6 slice, not as its own bead.
    **Bead:** `beadloom-f3gl` (re-measured live on 2026-10-20 by BDL-083 S3f, `beadloom-3jlv`)
    **measured_on:** 2026-10-20 9.0.0

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
    **Bead:** `beadloom-velh` (re-measured live on 2026-10-20 by BDL-083 S3f, `beadloom-3jlv`)
    **measured_on:** 2026-10-20 9.0.0

230. [2026-09-03] [MEDIUM] a branch whose name carries a suffix after the work-item key names no work item

    **Severity:** medium
    **Tracker:** `beadloom-bdnv`
    **Issue:** On `features/BDL-068-S2S3` the brief's work-item channel reads NOT INSPECTED while the reviewer was reading RFC.md and CONTEXT.md from that very folder. `declared_scope.py` matches a segment that EQUALS a key; it should match one that BEGINS WITH it, longest key wins. The coordinator's branch naming exposed it; the defect is real for any adopter whose branch names carry a suffix.
    **Detail:** the full measurement, the reproduction and the fix shape are on the bead — `bd show beadloom-bdnv`. This entry exists so the number is allocated and the finding is findable; the tracker is the source of truth for its text.
    **Bead:** `beadloom-bdnv` (re-measured live on 2026-10-20 by BDL-083 S3f, `beadloom-3jlv`)
    **measured_on:** 2026-10-20 9.0.0

229. [2026-09-03] [MEDIUM] the brief sends the reviewer to the tracker export and does not name it as a channel

    **Severity:** medium
    **Tracker:** `beadloom-qil0`
    **Issue:** `git diff main...HEAD -- .beads/issues.jsonl` adds 16 record lines carrying 30 author comments and 81,270 characters, and the brief's own change inventory lists that file and tells the reviewer to read it. `models.py:170` asserted that a reviewer seeing `0 withheld` learns the author wrote nothing; on that run it was false by 31,544 characters.
    **Detail:** the full measurement, the reproduction and the fix shape are on the bead — `bd show beadloom-qil0`. This entry exists so the number is allocated and the finding is findable; the tracker is the source of truth for its text.
    **Bead:** `beadloom-qil0` (re-measured live on 2026-10-20 by BDL-083 S3f, `beadloom-3jlv`)
    **measured_on:** 2026-10-20 9.0.0

225. [2026-09-03] [HIGH] `impact` under-reports on `src/<one package>` beside code outside src/

    **Severity:** high
    **Tracker:** `beadloom-f7kb`
    **Issue:** The narrowing gap is compared against `src/<package>` rather than against the project, so Python outside `src/` is swept by nothing and declared by nothing, with `callers.resolved` and `co_writers.resolved` both True over a demonstrably partial answer. The commonest Python layout there is. Found by the S1 re-review with a red proof in the layout matrix's own form.
    **Detail:** the full measurement, the reproduction and the fix shape are on the bead — `bd show beadloom-f7kb`. This entry exists so the number is allocated and the finding is findable; the tracker is the source of truth for its text.
    **Bead:** `beadloom-f7kb` (re-measured live on 2026-10-20 by BDL-083 S3d, `beadloom-d9te`)
    **measured_on:** 2026-10-20 9.0.0

224. [2026-09-02] [HIGH] a new test file landing on an existing path deletes its scenarios and the suite goes GREEN over the wreckage

    **Severity:** high
    **Tracker:** `beadloom-hdky`
    **Issue:** `beadloom-0mdo.6` overwrote two of BDL-061 S6's acceptance files. Deleting scenarios REMOVES tests rather than failing them: 8026 baseline, 8087 after, +61 where 63 were added. `git status` showing ` M` where `??` was expected is the only thing that reports it; `scenario-coverage` cannot see that a file which held four scenarios now holds nine different ones.
    **Detail:** the full measurement, the reproduction and the fix shape are on the bead — `bd show beadloom-hdky`. This entry exists so the number is allocated and the finding is findable; the tracker is the source of truth for its text.
    **Bead:** `beadloom-hdky` (re-measured live on 2026-10-20 by BDL-083 S3f, `beadloom-3jlv`)
    **measured_on:** 2026-10-20 9.0.0

223. [2026-09-02] [LOW] 102 planning documents depart from the shape their peers keep

    **Severity:** low
    **Tracker:** `beadloom-l27n`
    **Issue:** Measured when the section checks were wired: missing-section 102 over 256 read, under `doc_shape`'s majority policy; a non-peer-relative policy over the same requirement gives 767. The 102 are the archive — old RFCs with no `## Overview`, old PRDs with no `## Impact`. Reported rather than suppressed by owner decision.
    **Detail:** the full measurement, the reproduction and the fix shape are on the bead — `bd show beadloom-l27n`. This entry exists so the number is allocated and the finding is findable; the tracker is the source of truth for its text.
    **Bead:** `beadloom-l27n` (re-measured live on 2026-10-20 by BDL-083 S3b, `beadloom-wvcc`; the owner's ruling is asked in PLAN.md, "S3 — rulings put to the owner")
    **measured_on:** 2026-10-20 9.0.0

222. [2026-09-02] [LOW] The independent cross-check states and computes an attribution rule the implementation stopped using

    **Severity:** low (it cannot fail against the regression it was written to catch, and it will one day fail against a correct implementation)
    **Command:** `uv run pytest tests/test_init_one_table_over_every_axis.py`
    **Context:** found by the ninth review pass of BDL-067 (`beadloom-e8s4.28`), filed rather than fixed under the epic's stop rule.
    **Issue:** invariant 3 of that module reads "the bug-report request appears exactly where THIS run wrote both the rules and the graph FILE the failing node came from". That was the key until BDL-067 `.24`; the shipped key is `_this_run_wrote_the_node_that_fails`, read at the NODE grain. `RunOutcome.corner` still computes the file-grain answer, under a docstring saying the case fails when the report and the tree disagree.
    **Measured:** over all ten red runs the table performs, both grains computed side by side, they AGREE in every cell. The agreement is a consequence of the ARRANGEMENTS, not of the rules: since `.21`, `generate_skeletons` annotates every node on disk, so a cell that rewrites `legacy.yml` also rewrites the failing node's own entry. The one tree where the two rules diverge — the file moves for a SIBLING while the failing node does not — is the tree the eighth review measured, and no cell of this table builds it.
    **Expected:** either compute the corner at the node grain here too (the module already digests `.beadloom/_graph/` before and after, so a `{ref_id: node}` digest is the same walk), or keep the file grain as a deliberately coarser instrument and SAY so — rename `wrote_the_failing_graph_file`, correct invariant 3 to name the node, and add one case asserting that the two grains coincide on this table, so the day they stop coinciding is the day it is noticed.
    **Why it is not merge-blocking:** the divergence tree is covered by two sibling classes, `TestTheGraphHalfIsAskedOfTheNodeAndNotOfTheFile` and `TestEachSentenceSpeaksAtTheGrainItsKeyIsReadAt`, which build it and would go red.
    **Tracker:** `beadloom-tgo8`.
    **Bead:** `beadloom-tgo8` (re-measured live on 2026-10-20 by BDL-083 S3c, `beadloom-al1i`)
    **measured_on:** 2026-10-20 9.0.0

221. [2026-09-02] [MEDIUM] Attribution keys on the whole node, so annotating a node makes its neighbour's failure read as ours

    **Severity:** medium (it asks an adopter for a bug report about a writer that did not run, on an ordinary tree shape)
    **Command:** `beadloom init --bootstrap` on a project carrying an inherited `.beadloom/_graph/legacy.yml`
    **Context:** the open question of BDL-067 `.24`, answered NO by the eighth review (`beadloom-e8s4.26`) and re-planned out on the reviewer's own recommendation.
    **Issue:** "is a node whose `docs:` field this run wrote a node this run wrote?" — not for this instrument. The instrument exists to answer whether this run produced the property that makes the node FAIL, and the failing rule reads `kind` and `part_of` edges. `docs:` is not a field the finding's rule can see, so answering yes attributes to Beadloom a failure Beadloom did not cause.
    **Measured:** an inherited `legacy.yml` holding ONE undocumented orphan still prints `(True, True)` — "This is a defect in Beadloom's bootstrap rather than in your project — please report it" — about a node no writer in this run produced. Single-node inherited graph files are at least as ordinary as the two-node case BDL-067 `.24` did close.
    **Expected:** key the node sample on a RULE-RELEVANT PROJECTION of the node, DERIVED rather than hand-listed — digest the node restricted to the fields the rule engine can read, taken from `graph/rules/loader.py`'s own authoring surface. A `docs:`-only annotation is then not a change the failing rule can see, while a `kind`, `source` or edge rewrite still reads as ours, so the created-or-CHANGED error direction is preserved rather than traded away. **Not** an exemption for a `docs:`-only diff: a filter over one named field goes stale the next time the block gains a writer.
    **Precedent:** `test_every_authoring_key_the_loader_accepts_has_a_type` holds `_detect_rule_type` to `graph.rules.loader.AUTHORING_KEYS`, so a rule dimension added later widens the projection by the same act.
    **Tracker:** `beadloom-0mb5`.
    **Bead:** `beadloom-0mb5` (re-measured live on 2026-10-20 by BDL-083 S3c, `beadloom-al1i`)
    **measured_on:** 2026-10-20 9.0.0

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
    **Bead:** `beadloom-l22o` (re-measured live on 2026-10-20 by BDL-083 S3d, `beadloom-d9te`)
    **measured_on:** 2026-10-20 9.0.0

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
    **Bead:** `beadloom-tm76` (re-measured live on 2026-10-20 by BDL-083 S3f, `beadloom-3jlv`; the owner's ruling is asked in PLAN.md, "S3 — rulings put to the owner")
    **measured_on:** 2026-10-20 9.0.0

218. [2026-09-02] [HIGH] `init` holds three hand-written step sequences and no artifact states what the sequence is

    **Severity:** high (it is the class the seventh review pass found after six passes of fixing its instances one symbol at a time)
    **Command:** `beadloom init` (all four entry points)
    **Context:** re-planned out of BDL-067 by owner decision on the seventh review's diagnosis. **Needs `/task-init` and an RFC before any code** — the fix changes `init`'s control flow, and appending it as cycle 8 of a bug fix is what the re-plan rule ranked P0 in the ROADMAP exists to prevent.
    **Issue, quoted from `beadloom-e8s4.23`:** "Every instrument this epic has built ranges over ONE symbol's callers. Nothing ranges over one entry point's STEPS. `init` holds three hand-written step sequences — the `--bootstrap` branch inline in `setup.py`, `non_interactive_init`, `interactive_init` — and no artifact states what the sequence is. So the next divergence was a step that two sequences run and the third does not, and a step that runs once over one writer's output and is never revisited."
    **Three measured instances:** `auto_link_docs` is run by two of the three sequences, so doc-sync is off on the third; `generate_rules` is a second whole-graph artifact rendered from ONE writer's node list; and `--bootstrap` honours neither the existing-`.beadloom/` check nor `--force`, unlike `--yes`, so it re-bootstraps over an existing graph silently.
    **Expected:** declare what `init`'s sequence IS — one artifact the entry points share, or derive from — rather than fixing the sequences one divergence at a time.
    **Evidence that iteration had stopped paying:** majors per review pass on BDL-067 ran 2, 1, 1, 3, 4, 3, 5, 2, 2.
    **Tracker:** `beadloom-6i5q`.
    **Bead:** `beadloom-6i5q` (re-measured live on 2026-10-20 by BDL-083 S3d, `beadloom-d9te`)
    **measured_on:** 2026-10-20 9.0.0

217. [2026-09-02] [MEDIUM] An earlier `init --mode import` leaves domains that no later run will parent

    **Severity:** medium (the report is honest about it, and the adopter still has a manual repair with no reminder)
    **Command:** `beadloom init --yes --mode import`, then `beadloom init --bootstrap` on the same tree
    **Context:** found and named by BDL-067 `.17` as its own stated limit, reported rather than absorbed.
    **Issue:** `.17` made the verdict tree-level, which removed the REASON for the `--mode import` carve-out rather than the check. It does not parent the nodes an EARLIER import run already left in `imported.yml`. So the sequence the fifth review measured is narrowed, not closed: an import-only run followed later by a bootstrap still meets domain nodes that no run of this command parented. The report now names them honestly — it prints "the graph already in `.beadloom/_graph/`" and asks for no bug report — and the graph is still one the adopter repairs by hand.
    **Why `.17` stopped there:** making the bootstrap parent nodes it did not write means REWRITING A GRAPH FILE THE ADOPTER MAY HAVE AUTHORED. Every other fix in BDL-067 constrains what Beadloom writes about its own output; this one would have Beadloom edit an existing graph on the adopter's disk.
    **Expected — a decision, before any code:** (a) parent the orphans on a later run, which is structurally complete and edits a file the adopter may own; (b) report them and stop, which is honest and leaves a manual repair with no reminder; or (c) parent only nodes carrying provenance that Beadloom wrote them, which needs provenance the graph does not record today.
    **Tracker:** `beadloom-gv0z`.
    **Bead:** `beadloom-gv0z` (re-measured live on 2026-10-20 by BDL-083 S3d, `beadloom-d9te`)
    **measured_on:** 2026-10-20 9.0.0

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
    **Bead:** `beadloom-uz8x` (re-measured live on 2026-10-20 by BDL-083 S3d, `beadloom-d9te`)
    **measured_on:** 2026-10-20 9.0.0

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
    **Bead:** `beadloom-weh1` (re-measured live on 2026-10-20 by BDL-083 S3f, `beadloom-3jlv`)
    **measured_on:** 2026-10-20 9.0.0

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
    **Bead:** `beadloom-ajyq` (re-measured live on 2026-10-20 by BDL-083 S3b, `beadloom-wvcc`)
    **measured_on:** 2026-10-20 9.0.0

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
    **Bead:** `beadloom-aiha` (re-measured live on 2026-10-20 by BDL-083 S3b, `beadloom-wvcc`)
    **measured_on:** 2026-10-20 9.0.0

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
    **Bead:** `beadloom-ik18` (re-measured live on 2026-10-20 by BDL-083 S3b, `beadloom-wvcc`)
    **measured_on:** 2026-10-20 9.0.0

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
    **Bead:** `beadloom-y3qu` (re-measured live on 2026-10-20 by BDL-083 S3b, `beadloom-wvcc`)
    **measured_on:** 2026-10-20 9.0.0

203. [2026-08-26] [LOW] Two stated behaviours in `doc_area` survive mutation — the rationale is documented and observed by nothing

    **Severity:** low (both are supporting decisions, not headline behaviour)
    **Context:** the `.6` reviewer ran the mutation testing `.5` did not: 8 mutations, 6 killed, 2 survived the full 7257-test suite.

    ```
    _area_depth tie-break flipped shallower -> deeper   7257 passed, 0 behavioural kills
    _normalise  hyphen/underscore folding removed       7257 passed, 0 behavioural kills
    ```

    Both docstrings state a rationale; no test observes it. Folding is not load-bearing on THIS repository because the rule learns a per-area vocabulary — which is exactly the TRUE HERE IS NOT TRUE shape: it will be load-bearing on the first adopter whose directories are spelled the other way.

    The reviewer's judgement, which is worth keeping: the missing mutation run would have added precisely these — *"the supporting decisions nobody thought to neuter because they are not the headline. Low yield, real, and cheap enough that it should become routine rather than a bead-by-bead choice."*
    **Bead:** `beadloom-oqo4` (re-measured live on 2026-10-20 by BDL-083 S3b, `beadloom-wvcc`)
    **measured_on:** 2026-10-20 9.0.0

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
    **Bead:** `beadloom-sgxz` (re-measured live on 2026-10-20 by BDL-083 S3b, `beadloom-wvcc`)
    **measured_on:** 2026-10-20 9.0.0

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
    **Bead:** `beadloom-ksub` (re-measured live on 2026-10-20 by BDL-083 S3c, `beadloom-al1i`)
    **measured_on:** 2026-10-20 9.0.0

200. [2026-08-26] [LOW] An inert `docs_audit.ignore` triple is neither computed nor reported — the check exists one layer up and was never built here

    **Severity:** low (nothing is currently inert; the defect is that nothing would notice if something were)
    **Context:** found by `beadloom-viaj.5` while testing the seams between this feature's beads.

    `.4` retired the `context-oracle` suppression **by hand** after the `framework_count` rename made it inert, and measured the inertness by hand (0 framework-family mentions over 58 documents). Nothing in the product would have told it. `config_sync._suppression_drifts` performs the equivalent check for a different suppression surface, so the pattern exists in the codebase — it was simply never applied to `docs_audit.ignore`.

    Current state, measured: 10 triples, 59 documents, 41 mentions, **all live**. So this is dormant, and the only reason it stayed dormant is that a person swept it manually this morning.

    This is `rule_liveness` applied to a suppression rather than a rule, and BDL-061 established the contract: *a rule, exclusion or glob that cannot match anything reports itself.* An `ignore` triple is an exclusion. It was left out of that sweep.
    **Bead:** `beadloom-jogg` (re-measured live on 2026-10-20 by BDL-083 S3b, `beadloom-wvcc`)
    **measured_on:** 2026-10-20 9.0.0

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
    **Bead:** `beadloom-i3d5` (re-measured live on 2026-10-20 by BDL-083 S3a, `beadloom-k6f1`)
    **measured_on:** 2026-10-20 9.0.0

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
    **Bead:** none — a Won't-fix candidate, put to the owner on 2026-10-20 (measured by BDL-083 S3a, `beadloom-k6f1`; PLAN.md, "S3 — rulings put to the owner")
    **measured_on:** 2026-10-20 9.0.0

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
    **Bead:** `beadloom-cdgn` (re-measured live on 2026-10-20 by BDL-083 S3c, `beadloom-al1i`)
    **measured_on:** 2026-10-20 9.0.0

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
    **Bead:** `beadloom-6nk6` (re-measured live on 2026-10-20 by BDL-083 S3b, `beadloom-wvcc`)
    **measured_on:** 2026-10-20 9.0.0

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
    **Bead:** none — a Won't-fix candidate, put to the owner on 2026-10-20 (measured by BDL-083 S3f, `beadloom-3jlv`; PLAN.md, "S3 — rulings put to the owner")
    **measured_on:** 2026-10-20 9.0.0

184. [2026-08-23] [MEDIUM] `config-check --project <dir>` crashes with a raw sqlite error on a project that has no index — exit 1 with nothing on either stream

    **Severity:** medium (it is indistinguishable from a verdict, and it was silently corrupting a measurement while nobody noticed)
    **Command:** `beadloom config-check --project <dir>`
    **Context:** found by the `.57` agent while measuring a control case, and it is the manner of finding that matters: the agent was using a never-adopted project as a control to prove a fix did not over-report. The control's exit 1 was read as meaningful until it turned out to be a crash.
    **Issue:** on a project with no `.beadloom/beadloom.db`, the command dies with `sqlite3.OperationalError("unable to open database file")` and exits 1, printing nothing on stdout or stderr. A caller — a gate action, a script, an agent — sees a non-zero exit and no output, which is exactly the shape of a failing check.
    **Why it is worse than an ugly traceback:** an uninitialised project is a *legitimate, expected* state for this command, since `config-check` is one of the first things anyone runs. So the most likely first-contact experience with the command is a silent failure that reads as "your config is wrong" rather than "there is no index yet, run `beadloom init`".
    **Expected:** an absent index is an answer, not an exception — say so and exit on a code that means it (this is `unverifiable is not clean` again, from the caller's side rather than the checker's). At minimum, never exit non-zero with both streams empty: a verdict nobody can read is not a verdict.
    **Related:** #175 (a rebuilt index has nothing to compare against), #174, #146 — the same family, and this is the entry point.
    **Bead:** `beadloom-leio` (re-measured live on 2026-10-20 by BDL-083 S3d, `beadloom-d9te`)
    **measured_on:** 2026-10-20 9.0.0

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
    **Bead:** `beadloom-i7m2` (re-measured live on 2026-10-20 by BDL-083 S3b, `beadloom-wvcc`)
    **measured_on:** 2026-10-20 9.0.0

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
    **Bead:** none — a Won't-fix candidate, put to the owner on 2026-10-20 (measured by BDL-083 S3a, `beadloom-k6f1`; PLAN.md, "S3 — rulings put to the owner")
    **measured_on:** 2026-10-20 9.0.0

176. [2026-08-23] [LOW] An incremental `reindex` prints `Imports: 0` and `Rules: 0` on the run that refreshed them

    **Severity:** low (cosmetic, but it is a zero printed by the command whose honesty BDL-061 S2 restored)
    **Command:** `beadloom reindex`
    **Context:** found by the S2 review while watching the incremental path catch an injected boundary violation — the run genuinely re-extracted imports, and its summary said it had indexed none.
    **Issue:** `ReindexResult.imports_indexed` and `.rules_loaded` are only populated on the `--full` path (`application/reindex/full.py`), while the incremental path calls `reindex_file_imports()` without recording a count, so the CLI's `Imports:` / `Rules:` lines print the dataclass defaults. A reader cannot distinguish "no imports were touched" from "imports were refreshed and nobody counted them".
    **Expected:** either backfill both counters to the live DB totals on the incremental path — the fix #112 already applied to `Symbols:` for exactly this reason — or label them as per-run deltas and omit them when the path does not compute one. Same shape as #148: a number whose meaning depends on which path produced it.
    **Related:** #112 (closed, BDL-047 — the identical defect on `Symbols:`), #148.
    **Bead:** `beadloom-e5g0` (re-measured live on 2026-10-20 by BDL-083 S3d, `beadloom-d9te`)
    **measured_on:** 2026-10-20 9.0.0

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
    **Bead:** none — a Won't-fix candidate, put to the owner on 2026-10-20 (measured by BDL-083 S3f, `beadloom-3jlv`; PLAN.md, "S3 — rulings put to the owner")
    **measured_on:** 2026-10-20 9.0.0

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
    **Bead:** `beadloom-7qo4` (re-measured live on 2026-10-20 by BDL-083 S3b, `beadloom-wvcc`)
    **measured_on:** 2026-10-20 9.0.0

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
    **Bead:** `beadloom-4wps` (re-measured live on 2026-10-20 by BDL-083 S3b, `beadloom-wvcc`)
    **measured_on:** 2026-10-20 9.0.0

163. [2026-08-20] [MEDIUM] `sync-update` can re-attest a doc nobody read — re-baselining silences `sync-check` without evidence

    **Severity:** medium (the freshness guarantee quietly weakens to "the hashes were reset", which is not what a green sync-check is read to mean)
    **Command:** `beadloom sync-update <ref>`, `beadloom sync-check`
    **Context:** `sync-check` compares hashes and `sync-update` resets them; nothing records whether the DOC was read or revised. During BDL-060 S4 this happened repeatedly — a dev change re-stales a domain doc, the baseline is reset to keep the gate moving, and the prose drifts silently. Concretely: the `vitepress-site` guide still described the landscape as "an interactive Mermaid diagram" and called Cytoscape "a follow-up" **after** the slice that shipped Cytoscape, while `sync-check` read 0 stale throughout.
    **Two distinct holes, needing different answers:**
    - **Prose with no pair.** A guide anchored to no symbol can never go stale. The only signal today is the opt-in, coarse `reference`/`watches` mechanism (BDL-057). Either make `watches` discoverable (warn when a `docs/guides/*.md` declares none) or let a doc watch a NODE rather than a symbol surface.
    - **Blind re-baseline.** Re-attesting without touching the doc is *sometimes* legitimate (an internal rename the doc never mentions), so it cannot be forbidden. Instead RECORD it: per pair, count re-baselines where the code symbols changed and the doc file did not. A high count means "attested but never revised" — a staleness SUSPICION the gate can surface as advisory. That is honest: it does not claim the prose is wrong, it says nobody has looked while the code moved underneath.
    **Related:** #161 catches a phantom symbol name; this catches prose that stopped being true while every number in it stayed correct.
    > Tracked as a bead (P2).
    **Bead:** `beadloom-9glj` (re-measured live on 2026-10-20 by BDL-083 S3b, `beadloom-wvcc`)
    **measured_on:** 2026-10-20 9.0.0

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
    **Bead:** `beadloom-uxqc` (re-measured live on 2026-10-20 by BDL-083 S3d, `beadloom-d9te`)
    **measured_on:** 2026-10-20 9.0.0

161. [2026-08-20] [MEDIUM] `docs audit` checks numeric facts but never checks that a documented identifier still exists

    **Severity:** medium (documentation can name a function the code no longer has, and every gate stays green — the failure mode this project exists to catch, in the gate's own blind spot)
    **Command:** `beadloom docs audit`, `beadloom ci`
    **Context:** While narrowing the `surface_registry` port from CLI+MCP to CLI-only, two functions were deleted from the code and left in two documents. Both files passed `beadloom ci` 6/6 on the release branch. `sync-check` did not object because it compares hashes and the pair had been re-baselined after the edit; `docs audit` did not object because it verifies numeric claims (version, node/edge counts, CLI-command and MCP-tool counts) and has no notion of a named symbol. They were found by a ten-line ad-hoc script written for an unrelated reason.
    **Issue:** the audit answers "is this number still true?" but not "does this name still exist?". The second question is cheaper to answer and catches a strictly worse class of error: a stale number misleads, a phantom symbol sends the reader — or an agent — after something that is not there.
    **Expected:** extend `docs audit` with an identifier check — for each backticked `name(` in a tracked doc, verify a matching `def`/`class` (or a documented external API) exists in the indexed symbols, reporting the doc, the name and the node. Care is needed for legitimate references to framework APIs (`pop_screen` from Textual) and to prose that mentions a removed symbol deliberately, so the check likely wants the same `docs_audit.ignore` escape hatch, with a named reason.
    **Measured:** an ad-hoc version of this check over the release branch's 13 changed docs produced exactly one hit, and it was a correct reference to a framework API — so the false-positive rate on a real tree looks workable.
    **Bead:** `beadloom-431c` (re-measured live on 2026-10-20 by BDL-083 S3b, `beadloom-wvcc`)
    **measured_on:** 2026-10-20 9.0.0

160. [2026-08-19] [HIGH] 🔴 AsyncAPI ingestion is documented as a capability but wired to nothing — `extract_payload_body` is reachable from no code path

    **Severity:** high (the docs promise an integration the product does not perform; a user pointing Beadloom at an AsyncAPI-described project gets nothing, silently)
    **Command:** `beadloom reindex` / `beadloom federate` on a project described with AsyncAPI
    **Context:** Found while dogfooding the BDL-060 S4 architecture map — the `asyncapi` node showed no dependency in EITHER direction. Verified independently of the graph: `grep` finds `src/beadloom/graph/asyncapi.py` referenced by **zero** other files under `src/`; only its two test files import it.
    **Issue:** the claim is explicit — `docs/domains/graph/features/federation/SPEC.md` says *"teams on AsyncAPI ingest the payload schema via the source-only `asyncapi.extract_payload_body` adapter"*, and the component DOC opens with *"Teams that already describe their AMQP messages with an AsyncAPI document…"*. What is true: the function works and is well tested (`test_asyncapi_ingest.py`, `test_asyncapi_fidelity.py`). What is false: that anything *ingests*. The loader never reads an AsyncAPI document, and nothing calls the adapter.
    **Why it survived:** this is the house failure mode one level up — not a check reporting success for work it did not do, but DOCUMENTATION claiming a capability the product does not deliver. It passed a dev bead, a test bead, a review bead, a tech-writer bead and a green gate, because every one of them verified the FUNCTION and none asked whether anything calls it.
    **Expected:** either wire it (the loader reads a configured AsyncAPI document per service and feeds `extract_payload_body` into the contract body, closing the claim) or correct the claim to "unwired building block" until that ships. The first is the real close — otherwise BDL-060 S3 delivers less than its SPEC states.
    **Related:** worth a machine check of its own — a **code island**: a node with no first-party dependency in either direction whose files nothing references. `doctor`'s `isolated_nodes` does not catch it, because `part_of` makes the node look connected. Measured here, `asyncapi` is the only true island (`ai_agents`/`ai-techwriter` are reached by subprocess, `vitepress-site` is not Python).
    > Tracked as bead `beadloom-g79p`. **DEFERRED by owner 2026-08-20** (P1→P2) — real but outranked; the adapter is inert, so nothing regresses while it waits. The implementation plan is recorded in `ROADMAP.md` under P1 → *"⏸ Deferred (planned, not scheduled) — wire the AsyncAPI ingestion path"* (`body_from:` declaration → loader resolution into the same body model → no silent no-op → determinism → end-to-end golden + an island guard → docs). What is NOT deferred is the honesty of the claim: if this slips much further, the federation SPEC sentence should be downgraded to "unwired building block".
    **Bead:** `beadloom-g79p` (re-measured live on 2026-10-20 by BDL-083 S3e, `beadloom-8pzg`; the owner's ruling is asked in PLAN.md, "S3 — rulings put to the owner")
    **measured_on:** 2026-10-20 9.0.0

158. [2026-08-19] [MEDIUM] No signal for a bounded context that is too large by SUBTREE — `max_symbols` now measures a node's own code only

    **Severity:** medium (a governance signal that used to exist is now unmeasured; recorded openly rather than papered over with a threshold)
    **Command:** `beadloom lint --strict`
    **Context:** Fixing #144 changed what `max_symbols` means: it counts the symbols a node OWNS (nested nodes excluded) instead of everything under its path prefix. That is what makes the rule's own remedy work — carving a subpackage out now genuinely relieves the parent. But the OLD metric also carried a second, legitimate signal: "this bounded context has grown too large overall". A domain decomposed into many features owns very little and will never trip the rule, however large its subtree becomes. Measured on Beadloom itself after the fix: `context-oracle`, `ai_agents` and `infrastructure` own **0** symbols each (every file belongs to a component/feature node) while their subtrees hold 99, 108 and 63.
    **Issue:** two different questions were riding on one number — "is this node's own code too big?" (own count, the re-scoping prompt) and "is this bounded context too big?" (subtree count, the split-the-domain prompt). Only the first is now expressible.
    **Expected:** a separate cardinality key for the second question rather than overloading `max_symbols` — e.g. `max_subtree_symbols` (all symbols under the node's source, the old semantics) and/or `max_children` (how many nodes are `part_of` it). Keeping them distinct is the point: a threshold that silently answers whichever question happens to be convenient is how a metric stops meaning anything.
    > Deliberately NOT folded into the `domain-size-limit` threshold when it was recalibrated 290 → 180.
    **Bead:** `beadloom-1d70` (re-measured live on 2026-10-20 by BDL-083 S3c, `beadloom-al1i`)
    **measured_on:** 2026-10-20 9.0.0

149. [2026-08-05] [LOW] `graph --format c4 --level component --scope <ref>` on a node with no internals prints a single useless `C4Container` instead of saying so

    **Severity:** low (silently useless output rather than an error — reads as a rendered diagram)
    **Command:** `beadloom graph --format c4 --level component --scope <ref_id>`
    **Context:** Dogfood: an integration offers a "detailed diagram of one container" view and passes whatever node the user names.
    **Issue:** when `<ref>` is a leaf (no nested nodes), the command exits 0 and emits a valid-but-empty C4 diagram — one `C4Container` block, no internals. Rendered, it is a single box. There is no signal distinguishing "this node has no internals" from "here are its internals", so a caller cannot tell the user the truth without pre-checking the graph itself.
    **Expected:** exit non-zero (or print an explicit note) when `--scope` resolves to a node with no contained nodes, so the caller can fall back to a neighbourhood view and say why.
    **Workaround:** downstream detects the degenerate output and falls back to the node's neighbourhood diagram plus an honest note to the reader.
    **Bead:** `beadloom-qxp2` (re-measured live on 2026-10-20 by BDL-083 S3e, `beadloom-8pzg`)
    **measured_on:** 2026-10-20 9.0.0

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
    **Bead:** `beadloom-i8k1` (re-measured live on 2026-10-20 by BDL-083 S3c, `beadloom-al1i`)
    **measured_on:** 2026-10-20 9.0.0

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
    **Bead:** `beadloom-tlzl` (re-measured live on 2026-10-20 by BDL-083 S3c, `beadloom-al1i`)
    **measured_on:** 2026-10-20 9.0.0

145. [2026-08-03] [MEDIUM] `ctx <ref> --json` returns the REPO-WIDE `code_symbols` array, not the focused node's — an agent sizing/inspecting a node from its own context bundle reads every other package's symbols

    **Severity:** medium (agent-facing correctness; silently wrong data, not an error)
    **Command:** `beadloom ctx <ref-id> --json`
    **Context:** Dogfood on a downstream DDD project. An orchestrator wanted to verify a `max_symbols` rule independently ("how big is this node really?") and did the obvious thing: `beadloom ctx <node> --json` → count `code_symbols`. The node held **172** symbols; the bundle returned **1342** — every symbol in the repository, spanning all 12 top-level packages, while `focus.ref_id` correctly named the single node.
    **Issue:** The JSON bundle's `code_symbols` is not scoped to the focused subgraph. `focus`/`graph` are node-scoped, so the payload *looks* node-scoped — the mismatch is invisible without cross-checking against the DB. Any consumer that treats the bundle as "this node's context" (an agent budgeting tokens, counting symbols, or reasoning about what the node contains) is silently wrong, and wrong in the direction of "everything looks huge and entangled". Related to #95, which describes the same query as a **performance** problem and states the result is "then filter[ed] to the subgraph in Python" — in the `--json` output that filtering is not observable, so either it does not happen on this path or it is applied to other fields only.
    **Expected:** `code_symbols` scoped to the focused node's `source` (plus explicitly-included neighbours), or — if repo-wide is deliberate for context-priming — a distinct field name (`repo_symbols`) and a `focus_symbols` counterpart, so consumers cannot mistake one for the other.
    **Workaround:** Query the index directly: `SELECT COUNT(*) FROM code_symbols WHERE file_path LIKE '<source>%'`.
    **Bead:** `beadloom-pprp` (re-measured live on 2026-10-20 by BDL-083 S3d, `beadloom-d9te`)
    **measured_on:** 2026-10-20 9.0.0

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
    **Bead:** `beadloom-7qo4` (re-measured live on 2026-10-20 by BDL-083 S3b, `beadloom-wvcc`)
    **measured_on:** 2026-10-20 9.0.0

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
    **Bead:** `beadloom-uh5u` (re-measured live on 2026-10-20 by BDL-083 S3b, `beadloom-wvcc`)
    **measured_on:** 2026-10-20 9.0.0

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
    **Bead:** `beadloom-4wps` (re-measured live on 2026-10-20 by BDL-083 S3b, `beadloom-wvcc`)
    **measured_on:** 2026-10-20 9.0.0

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
    **Bead:** `beadloom-ay6b` (re-measured live on 2026-10-20 by BDL-083 S3d, `beadloom-d9te`)
    **measured_on:** 2026-10-20 9.0.0

73. [2026-03-10] [LOW] `beadloom doctor` reports "Version drift" and "Package drift" by checking `.claude/CLAUDE.md`

    **Severity:** low
    **Command:** `beadloom doctor`
    **Context:** After bootstrapping on an external project, the existing `.claude/CLAUDE.md` contained content from a previous project (Beadloom itself) with `Version: 1.9.0` and DDD package references (`context_oracle/`, `doc_sync/`, etc.).
    **Issue:** `doctor` checks `.claude/CLAUDE.md` for version and package claims, finding `CLAUDE.md claims 1.9.0, actual is 1.7.0` and `Package drift: claimed but missing: context_oracle, doc_sync, graph, infrastructure, onboarding, services, tui`. These are false positives — CLAUDE.md is a user-maintained file that may describe the project in custom terms, not necessarily matching Beadloom's internal structure.
    **Expected:** `doctor` should validate `.beadloom/AGENTS.md` (which Beadloom generates and controls) rather than `.claude/CLAUDE.md` (which is user-authored and project-specific). If CLAUDE.md is checked at all, it should be limited to `<!-- beadloom:auto-start -->` / `<!-- beadloom:auto-end -->` sections.
    **Workaround:** Ignore the warnings; they're false positives caused by stale CLAUDE.md content from another project.
    **Bead:** none — a Won't-fix candidate, put to the owner on 2026-10-20 (measured by BDL-083 S3d, `beadloom-d9te`; PLAN.md, "S3 — rulings put to the owner")
    **measured_on:** 2026-10-20 9.0.0

---

## Improvements

> Proposals, not defects. The twelve proposals from the first field tests of March 2026 moved
> to the archive on 2026-10-05, unmeasured since they were written.

### Index

| No | Date | Severity | What | Bead |
|---|---|---|---|---|
| 156 | 2026-08-19 | medium | Context rot explains WHY a long instruction file stops being followed | `beadloom-ba9w.8` |
| 155 | 2026-08-19 | high | Multi-agent failure modes and long-running-harness patterns Beadloom can act on | `beadloom-wvf3` |
| 154 | 2026-08-19 | high | Oversight patterns a controlled multi-agent flow should adopt | `beadloom-wvf3`, `beadloom-vom5` |
| 96 | 2026-05-28 | medium | Test suite is volume-heavy but brittle: implementation-coupled and rarely parametrized | `beadloom-slxk` |

### Entries

156. [2026-08-19] [MEDIUM] Context rot explains WHY a long instruction file stops being followed — plus selective escalation as a second graph-derived feature

    **Reference added 2026-10-11:** *Evaluating AGENTS.md* (arXiv 2602.11988) measures that auto-generated repository-level context files can lower task success and raise cost — the agent follows the extra instructions without finding the code faster. A warning against "more instructions → better agent", the premise slice H (`beadloom-ba9w.8`) is written against; not a result about Beadloom's own mechanism.

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
    **Bead:** `beadloom-ba9w.8` (re-measured live on 2026-10-20 by BDL-083 S3f, `beadloom-3jlv`)
    **measured_on:** 2026-10-20 9.0.0

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
    **Bead:** `beadloom-wvf3` (re-measured live on 2026-10-20 by BDL-083 S3f, `beadloom-3jlv`; archiving the note as research with the carried items is put to the owner (PLAN.md, "S3 — rulings put to the owner"))
    **measured_on:** 2026-10-20 9.0.0

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
    **Bead:** `beadloom-wvf3`, `beadloom-vom5` (re-measured live on 2026-10-20 by BDL-083 S3f, `beadloom-3jlv`; archiving the note as research with the carried items is put to the owner (PLAN.md, "S3 — rulings put to the owner"))
    **measured_on:** 2026-10-20 9.0.0

96. [2026-05-28] [MEDIUM] Test suite is volume-heavy but brittle: implementation-coupled and rarely parametrized

    **Severity:** medium
    **Context:** Self-audit (2026-05-28). Test:source ratio ≈1.9:1 (~48K test LOC / ~25K src LOC), 2576 test functions.
    **Issue:** The volume reflects breadth, not depth: only ~4 uses of `@pytest.mark.parametrize` (test bodies are copy-pasted instead of data-driven), and ~193 accesses to private attributes (`._foo`) in tests — assertions welded to current internals that will break on refactor. `test_tui.py` alone is ~5989 LOC for a low-value surface. This brittleness will make the #91 architecture refactor far more painful than necessary.
    **Expected:** Before the #91 refactor: (a) convert copy-pasted test groups to `parametrize`; (b) replace private-attribute assertions with behavior / public-API assertions; (c) reassess whether the TUI warrants ~6K LOC of tests. Treat coverage as a means, not the `fail_under=80` number as the goal.
    **Bead:** `beadloom-slxk` (re-measured live on 2026-10-20 by BDL-083 S3f, `beadloom-3jlv`)
    **measured_on:** 2026-10-20 9.0.0

---

## Closed numbers that must stay written

> One line per number that a check still resolves here: numbers claimed in the ledger
> (262 and higher), and numbers the shared media of `beadloom waves` cite as evidence. The
> text of each is in `archive/BDL-UX-Issues-closed.md`.

354. ~~[2026-10-19] [MEDIUM] a merge-slot `release` made after `git push` lands in no merged commit, so `master` carries the slot held by a closed bead and the next clone's `acquire` is refused~~ **CLOSED** (BDL-083 S3, verified 2026-10-20)
352. ~~[2026-10-19] [MEDIUM] the TUI lint panel counts warnings by the severity `warning` while the engine emits `warn`, so every warn finding shows as info and the panel's warning count reads 0~~ **CLOSED** (duplicate of #292, BDL-083 S3, 2026-10-20)
335. ~~[2026-10-18] [MEDIUM] `clean-room --carry` refuses the whole room for a path the tree no longer holds, carries no deletions or renames, and copies a shared file whole with a neighbour bead's edits in it~~ **CLOSED** (BDL-083 S3, verified 2026-10-20)
334. ~~[2026-10-18] [HIGH] `config-check` is red in a clean room and in a `git worktree` (`.claude/CLAUDE.md stale`, `config-drift`) and green in the main checkout of the same files, and the verdict does not say what it compared~~ **CLOSED** (BDL-083 S3, verified 2026-10-20)
333. ~~[2026-10-18] [MEDIUM] `clean-room` builds no environment for a Python project under `backend/` and its "Measure in the room" hint prints Beadloom's own layout (`PYTHONPATH=<room>/src ... -m pytest <room>/tests`, `import beadloom`)~~ **CLOSED** (BDL-083 S3, verified 2026-10-20)
332. ~~[2026-10-18] [HIGH] `rooms` reads the root `pyproject.toml` and `.github/workflows` only: a monorepo with `backend/pyproject.toml` and `.gitlab-ci.yml` declares 0 rooms, and `ci` prints `0 of 0 declared room(s)` naming no leg~~ **CLOSED** (BDL-083 S3, verified 2026-10-20)
331. ~~[2026-10-18] [MEDIUM] `issue-number check` exits 0 on a declared but missing log (`no leg ran`) while the Gate's `issue-log` step on the same tree is red~~ **CLOSED** (BDL-083 S3, verified 2026-10-20)
330. ~~[2026-10-18] [HIGH] `scope-check` judges against trunk, so a branch cut from an unmerged feature branch gets the parent's whole diff: 304 `outside-the-declared-axes` warnings about files the work item never touched~~ **CLOSED** (BDL-083 S3, verified 2026-10-20)
329. ~~[2026-10-18] [HIGH] `ci` "owned by" attributes a neighbour bead's findings: 36 findings owned by a bead that touched none of the files, twice in one week~~ **CLOSED** (BDL-083 S3, verified 2026-10-20)
328. ~~[2026-10-18] [HIGH] `rule_liveness` calls a live `forbid_import` rule dead: `to: os/**` "matches 0 of 274 import paths, cannot fire" while `import os` fires it — and two reviews concluded the boundary was unchecked~~ **CLOSED** (BDL-083 S3, verified 2026-10-20)
327. ~~[2026-10-18] [MEDIUM] the pre-commit ruff leg hides stderr and prints "ruff lint violations" when ruff is not installed, and runs from the root ignoring a `pyproject.toml` in a subfolder~~ **CLOSED** (BDL-083 S3, verified 2026-10-20)
326. ~~[2026-10-18] [HIGH] the pre-push Gate hook exits 0 silently when `beadloom` is not on PATH, and pre-commit never runs `beadloom lint`: an FSD layer violation (widgets → app) reached the remote with both hooks installed~~ **CLOSED** (BDL-083 S3, verified 2026-10-20)
322. ~~[2026-10-11] [LOW] the README pair says 15 authoring keys (the loader has 17), `ctx` is said to return the rules in force, `why` what breaks, and `architecture.md` claims `<20ms` three times unmeasured~~ **CLOSED** (BDL-083 S3, verified 2026-10-20)
318. ~~[2026-10-11] [MEDIUM] the Gate has no per-step exception boundary and no 'checker error' status, so 'never short-circuit' holds for FAIL results and not for exceptions~~ **CLOSED** (BDL-083 S3, verified 2026-10-20)
315. ~~[2026-10-10] [MEDIUM] `sync-update <ref> --yes --pair <doc> --code <file>` clears pairs it was not asked to attest~~ **CLOSED** (BDL-083 S3, verified 2026-10-20)
313. ~~[2026-10-10] [MEDIUM] `init --project .` names the root service `''` (`Path('.').name`), so on a JVM or Swift project `init` exits 1 with `domain-needs-parent`~~ **CLOSED** (BDL-080, PR #98)
311. ~~[2026-10-10] [MEDIUM] `clean-room` installs with `uv pip install -e`, ignoring `uv.lock`, so a room resolves dependencies CI never sees~~ **CLOSED** (BDL-083 S3, verified 2026-10-20)
307. ~~[2026-10-07] [MEDIUM] the portal's Source link is a permalink to the built commit, so a local build from an unpushed commit links to a 404 on every node~~ **CLOSED** (BDL-080, PR #98)
306. ~~[2026-10-07] [MEDIUM] a box's card says `Debt 0` from the box's own score while its activity rolls up from its parts — two populations on one card, unnamed~~ **CLOSED** (BDL-080, PR #98)
305. ~~[2026-10-07] [MEDIUM] `Rule findings: none` on a node card is indistinguishable from "lint never ran", and the 36 findings bound to no node are shown nowhere on the portal~~ **CLOSED** (BDL-080, PR #98)
304. ~~[2026-09-29] [HIGH] a replacement for a heuristic was proven "no worse than main" one ecosystem at a time, so the review found the same regression three times~~ **CLOSED**
303. ~~[2026-09-19] [HIGH] the nightly mutation job is killed by its runner at 93-100 minutes, so the declared scope has had no aggregate score since 2026-09-09 even now that the run works~~ **CLOSED**
300. ~~[2026-09-13] [HIGH] `scope-check` never runs in CI: Actions checks a pull request out on a detached HEAD, so no branch names a work item and the step skips on every pull request~~ **CLOSED** (BDL-083 S3, verified 2026-10-20)
298. ~~[2026-09-13] [MEDIUM] a vacuity guard added in BDL-070 reads the live index while other tests in the same run rebuild it, and saw 57 edges of 365~~ **CLOSED**
296. ~~[2026-09-13] [MEDIUM] a layer rule reports an error and is counted inert in the same run, because liveness still reads own tags~~ **CLOSED**
293. ~~[2026-09-12] [MEDIUM] running the suite with `--cov` corrupts the project's own index, and 18 tests then fail with `database disk image is malformed`~~ **CLOSED** (BDL-083 S3, verified 2026-10-20)
290. ~~[2026-09-12] [MEDIUM] `beadloom reindex` is not idempotent across a fresh and a carried-forward index, and the layer rule's new population statement inherits the difference~~ **CLOSED** (BDL-083 S3, verified 2026-10-20)
289. ~~[2026-09-12] [HIGH] a self-scanning guard test reads mutmut's own mutated copy of the package, so the nightly mutation run reaches a verdict on 0 of 6544 mutants~~ **CLOSED**
286. ~~[2026-09-12] [MEDIUM] a review launch prompt can defeat the withholding it is meant to preserve, and nothing counts it~~ **CLOSED** (BDL-083 S3, verified 2026-10-20)
285. ~~[2026-09-11] [WITHDRAWN] a bead's scope appended by the documented command is silently ignored when its description already carries a `refs:` line~~ **CLOSED**
284. ~~[2026-09-11] [MEDIUM] an axis row is ruled by the axis a node first surfaced under, and three nodes ruled out as blast radius turned out to be the sites the fix had to reach~~ **CLOSED**
283. ~~[2026-09-11] [MEDIUM] `beadloom waves --parent` compares only READY beads, so it reports a clean wave for a bead that conflicts with one already running~~ **CLOSED**
282. ~~[2026-09-10] [CRITICAL] a virgin `init` leaves the Gate RED on the documents it just wrote, and the remediation the error names does not clear it~~ **CLOSED**
281. ~~[2026-09-10] [MEDIUM] the release version is stated in NINE places, and no command names that population — three instruments each check a disjoint part of it and none knows the others exist~~ **CLOSED**
276. ~~[2026-09-09] [MEDIUM] the ownership block's GitHub surface drops the caveat that says `unowned` is not a proof~~ **CLOSED** (BDL-083 S3, verified 2026-10-20)
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
#51 #52 #53 #54 #55 #56 #57 #58 #59 #60 #61 #62 #63 #64 #65 #66 #67 #68 #69 #70 #71 #72 #74 #75
#76 #77 #78 #79 #80 #81 #82 #83 #84 #85 #86 #87 #88 #89 #90 #91 #92 #93 #94 #97 #98 #99 #100
#101 #102 #103 #104 #105 #106 #107 #108 #109 #110 #111 #112 #113 #114 #115 #116 #117 #119 #120
#121 #122 #123 #124 #125 #126 #127 #128 #129 #130 #131 #132 #135 #136 #137 #139 #141 #142 #143
#144 #146 #150 #151 #152 #153 #157 #159 #164 #169 #170 #172 #173 #174 #175 #177 #180 #183 #185
#186 #188 #189 #191 #192 #193 #195 #196 #204 #207 #211 #212 #213 #214 #216 #226 #227 #228 #231
#233 #234 #236 #238 #239 #240 #241 #243 #244 #245 #247 #248 #249 #250 #251 #252 #253 #254 #255
#256 #258 #259 #288
