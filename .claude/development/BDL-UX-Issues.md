# BDL UX Feedback Log

> Collected during development and dogfooding.
> Total: 161 issues | Open: 43 | Improvements: 20 | Excluded: 7 | Closed: 91
> 2026-08-20 (v2.2.0 release): Opened #161 — `docs audit` verifies numeric FACTS but never checks that a documented identifier still EXISTS, so documentation can name a function the code no longer has and the gate stays green. Found the hard way: two functions removed while narrowing the `surface_registry` port stayed documented in this very release's branch, past a 6/6 gate, and were caught by a hand-written ten-line grep during an unrelated question. Also: #160 (AsyncAPI ingestion) deferred with its plan recorded in ROADMAP. Total 160→161, Open 42→43.
> 2026-08-19 (BDL-060 S4 dogfood — the owner clicking nodes in the architecture map): CLOSED #159 (imports below a file's top level were never extracted — 460 nested, 231 first-party, about a third of all imports; making them visible took `depends_on` from 51 to 146 edges and surfaced SIX real boundary violations at once, all one pattern: domain/application code reaching UP into `services` to introspect the live CLI/MCP surface, fixed by inverting it through a `surface_registry` port). Opened #160 (🔴 **AsyncAPI ingestion is documented as a capability but wired to nothing** — `extract_payload_body` is called by ZERO code paths in `src/`; the function works and is tested, but no document ever reaches it, so the SPEC's "teams on AsyncAPI ingest the payload schema via…" describes a capability the product does not deliver. It survived dev + test + review + tech-writer beads and a green gate because each verified the FUNCTION and none asked whether anything calls it). Total 158→160, Closed 90→91.
> 2026-08-19 (BDL-UX #144/#157 fixed together): CLOSED #144 and #157. Both had the SAME root — attribution by raw path prefix — so they were fixed once, in one place: **a file belongs to exactly one node, the most specific one whose `source` covers it** (`infrastructure/repository`), now shared by `max_symbols`/`max_files`, the architecture view's symbol badge, node-page symbol listings and `import_resolver`'s file→node attribution. Three things fell out that no single-surface patch would have reached: (1) a node whose source IS a file never owned that file, so its imports were credited to the enclosing directory's node; (2) derived `depends_on` edges between a node and its `part_of` ancestor are a category error and are no longer emitted — 5 of 14 edges were this noise, and they were manufacturing node-level cycles that do not exist at module level; (3) with honest ownership the dependency graph went 14 → 24 edges, surfacing real feature-level dependencies (`graph-loader → federation`, `mcp-server → reindex`, `site-generation → graph`) that prefix attribution had collapsed into their parents. Opened #158 (the subtree-size signal the new metric no longer carries). Total 157→158, Open 42→41, Closed 88→90.
> 2026-08-19 (BDL-060.15 review): Opened #157 (HIGH — a package that carries its `# beadloom:feature=` annotation in `__init__.py` (the natural place after BDL-059's decomposition) gets its node `source` recorded as that FILE, so every symbol read sees an empty façade: **5 nodes, 228 symbols invisible** on Beadloom's own graph. All five readers agree on 0, so it must be fixed at the source, not in a reader. Consequence in the #146 family: `max_symbols` can never fire on those nodes — a size rule reporting clean because it is looking at nothing — which also distorts the very `domain-size-limit` recalibration the S4 review was assessing). Total 156→157, Open 41→42.
> 2026-08-19 (dependency currency pass): CLOSED #150 — REPRODUCED on Beadloom's own tree and FIXED. The reporter's minimal case does not reproduce today (core 0.26.0 loads all ten grammar wheels and parses small files cleanly through `get_lang_config`/`extract_symbols`, and a fresh `pip install beadloom[languages]==2.1.0` resolves a pair that survives `beadloom init` + `reindex` on a 5-file project) — the crash needs VOLUME: the full test suite segfaulted inside `_index_code_files` partway through a real repo-wide reindex. That sharpens the issue rather than softening it: **loading a grammar is not evidence that the pairing is safe**, which is exactly why it survived a gate. Fixed by `tree-sitter>=0.25,<0.26` plus two guards in `tests/test_grammar_guard.py` (the declared pin must carry an upper bound; the INSTALLED core must fall inside it, so a local upgrade cannot pass the suite while claiming an untested range). Still open from #150's ask: the from-scratch-resolver CI job. Open 42->41, Closed 87->88.
> 2026-08-19 (design input): Opened #156 — 🔴 **context rot** gives #153 a measurable root: recall of a long instruction file DEGRADES as context fills, i.e. exactly when a long session needs the rules most, so shrinking the scaffolded `CLAUDE.md` is mechanism and not tidiness; the design target is *"the smallest possible set of high-signal tokens"* at the *"right altitude"* between brittle hardcoding and vague guidance. Also: role agents should return a bounded distilled result (~1-2k tokens) as a stated contract; and 🔴 **selective escalation is a second graph-derived feature** — blast radius, boundary crossings and invariant-bearing nodes decide what must stop for a human, turning "escalate when unsure" into a harness rule. Improvements 19->20, Total 155->156.
> 2026-08-19 (design input): Opened #155 — multi-agent failure modes and long-running-harness patterns from three current Anthropic publications. 🔴 Headline: **wave shape should be DERIVED FROM THE GRAPH** — parallel agents pay off on independent subgraphs (266 vs 21 vulnerabilities found) and rot on shared code with rich interdependencies; only Beadloom holds the code-level interdependence needed to decide. Also: conformity cascades (18/30 agents chose the same branch name; identical context ⇒ identical mistakes, and shared state is the vector); a review role fed the author's summary converges on it (hidden-profile groups scored 17–36% vs ~100%), so the reviewer must see diff+spec BEFORE advocacy; named long-running failure modes led by *premature victory declaration*; and state files in JSON because agents corrupt Markdown. Improvements 18→19, Total 154→155.
> 2026-08-19 (design input): Opened #154 — oversight patterns for the #153 enforcement epic, drawn from Anthropic's public *Risk Report: August 2026*: separate asynchronous monitoring from blocking interventions and label which is which; claim raised DETECTABILITY rather than prevention; ship a machine-readable "does not cover" note with every gate; make "diff vs its own stated purpose" a check type (Beadloom holds the stated purpose); 🔴 spawning must narrow authority, never widen it (their incident: legacy instructions propagated `--dangerously-skip-permissions` to child agents, detected only by the damage); 🔴 shared agent context propagates DECISIONS — one agent's silent scope-narrowing spread to later agents while metrics looked green, found 3 days later by a human; 🔴 gates need a LIVENESS proof — their filter ran misconfigured for several model generations "without anyone noticing", the same defect as #61. Improvements 17→18, Total 153→154.
> 2026-08-19 (dogfood — DDD project, one full working session through the scaffolded flow): Opened #153 (HIGH, EPIC PROPOSAL — the scaffolded multi-agent flow is advisory and therefore silently skipped: measured 0/6 beads reviewed, 1/6 mutation-gated, 0 `.feature`, 0 `/task-init`, while the ONE rule backed by a machine check blocked the agent 4 times in the same session. Root: `CLAUDE.md` is delivered as a user message the model may deem inapplicable, and compliance degrades with instruction count — cf. anthropics/claude-code#32163. Proposal: ship blocking `Stop`/`PreToolUse` hooks with the flow, derive their conditions FROM THE GRAPH, make strictness configurable per rule and work kind, give exclusions a named reason + exit condition, and let roles run as independent subagents). Improvements 16→17, Total 152→153.
> 2026-08-18 (dogfood — DDD project, wiring the beadloom gate into GitHub Actions CI): Opened #150 (HIGH — `tree-sitter` unbounded upper pin pairs core 0.26 with 0.25-ABI grammars, so a FRESH install segfaults with zero output on every parsing command; invisible to anyone who does not reinstall, since existing environments keep a matching pair — measured on two isolated venvs, reproduces on macOS as SIGBUS too, so it is a dependency bug, not an environment one) #151 (HIGH — the published release lags `main`: BDL-059's role templates are unreleased, so a fresh install reports drift against projects scaffolded from `main`, and `--fix` would rewrite them back to the OLDER templates: 42 deletions / 0 insertions, deleting a standing engineering paradigm. Diagnosed only via an env-skew trap: exit 1 from a PyPI install vs exit 0 from a source install, same self-reported version 2.1.0, byte-identical files) and #152 (MEDIUM — structural: role overlays resolve only INSIDE the installed package, so a project has no supported place for its own additions; that is *why* the paradigm had to go upstream, which is what coupled a downstream gate to an unreleased change). Common thread with #142/#146/#147: a verb that reads as a check either changes state or reports success for work it did not do. Total 149→152, Open 39→42.
> 2026-08-05 (dogfood — DDD project, exposing the READ-ONLY beadloom surface to an agent): Opened #147 (HIGH — plain `lint` MUTATES `beadloom.db`; measured by DB sha256 before/after, only `--no-reindex` is read-only, and `--strict` is additionally required for a non-zero exit on an error-severity violation, so a caller checking the exit code alone reads a real boundary break as clean), #148 (MEDIUM — `lint` output shape depends on TTY: the documented `N violations, M rules evaluated` summary is absent through a pipe, with no flag to select a stable contract), #149 (LOW — `graph --format c4 --level component --scope <leaf>` exits 0 with a single empty `C4Container`, giving no way to distinguish "no internals" from "here are the internals"). Common thread with #142/#146: the tool reports success for work it did not do, or changes state under a verb that reads as a check. Total 146→149, Open 36→39.
> 2026-08-03 (dogfood — DDD project, splitting an oversized vertical-module node): **THIRD in-the-wild confirmation of #142** (incremental `reindex` does not refresh import edges): a slice added a runtime import that closed a `A → B → runtime-app → A` module cycle; `reindex && lint --strict` reported **0 violations** through the whole verification pass — the coordinator's own independent re-run included — and the cycle was only surfaced later by a full rebuild (`rm .beadloom/beadloom.db && reindex`) during an unrelated refactor. Note the compounding factor: the false-green survived a *deliberately sceptical* review because the documented loop (`reindex` → `lint`) is itself the thing that lies; there is no signal distinguishing "clean" from "stale import graph". Reinforces the #142 fix priority (Gate must full-reindex, or `lint` must refuse a stale graph). Opened #146 (HIGH — `component` nodes contribute NO sync-check pairs at all, so their docs are never freshness-checked and the gate's green reads as "fresh" when it means "not looked at"; found when a wave's "sync-check by node X — clean" turned out to mean "zero pairs exist"), #144 (MEDIUM — `max_symbols` counts by source-path PREFIX without subtracting nested nodes, so carving a subpackage into its own node does NOT relieve the parent — the natural remedy for an oversized node silently does nothing), #145 (MEDIUM — `ctx <ref> --json` returns the repo-wide `code_symbols` array, not the node's, so an agent sizing a node from its own context bundle reads garbage). Total 143→145, Open 33→35.
> 2026-07-23 (dogfood — DDD project, enforcing boundaries between equal-rank vertical modules): Opened #143 (HIGH — no native module-boundary / mutual-isolation rule primitive. Enforcing that each vertical module's internals are reachable only via its public facade (not a sibling's `usecases/`/`adapters/`) requires hand-written **O(N²)** `forbid_import` path-glob rules — one per ordered module pair per internal layer. Root causes in the rule engine: (a) `forbid_import.from`/`.to` accept only a SINGLE glob string each — no list, and fnmatch has no brace-expansion, so `src/bob/{a,b}/**` is literal; (b) "all modules except X" is expressible only via first-char negation `[!x]`, which SILENTLY mis-groups two modules sharing an initial letter — e.g. two `c…` modules (`coding`/`capabilities`) become indistinguishable, so the isolation glob wrongly excludes BOTH → a real cross-module import goes uncaught; (c) `domain-root ↛ adapters` cannot be expressed cleanly because fnmatch `*` spans `/` (workaround `<mod>/[!au]*` drops root files starting a/u — accepted only because they're import-leaves). No existing rule type derives pairwise isolation from node tags: `LayerRule` is a linear top-down order (not mutual isolation), `ForbidEdgeRule`/`DenyRule` matchers select one from-group + one to-group (no same-tag-different-node correlation). Workaround adopted downstream: a ~60-line `scripts/gen_boundary_rules.py` emitting explicit-path rules into a marker-delimited region with a `--check` mode. Proposal: a `module_isolation` rule type `{tag: <module-tag>, internal_layers: [usecases, adapters]}` that the engine expands into pairwise isolation + internal-layering from each node's `source` path — removes both the O(N²) hand-generation and the char-class collision at the core). Total 142→143, Open 32→33.
> 2026-07-23 (dogfood — DDD project, domain-first vertical-module migration): Opened #142 (MEDIUM — incremental `beadloom reindex` does NOT refresh import edges: after moving a file and adding a boundary-violating import, `reindex` prints "Imports: 0" and the `code_imports`/`depends_on` edges are stale, so `beadloom lint --strict` does NOT catch the fresh violation — the documented `reindex && lint` loop silently passes a real boundary break. `reindex --full` is required to re-derive import edges; only the full CI build catches it. Sibling of #112 (incremental `Symbols: 0`). Impact: `forbid_import`/layer rules give false-green during iterative dev; a boundary violation can slip through local pre-commit and only surface in CI. Fix: incremental reindex should re-extract imports for changed files, or `lint` should warn when import edges are staler than the working tree. **🔴 SEVERITY UPGRADE MEDIUM→HIGH (2026-07-28, confirmed in the wild): if pre-commit AND pre-push AND CI all run the INCREMENTAL path, a real `no-dependency-cycles`/`forbid_import` violation reaches the protected main branch with a fully GREEN gate — observed a module-cycle merged undetected across a whole PR, surfaced only later by a manual `reindex --full` on a downstream branch. The "green CI" guarantee is unsound while any gate stage uses incremental reindex. Fix priority: the Gate (`ci`) MUST full-reindex before `lint`, or lint must refuse to pass on a stale import graph.**). Total 141→142, Open 31→32.
> 2026-07-02 (dogfood — DDD project, detailed-graph + AaC-rules foundation): Opened #139 (MEDIUM — `docs generate` writes STRAY files to the project ROOT: running it produced a root-level `architecture.md` + a root `domains/` dir with layer READMEs, alongside the correct `docs/**` output — a cwd/base-path bug that pollutes the repo root and shadows the real `docs/architecture.md`), #140 (HIGH — misleading remediation for `untracked_files` staleness: `sync-check`/`ci` tells the operator to run `beadloom sync-update <ref>`, but for a directory-source node with a freshly-generated skeleton there is no `sync_state` pair, so `sync-update` returns "No sync pairs found; nothing to re-baseline" and CANNOT clear it — `untracked_files` is a per-file coverage gap, not hash drift; the only fixes are file-level `# beadloom:feature=` annotations or `<!-- beadloom:track= -->` doc markers, which the remediation string never mentions → operator dead-end. Also: a linked EMPTY skeleton then fails on `missing_modules`, so `docs generate`'d skeletons cannot pass `beadloom ci` until hand-filled — generating+linking a skeleton makes the Gate RED with no green intermediate state), #141 (LOW — `docs generate` re-serializes/patches `.beadloom/_graph/services.yml` as an unprompted side-effect, writing outside its docs output dir). Total 138→141, Open 28→31.
> 2026-07-02 (dogfood — DDD project docs audit): Opened #138 (MEDIUM — `docs generate` silently no-ops on a coarse graph: a project accumulated a ~4000-line `architecture.md` / ~100 sections because its graph had few nodes w/ blanket `beadloom:domain=` tags → 0 feature/component nodes → nothing to emit, exit 0, no warning; + `component`→`DOC.md` not generated (parity gap w/ feature SPEC); + no monolith-drift detector). Total 137→138, Open 27→28.
> 2026-06-18 (dogfood — adopter flow re-init on a binary-asset, non-English project): Opened #135 (HIGH — `init` crashes with `UnicodeDecodeError` on binary/venv files), #136 (MEDIUM — scaffolded flow is English-only + templates not overlay-aware), #137 (LOW — cross-major flow re-init leaves orphaned/skipped command files). Total 134→137, Open 24→27.
> 2026-06-15 (BDL-056/057 + v2.1.0 release): CLOSED #130 (rule-type dataclass names fixed in `architecture.md`, BDL-057 SPEC-fill), #131 (all sub-items fixed in v2.1.0: `--non-interactive` removed from getting-started, DDD domain count corrected, CONTRIBUTING `your-org`→`zoologov` + release section added), #121 (RU `docs audit` false positive now suppressed via `.beadloom/config.yml` `docs_audit.ignore` — BDL-057.6; root-cause classifier weakness tracked in ROADMAP P3 "Semantic docs audit"). Opened #132 (`setup-agentic-flow --force` in Beadloom's own repo corrupts the vendored `CLAUDE.md` `__BEADLOOM_PROJECT_NAME__` placeholder) and #133 (per-worktree `beadloom.db` baseline → mass false re-baseline when integrating parallel worktree waves; relates #118). Total 131→133, Open 24→23, Closed 84→87.
> 2026-06-10 (BDL-047 / F4.1 AI tech-writer): CLOSED #106 (non-interactive `sync-update --yes`/`--all` — the F4.1 fixpoint primitive, W1), #112 (incremental reindex `symbols_indexed` now backfilled to the live DB total per #88), and #127 (the `doc_generator.py` `except sqlite3.OperationalError: pass` swallows are gone — note `git_activity.py:251` `except ValueError: pass` + the broader onboarding `Any` concentration remain, deferred). Total 131, Open 27→24, Closed 81→84.
> 2026-06-04 (post-v1.10.0 ROADMAP revision): Opened #122–#131 — engineering/test/doc debt from the comprehensive product review (`archive/REVIEW-2.md` §2/§3/§4), spot-verified at HEAD. Tracked here; cross-referenced from `ROADMAP.md` (Technical debt section). Total 121→131, Open 17→27.
> 2026-06-02 (BDL-045): Opened #121 (LOW — `docs audit` metric classification is English-keyword-based, so it mislabels numbers in non-English docs: `README.ru.md` "14 инструментов" (MCP) is reported as `cli_command_count 14→34`, a false positive — the English README's same "14" is correctly `mcp_tool_count` OK. The number is right; the classifier just can't read Russian. Either localize the keyword map or skip non-English files in the audit). Total 120→121, Open 16→17.
> 2026-06-02 (BDL-043 fix): CLOSED #120 — `dashboard.data.json` 404'd on GitHub Pages (widgets blank): the generator wrote it to the VitePress srcDir root (`site/`), which VitePress does NOT copy to the built `dist/` (only `site/public/` is copied verbatim); the dev server masked it by serving srcDir. FIXED: emit to `site/public/dashboard.data.json` → copied to dist root → the widgets' `withBase("/dashboard.data.json")` fetch resolves in the static build. Another "works in dev, breaks in the static build" class (cf. the F4 dead-links + F4.4 mermaid render) — the dogfood must hit the DEPLOYED/built site, not just `docs:dev`. Total 119→120, Closed 80→81.
> 2026-06-02 (BDL-041 F4.4 BEAD-05): VERIFIED #117 (dogfood SUCCESS — F4.4 render fixes: the two F4 Mermaid bugs are fixed and the generation-time guard passes the real 26-diagram site with 0 issues; `npm run docs:build` exit 0; dashboard mounts the 4 ECharts widgets via `<ClientOnly>` with honest text fallback; `dashboard.data.json` carries `trends` (2 real points, sparse-honest) + 7 `recommendations`; automated render-validation green (build exit 0, no page-HTML error markers), live UX pan/zoom + charts PENDING owner re-check in-browser on the fixed site). Opened #118 (process: parallel dev subagents in a SHARED working tree don't conflict on disjoint *files* but DO collide on the pre-commit *hook* — it lints the whole tree, so one agent's commit catches the other's in-progress WIP; BEAD-02 had to `--no-verify` staging only its `site/**`. Mitigation: use git-worktree isolation for true parallel, or run dev beads sequentially; `merge-slot` serializes *who* commits but does not isolate tree state). Opened #119 (LOW: `graph` domain now 202 symbols > 200 `domain-size-limit` — non-blocking warning; F2/F3/F4 grew it via contracts.py/sdl.py/site_mermaid_guard.py etc.; candidate future split). Total 116→119, Open 14→16, Closed 79→80.
> 2026-06-02 (BDL-040 F4 BEAD-05): Dogfood — generated + built Beadloom's own VitePress site. CLOSED #113 (generator bug: `publish_docs` copied hidden/OS-junk like `docs/.DS_Store` into `site/docs/` — non-deterministic + pollution; FIXED: skip dot-prefixed path parts; RED→GREEN regression test). CLOSED #114 (lockfile: `site/package-lock.json` now committed → `npm ci` reproducible). CLOSED #116 (generator bug surfaced by the dogfood build: node-page doc links + `/docs/` nav target were dead in the built site — FIXED by rooting doc links at `/docs/` + emitting a generated `site/docs/index.md` landing page; node-free dead-link guards added; `npm run docs:build` now exit 0, no `ignoreDeadLinks`). VERIFIED #115 (dogfood SUCCESS — 57 files, honest-by-construction dashboard matched `beadloom ci`, build green). Total 115→116, Open 15→14, Closed 77→79.
> 2026-06-02 (BDL-039 F3 BEAD-09): Opened #112 (incremental reindex displays `Symbols: 0` — per-run delta, not backfilled like nodes/edges per #88; cosmetic, zero gate impact). Total 111→112, Open 12→13.
> 2026-06-02 (BDL-039 F3 BEAD-06): VERIFIED #109 #110 #111 (dogfood SUCCESS — the F3 gate BLOCKS all three break-classes: boundary violation, cross-service BREAKING, drifted agent-config — each with a non-zero exit + agent-actionable output). Committed anonymized fixtures under `tests/fixtures/f3_gate/`. See Closed §BDL-039. Total 108→111, Closed 73→76.
> 2026-06-01 (BDL-038 F2 BEAD-08): VERIFIED #107 (live GraphQL contract mismatch caught before ship — the F2 success criterion) + #108 (paradigm-agnostic FSD round-trip + external native modules + nested company-landscape). See Closed §BDL-038. Closed 71→73.
> 2026-06-01 (BDL-038 F2 BEAD-01): Opened #105 (domain doc re-stales against all member files when one file is added) + #106 (no non-interactive `mark_synced` CLI). Open 10→12.
> Last reviewed: BDL-037 (F1: Federation Foundation)
> 2026-06-01 (BDL-037 F1): CLOSED #100 #101 #102 #103 (federation dogfood findings — FIXED in BEAD-09, commit d48bfeb) and #104 (federation dogfood SUCCESS — VERIFIED, BEAD-05). See Closed §BDL-037. Open 15→10, Closed 66→71.
> 2026-05-30 (BDL-036 Phase 0): CLOSED #91 #88 #92 #93 #94 #86 #89 #90 #71 #98 (honesty gate — see Closed §BDL-036). Opened #99 (repo-wide doc refresh — sync-check has ~30 pre-existing stale doc pairs unrelated to Phase 0; the sync-check *mechanism* is now honest, the doc *content* needs a dedicated pass). Still open: #72, #73, #95, #97 (external), #99. Exact category recount folded into #99.
> 2026-05-28: added #91–#96 from the comprehensive architecture/code review (see `.claude/development/REVIEW.md`); refined #88 root cause.

# Beadloom UX Issues

> Dogfooding feedback: issues, friction points, and improvement ideas collected while using Beadloom in the Bob project.
>
> **How to use:** Add entries during development. Each entry should include date, context, and severity.

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


150. [2026-08-18] [HIGH] 🔴 `tree-sitter` has no upper bound → a fresh install pairs core 0.26 with 0.25 grammars and every command SEGFAULTS with zero output

      **Severity:** high (a fresh install of the tool is dead on arrival; the failure is a native crash with no message, so it reads as an environment problem rather than a dependency one)
      **Command:** `beadloom reindex` (any command touching the parser)
      **Context:** Dogfood on a downstream project wiring `beadloom ci` into GitHub Actions. The step died with `Segmentation fault (core dumped) beadloom reindex`, exit 139, ~1s in, no output at all. It had been dismissed in the workflow comment as "native sqlite-vec/dolt segfaults on the runner — an environment problem, not a logical one" and silenced with `continue-on-error`, which is exactly the wrong conclusion and cost the project a day and a half of a gate that verified nothing.
      **Issue:** `pyproject.toml` pins `tree-sitter>=0.23` with **no upper bound**, while the grammar wheels (`tree-sitter-python` 0.25.0, and the nine other `tree-sitter-*` grammars) are built against the 0.25 language ABI. A fresh resolve now picks core **0.26.0**, and loading a grammar built for the older ABI crashes natively.
      **Measured** (two isolated venvs, Python 3.12, one factor changed):

      | `tree-sitter` | `tree-sitter-python` | result |
      |---|---|---|
      | 0.26.0 | 0.25.0 | **exit 138** (SIGBUS, macOS) / **139** (SIGSEGV, Linux) — zero output |
      | 0.25.2 | 0.25.0 | **exit 0** — `Symbols: 1620`, `Imports: 1477` |

      Note this is NOT platform-specific: it reproduces on macOS as SIGBUS. The "works on my machine, crashes on CI" impression came purely from **install date** — an environment installed before 0.26.0 was published still holds a matching pair, so every existing user keeps working and only new installs break. That makes the regression invisible to anyone who does not reinstall, including maintainers.
      **Expected:** cap the core to the ABI the shipped grammars target (`tree-sitter>=0.23,<0.26`) and add a CI job that installs the tool **from scratch** with a fresh resolver (no lockfile, no cache) and runs `reindex` on a fixture — the existing suite cannot catch this because it runs in an environment that already has a compatible pair pinned. Optionally, catch the load failure and emit a diagnostic naming the two versions instead of letting the process die silently.
      **Workaround adopted downstream:** `uv tool install beadloom --with "tree-sitter<0.26"`.

  </details>

### BDL-040 — F4: Living Knowledge Base + Visual Landscape (2026-06-02)

> F4 dogfooded (BEAD-05) by generating Beadloom's own VitePress site (`beadloom docs site --out site --federated <fed.json>`) — all three showcases: the honest-by-construction metrics dashboard, the 6-domain/4-service/14-feature architecture pages + diagrams, the 🌟 cross-repo landscape map (from a committed *anonymized* `federated.json` fixture — `catalog-service`/`storefront-web`/`commerce-platform`, NOT any private repo), and the published `docs/` with per-doc `doc_sync` validation badges. Dashboard numbers matched `beadloom ci` exactly (lint 0 / doctor 13 checks 0-err / sync-check fresh / federated repo_count 2, contract BREAKING 1).

- 113. ~~[MEDIUM] `docs site` publishes hidden/OS-junk files (e.g. `docs/.DS_Store`) into `site/docs/`~~ **FIXED (BEAD-05)** — `publish_docs`/`build_published_docs` (`application/site_published.py`) globbed `docs/**` and copied every non-`.md` file verbatim, sweeping up `docs/.DS_Store` (and any dotfile). That is non-deterministic per machine (breaks the byte-stable-regeneration guarantee) and pollutes the published site (57→56 files after the fix). Fix: skip any path whose parts start with `.`. RED→GREEN regression test `tests/test_site_published_docs.py::test_os_junk_files_not_published`.
- 115. ~~[INFO] F4 dogfood SUCCESS — `beadloom docs site` regenerates Beadloom's own 3-showcase site, deterministic + honest~~ **VERIFIED (BEAD-05)** — a single `beadloom docs site` run emits 57 files: `dashboard.md` + `dashboard.data.json`, `architecture.md`, one page per domain/service/feature with embedded Mermaid, `landscape.md` (anonymized `catalog-service`/`storefront-web` as clickable health-classed nodes), and the published `docs/` tree (with a generated `docs/index.md` landing page) carrying marker-delimited validation badges. Honest by construction: the dashboard JSON's lint/doctor/sync-check/federated numbers equal the live `beadloom ci` output (the same code path). Regeneration is byte-identical (determinism test). **Build now green:** `npm run docs:build` passed exit 0 after the dead-link fix (#116) — no `ignoreDeadLinks` suppression (honest source-of-truth).
- 116. ~~[MEDIUM] `docs site` node-page doc links + `/docs/` nav target are dead in the built VitePress site~~ **FIXED (BEAD-05 follow-up)** — the F4 dogfood `npm run docs:build` failed with 24 dead links. Root cause: node pages (`application/site_pages.py::_docs_section`) linked hand-written docs at `/<path>` (e.g. `/architecture.md`, `/domains/.../SPEC.md`), but Showcase C publishes the real `docs/` tree under `site/docs/<path>` — so the doc lives at `/docs/<path>`, not `/<path>`. The `docs` table stores paths relative to the source `docs/` dir, so a bare `/<path>` root was always wrong. Fix: `_published_doc_link` roots every node-page doc link at `/docs/` (normalising any stray `docs/` prefix to avoid `/docs/docs/…`). Separately, the `/docs/` Documentation nav target had no landing page (the source `docs/` has no root index), so `publish_docs` now emits a generated `site/docs/index.md` (sorted links to every published doc). No `ignoreDeadLinks` — the source of truth resolves honestly. RED→GREEN node-free guards: `tests/test_site_generator.py::test_generated_internal_links_resolve` (synthetic tree) + `::test_committed_site_tree_has_no_dead_links` (the real committed `site/` tree), both mirroring VitePress clean-URL / `.md`-optional / relative+absolute resolution so the regression is caught WITHOUT node.

### BDL-039 — F3: Tool-Agnostic Enforcement Everywhere (2026-06-02)

> F3 dogfooded (BEAD-06) with committed, anonymized, byte-stable fixtures under `tests/fixtures/f3_gate/` (synthetic role names — `catalog-service`/`storefront-web`/`commerce-platform`; NOT derived from any private repo; the real landscape stays in gitignored scratch). Three reproducible tests (`tests/test_f3_gate_dogfood.py`) prove the F3 success criterion: a CI gate blocks each break-class regardless of who wrote the code, with a non-zero exit AND agent-actionable output. This formalizes the live signal already seen in BEAD-04, where `beadloom ci`'s config-check caught a real stale auto-managed section in Beadloom's own AGENTS.md.

- 109. ~~[INFO] F3 dogfood SUCCESS — the gate BLOCKS a boundary violation, agent-actionable~~ **VERIFIED (BEAD-06)** — a fixture project whose `checkout` module imports `catalog` directly, breaching a committed `forbid_import` rule, runs through `run_ci_gate` (reindex → lint --strict). The gate's `lint` step → **FAIL**, `result.ok is False`, and the finding carries `rule: checkout-no-import-catalog` + a `remediation` hint ("remove the import …, or route it through an allowed intermediary"). `beadloom ci --format github` exits 1 and emits an inline `::error` annotation naming the rule — a violation an agent/CI can act on unaided (principle 4).
- 110. ~~[INFO] F3 dogfood SUCCESS — the gate BLOCKS a cross-service BREAKING, names the missing field~~ **VERIFIED (BEAD-06)** — two committed satellite `export` artifacts form a one-landscape break: producer `catalog-service` exposes GraphQL `{account, plan}`; consumer `storefront-web` references `{plan, subscriptionTier}`. `gate_failures(fed, {"breaking"})` → exactly one BREAKING contract failure whose `.missing == ("subscriptionTier",)`; the remediation hint names `subscriptionTier`. `beadloom ci --hub producer.json --hub consumer.json` exits 1, naming the `federate` step. Cross-language by NAME, no shared symbol.
- 111. ~~[INFO] F3 dogfood SUCCESS — the gate BLOCKS a drifted agent-config (AgentConfigAsCode)~~ **VERIFIED (BEAD-06)** — a project whose `.claude/CLAUDE.md` auto-managed section (between `beadloom:auto-start`/`auto-end`) is stale vs the graph. `check_config_drift` reports exactly one drift naming `.claude/CLAUDE.md` (which-file = agent-actionable); `run_ci_gate`'s `config-check` step → **FAIL**, `result.ok is False`; `beadloom ci --format json` exits 1 with the `config-check` step `status: FAIL`. Same class as the live BEAD-04 AGENTS.md catch — human prose outside the markers is never checked (no #73 false positive).

### BDL-038 — F2: Cross-Service Contract Graph (2026-06-01)

> F2 dogfooded (BEAD-08) on the real landscape via hand-curated, anonymized scratch slices (real repos NOT mutated; slices gitignored). Two parts: (A) live GraphQL contract between the web monolith and its web client; (B) a target-FSD round-trip for a second, separate mobile product. All names anonymized in this log; the real SDL was read read-only.

- 107. ~~[INFO] F2 dogfood SUCCESS — real GraphQL contract mismatch caught BEFORE it ships~~ **VERIFIED (BEAD-08)** — the F2 "what done looks like" criterion. `extract_surface` parsed the monolith's **real 3465-line `schema.graphql` → 266 surface names** (parser robust on production SDL). Modeled the monolith as the `graphql:WebAPI` **producer** (exposed = 266) and its web client as the **consumer** (references = a real subset). `federate` verdict = **CONFIRMED** while references ⊆ exposed. Then injected a realistic drift — the client still calls an operation the newer schema dropped — and `federate` flagged **`BREAKING: graphql:WebAPI — missing: <op>`**, naming the exact missing operation. Cross-language by NAME (TS client ↔ Python backend, no shared code symbol — G3). The 4 F1 AMQP contracts stayed **CONFIRMED** (no regression).
- 108. ~~[INFO] F2 dogfood SUCCESS — paradigm-agnostic FSD round-trip + external native modules + nested landscapes~~ **VERIFIED (BEAD-08)** — a second product (separate landscape) modeled on its **target FSD architecture** (`app→features→entities→shared`, kinds `page`/`feature`/`entity`/`repository`/`service`) round-tripped `export → federate` with **zero kind loss/rejection** (U1 — proves the BEAD-07 DB kind-CHECK drop on a real FSD shape). Its three **native bridge modules** (`lifecycle: external`, outside FSD) resolved to **EXTERNAL**, never DRIFT (U4). As a contract-less product in a **company-landscape** federate run alongside the web product, it produced **zero** mutual DRIFT/UNDECLARED (U5) — the report grouped satellites by landscape. Final company-landscape run: 5 contracts (4 AMQP + 1 GraphQL) CONFIRMED, 3 EXTERNAL edges, 37 OK, 0 false signals.

### BDL-037 — F1: Federation Foundation (2026-06-01)

> Cross-repo federation thin slice dogfooded on the real core-monolith ↔ integration-service RabbitMQ contract. The 4 findings below were raised during the dogfood (BEAD-05) and fixed in BEAD-09; #104 records the dogfood success.

- 100. ~~[HIGH] `beadloom export` silently drops cross-repo `@repo:` edges~~ **FIXED (BEAD-09, d48bfeb)** — new `foreign_edges` table (no FK) persists declared cross-repo edges; the loader writes them and `build_export` unions `edges` + `foreign_edges`, so intent-declared `@repo:` links reach the hub.
- 101. ~~[HIGH] Edge `kind` CHECK rejects `produces`/`consumes`~~ **FIXED (BEAD-09, d48bfeb)** — `produces`/`consumes` added to the `edges.kind` CHECK; the edges table is rebuilt (SQLite cannot `ALTER` a CHECK), additive and idempotent.
- 102. ~~[MEDIUM] UNIQUE `(src,dst,kind)` collapses multiple contracts on one node pair~~ **FIXED (BEAD-09, d48bfeb)** — `contract_key` (derived from `contract.message_type`) is now part of the edges primary key, so N contracts between one node pair survive instead of colliding.
- 103. ~~[LOW] `export` `commit_sha` leaks the host repo's HEAD for a nested project dir~~ **FIXED (BEAD-09, d48bfeb)** — `current_commit_sha` verifies `git --show-toplevel == project_root` and returns `null` (honest "unknown HEAD") for nested non-repo dirs.
- 104. ~~[INFO] Federation dogfood SUCCESS — both-sides confirmed on the real AMQP contract~~ **VERIFIED (BEAD-05, f2eaa94)** — end-to-end proof of F1: all 4 message types confirmed both-sides (`start_plan_version_upload` + `ensure_plans_folder_path` core→integration; `*_completed` integration→core), 16 edges all OK, `unresolved_refs: []`, per-satellite staleness reported. The reconciliation model (match by `message_type`; confirmed = produces ∧ consumes) maps cleanly onto the real contract.

### BDL-036 — Phase 0: Foundation / Honesty Gate (2026-05-30)

> The product now passes its own checks honestly. `lint --strict` exit 0 (rules at ERROR, 0 violations), `doctor` exit 0, 2608 tests pass, coverage 90.54%. Adversarial review (BEAD-08) = PASSED, no faked green.

- 91. ~~[CRITICAL] Beadloom violates its own architecture rules; lint --strict passes anyway~~ **FIXED (BEAD-03, 9c480d2)** — extracted orchestrators (reindex/doctor/debt_report/watcher) into a new `application/` DDD layer; `infrastructure/` is now domain-agnostic (zero domain imports); restored `no-dependency-cycles` + `architecture-layers` to `severity: error`; `lint --strict` genuinely clean.
- 88. ~~[HIGH] Incremental reindex returns 0 nodes~~ **FIXED (BEAD-02, 960f325)** — incremental path now reports true live-DB totals (was a display bug).
- 92. ~~[HIGH] doctor false version drift~~ **FIXED (BEAD-01, 960f325)** — reads in-tree `__version__`, not stale `importlib.metadata`.
- 93. ~~[LOW] AGENTS.md MCP tool count drift (13 vs 14)~~ **FIXED (BEAD-01, 960f325)** — single-source `mcp_tools` catalog pinned to live registry by a drift-guard test.
- 94. ~~[MEDIUM] Over-broad except Exception~~ **FIXED (BEAD-02, 960f325)** — narrowed to `sqlite3.OperationalError` (missing-table only).
- 86. ~~[HIGH] YAML edges silently produce 0 nodes~~ **FIXED (BEAD-04, 960f325)** — loader raises `GraphParseError` with file+line on malformed YAML; flow-style edges parse correctly.
- 89. ~~[MEDIUM] sync-check false untracked_files~~ **FIXED (BEAD-06, 960f325)** — file-level annotations on symbol-less modules now count as tracking signals; genuine 100% reachable (E2E test).
- 90. ~~[MEDIUM] beadloom:track markers inert~~ **FIXED (BEAD-06, 960f325)** — track markers now count as a doc→file binding signal.
- 71. ~~[MEDIUM] bootstrap generates rules that fail lint out-of-the-box~~ **FIXED (BEAD-07, b4d5e62)** — generated rule is `feature-needs-parent` (`has_edge_to: {}`); fresh bootstrap lints clean; regression test added.
- 98. ~~[LOW] test_git_activity date-relative flake~~ **FIXED (BEAD-10, b4d5e62)** — `_SAMPLE_GIT_LOG` uses relative dates; deterministic windows.

99. [2026-05-30] [MEDIUM] Repo-wide documentation drift — sync-check has ~30 pre-existing stale doc pairs

    **Severity:** medium
    **Command:** `beadloom sync-check`
    **Context:** Surfaced honestly during BDL-036 Phase 0. After fixing the sync-check *mechanism* (#89/#90) and restoring honest checks, `sync-check` still reports ~30-32 stale doc-code pairs (graph, tui, onboarding, doc-sync, etc.). Investigation showed the bulk is **accumulated content drift from prior releases**, largely unrelated to Phase 0 changes (e.g. `tui` docs, untouched by Phase 0 code).
    **Issue:** Beadloom's own docs have not kept pace with code; the doc *content* is stale even though the sync-check engine is now honest. Driving sync-check to zero is a repo-wide doc refresh, out of scope for the Phase 0 honesty gate.
    **Expected:** A dedicated doc-refresh epic: update each stale ref's prose to match current symbols, reach genuine `sync-check` exit 0, then keep it green via the BEAD-09 / CI tech-writer loop (ties to STRATEGY-3 F4). Also do the exact UX-log category recount here.
    > **Open — new epic.** The honest re-scope of BDL-036's exit criterion (lint + doctor green now; full sync-check green deferred to this epic).

### v1.9.0 — BDL-034 (UX Batch Fix)

> Phase 13. UX issues and improvements batch fix — rules DB, AGENTS.md regen, docs audit FP, two-phase sync.

65. ~~[2026-02-21] [MEDIUM] `docs audit` still has ~60% false positive rate on beadloom itself~~ **FIXED (BDL-034)** — 3-layer FP reduction pipeline: blocklist modifiers (skip numbers near `max`, `limit`, `%`, etc.), proximity scoring (closest keyword wins with distance ranking), file-type heuristics (SPEC.md/CONTRIBUTING.md suppressed). FP rate reduced from ~60% to ~11%.

66. ~~[2026-02-21] [LOW] `graph_snapshots` lacks diff/compare capability~~ **ALREADY RESOLVED** — Snapshot diffing was already implemented (`beadloom snapshot save`, `snapshot list`, `snapshot compare`) in prior work. No code changes needed.

67. ~~[2026-02-21] [MEDIUM] `_load_rules_into_db` silently drops v3 rule types~~ **FIXED (BDL-034)** — Added `_serialize_rule()` with generic isinstance branches for all 7 v3 rule types (DenyRule, RequireRule, CycleRule, LayerRule, CardinalityRule, ImportBoundaryRule, ForbidEdgeRule). Rules DB table now correctly stores all 9 rules.

68. ~~[2026-02-21] [LOW] `_build_rules_section` and `_read_rules_data` use simplistic rule type detection~~ **FIXED (BDL-034)** — New `_detect_rule_type()` function checks all 7 YAML keys (`require`, `deny`, `forbid_cycles`, `layers`, `check`, `forbid_import`, `forbid`) for accurate type labels in AGENTS.md and `beadloom prime`.

69. ~~[2026-02-21] [LOW] `generate_agents_md` Custom section preservation corrupts file on regeneration~~ **FIXED (BDL-034)** — Switched to HTML comment markers (`<!-- beadloom:custom-start -->` / `<!-- beadloom:custom-end -->`). Old `## Custom` format auto-migrated. No more duplication on regeneration.

70. ~~[2026-02-21] [MEDIUM] `sync-check` resets baseline on `reindex`, masking stale doc content~~ **FIXED (BDL-034)** — Two-phase sync via additive `doc_hash_at_last_edit` column in `sync_state`. Tracks doc content independently from reindex baseline. sync-check detects code drift that survives reindex.

### v1.8.0 — BDL-028 (TUI Bug Fixes)

> Phase 12.13. TUI stabilization round 3 — threading, Explorer dependencies, screen state.

58. ~~[2026-02-20] [MEDIUM] TUI: File watcher thread doesn't stop cleanly on exit~~ **FIXED (BDL-028 BEAD-01)** — Added `threading.Event` as `stop_event` passed to `watchfiles.watch(stop_event=...)`. On unmount, `stop_event.set()` is called, which makes `watchfiles.watch()` exit its blocking loop immediately.

59. ~~[2026-02-20] [MEDIUM] TUI: Domain nodes in graph tree not navigable to Explorer~~ **RECLASSIFIED (BDL-028 BEAD-02)** — UX navigation issue, not a code bug. Domain nodes (nodes with children) only expand/collapse on Enter — no way to open them in Explorer. Recognized as a feature request, now tracked as BEAD-01 in BDL-029 (see #61).

60. ~~[2026-02-20] [HIGH] TUI: Static widgets not updating after screen switch~~ **FIXED (BDL-028 BEAD-03)** — Changed `_push_content()` in `ContextPreviewWidget`, `NodeDetailPanel`, and `DependencyPathWidget` to use `update(self._build_text())` instead of `refresh()`. `Static.refresh()` only triggers a re-render of existing content, while `update()` actually replaces the widget's content with new Rich Text.

### v1.8.0 — BDL-029 (TUI UX Improvements)

> Phase 12.14. TUI usability improvements — domain navigation, tree icons, edge labels, screen switching.

61. ~~[2026-02-21] [MEDIUM] TUI: Explorer — no way to open domain nodes directly~~ **FIXED (BDL-029 BEAD-01)** — Domain nodes in graph tree only expand/collapse on Enter. Added `e` keybinding to Dashboard that opens Explorer for any highlighted node, including domain nodes with children.

62. ~~[2026-02-21] [MEDIUM] TUI: Triangle icon shown for childless nodes at cold start~~ **FIXED (BDL-029 BEAD-02)** — Some nodes (e.g. "tui") show expandable triangle icon but have no children at cold start. Root cause: `_build_tree` checked `ref_id in hierarchy` but hierarchy dict could contain entries with empty children lists `{"tui": []}`. Changed condition to `hierarchy.get(ref_id)` which is falsy for empty lists.

63. ~~[2026-02-21] [MEDIUM] TUI: Edge count `[N]` has no legend~~ **FIXED (BDL-029 BEAD-03)** — `[N]` numbers next to tree nodes have no explanation. Changed label format to `[N edges]` (plural), `[1 edge]` (singular), omit badge for 0.

64. ~~[2026-02-21] [HIGH] TUI: Esc (Back) from Explorer/DocStatus crashes with ScreenStackError~~ **FIXED (BDL-029 BEAD-04)** — Pressing Esc from Explorer or DocStatus after navigating via `switch_screen` (keys 1/2/3) crashes with `ScreenStackError: Can't pop screen`. Root cause: `action_go_back()` called `pop_screen()` but `switch_screen` navigation keeps only 1 screen on the stack. Fixed in both ExplorerScreen and DocStatusScreen by using `_safe_switch_screen("dashboard")`.

### v1.8.0 — BDL-025 (TUI), BDL-026 (Docs Audit), BDL-027 (UX Batch Fix)

> Phases 12.10–12.12. Dogfooding on beadloom itself and an external React Native + Expo project.

26. ~~[2026-02-16] [MEDIUM] Test mapping shows "0 tests in 0 files" for domains despite 1408+ tests~~ **FIXED (BDL-027 BEAD-05)** — `aggregate_parent_tests()` rolls up child node test counts to parent domain nodes.

29. ~~[2026-02-16] [HIGH] Route extraction false positives~~ **FIXED (BDL-027 BEAD-05)** — Self-exclusion added: files named `route_extractor` are skipped. Route aggregation scoped to source file ownership.

30. ~~[2026-02-16] [MEDIUM] Routes displayed with poor formatting in polish text~~ **FIXED (BDL-027 BEAD-05)** — `format_routes_for_display()` separates HTTP routes from GraphQL routes with wider columns.

32. ~~[2026-02-17] [HIGH] `beadloom init` scan_paths incomplete for React Native projects~~ **FIXED (BDL-027 BEAD-04)** — `detect_source_dirs()` now scans all top-level directories containing code files, not just manifest-adjacent ones.

33. ~~[2026-02-17] [MEDIUM] `beadloom init` is interactive-only — no CLI flags for automation~~ **FIXED (BDL-027 BEAD-04)** — Already resolved in prior work; verified during BDL-027.

34. ~~[2026-02-17] [MEDIUM] Auto-generated `rules.yml` includes `service-needs-parent` that always fails on root~~ **FIXED (BDL-027 BEAD-04)** — Already resolved in prior work; verified during BDL-027.

38. ~~[2026-02-19] [MEDIUM] `beadloom doctor` shows `[info]` not `[warn]` for nodes without docs~~ **FIXED (BDL-027 BEAD-03)** — Promoted from `Severity.INFO` to `Severity.WARNING`, making it actionable for agents and CI.

39. ~~[2026-02-20] [MEDIUM] Debt report "untracked: 8" — no way to see which files~~ **FIXED (BDL-027 BEAD-03)** — `_count_untracked()` now returns `(count, ref_ids)` list in both human and JSON output.

40. ~~[2026-02-20] [MEDIUM] Oversized false positive on root and parent nodes~~ **FIXED (BDL-027 BEAD-03)** — `_count_oversized()` counts only direct files, excluding subdirectories claimed by child node source prefixes.

41. ~~[2026-02-20] [HIGH] C4 diagram: all elements render as `System()` — no Container/Component differentiation~~ **FIXED (BDL-027 BEAD-01)** — `_compute_depths()` filters self-referencing `part_of` edges. BFS correctly computes depths.

42. ~~[2026-02-20] [MEDIUM] C4 diagram: label and description are identical~~ **FIXED (BDL-027 BEAD-01)** — Label generated from ref_id via title-casing + hyphen-to-space; summary used as description only.

43. ~~[2026-02-20] [MEDIUM] C4 diagram: root node appears inside its own boundary~~ **FIXED (BDL-027 BEAD-01)** — `_load_edges()` skips self-referencing `part_of` entries.

44. ~~[2026-02-20] [LOW] C4 diagram: boundary ordering is non-semantic~~ **FIXED (BDL-027 BEAD-01)** — Orphan boundaries sorted by node kind/depth; root rendered first, then alphabetical.

45. ~~[2026-02-20] [LOW] C4 diagram: `!include` always uses `C4_Container.puml`~~ **FIXED (BDL-027 BEAD-01)** — PlantUML `!include` selects `C4_Context.puml` / `C4_Container.puml` / `C4_Component.puml` based on `--level` flag.

46. ~~[2026-02-20] [HIGH] TUI: Graph tree empty — only "Architecture" label visible~~ **FIXED (BDL-025)** — Self-referencing `part_of` edge caused `get_hierarchy()` infinite loop. Added `if child != parent` filter.

47. ~~[2026-02-20] [HIGH] TUI: Activity widget shows 0% for all domains~~ **FIXED (BDL-025)** — Wrong attribute name: `commit_count` → `commits_30d`. Normalization: `min(commits_30d * 2, 100)`.

48. ~~[2026-02-20] [MEDIUM] TUI: Enter on tree node only expands — doesn't navigate to Explorer~~ **FIXED (BDL-025)** — Leaf-node detection added: if `ref_id not in hierarchy`, opens Explorer screen.

49. ~~[2026-02-20] [HIGH] TUI: Doc Status screen shows "–" for all Doc Path and Reason~~ **FIXED (BDL-025)** — DB opened as `mode=ro` but `check_sync()` needs writes. Switched to WAL mode read-write.

50. ~~[2026-02-20] [MEDIUM] TUI: Explorer shows self-referencing edges as duplicates~~ **FIXED (BDL-025)** — Added `dst != ref_id` / `src != ref_id` filter to edge lists.

51. ~~[2026-02-20] [MEDIUM] TUI: Explorer defaults to "Downstream Dependents" — empty for leaf nodes~~ **FIXED (BDL-025)** — Default changed to `MODE_UPSTREAM`. User presses `d` to switch to downstream.

52. ~~[2026-02-20] [HIGH] `docs audit` high false positive rate (~86%) on real project~~ **FIXED (BDL-027 BEAD-02)** — Skip numbers <10 for count facts, percentage FP filter, SPEC.md/CONTRIBUTING.md excluded from scan.

53. ~~[2026-02-20] [MEDIUM] `docs audit` year "2026" matched as mcp_tool_count~~ **FIXED (BDL-027 BEAD-02)** — Standalone year regex `\b20[0-9]{2}\b` added to false positive filters.

54. ~~[2026-02-20] [MEDIUM] `docs audit` SPEC.md files dominate false positives~~ **FIXED (BDL-027 BEAD-02)** — `_graph/features/*/SPEC.md` excluded from default scan paths.

55. ~~[2026-02-20] [LOW] `docs audit` test_count ground truth seems inflated~~ **FIXED (BDL-027 BEAD-02)** — Labeled as symbol count in output; documented distinction between test symbols and test cases.

56. ~~[2026-02-20] [LOW] `docs audit` Rich output lacks file path context~~ **FIXED (BDL-027 BEAD-02)** — Stale mentions show full relative path from project root.

57. ~~[2026-02-20] [MEDIUM] `docs audit` version fact not collected for dynamic versioning~~ **FIXED (BDL-027 BEAD-02)** — Detects `dynamic = ["version"]` + `[tool.hatch.version]`; fallback to `importlib.metadata.version()`.

### v1.6.0 — BDL-017 (Context Oracle), BDL-019 (Docs Refresh)

16. ~~[2026-02-13] [MEDIUM] After BDL-012 bug-fixes, beadloom's own docs are outdated~~ **FIXED (BDL-019)** — All 13 domain/service docs refreshed. `symbols_changed` reduced from 35 to 0.

27. ~~[2026-02-16] [LOW] `docs polish` text format doesn't include routes/activity/tests data~~ **FIXED (BDL-017 BEAD-14)** — Smart `docs polish` now includes routes, activity level, test mappings, and deep config data.

28. ~~[2026-02-16] [INFO] `beadloom status` Context Metrics section working well~~ **CLOSED** — Confirmed working. No action needed.

### v1.5.0 — BDL-015 (Stabilization), BDL-016 (E2E Baseline)

15. ~~[2026-02-13] [HIGH] `doctor` 100% coverage + `Stale docs: 0` is misleading after major code changes~~ **FIXED (BDL-015 + BDL-016)** — Symbol-level drift detection via `_compute_symbols_hash()` + `_check_symbol_drift()`.

17. ~~[2026-02-14] [LOW] `setup-rules` auto-detect doesn't work for Windsurf and Cline~~ **FIXED (BDL-015 BEAD-12)** — Content-based detection instead of file presence.

18. ~~[2026-02-14] [HIGH] `sync-check` reports "31/31 OK" despite massive semantic drift~~ **FIXED (BDL-015 + BDL-016)** — Symbol-level drift detection works end-to-end.

19. ~~[2026-02-14] [MEDIUM] `.beadloom/AGENTS.md` not auto-generated during bootstrap~~ **FIXED (BDL-015 BEAD-06)**.

21. ~~[2026-02-14] [HIGH] Incremental reindex returns Nodes: 0 after YAML edit~~ **FIXED (BDL-015 BEAD-11)**.

22. ~~[2026-02-15] [HIGH] `.claude/CLAUDE.md` references obsolete project phases~~ **FIXED** — Updated phases, docs references.

23. ~~[2026-02-15] [HIGH] `/templates` has wrong project structure~~ **FIXED** — Fully rewritten with stabilized format.

24. ~~[2026-02-15] [HIGH] `/test` has wrong import paths~~ **FIXED** — Updated all paths and patterns.

25. ~~[2026-02-15] [MEDIUM] `/review` references old architecture layers~~ **FIXED** — Updated layer names.

### v1.0.0–v1.4.0 — BDL-012 (Bug Fixes), early fixes

1. ~~[2026-02-13] [MEDIUM] `doctor` warns about auto-generated skeleton docs as "unlinked from graph"~~ **FIXED** — `generate_skeletons()` writing to wrong paths. Fixed by using `docs:` paths from graph.

2. ~~[2026-02-13] [LOW] `lint` produces no output on success~~ **FIXED** — CLI now prints `"0 violations, N rules evaluated"` as confirmation.

3. ~~[2026-02-13] [LOW] `docs generate` creates skeleton files for services including the root~~ **FIXED** — Root detection changed from "empty source" to "no `part_of` edge as src".

4. ~~[2026-02-13] [INFO] MCP server description says "8 tools" / CLI "18 commands"~~ **FIXED** — services.yml updated to 20 commands, 9 tools.

5. ~~[2026-02-13] [HIGH] `doctor` shows 0% doc coverage on bootstrapped projects~~ **FIXED (BDL-012 BEAD-01)** — `generate_skeletons()` writes `docs:` field back to `services.yml` via `_patch_docs_field()`.

6. ~~[2026-02-13] [HIGH] `lint` false positives on hierarchical projects~~ **FIXED (BDL-012 BEAD-02)** — Rule engine accepts empty `has_edge_to: {}`. `service-needs-parent` removed.

7. ~~[2026-02-13] [MEDIUM] Dependencies empty in polish data~~ **FIXED (BDL-012 BEAD-03)** — `generate_polish_data()` reads `depends_on` edges from SQLite via `_enrich_edges_from_sqlite()`.

8. ~~[2026-02-13] [MEDIUM] `docs polish` text format = 1 line~~ **FIXED (BDL-012 BEAD-03)** — `format_polish_text()` renders multi-line output with node details, symbols, deps, doc status.

9. ~~[2026-02-13] [LOW] Generic summaries~~ **FIXED (BDL-012 BEAD-06)** — `_detect_framework_summary()` detects Django apps, React components, Python packages, Dockerized services.

10. ~~[2026-02-13] [LOW] Parenthesized ref_ids from Expo router~~ **FIXED (BDL-012 BEAD-06)** — `_sanitize_ref_id()` strips parentheses: `(tabs)` → `tabs`.

11. ~~[2026-02-13] [MEDIUM] Missing language parsers — 0 symbols with no warning~~ **FIXED (BDL-012 BEAD-05)** — `check_parser_availability()` + `_warn_missing_parsers()` in CLI.

12. ~~[2026-02-13] [LOW] `reindex` ignores new parser availability~~ **FIXED (BDL-012 BEAD-06)** — Parser fingerprint tracked in `file_index`. Extension changes trigger full reindex.

13. ~~[2026-02-13] [INFO] Bootstrap skeleton count includes pre-existing files~~ **FIXED (BDL-012 BEAD-06)** — CLI shows "N created, M skipped (pre-existing)".

14. ~~[2026-02-13] [MEDIUM] Preset misclassifies mobile apps as microservices~~ **FIXED (BDL-012 BEAD-04)** — `detect_preset()` checks for React Native/Expo and Flutter before `services/` heuristic.
