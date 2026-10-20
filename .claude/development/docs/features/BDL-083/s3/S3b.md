# S3b — the doc-sync, docs-audit, doc-shape and README-pair entries, re-measured

- **Date:** 2026-10-20
- **Bead:** `beadloom-wvcc`
- **Version:** Beadloom 9.0.0 as S2 ships it: a git worktree of `features/BDL-083` at
  `cdaf3f78428061e51479723f59d666d952bf774e`. `git diff --quiet 41245dc7 cdaf3f78 -- src
  pyproject.toml uv.lock docs tests .beadloom/_graph .beadloom/config.yml README.md
  README.ru.md` exits 0, so the code, the tests and the documents measured are those of `main`
  at `41245dc7`. The one difference in `.beadloom/` is the S3 wave override in `flow.yml`.
- **Machine:** macOS 27.0 (Darwin 27.0.0), arm64, CPython 3.12.12. The worktree's environment
  is `uv sync --frozen --all-extras`: plain `uv sync --frozen` installs no TypeScript parser and
  no pytest, and the monorepo fixture's frontend and #203's test run need both. bd 1.0.4.
- **Index:** the worktree's own, built by `beadloom reindex` inside it, and one index per
  scratch project. The main checkout's index was not read or written.
- **Projects:** this repository (the worktree); one copy of the monorepo fixture
  `tests/fixtures/monorepo` with a fresh `git init`, driven through successive committed
  states; a throwaway Python project with a hand-written coarse graph for #138. Every probe
  edit in the worktree was reverted, and the worktree's tree was clean after each.
- **Room:** one room, this machine. No Linux leg and no other interpreter was entered. None of
  the twenty-six entries is about the platform, and that is a reading of the code, not a
  measurement on another leg.

### #349

- **Command:** `beadloom sync-check`, `beadloom sync-update --pair`
- **Where:** the monorepo fixture copy. One line appended to
  `frontend/src/widgets/kpi-panel/ui/KpiPanel.spec.ts`, then `reindex`.
