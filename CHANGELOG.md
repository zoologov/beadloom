# Changelog

All notable changes to Beadloom are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.1] - 2026-08-27

**A patch that grew past its scope, and says so.** BDL-062 set out to close one gap — the graph's
own metadata was the last surface nothing checked — and found, on the way, that `beadloom docs
audit` had been reporting facts about *Beadloom* as facts about *the adopter's project* since the
audit existed. Three mechanisms ship, one defect every adopter had is fixed, and two behaviour
changes land that an upgrader has to know about before running the Gate. The version is a
**patch** because no interface moved: every command keeps its flags, every JSON key a 3.0.0
consumer parses is still emitted, and nothing an adopter wrote stops loading. What can change is
the *verdict* a graph gets, and both cases are stated below with their one-key opt-out.

The release exists because of the item that sounds smallest. The package description on the PyPI
project page still read `Context Oracle + Doc Sync Engine for AI-assisted development` — the 1.x
sentence, unchanged across three major releases, on the page that is the first thing anybody
reads. A metadata field is only published by publishing.

### Added

- **`graph_summary_facts` — a number or version stated in a node `summary` is checked against the
  fact the project computes.** A `summary` is the sentence every other surface quotes: `beadloom
  ctx`, `prime`, the generated site, the agent adapters. Until this rule nothing compared it
  against anything, and the measurement that opened the bead is the argument for it — on *this*
  repository the root node claimed `v1.5.0` against a computed `3.0.0` and `mcp-server` claimed
  `14 tools` against a catalogue of 18, both wrong across three major releases with no check going
  red. The rule owns neither the extraction nor the comparison: `DocScanner.scan_line` reads the
  claim and `compare_facts` judges it, so the version pattern, the keyword table, the clause-scoped
  proximity and the per-fact tolerances are the documentation audit's single answer rather than a
  second one. It takes no configuration keys and the loader rejects an unknown one. Four outcomes
  are counted apart: agrees, states no claim, disagrees (a finding at the rule's severity), and
  `unverifiable` — a claim naming a fact the project declined to compute, which reports the reason
  and names its node. Enable it with a `summary_facts: {}` block in `.beadloom/_graph/rules.yml`;
  `beadloom init` does not write it for you. Measured on this repository at release: of 84 node
  summaries, **2 state a checkable fact and both agree, 0 disagree, 0 are unverifiable and 82 state
  no number at all** — which is itself the fact worth knowing, and see **Changed** for what it now
  costs a graph where that last number is all 84.

- **`doc_area_coherence` — a node documents itself where the graph's own convention says it
  should.** The convention is **derived from the graph under test, never hardcoded**: the source
  root is found by descending while exactly one next segment is supported, the source area is the
  segment below it, and the documentation area is the segment at the depth where documentation
  paths name source areas. No directory literal appears anywhere in the rule, and an AST test fails
  the build if one is introduced — which is why it holds on a Feature-Sliced Design tree exactly as
  it holds on a Domain-Driven Design one, without either layout being named in the code. A graph
  with no dominant mapping is reported as having checked nothing rather than passed. `min_support`
  (default 2) exists because without it an area holding one documented node is unanimous at one
  observation, so a six-node graph would report a clean sweep having compared nothing; the loader
  rejects `threshold <= 0.5` and `min_support < 2`, both being configuration that reads as a rule
  and behaves as a silence. It ships `warn`, because a convention check that blocks an adopter's
  first run on their own house style is a rule they switch off. Measured on this repository at
  release: **79 placements compared under 8 dominant mappings, 3 rootless, 3 with no segment at the
  area depth, 0 outside the source root.**

- **`docs audit` reports three populations instead of one.** A declared fact is now *verified*,
  *not applicable to this project*, or *declared and unverified*, and each not-applicable fact
  carries the reason it could not be computed plus the `docs_audit.extra_facts` key that would let
  the project declare its own. `N mention(s) fresh` counts what the audit found and says nothing
  about the facts it found nothing for, which is how a report covering one fact of nine printed as
  a clean bill of health. The `--json` payload gains `verified_facts`, `not_applicable` and
  `summary.not_applicable_count`, and **every top-level key 3.0.0 emitted is still emitted** — a
  test pins the literal 3.0.0 key set, so a lost key fails rather than a changed shape passing.
  Measured on this repository: 9 facts declared, 5 verified, 0 not applicable.

### Fixed

- **`docs audit` declared two facts about Beadloom as facts about the audited project (BDL-062
  `.3`).** `_collect_mcp_tool_count(self, facts)` took no `project_root` at all, and
  `_collect_cli_command_count` counted the commands of the Click group in the *running* process. On
  any project that is not Beadloom, both answered anyway. Captured on the published 3.0.0 wheel in
  a fresh virtual environment, against a Python project created from scratch outside this
  repository and declaring itself `invoice-svc`:

  ```
  3.0.0   facts declared: 9   mcp_tool_count = 18  (source: MCP tool catalog)
                              cli_command_count = 43 (source: CLI)
  ```

  Both surfaces are now gated on identity — the project under audit must declare itself as the
  distribution whose surfaces this process can introspect, read from `pyproject.toml`,
  `package.json` or `Cargo.toml` with **no directory-name fallback**, because a clone in a
  directory called `beadloom` is not Beadloom. Verified on the same project with this release:

  ```
  3.0.1   facts declared: 7   mcp_tool_count, cli_command_count: absent from `facts`,
                              reported as NOT APPLICABLE with the identity clause and the
                              `docs_audit.extra_facts` key that would declare the project's own
  ```

  The denominator moved 9 → 7 and the report says so. On Beadloom itself the human output is
  byte-identical, because the not-applicable population is named only when it is non-empty.

- **`framework_count` is renamed `nodes_with_framework`, and its keywords now mean nodes rather
  than frameworks (BDL-UX #193).** The old name read "12 web frameworks the route extractor parses"
  as a claim about `COUNT(*)` of nodes declaring a test framework — two different quantities under
  one name. **A consumer reading `framework_count` out of the `docs audit --json` payload must read
  `nodes_with_framework` instead**; it is the one fact name that moved. Whether the fact keeps the
  count floor is decided by `scanner.is_count_fact()` rather than by the `_count` suffix, so the
  rename did not silently take it out of the floor.

- **A module docstring that described a function deleted the same morning (BDL-062 `.11`).**
  `graph/rules/doc_area.py` documented `_common_prefix`, which `_source_root` had replaced, while
  `docs/domains/graph/README.md` described the replacement correctly — the project's thesis
  inverted. A docstring lives inside the file whose hash defines its pair's freshness, so **a file
  is always fresh with respect to itself** and `sync-check` cannot see this class by construction.
  All 11 modules under `graph/rules/` were swept and the 32 symbols their docstrings name resolved;
  `tests/test_rules_docstring_references.py` now pins that.

- **A single misplaced node could veto the derived source root (BDL-062 `.9`).** `doc_area`'s first
  derivation took the longest common prefix of every node source, so one node outside the tree
  collapsed the root and the rule reported 7 false errors while comparing 0 and leaving 86 nodes
  unnamed. A threshold-based descent was tried first and discarded, and the reason is worth
  recording: at 0.60 a modal prefix of 6/10 is accepted, so the root deepens by one level and stops
  being a root. A root is the level *above* where the areas start, so the dial is `min_support`, not
  `threshold`.

### Changed

Two changes alter a verdict without altering an interface. Both are stated with the remedy.

- **`graph_summary_facts` ships at `error` severity, so a graph whose summaries state no checkable
  number goes red the first time it is enabled.** The rule is new, so nothing regresses — but a
  total stand-down is a blocking finding rather than a note, and that is deliberate: a summary
  contradicting the project it describes is wrong in every house style, so there is no adopter
  preference to respect, and the value being checked is in the graph the adopter wrote. The cost is
  real and was measured before the change was made rather than argued about. On a two-module Python
  project bootstrapped with `beadloom init --mode bootstrap`, with the rule enabled:

  ```
  Rule 'graph-summary-facts' checked nothing: none of the 3 node summaries in this graph
  states a number or version that the project computes a fact for.
  lint --strict -> rc 1     rules_inert: 1, error_count: 1
  ```

  The condition is narrower than "any bootstrap", and the boundary is worth knowing: the generated
  root summary quotes the README's opening sentence, so a README that states a version gives the
  rule one claim and the run stays green. The same project with `version 0.4.2` in that sentence
  reported 0 violations. **The opt-out is one key** — `severity: warn` in the same `rules.yml`
  entry that enabled the rule, measured to return `rc 0` with the stand-down still printed as a
  warning.

- **A rule that stands down over its *whole* population now carries the severity the project
  declared for it.** `liveness_finding` hardcoded `severity = "warn"`, so a rule a project had
  escalated to `error` could stop checking every one of its 86 pairs while `lint --strict` exited
  0 — a green Gate describing the checker's ignorance rather than the code's health. `total` and
  `partial` are two different facts and now reach the reader at two severities: a total stand-down
  names no node and carries the declared severity, while **partial inertness stays `warn`** and
  names the node it could not check. `beadloom lint`'s summary line reads `N rules evaluated, M of
  them unable to check anything`. For a project whose rules all ship `warn`, nothing changes.

- **Both READMEs are restructured as a landing page.** `README.md` 396 → **283** lines and
  `README.ru.md` 397 → **283**, identical in structure — 18 headings each, section order matching
  line for line, and a "Where to start" paragraph giving the reader one order and one first
  command. The section order is graph → tools → what it solves → federation → Gate → agentic
  workflow → no shadow code.

- **All eleven guides brought to current functionality**, read in full — 4602 lines,
  measured before the edits: 9 changed, 2 judged current without change. Four superseded behaviours were found by reading rather than by
  any check — the pre-push Gate documented as 5 steps when it runs 8, two guides contradicting each
  other on the composed adapter line counts (measured: 401 with the `ddd` and `python` overlays, 371
  with neither), `module-coverage` described as "warn for now" when `rules.yml` sets `error`, and
  the AI tech-writer listed as deferred when it shipped in BDL-047.

- **The package description states what 3.x is.** `Context Oracle + Doc Sync Engine for
  AI-assisted development` → `The architecture graph of your codebase, and the gate that holds
  documentation, boundaries, cross-repo contracts and the agentic workflow to it`, in
  `pyproject.toml` and in the package docstring, with a test pinning the two to agree. **Agreement
  is checkable and currency is not** — the module says so in its own docstring, and reverting both
  copies to the 1.x sentence leaves that test green. That is exactly how the old sentence survived
  three major releases.

### Known limitations

Measured and open at release, listed here rather than left to be discovered. These six are the
ones an adopter or a contributing agent will meet; the last was found by this release's own
housekeeping.

- **`docs audit` extracts zero facts from a non-English document and counts it as scanned anyway
  (BDL-UX #209).** `DocScanner.FACT_KEYWORDS` is English by construction — `["MCP", "tool", "server
  tool"]`, `["rule type", "rule kind", "rule"]` and so on — so a document written in another
  language contains none of those tokens near its numbers and yields no claim. The document is not
  excluded: it matches the `*.md` glob, enters the scan surface and is counted among the files
  scanned. Measured on the two halves of this repository's own translation pair: `README.md` 1 fact
  mention found, `README.ru.md` 0. Every number in the Russian README is therefore unverified, and
  they are correct today because a person kept them correct. **Until it is fixed:** treat
  `N mention(s) fresh` as a statement about the English surface only, and review non-English
  documents by hand.

- **A factually correct number can bind to a fact that computes something else (BDL-UX #205).**
  Keyword-proximity binding has no notion of sense, so `supports 11 languages` binds to
  `language_count` (which counts the languages the *project is written in*, 1 here) and `Rules
  support 12 authoring keys` binds to `rule_type_count` (which is `COUNT(*) FROM rules`, 15). Both
  sentences are true and both make the Gate exit 1, which punishes correcting documentation. The
  edge is fine enough to be surprising: the same phrase is safe 254 lines earlier in
  `architecture.md` because no `rule` token falls inside the five-word proximity window. **The
  working rule is to measure the audit's answer rather than predict it**; the remedy for a genuine
  collision is a `{path, fact, value}` triple under `docs_audit.ignore`, which silences exactly one
  match and is reported when it goes inert.

- **`docs/**/features/*/SPEC.md` is excluded from `docs audit` outright (BDL-UX #206).**
  `scanner._EXCLUDE_PATTERNS` drops it from the audit surface entirely, so a SPEC — the document
  where a node's contract is written — is the one class nothing fact-checks. Measured: three
  forward references to a release that did not exist yet survived in SPEC files while the same
  defect was being removed from a README hours earlier. "Excluded" and "verified" print the same
  way in the coverage report.

- **`bd merge-slot` is not an exclusion primitive (BDL-UX #194 — External, `steveyegge/beads`
  1.0.4).** Two independent defects: the actor chain is `$BEADS_ACTOR` → `git user.name` → `$USER`,
  so every concurrent agent under one git identity resolves to the same actor and `acquire` cannot
  tell a sibling from the holder; and `release` accepts any caller, so one agent can free another's
  hold. Observed again during this cycle — the slot was left held by a stale `coordinator` entry
  with four waiters, three of which had finished hours earlier, and two agents polled it for 18 and
  13 minutes. **Set `BEADS_ACTOR` per agent**, treat `acquire --wait` as capable of enqueuing
  behind a holder that will never release, and do not poll indefinitely. The related gap on the
  Beadloom side is #207: the pre-commit hook re-stages `.beads/issues.jsonl` even against an
  explicit pathspec commit, so "commit only your own files by explicit path" cannot be satisfied by
  an agent following it exactly.

- **`beadloom active-sync` resolves no row when a bead id is written as a Markdown code span
  (BDL-UX #210, filed by this release).** `_reconcile_one` passes the first cell to the resolver
  verbatim, so `` `beadloom-viaj.1` `` matches neither a full id nor the short form and the run
  reconciles nothing — while reporting that the cell *is not a bead id*, which sends the reader to
  the tracker rather than to the formatting. Measured on this repository: of 29 `ACTIVE.md` tables
  carrying rows, **13 resolve none**. The shipped template writes ids bare, so a project that has
  not restyled it is unaffected. Plain `active-sync` — the form the pre-commit hook runs — exits 0
  whether it reconciled every row or none, so at the hook an inert table is indistinguishable from
  a coherent one. **Remedy:** write bead ids bare in the first column, and use `active-sync
  --check`, which exits 1 on drift and names every row it could not resolve.
- **A virgin `beadloom init --yes` still leaves `beadloom ci` red (BDL-UX #192, carried from
  3.0.0).** Re-measured against this release on a scratch TypeScript project with one file under
  `src/`: `beadloom init --yes --mode bootstrap` exits 0 over a graph of **2 nodes and 0 edges**,
  then `beadloom lint --strict` and `beadloom ci` both exit 1 on `domain-needs-parent` — a rule the
  same command wrote one step earlier. The classifier writes a `src` node of kind `domain` and no
  edges at all, while the rule generator writes `domain-needs-parent` whenever any node is a
  domain. **Remedy until it is fixed:** add the edge by hand — an `edges:` entry `{src: <domain>,
  dst: <root ref_id>, kind: part_of}` in `.beadloom/_graph/services.yml` — and run `beadloom
  reindex`. Plain `beadloom lint` without `--strict` exits 0 throughout.

## [3.0.0] - 2026-08-26

**The flow is enforced, and what cannot be checked says so.** BDL-061 ships six slices and a
drift wave: flow guards, the false-green residue S2 measured and left open, a project layer for
the agentic flow, executable scenarios plus document quality, three document spaces, and a wave
shape decided from the architecture graph rather than guessed. The version is **major** for two
reasons. By semver it is breaking — `sync-check` fails where it passed, `sync-update <ref>`
attests less than it did, and the scaffolded required-context set went from seven to nine. And
this is the release of a tool that spent an entire epic on *do not claim more than you did*:
numbering a behaviour-changing release as a minor would be that same failure, in the version
number.

### BREAKING

Three changes can turn a green project red, or make a command that still passes claim less than
it used to. Each is stated with its remedy.

- **A document the graph declares and the tree does not hold is `missing`, and `sync-check`
  exits 2 (BDL-UX #174).** Before this release, deleting a declared document made the check
  *quieter*: the reindex that followed removed that document's pairs, so nothing was left to
  miss and the Gate stayed green. Declarations are now cached from the committed graph YAML in
  a `declared_docs` table and outlive the file they name, so the pair is reported `missing`
  with the reason `declared_doc_missing`, `missing` is a blocking status, and `beadloom ci`
  fails on it. **A project whose graph declares a document it no longer holds goes red on
  upgrade, and that is the intended fix** — the check was passing because it had less to check.
  **The remedy is one of two:** restore the file at the declared path, or delete the `docs:`
  entry naming it from `.beadloom/_graph/*.yml` and run `beadloom reindex`. **Before
  upgrading**, run `beadloom sync-check --json` against 3.0.0 in a scratch clone and read
  `summary.missing`; every such pair is listed by path under `pairs`, and that count is what
  your pipeline will exit 2 on.

- **`sync-update <ref> --yes` attests the STALE pairs of the ref, not all of them (BDL-UX
  #163).** A script calling it keeps working and keeps exiting 0; what changed is how much it
  claims. The command records that somebody read a document and that the document still
  describes the code, and the whole-ref form made that claim for every pair of the ref,
  including pairs the run had no grounds for. That is not bookkeeping: `check_sync`
  corroborates an `index_build` baseline against `HEAD` rather than trusting it, and writing
  `baseline_source = attested` switches that harder check off — so the bulk form was silencing
  the stricter path for documents nobody had opened. The default scope is now the pairs
  `sync-check` reports `stale` or `missing`. `--pair <doc_path>` names one document, `--code
  <file>` narrows a document to one of its code files, and **`--all-pairs` restores the old
  whole-ref scope**, kept because an operator who has read all of it must still be able to say
  so in one command. A fixpoint loop that re-baselines what `sync-check` reports stale needs no
  change. A script that used `sync-update <ref>` to clear an `unverified` row must now read the
  document and name it with `--pair`, or say `--all-pairs` and own the claim. Measured on the
  change that introduced it: 7 pairs revised and 7 attested, against ratios of 1/27, 13/20,
  26/56 and 15/10 recorded earlier in the same epic, with `unverified` falling from 107 to 0.

- **`beadloom setup-branch-protection` declares nine required contexts, up from seven — do not
  re-run it until all nine report green.** The two environment-dimension legs `tests-locale
  (C)` and `tests-locale (en_US.ISO-8859-1)` joined `DEFAULT_STATUS_CHECK_CONTEXTS`. The
  command is a declarative `PUT`, so it always settles the same state — and that is the hazard
  rather than the reassurance, because the state it settles is **the set this version
  declares**, not the set your repository already has. Under `strict: true` a required context
  that no workflow produces makes the branch permanently unmergeable. **The remedy, in order:**
  re-scaffold the pipeline (`beadloom setup-ai-techwriter`) so a `tests-locale` job exists,
  open a pull request and confirm both contexts actually report (`gh pr checks <pr>`), compare
  that against what is live (`gh api repos/:owner/:repo/branches/main/protection --jq
  '.required_status_checks.contexts'`), and only then re-run the command — or pass the set your
  pipeline can satisfy through the repeatable `--check`, which replaces the default entirely.
  `--dry-run` prints the exact `gh api` call and payload without touching GitHub. This is not
  hypothetical: this repository's own `main` requires **seven** contexts against the **nine**
  this version declares, measured on the day of the release.

Three further changes can surprise a script without turning a correct project red. The
freshness baseline moved out of `.beadloom/beadloom.db` into git, so `rm .beadloom/beadloom.db
&& beadloom reindex` no longer reaches a green `sync-check`. The `rules.rule_type` CHECK
constraint was dropped and existing databases are migrated in place, so a consumer that relied
on the database to reject an unknown rule type must rely on `load_rules` instead. And an
installed pre-commit hook keeps its old whole-tree behaviour until you re-run `beadloom
install-hooks`.

### Added
- **`beadloom ctx` carries intent — the reason a node exists, beside what it is (BDL-061
  `.87`).** `beadloom ctx <ref-id>` is step 4 of the start-of-work protocol, so it is the one
  moment an agent is guaranteed to ask about a node, and it returned reality with no intent.
  The bundle now carries an `intent` section: the epics whose planning documents **declared**
  the focus node, with the document and the line to read the reason at. A node nothing declares
  — 69 of this repository's 84, so the common case — reports `none_declared` **with the size of
  what was searched** (`61 epic(s) read, 5 of them declare a node`). That is a measurement, and
  it is deliberately not the status `not_checked`, which `--no-intent`, an empty TO-BE space, a
  population that declares nothing anywhere and an unreadable `doc_roots` each carry with their
  own reason. On by default on measured cost: 306 B on `flow-guards` and 713 B on `why` against
  bundles of 124 KB and 150 KB, a mean of 22 B per bundle (0.015%), and 26 ms on a cold bundle
  against nothing on a cached one. The TO-BE tree is folded into the bundle cache's freshness
  inputs, so an edited `CONTEXT.md` invalidates the bundles that carry it.
- **The guard firing record is bounded, and rotation loses no count (BDL-061 `.56`).** Bounded
  by RECORDS (2000) rather than by bytes or by age: a byte cap truncates mid-record, and an age
  cap loses *how often* on a long-lived project and makes a quiet month read like a dead guard.
  Firings that leave the active file fold into a carried summary holding, per guard, the count,
  how many reached a verdict, and the first and last moment and outcome — every input
  `beadloom guard --liveness` reads — so `fired_count`, `never-fired` and the last outcome are
  unchanged across a rollover. What rotation costs is per-firing `why` text older than one
  generation, and `carried_count` states how much of a count rests on a summary rather than on
  readable lines. The scaffolded ignore pattern widened to `guard-firings*.jsonl` so the
  archive is not left as untracked churn.
- **`beadloom waves` — the wave shape is decided from the graph, not guessed (BDL-061 S6).**
  `beadloom waves BEAD [BEAD ...] [--json]` decides which of the named beads may run at the
  same time from the code-level independence of their declared node scopes, because a tracker
  knows which beads block which while only the architecture graph knows which code they
  occupy. Each serialised pair carries one reason from a closed vocabulary
  (`blocked_by_bead`, `unresolved_scope`, `shared_node`, `shared_file`, `dependency_edge`,
  `override_serial`). The guarantee it keeps, in one sentence: for any two beads placed in
  the same wave, no medium they share can carry one bead's in-progress state into the other's
  result — and where a medium cannot give that guarantee, the wave says so and names the one
  bead (`gate_owner`) that measures the combined outcome. Four media are shared no matter
  what shape is chosen — one working tree, one pre-commit hook, one doc-freshness baseline,
  one tracker id space — and each now carries a **plan-time verdict** that can come back
  `failed`, while a medium nobody observed comes back `unmeasured`, which is a finding
  reaching exit 1 rather than a silent pass. What is checked is a precondition measured
  before the wave runs; the wave's conduct afterwards is checked by nothing here and cannot
  be by anything holding a plan. A human outranks the decision through
  `.beadloom/flow.yml` `waves.overrides[]`, with a mandatory reason and exit condition, and
  an override that changed no decision is reported as inert. Exit 0 clean / 1 findings / 2
  undecidable. See the [Parallel waves guide](docs/guides/parallel-waves.md).
- **`beadloom review-brief` — a reviewer is handed the change and the specification, not the
  author's account of either (BDL-061 S6).** `beadloom review-brief BEAD [--since REF]
  [--release] [--json]` assembles the assignment, the declared scope, the graph's
  specification documents, the bound `@bead:` scenarios and every changed file, and
  **withholds the bead's own comments**, reporting how many it withheld. The measurement
  behind the ordering: in hidden-profile tasks a group that hears one member's conclusion
  first scores 17–36% where a single holder of all the facts scores ~100%. The account is
  released, not destroyed — `--release` prints it once a verdict comment is recorded, so
  deferrals and measured numbers stay available after the reviewer's own judgement is on the
  record. Exit 0 clean / 1 findings / 2 unassemblable / 3 release refused; `3` is distinct
  from `2` so a caller cannot confuse *refused* with *failed*. Enforced for what it can see;
  **documented, not enforced** for two defeats it cannot — a reviewer running `bd comments`
  itself, and a coordinator pasting a summary into the launch prompt, which `coordinator.md`
  now forbids by name.
- **`sync-check --staged` — the pre-commit hook judges the commit, not the tree (BDL-061 S6,
  BDL-UX #118).** The installed hook now runs ruff and mypy over the staged `src/`/`tests/`
  Python files and `sync-check` over the pairs the commit stages either side of, and prints
  how many modified or untracked files outside the commit it did not judge. `--staged` adds
  two summary keys present in that mode only (`not_checked_outside_commit`, `commit_scope`),
  a `scope` record to `--porcelain` in the existing five-column shape, and a leading line to
  the human output. The pre-push Gate is unchanged and still judges the whole tree.
  **Adopters must re-run `beadloom install-hooks`** — an installed hook keeps its old
  behaviour until they do, and `beadloom waves` now reports `commit-gate: failed` instead of
  leaving it to be noticed.

- **Three documentation spaces, and a relation between two of them (BDL-061 S5).** Every
  document a project holds is classified TO-BE (`PRD`, `RFC`, `BRIEF`, `CONTEXT`, `PLAN`),
  AS-IS (`SPEC`, `DOC`, `README`) or WORKING (`ACTIVE`). The names are deliberately not
  TODO/DONE, because **nothing changes status**: a PRD stays the record of what was intended
  while a *different* artifact is updated to describe the new reality, so the checkable claim
  is a relation between two artifacts rather than a flag on one — a flag has nothing to be
  verified against. `beadloom docs spaces [--json] [--strict]` reports an epic that recorded
  intent in its `CONTEXT.md`/`BRIEF.md` *Related Files* section, has at least one closed
  bead, and declared a graph node with **no AS-IS document**. Measured on this repository:
  one finding, and it is true — this epic declares the `cli-commands` node, which carries no
  `docs:` entry at all. No other check could see it: `lint` asks whether modules reach nodes,
  and `sync-check` compares pairs, so an undeclared document has no pair to go stale. Roots,
  kinds and intent documents are configurable under `doc_roots` in `.beadloom/config.yml`
  from the first release, and `beadloom search --kind {to_be,as_is,working}` searches the
  planning tree in place. New `beadloom ci` step `doc-spaces`, warn-only. See the
  [Document Kinds guide](docs/guides/document-kinds.md).
- **`exempt` — a WORKING document is excused from freshness by DECLARATION (BDL-061 S5).** A
  sixth `sync-check` verdict. The exemption is a config declaration carrying a mandatory
  reason, never an inference from a missing pair, because deleting a pair must not make a
  check quieter. A wrong declaration is detectable two ways: `working_exemption_inert` names
  each declared kind and each declared root that matched no document, and
  `working_declaration_contradicted` names a document the config calls ephemeral that the
  graph also declares as a node's documentation. `missing` is decided before any exemption
  applies, so a deleted file is never made quieter by a declaration.
- **`sync-check --json` counts every verdict (BDL-061 S5).** The summary gains `exempt` and
  `incomplete`, so `ok + stale + missing + unverified + exempt + incomplete` sums to `total`;
  a consumer computing `total - ok` no longer reads unexplained pairs. The rich output gains
  an `[exempt]` marker with the declared reason, and the Gate's sync-check line gains
  `, M exempt — <reason>`. The `--since` shape is unchanged.
- **A project layer for the agentic flow — every artifact composes (BDL-061 S3).**
  `compose(kind, name, config, project_root)` assembles the role protocols, the slash
  commands and `CLAUDE.md` from four layers in a fixed order: the shipped stack-neutral
  CORE, one architecture overlay (`ddd` | `fsd`), each stack overlay **sorted**, and the
  adopting repository's own fragment under `.beadloom/flow/{roles,commands,claude}/`. The
  project layer is appended verbatim, cannot delete core text, is never overwritten, and
  **survives every upgrade** — it lives in Beadloom's configuration directory rather than
  inside a vendored file. Measured on the shipped artifact: the core `CLAUDE.md` went from
  **440 to 376 lines**, with every removed line mapped to a replacement (the Quick
  Reference and Agent Checklist sections restated §0 command for command; the Python
  anti-patterns and the `uv run pytest` / `ruff` / `mypy` block moved into the Python stack
  overlay). A `ddd` + `python` project composes 406 lines; a project selecting no stack
  overlay gets 376 and no Python command in its critical rules. Closes BDL-UX #139 and
  #152. See the new [Project Overlays guide](docs/guides/project-overlays.md).
- **`overlays.suppress` — standing a core rule down is a declaration (BDL-061 S3).**
  `.beadloom/flow.yml` gains `overlays.suppress`, each entry carrying a mandatory `rule`,
  `reason` and `until`; an entry missing any of them is a configuration error, and an
  unknown key under `overlays` is rejected with the reminder that project additions are
  files, not keys. Every suppression is appended to **each** composed artifact as a visible
  notice, so the reader about to follow the core rule is told it was stood down, why, and
  what retires it. `config-check` reports one that has expired and one whose `rule` names
  no heading in the project's own composed corpus, both at `warn` — the findings
  `forbid_import` exemptions already made, one layer up, through the same
  `exit_condition_deadline`.
- **`language:` in `flow.yml` (BDL-061 S3).** A BCP-47-ish tag validated for shape rather
  than against a closed list, selecting a `<name>.<lang>.md.txt` fragment in every layer.
  A localisation that has not shipped falls back to the default **and says so** in the
  composition notes. The core's unconditional "documents MUST be written in English" is now
  the `doc-language` auto-region rendered from this key. Closes BDL-UX #136.
- **`.beadloom/flow-manifest.json` — the record of what Beadloom wrote (BDL-061 S3).** Every
  composed write is fingerprinted, so a later run can tell its own output (`stale`,
  recomposable) from a hand edit (`hand_edited`, reported and never rewritten) from a file
  it wrote that is now gone (`missing`) from one nothing accounts for (`unverified`). The
  file is generated state and **belongs in git**: without it in the clone, ownership rests
  on the artifact's provenance stamp alone.
- **An ignore block at `init` (BDL-061 S3).** `beadloom init` and `beadloom
  setup-agentic-flow` append Beadloom's generated working set to the project's `.gitignore`,
  once, each pattern preceded by the reason it is there. Written once and never rewritten,
  so deleting a line is a permanent override rather than a losing fight with the tool.
  Nothing is written outside a git working tree and no pattern the project already declares
  is duplicated.
- **`scenario_coverage` — behaviour bound to an executable claim (BDL-061 S4).** A tenth rule
  type. A behaviour-bearing node with no scenario is reported, a scenario naming no bead is
  reported, and a scenario a PRD or BRIEF references and the suite does not contain is
  reported. The binding rides on ordinary Gherkin tags — `@bead:<id>` and `@node:<ref_id>`,
  with the language's own `Feature:` / `Rule:` inheritance — so every parser, runner and
  editor already reads it. The `.feature` file is the source of truth and the document
  references it: an executable artifact cannot silently lie, and a generator between the two
  becomes a synchronisation problem of its own. `en` and `ru` dialects ship and
  `# language: xx` is honoured; any other declared dialect, a file that is not UTF-8 and a
  file declaring a second `Feature:` are each reported as UNREADABLE rather than counted as a
  file with no scenarios. Work with no observable behaviour declares itself under
  `non_behavioural:` with a mandatory **reason** and deliberately no `until` — a
  classification is not an expiring debt — and a declaration that excuses nothing is itself a
  finding. `for.exclude` is rejected on this rule type, because an exclusion there carries no
  reason and is never reported. Severity `warn`. Measured on this repository: **68** findings
  — 35 feature nodes with no scenario and 33 scenarios our own PRD names that do not exist.
  See the new [BDD guide](docs/guides/bdd-scenarios.md).
- **`beadloom docs quality` — the writing standard is checkable (BDL-061 S4).** Five checks
  over a project's planning documents, all `warn`: a goal with a measurable clause, a
  decision carrying a reason, a risk carrying a mitigation, no `Pending` question inside an
  `Approved` document, and no unfilled template placeholder. The report states, per check,
  how much there was to READ, and — because that count is a global OR that goes silent as
  soon as one document carries one row — also per document KIND. Measured on this
  repository: `measurable-goal` 154 over 235, `pending-in-approved` 2 over 69, and 0 over
  269 / 138 / 243 for the other three, with **56 of 243 documents (23%) in a kind no content
  check enters** (BRIEF, PLAN, SUMMARY) while the global count read clean throughout. A
  seventh `beadloom ci` step, `docs-quality`, runs the same checks and never blocks.
- **`missing_sections` — `sync-check` compares structure, not only content (BDL-061 S4).** A
  fifth verdict, `incomplete`, reports a document that is current and no longer carries the
  sections its kind requires. The check is peer-relative by MAJORITY: a section a minority
  of a kind's documents carry is reported once against the KIND with its ratio
  (`Source (5/39)`) rather than against every document that follows the project's actual
  convention. Section names match case-insensitively, whole-word and at any heading depth.
  `incomplete` never blocks and is never written to `sync_state`.
- **Document templates compose, and a project can extend them (BDL-061 S4).** The five doc
  skeletons `beadloom docs generate` writes moved out of `doc_generator.py`'s string
  literals into `templates/docs/`, composing through the same
  `core → architecture → stack → project` assembly the role files use. A fragment at
  `.beadloom/flow/docs/<kind>.md` appends your own sections, and a section it adds becomes a
  **required** section of that kind by the same act — required sections are derived from the
  composed template rather than declared a second time. The generated bytes are unchanged.
- **The writing standard is shared by all four roles, in your language (BDL-061 S4).** It
  moved out of the `tech-writer` protocol into a shared `core:_writing` layer composed into
  `dev`, `test`, `review` and `tech-writer`, because the roles that produce intent documents
  had no standard at all. It is language-selectable like every other layer (`en` and `ru`
  ship). The role protocols also gain the BDD duty (`dev`), the mutation duty (`test`) and
  the "BDD is not ceremony" review criteria (`review`).
- **A declared mutation target is checked against the project it describes (BDL-061 S4).**
  `.beadloom/flow.yml` gains `mutation.targets`. `config-check` reports a target outside the
  configured source paths, one that is not on disk, and one holding no file in an indexed
  language — all `warn`. Beadloom runs no mutants and ships no runner: the tool is the
  project's choice, and the failure worth catching is a score computed over an empty
  denominator.
- **Flow guards — the enforcement primitive (BDL-061 S1).** `beadloom guard NAME`
  evaluates one named guard and returns a verdict
  `{guard, outcome, why, not_covered[], remediation, context}` where the outcome is
  `pass` / `warn` / `block` / `skip`. **Exit codes carry the outcome** (`0` pass/skip,
  `1` warn, `2` block, `3` usage/config error) so a shell adapter needs no parsing.
  Guards are declared in `.beadloom/flow.yml` with strictness per work kind and path
  exclusions; **an exclusion must carry both `reason` and `until`**, a guard name
  with no implementation is a configuration error rather than a silently dead gate,
  and so is **a key the loader does not read** — `option:` for `options:` used to be
  dropped in silence, leaving `working-branch` comparing against `main` and passing an
  edit made on the project's real trunk.
  Two guards ship: `bead-claimed` (an edit happens under a claimed work item) and
  `working-branch` (work happens off the protected trunk). `beadloom guard --liveness`
  reports which guards have never fired or are excluded everywhere, from an append-only
  firing record — a gate that cannot demonstrate it ran is treated as not having run.
  `beadloom setup-agentic-flow` now emits `.claude/hooks/beadloom-guard.sh`, a hook
  adapter containing **no logic**: it forwards the harness event to the CLI, so a hook
  and a shell cannot produce different verdicts. Defaults are `warn`, and a warning
  always names what it did not check, so no green project turns red on upgrade.
- **`sync-check --record-surface` and the committed surface ledger (BDL-061 S2b).** The
  declared documentation surface — the pair count and the declared-doc count — is recorded
  to `.beadloom/sync-surface.json`, which is committed and rewritten only by that explicit
  flag. A later run whose surface FELL says so by name with both numbers, instead of quietly
  printing the smaller one. `sync-check --json` gains `missing`, `unverified` and
  `declared_docs` counts, a `declared_surface` block, and a `baseline` key on every pair
  (`index` / `git:HEAD` / `none`) so a green result says what it was green against. The
  `--since` JSON shape is unchanged.
- **`docs audit` reports its own coverage (BDL-061 S2b).** Every declared fact carries
  `verified` / `not_covered` / `unreadable` with the reason, printed against the fact in the
  `Ground Truth` block and summarised on the line the Gate prints. `--json` gains `coverage`,
  `unverified_facts`, `scan_surface` and four summary counts; `--fail-if` accepts
  `unverified>N` / `unverified>=N`; `--verbose` names every document the scan did not read
  and the pattern that skipped it. Measured on this repository at the time of writing: 2 of 9
  declared facts verified, the other seven named, over 48 documents scanned and 36 not read.
- **`lint` counts what it could not check and what it excused (BDL-061 S2b).**
  `LintResult.rules_inert` qualifies the summary line (`N rules evaluated, M of them unable
  to check anything`) and `LintResult.suppressed` carries every crossing a `forbid_import`
  exemption excused, printed as `, N crossings suppressed by an exemption` on the rich, piped
  and Gate summaries and as a `suppressed` array under `--format json`. Both clauses are
  absent at zero, so the everyday line keeps its shape.
- **An environment dimension in CI (BDL-061 S2).** The scaffolded pipeline gains a
  `tests-locale` job — the same whole suite under `LC_ALL=C` and under
  `en_US.ISO-8859-1`, with `PYTHONUTF8=0` + `PYTHONCOERCECLOCALE=0` so PEP 538/540
  cannot put it back on UTF-8 — and its two check-runs join
  `DEFAULT_STATUS_CHECK_CONTEXTS`. The value is the difference between this leg and
  the UTF-8 `tests` legs, so pinning a UTF-8 locale to make it green is a change the
  suite itself rejects.

### Changed
- **An attestation covers only the documents a run had grounds for (BDL-061 `.85`, BDL-UX
  #163).** See BREAKING above for what a caller must change. What moved underneath it: a FACT
  and a CLAIM used to be one `UPDATE`. The node-level `symbols_hash` is what the index saw, so
  `attest_ref` carries it forward for every pair of the ref and `.78`'s
  `sibling_symbols_changed` verdict clears once its cause is re-baselined; `baseline_source =
  attested` is a claim about a document somebody read and is written only inside the scope.
  Both axes of the new vocabulary were decided by measurement rather than by taste —
  `domains/doc-sync/README.md` was stale against two agents' files in one run, so naming the
  document alone would have recorded a reading of a change nobody had seen, which is why
  `--code` exists beside `--pair`.
- **`scenario-coverage` states the reach of its own population (BDL-061 `.63`).** The
  population is defined by node kind, and a kind is one line in `services.yml`, so
  reclassifying a node `feature` → `component` removed it from the rule with no finding of any
  sort. Reporting the reclassification was rejected with its reason: an evaluator that
  remembered its own past population would be a writer, which is the BDL-UX #147/#189 shape.
  Widening the rule to components was rejected too — excluding plumbing is the architecture
  model's own definition, and 24 further findings is a decision nobody took. So the
  denominator is printed beside the fraction: measured on this repository at release, `42 of
  84 graph node(s) (kind=feature); the other 42 are outside it … component (30), domain (7),
  service (4), site (1)`.
- **A doc pair whose sibling file moved is `unverified`, not `stale` (BDL-061 S6, BDL-UX
  #182, #133, #105).** `symbols_hash` was stored per pair and computed per **node**, so one
  changed file marked every pair its node owned `stale/symbols_changed` and the followers
  could only be cleared by the bulk re-attestation BDL-UX #163 exists to prevent. `sync_state`
  now also carries `file_symbols_hash`, the symbol surface of a pair's own code file, and
  only that fact can make a pair stale. A follower is reported `unverified` with the new
  reason `sibling_symbols_changed`, **names the file that moved**, and is offered no
  `sync-update`, because nobody can revise it. No fifth verdict word was invented and no
  summary key was added, so `ok + stale + missing + unverified + exempt + incomplete = total`
  is untouched. Behaviour change: a project whose only finding was follower noise now exits 0
  instead of 2. Measured in two clean rooms differing only in this change: appending one
  function to `application/architecture_view.py` gave **69 stale, 67 of them naming an
  untouched file**, and now gives **2 stale plus 67 `unverified`**, each carrying the moved
  file in `details`. A row with an empty `file_symbols_hash` keeps the node-level answer, so
  an un-rebuilt index is never quieter than a rebuilt one. Three filings of one root over
  eleven weeks close together.
- **A verdict must open its comment and carry its colon (BDL-061 S6).** `review-brief
  --release` recognised the marker at a line start and nothing more, so a checkpoint reading
  `REVIEW ISSUES are still open, will fix` released the author's account — the exact string
  the code's own docstring named as the case it prevented. The marker must now be the first
  non-blank line and carry its colon. The verdict comment's author is also compared with the
  bead's assignee, and the answer is **reported, not enforced**: a self-recorded verdict
  still releases, prints why its independence cannot be established before the account rather
  than after it, and exits 1. Refusing was rejected on a measurement — where every role
  writes under one tracker identity a refusal refuses every release, and a gate nobody can
  pass is bypassed rather than obeyed.
- **The wave declaration parser fails toward serialisation (BDL-061 S6).** Every way the
  parser could be defeated widened a wave, which is the dangerous direction for a shape that
  is acted on. The declaration must now **open a line**, its list runs to the end of that line
  and splits on `,` and `;`, and a dropped word the graph confirms is a node is named rather
  than silently lost. Two new unresolved reasons — `declaration_not_at_a_line_start` and
  `declaration_dropped_a_node` — join `no_declared_refs` and `ref_not_in_graph`, each with
  its own remedy, and all four serialise the bead. Measured before the fix: `refs: wave-plan;
  sync-check` beside `refs: sync-check` gave one wave, zero findings and exit 0. One
  `compose_declaration` is now shared by `beadloom waves`, `beadloom review-brief` and the
  MCP `bead_context` tool, so the planner and the tool cannot read one bead differently.

- **`measurable-goal` re-scoped from a numeral detector to a two-leg witness test
  (BDL-061 S5).** As shipped the check looked for a digit and called its absence "no
  measurable clause" — a premise that is false, since an exit code and a named artifact are
  measurable without one. It now reports a goal only when its predicate is an **unbounded
  improvement** (`improve`, `establish`, `clean up`, `make` something *better*) AND it
  **names no witness** — no quantity, no named artifact, no observable outcome. Measured on
  this repository: **154 of 235 goal statements became 4 of 232**, and all four are in
  closed epics, which is why the remaining debt is a historical exclusion rather than a
  rewrite. `doc_quality` gains the public `names_a_witness(statement)` and
  `states_an_unbounded_improvement(statement)`; the check name, the report shapes, the CLI
  and the gate step are unchanged. Stated limit, measured: 27 of the 150 newly-accepted
  statements name no witness either, so the check now decides nothing about them —
  precision was bought with recall, deliberately.
- **`beadloom ci` gained an eighth step (BDL-061 S5).** `doc-spaces` runs between
  `docs-quality` and `config-check` and never blocks. Four states set it to **WARN** rather
  than PASS: no tracker was readable, no epic with closed beads declared a node, some epics
  declare none, and some epics the tracker does not name. Its line states both WORKING
  populations apart — `N WORKING document(s) in the exempt space, M sync pair(s) excused` —
  because one word for two populations is how a reader takes the document count as the
  excused-pair count. Anything asserting the exact step list needs the new name.
- **Every document a declared root matched is in exactly one population (BDL-061 S5).** When
  a document's kind places it in a space whose declared roots exclude it, it is now counted
  in that space and reported as `document_outside_declared_root`; it used to fall out of
  every count in silence. The invariant that holds is
  `sum(populations) == |files any declared root matched|` on any tree. Populations therefore
  grow on a project whose file stems disagree with its roots. Among kinds, and among roots,
  the WORKING space is consulted first, so a project's explicit declaration is honoured over
  a shipped default — the three shipped kind lists are disjoint, so nothing changes for a
  project that declares nothing.
- **An epic the tracker export does not name is not an epic whose beads are open
  (BDL-061 S5).** The two used to be the same empty tuple and both were skipped; only the
  second is an honest skip. Such an epic now has `bead_statuses` of `None`, is counted in
  `epics_without_bead_status`, and — when it declares a node — is reported as an
  `epic_not_in_tracker` warning. `docs spaces --json` gains `tracker_source` and
  `epics_unknown_to_tracker`.
- **`unspecified-encoding` is enforced by ruff, on three settings that travel together
  (BDL-061 S5).** `[tool.ruff.lint]` carries `preview = true`, `explicit-preview-rules =
  true` and `PLW1514` in `select`. The middle one is not optional bookkeeping: selecting a
  preview rule **without** it is not an error — ruff prints "has no effect because preview
  is not enabled" and exits 0, which is a config line that reads as a gate and checks
  nothing. `explicit-preview-rules` keeps every other preview rule out. The rule's reach was
  measured rather than read off its description: it reports `Path.read_text` only where a
  `Path` receiver can be inferred and does not look at `subprocess(text=True)` at all, so
  the receiver-agnostic AST sweep still covers `src/` and `PLW1514` adds `tests/`. This is a
  contributor-facing lint contract; no product API, CLI flag or schema moved.
- **The rules table no longer restates the loader's vocabulary (BDL-061 S4).** The
  `rules.rule_type` CHECK constraint is removed and an existing database is migrated in
  place, row for row. A `rule_type` the loader knows and the database did not used to fail
  at INSERT time with an integrity error naming nothing useful; the vocabulary now lives in
  `load_rules`, where the error message can say what is wrong. A consumer that relied on the
  database rejecting an unknown `rule_type` must rely on `load_rules` instead.
- **`beadloom prime` lists at most 10 findings of a kind (BDL-061 S4).** The COUNT is never
  truncated; only the list is, and the cut line names how many are not shown and the command
  that shows the rest. Measured: opting this repository into `scenario-coverage` (68
  findings) grew `prime`'s output from 2.6 KB to 13.1 KB, which is an agent's context budget
  spent on one rule's backlog.
- **The scaffolded branch protection declares nine required contexts, not ten (BDL-061 S4).**
  A `tests-windows` context was added and withdrawn while this cycle was unreleased, so no
  released version ever carried it. **Windows is unverified by decision**: the leg was
  measured at ~16-28 runner-minutes per pull request and, unlike the two `tests-locale` rows,
  it becomes the pipeline's critical path and roughly triples PR-to-merge latency, for a
  platform outside this project's audience. What the withdrawn leg taught did not leave with
  it — six guard tests that used to skip on `sys.platform == "win32"` now run wherever the
  process can genuinely create a symbolic link, decided by a probe that creates a file link
  AND a directory link and reads both back.
- **`beadloom ci` gained a seventh step (BDL-061 S4).** `docs-quality` runs between
  `docs-audit` and `config-check`. It never blocks. It reports **WARN** rather than PASS when
  a check read nothing anywhere, when a document kind no content check enters, or when a
  document could not be decoded. Anything asserting the exact step list needs the new name.
- **`config-check` carries the mutation-scope findings (BDL-061 S4).** They are computed
  before the step's database guard, because a declaration is checkable against the tree
  whether or not the index was built.
- **`config-check` verifies the composition result, not file bytes (BDL-061 S3).** Byte-guarding
  a generated file against a fixed template makes extension impossible: any project addition is
  drift and `--fix` deletes it. The check now compares each artifact against its composition,
  so a project fragment is part of the expected output while a change to a shipped fragment
  still is not. **Before this, the `CLAUDE.md` body was verified by nothing** — measured on a
  scaffolded project, replacing the whole file with a single line returned zero drifts and the
  Gate printed `config-check PASS: agent-config in sync` (BDL-UX #177). Severity follows the
  state: `stale`, `hand_edited` and `missing` are errors, `unverified` is a warning, and the
  command exits 1 only on error-severity drift. `--fix` runs the scaffold's **non-forcing**
  path for the commands and `CLAUDE.md`, so a hand edit there is no longer deleted (BDL-UX
  #151). Two limits are stated rather than omitted: a project fragment's **prose is not
  judged** — only its presence is reported, at `warn`, with each fragment named — and deleting
  both the manifest and the provenance stamp downgrades the `CLAUDE.md` body from `error` to
  `warn`, because every ownership signal is in band and can therefore be deleted. The
  achievable floor is that the deletion is visible and the file is named, not that it blocks.
- **Nothing an editor deletes makes `config-check` quieter (BDL-061 S3).** Three deletions used
  to reduce the finding count. `rm .beadloom/flow-manifest.json` took a hand-edited `CLAUDE.md`
  from error to warn (exit 1 → 0); deleting the `<!-- beadloom:composed` stamp as well took it
  to zero findings; `rm .claude/agents/dev.md` switched the checks off for every other file,
  silently. All are findings now, and the absent manifest, the missing canonical file and the
  project layer in effect are each reported by name.
- **A composed artifact is a function of its inputs and of nothing else (BDL-061 S3).**
  `FlowSuppression.describe()` no longer stamps `— EXPIRED` into the composed text; expiry is
  a `config-check` finding instead. Measured before the change: one dated suppression took an
  untouched repository from 0 findings / exit 0 to **9 errors / exit 1** three days later, with
  nothing on disk touched, under a reason that named three causes which had not occurred. A
  project with an already-expired dated suppression composes different bytes than before and
  adopts them on one `beadloom setup-agentic-flow`.
- **`sync_agentic_flow` no longer snapshots `CLAUDE.md` or the slash commands (BDL-061 S3).**
  The shipped core is authored package data and the live file is composed from it. Enforcing
  *template equals our file* in one direction made the distributed artifact unable to differ
  from this project's local text — a bead id and a false claim about this repository's branch
  protection reached the shipped template twice, the second time over the correction (BDL-UX
  #177). It also removes BDL-UX #132 by construction: nothing writes the core, so `--force`
  cannot overwrite its project-name placeholder.
- **The freshness baseline moved out of the database (BDL-061 S2b).**
  `.beadloom/beadloom.db` is a derived cache again — git-ignored, per-machine, dropped by
  every rebuild and absent on every fresh CI checkout — so a baseline kept only there is
  destroyed by the act that most needs it. Freshness now rests on **git**: each `sync_state`
  row records a `baseline_source` (`index_build` / `carried` / `attested`) which is carried
  verbatim across a reindex and never promoted, and a baseline fabricated at index-build time
  that would otherwise read `ok` is corroborated against `HEAD`. The declared surface rests on
  the committed ledger above. **If you have scripted `rm .beadloom/beadloom.db && beadloom
  reindex` to reach a green `sync-check`, it no longer works, and that is the point** — the
  instruction to verify on a clean database was retired in S2 for the same reason. A clean
  database is still the right instrument for `lint`.
- **`sync-check` has four verdicts, and `beadloom ci` has four outcomes (BDL-061 S2b).**
  `ok` / `stale` / `missing` / `unverified`. `missing` — a doc file, a code file, or a doc the
  graph DECLARES that is not on disk — exits 2 and fails the Gate, because the Gate is not
  satisfied by having less to check. `unverified` means nothing could be compared: it is
  printed by name, counted separately, never counted as fresh, and the Gate step prints
  `WARN` with the exit code unchanged, so no adopter goes red on upgrade. `min_doc_coverage`
  counts pairs not known to be behind, so an unverified pair cannot turn a green project red.
- **`doctor` counts the checks that ran, not the findings (BDL-061 S2b).** `run_checks`
  returns one entry per finding, so `N check(s) clean` was counting problems — it rose from 20
  to 21 while a file was being deleted, and included nine warnings and one *not verified*. The
  summary now reads `N check(s): E error(s), W warning(s), I info` over distinct check names,
  and the word *clean* appears only when every check is OK (13 checks on this repository).
- **A guard that cannot answer now blocks (BDL-061 S2).** Through `--hook`, the
  configuration/usage class (an unparseable `guards:` block, an exclusion missing
  `reason` or `until`, an unregistered guard name, an unsupported harness) exits `2`
  — the code the harness reads as "stop" — instead of `3`, which the harness read as
  "proceed". From a shell the distinction survives: `3` still means "your declared
  configuration is broken" and is separate from Click's own usage exit.
- **`beadloom lint` says which form writes the index.** The default reindexes first
  and therefore writes `beadloom.db`, by design, so it never lints a stale graph;
  `--no-reindex` is the read-only form and now refuses a missing index at exit `2`
  instead of creating one. Plain `lint` also names on stderr that its exit code stays
  `0` over error-severity violations without `--strict`; the exit code is deliberately
  unchanged so no adopter's pipeline turns red on upgrade.

### Fixed
- **A document that SHOWS the `watches` syntax opted itself into surface drift (BDL-061
  `.86`).** `parse_watches` searched the whole text, so four documents were enrolled in a check
  none of them asked for: a CHANGELOG entry describing the feature, two SPECs mentioning it in
  a sentence, and the code-indexer SPEC's fenced example whose own caption reads *also an
  example: not read*. A declaration must now open a line and sit outside a fenced block, and
  what position cannot decide is stated rather than hidden. `docs/services/cli.md` was enrolled
  the same way and genuinely wants the watch, so it declares one in its header; the other three
  leave the reference population. Measured: reference documents 12 → 9, unattestable
  `surface_drift` entries 1 → 0.
- **The `reference` leg read two forms as claims (BDL-061 `.62`).** `Example:` and `Пример:`
  are Gherkin keywords and ordinary words at the same time, so a bare line opening with one now
  needs the author's own mark — a bullet, a quote or backticks — before it is read as a claim
  that a scenario exists. An indented block is markdown's other code syntax and is skipped like
  a fence, unless the line opens with a list or quote marker. Measured: 33 references before
  the change and 33 after. A document that cannot be DECODED is now reported with its reason
  instead of contributing nothing — `load_references` returns a `ReferenceSet` carrying
  `unreadable` beside `dead_globs`, and `scenario-coverage` reports each one.
- **`beadloom active-sync` was inert on the repository that authored it (BDL-061 `.84`).** Four
  faults kept it that way. The lookup compared a full tracker id against a table written in
  short form, so it matched no row and printed `already coherent` over a comparison of zero.
  The scan gave up at the first `Bead`-headed table, and this epic's own `ACTIVE.md` carries a
  deferral table 480 lines above its status table. `bd list --json` returns open beads capped
  at 50 rows — 41 of this repository's 709, every closed one missing — so `✓ done` could never
  be written; the query now asks for `--all -n 0`. And a short id is resolved against the
  epic's own tracker prefix, because eight beads here are numbered `.17` and the first working
  run resolved this epic's `.17`–`.24` rows onto another epic's beads. A run now states how
  many rows it RESOLVED out of how many it read, names every row it could not resolve with a
  reason, and `--check` exits 1 when it resolved none. `Done`, `✓ done` and `**DONE**
  (a1b2c3d)` are compared as one state, so a first working run corrects drift instead of
  rewriting 78 rows to add a checkmark. The first working run: 191 of 283 rows resolved, **56
  rows corrected across 12 `ACTIVE.md` files**, 92 rows named as resolving to no bead — two of
  the corrections being beads closed in the tracker and still reading `Pending` and `Open` in
  the epic's own table.
- **One undecodable planning document no longer takes the whole `beadloom ci` gate down
  (BDL-061 S4).** `check_documents` caught `OSError` and `read_text(encoding="utf-8")` raises
  `UnicodeDecodeError`, which is a `ValueError`. Measured: a single cp1251 document under the
  default globs took `beadloom docs quality` to exit 1 with a traceback and no JSON, and
  `beadloom ci` with it — losing the reindex, lint, sync-check and docs-audit results of that
  run, because the step list is built eagerly. The handler is now as wide as what the call can
  raise, the document is COUNTED, and it carries a named `unreadable` finding with its reason:
  a document nobody could read is unverified, never silently absent. The same one-line class
  was fixed in `doc_shape` (reported as `unverified` / `unreadable` and left out of the
  majority denominator) and in an unguarded read one phase earlier in `engine.check_sync`.
- **`rules_inert` now counts the tenth rule type (BDL-061 S4).** `13 rules evaluated, 0 inert`
  printed over a `scenario_coverage` rule that had stood all four of its legs down. The count
  asks the rule's own `inert_reason` predicate — one fact, one source — and the generic
  liveness pass skips the type so the same fact is not affirmed twice.
- **The `scenario_coverage` deliberate-silence note said one leg where the code skips four
  (BDL-061 S4).** A `features` glob matching no file stands the whole rule down, not the
  coverage leg alone. Measured: repointing `features:` at a directory that does not exist
  takes this repository's lint from 68 findings to exactly 1, and that 1 is the liveness
  finding naming the dead glob.
- **A live `non_behavioural` declaration was silent (BDL-061 S4).** Excused nodes left the
  population, the coverage fraction improved and nothing said the denominator had moved. A run
  that excuses anything now states `N of M node(s) … are excused …, so every coverage figure
  below is a fraction of M-N`, naming each node and its reason. Silent at zero, always `warn`.
- **A whole document kind no check entered was invisible (BDL-061 S4).**
  `checks_that_read_nothing` is a global OR over the corpus and goes permanently silent the
  moment one document carries one row, so it could detect a check blind everywhere and not one
  blind on an entire shipped document kind. `docs quality` and the gate step now report
  applicability per KIND. Measured on this repository: 56 of 243 documents are in a kind no
  content check enters, while the global count read `()` throughout.
- **Five documentation-only staleness classes carried over from BDL-061 S3 are closed
  (BDL-061 S4).** BDL-UX #183, #186, #187, #188 and #189 were listed as known limitations of
  S3 while this cycle was unreleased and are fixed within this release. (Two entries in the
  issue log carry the number 187; the one closed here is the `setup-agentic-flow` scaffold
  leaving `config-check` red, not the `bd list --json` item under Known limitations below.)
- **Five states that read as a pass because nothing could check them (BDL-061 S2b).** One
  sentence, four fixes: *unverifiable is not clean*. A **deleted declared document** left the
  Gate green — the reindex that followed simply removed its pairs, so there was nothing left to
  miss; declarations are now cached from the committed graph YAML in a `declared_docs` table
  and survive the file they name (#174). A **rebuilt index** stored the current tree as its own
  baseline and reported every pair fresh, which made the CI gate structurally blind on every
  fresh checkout rather than only when someone typed `rm` (#175). A **rule that cannot match
  anything** counted toward `N rules evaluated, 0 violations`; all nine rule types now report
  their own inertness — a matcher selecting no node, an edge kind the graph does not have, a
  `check` with no threshold, a `source_root` with no module (#172). An **exemption whose
  `until:` has passed** kept suppressing in silence; a passed ISO deadline on an entry that is
  still suppressing something is a finding, the same deadline grammar is shared with the flow
  guards' exclusions so `flow.yml` and `rules.yml` cannot promise different things, and expiry
  never changes what is suppressed — a build reddening because a calendar day passed has no
  commit behind it. And a **fact the audit never checked** was invisible behind a count of what
  it did find (#173). Every one of these is reported at `warn` unless something in the tree is
  actually wrong, so a green project stays green on upgrade; `--fail-on-warn` and
  `docs audit --fail-if unverified>N` are the levers for a project that wants them enforced.
- **Three checks that reported green over work they had not done (BDL-061 S2).**
  An incremental `reindex` now re-extracts imports for the code files it touched,
  drops those of files that disappeared and rebuilds the derived `depends_on` set
  (marked `extra.derived='imports'`, so a graph-declared edge is never collateral
  damage) — a boundary violation introduced between two incremental runs is caught
  without a full rebuild. `sync-check` builds pairs for **any** node that declares
  `docs:`, falling back to the files its `source:` owns when annotations yield none,
  and names whatever is still uncovered with a reason instead of printing nothing
  (275 of 279 declared pairs checked on this repository, 4 named). `lint` without a
  reindex opens the index read-only and refuses a missing one, where it used to
  create an empty database and report `0 violations` against it.
- **Two lint rules could never match (#172).** `from:` is compared against the
  indexed source path and `to:` against the dotted import path, so a `to:` written
  `src/pkg/**` matched nothing, ever — and the rules reference taught that form. Both
  vocabularies are now stated in the reference, a `to:` covering a package also covers
  a bare import of it, and a glob matching zero candidates anywhere in the index is
  reported as a `rule_liveness` warning, as is an exemption that suppresses nothing.
  `forbid_import` gains `exempt[]` entries, each of which must carry `reason` and
  `until`.
- **The Gate's own instruments on a non-UTF-8 image.** `sync-check --since`,
  `diff --since`, the contributor activity read and the federation export decoded the
  two sides of a comparison by different rules — the current file explicitly as UTF-8,
  the other side with whatever the image's locale said — so an ambient `latin-1`
  reported drift in an untouched file and an ambient `ascii` raised out of a command
  that runs inside `beadloom ci`. Each site now decodes both sides through one stated
  codec. The digest of a valid UTF-8 file is unchanged, so no stored baseline moves.
- **`bd` and `git` probes.** Both subprocess seams state their codec instead of
  inheriting the ambient locale, and `bd` failing for any reason — missing, not
  executable, wedged past its timeout, undecodable — is now a `skip` that says why
  rather than an error that blocks the edit.
- **`docs audit` read numbers out of identifiers (#169).** A line is tokenized on
  whitespace and only a token whose whole core is a number is a candidate, so
  `BDL-061.33` is no longer an `mcp_tool_count` of 33 and `6,390` is read whole.
- **`config-check --fix` may only rewrite what Beadloom wrote (BDL-UX #186).** The role
  adapters were the one kind left out: `refresh_composed_adapters` rewrote
  `.claude/agents/<role>.md` unconditionally, so doing what the command's own closing line
  said undid what the line above it promised, and the re-check then printed *Agent-config in
  sync — no blocking drift* at exit 0 over the deletion. An adapter Beadloom cannot prove it
  wrote — `hand_edited`, and `unverified` too, which is the worse case because it is only a
  warning — is now **declined**: left byte-identical, named in the output, its finding still
  standing. Every file a `--fix` run creates or rewrites is named, measured against the disk
  rather than taken from each writer's account of itself, and the closing advice stops
  offering `--fix` for a finding it will decline.

### Known limitations

Measured and open at release, listed here rather than left to be discovered. **Seventeen beads of
this epic are open in the tracker** (counted with `bd list --status open --json`, excluding the
epic row and the swarm placeholder); the nine below are the ones an adopter will meet.
Three limitations this section carried while the cycle was unreleased — the `incomplete`
verdict having no `--json` counter, the `measurable-goal` numeral detector, and the reference
leg reading a line rather than a sentence — are fixed above, inside this same cycle.

- **A virgin `beadloom init` leaves `beadloom ci` red (BDL-UX #192, filed by this release's own
  artifact verification).** Measured on the built 3.0.0 wheel in a fresh virtual environment,
  against a scratch TypeScript project with one file under `src/`: `beadloom init --yes --mode
  bootstrap` exits 0 and writes a graph of 2 nodes and **0 edges**, then `beadloom lint
  --strict` exits 1 with `domain-needs-parent:require:error:::src:` and `beadloom ci` exits 1.
  The two halves of one command disagree — the classifier writes a `src` node of kind `domain`
  and no edges at all, while the rule generator writes `domain-needs-parent` whenever any node
  is a domain. It is not new in 3.0.0; it had never been measured, because everything this
  project measures runs on this project, whose graph has been hand-authored since BDL-008.
  **Remedy until it is fixed:** add the edge by hand — an `edges:` entry `{src: <domain>, dst:
  <root ref_id>, kind: part_of}` in `.beadloom/_graph/services.yml` — and run `beadloom
  reindex`. Plain `beadloom lint` (without `--strict`) exits 0 throughout, so a pipeline that
  has not adopted the Gate is unaffected.
- **`bd list --json` returns a filtered view as a bare list, and nothing says it filtered
  (BDL-UX #187 of 2026-08-25 — External, `steveyegge/beads`).** Measured while fixing `beadloom active-sync`:
  the default returns 38 rows of this repository's 709 with zero closed beads, while
  `--status closed` returns 50, and the payload is a bare JSON array with no envelope — so
  there is nowhere for the tool to say a filter was applied, and nothing does. A consumer
  cannot tell a complete answer from a partial one, and the partial one looks complete.
  Beadloom's own reads now ask for `--all -n 0`; **a project scripting `bd list --json` must do
  the same**, and any count computed from the default is a count of the first page.
- **`beadloom setup-agentic-flow` recomposes a hand-edited role adapter without asking (BDL-UX
  #191), which is the command an upgrader runs.** `config-check --fix` learned one rule in this
  release — rewrite only what Beadloom can prove it wrote — and declines a hand-edited
  `.claude/agents/<role>.md`. The scaffold did not learn it: `setup-agentic-flow` calls
  `generate_adapters(config, project_root)` with no `preserve=`, so the same hand edit `--fix`
  declines is overwritten by the command `--fix`'s own remediation points at. It is recorded as
  undecided rather than as a defect with an obvious fix, because the two commands have
  genuinely different contracts — a repair must not destroy, while a scaffold may reasonably
  reinstate the shipped flow — and nothing today states which is intended for the third
  artifact kind. **Until it is decided: copy any hand-edited role adapter aside before you
  re-scaffold**, or keep your additions in the project layer under `.beadloom/flow/roles/`,
  which is appended verbatim and never overwritten.
- **The commit gate cannot see a neighbour's hunk inside a file the committer owns
  (`beadloom-mr2l.81`).** `sync-check --staged` judges the paths a commit stages, so work
  swept in from a shared working tree — inside a file the committer legitimately touches,
  because `git add -p` is not available to an agent — is *inside* the region the gate judges.
  Measured: `not_checked_outside_commit` reads 0 and the file is named as staged, so the hook
  prints a confident "0 file(s) outside this commit were not judged" over a commit carrying
  someone else's work. Nothing the hook can read distinguishes the two, because the index does
  not record who wrote a line. The mechanism that would catch it — comparing the staged paths
  against the scope the committing bead declared — needs four decisions taken first, starting
  with how the hook learns whose bead is committing.
- **The commit-scoped hook type-checks a surface the project never declared typed
  (`beadloom-mr2l.82`).** Its mypy leg runs over the staged `src/` **and** `tests/` files,
  while this project's declared type surface, its `pyproject.toml` strictness and its CI are
  `src/` alone. Measured on the commit that exposed it: eight mypy errors in two files, all
  eight pre-existing and reproducing byte for byte on the previous revision, printed over a
  commit that introduced none of them. So the hook holds `tests/` to a standard the Gate does
  not enforce and will warn on nearly every commit that touches a test — and a warning nobody
  is expected to act on is how the next warning gets read. The leg is `warn` in the default
  mode and blocks nothing; **under `--mode block` it blocks**, which is what raises this for an
  adopter who installed the blocking hook.
- **Windows is unverified by decision (`beadloom-mr2l.60`).** The product carries zero
  `sys.platform` and zero `os.name` branches, so it is either genuinely portable or has never
  been asked, and an all-green Linux pipeline cannot tell those apart. A Windows CI leg was
  built and withdrawn on measured cost (~16-28 runner-minutes per pull request, and the
  pipeline's critical path), so the Windows verdict for the flow guards is composed from
  `ntpath` plus a refusal proved branchless rather than measured on a runner — and the known
  defect it points at, a backslash refusal that would refuse every edit on a Windows harness,
  is pinned as a strict `xfail` rather than fixed. **Nothing here claims Windows support.**
- **`measurable-goal` bought precision with recall, and its historical debt is unpaid
  (`beadloom-mr2l.71`).** The re-scope above took this repository from 154 findings of 235
  goal statements to **4 of 232**, measured. The stated cost: 27 of the 150 newly-accepted
  statements name no witness either, so the check now decides nothing about them. And the four
  that remain are all in closed epics, whose goals cannot be made measurable retroactively —
  the historical exclusion that would resolve them is a design decision that has not been
  taken, so the four stand as findings.
- **56 of 243 planning documents (23%) are in a kind none of the four content checks enters** —
  BRIEF (11), PLAN (42) and SUMMARY (3), measured at release — because the shipped templates
  for those kinds carry no Goal section, no Reason column, no Risks and no Open Questions, and
  BRIEF is the kind every `bug`, `task` and `chore` uses. Whether to give those templates the
  rows or to place those kinds outside the four checks is a product decision with a migration
  behind it, and **it has not been taken**. What changed in this release is that the state is
  printed rather than inferred.
- **`scenario-coverage` checks that a scenario NAMES a bead, never that the bead exists.**
  Reading the tracker from the rule engine would make a domain depend on the application layer.
  The limit travels on the findings that would otherwise imply otherwise. Only structure is
  parsed, so a scenario that binds correctly and asserts nothing counts as coverage — whether
  its assertions would notice a defect is the mutation duty's question, not this rule's.

## [2.2.0] - 2026-08-20

**Interactive architecture + a graph that stops lying.** The portal renders both the
repository's architecture and the cross-service landscape as interactive graphs — and
dogfooding that view exposed four defects in how the graph was built, each of which made
it report something untrue with a straight face. Those are fixed at the root.

**Requires `mcp >= 2.0`** — breaking by dependency, not by API.

### Added
- **Interactive architecture and landscape views (BDL-060 S4).** `beadloom docs site`
  now renders both the repository's own architecture and the cross-service landscape
  as Cytoscape + ELK graphs, each fed by a deterministic `public/*.data.json`
  artifact, with the previous Mermaid versions kept as `*-diagram.md` fallbacks.
  Domains are compound boxes holding their features and components; nodes sit in
  canonical layer lanes, so a healthy dependency points down and one that points up
  or cross-cuts is drawn as a layering concern. Clicking a node opens its card
  (kind, summary, layer, symbol count, doc freshness, lint status, dependency lists,
  documentation links) and highlights its blast radius; clicking a landscape edge
  opens the contract behind it — protocol, routing identity, producer and consumer,
  verdict, and the GraphQL field surface or AMQP JSON-Schema body, rendering
  `undeclared` rather than an empty-looking success when a surface was never
  declared. Filters narrow by kind, domain, layer, protocol and health.
- **Declared runtime coupling reaches the architecture view.** A `uses` edge — a
  component that shells out to the published CLI, or one that reads a file another
  writes — is coupling no import analysis can see, so it is authored in the graph.
  Nodes now carry `uses` / `used_by` beside their import lists, kept separate and
  drawn dotted, and never flagged as a layering concern: crossing a process boundary
  to call a published interface is not the same as binding to a module at import
  time. The view previously discarded these edges entirely, so authored
  architectural intent already in the graph never reached the picture.
- **Atomic graph-YAML writes (BDL-060 S1).** Every write to `.beadloom/_graph/*.yml`
  goes through `write_yaml_atomic`, so an interrupted command can no longer leave a
  half-written graph behind.
- **Typed GraphQL contract surface (BDL-060 S2).** Tier-A extraction of field types,
  nullability/list wrapping, arguments and subscriptions, with a native breaking-change
  verdict. `graphql-core` is optional: without it the scanner falls back to the honest
  name-level surface rather than pretending to type information it does not have.
- **AMQP message-body contracts (BDL-060 S3).** JSON-Schema bodies with a native
  body-diff verdict, plus optional AsyncAPI ingestion.

### Changed
- **Requires `mcp >= 2.0`.** The MCP server was migrated to the 2.0 low-level API:
  handlers are supplied at construction (`Server(on_list_tools=…, on_call_tool=…)`)
  rather than through the 1.x `@server.list_tools()` decorators, results are protocol
  models (`ListToolsResult` / `CallToolResult`), and `Tool.inputSchema` is now
  `input_schema`. Because 2.0 no longer wraps handler exceptions, the server classifies
  dispatch failures itself — an unknown tool or missing `ref_id` comes back as
  `CallToolResult(is_error=True)` with a correctable message instead of a protocol error.
- **The TUI dashboard paints immediately.** The debt score and git activity moved to a
  background worker with their own SQLite connection; the gauge shows `Debt: computing…`
  and the activity panel `Analyzing git history…` until real values arrive, instead of
  holding a blank terminal for seconds on a large repository.
- **Test mapping walks the project once.** `map_tests` replaced a recursive glob per
  framework pattern with a single pruned walk that skips dependency, VCS, cache and build
  trees (`node_modules`, `.venv`, `vendor`, `.git`, `dist`, `build`, …) — those hold no
  first-party tests and could previously be attributed to project nodes.
- **Dependency refresh.** mypy 1.19→2.3, textual 7.5→8.2, rich 14→15, ruff 0.15→0.16,
  pytest 9.0→9.1; site: echarts 5→6 with vue-echarts 7→8, elkjs 0.9→0.12,
  cytoscape 3.30→3.34, mermaid 11.4→11.17.

### Fixed
- **Symbols and dependencies were attributed by raw path prefix (BDL-UX #144, #157).**
  A node's `source` is a prefix and graphs nest, so a child's files counted against
  its parent too — which is why carving a subpackage into its own node never
  relieved the parent, the very remedy a size limit exists to prompt. A source
  naming a package's `__init__.py` was read as a lone file, so five nodes reported
  **0 symbols** while their packages held 228. Both had one root and are fixed once:
  a file belongs to exactly one node — the most specific whose `source` covers it —
  shared by `max_symbols`, `max_files`, the architecture view, node pages and import
  attribution, so no two surfaces can disagree. That unanimity of five wrong readers
  is exactly what kept it invisible. Measured here: `application` 284 → 150, `graph`
  257 → 61. `domain-size-limit` is recalibrated 290 → 180 as a consequence of the
  metric changing meaning, with the signal the new one does not carry (bounded-context
  size by subtree) filed as #158 rather than folded into the threshold.
- **An import resolved to the enclosing directory's node, not the file's owner.**
  Target resolution converted a dotted path to an extension-less directory path, which
  can never match a node whose source is a file — so feature- and component-level
  dependencies were collapsed into their domain.
- **Imports below a file's top level were never extracted (BDL-UX #159).** All nine
  language extractors walked only the module's top-level statements, so an import
  inside a function, a class body, an `if TYPE_CHECKING:` guard or a `try:` block was
  invisible — precisely where an import is placed to defer cost or to break a cycle.
  On this repository that hid **460 nested imports, 231 of them first-party**, about a
  third of the total, leaving `no-dependency-cycles` and `forbid_import` blind to the
  edges they exist to judge. Making them visible surfaced six real boundary violations
  at once, all one pattern: domain and application code reaching up into `services` to
  introspect the live CLI surface. Fixed by inverting that through a new
  `infrastructure/surface_registry` port whose contract is **unknown is not zero** — a
  surface nobody provided reports "not verified", never a plausible count.
- **The architecture view discarded every declared `uses` edge**, so authored
  architectural intent already present in the graph never reached the picture.

  Together these took the dependency graph from 14 to 156 derived edges. Every node
  still reporting no dependency was then audited and cross-checked independently:
  all explained, none unexplained.
- **A fresh install could segfault mid-reindex (BDL-UX #150).** `tree-sitter` carried no
  upper bound, so a new install paired a newer core with grammar wheels built against an
  older ABI — grammar wheels only declare their core requirement under a `core` extra that
  a normal install never activates. The pairing survives loading and small parses and
  crashes partway through a real repo-wide reindex, which is how it reached users without
  tripping a gate. Pinned `tree-sitter>=0.25,<0.26`, and `tests/test_grammar_guard.py` now
  fails both if the pin loses its ceiling and if the environment running the suite falls
  outside the declared range.

## [2.1.0] - 2026-06-15

**Reference-documentation freshness + positioning refresh.** A minor, backward-compatible
release: Beadloom now guards the freshness of overview/reference docs (READMEs, guides)
that aren't paired to a code symbol, and the public docs lead with the data-core positioning.

### Added
- **`docs audit` in the Gate (BDL-057).** `beadloom docs audit` is promoted out of
  `[experimental]` and runs inside `beadloom ci` as a blocking step (fails on `stale>0`):
  stale numeric/version facts in prose (version, node/edge counts, MCP-tool/CLI-command
  counts) are caught before merge.
- **`reference` doc kind with `watches:` (BDL-057).** A doc opts in with
  `<!-- beadloom:watches=cli,graph,flow.yml -->`; `sync-check` computes a coarse aggregate
  hash over the watched surface and reports an advisory `surface_drift` (warn-only — never
  blocks), cleared by `sync-update`. New `reference_state` table; the symbol-pair
  `sync_state` logic and the reason-masking/fixpoint invariant are untouched.
- **`docs_audit.ignore` config key (BDL-057).** Targeted suppression of false-positive fact
  matches in `.beadloom/config.yml` (`{path, fact, value}` triples) plus per-fact tolerances.
- The multi-agent development process is now documented bilingually at
  `docs/guides/multi-agent-development.md` (+ `.ru`), on the VitePress portal.

### Changed
- **Positioning (BDL-056).** README (en/ru) rewritten to "the source of truth about your
  code — its architecture, contracts, and documentation," with a single Gate enforcing it
  the same way for people and agents.
- **Writing-quality standard** added to the CORE tech-writer role, so documentation quality
  is reproducible by the agent rather than ad hoc.
- The 11 remaining skeleton SPECs are filled with code-accurate prose.
- Doc fixes: `getting-started` drops the non-existent `--non-interactive` flag; the
  architecture domain count is corrected; `CONTRIBUTING` gains a release-process section.

### Removed
- The generated VitePress `site/` content tree is **no longer committed** — it is regenerated
  by CI and the deploy workflow (`beadloom docs site`). Only the hand-authored shell
  (`.vitepress/config.mjs`, `.vitepress/theme/**`, `package*.json`) stays tracked.
- The accidentally-committed team presentation deck (`docs/presentations/`).

Backward-compatible (MINOR): repositories without `watches` annotations and with
audit-clean docs are unaffected; `reference_state` ships with a migration guard.

## [2.0.0] - 2026-06-14

**Beadloom 2.0 — the self-governing, configurable, tool-agnostic agentic dev loop.**
A major release consolidating BDL-049/050/051/053/052. Headline: Beadloom now
applies its own architecture-as-code thesis to itself (no shadow code, no stale
docs — enforced by deterministic gates), and the packaged multi-agent flow is
configurable per stack/architecture/tool (Claude Code + Cursor).

**Breaking changes (why MAJOR):**
- The AI tech-writer harness moved `tools.ai_techwriter` → `beadloom.ai_agents.ai_techwriter`
  (invoke `python -m beadloom.ai_agents.ai_techwriter`); the BDL-047/048 Python
  vendoring in `setup-ai-techwriter` is retired (harness ships in the wheel).
- `module-coverage` lint promoted to `severity: error` — a repo with an
  unclassified `src` module now fails `beadloom ci` (previously a warning).
- `setup-agentic-flow` role files are now composer-owned (generated from
  `.beadloom/flow.yml`); hand-edits are recomposed.

Phase "Usable doc-flow + role configurator" (BDL-052): makes the packaged
multi-agent flow **tool- and stack-agnostic** and adds a **local-primary**
enforcement layer. (S1) a blocking **pre-push Beadloom Gate** hook runs the full
`beadloom ci` on every push and blocks on red (`git push --no-verify` is the
documented escape hatch), with the coordinator Gate-loop + explicit parallelism.
(S2) restored + modernized the CORE `dev`/`test`/`review`/`tech-writer` role
protocols. (S3) the **role configurator**: a repo declares `.beadloom/flow.yml`
(`architecture: ddd|fsd` + `stack` + `tools` + `quality`) and Beadloom **composes**
each role from CORE + the selected architecture overlay + stack overlays, then
writes a per-tool **adapter set** — `.claude/agents/*` for Claude Code and
`.cursor/agents/*` (+ a Cursor orchestrator pointer) for Cursor — at parity;
`config-check` byte-guards every composed adapter against `compose_role(...)`.
(S4) **symbol-level scope** for the AI tech-writer: a changed file no longer
fans out to every linked doc — a doc is rewritten only when it references a
symbol whose body changed (unioning new-side edits AND old-side removed/renamed
defs so a doc naming a deleted symbol is still KEPT), conservative when
attribution is unavailable. (S5) the CI `ai-techwriter` job runs per-doc repair
in a **bounded parallel session pool** (`HarnessConfig.max_parallel`, default 3)
with per-session 429/5xx **exponential back-off** and a uv-dependency + Beadloom-
index **cache** (behaviour unchanged vs sequential; folded in stale order so the
verdict is identical). (S6) `beadloom active-sync --stage` (restage the touched
files). Result: local authoring is tool-agnostic and Gate-enforced, CI is the
fallback/true enforcement, and the same canonical flow runs on Claude Code +
Cursor.

### Added (BDL-052)
- **Pre-push Beadloom Gate** — `beadloom install-hooks --pre-push` installs a hook that runs `beadloom ci` (reindex → `lint --strict` → sync-check → config-check → doctor) and blocks the push on red; fail-safe (no-op without `beadloom` on `PATH`); `git push --no-verify` overrides
- **`.beadloom/flow.yml` + `flow_config.py`** — `FlowConfig` (frozen) + `build_flow_config` / `load_flow_config` / `load_flow_config_or_default` / `resolve_flow_config` (flag → flow.yml → default) + `detect_stack`; strict validation naming the bad value + allowed set (`FlowConfigError`). Supported: tools `claude`/`cursor`; architecture `ddd`/`fsd` (exactly one); stack `python`/`fastapi`/`javascript`/`typescript`/`vuejs`
- **`role_composer.py`** — `compose_role(role, *, architecture, stack)` = CORE + one architecture overlay + sorted stack overlays (byte-deterministic); `compose_all_roles`; FSD at parity with DDD
- **`role_adapters.py`** — `generate_adapters(config, project_root)` writes the per-tool adapter set(s) (`claude` → `.claude/agents/*`; `cursor` → `.cursor/agents/*` + `.cursor/rules/beadloom-flow.md`); the single writer the drift-guard verifies against
- **`beadloom setup-agentic-flow --tool/--architecture/--stack`** — compose + write the configured adapters (defaults `claude`/`ddd`/auto-detected); `config-check`/`--fix` validate `flow.yml` and recompose drifted adapters (`_composed_adapter_drifts` / `refresh_composed_adapters`)
- **AI tech-writer symbol scope** (`ai_techwriter/symbol_scope.py`) — narrows the stale set to docs that reference a changed symbol (git hunks ∩ Python `def`/`class` ranges, both diff sides); an empty intersection drops AND baselines the pair so `sync-check` still reaches 0
- **AI tech-writer bounded parallel + back-off** (`ai_techwriter/runner.py` pool keyed on `HarnessConfig.max_parallel` default 3; `ai_techwriter/backoff.py` `RateLimitError`/`retry_with_backoff`) + CI uv-dep + index caches
- **`beadloom active-sync --stage`** — restage the touched `ACTIVE.md` + `.beads/issues.jsonl`

### Known limitations (BDL-052)
- **Orphaned adapters not drift-guarded.** `config-check`'s composed-adapter check iterates only the tools named in `.beadloom/flow.yml`. If a tool is dropped from a narrowed `flow.yml`, the previously-scaffolded adapter set (e.g. `.cursor/agents/*`) is left un-checked and un-recomposed. A follow-up bead tracks an orphaned-adapter lint; until then, remove a dropped tool's adapter directory by hand.

Phase "Tracker / ACTIVE coherence hook" (BDL-053): makes each epic's `ACTIVE.md`
bead-status table **correct by construction** instead of by coordinator
discipline. New `beadloom active-sync` reconciles every epic's table FROM `bd`
(the source of truth) — rewriting each Status cell to match the bead's `bd`
status while preserving a richer coordinator note when its state agrees — and
re-exports the tracked `.beads/issues.jsonl`. It is wired into the pre-commit hook
(both `warn` and `block` templates) as a **guarded auto-fix step** that restages
the touched `ACTIVE.md` + jsonl so every commit is coherent. The reconcile core
(`application/active_table.py`) is the SAME tolerant, fail-safe parser the MCP S4
`checkpoint` / `complete_bead` tools use for single-row updates. **Safe no-op by
construction:** with no `ACTIVE.md` table, no `bd`, or an untracked jsonl, the
command (and the hook step) exits 0 and changes nothing — so it works
out-of-the-box for every adopter and never blocks a commit.

### Added (BDL-053)
- **`beadloom active-sync`** (`services/cli.py`) — reconcile each epic's ACTIVE.md bead-status table from `bd`. `--epic KEY` scopes to one epic; `--check` reports drift on a throwaway copy without writing (exit 1 on drift, 0 clean); `--json` emits `{changed_files, drifted_rows[{path,bead_id,old,new}]}`; `--no-export` skips the jsonl sync. Default (fix) mode rewrites drifted Status cells and best-effort runs `bd export -o .beads/issues.jsonl` (only when that file is git-tracked). No-op contract: no ACTIVE table / no `bd` / untracked jsonl → exit 0, zero behavior change
- **`application/active_table.py` reconcile core** — `reconcile_active_tables(project_root, bd_statuses, *, epic=None)` (pure with respect to `bd`: the caller injects the status map) returns a `ReconcileResult` (`changed_files`, `drifted_rows`); `bd_status_to_cell` documents the `bd`-status → Status-cell map (`closed → ✓ done`, `in_progress → in progress`, `blocked → blocked`, `open`/`ready → ready`; unknown → `None`). Classified as the new `active-table` **component** node with its own DOC.md
- **Pre-commit hook ACTIVE / tracker coherence step** — both `install-hooks` templates (`warn` and `block`) gained a guarded final step that runs `beadloom active-sync` and restages `.claude/development/docs/features/**` + `.beads/issues.jsonl` only when both `bd` and `beadloom` are installed. Never blocks the commit; a complete no-op in any repo without `bd`/ACTIVE

Phase "Beadloom governs itself" (BDL-051): closes the graph-discipline gap so
Beadloom's own architecture is **honest-by-construction**. Three threads land
together: (1) a new **`component` node kind** — an internal/infra building block
that earns a node + a `DOC.md` (the mirror of a `feature`'s `SPEC.md`), attributed
in code with `# beadloom:component=<id>`; (2) a **`module-coverage` lint** promoted
to **`severity: error`** (it supersedes the advisory `unregistered-feature-candidate`
sprawl-lint): every `src/beadloom/**.py` module with ≥1 symbol is either a tracked
node (feature/component, or under a node's `source` — incl. a **directory** source
like `tui/`) or named on a minimal, **visible** `exempt:` list in `rules.yml` —
**no shadow code**, and a new untracked module now **fails `beadloom ci`**; (3) the
AI tech-writer harness moved out of `tools/` into a first-class
**`ai_agents/ai_techwriter` domain** shipped inside the wheel (adopters run
`python -m beadloom.ai_agents.ai_techwriter` — **no Python vendoring**). ALL src
modules were classified (**21 new feature/component nodes** + the seeded exempt
list). The MCP `checkpoint` / `complete_bead` process-tools now **maintain the
`ACTIVE.md` status table** correct-by-construction. **Honest framing:** the lint is
the enforcement; this epic dogfooded the whole model on Beadloom itself.

### Added (BDL-051)
- **`component` node kind** — a tracked internal/infra building block with a `part_of` edge to its domain, a `source: <file>`, and a `docs: <DOC.md>`; attributed via `# beadloom:component=<id>` (the mirror of `# beadloom:feature=`). 10 component nodes: `graph/{loader,contracts,sdl}`, `context-oracle/context-builder`, `doc-sync/doc-indexer`, `infrastructure/{db,health,git-activity,mcp-tools}`, `services/bd-seam` (BDL-051 / S3a/S3b)
- **`ai_agents/ai_techwriter` domain** — the deterministic, seam-isolated PR-triggered doc-refresh harness, moved from the retired `tools/ai_techwriter` repo-tooling package INTO the installed `beadloom` package (graph-tracked, lint-governed, shipped in the wheel). Behaviour is the BDL-049/050 model byte-unchanged; adopters invoke `python -m beadloom.ai_agents.ai_techwriter`. A `core-no-import-ai-agents` / `application-no-import-ai-agents` `forbid_import` pair keeps it a **leaf consumer** (BDL-051 / S2)
- **11 feature `SPEC.md` + 10 component `DOC.md`** filled — the newly-classified capabilities (`site-generation`, `ci-gate`, `code-indexer`, `route-extraction`, `test-mapping`, `sync-check`, `snapshot`, `config-check`, `branch-protection`, `agentic-flow-setup`, `ai-techwriter-setup`, `ai-techwriter`) and the component docs (BDL-051 / S3b + the docs wave)

### Changed (BDL-051)
- **`module-coverage` lint is now `severity: error`** (was `warn`) — with every src module classified, a new untracked module fails `beadloom lint --strict` / `beadloom ci`. It supersedes the older `unregistered-feature-candidate` advisory sprawl-lint with a whole-tree check; a node's `source` may be a **directory** (dir-source coverage — the `tui` service covers all of `src/beadloom/tui/`) (BDL-051 / S3a)
- **No Python vendoring in `setup-ai-techwriter`** — the scaffold no longer copies harness Python into a target repo (the BDL-047/048 `HARNESS_MODULES` / `vendor_harness` / `sync_vendored_harness` drift-guard machinery is retired); it emits only the CI wrapper (invoking the packaged module) + the operator artifacts (`recipe.yaml` / `provision-runner.sh`, copied from package data) (BDL-051 / S2)
- **MCP `checkpoint` / `complete_bead` maintain the `ACTIVE.md` status table** — the process-tools update the bead-status table + progress log in `ACTIVE.md` correct-by-construction, not just `bd` comments (BDL-051 / S4)
- **Docs** — the architecture-model guide gained the directory-`source` coverage note + the corrected feature/component example (`code-indexer` is a feature); domain READMEs now index their features + components; the AI tech-writer guide + `services/cli.md` reference the packaged `beadloom.ai_agents.ai_techwriter` module (no `tools.ai_techwriter`) (BDL-051 docs wave)

Phase "CI consolidation" (BDL-050): replaces the three independent PR workflows
(`beadloom-gate.yml` / `tests.yml` / `ai-techwriter.yml`) with **one
`.github/workflows/ci.yml`** on `pull_request → main`. Jobs `gate` ∥ `tests`
(3.10–3.13 matrix) ∥ `site-build` (VitePress build) run in parallel; `ai-techwriter`
has **`needs: [gate, tests, site-build]`** so it runs only when all three are green —
**a broken PR never spends Qwen tokens**. The AI tech-writer harness now classifies
each run into a **verdict** `{ok, flagged, infra}` (discriminator: `tokens > 0`): a
genuine unresolved doc drift (`flagged`) blocks the PR (exit 1), but an **infra
failure** (`infra` — a dead self-hosted runner, an exhausted `$30` quota, a provider
5xx; `tokens == 0`) PASSES (exit 0) with a loud `::warning::` + a best-effort PR
comment, so dead infra never freezes merges. `tests` dropped its `paths:` filter (so
every leg runs on every PR and is a reliable required check); `site-build` is now a PR
check (a VitePress/mermaid/interpolation break is caught **before** it lands on
`main`); the redundant `push: main` gate/tests runs were removed (`main` is green by
construction under strict trunk-based — `deploy-site.yml` is the only `push: main`
job). All workflow actions are Node24-compatible. Branch protection now requires the
**7 consolidated check-runs**. GitLab mirrors the structure via stages
`verify → docs` with the same `needs`. **Honest framing:** still no auto-merge — a
human merges; CI on the PR is the true enforcement; the agent's refresh is a proposal.

### Added (BDL-050)
- **Consolidated `.github/workflows/ci.yml`** — one `on: pull_request → [main, master]` (+ `workflow_dispatch`) pipeline with jobs `gate` (the `beadloom-gate` composite Action) ∥ `tests` (3.10–3.13 matrix) ∥ `site-build` (`beadloom docs site` + `npm run docs:build`) → `ai-techwriter` (`needs: [gate, tests, site-build]`, self-hosted). `concurrency: ci-${{ github.event.pull_request.number || github.ref }}` with `cancel-in-progress: true`. The `ai-techwriter` job body is the BDL-049 model verbatim (loop-guard, `--since merge-base`, `--target pr-branch`, `AI_TW_PAT` push, PR comment) — only the trigger moved into `ci.yml` and the exit code is now verdict-driven (BDL-050 G1/G7)
- **AI tech-writer verdict `{ok, flagged, infra}`** (`tools/ai_techwriter/runner.py::classify_verdict` + `cli.py::_report`) — the discriminator between a doc problem and an infra failure is whether the model produced output (`input_tokens + output_tokens > 0`). `ok` (no-op / clean) and `infra` (`tokens == 0` — process/provider error, 5xx, exhausted quota) → exit 0; `flagged` (`tokens > 0` but docs still dirty: post-refresh `beadloom ci` red / fixpoint not reached / budget exceeded) → exit 1 (the required check goes red). On `infra` the entrypoint also emits a GitHub `::warning::` annotation + a best-effort PR/MR comment so a skipped check is visible. A dead runner / exhausted `$30` quota never freezes merges; a real unresolved doc drift does (BDL-050 G1 / RFC Q1)

### Changed (BDL-050)
- **Required status checks = the 7 consolidated `ci.yml` check-runs.** `onboarding/branch_protection.py::DEFAULT_STATUS_CHECK_CONTEXTS` is now `("gate", "tests (3.10)", "tests (3.11)", "tests (3.12)", "tests (3.13)", "site-build", "ai-techwriter")` (was the single `beadloom-gate`). `enforce_admins: true` + 0 required reviews kept (strict trunk-based; owner self-merges). Re-apply with `beadloom setup-branch-protection` (BDL-050 G2/G4)
- **`tests` un-filtered + required.** The 3.10–3.13 matrix lost its `paths:` filter and runs on every PR, so each leg can be a strict required check without stalling. `push: main` gate/tests runs were removed — `deploy-site.yml` is the ONLY `push: main` job (BDL-050 G2/G5)
- **`site-build` is a PR check** (closes `beadloom-wozp`) — the VitePress build (the BUILD half of `deploy-site`, no Pages deploy) runs on every PR, catching VitePress/mermaid/dead-link/interpolation breaks before they reach `main` (BDL-050 G3)
- **Node24-compatible actions** (closes `beadloom-t7vn`) — `actions/checkout@v5`, `astral-sh/setup-uv@v6`, `actions/setup-node@v5`, `node-version: 22` across the workflows; `deploy-site.yml` opts the whole workflow into the Node24 runtime via `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true` as a documented stopgap until `configure-pages` / `upload-pages-artifact` / `deploy-pages` publish Node24 majors — avoids the 2026-06-16 Node20 deprecation (BDL-050 G6)
- **GitLab mirror** — `.gitlab-ci.yml` now consolidates into stages `verify` (`gate` ∥ `tests` ∥ `site-build`) → `docs` (`ai-techwriter` with `needs: [gate, tests, site-build]`), gated on `$CI_PIPELINE_SOURCE == "merge_request_event"`, with the same `AI_TW_PAT` push + verdict exit handling (no `allow_failure` — the verdict IS the gate). Vendored CI templates re-vendored to match (drift-guard green) (BDL-050 G7)
- **Docs** — the AI tech-writer guide (`docs/guides/ai-techwriter.md`) and the agentic-flow guide (`docs/guides/agentic-flow.md`) now describe the consolidated `ci.yml` (needs-ordering), the verdict semantics, and the 7-check branch protection; the team-facing `BDL-AI-AGENTS-ARCHITECTURE.md` was refreshed end-to-end (PR-triggered consolidated model + diagrams) (BDL-050 G8)

Phase "Trunk-based + PR-triggered AI tech-writer" (BDL-049): moves the AI
tech-writer from an `on: push` to `main` trigger to **`on: pull_request` → `main`**,
and the whole dev flow to **trunk-based development**. The agent now runs **once per
PR** against a clean `--since $(git merge-base origin/<base> HEAD)` baseline and
**commits its doc refresh back onto the PR head branch** (`--target pr-branch`,
message `[skip ai-techwriter] …`) + posts a PR comment — code and its doc updates
review and merge in one PR; no orphan doc-PRs. A **loop-guard** (bot author /
`[skip ai-techwriter]` subject → the workflow's `AI_TW_SKIP` early-skip step) stops
the agent's own push from re-triggering the `synchronize` event, and
`cancel-in-progress: true` cancels a superseded in-flight run. GitLab mirrors the
model via `merge_request_event`. This fixes the redundant 1h/768K-token re-refreshes,
the red-`main` window, and the orphan-doc-PR pile-up seen during BDL-047/048.
**Honest framing (not overclaimed):** no auto-merge — a human merges the PR; CI on
the PR (`beadloom-gate` as a **required check** via the new
`beadloom setup-branch-protection`) is the true enforcement; the agent's refresh is a
proposal in the PR.

### Added (BDL-049)
- **`beadloom setup-branch-protection --repo OWNER/NAME [--branch] [--check] [--dry-run]`** — idempotent `main` (or `--branch`) branch protection via `gh api` (declarative `PUT .../protection`): a PR is required (no direct push), the always-on `beadloom-gate` check is a **required status check** (`strict: true`), `enforce_admins: false` + 0 required reviews + `restrictions: null` so the solo owner is never locked out (can self-merge). `--check` (repeatable) overrides the default required-check context entirely; it must match a **real** GitHub check-run name and must NOT be a path-filtered workflow's check (it would not run on every PR → stuck PRs under `strict`). `--dry-run` prints the exact `gh api` call + JSON payload without touching GitHub. New module `onboarding/branch_protection.py` (`build_protection_payload`, `BranchProtectionRequest`, `apply_branch_protection`; injectable `GhRunner` seam for mockable tests) (BDL-049 G6)
- **`--target {branch-pr,pr-branch}` on the AI tech-writer harness** (`tools/ai_techwriter`) — `pr-branch` (the `on: pull_request` path) commits the refresh **onto the existing PR head branch** + posts a PR/MR comment (`GitHubPRBranchPublisher` / `GitLabPRBranchPublisher`), resolving the PR/MR from the CI env; `branch-pr` (the default, for manual `workflow_dispatch` with no PR context) keeps the original branch-cutting + open-PR behaviour (BDL-049 G4)

### Changed (BDL-049)
- **AI tech-writer triggers on `pull_request` to `main`/`master`, not `push`.** `.github/workflows/ai-techwriter.yml` now fires on `pull_request` (`opened`, `synchronize`, `reopened`); the `push: branches:[main]` trigger is removed. `--since` is `git merge-base origin/$BASE_REF HEAD` (fallback: the PR base SHA) — exactly "what this PR changed" — replacing `--since github.event.before`. A **loop-guard** step skips the run (`AI_TW_SKIP=1`) when the PR head commit's author is `beadloom-ai-techwriter` OR its subject contains `[skip ai-techwriter]`. `concurrency` now sets `cancel-in-progress: true` (a new commit cancels the older in-flight run for that PR). `workflow_dispatch` is kept as a manual fallback and uses the `--target branch-pr` path (BDL-049 G2/G3/G5/G8)
- **GitLab CI mirrors the model** — the `ai-techwriter` job in `.gitlab-ci.yml` now runs on `rules: $CI_PIPELINE_SOURCE == "merge_request_event"`, computes `--since` from `git merge-base origin/$CI_MERGE_REQUEST_TARGET_BRANCH_NAME HEAD` (fallback `$CI_MERGE_REQUEST_DIFF_BASE_SHA`), publishes `--target pr-branch` onto `$CI_MERGE_REQUEST_SOURCE_BRANCH_NAME`, and applies the same loop-guard. The vendored CI templates (`onboarding/templates/ai_techwriter/{github-workflow,gitlab-ci-job}.yml`) mirror both platforms (BDL-049 G7)
- **Vendored coordinator flow is now trunk-based** — `CLAUDE.md` §6 (Git) and the vendored `.claude/commands/coordinator.md` describe feature-branch + one PR to `main` + merge-when-green, re-vendored so the BDL-048 drift-guard stays green and `setup-agentic-flow` scaffolds the trunk-based flow into any repo (BDL-049 G1)
- **Docs** — the AI tech-writer guide (`docs/guides/ai-techwriter.md`) and the agentic-flow guide (`docs/guides/agentic-flow.md`) now describe the PR-triggered / trunk-based model (merge-base `--since`, `--target pr-branch`, loop-guard, `cancel-in-progress`, `workflow_dispatch` fallback, GitLab MR mirror, `setup-branch-protection`) (BDL-049 G10)

Phase "Agentic-flow packaging" (BDL-048): packages Beadloom's proven solo
multi-agent dev flow into the product. One command (`beadloom setup-agentic-flow`)
scaffolds the flow into any repo — the role subagents + slash skills vendored
**byte-identical** to Beadloom's own live `.claude/` (drift-guarded), with the
`CLAUDE.md` auto-regions generated per-project — and `config-check` now
drift-checks (and `--fix` restores) those scaffolded flow files. Four MCP
**process-tools** (`task_init` / `bead_context` / `complete_bead` / `checkpoint`)
make the flow's deterministic steps callable from ANY MCP client; the MCP catalog
is now **18 tools**. **Honest boundary (not overclaimed):** MCP serves
deterministic process-tools, NOT orchestration — the coordinator + Agent-spawn
stay Claude-Code-native/harness; `complete_bead` is advisory-strong; the single
source of TRUE enforcement remains `beadloom ci` in CI. Additive — no schema bump.

### Added (BDL-048)
- **`beadloom setup-agentic-flow [--project DIR] [--force]`** — one-command, idempotent scaffold of the packaged multi-agent dev flow into a repo (in the `setup-*` family). Drops `.claude/agents/{dev,test,review,tech-writer}.md` + `.claude/commands/{coordinator,task-init,checkpoint,templates}.md` **vendored byte-identical** from package-data assets (drift-guarded against the live `.claude/`), plus a `.claude/CLAUDE.md` whose auto-regions are generated for THIS project (name / stack / version — version from Beadloom's `__version__`) via the existing `refresh_claude_md` machinery. A matching file is left alone, a hand-edited file is skipped (reported as such) unless `--force`; user prose outside the CLAUDE.md auto-regions is never touched. New module `onboarding/agentic_flow_setup.py` (`scaffold()` + `sync_agentic_flow()` drift guard) (BDL-048 G1)
- **`config-check` covers the scaffolded flow** — when a repo has the agentic flow scaffolded, `config-check` byte-compares each vendored `agents/*` + `commands/*` file against the shipped template, and `--fix` re-drops them (`config_sync.refresh_agentic_flow_files`, gated on the flow already being present — never forced onto a repo that did not adopt it) alongside refreshing the CLAUDE.md auto-regions (BDL-048 G1)
- **Four MCP process-tools** on `services/mcp_server.py` (catalog 14 → 18) — deterministic, refusable operations over the substrate, callable from any MCP client (tool-agnostic via `setup-mcp`). They do NOT orchestrate or spawn sub-agents:
  - **`task_init(type, key)`** — scaffold the docs folder + per-type skeletons (PRD/RFC/CONTEXT/PLAN/ACTIVE or BRIEF/ACTIVE) + a valid 4-role bead DAG (dev → test → review → tech-writer) via `bd`.
  - **`bead_context(bead)`** — ONE payload: `ctx` + `why` + a CONTEXT.md/ACTIVE.md excerpt + the active architecture rules for the bead's area (resolves the bead's graph ref from `bd show`); read-only.
  - **`complete_bead(bead, run_tests=true)`** — the **refusing gate**: runs `beadloom ci` (reindex → lint → sync-check → config-check → doctor, via `application/gate.run_ci_gate`) + the test suite; **on PASS** closes the bead (`bd close --suggest-next`), **on FAIL REFUSES to close** and returns the findings. Advisory-strong, not the true enforcement point.
  - **`checkpoint(bead, text)`** — `bd comments add` + a best-effort timestamped ACTIVE.md note.
- **`services/bd_seam.py`** — a thin, mockable wrapper over the `bd` (beads) CLI (`run_bd()` → `BdResult`; `BdUnavailableError` with a clear message when `bd` is absent), so the bead-touching process-tools are testable without a real `bd` binary (BDL-048)
- **Getting-started guide** `docs/guides/agentic-flow.md` — the packaged flow, `setup-agentic-flow` (scaffold / idempotency / `config-check --fix`), the four process-tools (and that `complete_bead` refuses red), the tool-agnostic angle, and the honest boundary (orchestration stays in the harness; CI is the true enforcement) (BDL-048 G7)

Phase F4.1 "AI tech-writer in CI" (BDL-047): closes the DocAsCode loop at the *fix*
step. Beadloom already detects doc drift honestly; F4.1 adds automated remediation —
on push to `main`/`master`, a deterministic, platform-agnostic harness
(`tools/ai_techwriter/`) drives a **Goose** agent + **Qwen3.7-Plus** (external API)
to rewrite ONLY the drifted docs, verifies freshness to a fixpoint, runs
`beadloom ci`, and opens a **PR/MR for human review** (never auto-merges; flagged
"⚠ needs human" if the gate is not green). Runs on a self-hosted VPS runner where
the API key + Goose live; dual-platform (GitHub Actions + GitLab CI), first-class.
Dogfood-proven on the real VPS runner (refresh PR merged). Honesty preserved:
`sync-check → 0` proves *freshness*, the human PR review proves *correctness*. Only
two additive core changes (a non-interactive `sync-update` and a `sync-check --since`
primitive) + one new `setup-*` command; no schema bump.

### Added (BDL-047 / F4.1)
- **`beadloom sync-check --since <git-ref>`** — measures doc-code drift against the code state at a **git ref** (e.g. the push's parent) instead of the stored `sync_state` baseline. Reports pairs whose code drifted since the ref while the doc was not correspondingly updated. Makes drift detection survive a **fresh CI checkout** (a clean clone re-baselines `sync_state` to the just-pushed code, masking per-push drift). Mirrors `diff --since`; rejects invalid/all-zero refs. New engine fn `doc_sync/engine.check_sync_since` (reads `git show <ref>:<path>` + disk only; mutates nothing) (BDL-047 G12)
- **`beadloom sync-update [REF] --yes [--all]`** — a **non-interactive** re-baseline (no editor/prompt): records that the doc(s) match the code now (recompute hashes/symbols, `status='ok'`). `--all` (with `--yes`) re-baselines every currently-stale ref in one call — the primitive a CI fixpoint loop needs. Wraps the existing `mark_synced_by_ref`. Closes UX #106 (BDL-047 W1)
- **`beadloom setup-ai-techwriter --platform {github,gitlab}`** — one-command, idempotent opt-in (in the `setup-*` family). **Vendors** the deterministic harness package + Goose recipe into `tools/ai_techwriter/` (self-contained — the runner needs only `beadloom` + `goose` + python), drops the chosen platform's CI wrapper, a hardened `provision-runner.sh`, and the getting-started guide `docs/guides/ai-techwriter.md`. The harness is shipped as drift-guarded package data (inert `.py.txt` assets kept byte-identical to the live source) (BDL-047 G8/G11)
- **The deterministic harness** (`tools/ai_techwriter/`, repo tooling, not the wheel): discover scope from `sync-check --json --since` → per-doc context packet (`docs polish --format json` + `ctx`/`why`) → Goose rewrite → `sync-update --yes` → fixpoint re-check (per-doc retry ≤2, fixpoint rounds ≤10, hard caps 50 turns / 2M tokens) → `beadloom ci` gate → branch + PR/MR via a per-platform adapter (`gh` / `glab`). Entrypoint `python -m tools.ai_techwriter --platform {github,gitlab} --since <ref> [--dry-run]`. Goose never decides scope, marks synced, or merges (BDL-047 W2/W3)
- **Both CI wrappers trigger on push to main/master** (+ manual dispatch): `.github/workflows/ai-techwriter.yml` and the `ai-techwriter` job in `.gitlab-ci.yml` call the SAME entrypoint; only the trigger, secret naming (`QWEN_API_KEY` repo secret / CI/CD variable; optional `QWEN_BASE_URL`), and `--platform` differ. The push parent (`github.event.before` / `$CI_COMMIT_BEFORE_SHA`, fallback `HEAD~1`) feeds `--since`. Loop-safe: a human-merged refresh PR triggers a 0-stale no-op; `concurrency` serializes (BDL-047 G10)
- **`provision-runner.sh`** — a hardened, idempotent, executable self-hosted-runner provisioner (`--platform/--repo/--token`): guarantees swap **before** apt/build (the OOM lesson), RAM (~2 GB min, ~4 GB recommended) + disk (~5 GB) prechecks, fail-hard on the critical steps (toolchain + runner register/start), best-effort + verified Goose/beadloom/bd installs reported at the end (BDL-047 G11)
- **G9 dashboard widget "AI tech-writer activity"** — the harness appends an honest **run-record** per run to `.beadloom/ai_techwriter_runs.json` (`ts` stored not `now()`, platform, docs_refreshed, input/output tokens, model, gate, pr_url); the VitePress dashboard renders an `AiTechwriterActivity` widget (`site_dashboard.build_dashboard_data` `ai_techwriter` section): docs-refreshed + token spend per-run and cumulative, ONLY real recorded runs (no interpolation). **Tokens are fact** (from the API `usage`); the **dollar figure is a clearly-labeled estimate** ("est. @ $X/1M tokens"), never a hard cost. Absent/empty/corrupt store → empty-but-present section (BDL-047 G9)
- **Getting-started guide** `docs/guides/ai-techwriter.md` — the loop, the 3-step setup, both platforms, the on-push trigger, the honesty model, and the G9 widget (BDL-047 G7)

## [1.10.0] - 2026-06-02

**Federation + a living, navigable public portal.** This release adds cross-repo contract federation and a tool-agnostic CI gate (F1–F3), a generated VitePress knowledge-base portal with an interactive metrics dashboard, interactive architecture + cross-repo landscape map, and the published validated docs (F4/F4.4), and reshapes that portal into a navigable, bilingual (EN/RU) front door with the README as its landing page (BDL-046). Everything is additive — no breaking changes to the CLI/API or the graph schema.

Phase 0 "Foundation / Honesty Gate" (BDL-036): Beadloom now passes its own checks honestly.
Phase F1 "Federation Foundation" (BDL-037): cross-repo federation thin slice — `@repo:ref_id` identity, the `lifecycle` field, `beadloom export`, and `beadloom federate`, dogfooded on the real core-monolith ↔ integration-service RabbitMQ contract.
Phase F2 "Cross-Service Contract Graph" (BDL-038): a first-class cross-service contract graph — AMQP exchange identity + GraphQL SDL contracts, contract-level intent-vs-reality verdicts (incl. presence-based `BREAKING`), the `external`/`unmapped` lifecycle, nested product-vs-company landscapes, and paradigm-agnostic node/edge kinds.
Phase F3 "Tool-Agnostic Enforcement Everywhere" (BDL-039): the detection from F1/F2 gains teeth — a federated landscape gate (`federate --fail-on`), agent-actionable violation output, AgentConfigAsCode (`config-check`), a single `beadloom ci` gate, and a reusable composite GitHub Action + GitLab template, dogfooded on Beadloom's own CI. All additive — no schema/version bump.
Phase F4 "Living Knowledge Base + Visual Landscape" (BDL-040): a `beadloom docs site` VitePress generator with three showcases — an AaC/DocAsCode metrics dashboard, an interactive architecture + 🌟 cross-repo landscape map, and the published validated docs with per-doc `doc_sync` badges. Deterministic, honest-by-construction, and dogfooded by building Beadloom's own site with a real `vitepress build`. No schema bump.
GitHub Pages deploy (BDL-042): the VitePress site is published as a project page at `https://zoologov.github.io/beadloom/` — `base: "/beadloom/"` set, Mermaid `click` targets made base-aware at runtime (`DiagramViewer` prepends `import.meta.env.BASE_URL`; generated Markdown stays base-agnostic), and `.github/workflows/deploy-site.yml` regenerates + builds + deploys on every push to `main` (so the published page never drifts from the code).
Phase F4.4 "Site rendering fixes + dashboard UX" (BDL-041): hardens F4 — fixes the two F4 Mermaid render bugs and adds a generation-time validity guard (a broken diagram fails pytest, not the browser), pan/zoom/fullscreen on every diagram, a real interactive ECharts dashboard (critical-first alert banner + status cards, gauges, category charts, honest trends, recommendations — the verbose text dump removed), and a local contract-graph landscape with safe page-aware clicks. Dogfooded on Beadloom's own site (real `vitepress build` exit 0, render browser-confirmed). **F4 and F4.4 ship together** (a published broken diagram = a published lie). No schema bump.
Portal IA + bilingual About (BDL-046): reshapes the generated VitePress portal — About (the README) becomes the landing page, a single ordered EN sidebar replaces the old nav, the architecture overview moves to `/architecture`, the Documentation group gains a descriptive Overview, the top nav is removed, and About becomes bilingual (EN/RU) via an in-page toggle (VitePress `locales` was evaluated and dropped). Browser-confirmed on the deployed site. No schema bump.

### Added (BDL-046)
- **Portal navigation restructure** — the generated left sidebar is now a single ordered EN tree: About (`/`) · Getting Started (only if its page exists) · Dashboard (flat) · Architecture (collapsed, led by an "Architecture overview" → `/architecture`) · Landscape map (flat) · Documentation (expanded, led by an Overview). Dashboard and Landscape are flattened (the single-child "Metrics" / "Map" groups removed) (`application/site_nav.py` — `render_sidebar()`) (BDL-046 BEAD-02/BEAD-03)
- **About = README landing (EN `/`, RU `/ru/`)** — the home page is generated from `README.md` (and `README.ru.md`) by `application/site_about.render_about()`, which rebases repo-relative links so they resolve on the site (published `docs/<x>.md` → `/docs/<x>`; unpublished internal targets → absolute GitHub URL; external URLs / shields.io badges / anchors untouched; the badge-link `[![alt](img)](target)` idiom handled). The architecture overview that used to be the landing moves to `/architecture` (BDL-046 BEAD-01/BEAD-03)
- **Bilingual About via in-page toggle** — the README's `[Русский](README.ru.md)` / `[English](README.md)` line is rewritten to the counterpart route (`/` ↔ `/ru/`), so the language toggle appears only on About and never 404s elsewhere; the rest of the portal stays EN (`site._CROSS_LINK_ROUTES`) (BDL-046 BEAD-11)
- **Documentation Overview** — `docs/index.md` is now a short descriptive page (intro + a one-sentence description naming each section's members as text) instead of a flat link wall; the expanded Documentation sidebar is the navigable map (`application/site._render_docs_overview()`) (BDL-046 BEAD-03)
- **Top nav removed** — the top `nav` is empty (`render_nav()` → `[]`); the default theme still renders the appearance toggle + built-in search (BDL-046 BEAD-02)
- **Feature-SPEC tracking + neutral reference badge** — per-symbol `# beadloom:feature=<ref>` source annotations bind a file to a graph node (read by `doc_sync`'s `build_sync_state`) so a feature SPEC is freshness-checked rather than badged as untracked; a doc tied to no sync pair now shows the neutral **"📘 reference — overview/guide, not tied to a code symbol"** badge (reworded from "untracked", with no misleading coverage %) (`application/site_published.py`, `doc_sync/engine.py`) (BDL-046 BEAD-14)

### Changed (BDL-046)
- **Badge-link rebasing fix** — `render_about` now rewrites the README's README↔README cross-link to the counterpart About route instead of dropping it, and recurses the inner image of a `[![badge](img)](link)` so an absolute shields.io badge stays untouched while a relative inner target is still rebased (BDL-046 BEAD-01/BEAD-11)
- **VitePress `locales` evaluated and dropped** — the original plan used VitePress i18n for the language switch; live dogfood proved it the wrong tool for curated About-only (its global `/x ↔ /ru/x` mapping translated the whole menu and 404'd off `/ru/`), so `locales` / `navRu` / `sidebarRu` were removed in favour of the in-page About toggle (BDL-046 BEAD-11)

### Added (F4)
- **`beadloom docs site [--out DIR] [--federated FILE]`** — generates a VitePress knowledge-base content tree from the indexed graph (read-only), under `--out` (default `site/`); never writes into the source `docs/`. Emits an architecture overview, one page per node, the three showcases below, and `.vitepress/config.generated.mjs` (nav/sidebar). Output is deterministic (sorted, stable frontmatter, no wall-clock in the diffed tree). **Beadloom produces, VitePress renders** — no live server, no LLM (`application/site.py` + `site_pages.py`) (BDL-040 BEAD-01)
- **Showcase A — AaC/DocAsCode metrics dashboard** (`dashboard.md` + `dashboard.data.json`): lint count + severity, debt score + trend, doc coverage / `sync-check` freshness / stale count, the `doctor` summary, and an optional federated rollup. **Honest by construction** — every figure comes from the SAME code path as its gate (`graph/linter.lint` / `debt_report` / `doc_sync` `sync_state` / `doctor.run_checks` / the `federate` output verbatim); the page never invents a number (`application/site_dashboard.py`) (BDL-040 BEAD-02)
- **Showcase B — 🌟 cross-repo landscape map** (`landscape.md`): the F2 federated contract graph rendered as a clickable **Mermaid** diagram — satellites as nodes, contract edges carrying the hub's verdict verbatim, edges labelled by verdict, a `classDef` health overlay (green/red/grey), broken edges red, nodes clickable to their intra-repo page. With `--federated` it reads a `federate` hub artifact; without it the map degenerates to the local graph. Thin slice = Mermaid only (Cytoscape/D3 is a follow-up; no schema bump) (`application/site_landscape.py`) (BDL-040 BEAD-03)
- **Showcase C — published validated docs** (`docs/**` + `docs/index.md`): the REAL `docs/` tree copied verbatim (the source of truth, rendered as-is) with a per-doc validation badge injected into the COPY only — the source `docs/` is **NEVER mutated** (no AI prose-rewriting; that is the deferred F4.1). The badge status comes from `doc_sync`'s `check_sync` — the SAME path `beadloom sync-check` runs — and shows `fresh` / `stale — <reason>` / `untracked`, the stored `last synced` (deterministic), and the node's source-coverage %; marker-delimited so regeneration overwrites only the badge region (`application/site_published.py`) (BDL-040 BEAD-04)
- **Committed VitePress scaffold** (`site/package.json`, `site/.vitepress/config.mjs`) renders the generated tree; build output + `node_modules` are gitignored. Build with `cd site && npm install && npm run docs:build`; preview with `npm run docs:preview`. See `docs/guides/vitepress-site.md` (BDL-040 BEAD-01/BEAD-05)
- **Dogfood proof (F4)** — built Beadloom's own site end-to-end (`vitepress build` exit 0). The real build surfaced and fixed two genuine generator bugs invisible to unit tests — `.DS_Store` pollution copied into the published tree, and 24 dead intra-site links — validating the honesty principle: only a real build proves the produced tree renders (BDL-040 BEAD-05)
- **F4.1 deferred (next follow-up epic)** — the AI tech-writer in CI (orchestrating an *external* model to refresh drifted docs, scoped by `sync-check` / `docs polish --json`, with team review on a PR) is intentionally NOT in this release. The published-docs showcase computes badges, it does not rewrite prose.

### Added (F4.4)
- **Mermaid render correctness + generation-time guard** — the two F4 diagram bugs that rendered broken in the browser are fixed at the source: landscape node ids are **prefixed** (`n_<sanitized>`) so a node named `graph` can never collide with the `graph LR` keyword (the "got GRAPH" crash), and C4 emits a `Rel(a, b)` only between **declared** diagram nodes (dropping — and logging — Rels to the undrawable `System` root that crashed `drawRels`; the relationship still lives in the graph + the landscape). A new generation-time guard (`application/site_mermaid_guard.validate_mermaid`) runs targeted structural validators over every emitted diagram and raises `MermaidValidationError` at generation/pytest time on a reserved-id/charset or undeclared-C4-Rel issue — **closing the "build green ≠ renders ok" gap** so a broken page fails the build, not the browser (BDL-041 BEAD-01)
- **Pan / zoom / fullscreen diagrams** — a global `DiagramViewer` theme component attaches pan + wheel-zoom + reset (`svg-pan-zoom`) and a Fullscreen toggle to every rendered Mermaid SVG (re-scanning on route change since Mermaid renders async); SSR-safe and gracefully static when JS is off (BDL-041 BEAD-02)
- **Interactive ECharts dashboard** — `dashboard.md` is now a thin page (title + intro + component mounts) backed by `dashboard.data.json`; committed Vue/ECharts widgets render it client-side: a **critical-first** `AlertBanner` + `StatusCards` (severity computed deterministically in Python — BREAKING leads; an empty alert list = all-clear), `HealthGauges`, `CategoryChart`, `TrendCharts`, and a `Recommendations` panel. **Honest trends** come only from real recorded points in an additive `.beadloom/metrics_history.json` append-log (seeded day-one from `graph_snapshots`) — sparse at first, no interpolation, timestamps stored not `now()` — and `recommendations` are built from the EXISTING gate data (lint / BREAKING-DRIFT contracts / stale docs / worst-debt), severity-ordered and deterministic. The verbose per-metric **text dump was removed** (no `<noscript>` fallback) — the widgets are the single presentation surface; data honesty lives in `dashboard.data.json` (`application/site_dashboard.py` + `site_metrics_history.py`) (BDL-041 BEAD-03/BEAD-04/BEAD-12)
- **Local contract-graph landscape + safe clicks** — without `--federated`, `landscape.md` is now the repo's **own contract graph**: it reconciles the local `produces`/`consumes` edges by `contract_key` into `Contract`s, classifies each to a `ContractVerdict`, and renders one verdict-coloured edge per producer→consumer (Beadloom's own site — which now models a real `beadloom --produces--> vitepress-site` / `vitepress-site --consumes--> beadloom` contract in its graph — renders a single `beadloom → vitepress-site` **CONFIRMED** edge; a repo with no contracts → an empty map). Clicks are **page-aware** (`existing_page_urls`): a node links to `/<dir>/<ref>` only when a page was actually generated for it, so a `site` node or a foreign federated repo renders without a click — killing the dead-link 404/MIME bug. `--federated` still renders the cross-repo hub map (BDL-041 BEAD-09)
- **Navigation trees** — the generated `.vitepress/config.generated.mjs` now carries a `collapsed`, `part_of`-nested **Architecture** tree (service → domains → features) with human-readable labels (`context-oracle` → "Context Oracle") and a nested, collapsible **Documentation** tree mirroring the `docs/` directory; both deterministic with no dead links (`application/site_nav.py`) (BDL-041)
- **Dogfood proof (F4.4)** — regenerated and rebuilt Beadloom's own site: the real `vitepress build` exits 0, all diagrams pass the guard, the landscape shows the real CONFIRMED contract edge with no dead clicks, and the ECharts dashboard render was browser-confirmed (BDL-041 BEAD-05)

### Added (F3)
- **Landscape gate** (`federate --fail-on <csv>`) — turns the F2 contract/edge verdicts into a CI gate: exits `1` when any verdict matches the fail-set, but **always writes `.beadloom/federated.json` + the report first** so CI can upload the artifact even on failure. A bare `--fail-on` / `default` arms the safe-default set `breaking,drift,orphaned_consumer,undeclared_producer` (+ edge-level `undeclared`); no-false-gate verdicts (`external`/`expected`/`dead`/`unmapped`/`confirmed`/`ok`/`cleanup_candidate`) can never be armed (rejected, exit `2`). Backed by the pure `gate_failures(fed, fail_on)` + `SAFE_DEFAULT_FAIL_ON` / `NEVER_FAIL_VERDICTS` in `graph/federation.py` (BDL-039 BEAD-01)
- **Agent-actionable output** — every architecture violation carries a `Violation.remediation` ("how to fix"), surfaced by `beadloom lint --format json` (a `remediation` key) and `--format github` (rendered into `::error` annotations so it shows inline on the PR) (BDL-039 BEAD-02)
- **AgentConfigAsCode** (`beadloom config-check [--fix]`) — regenerates `AGENTS.md`, the auto-managed regions of `CLAUDE.md`, and the IDE rules adapters **in memory** (reusing the exact `setup-rules --refresh` generator — no parallel reimplementation) and diffs them against disk; exits `1` on drift. Checks only the `beadloom:auto-start`/`auto-end` regions, never user-authored prose (`onboarding/config_sync.py`) (BDL-039 BEAD-03)
- **Unified gate** (`beadloom ci`) — composes reindex → `lint --strict` → sync-check → config-check → doctor → optional `federate --fail-on` (`--hub`) into one verdict with a single exit code; never short-circuits, names every step with an honest PASS/FAIL/SKIP, and shares one finding shape (`{kind, rule, severity, locations, why, remediation}`) so `--format rich|json|github` applies uniformly (`application/gate.py`) (BDL-039 BEAD-04)
- **Reusable CI integration** — a thin composite GitHub Action (`.github/actions/beadloom-gate`) wrapping `beadloom ci` (all logic in the CLI) + a GitLab template, with a documented pull-based hub pattern for the cross-service landscape (satellites publish commit-SHA-tagged exports; a hub job pulls ≥2 + `federate --fail-on`). Dogfooded on Beadloom's own CI (BDL-039 BEAD-05)
- **Dogfood proof (F3)** — the gate blocks a real boundary violation, a cross-service `BREAKING`, and a drifted agent-config; AgentConfigAsCode caught a genuine `AGENTS.md` drift on Beadloom itself during the dogfood (BDL-039 BEAD-06)

### Added
- **Cross-service contract graph (F2 moat)** — federation reconciles AMQP **and** GraphQL contracts into first-class `Contract`s (`graph/contracts.py`) keyed by a protocol-prefixed, **language-neutral** `contract_key` (AMQP `amqp:<exchange>/<routing>:<message_type>`, GraphQL `graphql:<schema>`), so a cross-language edge (e.g. a TS client ↔ a backend's GraphQL schema) resolves by contract *name*, never by code symbol (BDL-038 U3/G2/G3)
- **GraphQL SDL contract source** (`graph/sdl.py`) — extracts a producer's `exposed` SDL surface and a consumer's `references`; a presence-based **`BREAKING`** verdict fires when `references ⊄ exposed` (a consumer relies on a name the producer no longer exposes — caught before it ships, not a version diff) (BDL-038 U2/G3)
- **Contract-level intent-vs-reality verdicts** (`ContractVerdict`) — `CONFIRMED` / `BREAKING` / `ORPHANED_CONSUMER` / `UNDECLARED_PRODUCER` / `EXTERNAL` / `DEAD` / `EXPECTED`, with declared edge `lifecycle` (`external` > `dead` > `deprecated` > `planned` > `active`) folded onto the contract so intent dominates the shape check. Contract-level `DRIFT` is intentionally subsumed by `ORPHANED_CONSUMER` / `UNDECLARED_PRODUCER`; `DRIFT` stays the edge-level `EdgeVerdict` (BDL-038 G5)
- **`external` / `unmapped` lifecycle** — a node declared present-but-not-ours (`lifecycle: external`, e.g. a native Swift/Kotlin bridge) → `EXTERNAL`; a foreign ref that resolves but is exported without a usable surface → `EdgeVerdict.UNMAPPED`; both suppress DRIFT and stay distinct from a genuinely-absent `unresolved_refs` target (BDL-038 U4/G7)
- **Nested landscapes — product vs company scope** — an optional `landscape` provenance scopes implicit same-key contract matching to `(landscape, contract_key)`, so unrelated products sharing a coincidental message_type/schema name never auto-confirm or cross-pollute verdicts; a genuine cross-product contract is promoted cross-landscape via an explicit `@repo:` consumer edge. `federate` composes one product-landscape or a company-landscape of several (BDL-038 U5)
- **Paradigm-agnostic node/edge kinds** — arbitrary `kind`/`edge_kind` round-trips through `export`/`federate` without loss or rejection (FSD `page`/`feature`/`entity`/`repository` alongside DDD `domain`/`service`); the DDD-only DB `kind` CHECK was dropped (BDL-038 U1)
- **Dogfood proof (F2)** — verified end-to-end on a real landscape: a real GraphQL `BREAKING` mismatch caught before ship (a consumer-referenced field absent from the producer's current SDL), and a separate FSD-architecture product round-tripped through `export`/`federate` with zero kind loss, native bridges classified `EXTERNAL` (not DRIFT), and zero cross-pollution as a contract-less member of a company-landscape run (BDL-038)

### Added (F1)
- **Cross-repo node identity** — a graph ref may name a node in another repo as `@<repo>:<ref_id>` (`FederatedRef` / `parse_ref` in `graph/federation.py`); plain refs stay local. Malformed `@...` refs are surfaced as errors, never silently accepted. Cross-repo edges persist in a new `foreign_edges` table (BDL-037 F1)
- **`lifecycle` field** on every node and edge — `active` (default) | `planned` | `deprecated` | `dead`, as a first-class SQLite column (not `extra`). Only `active` edges count as live for `no-dependency-cycles` / `architecture-layers`; the federation hub reconciles `lifecycle` against reality into a three-valued intent-vs-reality verdict (BDL-037 F1)
- **`beadloom export`** — emit the indexed graph as a deterministic, self-describing federation artifact (schema v1: `repo`, `commit_sha`, `exported_at`, `generator`, `nodes`[lifecycle], `edges`[lifecycle + optional AMQP `contract` meta]). Byte-stable diffs (sorted nodes/edges + sorted keys); `commit_sha` is `null` when it cannot be honestly verified (BDL-037 F1)
- **`beadloom federate`** — hub aggregation of ≥2 satellite exports into one namespaced federated graph: resolve `@repo:` refs, assign an `EdgeVerdict` per edge (`OK` / `DRIFT` / `EXPECTED` / `CLEANUP_CANDIDATE` / `UNDECLARED` / `DEAD`), reconcile AMQP contracts (confirmed both-sides vs one-sided), report per-satellite staleness. Writes `.beadloom/federated.json` + `.beadloom/federated.txt` (BDL-037 F1)
- **Dogfood proof** — F1 verified end-to-end on the real core-monolith ↔ integration-service RabbitMQ contract: all 4 message types confirmed both-sides, 16 edges OK, no unresolved refs (BDL-037, UX #104)

### Migration
- **Schema versions (F2)** — `EXPORT_SCHEMA_VERSION` 1 → 2 (GraphQL SDL `contract` meta on edges), `FEDERATION_SCHEMA_VERSION` 1 → 2 (contract-level `verdict`/`protocol`/`contract_key`/`lifecycle` on hub output, GraphQL `exposed`/`references`/`missing`), and **SQLite schema 3 → 4**. All backward-compatible: `federate` still ingests v1 **and** v2 exports (the two export/federation versions are independent), and an older DB migrates idempotently with no data loss (BDL-038)
- **SQLite schema 3 → 4** — additive, idempotent table-rebuild (SQLite cannot `ALTER` a CHECK in place): adds `external` to the `lifecycle` CHECK on `nodes`/`edges`/`foreign_edges`, and drops the DDD-only `kind` CHECK so paradigm-agnostic kinds (FSD `page`/`feature`/`entity`/`repository`) load without rejection. Composes with the F1 changes; no regression (BDL-038 U1/G6/G7)
- **SQLite schema 2 → 3** — additive, idempotent: `lifecycle` columns on `nodes`/`edges`, a `foreign_edges` table, `produces`/`consumes` added to the `edges.kind` CHECK, and `contract_key` added to the edges primary key so multiple AMQP contracts on one node pair survive. Existing DBs upgrade cleanly (BDL-037)

### Changed
- **New `application` layer** — orchestrators (`reindex`, `doctor`, `debt_report`, `watcher`) moved from `infrastructure/` to a new `src/beadloom/application/` DDD layer. `infrastructure/` is now domain-agnostic (zero domain imports); layer order is `services → application → domains → infrastructure`. Module import paths changed `beadloom.infrastructure.{reindex,doctor,debt_report,watcher}` → `beadloom.application.*` (BDL-036 #91)
- **Architecture rules enforced** — `no-dependency-cycles` and `architecture-layers` restored to `severity: error`; `beadloom lint --strict` now fails on real cycle/layer violations and is genuinely clean on Beadloom itself (BDL-036 #91)
- **Generated bootstrap rule** is now `feature-needs-parent` (`has_edge_to: {}`) so a fresh `beadloom init --bootstrap` passes `lint --strict` out-of-the-box (BDL-036 #71)

### Fixed
- **doctor version drift** — reads in-tree `__version__` instead of stale `importlib.metadata` (BDL-036 #92)
- **AGENTS.md MCP tool count** — driven by a single-source catalog pinned to the live MCP registry; no longer drifts (13→14) (BDL-036 #93)
- **Incremental reindex "Nodes: 0"** — reports true live-DB node/edge totals on the docs/code-only path (BDL-036 #88)
- **Silent YAML failure** — graph loader raises `GraphParseError` with file+line on malformed YAML instead of silently producing 0 nodes (BDL-036 #86)
- **sync-check false `untracked_files`** — file-level `# beadloom:domain=` annotations on symbol-less modules and `<!-- beadloom:track= -->` doc markers now count as tracking signals (BDL-036 #89/#90)
- **Over-broad exception handling** in reindex narrowed to `sqlite3.OperationalError` for missing-table cases (BDL-036 #94)
- **`export` dropped declared cross-repo edges** — `@repo:` edges now persist in a `foreign_edges` table and union into the export artifact, so a satellite's intent-declared cross-repo links reach the hub (BDL-037 #100)
- **`produces`/`consumes` edge kinds rejected** — added to the `edges.kind` CHECK (the edges table is rebuilt, since SQLite cannot `ALTER` a CHECK) so contract edges persist through the real reindex → export path (BDL-037 #101)
- **Multiple contracts on one node pair collapsed** — `contract_key` (derived from `contract.message_type`) is part of the edges primary key, so a producer publishing N message types to one target survives instead of hitting `UNIQUE constraint failed` (BDL-037 #102)
- **`export` `commit_sha` leaked the host repo's HEAD** — `current_commit_sha` returns `null` when the project root is not the git toplevel, instead of an enclosing repo's sha (BDL-037 #103)

### Known
- `beadloom sync-check` still reports pre-existing documentation drift across several domains (accumulated content staleness, not a mechanism bug); a dedicated repo-wide doc-refresh is tracked as BDL-UX #99.

## [1.9.0] - 2026-03-10

Data accuracy, docs audit precision, and sync-check reliability. 6 UX issues resolved, 43 new tests. 2580 tests total.

### Fixed
- **Rules DB completeness** -- `_load_rules_into_db()` now handles all 9 v3 rule types (`ForbidCyclesRule`, `LayerRule`, `CardinalityRule`, `ForbidImportRule`, `ForbidEdgeRule`) instead of silently dropping 5 of 9 (BDL-034, UX #67)
- **Rule type labels** -- `_build_rules_section()` and `_read_rules_data()` detect all 7 YAML rule keys (`require`, `deny`, `forbid_cycles`, `layers`, `check`, `forbid_import`, `forbid_edge`) instead of binary require/deny classification (BDL-034, UX #68)
- **AGENTS.md regeneration** -- replaced `## Custom` marker with `<!-- beadloom:custom-start/end -->` HTML comment markers to prevent content duplication on `setup-rules --refresh` (BDL-034, UX #69)

### Changed
- **Docs audit false positive rate** -- reduced from ~60% to ~11% via three-layer filtering: blocklist modifiers (`>=`, `%`, `up to`), proximity scoring (keyword-distance weighting), and file-type heuristics (lower confidence for SPEC.md, CONTRIBUTING.md) (BDL-034, UX #65)
- **Two-phase sync-check** -- added `doc_hash_at_last_edit` column to `sync_state` table; `sync-check` now detects code changes since last doc edit, preventing `reindex` from masking stale documentation (BDL-034, UX #70)

### Verified
- **Snapshot diffing** -- confirmed `beadloom snapshot save/list/compare` CLI commands and `compare_snapshots()` diff logic already fully functional (BDL-034, UX #66 — closed as already resolved)

## [1.8.0] - 2026-02-21

C4 diagrams, debt reporting, interactive TUI, docs audit, agent instructions freshness, enhanced architecture rules, and 60+ UX fixes. 2537 tests.

### Added
- **C4 architecture diagrams** -- `beadloom graph --format=c4` (Mermaid C4 syntax) and `--format=c4-plantuml` (PlantUML with standard macros) (BDL-023)
- **C4 drill-down levels** -- `--level=context|container|component` for multi-resolution views; `--scope=<ref-id>` for component-level diagrams (BDL-023)
- **C4 external systems** -- `external: true` tag renders as `System_Ext`; database/storage tags render as `ContainerDb` (BDL-023)
- **C4 level mapping** -- automatic level inference from `part_of` depth + kind heuristics (BDL-023)
- **Architecture debt report** -- `beadloom status --debt-report` with aggregated score 0-100 and severity labels (BDL-024)
- **Debt scoring formula** -- weighted: rule violations (errors x3 + warnings x1), doc gaps (undocumented x2 + stale x1), complexity smells (BDL-024)
- **Debt CI gates** -- `--debt-report --json` for CI consumption; `--fail-if=score>N` and `--fail-if=errors>0` (BDL-024)
- **Debt trend tracking** -- delta per category vs last snapshot; top offenders list ranked by debt contribution (BDL-024)
- **MCP tool `get_debt_report`** -- debt report for AI agents (BDL-024)
- **Multi-screen TUI** -- 3-screen architecture workstation with Dashboard, Explorer, and Doc Status screens (`beadloom tui`) (BDL-025)
- **7 data providers** -- thin read-only wrappers over existing infrastructure APIs (Graph, Lint, Sync, Debt, Activity, Why, Context) (BDL-025)
- **GraphTreeWidget** -- interactive architecture hierarchy tree with doc status indicators (fresh/stale/missing) and edge count badges (BDL-025)
- **DebtGaugeWidget** -- debt score display with severity coloring (green/yellow/red) (BDL-025)
- **LintPanelWidget** -- violation counts with severity icons and individual violation details (BDL-025)
- **ActivityWidget** -- per-domain git activity progress bars with color coding (BDL-025)
- **StatusBarWidget** -- health metrics, watcher status indicator, auto-dismissing notifications (BDL-025)
- **NodeDetailPanel** -- node deep-dive with ref_id, kind, summary, source, edges, doc status (BDL-025)
- **DependencyPathWidget** -- upstream/downstream dependency tree visualization with impact summary (BDL-025)
- **ContextPreviewWidget** -- context bundle preview with token estimation (BDL-025)
- **DocHealthTable** -- per-node documentation health table with coverage tracking and row selection (BDL-025)
- **FileWatcherWorker** -- background file watcher with 500ms debounce, extension filtering, `ReindexNeeded` messages (BDL-025)
- **SearchOverlay** -- modal FTS5 search with LIKE fallback and result navigation (BDL-025)
- **HelpOverlay** -- modal keybinding reference organized by context (BDL-025)
- **17 keyboard bindings** -- screen switching (1/2/3), navigation, actions (r/l/s/S), overlays (?//) (BDL-025)
- `beadloom tui` command (primary), `beadloom ui` kept as alias (BDL-025)
- `--no-watch` flag to disable file watcher (BDL-025)
- **Docs audit** -- `beadloom docs audit` zero-config meta-doc staleness detection with fact registry (BDL-026, experimental)
- **Fact registry** -- auto-compute version, node/edge/test counts, CLI commands, MCP tools (BDL-026)
- **Doc scanner** -- keyword-proximity matching for fact verification; Rich color-coded output (stale/fresh/unmatched) (BDL-026)
- **Docs audit CI gates** -- `--json` output, `--fail-if=stale>0` (BDL-026)
- **Agent instructions freshness** -- `beadloom doctor` now checks CLAUDE.md and AGENTS.md for stale facts (BDL-030)
- **6 fact extraction helpers** -- version, packages, CLI commands, MCP tools, stack, test framework (BDL-030)
- **`beadloom setup-rules --refresh`** -- auto-update CLAUDE.md dynamic sections with `--dry-run` preview (BDL-030)
- **`<!-- beadloom:auto-start/auto-end -->` markers** -- safe section regeneration for agent instruction files (BDL-030)
- **NodeMatcher `exclude` filter** -- `exclude` field on NodeMatcher dataclass filters specific nodes from rule evaluation; used in `service-needs-parent` to skip root node (BDL-032)
- **`forbid_import` rules** -- 2 new rules: `tui-no-direct-infra` and `onboarding-no-direct-infra` enforce import boundaries via `code_imports` table (BDL-032)
- **Rules schema v3 tags** -- bulk tag assignments in `rules.yml` v3; `layer-service`, `layer-domain`, `layer-infra` tags for architecture layer enforcement (BDL-032)
- **5 new architecture rules** -- `no-dependency-cycles`, `architecture-layers`, `domain-size-limit`, `tui-no-direct-infra`, `onboarding-no-direct-infra` (9 rules total, 6/7 types exercised) (BDL-032)
- **API CHANGE tracking in agent skills** -- `/dev`, `/review`, `/tech-writer` skills updated with explicit API change handoff protocol to prevent doc staleness (BDL-032)

### Changed
- Textual dependency upgraded from `>=0.50` to `>=0.80` (BDL-025)
- Explorer `e` keybinding opens any node including domain nodes (BDL-029)
- Edge count legend uses `[N edges]` format instead of raw `[N]` (BDL-029)
- Tree icons: fixed triangle display for childless nodes at cold start (BDL-029)
- Doctor promoted undocumented nodes to WARNING severity (BDL-027)
- Untracked file details included in debt report output (BDL-027)
- Init now scans all code directories for React Native projects (BDL-027)
- Rules schema version upgraded from v1 to v3 with backward compatibility (BDL-032)
- `service-needs-parent` rule uses `exclude: [beadloom]` to skip root service node (BDL-032)
- Architecture lint: 9 rules evaluated (was 4), covering 6 of 7 rule types (BDL-032)

### Fixed
- **C4 depth computation** -- correct boundary nesting for deeply nested nodes (BDL-027)
- **C4 label/description separation** -- labels no longer include description text (BDL-027)
- **C4 self-referencing edges** -- filtered out to prevent diagram errors (BDL-027)
- **C4 boundary ordering** -- stable ordering for deterministic diagram output (BDL-027)
- **PlantUML level selection** -- correct C4 level passed to PlantUML output (BDL-027)
- **Debt report oversized false positive** -- parent nodes no longer flagged incorrectly (BDL-027)
- **Docs audit number filter** -- skip numbers <10 to avoid false matches (BDL-027)
- **Docs audit year filter** -- year values excluded from staleness checks (BDL-027)
- **Docs audit SPEC.md exclusion** -- specification files excluded from audit scope (BDL-027)
- **Docs audit dynamic versioning** -- correct version detection for hatch-vcs projects (BDL-027)
- **Docs audit full path display** -- show complete file paths in audit output (BDL-027)
- **TUI aggregate parent test counts** -- parent nodes show sum of child test counts (BDL-027)
- **TUI route extraction self-exclusion** -- node's own routes excluded from dependency view (BDL-027)
- **TUI route formatting** -- consistent route display across widgets (BDL-027)
- **File watcher thread shutdown** -- clean shutdown via `threading.Event` instead of daemon thread (BDL-028)
- **Static widgets not updating** -- `update()` instead of `refresh()` after screen switch (BDL-028)
- **Esc (Back) crash** -- `ScreenStackError` on `switch_screen` navigation fixed (BDL-029)

## [1.7.0] - 2026-02-17

AaC Rules v2, Init Quality, and Architecture Intelligence. 1657 tests.

### Added
- **NodeMatcher** — tag/kind-based node matching for rule definitions; `matches(ref_id, kind, tags=)` method (BDL-021 BEAD-01)
- **Node tags/labels** — tags stored in `extra` JSON column, bulk assignment via `tags:` block in rules.yml v3; `get_node_tags()` API (BDL-021 BEAD-01)
- **ForbidEdgeRule** — deny rules evaluated against `edges` table (vs DenyRule which checks `code_imports`); supports tag-based matching (BDL-021 BEAD-02)
- **LayerRule** — enforce layered architecture: define ordered layers with `allow_skip`, violation on reverse-direction edges (BDL-021 BEAD-03)
- **CycleRule** — circular dependency detection via iterative DFS; configurable `edge_kind` (single or tuple) and `max_depth`; reports full cycle path (BDL-021 BEAD-04)
- **ImportBoundaryRule** — file-level import restrictions using fnmatch glob patterns on `code_imports` file paths (BDL-021 BEAD-05)
- **CardinalityRule** — architectural smell detection: `max_symbols`, `max_files`, `min_doc_coverage` thresholds per node (BDL-021 BEAD-06)
- **Rules schema v3** — top-level `tags:` block for bulk tag assignments; backward compatible with v1/v2 (BDL-021 BEAD-01)
- **`load_rules_with_tags()`** — returns both rules and tag assignments from rules.yml (BDL-021 BEAD-01)
- **Architecture snapshots** — `beadloom snapshot save/list/compare`: save graph state to `graph_snapshots` table, list history, compare any two snapshots (BDL-021 BEAD-12)
- **Enhanced diff** — `NodeChange` now tracks source path changes, tag changes, symbol counts; `compute_diff_from_snapshot()` for snapshot-based comparison (BDL-021 BEAD-13)
- **Non-interactive init** — `beadloom init --mode bootstrap --yes --force` for CI/scripts; `non_interactive_init()` API (BDL-021 BEAD-08)
- **Doc auto-linking** — `auto_link_docs()` fuzzy-matches existing docs to graph nodes by path/ref_id similarity during init (BDL-021 BEAD-11)
- **Docs generate in init** — `beadloom init` offers doc skeleton generation as a final step (BDL-021 BEAD-10)
- **Enhanced `why --reverse`** — `render_why_tree()` for reverse dependency view; `--reverse` and `--format` flags on CLI (BDL-021 BEAD-14)
- **Scan all code directories** — bootstrap now scans all top-level dirs with code files, not just manifest-adjacent ones (BDL-021 BEAD-07)
- **249 new tests** (1657 total)

### Changed
- **Rule engine** — `Rule` type union expanded: `DenyRule | RequireRule | CycleRule | ImportBoundaryRule | ForbidEdgeRule | LayerRule | CardinalityRule`
- **`evaluate_all()`** — dispatches all 7 rule types (was 2)
- **`render_diff()`** — shows source path changes, tag changes, symbol counts for changed nodes
- **4 domain docs refreshed** — context-oracle, graph, onboarding, cli documentation updated

### Fixed
- **Root service rule** — `service-needs-parent` rule no longer fails on root node; root detection uses `part_of` edge presence (BDL-021 BEAD-09)

## [1.6.0] - 2026-02-17

Deep Code Analysis, Honest Doc-Sync, and Agent Infrastructure. 1408 tests.

### Added
- **API route extraction** — tree-sitter + regex detection for 12 frameworks: FastAPI, Flask, Django, Express, NestJS, Spring Boot, Gin, Echo, Fiber, Actix, GraphQL (schema + code-first), gRPC (BDL-017 BEAD-01)
- **Git history analysis** — `analyze_git_activity()` classifies modules as hot/warm/cold/dormant based on 6-month commit history (BDL-017 BEAD-02)
- **Test mapping** — `map_tests()` detects test framework (pytest, jest, go test, JUnit, XCTest) and maps test files to source modules (BDL-017 BEAD-03)
- **Rule severity levels** — rules support `severity: warn` vs `severity: error` (default); `beadloom lint` shows both, `--strict` fails only on errors; backward-compatible v1→v2 migration (BDL-017 BEAD-04)
- **MCP tool `why`** — impact analysis via MCP: upstream dependencies + downstream dependents as structured JSON (BDL-017 BEAD-05)
- **MCP tool `diff`** — graph changes since a git ref via MCP (BDL-017 BEAD-06)
- **MCP tool `lint`** — architecture validation via MCP with severity in JSON output (BDL-017 BEAD-12)
- **Deep config reading** — extracts scripts, workspaces, path aliases from pyproject.toml, package.json, tsconfig.json, Cargo.toml, build.gradle (BDL-017 BEAD-07)
- **Context cost metrics** — `beadloom status` shows average/max bundle sizes in estimated tokens (BDL-017 BEAD-08)
- **Smart `docs polish`** — enriched with routes, activity, tests, config data from deep analysis (BDL-017 BEAD-14)
- **AGENTS.md v3** — now documents 13 MCP tools (was 10) (BDL-017 BEAD-15)
- **3-layer staleness detection** — `check_sync()` now detects: `symbols_changed` (hash mismatch), `untracked_files` (files in source dir not tracked), `missing_modules` (doc doesn't mention module) (BDL-018)
- **Source coverage check** — `check_source_coverage()` finds Python files in node source directories not tracked in sync_state or code_symbols (BDL-018 BEAD-02)
- **Doc coverage check** — `check_doc_coverage()` verifies documentation mentions all modules in source directory (BDL-018 BEAD-03)
- **Hierarchy-aware coverage** — `check_source_coverage()` queries `part_of` edges to recognize files annotated to child feature nodes as tracked under parent domain (BDL-020 BEAD-02)
- **`/tech-writer` role** — new agent skill for systematic documentation updates using sync-check + ctx + sync-update workflow (BDL-019)
- **`/task-init` skill** — unified task initialization for all types (epic, feature, bug, task, chore); replaces `/epic-init` (BDL-021)
- **`BRIEF.md` template** — simplified doc format for bug/task/chore (one-approval flow)
- **255 new tests** (1408 total)

### Changed
- **`sync-check` CLI output** — now shows reason (symbols_changed, untracked_files, missing_modules) and details per stale entry (BDL-018)
- **`sync-check --json`** — structured JSON output with `reason` and `details` fields (BDL-018)
- **Routes/activity/tests integrated into reindex** — stored as JSON in `nodes.extra` during full and incremental reindex (BDL-017 BEAD-09, BEAD-10, BEAD-11)
- **Deep config integrated into bootstrap** — config data in root node `extra.config` (BDL-017 BEAD-13)
- **13 domain/service docs refreshed** — all documentation updated to match current code (BDL-019)
- **`.claude/commands/templates.md`** — stabilized: no numbered sections, strict status lifecycle (Draft/Approved/Done)
- **`.claude/CLAUDE.md`** — added `/task-init`, `/tech-writer`; updated file memory to include BRIEF.md

### Fixed
- **Symbol drift detection E2E** — `incremental_reindex()` now preserves `symbols_hash` baseline across reindexes (BDL-016)
- **`_compute_symbols_hash()` annotation query** — fixed to handle both `"ref_id"` and `["ref_id"]` JSON formats (BDL-018 BEAD-01)
- **Sync baseline preservation** — `_snapshot_sync_baselines()` preserves symbol hashes during full reindex (BDL-018 BEAD-01)
- **4 annotation mismatches** — `why.py` (was `impact-analysis`→`context-oracle`), `doctor.py` (was `doctor`→`infrastructure`), `watcher.py` (was `watcher`→`infrastructure`), `app.py` (was missing→`tui`) (BDL-020 BEAD-01)

## [1.5.0] - 2026-02-16

Smart Bootstrap v2, Doc Sync v2, 5 new languages, and a full documentation overhaul. 1153 tests.

### Changed
- **README.md + README.ru.md** — rewritten with new positioning: "Architecture as Code → Architectural Intelligence"; Agent Prime as flagship feature; real dogfooding examples; research references; full EN/RU parity
- **`docs/architecture.md`** — rewritten: 13 SQLite tables (was 7), 22 CLI commands (was 21), 9 import analysis languages (was 4); new sections: Rules Engine, Cache Architecture, Incremental Reindex, Health Snapshots, Agent Prime, Configuration
- **`.claude/CLAUDE.md`** — Beadloom dogfooding: `beadloom prime` as first session step, `beadloom ctx`/`why` for context discovery, expanded CLI reference (17 commands)
- **`.claude/commands/*`** — all 7 skills updated with Beadloom integration (`prime`, `ctx`, `why`, `search`, `lint --strict`)
- **Social preview** — `.github/social-preview.svg` for GitHub/messenger previews

### Added
- **README/doc ingestion** — `_ingest_readme()` extracts project description, tech stack, and architecture notes from README.md, CONTRIBUTING.md, ARCHITECTURE.md
- **Extended framework detection (18+)** — FastAPI, Flask, Django, Express, NestJS, Angular, Next.js, Vue, Spring Boot, Actix, Gin, SwiftUI, Jetpack Compose, React Native, Expo, and more
- **Entry point discovery** — `_discover_entry_points()` detects CLI tools (Click, Typer, argparse), server entry points, `__main__.py`, and `func main()` across 6 languages
- **Import analysis at bootstrap** — `_quick_import_scan()` infers `depends_on` edges between clusters from import statements (capped at 50)
- **Contextual node summaries** — `_build_contextual_summary()` combines framework, symbols, README excerpt, and entry points into rich summaries like "FastAPI service: auth — JWT auth, 3 classes, 5 fns"
- **Symbol-level drift detection** — `_compute_symbols_hash()` tracks SHA-256 of code symbols per ref_id; `check_sync()` detects semantic drift even when file hashes match
- **Doctor drift warnings** — `_check_symbol_drift()` and `_check_stale_sync()` surface drift/stale entries in `beadloom doctor`
- **Symbol diff in polish** — `_detect_symbol_changes()` shows drift warnings in `beadloom docs polish` output
- **`service-needs-parent` rule** — auto-generated require rule: every service node must have a `part_of` edge
- **Kotlin support** — `_load_kotlin()`, `_extract_kotlin_imports()` with stdlib filtering (kotlin.*, kotlinx.*, java.*, javax.*, android.*)
- **Java support** — `_load_java()`, `_extract_java_imports()` with static/wildcard imports and stdlib filtering
- **Swift support** — `_load_swift()`, `_extract_swift_imports()` with 35 Apple framework filters
- **C/C++ support** — `_load_c()`, `_load_cpp()`, `_extract_c_cpp_imports()` with 80+ system header filters; extended `_get_symbol_name()` for declarator chains
- **Objective-C support** — `_load_objc()`, `_extract_objc_imports()` with #import/#include and @import support; 48 system framework filters
- **306 new tests** (1153 total)

### Fixed
- **Reindex graph YAML detection** — `_graph_yaml_changed()` checks graph files before `_diff_files` to catch changes even with stale `file_index`
- **AGENTS.md template** — added `beadloom ctx <ref-id>` and `beadloom search "<query>"` CLI commands
- **Content-aware `setup_rules_auto()`** — detects beadloom adapter files vs user content; updates adapters, skips user files

## [1.4.0] - 2026-02-14

Agent Prime: cross-IDE context injection for AI agents. Full documentation audit.

### Added
- **`beadloom prime`** — output compact project context (architecture summary, health, rules, domains) for AI agent session start
- **`prime` MCP tool** — 10th tool; returns JSON context for agent sessions
- **`beadloom setup-rules`** — create IDE adapter files (`.cursorrules`, `.windsurfrules`, `.clinerules`) that reference `.beadloom/AGENTS.md`
- **AGENTS.md v2** — `generate_agents_md()` produces `.beadloom/AGENTS.md` with MCP tool list, architecture rules from `rules.yml`, and `## Custom` section preservation
- **`prime_context()`** — three-layer architecture: static config + dynamic DB queries with graceful degradation
- **`setup_rules_auto()`** — auto-detect IDEs by marker files; integrated into `beadloom init --bootstrap`
- **`agent-prime` graph node** — 20th node in architecture graph (feature under onboarding)
- **Architecture lint CI** — `.github/workflows/beadloom-aac-lint.yml` runs `beadloom lint --strict` on PRs
- **Known Issues section** — README.md and README.ru.md link to UX Issues Log
- **36 new tests** (847 total)

### Fixed
- **12 documentation discrepancies** — README/architecture/CLI/MCP docs all said "18 commands, 8 tools" (actual: 21 commands, 10 tools); `docs polish` documented `--ref` flag but code uses `--ref-id`; MCP docs used `ref_ids` (array) but schema is `ref_id` (string); `list_nodes` had undocumented `kind` filter; onboarding README missing 3 exported functions; infrastructure README missing 5 reindex pipeline steps; getting-started.md said "Python only" (supports 4 languages); root graph node said "v1.3.0" (was v1.3.1)
- **`docs/getting-started.md`** — fully rewritten to reflect current bootstrap flow (rules, skeletons, MCP, IDE adapters, sync-check)
- **`.beadloom/README.md`** — added missing `get_status` and `prime` to MCP tools list

## [1.3.1] - 2026-02-13

Onboarding Quality: 10 bug-fixes from dogfooding on real projects (core-monolith, secondary-system).

### Fixed
- **Doctor 0% coverage** — `generate_skeletons()` writes `docs:` field back to services.yml (core-monolith: 0% → 95%, secondary-system: 0% → 83%)
- **Lint false positives** — empty `has_edge_to: {}` matcher (any node), removed `service-needs-parent` rule (core-monolith: 33 → 0 violations)
- **Polish deps empty** — `generate_polish_data()` reads `depends_on` edges from SQLite post-reindex
- **Polish text = 1 line** — new `format_polish_text()` with node details, symbols, deps, doc status
- **Preset misclassifies mobile** — `detect_preset()` checks React Native/Expo/Flutter before `services/` heuristic
- **Missing parser warning** — `check_parser_availability()` warns about missing tree-sitter grammars in bootstrap/reindex
- **Generic summaries** — detects Django apps, React components, Python packages, Dockerized services
- **Parenthesized ref_ids** — strips `()` from Expo router dirs (`(tabs)` → `tabs`)
- **Reindex ignores parsers** — parser fingerprint tracked; new parsers trigger full reindex
- **Skeleton count** — CLI shows "N created, M skipped (pre-existing)"

## [1.3.0] - 2026-02-13

Plug & Play Onboarding: from install to first useful result in one command.

### Added
- **`beadloom docs generate`** — generate doc skeletons (architecture.md, domain READMEs, service pages, feature SPECs) from knowledge graph
- **`beadloom docs polish`** — structured JSON/text output with code symbols, Mermaid diagrams, and AI enrichment prompts for agent-driven doc polish
- **`generate_docs` MCP tool** — 9th tool, returns polish data as JSON for AI agents
- **Auto-rules generation** — `beadloom init --bootstrap` now generates `rules.yml` with structural require rules (domain-needs-parent, feature-needs-domain, service-needs-parent)
- **Auto MCP config** — bootstrap auto-detects editor (Cursor, Windsurf, Claude Code) and creates `.mcp.json`
- **Root node + project name detection** — reads name from pyproject.toml/package.json/go.mod/Cargo.toml with directory fallback
- **Enhanced init output** — summary with Graph/Rules/Docs/MCP/Index counts and Next steps
- **Doc-generator feature** — added to knowledge graph under onboarding domain
- **13 end-to-end integration tests** — full pipeline from bootstrap through docs generate/polish with idempotency checks

## [1.2.0] - 2026-02-13

DDD restructuring: code, docs, and knowledge graph now follow domain-driven design.

### Changed
- **Code → DDD packages** — flat modules reorganized into 5 domain packages (`infrastructure/`, `context_oracle/`, `doc_sync/`, `onboarding/`, `graph/`) with `__init__.py` re-exports
- **Package names aligned to docs** — `context/` → `context_oracle/`, `sync/` → `doc_sync/`, `infra/` → `infrastructure/`
- **Services layer** — `cli.py` and `mcp_server.py` moved into `services/` package
- **Loose files absorbed** — `doctor.py` → `infrastructure/`, `watcher.py` → `infrastructure/`, `why.py` → `context_oracle/`
- **Docs → domain-first layout** — `docs/` restructured into `domains/`, `services/`, `guides/` directories
- **Knowledge graph updated** — 18 nodes (5 domains, 3 services, 9 features, 1 root), 32+ edges reflecting DDD structure; `doctor` and `watcher` reclassified as features under `infrastructure`
- **Architecture lint rules** — 2 rules: `domain-needs-parent`, `feature-needs-domain`
- **CLI reference** — all 18 commands documented
- **MCP docs** — all 8 tools documented
- **Doc coverage 100%** — SPEC.md for all 9 features (cache, search, why, graph-diff, rule-engine, import-resolver, doctor, reindex, watcher) + TUI service doc
- **`guides/ci-setup.md`** — linked to `beadloom` root node in knowledge graph
- **`architecture.md` constraints** — updated for multi-language support and configurable paths
- **`import-resolver` summary** — corrected from "Python import analysis" to "Multi-language import analysis"
- **README.md + README.ru.md** — abstract examples replaced with real Beadloom data (architecture rules, docs tree, context bundle example)

### Fixed
- Circular import in `graph/linter.py` resolved via lazy import of `incremental_reindex`
- Integration tests updated for new graph structure (domain nodes instead of `linter` node)

## [1.1.0] - 2026-02-12

Improved import analysis and broader project support.

### Added
- **Deep import analysis** — `depends_on` edges generated from resolved imports between graph nodes
- **Hierarchical source-prefix resolver** — handles Django-style imports (`apps.core.models`), TypeScript `@/` aliases, and nodes with/without trailing slash
- **Auto-reindex after init** — no more manual `beadloom reindex` needed after `--bootstrap` or interactive setup
- **Noise directory filtering** — `static`, `templates`, `migrations`, `fixtures`, `locale`, `media`, `assets` excluded from architecture node generation

### Fixed
- Source dir discovery expanded (`backend`, `frontend`, `server`, `client`, etc.) with fallback to scanning all non-vendor dirs
- `reindex` and `import_resolver` now read `scan_paths` from `config.yml` instead of hardcoding `src/lib/app`
- `node_modules` and other junk dirs filtered from recursive scans
- `.vue` files recognized as code extensions

## [1.0.0] - 2026-02-11

Architecture as Code: Beadloom evolves from documentation tool to architecture enforcement platform.

### Added
- **`beadloom lint`** — validate code against architecture boundary rules defined in YAML
- **Rule engine** — declarative `rules.yml` with `deny` and `require` directives
- **Import resolver** — static analysis for Python, TypeScript/JavaScript, Go, and Rust
- **Agent-aware constraints** — `get_context` MCP tool returns active rules alongside context
- **CI architecture gate** — `beadloom lint --strict` exits 1 on violations

### Fixed
- `beadloom ui` traceback when textual not installed (lazy import guard)
- TUI shows real data — edges, docs, sync status, proper counts
- `beadloom reindex` shows "up to date" with DB totals when nothing changed
- `beadloom watch` traceback when watchfiles not installed

## [0.7.0] - 2026-02-11

Developer Experience: interactive exploration and real-time feedback.

### Added
- **`beadloom ui`** — interactive terminal dashboard (Textual) for browsing domains, nodes, and edges
- **`beadloom why REF_ID`** — impact analysis showing upstream deps and downstream dependents
- **`beadloom diff`** — show graph changes since a git ref (nodes/edges added, removed, modified)
- **`beadloom watch`** — auto-reindex on file changes during development

## [0.6.0] - 2026-02-10

Performance and agent-native evolution: caching, search, and write operations.

### Added
- **L1 in-memory cache** — ContextCache integrated with MCP server for token savings
- **L2 SQLite cache** — persistent `bundle_cache` table survives MCP restarts
- **Incremental reindex** — `file_index` tracks hashes, only re-processes changed files
- **Auto-reindex in MCP** — detects stale index, triggers incremental reindex before responding
- **FTS5 full-text search** — `beadloom search` command + MCP `search` tool
- **MCP write tools** — `update_node`, `mark_synced` for agent-driven graph updates
- **`beadloom search`** — CLI command for searching nodes, docs, and code symbols

### Removed
- `sync-update --auto` flag and `llm_updater.py` — Beadloom is now fully agent-native with no LLM API dependency

## [0.5.0] - 2026-02-10

Team adoption: CI integration, health metrics, and external linking.

### Added
- **CI integration** — `beadloom sync-check --porcelain` for GitHub Actions / GitLab CI
- **Health dashboard** — `beadloom status` shows doc coverage trends, stale doc counts
- **`beadloom link`** — connect graph nodes to Jira, GitHub Issues, Linear
- **MCP templates** — ready-made `.mcp.json` snippets for Cursor, Claude Code, Windsurf

## [0.4.0] - 2026-02-10

Lower the barrier: from install to useful context in under 5 minutes.

### Added
- **Architecture presets** — `beadloom init --preset {monolith,microservices,monorepo}`
- **Smarter bootstrap** — infers domains from directory structure, detects common patterns
- **Zero-doc mode** — graph-only workflow without any Markdown files
- **Interactive bootstrap review** — confirm/edit generated nodes before committing

## [0.3.0] - 2026-02-10

Foundation and agent-native pivot.

### Added
- **AGENTS.md generation** — `beadloom reindex` produces `.beadloom/AGENTS.md` for AI agents
- **README rewrite** — new positioning, value proposition, comparison table
- **README.ru.md** — Russian translation

### Changed
- Deprecated `sync-update --auto` in favor of agent-native workflow
- Annotation coverage improved to 100% across all modules

## [0.2.0] - 2026-02-09

Extended features: interactive sync, multi-language indexing, PyPI publishing.

### Added
- `sync-update --auto` — LLM-assisted doc update (later removed in v0.6)
- Interactive `sync-update` review mode
- Multi-language tree-sitter indexer
- Init wizard for guided project setup
- PyPI publishing workflow with dynamic versioning
- End-to-end test suite

### Fixed
- Module-level annotation parsing
- Doc ref_map collision on duplicate prefixes
- Heading collision in Mermaid graph output

## [0.1.0] - 2026-02-09

Initial release: Context Oracle + Doc Sync Engine.

### Added
- **Context Oracle** — BFS graph traversal, deterministic context bundles
- **Doc Sync Engine** — code-to-doc relationship tracking, staleness detection
- **Knowledge graph** — YAML-based node/edge definition
- **MCP server** — stdio transport with `get_context`, `get_graph`, `list_nodes`, `sync_check`, `get_status`
- **CLI** — `init`, `reindex`, `ctx`, `graph`, `status`, `doctor`, `sync-check`, `sync-update`
- **Tree-sitter indexer** — Python source code annotation extraction
- **Git hooks** — pre-commit doc sync check
- mypy strict mode, 91% test coverage, MIT license