- **Printed:**
  ```
  [stale] widgets-kpi-panel: frontend/widgets-kpi-panel.md <-> .../ui/KpiPanel.spec.ts (hash_changed)
  $ beadloom sync-update widgets-kpi-panel --yes --pair frontend/widgets-kpi-panel.md
  Re-baselined widgets-kpi-panel: attested 3 pair(s).
  ```
  One pair was stale, three were attested, and none of the three is named. `--code` narrows
  to the one file (see #315), but the spec file still pairs with the node's document as code.
- **Outcome:** live.
- **Evidence:** On 2026-10-20, on Beadloom 9.0.0 (`cdaf3f78`, code identical to `main` at
  `41245dc7`), a one-line edit of a spec file beside the code on the monorepo fixture made the
  node's document `stale (hash_changed)`, and `sync-update --pair` attested 3 pairs without
  naming them.
- **Bead:** none exists (`bd list --all --limit 0`, 1330 rows, no title carries `#349`).
  Proposed: `[BDL-UX #349] a spec file beside the code does not pair with the node's document
  as code, and sync-update --pair names the pairs it attests`.

### #348

- **Command:** `beadloom reindex && beadloom sync-check`, `beadloom sync-update --yes --pair`,
  `beadloom reindex --full`
- **Where:** the monorepo fixture copy. A new `frontend/src/entities/metric/model/metric.spec.ts`
  and a line added to the node's document, then incremental `reindex`.
- **Printed:**
  ```
  [stale] entities-metric: ... <-> frontend/src/entities/metric/index.ts (untracked: metric.spec.ts)
  [stale] entities-metric: ... <-> .../model/metric.ts (untracked: metric.spec.ts)
  --report hint: pair metric.spec.ts with frontend/entities-metric.md: annotate each file with
    `# beadloom:<kind>=entities-metric`, or add `<!-- beadloom:track=<path> -->` ...
  $ beadloom sync-update entities-metric --yes --pair frontend/entities-metric.md
  Still stale after this run: 2 pair(s) ... re-attesting cannot clear untracked_files
  $ beadloom reindex --full && beadloom sync-check      -> no stale pair
  ```
  The hint never names `reindex --full`, and it proposes a `#` comment for a TypeScript file.
- **Outcome:** live.
- **Evidence:** On 2026-10-20, on Beadloom 9.0.0 (`cdaf3f78`), a new spec file under a
  frontend node of the monorepo fixture read `untracked_files` after an incremental `reindex`,
  the hint named an annotation or a track marker, `sync-update --pair` left both pairs stale,
  and only `reindex --full` cleared them.
- **Bead:** none exists. Proposed: `[BDL-UX #348] incremental reindex opens the pair for a new
  file under a node's source, and the untracked_files hint names reindex --full first`.

### #347

- **Command:** `beadloom sync-check`
- **Where:** the monorepo fixture copy. A node `fh-auth` with `source:
  backend/src/file_history/auth.py`, the file annotated `component=fh-auth`, `part_of` the
  backend service. `backend/src/file_history/` is the source of the node `file-history`.
- **Printed:**
  ```
  [stale] file-history: backend/file-history.md <-> .../file_history/__init__.py (untracked: auth.py)
  [stale] file-history: backend/file-history.md <-> .../file_history/entries.py (untracked: auth.py)
  [ok] fh-auth: backend/fh-auth.md <-> backend/src/file_history/auth.py
  hint: pair auth.py with backend/file-history.md: annotate each file with
    `# beadloom:<kind>=file-history` ...
  ```
  `reindex --full` does not change it. The hint proposes re-annotating a file that already
  has its own node to the parent, which would take it from its owner.
- **Outcome:** live.
- **Evidence:** On 2026-10-20, on Beadloom 9.0.0 (`cdaf3f78`), a file that is the `source:`
  of its own node made both pairs of the enclosing directory's node `stale (untracked:
  auth.py)` on the monorepo fixture, and the hint named neither the owner nor `part_of`.
- **Bead:** none exists. Proposed: `[BDL-UX #347] a file owned by another node's source or
  annotation is not an untracked file of the directory's node, and details name the owner`.

### #346

- **Command:** `beadloom reindex && beadloom sync-check`, `beadloom sync-update <ref> --yes`
- **Where:** the monorepo fixture copy. The two `entities-metric` files annotated
  `// beadloom:component=entities-metric` and baselined; then a new exported function in
  `model/metric.ts` and a Specification section naming it in the document, one `reindex`, three
  `sync-check` runs. Without annotations the fixture records no symbol hash and the reason does
  not arise: a new symbol reads `hash_changed`, and the document edit clears it.
- **Printed:**
  ```
  == run 1, 2 and 3, identical
  [stale] entities-metric: ... <-> .../model/metric.ts (symbols_changed)
  [stale] entities-metric: ... <-> .../metric/index.ts (symbols_changed)
  [stale] entities-metric: ... <-> .../model/metric.spec.ts (symbols_changed)
  --report: Run `beadloom sync-update <ref_id>` to review and re-attest a pair stale on
    hash_changed, hash_changed_since_head, symbols_changed
  $ beadloom sync-update entities-metric --yes      -> attested 3 pair(s), none still stale
  ```
  `index.ts` and the spec did not change; they carry no file-level symbol hash, so they keep
  the node-level `symbols_changed` instead of `sibling_symbols_changed`. No output names the
  symbol `under`. The plain text output names no clearing action; `--report` does.
- **Outcome:** live.
- **Evidence:** On 2026-10-20, on Beadloom 9.0.0 (`cdaf3f78`), three pairs of an annotated
  node of the monorepo fixture stayed `stale (symbols_changed)` over three `sync-check` runs
  after the document named the new symbol, two of them about files that did not change; no
  output named the symbol, and `sync-update --yes` cleared them.
- **Bead:** none exists. Proposed: `[BDL-UX #346] symbols_changed names the symbols that moved
  and the clearing action in the plain output, and an unchanged file reads sibling, not stale`.

### #345

- **Command:** `beadloom docs quality`
- **Where:** the worktree (this repository). The entry was not re-measured on the adopter's
  side; this repository reproduces it.
- **Printed:**
  ```
  CONVENTION: PRD documents do not carry Acceptance Criteria (overall) (0/58) — no document is
  reported for it
  $ grep -rl '^## Acceptance Criteria (overall)' --include=PRD.md .claude/development | wc -l
        29
  ```
  The cause, read and then run: `doc_sync/doc_shape.py:174` builds
  `rf"\b{re.escape(required)}\b"`. The heading ends in `)`, so the closing `\b` needs a word
  character after it and can never match at the end of the heading;
  `re.search(r"\bAcceptance Criteria \(overall\)\b", "Acceptance Criteria (overall)")` is
  `None`. The finding names neither the heading pattern nor a file.
- **Outcome:** live.
- **Evidence:** On 2026-10-20, on Beadloom 9.0.0 (`cdaf3f78`), `docs quality` on this
  repository reported `Acceptance Criteria (overall)` carried by 0 of 58 PRDs while 29 PRDs
  carry the heading, because the word-boundary match cannot close after `)`.
- **Bead:** none exists. Proposed: `[BDL-UX #345] the required-section match accepts a heading
  that ends in punctuation, and section-not-in-use names the heading and the files it read`.

### #342

- **Command:** `beadloom sync-check`, `beadloom reindex`
- **Where:** the monorepo fixture copy. `# beadloom:component=fh-auth` added to
  `backend/src/file_history/entries.py`, a module inside `file-history`'s source, then
  `reindex --full`. `application/digest/sections.py` imports `file_history.entries`.
- **Printed:**
  ```
  [stale] fh-auth: backend/fh-auth.md <-> backend/src/file_history/entries.py (symbols_changed)
  [stale] file-history: backend/file-history.md <-> backend/src/file_history/entries.py (hash_changed)
  edges: application-digest|file-history|depends_on      (no edge to fh-auth)
  doctor: no finding about entries.py
  ```
- **Outcome:** live.
- **Evidence:** On 2026-10-20, on Beadloom 9.0.0 (`cdaf3f78`), a module annotated to one node
  inside another node's source directory paired with both nodes' documents on the monorepo
  fixture, the import edge to it landed on the directory's node, and `doctor` named neither.
- **Bead:** none exists. Proposed: `[BDL-UX #342] one owner per file — the annotation decides
  pairs and edges alike — and doctor names a file two nodes claim`.

### #322

- **Command:** `README.ru.md`, `README.md`, `docs/architecture.md`; `beadloom docs audit`
- **Where:** the worktree.
- **Printed:**
  ```
  README.ru.md:304  Правило объявляет ровно один из 17 ключей: ... `slice_public_api` и `slice_shape`.
  README.md:304     Each entry declares exactly one of 17 authoring keys: ...
  README.md:175     `ctx` returns a node's code symbols, documentation, tests and the freshness
                    of its documents, and its `--json` output adds the `deny` and `require` rules
  README.md:167     `beadloom why <node>` shows what an edit to it can reach.
  README.md:358     | `why REF_ID` | What depends on a node and what an edit to it can reach |
  grep '<20\|20 ms' docs/architecture.md README.md README.ru.md   -> nothing
  docs audit: authoring key count: 17 -- NOT VERIFIED: no scanner keywords are registered
  ```
  The four claims are corrected in both languages. The count is declared in
  `.beadloom/config.yml` (`extra_facts.authoring_key_count: 17`), and the audit cannot bind a
  sentence to it; that residue is the open bead `beadloom-ba9w.16`.
- **Outcome:** closed.
- **Evidence:** On 2026-10-20, on Beadloom 9.0.0 (`cdaf3f78`), both READMEs state 17 authoring
  keys including `slice_public_api` and `slice_shape`, `ctx` is described by what it returns,
  `why` by what an edit can reach, and no `<20ms` figure remains in `docs/architecture.md`;
  the unbound declared fact is carried by `beadloom-ba9w.16`.
- **Bead:** none for the entry; the residue is `beadloom-ba9w.16`.

### #315

- **Command:** `beadloom sync-update site-generation --yes --pair
  docs/domains/application/features/site-generation/SPEC.md --code .../moved_pages.py --code
  .../scaffold.py`
- **Where:** the worktree, with a probe line appended to `moved_pages.py`, `scaffold.py`,
  `node_pages.py` and `generate.py` and `reindex`, so four pairs of the SPEC were stale.
  Repeated on the monorepo fixture with two stale pairs.
- **Printed:**
  ```
  Error: site-generation has no doc pair named docs/domains/.../SPEC.md. Its doc paths are:
  domains/application/features/site-generation/SPEC.md.
  $ (the same, with --pair domains/application/features/site-generation/SPEC.md)
  Re-baselined site-generation: attested 2 pair(s).
    Left unclaimed: 37 pair(s) nobody read — their baseline stands.
  Still stale after this run: 2 pair(s) — the verdict on these did not move:
    ... <-> src/beadloom/application/site/generate.py (hash_changed) — not claimed by this run
    ... <-> src/beadloom/application/site/node_pages.py (hash_changed) — not claimed by this run
  ```
  The entry's own Command is refused as written: `--pair` takes the path relative to the docs
  root, and the error names it.
- **Outcome:** closed.
- **Evidence:** On 2026-10-20, on Beadloom 9.0.0 (`cdaf3f78`), `sync-update site-generation
  --yes --pair <SPEC> --code moved_pages.py --code scaffold.py` attested exactly 2 pairs and
  left the SPEC's two other stale pairs stale, naming both, on this repository's worktree.
- **Bead:** `beadloom-ba9w.10` is open on the entry; S3z closes it with this evidence.

### #279

- **Command:** `beadloom sync-update --yes --all`
- **Where:** the worktree. `- bdd` added under `quality:` in `.beadloom/flow.yml` and a probe
  line in `doc_sync/scanner.py`, then `reindex`: 9 reference documents in surface drift and 3
  stale pairs over 2 refs.
- **Printed:**
  ```
  Re-baselined docs-audit: attested 1 pair(s).
  Re-baselined site-generation: attested 2 pair(s).
  Marked 2 ref(s) synced (3 pair(s) total).
  Re-baselined 11 reference doc(s).
  $ beadloom sync-update --help   -> --all: "With --yes: re-baseline every currently-stale ref
                                     (for the fixpoint loop)."
  ```
  Nine documents were drifted and eleven were re-recorded; none is named before or after.
- **Outcome:** live.
- **Evidence:** On 2026-10-20, on Beadloom 9.0.0 (`cdaf3f78`), `sync-update --yes --all` run
  for 3 stale pairs re-baselined 11 reference documents (9 of them drifted) on this
  repository's worktree, and neither the help nor the output names them.
- **Bead:** none exists. Proposed (with #166 and #134):
  `[BDL-UX #279 #166 #134] sync-update --all re-records reference documents only under its own
  flag, names each one, and counts only the drifted`.

### #223

- **Command:** `beadloom docs quality`
- **Where:** the worktree.
- **Printed:**
  ```
  missing-section: 146 finding(s) over 328 read
  341 document(s) read
  ```
  The count grew from 102 over 256 on 2026-09-02. The bead's own decision — a dated cut-off
  for the archive, or a computed standing count — has not been taken.
- **Outcome:** live.
- **Evidence:** On 2026-10-20, on Beadloom 9.0.0 (`cdaf3f78`), `docs quality` on this
  repository reported `missing-section: 146 finding(s) over 328 read`.
- **Bead:** `beadloom-l27n` (open, P2). It needs the owner's ruling between the two outcomes
  it names, and could equally be ruled a won't-fix with a dated stand-down for the archive.

### #209

- **Command:** `beadloom docs audit --verbose`
- **Where:** the worktree.
- **Printed:**
  ```
  README.md:375     mcp_tool_count   "18" OK
  README.ru.md:111  version          "9.0.0" OK          (the only mention read in README.ru.md)
  README.ru.md:375  `beadloom mcp-serve` даёт агентам **18 инструментов** ...   (not read)
  109 document(s) scanned, 53 not read, 1 scanned for versions only
  ```
  The same sentence is checked in English and unread in Russian, and no section of the output
  names a scanned document from which no count was extracted (candidate (b)).
- **Outcome:** live.
- **Evidence:** On 2026-10-20, on Beadloom 9.0.0 (`cdaf3f78`), `docs audit --verbose` read
  `mcp_tool_count 18` at `README.md:375` and no count at `README.ru.md:375`, which states the
  same 18 in Russian, and the summary named no document from which nothing was read.
- **Bead:** none exists. Proposed: `[BDL-UX #209] docs audit names each scanned document from
  which no count claim was extracted, so a non-English page is not read as verified`.

### #208

- **Command:** reading `src/beadloom/graph/rules/evaluators.py` and `graph/rules/__init__.py`
  against the package; `ls src/beadloom/graph/rules/*.py`.
- **Where:** the worktree.
- **Printed:**
  ```
  evaluators.py:  "it produces :class:`Violation` objects for every rule kind except cycles"
  __init__.py:    lists .types, .loader, .evaluators, .slices, .cross_imports, .cycles (6)
  ls graph/rules/*.py | wc -l   -> 28
  ```
  Both residues the entry named are still false: `doc_area`, `summary_facts`,
  `scenario_coverage`, `test_binding` and others evaluate in their own modules, and the
  package lists 6 of 28 modules. `tests/unit/graph/rules/test_rules_docstring_references.py`
  holds the dead-name half; nothing checks the prose half, by construction.
- **Outcome:** live.
- **Evidence:** On 2026-10-20, on Beadloom 9.0.0 (`cdaf3f78`), `evaluators.py` still claims to
  evaluate every rule kind except cycles and `graph/rules/__init__.py` lists 6 of the package's
  28 modules.
- **Bead:** none exists. Proposed: `[BDL-UX #208] the two stale docstrings in graph/rules
  corrected, and the owner rules the unchecked class (prose that names no dead symbol)`. The
  class itself is a won't-fix candidate: no mechanical check finds prose that names nothing.

### #206

- **Command:** `beadloom docs audit --verbose`
- **Where:** the worktree.
- **Printed:**
  ```
  Documents Not Read
    docs/domains/ai_agents/features/ai-techwriter/SPEC.md -- built-in exclude pattern
    docs/**/features/*/SPEC.md
    ... (52 SPEC files and CHANGELOG.md)
  ```
  The fixed half (the audit names what it did not read) holds. The SPECs are still excluded.
- **Outcome:** live.
- **Evidence:** On 2026-10-20, on Beadloom 9.0.0 (`cdaf3f78`), `docs audit --verbose` listed
  every `docs/**/features/*/SPEC.md` under "Documents Not Read" by the built-in exclude
  pattern.
- **Bead:** none exists. Proposed: `[BDL-UX #206] docs audit reads feature SPECs, or the
  exclusion is ruled with its reason`. The choice between the two is the owner's.

### #205

- **Command:** `beadloom docs audit`
- **Where:** the worktree, with a probe document `docs/guides/probe-s3b.md` (removed after).
- **Printed:**
  ```
  docs/guides/probe-s3b.md:3   language_count   "11" -> 2    "supports 11 languages through tree-sitter"
  docs/guides/probe-s3b.md:5   rule_type_count  "12" -> 28   "Rules support 12 authoring keys"
  ```
- **Outcome:** live.
- **Evidence:** On 2026-10-20, on Beadloom 9.0.0 (`cdaf3f78`), `docs audit` read "supports 11
  languages" as `language_count` and "Rules support 12 authoring keys" as `rule_type_count`,
  both stale, on a probe document in this repository's worktree.
- **Bead:** none exists. Proposed: `[BDL-UX #205] keyword-proximity binding stops reading a
  count of another sense as a fact (parser languages, authoring keys)`.

### #203

- **Command:** the two mutations of the entry, applied by hand to
  `src/beadloom/graph/rules/doc_area.py` and reverted after each run.
- **Where:** the worktree. NOT the full suite: the 1509 tests of the files that name
  `doc_area` or its rule (`tests/test_gate_three_states.py`, `tests/unit/graph/rules`,
  `tests/integration/graph/rules`, `tests/acceptance/steps/graph/rule-engine`,
  `test_bdl062_seams.py`, `test_onboarding.py`, `tests/self_check/docs/test_rule_engine.py`).
  The full suite runs serially here (no `pytest-xdist`), so it was not run twice.
- **Printed:**
  ```
  baseline:                                        1509 passed
  _area_depth tie-break (-votes, index) -> (-votes, -index):   1509 passed
  _normalise without the hyphen fold:              1509 passed
  ```
- **Outcome:** live.
- **Evidence:** On 2026-10-20, on Beadloom 9.0.0 (`cdaf3f78`), both `doc_area` mutations — the
  tie-break flipped to the deeper depth and the hyphen fold removed — survived the 1509 tests
  that name the rule; the full suite was not run.
- **Bead:** none exists. Proposed: `[BDL-UX #203] a test observes doc_area's shallower
  tie-break and its hyphen/underscore fold`.

### #202

- **Command:** `beadloom doctor`, `beadloom docs audit`
- **Where:** the worktree.
- **Printed:**
  ```
  doctor: [ok] CLI has 45 commands registered.
  audit:  cli command count: 56  -- NOT VERIFIED: no document states it
  ```
  `beadloom ci` prints neither number, which is the fixed half.
- **Outcome:** live.
- **Evidence:** On 2026-10-20, on Beadloom 9.0.0 (`cdaf3f78`), `doctor` printed "CLI has 45
  commands registered" and `docs audit` computed `cli command count: 56` on this repository.
- **Bead:** none exists. Proposed: `[BDL-UX #202] doctor's top-level command count and docs
  audit's recursive cli_command_count carry different names`.

### #200

- **Command:** `beadloom docs audit --verbose`, `beadloom config-check`, `beadloom lint`
- **Where:** the worktree, with an inert triple added to `docs_audit.ignore` (`path:
  docs/guides/testing.md`, `fact: mcp_tool_count`, `value: 99`), reverted after.
- **Printed:** nothing about the triple from any of the three commands. The only detector is
  this repository's own test, `tests/self_check/docs/test_every_declared_suppression_still_suppresses.py`,
  which an adopter does not run, and `test_bdl062_seams.py` states "nothing computes whether a
  suppression still earns its place, and nothing prints it".
- **Outcome:** live.
- **Evidence:** On 2026-10-20, on Beadloom 9.0.0 (`cdaf3f78`), a `docs_audit.ignore` triple
  that matches no mention was reported by neither `docs audit`, `config-check` nor `lint`.
- **Bead:** none exists. Proposed: `[BDL-UX #200] docs audit reports a docs_audit.ignore triple
  that suppresses nothing`.

### #190

- **Command:** `beadloom docs audit`
- **Where:** the worktree, with the probe document of #205.
- **Printed:**
  ```
  probe-s3b.md:7   version   "0.4.1" -> 9.0.0    "A JavaScript project at `0.4.1` was told `2.2.0`."
  probe-s3b.md:7   version   "2.2.0" -> 9.0.0
  probe-s3b.md:9   version   "1.5.0" -> 9.0.0    "drifted from 1.5.0 to 3.0.0"
  probe-s3b.md:9   version   "3.0.0" -> 9.0.0
  (line 11, "Measured under CPython 3.13.7", not reported)
  ```
- **Outcome:** live.
- **Evidence:** On 2026-10-20, on Beadloom 9.0.0 (`cdaf3f78`), `docs audit` still read "a
  JavaScript project at `0.4.1`" and "drifted from 1.5.0 to 3.0.0" as this project's version
  (four stale mentions) while "Measured under CPython 3.13.7" passed.
- **Bead:** none exists; `beadloom-tu41` is a neighbour (attribution across code spans), not
  this. Proposed: `[BDL-UX #190] a version behind a preposition or in a past-tense sentence
  can be quoted without reading as this project's version`.

### #179

- **Command:** `beadloom docs audit`; `.beadloom/_graph/rules.yml`
- **Where:** the worktree.
- **Printed:**
  ```
  rule type count: 28  -- 2 mention(s) checked
  sqlite: SELECT count(*), count(DISTINCT rule_type) FROM rules   -> 28|15
  python: len(beadloom.graph.rules.loader.AUTHORING_KEYS)           -> 17
  ```
  `_collect_rule_type_count` (`doc_sync/audit.py:986`) still counts rows; feature SPECs are
  still excluded (#206). `docs/architecture.md:193` now explains the misnomer to the reader.
- **Outcome:** live.
- **Evidence:** On 2026-10-20, on Beadloom 9.0.0 (`cdaf3f78`), the audit fact
  `rule_type_count` read 28, the number of rules this repository declares, against 15 types in
  use and 17 authoring keys.
- **Bead:** none holds the rename; `beadloom-ba9w.16` holds the unbound `authoring_key_count`.
  Proposed: `[BDL-UX #179] rule_type_count is renamed rule_count, and the type count is a fact
  of its own`.

### #167

- **Command:** `beadloom sync-check`
- **Where:** the worktree, a probe line appended to 8 files of `application/site/`, `reindex`.
- **Printed:**
  ```
  rc=2; 14 [stale] lines over 2 documents (domains/application/README.md: 7,
  domains/application/features/site-generation/SPEC.md: 7); 856 lines in all; no total line
  ```
- **Outcome:** live.
- **Evidence:** On 2026-10-20, on Beadloom 9.0.0 (`cdaf3f78`), `sync-check` on this
  repository's worktree printed 14 stale pair lines for 2 documents, one per pair, with no
  grouping per document and no total.
- **Bead:** none exists. Proposed (with #140): `[BDL-UX #167 #140] sync-check and the Gate
  group stale pairs per document with a count and a total, the pairs behind --verbose`.

### #166

- **Command:** `beadloom sync-update --all --yes`, `beadloom sync-check`
- **Where:** the worktree, the run of #279.
- **Printed:** `Re-baselined 11 reference doc(s).`; the following `sync-check` shows 0 drift.
  No document is named.
- **Outcome:** live.
- **Evidence:** On 2026-10-20, on Beadloom 9.0.0 (`cdaf3f78`), `sync-update --all --yes`
  cleared the surface drift of 9 reference documents in one run and printed only
  "Re-baselined 11 reference doc(s).", naming none.
- **Bead:** the proposal under #279.

### #163

- **Command:** `beadloom sync-update <ref>`, `beadloom sync-check`, `beadloom doctor`
- **Where:** the worktree.
- **Printed:**
  ```
  sync_state columns: ... synced_at, status, symbols_hash, file_symbols_hash,
    doc_hash_at_last_edit, baseline_source        (no count of re-baselines)
  doctor: [warn] Doc 'guides/agentic-flow.md' has no ref_id — unlinked from graph.
          (the same line for every guide, with watches or without)
  ```
  Hole 2 (a re-baseline without a document revision is recorded and counted) is not built.
  Hole 1 is half answered: `doctor` flags every unlinked guide, but does not distinguish the 7
  guides with no `watches` (of 13) from the ones that can drift. The concrete instance (the
  Mermaid sentence of the site guide) was corrected by hand.
- **Outcome:** live.
- **Evidence:** On 2026-10-20, on Beadloom 9.0.0 (`cdaf3f78`), the index holds no count of
  attestations made without a document change, and `doctor` warns every guide as unlinked
  whether or not it declares `watches`.
- **Bead:** `beadloom-9glj` (open, P2).

### #161

- **Command:** `beadloom docs audit`, `beadloom ci`; run as its steps `docs audit --verbose`,
  `lint` and `doctor`, not as `ci`
- **Where:** the worktree, a probe document naming `compute_the_phantom_total()` and
  `_mark_synced_noninteractive()` in backticks (removed after).
- **Printed:** no line about either name from `docs audit --verbose`, `lint` or `doctor`.
- **Outcome:** live.
- **Evidence:** On 2026-10-20, on Beadloom 9.0.0 (`cdaf3f78`), a document naming a function
  that does not exist passed `docs audit`, `lint` and `doctor` with no finding.
- **Bead:** `beadloom-431c` (open, P2).

### #140

- **Command:** `beadloom ci`
- **Where:** the worktree, the 14 stale pairs of #167.
- **Printed:**
  ```
  ::notice::sync-check FAIL: 14 stale pair(s)
  ::error file=domains/application/README.md::doc-stale: application: doc out of sync ... (x7)
  ::error file=domains/application/features/site-generation/SPEC.md::doc-stale: ... (x7)
  ```
  One line per pair, not per symbol occurrence, and a total; no grouping per ref or document.
- **Outcome:** live.
- **Evidence:** On 2026-10-20, on Beadloom 9.0.0 (`cdaf3f78`), `beadloom ci` printed a total
  of 14 stale pairs and then 14 `::error` lines for 2 documents, with no line per document.
- **Bead:** the proposal under #167.

### #138

- **Command:** `beadloom docs generate`, `beadloom reindex`, `beadloom doctor`
- **Where:** a throwaway Python project: six subpackages under `src/shop/`, every file
  annotated `domain=shop`, a hand-written graph of one service, one domain over `src/shop/`
  and one `component` node over `src/shop/search/`; `docs/architecture.md` of 4182 lines
  under 110 `##` sections.
- **Printed:**
  ```
  $ beadloom docs generate     -> Created 1 files, skipped 1 existing    (rc 0)
  files: docs/architecture.md, docs/domains/shop/README.md              (no DOC.md for the component)
  $ beadloom doctor            -> [warn] Node 'shop-search' has no doc linked.
  $ beadloom lint              -> 0 violations, 1 rules evaluated
  ```
  No command says that six subpackages have no feature or component node, or that the
  architecture document is 4182 lines.
- **Outcome:** live.
- **Evidence:** On 2026-10-20, on Beadloom 9.0.0 (`cdaf3f78`), `docs generate` on a coarse
  graph wrote no skeleton for a `component` node and warned about nothing, and no command
  reported six subpackages under one domain or a 4182-line architecture document.
- **Bead:** none exists. Proposed: `[BDL-UX #138] docs generate writes a DOC.md for a
  component, and the granularity and the monolith document are reported`.

### #134

- **Command:** `beadloom sync-update --yes --all` (repeated)
- **Where:** the worktree, the run of #279, then two more passes.
- **Printed:**
  ```
  pass 1: Re-baselined 11 reference doc(s).   sync-check: 0 drift
  pass 2: Re-baselined 11 reference doc(s).
  pass 3: Re-baselined 11 reference doc(s).
  ```
  The drift converges in one pass; the count never reaches 0.
- **Outcome:** live.
- **Evidence:** On 2026-10-20, on Beadloom 9.0.0 (`cdaf3f78`), the second and third
  `sync-update --yes --all` passes over a tree with no drift each printed "Re-baselined 11
  reference doc(s)." on this repository's worktree.
- **Bead:** the proposal under #279.

## Observed beside the entries

These belong to no entry of this file, and S3z routes them.

- **`sync-check` is not idempotent after a document edit.** On the monorepo fixture, code and
  document edited together, one `reindex`: the first `sync-check` printed two pairs
  `stale (hash_changed)`, the second, with nothing changed between them, printed them `ok`.
  The first run records the document edit (`doc_sync/engine.py`, the two-phase block) and
  judges before it. A Gate that runs `sync-check` once reads a false stale. Likely S4's family.
- **`doctor` and `sync-check` disagree about stale.** On the same fixture state, `doctor`
  printed `[ok] No stale sync entries.` while `sync-check` printed two `untracked_files` pairs
  stale (rc 2). This is the population question of `beadloom-r9t5`.

## Summary

| Entry | Outcome | Bead |
|---|---|---|
| #349 | live | proposed: `[BDL-UX #349] a spec file beside the code does not pair with the node's document as code, and sync-update --pair names the pairs it attests` |
| #348 | live | proposed: `[BDL-UX #348] incremental reindex opens the pair for a new file under a node's source, and the untracked_files hint names reindex --full first` |
| #347 | live | proposed: `[BDL-UX #347] a file owned by another node's source or annotation is not an untracked file of the directory's node, and details name the owner` |
| #346 | live | proposed: `[BDL-UX #346] symbols_changed names the symbols that moved and the clearing action in the plain output, and an unchanged file reads sibling, not stale` |
| #345 | live | proposed: `[BDL-UX #345] the required-section match accepts a heading that ends in punctuation, and section-not-in-use names the heading and the files it read` |
| #342 | live | proposed: `[BDL-UX #342] one owner per file — the annotation decides pairs and edges alike — and doctor names a file two nodes claim` |
| #322 | closed | none; residue in `beadloom-ba9w.16` |
| #315 | closed | `beadloom-ba9w.10` (to close with this evidence) |
| #279 | live | proposed: `[BDL-UX #279 #166 #134] sync-update --all re-records reference documents only under its own flag, names each one, and counts only the drifted` |
| #223 | live | `beadloom-l27n` (owner's ruling) |
| #209 | live | proposed: `[BDL-UX #209] docs audit names each scanned document from which no count claim was extracted, so a non-English page is not read as verified` |
| #208 | live | proposed: `[BDL-UX #208] the two stale docstrings in graph/rules corrected, and the owner rules the unchecked class (prose that names no dead symbol)` |
| #206 | live | proposed: `[BDL-UX #206] docs audit reads feature SPECs, or the exclusion is ruled with its reason` |
| #205 | live | proposed: `[BDL-UX #205] keyword-proximity binding stops reading a count of another sense as a fact (parser languages, authoring keys)` |
| #203 | live | proposed: `[BDL-UX #203] a test observes doc_area's shallower tie-break and its hyphen/underscore fold` |
| #202 | live | proposed: `[BDL-UX #202] doctor's top-level command count and docs audit's recursive cli_command_count carry different names` |
| #200 | live | proposed: `[BDL-UX #200] docs audit reports a docs_audit.ignore triple that suppresses nothing` |
| #190 | live | proposed: `[BDL-UX #190] a version behind a preposition or in a past-tense sentence can be quoted without reading as this project's version` |
| #179 | live | proposed: `[BDL-UX #179] rule_type_count is renamed rule_count, and the type count is a fact of its own` |
| #167 | live | proposed: `[BDL-UX #167 #140] sync-check and the Gate group stale pairs per document with a count and a total, the pairs behind --verbose` |
| #166 | live | the #279 proposal |
| #163 | live | `beadloom-9glj` |
| #161 | live | `beadloom-431c` |
| #140 | live | the #167 proposal |
| #138 | live | proposed: `[BDL-UX #138] docs generate writes a DOC.md for a component, and the granularity and the monolith document are reported` |
| #134 | live | the #279 proposal |

Counts: 2 closed, 24 live, 0 won't-fix candidates, 0 not reproducible, 0 not this area. Two
of the live entries carry a won't-fix question for the owner inside them: #208's class (prose
that names no dead symbol) and #223's archive (`beadloom-l27n`). #203 was measured over 1509
tests that name the rule, not the full suite.
