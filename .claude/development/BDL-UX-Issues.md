# BDL UX Feedback Log

> Collected during development and dogfooding on Beadloom itself and on an anonymised
> downstream project. Open items are listed under **Open Issues**; recurring observations
> that are not defects live under **Improvements**.
>
> **No hand-written tally.** The counts that used to sit here were maintained by hand and
> were wrong (they claimed 46 open against 34 actual). This log becomes a shipped *kind*
> with computed facts in BDL-061 — until then a number here would be a claim nobody checks,
> which is the exact defect this log exists to record.


# Beadloom UX Issues

> Dogfooding feedback: issues, friction points, and improvement ideas collected while using Beadloom on a downstream project.
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

249. [2026-09-04] [MEDIUM] `ci.yml` names a locale macOS does not have, so anyone reproducing that leg locally measures the C row twice

    **Severity:** medium (the reproduction silently succeeds at measuring the wrong room, which is worse than failing to run)
    **Command:** the `tests-locale` matrix in `.github/workflows/ci.yml`; `beadloom rooms`
    **Tracker:** `beadloom-0mdo.50` (#248), same area
    **Context:** measured by `beadloom-0mdo.49` while entering the 8-bit room to fix PR #61's red leg.
    **Issue:** the matrix declares `en_US.ISO-8859-1`. That spelling is not a locale macOS has; setting it silently falls back to ASCII. So a developer reproducing the 8-bit leg with the name CI uses runs the **C** room a second time and reports it as the 8-bit one. The real 8-bit room on this platform is `en_US.ISO8859-1`, without the hyphen.
    **Why it is not merely a typo:** the two rooms differ in exactly the behaviour the leg exists to test. Under C, `beadloom scope-check`'s `Declared axes: NOT CHECKED — …` line carries three non-ASCII bytes; under a real 8-bit locale, `console_streams.tolerate_unencodable_output` degrades the em dash to a literal ASCII `\u2014` and all 540 bytes become ASCII. A test whose premise depends on the child's bytes therefore behaves differently in the two rooms — which is how PR #61 shipped a leg that was green in one and red in the other.
    **`ci.yml` already knows this can happen:** its anti-vacuity step exists to catch a locale that degraded rather than applied. That step protects the CI legs. Nothing protects the developer reproducing them, and the reproduction is where the room census claims its value.
    **Expected:** the room's name is the one the platform answers to, or the census says which spelling it resolved and whether the locale applied or degraded. A room that silently becomes a different room is a phantom room, and `beadloom rooms` is the instrument that should refuse to report it as entered.
    **Related:** #248 (the census carries no locale dimension at all), and the reason this was found rather than reasoned about — the fix that closed PR #61's leg was verified in three rooms, and this is the difference between two of them.

248. [2026-09-04] [MEDIUM] the room census carries platform and interpreter but not locale, so the one leg this project keeps tripping on cannot be entered from a developer machine

    **Severity:** medium (the instrument that qualifies every verdict in two epics is measured over a narrower vocabulary than the rooms it counts against)
    **Command:** `beadloom rooms`, `tests/room_simulation.py`
    **Tracker:** `beadloom-0mdo.50`, routed to S6
    **Context:** found by `beadloom-0mdo.49` while using the simulation to reproduce PR #61's red `tests-locale (C)` leg, and attributed by two controls rather than inferred.
    **Issue:** BDL-068 S3 shipped `room_simulation.py` so a CI leg could be entered locally — it replaces `current_room` at `pytest_configure`, and S3's own bite test proved it reddens exactly `[Linux/3.10]` and `[Linux/3.11]` from a laptop. It carries the platform and interpreter dimensions. It does not carry locale: `current_room()` derives no `locale`, so `beadloom rooms` reports the C leg as unentered while the process genuinely is running under an ASCII filesystem encoding. The verdict errs in the safe direction — it under-claims — and it is still wrong, about the one leg this project has now been bitten by twice (BDL-061 S2; BDL-068 S4 / PR #61). Used suite-wide the plugin also manufactures 11 failures.
    **Why it is worse than a missing field:** *"0 of the 21 declared rooms entered"* is the sentence every verdict across two epics has been qualified with. If the census cannot represent a dimension the CI matrix declares, that count is measured over a smaller vocabulary than the 21 it names — a population narrower than it appears, which is this epic's own subject inside the instrument the epic built to state it.
    **Expected:** `current_room()` derives the locale the way it derives platform and interpreter; the simulation carries it, so the leg is enterable locally, which is the whole point of S3's deliverable and is presently true for two dimensions of three. Diagnose the 11 manufactured failures before recommending the plugin suite-wide — `beadloom-0mdo.49`'s bead comment carries the two controls that attributed them.
    **Already measured, do not re-cost:** a suite-wide guard against reading a subprocess with no explicit encoding is not a new instrument. `tests/test_locale_independent_io.py::TestEveryTextIoSiteStatesItsEncoding` already is that guard, rooted at `src/beadloom`. Extending its root to `tests/` costs 26 triage decisions, counted rather than estimated.

247. [2026-09-04] [MEDIUM] the push Gate does not run the suite, and nothing in its output says the suite is not among the things it checked

    **Severity:** medium (agent-facing; it cost this project a red PR across six legs, measured)
    **Command:** `beadloom ci`, the pre-push hook
    **Tracker:** routed to S6
    **Issue:** `beadloom ci` runs reindex, lint, sync-check, docs-audit, docs-quality, doc-spaces, scope-check, config-check and doctor. It does not run `pytest`. That is a reasonable division — the Gate is about documents and architecture — and every step it *does* run is named in its output. What is missing is the other half of this project's own rule: the Gate never says the suite is not among them.
    **Why the surrounding text invites the mistake:** CLAUDE.md calls the pre-push hook "the full `beadloom ci`" and the coordinator skill calls it "the authoritative blocking backstop" whose red "blocks the push". Read together, a green Gate at push time reads as the last line of defence before a PR. For tests it is not one.
    **Measured, and by the coordinator that wrote most of this epic:** BDL-068 S4's docs wave introduced an inline code span spilling `<doc>` onto the next line in `docs/services/cli.md`. `beadloom ci` returned rc 0 twice over that tree. PR #61 opened and **all six test legs went red on that single test** — `tests/test_site_markdown_compiles.py::test_no_inline_code_span_spills_a_tag_onto_the_next_line`, which reproduces locally in 0.07 s. Roughly 55 runner-minutes to learn something one local command answers instantly. The same conflation had already cost a red tree earlier in the slice, at `8befa96`.
    **This is the epic's own rule turned on the epic's own Gate.** S4 shipped `NOTHING TO CHECK` for an empty typed surface, `not compared` for an unowned path, `not_covered` for an unresolvable write target and `unresolved` for an unreadable population — four instruments taught to distinguish "checked and clean" from "not checked". The Gate itself makes no such distinction about the largest thing it does not do.
    **Expected:** the Gate names the suite as not run, the way it already names the room it entered (`0 of 21 declared room(s)`). One line — `tests: NOT RUN — the suite is not a Gate step; run \`uv run pytest\`` — costs nothing and removes the reading. Whether the pre-push hook should additionally run the suite is a separate and more expensive question; do not conflate the two, and answer the cheap one first.
    **Not a defect in the steps it runs.** Every one of them reported honestly. The gap is a promise the surrounding documents make on the Gate's behalf, which the Gate is silent about.

246. [2026-09-04] [MEDIUM] a declared mutation target that no run ever covers passes every green Gate, and the one command that would say so is silenced by the flag its only caller passes

    **Severity:** medium (a declaration the Gate reports as satisfied while nothing measures it — a phantom gate with a name on it, in the feature built to remove phantom gates)
    **Command:** `beadloom ci`, `beadloom mutation --only`
    **Tracker:** `beadloom-0mdo.45`, routed to S6
    **Context:** BDL-068 S4's fix cycle. Measured on this repository, which is the one that shipped the feature: `doc_quality.py` and `doc_shape.py` were declared in `mutation.targets` in S3 and no run had covered either of them when this was written on 2026-09-04.
    **Issue:** three separate settings must agree before a declared target is measured, and Beadloom can see only one of them. `beadloom ci` calls `check_mutation_scope` — could a mutant run at this path — and never `report_mutation_score` — did one — because a score needs a stats file the tree does not carry. So a target declared and never measured passes every Gate this project has ever taken. The command that does report it, `beadloom mutation`, has `--only`, which prints the targets a run did not cover as "not judged by this run" rather than as `mutation-target-unmeasured`; the only caller in this repository is the nightly job, and it passed exactly the `--only` that suppressed the finding for those two targets.
    **Why the tool cannot simply check it:** whether a runner will mutate a path lives in the runner's own configuration — `[tool.mutmut] only_mutate` here — and reading that would make Beadloom own the runner, which CONTEXT Q5 declines. This repository's fix is therefore a repository test (`tests/test_mutation_runner_scope.py` now asserts both inclusions), and an adopter has nothing equivalent.
    **Expected:** what the product CAN check without owning a runner is whether it has ever seen a score for a declared target. `beadloom mutation --stats` could record the run it just judged — targets, score, tool, room, timestamp — under `.beadloom/`, and the Gate could then report a declared target whose last measurement is absent, or older than a stated age. That turns "declared" into "declared and measured on <date>", which is the distinction the feature exists to make and currently cannot.
    **Note:** `--only` itself is not the defect. A run that covers one slice of a larger scope is the normal state and saying so is right. The defect is that "this run did not cover it" and "no run has ever covered it" are printed as the same sentence.

245. [2026-09-04] [MEDIUM] the `unguarded_axis` remedy, followed literally, gives every bead one scope and collapses every wave to a wave of one

    **Severity:** medium (a correct verdict followed by advice that would switch off the parallelism the command exists to plan)
    **Command:** `beadloom waves`, `beadloom axes <doc> --refs`
    **Tracker:** `beadloom-0mdo.46`, routed to S6
    **Context:** BDL-068 S4's fix cycle, immediately after the RFC's `## Axes` section was populated at epic scale for the first time.
    **Issue:** on an `unguarded_axis` finding `waves` prints *"generate each bead's `refs:` from the `## Axes` section of <the RFC>"*. `beadloom axes <doc> --refs` prints ONE line generated from every row kept in scope — 24 nodes on this epic — and there is no per-bead selection; the help text confirms the unit is the work item. Performed exactly, the remedy hands every bead in the epic an identical 24-node scope, `shared_node` fires on every pair, and every wave becomes a wave of one.
    **The root is a level confusion, not a typo:** a work item's axes are the UNION of its slices' — the RFC says so — while a bead's scope is a SUBSET chosen for that bead. One document holds the union; nothing holds the per-bead subset, and `--refs` cannot invent it. CONTEXT Q1 ("a bead's `refs:` is generated from the document") is right; the selection step between the two is what is missing.
    **Same class as #234**, closed in this same epic: a correct verdict followed by a remedy that does not follow the cause down as far as the reason does. There it would have authored a scope; here it would disable every parallel wave. A remedy standing beside a correct verdict is the line nobody re-reads.
    **Expected:** either the section records which rows belong to which bead, so `axes --refs <bead-id>` can answer, or the remedy stops prescribing an action that has no correct form and states instead which comparison it could not make. Do not ship it unchanged — it is advice to make the tool useless, printed by the tool.

244. [2026-09-04] [MEDIUM] a second markdown table in `## Axes` contributes its header row as an approved node named `Node`

    **Severity:** medium (a phantom entry in the list `scope-check` compares every commit against)
    **Command:** `beadloom axes`, `beadloom waves`, `beadloom scope-check`
    **Tracker:** `beadloom-0mdo.46`, routed to S6
    **Context:** found by `beadloom-0mdo.44` while appending S4's 28 rows to BDL-068's `## Axes`. Measured after the append: `beadloom waves` reports `29 node(s) approved … 1 axis row(s) name no node`.
    **Issue:** `read_axes_section` takes the header row of a SECOND table in the section as data, producing an approved node literally named `Node`.
    **Why the document invites the second table:** the RFC's own per-slice union rule says each slice appends its rows with its own `Derived by` / `Measured on` line — which is naturally a new table, not more rows under one header. The parser's one-table-per-section assumption is contradicted by the document rule this project wrote for itself, and the contradiction can only appear once an epic reaches its second slice, which is why it survived S1.
    **Why a phantom here is worse than elsewhere:** the approval list is what `scope-check` compares commits against. A name nobody chose is a name every commit is allowed to touch.
    **Expected:** a row whose cells are a table header is not a row. Fix this before #245 is evaluated — that finding cannot be judged honestly while this one injects a node nobody wrote.

243. [2026-09-04] [MEDIUM] re-copying changed files into a room that has already been reindexed manufactures a stale-doc failure that looks exactly like a defect

    **Severity:** medium (a false red in the measurement whose whole purpose is to be trusted, and the false red is indistinguishable from a true one)
    **Command:** the clean-room convention (`git archive HEAD` + only your files), BDL-UX #181, #235, #236
    **Context:** BDL-068 S4, `beadloom-0mdo.41`, met and measured rather than reasoned about.
    **Issue:** an agent that has already built and reindexed its room, then edits a file and copies the new version in, gets a SECOND failure — `test_bead15_s3b_coverage`, `sync-check` exit 2, `stale: 2` — which does not reproduce at pure HEAD. The copy postdates the room's own doc-freshness baseline, so the room correctly reports the file as changed since it was last attested. Nothing is wrong with the change. The failure is produced by the room's lifecycle and is shaped exactly like a defect in the work being measured.
    **Why it belongs with #235 and #236:** those three are the whole isolation story of a clean room and all three were assumed rather than checked — #235 the room may contain a neighbour, #236 the room's dependency set is unstated so its verdict is not reproducible, #243 the room is not re-enterable and nothing says so. A convention that is only correct when performed exactly once, without saying so, is a convention that will be performed twice.
    **Expected:** a room is BUILT, never refreshed. The agent that met this rebuilt from scratch and the pristine room gave the same one-failure verdict as the first, which is the check that makes this an entry rather than a guess. The durable form is the one #235 already proposes: a command that creates the room and refuses a directory it did not create empty — which makes re-entry impossible rather than merely discouraged, and answers both entries at once.
    **Workaround (in use):** rebuild the room after any edit. Do not re-copy, do not re-sync.

242. [2026-09-04] [LOW] the launch context a subagent receives carries a `git status` snapshot that is stale by construction, and one agent published from it

    **Severity:** low (recoverable, and it was recovered) — but it produced a withdrawn public sentence, which is the outcome this project spends the most effort avoiding
    **Command:** none — the agent harness's launch context
    **Context:** BDL-068 S4. Every subagent's launch context opens with a `git status` block captured when the SESSION started, not when the agent did. `beadloom-0mdo.34` measured its own: the block described branch `features/BDL-067` at `6fb5093` with three modified `src/` files, against a tree that was actually `features/BDL-068` at `3ec1db2` with none. Twenty-eight commits and five waves of drift.
    **Issue:** `beadloom-en0x` described the room its combined-tree verdict was taken in using that block instead of re-deriving the state, published the sentence, then caught it and withdrew it in `f45dd62`. The block is labelled as a snapshot, which is honest; what it is not is inert, because it sits where an agent looks first and reads like current state.
    **Why it belongs in this log rather than being shrugged off:** it is the same shape as everything else in BDL-068 — a fact that was true when it was written, presented without the reader being able to tell how stale it is. The difference is that the agent caught its own instance, which is what the flow is supposed to produce.
    **Expected, and it is ours to do rather than the harness's:** the role protocol says a tree fact is DERIVED at the moment it is stated, never read from launch context. `beadloom-0mdo.27`'s duty mechanism can carry that as a declared duty, which makes it checkable rather than remembered. Routed as a note on the S6 slice, not as its own bead.

241. [2026-09-04] [MEDIUM] `config-check` reports a duty delivered to five roles on a project holding no role files, and does not say which question it answered

    **Severity:** medium (adopter-facing: the reassuring output is produced by the state in which nothing is protected)
    **Command:** `beadloom config-check`
    **Tracker:** `bd show` the S4 fix bead
    **Issue:** on a project with no role files on disk, `config-check` prints `Duties: 1 declared, checked over 10 composed artifact(s)` and `no blocking drift`. It judges the COMPOSITION rather than the artifact, which is a defensible choice — `--fix` writes compositions, and drift covers the scaffolded case — but the choice is nowhere stated and the printed sentence does not say which of the two questions it answered. On a scaffolded project the pair is sound; that was tested rather than assumed.
    **The root, shared with #239:** `beadloom-0mdo.31` and `beadloom-0mdo.27` landed in the SAME WAVE of BDL-068 S4 and answered one question in opposite ways. `.31` reads the artifact on disk and reports `unresolved` when it is missing, with the reason recorded and the reasoning stated. `.27` judges the composition and does not state that it did. Neither agent could see the other. This is the one place the slice's eight instruments disagree, and #239 and #241 are its two consequences.
    **Expected:** each instrument states which question it answered, in the sentence it prints. Then the divergence is a visible design choice instead of two commands that look like they agree.

240. [2026-09-04] [MEDIUM] the commit hook's typed leg is gated by a hand-written `^(src|tests)/` regex and prints nothing at all on a flat-layout project

    **Severity:** medium, and adopter-facing — **this repository cannot observe it**, being src-layout, which is why it survived the bead that built it
    **Command:** the pre-commit hook's type-check leg (`beadloom install-hooks`)
    **Tracker:** `bd show` the S4 fix bead
    **Issue:** the leg selects the files it will type-check with a literal `^(src|tests)/` path regex. A project whose package sits at the repository root — the flat layout, which is common and which `beadloom impact` already has a filed defect about (#225) — matches nothing, and the leg prints NOTHING. Not "no typed files staged", not a skip: silence.
    **Why it is the slice's own shape, one level up:** `beadloom-gsal` fixed exactly this defect in the same leg — it replaced a hand-written typed surface with one derived from `pyproject`, citing `beadloom-mr2l.82` shipping a hand-written list that `pyproject` then moved out from under. The derivation landed and the GATE ON IT stayed a spelling. A rule stated as a shape, reached through a filter stated as a spelling.
    **Expected:** the gate is derived from the same source as the surface. If `pyproject` says what is typed, nothing else needs to say where it lives.

239. [2026-09-04] [MEDIUM] `guard --liveness` prints `0 of 0 write path(s) bound`, and an empty population reads as full coverage

    **Severity:** medium (the phantom gate, in the instrument built during this slice to report exactly that class)
    **Command:** `beadloom guard --liveness`
    **Tracker:** `bd show` the S4 fix bead
    **Issue:** `surface.build_surface` correctly reports `unresolved` when a source cannot be READ — its docstring states the rule outright: "'100% of the zero tools I found' is the most confident way to state it". But an EMPTY population is not an unreadable one. Role adapters that exist and grant nothing produce `grants={}`, no error, and `covered == (0, 0)`; the renderer prints `surface (claude): 0 of 0 write path(s) bound, matcher(s) '...'` with no line saying the population was empty. Reproduced three ways, each a state an adopter reaches without doing anything wrong.
    **Why it is worth the entry:** `beadloom-0mdo.31` shipped this instrument in BDL-068 S4 to answer "what fraction of edit events could this binding have seen?", and got the unreadable case exactly right while leaving the empty case reading as a pass. The check that exists to find phantom gates has one.
    **Expected:** an empty population prints differently from a covered one. `0 of 0` is not a fraction, it is the absence of a denominator, and the report needs a word for that — the same distinction `beadloom-0mdo.32` shipped for unowned paths (`not compared`, never `agrees`) two waves earlier in the same slice.

238. [2026-09-04] [LOW] this repository's own `.gitignore` drifted from the ignore block Beadloom emits, and nothing compares the two

    **Severity:** low here, medium for an early adopter (an upgrade adds a written file that the ignore block written at `init` time does not name)
    **Command:** `beadloom init` / `beadloom config-check`, `onboarding/ignore_block.py`
    **Context:** BDL-068 S4. `.beadloom/guard-firings.1.jsonl` appeared as an untracked file during wave 3 and `beadloom waves` would have reported it as a path owned by no bead. It appeared now, and not earlier, because `beadloom-0mdo.31` widened the guard matcher to include `Bash` in the same slice, so firings roughly tripled and the log rotated for the first time.
    **Issue:** the pattern this project SHIPS is already correct — `ignore_block.py:95` emits `.beadloom/guard-firings*.jsonl`, a glob, and its own docstring explains the rotation it covers. This repository's `.gitignore` carries `.beadloom/guard-firings.jsonl`, the exact filename, written before rotation existed and never re-derived. So the product is right and its own repository is stale, and the only reason anyone noticed is that an unrelated bead made the rotation happen.
    **Why it is the epic's own shape:** a rule stated as a SPELLING rather than as a SHAPE, in the one file where nobody looks for rules. And a second layer: the ignore block is GENERATED for an adopter and hand-maintained here, so the two can only agree by coincidence. An adopter who ran `init` before the rotation feature has the same stale line and nothing will tell them either.
    **Expected:** `config-check` compares the ignore block on disk against the block the current version emits, and reports the drift — the same both-directions check `beadloom-0mdo.27` built for role duties, applied to the other thing `init` writes into a repository it does not own. Fixing this repository's line is the instance; the check is the class.
    **Fixed (instance):** `.gitignore` now carries the shipped glob. The class is filed as a bead under S6.

237. [2026-09-04] [MEDIUM] `bd merge-slot acquire --wait` does not wait, and cannot serialise agents that share one tracker identity

    **Severity:** medium (the convention that keeps two agents out of one commit is the one that silently does nothing)
    **Command:** `bd merge-slot acquire --wait` / `check`
    **Context:** BDL-068 S4 wave 3, `beadloom-0mdo.33` about to commit beside `beadloom-67t1` in one working tree. Every launch prompt in this epic carries "take `bd merge-slot acquire --wait` before committing and `release` after".
    **Issue:** two failures, and the second makes the first unfixable from here. `acquire --wait` returned **immediately** with `Slot held by v.zoologov, added to waiters queue (position 5)` and exit 0 — it queued and returned rather than waiting, so an agent that follows the instruction proceeds to commit exactly as if it had the slot. And the holder it named was `v.zoologov`, which is who **I** am: every role in this repository writes under one tracker identity, so the slot cannot tell the holder from the waiter. `bd show beadloom-merge-slot` says `Updated: 2026-09-03` — the hold is a day old and belongs to no live agent — and the queue carries four stale waiters (`coordinator`, `agent-viaj-12`, `agent-viaj-13`, `probe`) from sessions that ended. There is no safe move: waiting deadlocks on a stale hold, and `release` would release whatever a live neighbour holds.
    **Why it matters:** this is the same root the review's independence check already reports rather than enforces — one identity for every role — arriving in a primitive that is supposed to be an exclusive lock. A mutex whose holder is indistinguishable from its claimant is not a mutex, and `--wait` returning at once means nobody finds that out. The serialisation this epic's waves depend on is currently carried by the agents not colliding.
    **Expected:** the slot is held by the BEAD, not by the user — `acquire <bead-id>`, so a holder can be compared with a live claim and a stale hold can be aged out with its bead's status. `--wait` blocks until the slot is free or a stated timeout expires, and says which it did; without a timeout it is a poll loop the caller has to write. A hold whose bead is closed is reclaimable, and `check` says how old the hold is rather than only who has it.
    **The last observation, taken after the commit:** the slot then read `OPEN` with no holder at all, `Updated: 2026-09-03` unchanged. So across one wave's commit the primitive was, in order, held by a name indistinguishable from the claimant's, non-blocking on `--wait`, and empty — and nothing was serialised at any point. The commits did not collide because they touched different files, which is the property the slot exists so that nobody has to rely on.
    **Related:** the review-brief independence report (one tracker identity for every role), #235 and #236 (the other two conventions in this wave whose isolation was assumed rather than checked).

236. [2026-09-04] [MEDIUM] a clean room's verdict is decided by which optional extras it installed, and the convention never names them

    **Severity:** medium (the verdict is reported as a claim about the code, and three different verdicts about the same code were measured in one hour)
    **Command:** the clean-room convention (`git archive HEAD` + only your files + `uv run …`), BDL-UX #181, #235
    **Context:** BDL-068 S4 wave 3, verifying `beadloom-0mdo.33`. Room built exactly by the convention, then the same `mypy --strict src/` run three ways.
    **Issue:** the answers were **0, 1 and 82 errors**, over one code base, differing only in which extras the room's environment had. `uv run --extra dev mypy src/` in a room at HEAD reports **82 errors in 19 files** (`textual` is absent, so every TUI class subclasses `Any`); the same command in a room that had earlier installed `--extra tui` reports **1** (`unused-ignore` in `tui/file_watcher.py`, because `watchfiles` is absent); with the five extras the tree's own venv carries it reports **no issues found in 258 source files**, which is what the tree reports. The suite has the quieter half of the same defect: the room ran **8 557 passed, 68 skipped** where the tree ran **8 609 passed, 11 skipped** — about 57 rows that do not execute in a room and do execute on the tree, and a skip is not a failure, so nothing says so.
    **Why it matters:** the clean room exists to make a verdict attributable, and the convention specifies the FILES precisely and the ENVIRONMENT not at all. An agent that follows it exactly gets whatever `uv run` resolves by default, and then reports "green in a clean room over N files" — a sentence that reads as a claim about the code and is a claim about an environment nobody wrote down. The failure is silent in the safe direction here (a room over-reports errors, so the agent investigates) and is not silent in the other one: 57 rows that skip in the room are 57 rows a clean-room verdict did not cover, reported as passed-and-skipped by a runner that has no opinion about which skips were meant.
    **Expected:** the room-building step installs the extras the project declares, and the verdict names them the way `beadloom rooms` already names interpreters and CI legs — the room is a value with a stated composition, not a directory. The cheap first version is a line in the convention (`uv sync --all-extras`); the version this project would prefer is `beadloom rooms` reporting the extra-set dimension alongside the others, so "which room did you measure in" has one answer covering platform, interpreter and environment.
    **Related:** #235 (two agents, one room path — rooms are not neutral), #181 (the clean-room duty itself), #228 (the duty reaches roles only through a prompt).

235. [2026-09-03] [MEDIUM] the clean-room instruction names a fixed directory, so two agents in one wave build one room and both call it clean

    **Severity:** medium (the whole product of a clean room is isolation, and the failure looks like a set of unrelated red tests rather than like a room problem)
    **Command:** the clean-room convention every launch prompt carries (`git archive HEAD` + only your files), BDL-UX #181
    **Context:** BDL-068 S4 wave 1, `beadloom-0mdo.27` and `beadloom-0mdo.31` running concurrently. Both agents are handed a session-scoped scratchpad directory, and the convention names the room after the concept rather than after the bead, so both built `<scratchpad>/cleanroom`. Reconstructed from mtimes: `.31`'s `git archive HEAD | tar -x` landed at 22:53, `.27` copied its own untracked files in at 23:16, `.31` copied its files at 23:26.
    **Issue:** the run `.31` then took reported 8 failures. Five were `.27`'s — its acceptance steps, and two annotation-consistency checks over a graph node HEAD does not carry — and none of them was a defect in either bead. Rebuilding under a bead-unique name and re-running gave 1 failure, itself a stated property of the room (no `.git`, so `sync-check` has no baseline). So the polluted room cost one full 5-minute suite run and would have cost a wrong verdict: had the report been written from it, `.31` would have attributed `.27`'s work to itself, in the one measurement whose entire purpose is to separate them.
    **Why it matters more than the wasted run:** this is the failure the gate-owner rule exists to catch, one layer below where the rule looks. The gate owner is told that a clean room cannot see interactions between beads on the TREE. Nobody said the rooms themselves could interact. An agent that follows the convention exactly, and correctly, gets a room containing its neighbour's work — and every check it runs there is honest about a tree that exists nowhere.
    **Expected:** the room's path carries the bead id, and the convention says so — `<scratchpad>/room-<bead-id>`, not `<scratchpad>/cleanroom`. Stronger, and the form this project prefers: the room is created by a command that derives the path from the claimed bead and refuses a directory it did not create empty, so "is this room mine" is answered rather than assumed. A room that cannot say whose it is is not a clean room, it is a shared directory with a reassuring name.
    **Related:** #181 (the clean-room duty itself), #228 (the duty reaches roles only through the coordinator's typing — a convention typed into a prompt is a convention that can be typed imprecisely).
    **Partly addressed 2026-09-04 (`beadloom-67t1`), and still open for the rest:** the convention half shipped. `room_for(bead_id)` returns `room-<bead-id>`, `beadloom waves` prints it per bead for every wave including a wave of one, the `working-tree` medium's statement carries it, and the five role cores carry it under the `clean-room` duty `config-check` checks. What did NOT ship is the stronger form this entry asks for: no command creates the room, derives its path from the claimed bead and refuses a directory it did not create empty. So "is this room mine" is still answered by reading the path rather than by the tool, and the entry stays open on that clause.

234. [2026-09-03] [LOW] `waves` prints one remedy for four unreadable-scope causes, and on the no-declaration case it prescribes the authored scope the tool exists to refuse

    **Severity:** low (the verdict is right; the sentence after it sends the reader the wrong way)
    **Command:** `beadloom waves`
    **Tracker:** to be attached to `beadloom-en0x` (#232), which owns the scope parser
    **Issue:** planning S4's wave, `beadloom-nn4c` was serialised against all six other beads with the reason `unresolved_scope: declaration_not_at_a_line_start` and the remedy "move the declaration to the start of its own line". That bead has **no declaration to move**. Its note is a paragraph explaining, in prose, why writing `refs: flow-guards` there would be an authored scope dressed as a derived one — and the parser matched the `refs:` inside that explanation. So the tool read a sentence *about* a declaration as a malformed declaration, and then told the reader to promote it to a real one. Following the printed remedy would have created exactly the defect #232 is filed against, in the same slice.
    **Why it is worth an entry rather than a shrug:** the serialisation was CORRECT and the exit code was right. Only the remedy was wrong, which is the failure mode that survives longest — nobody re-reads a line that appears beside a correct verdict. The parser's four unreadable causes are already distinguished in the *reason* (`no declaration`, a name the graph lacks, a `refs:` inside a sentence, a second ref without a separator); the remedy does not follow the reason down that far.
    **Expected:** the remedy is derived from the cause, like the reason already is. For `declaration_not_at_a_line_start` the honest remedy is two-branched: *if* you meant this as a declaration, move it to the start of its own line; *if* the line is prose about a declaration, the serialisation is the correct answer and nothing needs fixing. A tool that cannot tell prose about `refs:` from a careless `refs:` should say which of the two it cannot tell apart, not pick one.
    **Found by:** the coordinator, on its own note, while planning BDL-068 S4 — the note deliberately said no scope could be derived (`impact` over `tests/` attributed a node to none of 148 sites, BDL-UX #225) and the tool answered as if the note were the scope.

233. [2026-09-03] [MEDIUM] the read-only guard test reports a `bd` export burst as the guard's own write

    **Severity:** medium
    **Tracker:** `beadloom-nn4c`
    **Issue:** The differing digest is `.beads/issues.jsonl`, never `beadloom.db`. `_moved_with_nothing_running` opens a control window of the measurement window's duration and skips only if the repository moves DURING it, so a millisecond `bd` export burst lands in the measurement window and misses the control. A two-writer wave makes it likelier — the check is least reliable exactly when the flow is most parallel. Attributed by `beadloom-0mdo.26` after `.22` recorded it non-reproducing and `.23` and `.24` each looked across four runs without meeting it.
    **Detail:** the full measurement, the reproduction and the fix shape are on the bead — `bd show beadloom-nn4c`. This entry exists so the number is allocated and the finding is findable; the tracker is the source of truth for its text.

232. [2026-09-03] [MEDIUM] `waves` plans from an authored `refs:` line, so two beads editing one document read as independent

    **Severity:** medium
    **Tracker:** `beadloom-en0x`
    **Issue:** `beadloom-0mdo.21` and `.26` both edited `docs/services/cli.md` concurrently; `waves` reported 0 findings. The graph knows the file — it is the `cli` node's spec — but `waves` compares the `refs:` each bead DECLARES, and both were authored from the CODE each would touch. The planner's input is authored while everything else BDL-068 built is derived.
    **Detail:** the full measurement, the reproduction and the fix shape are on the bead — `bd show beadloom-en0x`. This entry exists so the number is allocated and the finding is findable; the tracker is the source of truth for its text.

231. [2026-09-03] [MEDIUM] the commit hook warns about type errors on an undeclared surface, discards the output, and never blocks

    **Severity:** medium
    **Tracker:** `beadloom-gsal`
    **Issue:** `.git/hooks/pre-commit` runs mypy over every staged Python file with `2>/dev/null` and prints one contentless sentence. `[tool.mypy]` declares `packages = ["beadloom"]`; `uv run mypy tests/` reports 970 errors in 90 files. A real error in `src/` produces the identical sentence, so the case that matters is drowned by the case that does not. Sharper than `mr2l.82`'s one-liner.
    **Detail:** the full measurement, the reproduction and the fix shape are on the bead — `bd show beadloom-gsal`. This entry exists so the number is allocated and the finding is findable; the tracker is the source of truth for its text.

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

228. [2026-09-03] [HIGH] the clean-room duty reaches the roles that must perform it only through the coordinator's typing

    **Severity:** high
    **Tracker:** `beadloom-67t1`
    **Issue:** Zero occurrences of `clean room` in `.claude/agents/*` and in the role templates `setup-agentic-flow` composes for an adopter; the rule lives in the project layer of CLAUDE.md, which is never distributed, and in `waves/media.py`, which emits it only for a wave of more than one bead. Roughly twenty single-bead waves across two epics carried it by prompt alone. Same class as BDL-061 S4 and worse: there the duty at least reached the role.
    **Detail:** the full measurement, the reproduction and the fix shape are on the bead — `bd show beadloom-67t1`. This entry exists so the number is allocated and the finding is findable; the tracker is the source of truth for its text.

227. [2026-09-02] [MEDIUM] mypy --strict runs on one Python version locally and four in CI

    **Severity:** medium
    **Tracker:** `(fixed in BDL-068 S1)`
    **Issue:** `tests (3.10)` and `(3.11)` failed in 18 and 21 seconds on PR #59 while 3.12 and 3.13 passed: `--strict` reports an UNNECESSARY `type: ignore` as an error. Every local measurement in two epics ran `uv run mypy src/` against the developer's own interpreter. Third instance of a claim true of the room it was measured in — after nine macOS greens meeting six red Ubuntu legs, and `mr2l.61`.
    **Detail:** the full measurement, the reproduction and the fix shape are on the bead — `bd show (fixed in BDL-068 S1)`. This entry exists so the number is allocated and the finding is findable; the tracker is the source of truth for its text.

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

219. [2026-09-02] [HIGH] The review's withholding does not cover commit messages, which is where this project writes its accounts

    **Severity:** high (the better the commit message, the more completely the mechanism is defeated)
    **Command:** `beadloom review-brief`, followed by the review protocol's own `git diff <base>...HEAD`
    **Context:** found and declared unprompted by the seventh-pass reviewer of BDL-067 (`beadloom-e8s4.23`). The second structural defeat of this mechanism; #212 was the first.
    **Issue:** `git log main..HEAD` carries the author's full account in the commit bodies — on BDL-067 the `.21` and `.22` messages are longer and more specific than any bead comment, including `.22`'s explicit "FINDING for `.23`". Step 3 of the review protocol tells the reviewer to read the diff, so the account is one command away. `review-brief` reports "0 comments withheld" and is correct about bead comments while the account is fully available elsewhere.
    **Why it is worse than #212:** #212 was a coordinator handing over `ACTIVE.md`, fixable by changing the launch prompt, and it was. This one is not reachable by prompt discipline, because the protocol itself sends the reviewer to the diff and this project deliberately writes long, specific commit bodies.
    **Expected, and it is a decision rather than a patch:** (a) `review-brief` also withholds or summarises commit bodies on the reviewed range and says how many it withheld; or (b) the mechanism stops claiming to withhold and instead REPORTS what is reachable, so the reviewer can declare it — which is what both the `.16` and the `.23` reviewer did unprompted, and the only reason either leak is known; or (c) accept it, on the ground that independence on a re-review is not worth the cost and the first pass is the only one where it matters.
    **Related:** #212 (defeated through `ACTIVE.md`, fixed by prompt), #204 (`review-brief` reports "0 withheld" and cannot know what the coordinator's prompt contained). All three are one shape: an instrument that measures its own scope and is read as measuring the question.
    **Tracker:** `beadloom-tm76`.

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

216. [2026-09-01] [MEDIUM] `init --bootstrap` and the wizard leave different trees for the same declared mode

    **Severity:** medium (one declared mode, two entry points, two different graphs — on a project that already carried a graph file)
    **Command:** `beadloom init --bootstrap` versus `beadloom init` answered `bootstrap`
    **Context:** recorded rather than asserted away by BDL-067 `.19`, because closing it was a behaviour change and `.19` was a test bead. Raised as a major by the sixth review and closed by `.21`.
    **Measured** on a project carrying `.beadloom/_graph/legacy.yml` with one service root and one domain `ledger`:

    ```
    only `--bootstrap` left:  ledger with no `docs:` field
    only the wizard left:     ledger with docs: ['docs/domains/ledger/README.md'], that file,
                              and `ledger` in the Domains table of docs/architecture.md
    ```

    **Issue:** one argument. The `--bootstrap` branch called `generate_skeletons(root, result["nodes"], result["edges"])` while every other caller passed no node list and therefore wrote skeletons for every node on disk. `--yes --mode both` carried the sibling of the same defect: it imported the skeletons it had generated seconds earlier.

    > **FIXED on `features/BDL-067` (`.18` and `.21`); not yet merged, so this entry stays here until it is.** Closed by taking the parameter OFF `generate_skeletons` rather than by editing the third call site, since a function that renders a document about the whole tree and can be handed part of the tree is a defect one caller at a time. Pinned by `test_every_branch_leaves_the_same_thing_on_a_tree_it_did_not_start` and `test_the_skeleton_writer_cannot_be_handed_a_subset_of_the_tree`, both measured red before the parameter came off: the docs differed by `docs/domains/ledger/README.md` and the architecture document by whether it named `ledger` at all.

    **Tracker:** `beadloom-e8s4.18` / `beadloom-e8s4.21`, both closed.

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

214. [2026-08-31] [HIGH] `init` writes two nodes with the same `ref_id` on the classic Python src-layout, and the loader silently keeps one

    **Severity:** high (the most common Python layout there is, and the failure is silent in both directions — a node disappears and the gate stays green)
    **Command:** `beadloom init --yes --mode bootstrap`
    **Context:** measured during the BDL-067 review by the review subagent, on a fresh `ledger` project laid out as `src/ledger/`.
    **Measured:**

    ```
    beadloom init --yes --mode bootstrap  ->  rc 0   Graph: 2 nodes, 0 edges
    services.yml                              TWO nodes with ref_id `ledger` — one service (root), one domain
    the loader                                keeps ONE
    beadloom lint --strict                ->  domain-needs-parent:rule_liveness:warn
    beadloom ci                           ->  rc 0
    ```

    **Issue:** the root `ref_id` comes from `_detect_project_name` (the `pyproject`/`package.json` name) and the domain `ref_id` comes from the source directory; on `src/<project>/` those are the same string. The graph loses a node, and because the surviving node is the root, `domain-needs-parent` goes **inert** rather than failing — so the gate reports a warning about rule liveness and exits 0. The adopter is told nothing.
    **Not a regression, and not caused by BDL-067:** pre-fix behaviour is identical. BDL-067 deliberately carves out a domain whose `ref_id` equals the root's (`onboarding/scanner/bootstrap.py:69`), because a self-edge is not a parent — that carve-out is right, and the defect is upstream of it.
    **Expected:** unique `ref_id`s, not an edge. Disambiguate the colliding node, and make a duplicate `ref_id` in a *generated* graph something the writer refuses rather than something the loader silently resolves.
    **Numbering:** first filed as #211, which is already taken by the closed 1.x-description issue of 2026-08-27 further down this file. Caught by the `beadloom-e8s4.6` subagent, which noticed `CHANGELOG.md:17` and `docs/domains/onboarding/README.md:31` citing #211, before the duplicate shipped. The coordinator's own check had missed it: `grep -nE '^21[0-9]\. \['` does not match a closed entry, which is written `211. ~~[`. That is the `mr2l.91` shape — two issues numbered 187 — one allocation away from happening a second time.
    **Tracker:** `beadloom-7c6k`. Filed separately from BDL-067 by owner decision — a different defect with a different fix, deserving its own measurement rather than a line at the end of another PR.

213. [2026-08-31] [LOW] `decision-reason` reads a table of claims-and-measurements as a table of decisions

    **Severity:** low (a warning, not a block — but it is a false positive against honest documentation, and those teach people to stop reading the output)
    **Command:** `beadloom ci` (the `docs quality` step)
    **Context:** the BDL-067 coordinator wrote its verification of a subagent's report as a two-column table — the claim in one column, what re-measuring it produced in the other — in `ACTIVE.md`.
    **Issue:** the check reported `decision-reason: the decision carries no reason` against a row that records a *measurement*, not a decision. Rewriting the same content as a bulleted list silenced it, with no change in meaning. A table of "claim → what I measured" is a shape this repository will keep writing, because the playbook asks a coordinator to verify rather than believe its subagents, and nothing distinguishes it from a decision table but the words in the header.
    **Expected:** either recognise a verification table by its header vocabulary, or scope `decision-reason` to a section the document declares as decisions rather than to any two-column table.
    **Related:** the same run showed a second-order version of the problem — the coordinator counted error-level lines with `grep -c "::error"` and matched its own prose, because the text quoted the token. A substring count is not a measurement of severity.

212. [2026-08-31] [HIGH] The review's withholding is defeated by the epic document the playbook itself mandates

    **Severity:** high (the withholding is the whole mechanism; where it is ceremonial, the review's independence is asserted and not held)
    **Command:** `beadloom review-brief <bead-id>` + the `/coordinator` review-launch prompt
    **Context:** BDL-067, review bead `beadloom-e8s4.4`. The launch prompt carried no author summary — deliberately, per the playbook's own rule that a review prompt carries the bead id and nothing else about the change.
    **Issue:** `review-brief` reported **0 comments withheld** and was correct: the authors' accounts were not in bead comments. They were in `ACTIVE.md` — the per-bead Results table, carrying the `gate._step_lint -> lint_step` API change, the red-verification counts and the coverage numbers — and the launch prompt named `ACTIVE.md` as required reading, because the playbook says a role subagent gets `CONTEXT.md` + `ACTIVE.md`. So the coordinator withheld the author's account through one channel and handed it over through another, in the same prompt. **The reviewer detected this and declared it unprompted**, which is the only reason it is written down; nothing in the tooling could have reported it.
    **Expected:** the review launch prompt must not name `ACTIVE.md` (fixed as practice on 2026-08-31), and `review-brief` should be able to say that a document the reviewer was told to read carries author accounts — a withholding that a neighbouring file defeats is withholding nobody performed.
    **Related:** #204 (`review-brief` reports "0 withheld" and cannot know what the coordinator's prompt contained) — this is that issue arriving with a measured instance, and the instance is worse than the issue as written: the leak came not from a careless prompt but from the prompt the playbook prescribes.

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

207. [2026-08-26] [MEDIUM] The pre-commit hook re-stages `.beads/issues.jsonl` after an agent deliberately unstages it

    **Severity:** medium (it defeats the one discipline that keeps concurrent waves from committing each other's work)
    **Context:** self-reported by `.7` of BDL-062, unprompted, as "one thing to know before the next agent commits".

    `.7` unstaged `.beads/issues.jsonl` on purpose — it was another agent's tracker export — and `active-sync --stage` in the pre-commit hook **added it back**, saying so on stderr.

    The project CLAUDE.md instructs every agent, in these words: *"Commit only your own files, by explicit path — never `git add -A`."* That instruction is **not sufficient on its own**, because a hook stages a file after the agent has decided not to. An agent following the rule exactly still commits another agent's state.

    Same family as #194 (`bd merge-slot` is not an exclusion primitive): the concurrency discipline this project documents rests on primitives that do not enforce it. Two independent mechanisms, one gap.

    **Strengthened 2026-08-27 by BDL-062 `.12`.** An explicit pathspec commit — `git commit -- README.md README.ru.md`, which builds a temporary index and normally ignores hook staging — **did not** prevent it: `beadloom active-sync ADDED these path(s) to this commit: .beads/issues.jsonl`. So the pathspec form is not a workaround, and "commit only your own files by explicit path" cannot be satisfied by any agent following it exactly.

206. [2026-08-26] [MEDIUM] `docs/**/features/*/SPEC.md` is excluded from `docs audit` outright, so declared facts drift freely there

    **Severity:** medium (SPECs are where a node's contract is written, and they are the one doc class nothing fact-checks)
    **Context:** `.7` swept 97 documents and found what `.4`'s narrower sweep could not reach.

    `scanner._EXCLUDE_PATTERNS` drops `docs/**/features/*/SPEC.md` and `docs/**/features/**/SPEC.md` from the audit's surface entirely. Consequence, measured by `.7`: **three forward references to `3.0.1`** — a release that did not exist — survived in SPEC files, the same defect `.4` had removed from `doc-sync/README.md:95` hours earlier. It removed the instance it could see.

    Also found in the same sweep: stale gate step lists in **eight** files, one naming a `coverage-lint` step that does not exist.

    The exclusion is presumably deliberate (SPECs are generated skeletons in some projects). But "excluded" and "verified" print the same way in the coverage report, which is this feature's whole subject one level up. At minimum the audit should name the class it does not read.

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

204. [2026-08-26] [MEDIUM] `review-brief` reports "0 withheld" and cannot know what the coordinator's prompt contained

    **Severity:** medium (a number that describes the mechanism's ignorance rather than the reviewer's; the exact class BDL-062 exists to close)
    **Context:** self-reported by the `.6` review agent as the FIRST line of its verdict, unprompted.

    The withholding mechanism exists so a reviewer meets the work without the authors' account of it. `review-brief` printed **"0 withheld"**. The account had already arrived — through the coordinator's launch prompt, which carried `.4`'s "14 corrections, none of the 9 self-lint tests edited", `.5`'s "113 parses / 49 files / zero non-stream lines", `.5`'s two self-caught neutered-passing tests, `.9`'s severity fix, #198's 363/363 and #199/#200 by number.

    So several review checks were **verifications of stated claims rather than independent discoveries**, and the tool said withholding was in force. `--release` could not establish independence either: one tracker identity (#194).

    The mechanism measures its own channel and reports as if it measured the reviewer's knowledge. It has no way to see the prompt, and it does not say so — it says `0`.

    **This is the coordinator's process failure and the tool's honesty failure at once**, which is why it is filed rather than merely noted. Fix candidates: `review-brief` states the surface it can and cannot see instead of a bare count; or the coordinator's brief is itself passed through the withholding surface. Choosing is the work.

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

194. [2026-08-26] [HIGH] [External: bd 1.0.4] `bd merge-slot` is not an exclusion primitive — every agent is the same actor, and `release` is not owner-checked

    **Severity:** high (CLAUDE.md mandates this primitive before every commit in a shared working tree; it cannot deliver what it is relied on for)
    **Command:** `bd merge-slot acquire` / `release`
    **Context:** reported by the `.2` dev agent of BDL-062 — its second `acquire` queued rather than granted, it committed and released anyway, and the release may have freed the concurrent `.3` agent's hold. Reproduced by the coordinator immediately after.

    **Two independent defects, both measured.**

    *One — identity collapse.* The actor chain is `$BEADS_ACTOR` → `git user.name` → `$USER`. On this machine:

    ```
    BEADS_ACTOR=<unset>   git user.name=v.zoologov   USER=v.zoologov
    ```

    Every concurrent agent in this repository resolves to the same actor, so `acquire` cannot tell a sibling agent from the holder itself.

    *Two — `release` accepts any caller.* This survives the first defect being fixed:

    ```
    BEADS_ACTOR=agent-A bd merge-slot acquire   ✓ Acquired    Holder: agent-A
    BEADS_ACTOR=agent-B bd merge-slot acquire   ✗ Slot held by: agent-A     <- correct
    BEADS_ACTOR=agent-B bd merge-slot release   ✓ Released                  <- NOT correct
    ```

    `agent-B` unlocked `agent-A`'s hold and was told it succeeded. The primitive is advisory in both directions: it can refuse an acquire, and it cannot defend a hold.

    **Why it matters here.** `.beadloom/flow/claude/CLAUDE.md` instructs every agent to `acquire --wait` before committing and `release` after, because concurrent waves share one working tree. That rule rests on mutual exclusion this primitive does not provide. Two agents can commit interleaved after any stray release — which is exactly what the `.2` agent suspects happened.

    **Partial mitigation, adopted now:** the coordinator exports a distinct `BEADS_ACTOR` per subagent, which restores acquire-time refusal. It does **not** address the release hazard, and saying otherwise would overstate it. A caller-checked release has to come from `bd`.

    Related: #187 of 2026-08-25 (`bd list --json`), also External, also a default of the tracker rather than of Beadloom.

    **Third defect, measured 2026-08-27 — the queue admits the holder as its own waiter.** The coordinator held the slot as `coordinator` and ran `acquire --wait` again; instead of being recognised as the holder it was appended to its own queue:

    ```
    holder : coordinator
    waiters: ["v.zoologov", "coordinator", "agent-viaj-12", "agent-viaj-13"]
    ```

    Every `release` then handed the slot back to the same identity, so the queue could not drain and the hold looked permanent from outside. Two agents queued behind it; `.12` polled ~18 minutes across two rounds, saw the holder never change, and committed without the slot — declaring the excursion, and reasoning correctly that leaving finished work uncommitted in a shared tree is the larger version of the hazard the slot exists to prevent.

    **Deterministic reproduction, 2026-08-27, one actor, two commands:**

    ```
    BEADS_ACTOR=probe bd merge-slot acquire         -> acquired
    BEADS_ACTOR=probe bd merge-slot acquire --wait  -> "Slot held by probe, added to waiters queue (position 5)"
    ```

    The holder is enqueued behind itself. `position 5` also shows that waiters from earlier sessions survive a release, so the queue accumulates identities that will never wake.

    **This is not misuse.** The project CLAUDE.md tells every agent to run `acquire --wait` before committing, and an agent that commits twice runs it twice. Following the documented discipline exactly is what corrupts the primitive. The coordinator drained the queue once, used the slot normally for several more commits, and recreated the same deadlock — which then blocked the 3.0.2 release agent, who checked the slot rather than trusting the coordinator's assurance that it had been cleared, and was right to.

    **The coordinator caused this**, by treating `acquire --wait` as idempotent. But a mutual-exclusion primitive that enqueues its own holder behind itself is a deadlock the caller cannot see: `bd merge-slot check` reports a live-looking holder and a growing queue, with nothing distinguishing that from a legitimately busy slot. Combined with the two defects above, an agent following the documented discipline exactly can be blocked indefinitely by a peer that has already finished.

193. [2026-08-26] [MEDIUM] `framework_count` counts nodes that declare a framework, not frameworks — the name and its keywords promise the other number

    **Severity:** medium (dormant today; it becomes a false mismatch the moment any document states the true number)
    **Command:** `beadloom docs audit --json`
    **Context:** found while scoping BDL-062, checking why `framework_count` equalled `node_count` exactly.
    **Measured on `main`@`cdc16de`:**

    ```
    facts.framework_count.value = 84        # == node_count, exactly
    nodes carrying a framework  = 84
    DISTINCT frameworks         = 1         # {'pytest': 84}
    ```

    `_collect_framework_count` counts nodes whose `extra.tests.framework` is non-empty. The fact is named `framework_count` and the scanner matches it on the keywords `["framework", "supported framework"]` — both of which promise *how many frameworks*, not *how many nodes declare one*.

    So a document stating the true fact — "Beadloom supports 1 test framework" — would be reported as disagreeing with 84. The audit is currently `not_covered` on it only because no document happens to phrase it that way. The defect is latent in the prose, not in the code path.

    Same family as BDL-062's subject: a fact whose name does not describe what it computes, sitting green because nothing exercises it. Distinct from #187/#190 — this is semantics, not extraction.

    **Fix decided — rename.** Two later measurements settled it, so this is no longer an open choice.

    *The DISTINCT candidate is worse, measured by `.3`:* `unverifiable_reason('framework_count', 1)` returns *"its value is 1: 0 and 1 are too common in prose to be read as claims"*. Counting distinct frameworks yields 1 here, which renders the fact structurally uncheckable on this repository and on every single-framework project. It buys correct semantics at the price of never being verifiable again.

    *The defect is no longer latent — it reached the graph,* found by `.1`'s new `graph_summary_facts` rule:

    ```
    route-extraction summary states framework_count 12 but this project computes 84 (graph DB)
    summary: "API route extraction — tree-sitter AST + regex fallback across 12 web frameworks"
    ```

    The summary is **factually correct**: the extractor carries exactly 12 framework literals — `echo, express, fastapi, fiber, flask, gin, graphql_python, graphql_schema, graphql_ts, grpc, nestjs, spring`. Two unrelated meanings of "framework" collide under one fact name: *web frameworks a component parses* versus *nodes declaring a test framework*.

    So the finding is a true positive for the defect and a false positive for the node. The `.1` agent deliberately built **no** suppression mechanism, and was right to: silencing a correct sentence to protect a misnamed fact is backwards, and a silencer built before the owner has ruled would have had no caller.

    Renaming to `nodes_with_framework`, with scanner keywords that mean that, clears all three at once — the latent prose landmine, this live finding, and the collision itself. It has prose consequences, so it lands with `.4`/`.7` of BDL-062.

192. [2026-08-26] [HIGH] A virgin `beadloom init --yes` leaves `beadloom ci` RED — the bootstrap writes a domain with no `part_of` edge and a rule that requires one

    **Severity:** high (the first gate an adopter runs fails on a repository nobody has touched, and the failing rule was written by the same command one step earlier)
    **Command:** `beadloom init --yes --mode bootstrap` then `beadloom ci`
    **Context:** measured while verifying the 3.0.0 BUILT ARTIFACT (`beadloom-mr2l.90`) against a scratch adopter project — a TypeScript service at `0.4.1` with one file under `src/`, installed from the wheel into a fresh venv. Not introduced by 3.0.0: `rules_gen.py` and the bootstrap classifier both predate it. It had never been measured, because everything this project measures runs on this project, whose graph has been hand-authored since BDL-008.
    **Measured, on the built wheel:**

    ```
    beadloom init --yes --mode bootstrap   ->  rc 0   Graph: 2 nodes, 0 edges (preset: monolith)
    beadloom lint                          ->  rc 0
    beadloom lint --strict                 ->  rc 1   domain-needs-parent:require:error:::src:
    beadloom ci                            ->  rc 1
    ```

    **Issue:** the classifier writes a `src` node of kind `domain` and **no edges at all** (`services.yml` has no `edges:` key), while `generate_rules` writes `domain-needs-parent` whenever any node is a domain. The two halves of one command disagree, so the scaffold fails its own gate immediately.
    **Why the existing guard does not cover it:** `rules_gen.py` already carries this exact worry for `feature` — BDL-UX #71 made `has_edge_to` an empty matcher so a feature nested under a service is not flagged, and the comment says requiring a domain parent *"makes a clean bootstrap fail its own `lint --strict` gate out of the box"*. An empty matcher relaxes WHERE the edge may point; it does not excuse a node that has no edge. The `service-needs-parent` rule was removed outright for the same class. So the fix was applied twice, to the two neighbours, and the middle case is what ships.
    **Expected:** one command's output must pass that command's own rules. Two candidate fixes, and the choice is a decision rather than a patch: (a) the bootstrap emits `part_of` edges from every classified domain to the root service node, which makes the graph structurally complete and is what a hand-authored graph looks like; or (b) `generate_rules` omits `domain-needs-parent` when the bootstrap produced no `part_of` edge to require, which keeps the graph honest about what was inferred but ships a project with one fewer structural rule. (a) states a structure the classifier did not verify; (b) leaves the rule to be added when the human authors the parent. Whichever is chosen, `init` must not print `rc 0` over a graph that fails the rules it just wrote.
    **Workaround:** add the edge by hand — `edges: [{src: src, dst: <root-ref-id>, kind: part_of}]` in `.beadloom/_graph/services.yml`, then `beadloom reindex`.

    > **FIXED on `features/BDL-067` (`beadloom-e8s4`, 28 beads, nine review passes). Not yet merged, so this entry stays here until it is.** Both candidate fixes were on the table and (a) was taken — the bootstrap emits the `part_of` edge — with the addition that the epic closed the CLASS as well as the instance: `init` writing a graph and `init` requiring a graph are two halves of one command, and nothing checked that they agreed.
    >
    > **The instance.** `bootstrap_project` and `import_docs` are the two writers of graph nodes, and they now hold ONE post-condition — every node carries at least one outgoing `part_of` edge, to its classified parent where one exists, to the root service node otherwise, and to nothing when the node's `ref_id` is the root's own — computed by one function, `parent_edges.missing_parent_edges`. The fallback branch this report found (a flat `src/index.ts` produces no clusters, so the loop that attaches top-level nodes to the root reaches none of them) is closed by the post-condition rather than by a patch to that branch.
    >
    > **The class.** `beadloom init` no longer reports success over a graph that fails the rules on disk beside it. Every entry point that writes a file under `.beadloom/_graph/` re-indexes and then runs the Gate's own `lint_step` — the same object `beadloom ci` runs, shared rather than restated, so the two verdicts cannot drift — and exits 1 when it does not pass, withdrawing the completion it has already printed and naming each error-severity rule with its node and the graph file that node was written into.
    >
    > **Measured over four entry points and three modes**, not over the one this report used: eight (entry point x mode) cells, derived from `init`'s own source by `tests/test_init_one_table_over_every_axis.py` rather than listed by hand, on fixtures that are not this repository. The entry points are `--yes`, `--bootstrap`, `--import` and the default interactive wizard; the wizard was the branch a human adopter meets first and it carried this exact shape through four green waves, because the tests covering the other two were parametrised over two BINDINGS of `bootstrap_project` and the wizard shares one of them. Two paths take no verdict and both are stated rather than implied: a run that changed nothing under `.beadloom/_graph/`, and the wizard's `edit` review answer, which hands the graph over to be edited by hand.
    >
    > **What is NOT closed, stated because the epic's own accounting requires it.** `init` still ends in a Python traceback on a graph file it cannot handle — 24 runs over the same eight cells crossed with three shapes of a hand-edited `.beadloom/_graph/legacy.yml`, of which the 15 that reach the file traceback, in `application/reindex/indexing.read_declared_docs` and `graph/loader.load_graph`. That is #220, open, pinned by a test that fails the day somebody closes it. And `init` still writes two nodes under one `ref_id` on the classic Python `src/<project>/` layout, where `domain-needs-parent` goes inert rather than red, so the verdict above does not see it — #214, open.

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

191. [2026-08-23] [MEDIUM] `setup-agentic-flow` without `--force` still recomposes a hand-edited ROLE adapter — the asymmetry `--fix` no longer has

    **Severity:** medium (it is the #139/#151/#186 data-loss shape in the sibling command, and it is now the only door left open)
    **Command:** `beadloom setup-agentic-flow` (no flags), on a repo with a `flow.yml`
    **Context:** recorded, deliberately NOT fixed, by BDL-061 `.58` — it was named as adjacent to that bead and absorbing it would have made one bead answer for two decisions. `.59` closed #186 by teaching `config-check --fix` one rule: *rewrite only what Beadloom can prove it wrote*. `setup-agentic-flow` composes the role adapters through `generate_adapters(config, project_root)` with no `preserve=` argument, so the same hand edit `--fix` now declines is recomposed over by the command `--fix`'s own remediation tells the reader to run.
    **Why it is undecided rather than a defect with an obvious fix:** the two commands have genuinely different contracts. `--fix` is a repair and must not destroy; `setup-agentic-flow` is a scaffold and an adopter may reasonably expect a re-run to reinstate the shipped flow. But the commands + `CLAUDE.md` path in the SAME command already declines a hand edit and reports migration guidance (BDL-UX #188 made that guidance visible), so today one command treats two of its three artifact kinds one way and the third the other, with nothing stating which is intended.
    **Expected:** decide it, and make the three kinds agree. If the scaffold should preserve, pass `preserve=` the way `.59` does and report the decline; if it should overwrite, say so in the output and in the SPEC, and stop `config-check --fix` from pointing at a command that will do what `--fix` refused.
    **Related:** #186 (the decided half), #139, #152, #188.

190. [2026-08-23] [LOW] `docs audit` reads a version mentioned as an EXAMPLE as a claim about this project — a doc cannot cite anybody else's version

    **Severity:** low (it is a false positive with an obvious workaround, and it blocks a specific and now-recurring kind of sentence)
    **Command:** `beadloom docs audit` / the `docs-audit` step of `beadloom ci`
    **Measured** while documenting BDL-UX #183. The sentence *"a JavaScript project at `0.4.1` was told `2.2.0`"* — an illustration of the defect being fixed, in backticks — failed the Gate twice: `doc-fact-stale: version: doc says '0.4.1' but project state is '2.2.0'`. `doc_sync/scanner.py::_extract_versions` matches every `\bv?\d+\.\d+\.\d+\b` outside a version pin and hands each one to an exact-match comparison against the project's own version; there is no notion of a version that is *about something else*.
    **Why it is worth an entry:** the sentences this blocks are exactly the ones this epic keeps needing to write — "an adopter at X was told our Y". It is also the version-shaped cousin of #169, which drew the token boundary for counts and left versions to their own regex. The workaround used in `.58` was to rephrase (*"a JavaScript project a major version behind was told ours"*), which is weaker prose than the measurement deserved. Recorded rather than worked around silently, because the next writer will meet it and reach for `docs_audit.ignore`, which is the wrong door.
    **FOURTH INSTANCE, 2026-08-26 (BDL-062 `.4`), and this one is the sharpest.** The bead that made the root node's `(vX.Y.Z)` a checked claim then added a line to `CONTRIBUTING.md`'s release process explaining WHY the bump matters -- *"rather than letting it drift the way it drifted from 1.5.0 to 3.0.0 unnoticed"*. `beadloom ci` went rc 1 on `CONTRIBUTING.md:253: version "1.5.0" -> 3.0.0`. The sentence describing the drift the release checklist exists to prevent is a sentence the checker cannot survive, and the workaround was the same weakening this entry already recorded: *"letting it fall two majors behind unnoticed"*, which does not say what the two majors were. Three instances were prose about the epic; this one is prose about the RELEASE PROCESS, which every adopter reads.

    **Expected:** treat a version as a claim about THIS project only when the mention is attributive — near a project-version keyword, or in a line that does not already name another subject — the same clause-scoping `.45` gave the count facts. Failing that, an explicit inline escape (a fenced block, or a marker) so a doc can quote a foreign version without a tolerance entry.
    **Related:** #169 (the token boundary for counts), #161, BDL-057 (the audit surface).

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

181. [2026-08-23] [MEDIUM] Clean-room verification is the right technique and structurally cannot see a cross-bead interaction — nothing runs the combined tree until a human does

    **Severity:** medium (no defect ships, but every agent reports green on a tree that is red, and the discrepancy reads as a contradiction rather than as two different measurements)
    **Command:** the multi-agent wave protocol in `/coordinator`, not a Beadloom command
    **Context:** BDL-061 S2b ran four dev beads across two waves in one shared working tree. Because a shared tree makes a full-suite run meaningless for any single agent, each verified in a **clean room** — `git archive HEAD` plus only its own files — and each honestly reported green. The coordinator's combined run then found `beadloom ci` rc 1 with 28 stale pairs.
    **Issue:** the clean-room technique is *correct* — it is the only way to attribute a result to one bead while neighbours are editing — and it is *blind by construction* to any interaction between beads. Nothing in the protocol runs the combined tree until the coordinator does it at wave end, so a wave's integration state is unmeasured for its whole duration and the first honest number arrives last.
    **Why it is worth filing rather than shrugging at:** four agents reported green, the tree was red, and none of them was wrong. That is a signalling failure, not an engineering one, and it will recur on every wave. It also inverts the usual risk: the *more* carefully each agent isolates itself, the less anyone knows about the whole.
    **Expected:**
    - The wave protocol should name the combined run as a distinct, owned step — not a coordinator habit. It is currently in nobody's bead.
    - An agent's green should be *typed*: "green in a clean room over N files" is a different claim from "green on the tree", and reporting them with the same word is what makes the discrepancy read as a contradiction.
    - Cheapest mechanical improvement: have the last agent of a wave, or the merge-slot holder, run the combined gate — someone already holds a lock at exactly the right moment.
    **Related:** #118 (parallel agents collide on the shared pre-commit hook) — same root, that the wave shares one tree; BDL-061 S6 (`beadloom waves`) is where the decision about what may share a tree belongs.

180. [2026-08-24] [MEDIUM] A `docs-audit` fact that fails to COLLECT is silently dropped from the declared list, so coverage cannot report it

    **Severity:** medium (it is the one hole the coverage report cannot cover, and it is in the mechanism that was just built to close #173)
    **Command:** `beadloom docs audit`, `beadloom ci`
    **Context:** found while implementing `beadloom-mr2l.45`. `FactRegistry.collect` wraps every source in `try/except`, logs a warning, and omits the fact. Reproduced in-process: with the Click surface registry unpopulated, `cli_command_count` vanishes and the audit reports `2/8 declared fact(s) verified` — an honest-looking fraction over a denominator that silently lost a fact. The same happens to `rule_type_count` against a database with no `rules` table, and to `version` when a manifest cannot be parsed.
    **Issue:** BDL-061.45 made the audit report what it could not VERIFY, but a fact that could not be COLLECTED never reaches that report. Coverage can only speak about facts in `result.facts`, so the failure mode moved one level up rather than away: *a fact that failed to collect reads as a fact that does not exist*. The warning goes to a logger nobody reads at `beadloom ci` time — #178's shape exactly.
    **Expected:** `FactRegistry` records collection failures alongside successes (`uncollected: {name: reason}`), the audit prints them in the same place it prints `not_covered` / `unreadable`, and the declared-fact denominator counts them. A fact that could not be computed is a fourth coverage status, not an absence.
    **Related:** #173 (the coverage report this hole sits inside), #174/#175 (*unverifiable is not clean*), #178 (honesty routed to a channel nobody reads).

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

173. [2026-08-23] [HIGH] 🔴 `docs audit` reports green about facts it never checked — three measured false-negative classes, and one of them printed a false claim as *verified*

    **Severity:** high (a false positive fails the Gate and gets fixed; every one of these is silent, and the audit's own output reads as a clean bill of health)
    **Command:** `beadloom docs audit`, `beadloom ci`
    **Context:** the sweep asked for by `beadloom-mr2l.44` while fixing #169. #169 was found twice by the Gate going red; nobody had looked for the half that keeps the Gate green. Measured on this repo, 2026-08-23.
    **The worst one printed a lie as a verification.** `The graph holds 1,067 nodes.` was extracted as `067`, compared equal to the project's `node_count` of 67, and listed under **Fresh (verified)** — the audit affirmed a claim that is off by a thousand. Symmetrically, the TRUE sentence `The suite has 6,390 tests.` extracted as `390` and was reported stale. One defect, both directions, and only the noisy direction was ever noticed. (Fixed in `.44`; recorded here as the proof the class is real.)
    **Two more, unfixed and pinned as strict `xfail`s** in `tests/test_doc_scanner_tokenization.py::TestKnownBlindSpots` so they go LOUD when someone fixes them:
    - Counts below 10 are never extracted for any `*_count` fact. `language_count` is **1** in this repo, so that fact cannot be audited at all — any claim about it, right or wrong, is invisible, and the audit reads green.
    - A Layer-1 modifier word anywhere in the +/-3 word window suppresses a genuine count even when it modifies a different noun: `The graph holds 316 edges, one per import.` yields nothing, because of `per`.
    **The measurement that makes the shape plain:** the audit prints a Ground Truth block of **nine** facts and then `13 mention(s) fresh` — and all 13 are the **same** fact (`mcp_tool_count`). `cli_command_count`, `edge_count`, `node_count`, `rule_type_count`, `test_count` and `version` have **zero** findings; no doc in the repo states the current version at all. A green `docs-audit` leg today means "one fact of nine was checked", and nothing in the output says so. By design but equally silent: `SPEC.md` / `CONTRIBUTING.md` suppress all count facts and `docs/**/features/*/SPEC.md` is excluded outright — 26 of the 72 `.md` files under `docs/` are never scanned.
    **Expected — report the surface, not more heuristics:**
    - Emit per-fact coverage: for each fact in the registry, the number of mentions found. A fact with **zero** mentions is `not_covered`, printed as such, and never counted as passing. This is "unknown is not zero" applied to the audit's own output.
    - Name the files whose counts were suppressed by the file-type heuristic, and why.
    - Only then revisit the `<10` threshold and the modifier window: with coverage reported, their cost is visible instead of invisible.
    **Related:** #170's third piece ("report the surface, not just the firings") is the identical defect on the guard binding; #161 and #169 are the same audit being confident about text it misparsed. Tracked as `beadloom-mr2l.45`.
    > **FIXED in BDL-061 (`beadloom-mr2l.45`).** Not three parser fixes — the audit now REPORTS WHAT IT DID NOT VERIFY, which is the same equation as #174/#175 (`unverifiable is not clean`) and #172 (a rule that cannot match reports itself). Three parts. (1) **Per-fact coverage.** Every declared fact carries `verified` / `not_covered` / `unreadable`, printed against the fact in the `Ground Truth` block and summarised on the one line everybody reads — including the `beadloom ci` step line: `14 mention(s) fresh; 2/9 declared fact(s) verified, NOT VERIFIED: cli_command_count, edge_count, ...`. A fact nothing was found for is never counted as passing, and a mention hidden by a `docs_audit.ignore` rule is NOT coverage. (2) **Clause-scoped matching** fixes the modifier class: both the modifier window and the keyword window stop at `,` `;` `:` and the dashes, so `316 edges, one per import` is read and the `14` in `exposes 18 tools: 14 over the graph` is not. The separator set was chosen by MEASUREMENT — parentheses are deliberately excluded because they cost the true verification in `MCP tools (18):`, and a lost true positive is the very silent false negative being fixed. Repo-wide: 0 mentions gained, 5 lost, all five confirmed false positives; three more `docs_audit.ignore` entries went dead and were retired. (3) **The scan surface is published** — all 33 unread documents named with the pattern that skipped them, plus the count-suppressed ones, in `--verbose` and in `--json`. The single-digit floor was RE-MEASURED and KEPT: removing it yields 14 extra mentions on this repo of which 13 are ordinals, table cells and category breakdowns, several of which would have failed the Gate. Trading a silent false negative for a loud false positive that then needs a suppression entry is the wrong trade — so the floor stays and `language_count` (value 1) is now reported `unreadable` by name instead of reading green. Coverage is reported, not enforced (a WARN every project would carry on every run would spend the channel `sync-check` needs); `docs audit --fail-if unverified>N` is the opt-in. MEASURED after the fix: **2 of 9 declared facts verifiable-and-verified on this repo, 6 `not_covered` because no document states them, 1 `unreadable`** — and every one of those seven is now named in the output.

171. [2026-08-22] [MEDIUM] Concurrent `bd create` shifts the id out from under the id written in the title — and the wrong dependency edge is then perfectly valid

    **Severity:** medium (silent, produces a well-formed but wrong DAG, and only surfaces when someone reads the echo)
    **Command:** `bd create --parent <id>`, `bd dep add`
    **Context:** observed in BDL-061 S2 wave 1, with three agents and the coordinator working the same epic. Our convention writes the bead's own number into its title (`[BDL-061.39][dev] ...`), but the number is authored **before** creation while the id is allocated **at** creation. During a concurrent wave those two diverge: the coordinator wrote two beads intending `.39` and `.40`; a subagent had meanwhile created its own bead, which took `.39`; the coordinator's two landed as `.40` and `.41` carrying `[BDL-061.39]` and `[BDL-061.40]` in their titles.
    **The damage is not the cosmetic mismatch, it is the wiring.** The coordinator then ran `bd dep add beadloom-mr2l.39 beadloom-mr2l.5`, which made the *subagent's* Windows-CI bead depend on the S2 core — a real edge, on a real bead, accepted without complaint, and wrong. `bd dep add` cannot detect this: every id exists and the graph stays acyclic, so there is nothing malformed to reject.
    **What caught it:** `bd dep add` echoes both beads' **full titles**, not just their ids. Reading that echo is the only reason the mis-wiring was noticed within seconds instead of surviving into the next wave. That verbosity is good design and worth keeping — the entry records it so nobody "tidies" it into id-only output.
    **Expected:** three separable pieces.
    - **Stop keeping the number twice.** Either drop the id from the title convention and let `bd` be the single source of it, or have the scaffolding write the title *after* creation from the id actually allocated. Two sources of truth for one number is the root cause; the concurrency only exposes it.
    - **Make `bd create` report the id it allocated in a form a script can consume**, so an agent that must reference its own bead does not have to predict the number. (`--json` on create would be enough.)
    - **Consider a `bd dep add --expect-title <substring>` guard**, or at minimum document that dependency wiring under a concurrent wave must be verified against `bd dep tree`, not assumed from the ids the author had in mind.
    **Note on scope:** `/coordinator` *mandates* launching independent ready beads concurrently, so this is not an exotic mode — it is the prescribed one. The id-in-title convention is ours, not `bd`'s, which makes the first fix ours to make.

170. [2026-08-22] [HIGH] 🔴 A guard bound to `Edit|Write` does not see a file written through `Bash` — the enforcement surface is narrower than the promise

    **Severity:** high (the guard reports it ran and passed on the edits it saw; the edits it never saw are indistinguishable from none)
    **Command:** `beadloom guard`, `beadloom setup-agentic-flow` (the emitted `.claude/settings.json`)
    **Context:** found while dogfooding BDL-061 S1 on this repo. The shipped hook binds `PreToolUse` with `matcher: "Edit|Write|NotebookEdit"`. An agent that edits a file with `python3 - <<EOF`, `sed -i`, or a heredoc goes through `Bash` and fires no guard at all. This is not hypothetical: the coordinator's own session was operating under an instruction to prefer `Bash` for file edits, so a whole class of edits to this very repository was unguarded while `--liveness` showed the guards healthy and firing.
    **Why it is worse than a missing matcher:** the failure is silent and it is *shaped like success*. `bead-claimed` cannot warn about an edit it was never told about, so a session that edits exclusively through `Bash` produces a clean liveness report and zero warnings — the same output as a session that complied perfectly.
    **Expected:** three separable pieces, and the third is the real one.
    - Add `Bash` to the emitted matcher and derive the edit target from the command line where it can be — necessarily partial, since a shell command's write targets are not decidable in general.
    - Because it is partial, the verdict must say so: a `Bash` invocation whose target cannot be determined is `not_covered`, not `pass`. This is the "unknown is not zero" rule applied to the enforcement surface itself.
    - **Report the surface, not just the firings.** `--liveness` today answers "did each declared guard fire?". It should also answer "what fraction of edit events could this binding have seen?" — a guard that is healthy on a matcher covering one of three write paths is 33% of a guard, and nothing currently says so.
    **Related:** M3 from review `.3` (the harness owns event routing *and* the guard list, so `.claude/settings.json` carries two decisions Beadloom cannot see) is the same defect from the other end and is already S3 work. This entry is the reason M3 is not cosmetic.

169. [2026-08-22] [MEDIUM] `docs-audit` reads a bead reference as a numeric claim — `BDL-061.29` failed the Gate as a CLI count

    **Severity:** medium (a false Gate failure, and the fix is to write around the checker)
    **Command:** `beadloom docs-audit`, `beadloom ci`
    **Context:** a SPEC sentence mentioning bead `BDL-061.29` alongside the words "the CLI" was extracted as a `cli_command_count` claim; the Gate failed with "doc says 29 but project state is 39". The number was never a claim about anything — it is the tail of an identifier.
    **Expected:** do not extract a number that is part of a larger token (`BDL-061.29`, `v2.2.0`, `Python 3.10`). Tokenize before matching rather than scanning for digits near a keyword. Same family as #161: the audit is confident about text it has misparsed.
    **Workaround:** reword the sentence — which is exactly the outcome to avoid, since it trains authors to write for the checker.
    > Fixed in BDL-061 S2 (`beadloom-mr2l.44`). The extractor now tokenizes on whitespace and
    > accepts a number only when the token's whole core is a number, so `BDL-061.33`, `v2.2.0`,
    > `Python 3.10`, `PR #33`, `cli.py:645` and `33/40` are identifiers again. No prose was
    > reworded, no tolerance and no ignore entry were added — three now-dead ignore entries were
    > RETIRED instead. Measured: 4 spurious extractions removed repo-wide, 0 genuine ones lost.

168. [2026-08-22] [MEDIUM] `pytest-randomly` produces failures no seed reproduces, and nothing in the output says the order was random

    **Severity:** medium (agent-facing: a ghost failure costs a full investigation cycle, and the log is the only place that would have warned)
    **Command:** `uv run pytest`
    **Context:** during BDL-061 S1 an adversarial run reported 30 failures; five different seeds plus `-p no:randomly` all reproduced the same 3. The 30 were an artefact of ordering interacting with on-disk state (the index DB and its `-wal`), not of the code under test.
    **Expected:** pin a seed in CI and in the pre-push Gate so a red run is reproducible by construction, and keep randomisation for a separate scheduled job whose whole purpose is to find order dependence. A random-order failure that cannot be replayed is not a signal anyone can act on.
    **Related:** #147 / `.29` friction 3 — a stale `beadloom.db-wal` left by an earlier command is one of the shared-state channels that makes ordering matter.

167. [2026-08-22] [LOW] `sync-check` prints one `[stale]` line per pair, so a single stale doc reads as a wall of 28 identical lines

    **Severity:** low (pure signal-to-noise, but it lands on every agent at every gate)
    **Command:** `beadloom sync-check`
    **Context:** one doc with many watched symbols emits one line per pair. The output is 28 lines that differ in no visible way, and the count of distinct DOCUMENTS needing attention — the number the reader actually wants — has to be derived by eye.
    **Expected:** group by document: one line per doc with the pair count and the reasons, and the per-pair detail behind `--verbose` or `--json`.
    **MEASURED AGAIN AT GATE SCALE (BDL-061 S2b, 2026-08-24), and it is worse than filed.** The combined tree of a four-bead wave reported 28 stale pairs, all of them the SAME document (`docs/domains/onboarding/README.md`) — because `symbols_hash` is per `ref_id`, one changed file makes every sibling pair of that node stale. The Gate's output, `beadloom sync-check`'s output and `beadloom doctor`'s output each carried 28 near-identical lines, so the reader's first question — *is this one document or twenty-eight?* — could only be answered from `--json`. At gate scale the noise is not merely low signal-to-noise: it misrepresents the SIZE of the problem, which is what a reader decides how to spend an hour on.

166. [2026-08-22] [MEDIUM] Adding one CLI command drifts six reference docs, and `sync-update --all --yes` does not cover them

    **Severity:** medium (the bulk escape hatch does not cover the surface that most often drifts in bulk)
    **Command:** `beadloom sync-update --all --yes`, `beadloom sync-check`
    **Context:** adding a single command (`beadloom guard`) put six `watches: cli` documents into `surface_drift`. `sync-update --all --yes` re-baselines hash/symbol pairs but not the reference-doc surface-drift path, so each of the six needed an individual `sync-update <ref>` — six commands to record one fact that was already known.
    **Expected:** `--all` should mean all, or say plainly which surfaces it does not cover. Ideally a surface change touching N reference docs is one attestation with N consequences, not N attestations.
    **Related:** #163 — bulk re-baselining is exactly the operation that needs to be recorded rather than made frictionless, so the fix here should count these, not just make them faster.
    **RE-MEASURED (BDL-061 S2b, 2026-08-24): the second half no longer holds, the first half does.** `sync-update --all --yes` DOES clear the reference-doc path — `_mark_synced_noninteractive` calls `mark_reference_synced(conn, None, project_root, all_docs=True)` and reports the count (measured on this repository at the close of S2b: `Re-baselined 7 reference doc(s)`, clearing all six drifted entries in one command) — so the six-commands-for-one-fact friction is gone. What remains is the shape: adding the single flag `sync-check --record-surface` drifted all six `watches:` documents at once, and the bulk form clears them with no record of which six were re-read. That is #163's objection, not a convenience one, and it is the half worth fixing: one attestation with N consequences should say what it attested to.

165. [2026-08-22] [LOW] External (steveyegge/beads): `bd create` costs one process per bead, so building a DAG of ~50 beads stalls

    **Severity:** low (a workaround exists and is fast) — **External**
    **Command:** `bd create`
    **Context:** a background agent building a >50-bead fixture ran for 600s without finishing, because each `bd create` is a separate process against embedded Dolt. `bd import` created 60 issues in one process in 0.88s — roughly three orders of magnitude better.
    **Expected:** document `bd import` as the way to build a DAG (`bd create --graph <plan.json>` is already noted in `/task-init`, and is the same insight). Ours to fix in the shipped guidance: any scaffolding path that creates more than a handful of beads should generate a JSON plan and import it once.

164. [2026-08-20] [LOW] The beads git-hook prints a remediation command that does not exist (`bd import -i`)

    **Severity:** low (small blast radius, but the shape is the one this log keeps recording — advice that reads authoritative and does not work)
    **Command:** any merge that changes `.beads/issues.jsonl`
    **Context:** the hook printed `Warning: Failed to import bd changes after merge / Run 'bd import -i .beads/issues.jsonl' manually to see the error`. Running it prints help: bd 1.0.4 takes the file positionally (defaulting to `.beads/issues.jsonl`) and has no `-i`. Observed on the 2.2.0 release merge, where the state was in fact consistent — the tracked jsonl held 15 open + 1 deferred and `bd list` agreed — so the warning was also a false alarm, which makes the wrong command doubly misleading.
    **Expected:** correct the message to the real invocation, and warn only when the import genuinely failed. Verify the flag set against the pinned bd version rather than assuming it. Same family as #140.
    > Tracked as a bead (P3).

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

148. [2026-08-05] [MEDIUM] `lint` prints machine porcelain when stdout is not a TTY — the human summary line vanishes in a pipe, so the documented output is not what a program receives

    **Escalated 2026-08-22 — this is not cosmetic, it produces wrong conclusions.** `sync-check` has the same TTY-dependent shape, and it corrupted the coordinator's own verification twice in one session while investigating a suspected gate defect. Counting `beadloom sync-check | grep -c '^stale'` returned **0** on a tree with genuinely stale pairs, because the piped shape omits the per-pair lines the interactive shape prints. Measured on the same tree, same moment: piped grep count **0**, exit code **2**, `--json` **2 stale pairs**. The first reading was used to conclude — wrongly — that `reindex` re-baselines sync pairs and that the gate could be turned green by running it twice. Neither is true. A monitoring surface whose shape depends on whether a human is watching will be sampled by programs and by agents, and it will silently give them the wrong number. **Any agent instruction to "count the stale lines" is unsound today**; the exit code and `--json` are the only trustworthy contracts, and that should be stated in the docs until the shape is stable.

    **Severity:** medium (contract differs by TTY; parsers written against the documented/human output silently see nothing to parse)
    **Command:** `beadloom lint` / `beadloom lint --strict`
    **Context:** Dogfood: an integration captures `lint` output to summarise it for a chat reader.
    **Issue:** interactively `lint` ends with `N violations, M rules evaluated`; through a pipe that summary line is absent and the output switches to a porcelain form. Nothing in `--help` mentions a TTY-dependent format, and there is no `--porcelain`/`--json` flag to select the shape deliberately, so a caller cannot ask for a stable contract — it just gets a different one depending on how it was invoked.
    **Expected:** keep one shape by default and gate the machine form behind an explicit flag (`--porcelain`/`--json`), or emit the summary line in both modes. TTY-dependent output shape should never be the only way to get the documented text.
    **Workaround:** downstream reconstructs the verdict from the porcelain lines and appends its own summary.

149. [2026-08-05] [LOW] `graph --format c4 --level component --scope <ref>` on a node with no internals prints a single useless `C4Container` instead of saying so

    **Severity:** low (silently useless output rather than an error — reads as a rendered diagram)
    **Command:** `beadloom graph --format c4 --level component --scope <ref_id>`
    **Context:** Dogfood: an integration offers a "detailed diagram of one container" view and passes whatever node the user names.
    **Issue:** when `<ref>` is a leaf (no nested nodes), the command exits 0 and emits a valid-but-empty C4 diagram — one `C4Container` block, no internals. Rendered, it is a single box. There is no signal distinguishing "this node has no internals" from "here are its internals", so a caller cannot tell the user the truth without pre-checking the graph itself.
    **Expected:** exit non-zero (or print an explicit note) when `--scope` resolves to a node with no contained nodes, so the caller can fall back to a neighbourhood view and say why.
    **Workaround:** downstream detects the degenerate output and falls back to the node's neighbourhood diagram plus an honest note to the reader.

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

114. [2026-06-02] [LOW] Committed VitePress scaffold ships no `package-lock.json` — `npm ci` cannot run on a fresh checkout

    **Severity:** low
    **Command:** `cd site && npm ci`
    **Context:** BDL-040 F4 BEAD-05 dogfood. The BEAD-01 scaffold committed `site/package.json` (pinned deps) but no `site/package-lock.json`. The bead instructions (and the scaffold's own header comment) say to run `npm ci && npm run docs:build`, but `npm ci` hard-requires a lockfile and errors out without one — so the very first build must use `npm install` (which then generates the lockfile).
    **Issue:** Mismatch between the documented build command (`npm ci`) and what a fresh checkout actually supports (`npm install` only, until a lockfile is committed).
    **Expected:** Either commit a `package-lock.json` alongside `package.json` (so `npm ci` works + the build is reproducible/pinned), or change the documented first-run command to `npm install`. Committing the lockfile is preferable — it pins the transitive dep tree for a deterministic dogfood/CI build.
    **Workaround:** Use `npm install` for the first build; commit the resulting `package-lock.json` so subsequent `npm ci` works.
    **Resolution (BEAD-05 follow-up):** `site/package-lock.json` is now committed (generated by `npm install`), so `npm ci` works on a fresh checkout and the dogfood build is reproducible/pinned. `site/node_modules` + `site/.vitepress/dist` stay gitignored.

71. [2026-03-10] [MEDIUM] `beadloom init --bootstrap` generates rules that immediately produce lint violations

    **Severity:** medium
    **Command:** `beadloom init --bootstrap -y` → `beadloom lint --strict`
    **Context:** Bootstrapping Beadloom on a production FastAPI monolith project provided for field-testing. The project has a clean architecture with domain packages containing `graphql/` sub-packages.
    **Issue:** The auto-generated `rules.yml` includes a `feature-needs-domain` rule that requires every feature to be `part_of` a domain. However, the bootstrap classifier creates features inside services too (e.g., `core-rest` feature → `part_of` core service; `tasks-graphql` feature → `part_of` tasks service). Running `beadloom lint --strict` immediately after init exits with 2 violations — a "broken out of the box" experience.
    **Expected:** Either (a) the default rule should accept features inside both domains and services (`has_edge_to: {}`), or (b) the bootstrap classifier should only classify nodes as `feature` when they are inside a `domain`-kind parent (not `service`-kind). Zero violations should be the norm after a clean bootstrap.
    **Workaround:** Manually edit `.beadloom/_graph/rules.yml`: change `has_edge_to: { kind: domain }` to `has_edge_to: {}` and rename the rule to `feature-needs-parent`.

72. [2026-03-10] [LOW] `beadloom setup-rules` doesn't detect IDE when marker directory is gitignored

    **Severity:** low
    **Command:** `beadloom setup-rules`
    **Context:** The project has `.cursor/` listed in `.gitignore`, so the directory doesn't exist on a fresh clone, but does exist in the working tree.
    **Issue:** `setup-rules` outputs `No IDE markers detected` and creates no files. The `.cursor/` directory was present in the filesystem but gitignored. Auto-detection apparently checks for marker files but the detection logic may miss directories that exist but are in `.gitignore`.
    **Expected:** If marker directories exist on disk (regardless of gitignore), they should be detected. Alternatively, if no markers are found, print a helpful hint: `"No IDE markers detected. Use --tool cursor|windsurf|cline to specify."` so the user doesn't have to run `--help` to discover the flag.
    **Workaround:** Explicitly pass `--tool cursor`.

73. [2026-03-10] [LOW] `beadloom doctor` reports "Version drift" and "Package drift" by checking `.claude/CLAUDE.md`

    **Severity:** low
    **Command:** `beadloom doctor`
    **Context:** After bootstrapping on an external project, the existing `.claude/CLAUDE.md` contained content from a previous project (Beadloom itself) with `Version: 1.9.0` and DDD package references (`context_oracle/`, `doc_sync/`, etc.).
    **Issue:** `doctor` checks `.claude/CLAUDE.md` for version and package claims, finding `CLAUDE.md claims 1.9.0, actual is 1.7.0` and `Package drift: claimed but missing: context_oracle, doc_sync, graph, infrastructure, onboarding, services, tui`. These are false positives — CLAUDE.md is a user-maintained file that may describe the project in custom terms, not necessarily matching Beadloom's internal structure.
    **Expected:** `doctor` should validate `.beadloom/AGENTS.md` (which Beadloom generates and controls) rather than `.claude/CLAUDE.md` (which is user-authored and project-specific). If CLAUDE.md is checked at all, it should be limited to `<!-- beadloom:auto-start -->` / `<!-- beadloom:auto-end -->` sections.
    **Workaround:** Ignore the warnings; they're false positives caused by stale CLAUDE.md content from another project.

88. [2026-03-11] [HIGH] Incremental `beadloom reindex` returns 0 nodes after doc enrichment

    **Severity:** high
    **Command:** `beadloom reindex`
    **Context:** After enriching 18 documentation files (replacing skeleton content with detailed descriptions), an incremental `beadloom reindex` was run to update the index.
    **Issue:** Incremental reindex returned `Nodes: 0, Edges: 0, Symbols: 0, Imports: 0` — completely empty index. The `services.yml` was verified to be intact (18 nodes, 34 edges, correct YAML block format). Running `beadloom reindex --full` immediately after returned `Nodes: 18, Edges: 34, Symbols: 272` — completely normal.
    **Root cause hypothesis:** Incremental reindex likely detects that many files changed (18 doc files + potentially cached state) and incorrectly drops the entire index instead of updating it. The SQLite cache may have become inconsistent after bulk doc writes by parallel agents.
    **Expected:** Incremental reindex should never return 0 nodes when `services.yml` is valid. If the incremental path detects inconsistency, it should auto-fallback to `--full` reindex rather than returning an empty result. At minimum, print a warning: `"Incremental reindex returned 0 nodes — possible cache inconsistency. Retry with --full."`.
    **Workaround:** Always use `beadloom reindex --full` after bulk changes. Do not rely on incremental reindex after modifying many files simultaneously.
    **Root cause (confirmed 2026-05-28 code review):** NOT cache inconsistency. `incremental_reindex` (`infrastructure/reindex.py:1088-1296`) never assigns `result.nodes_loaded`/`edges_loaded` on the docs/code-only path — they keep their `ReindexResult` default of `0`, and the CLI prints them verbatim (`services/cli.py:288-289`). The index is intact; this is a **display bug**, not data loss. Trivial fix: query live DB totals (as the `nothing_changed` branch already does at `cli.py:274-279`). Note this is a recurrence — the same symptom (#21) was "fixed" in v1.5.0.

86. [2026-03-10] [HIGH] YAML flow-style edges silently produce 0 nodes on reindex

    **Severity:** high
    **Command:** `beadloom reindex`
    **Context:** During manual graph editing of `services.yml`, edges were written in YAML inline/flow format: `- { src: houses, dst: core-external-inspection-system, kind: depends_on }`. This is perfectly valid YAML per the spec. Nodes were written in block format.
    **Issue:** After saving `services.yml` with flow-style edges, `beadloom reindex` returned `Nodes: 0, Edges: 0` — a complete silent failure. No error, no warning. The YAML parser appears to not handle inline mapping syntax for edge entries. Rewriting all edges in block format (`- src: X\n  dst: Y\n  kind: Z`) fixed the issue immediately (18 nodes returned).
    **Expected:** Either (a) the YAML parser should correctly handle flow-style mappings (they are valid YAML), or (b) if the parser has limitations, it should detect the issue and emit a clear error: `"Error: edges at line N use unsupported inline format. Use block format instead."` Silent 0-node results are the worst possible failure mode — the user thinks the graph is empty.
    **Workaround:** Always use YAML block format for edges. Never use `- { key: value }` inline format in `services.yml`.

93. [2026-05-28] [LOW] `AGENTS.md` MCP tool list is stale (documents 13 tools, actual is 14)

    **Severity:** low
    **Command:** `beadloom doctor`
    **Context:** Self-audit (2026-05-28). doctor reports *"MCP tool drift: AGENTS.md documents 13 tools, actual is 14"*.
    **Issue:** The generated `AGENTS.md` lists 13 MCP tools but 14 are registered. Unlike the won't-fix README case (#20), `AGENTS.md` IS agent-facing and HAS a `generate_agents_md()` regeneration path — so this is a real regeneration/sync gap that should never drift.
    **Expected:** `generate_agents_md()` should enumerate MCP tools from the live registry so the count can't drift; `setup-rules --refresh` (or a doctor `--fix`) should bring it back in sync.
    **Workaround:** Regenerate `AGENTS.md`.

94. [2026-05-28] [MEDIUM] Over-broad `except Exception` for "table missing" can swallow real errors silently

    **Severity:** medium
    **Command:** internal (reindex / metadata reads)
    **Context:** Self-audit (2026-05-28). Same silent-failure class as #86 / #88.
    **Issue:** `infrastructure/reindex.py:125`, `:863`, `:926` use bare `except Exception` to mean "table doesn't exist on first run" and then return `{}` / skip. As written they also swallow genuine `sqlite3` corruption, IO errors, and programming errors — silently returning empty and masking real failures behind a "first run" assumption.
    **Expected:** Catch the specific `sqlite3.OperationalError` (and verify it's a missing-table case, e.g. via `PRAGMA table_info`) so only the intended condition is handled; let all other exceptions propagate.
    **Workaround:** None.

95. [2026-05-28] [MEDIUM] Per-bundle full table scan of `code_symbols` won't scale; L2 `bundle_cache` is not on the build path

    **Severity:** medium
    **Command:** `beadloom prime` / `beadloom ctx <id>`
    **Context:** Self-audit (2026-05-28). Invisible on this repo (506 symbols); a latent scale problem for the large monorepos a "context oracle" targets.
    **Issue:** `build_context` (`context_oracle/builder.py:377`) calls `_collect_code_symbols` (`:256`), which runs `SELECT * FROM code_symbols` (`:267`) and `json.loads(row["annotations"])` per row (`:268`) on EVERY bundle build, then filters to the subgraph in Python — O(total symbols in repo) per `prime`/`ctx` call. A SQLite L2 cache exists (`context_oracle/cache.py` → `bundle_cache` table) but `build_context` does not consult it on the hot path.
    **Expected:** Filter symbols in SQL by the subgraph's ref_ids (indexed join), avoid per-row JSON parsing of non-matching rows (e.g. a `symbol_annotations(ref_id, symbol_id)` table or an indexed `ref_id` column), and/or wire `build_context` through the existing `bundle_cache`.
    **Workaround:** None needed at small scale.

---

## Improvements

> Enhancement proposals for existing features. Not bugs — current behavior works but can be better.

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

153. [2026-08-19] [HIGH] 🔴 EPIC PROPOSAL — a multi-agent flow that is actually ENFORCED: the flow Beadloom scaffolds is advisory, and advisory flows are silently skipped

    **Severity:** high (this is the product's core promise: `setup-agentic-flow` scaffolds a dev process, and the scaffolded process does not hold)
    **Command:** `beadloom setup-agentic-flow` / the scaffolded `CLAUDE.md` + `.claude/agents/*` + `.claude/commands/*`
    **Context:** Dogfood on a downstream DDD project that adopted the full scaffolded flow — role files, slash commands, spec templates, a drift gate — and ran six work items through it in one working session with an agent instructed, in the very first message, to "strictly follow CLAUDE.md and the agentic flow".

    ### The measurement (this is the whole finding)

    Six beads shipped. Counted afterwards, honestly:

    | Flow rule the scaffold declares | What enforces it | Times honoured |
    |---|---|---|
    | `review` role runs on every bead | *nothing* | **0 of 6** (and only then because a human noticed) |
    | mutation gate on touched pure cores | *nothing* | **1 of 6** — and that run was nearly vacuous (see below) |
    | BDD `.feature` for behaviour-bearing work | *nothing* | **0** |
    | read `.claude/agents/<role>.md` before acting as that role | *nothing* | **0** |
    | scaffold specs via `/task-init` | *nothing* | **0** (hand-written instead) |
    | `beadloom ctx <ref>` before touching an area | *nothing* | **0** |
    | **bead has a spec folder; roadmap has a place for open P0/P1** | **a pytest gate** | **4 of 4** — it BLOCKED the agent every time |

    The pattern is not "the agent was careless". It is exact and mechanical: **every rule with a machine caller was obeyed; every rule without one was skipped.** The one gate with teeth stopped the work four times in a session, including catching a bead whose declared type (`feature`) did not match the spec set that had been written (`BRIEF`+`ACTIVE`, the `task` set).

    ### Why prompt-delivered rules cannot carry a flow

    Not a local defect and not fixable by better wording:
    * `CLAUDE.md` is delivered as a **user message, not system configuration**, and the model judges its relevance to the task at hand — i.e. it is entitled to consider a rule inapplicable;
    * compliance degrades as instruction count grows; the downstream file had grown to **~640 lines**, of which ~100 were a (genuinely excellent) narrative section of verification lessons. Narrative and imperative compete for the same attention budget;
    * upstream tracker carries the same request: anthropics/claude-code#32163, *"Hard-enforce CLAUDE.md rules via code — rules marked CRITICAL should trigger hooks, not just prompts"*.

    The scaffold currently ships ~640 lines of process as prose and **zero** blocking hooks. Its `settings.json` template wires `SessionStart`/`PreCompact` to a context-priming command — informational only, cannot block.

    ### What the host actually offers (verified against the hooks reference)

    | Event | Can block? | Mechanism |
    |---|---|---|
    | `PreToolUse` | yes | `hookSpecificOutput.permissionDecision: "deny"` + `permissionDecisionReason`, or exit 2 |
    | `Stop` | yes — refuses to let the turn end | exit 2 |
    | `SubagentStop` | yes | exit 2 |
    | `PostToolBatch` | yes — breaks the agentic loop before the next model call | `continue: false` / exit 2 |
    | `UserPromptSubmit` | yes, + `additionalContext` injection | `decision: "reject"` |
    | `SessionStart` | **no** — `additionalContext` only | — |

    `Stop` is the decisive one, because the observed failure mode is precisely *"the agent declares the work done having skipped a role"*. `PreToolUse` on push/PR-creation is the belt-and-braces companion.

    ### Proposal — five parts, and the fifth is what makes it Beadloom's rather than a snippet

    **A. Ship blocking hooks with the flow, not just prose.** `setup-agentic-flow` emits a `Stop` hook refusing turn-end while a bead is `in_progress` without a recorded `REVIEW:` note, and a `PreToolUse` hook refusing `git push` / PR creation under the same condition. The checks read the tracker — which the flow already requires — so they need no new state.

    **B. Derive the gate from the graph, not from a hand-written list.** Beadloom already knows which files belong to which node and layer. That makes machine-checkable claims possible that a human list cannot keep current: *"this diff touched a pure domain core, so a mutation note is required"*, *"this diff changed a feature node, so its doc must have moved"*. This is the part no generic hook snippet can do — it needs the graph.

    **C. Configurable strictness, project- AND user-level.** Not every project wants review on a typo fix. The flow config (`flow.yml`) should carry the enforcement level per rule (`off` / `warn` / `block`) and per work kind (`epic`/`feature`/`bug`/`task`/`chore`), composed the same way architecture/stack overlays already compose. 🔴 See #152: there is currently **no project-level overlay at all**, so an adopter who refines a role file is punished by `config-check` — the same structural hole blocks this feature.

    **D. An honest escape hatch, modelled on what the downstream project already does.** A gate that cannot be satisfied produces an infinite loop, and a gate people bypass silently is worse than none. The pattern that works there: an exclusion must carry **a named reason and an exit condition**, recorded where the work is (`REVIEW: skipped — <reason>` in the bead), so it stays visible instead of becoming ambient. Their CI does the same for one check that cannot pass yet: the step prints a warning naming the cause *and* the condition under which it rejoins the blocking gate, and it announces itself when that condition is met.

    **E. Roles as real subagents, with the host's own review as an option.** Recent host releases make this cheap: `/code-review` runs as a **background subagent** (so it does not consume the main conversation's context) and is no longer auto-invoked, i.e. it is a deliberate step the flow can require; subagent spawn caps and nesting controls exist to keep fan-out bounded. A scaffolded flow can therefore require an *independent* reviewer rather than the same context reviewing itself — which is the structural weakness of single-agent mode: author and reviewer share the same blind spots.

    ### Two adjacent findings from the same session, worth folding into the epic

    * **A gate can exit 0 having checked nothing, and that reads as success.** The downstream mutation runner returned exit 0 with **zero mutants generated for the target module**, because its coverage-stats phase only scans one test directory and the new tests were placed elsewhere. Nothing in the output distinguished "clean" from "did not run". Any gate Beadloom ships should be required to state *what it checked* (counts), not just its verdict — the same disease as a doc-freshness "PASS" that means "no pairs exist" (#146).
    * **`sync-check` amplification.** One undocumented module produced **44 identical `[stale]` lines** for the same doc — one per member file. Actionable content: one line. See #105; raising it here because a noisy gate is a gate people learn to skim, which is how enforcement dies quietly.

    **Expected:** `setup-agentic-flow` produces a flow whose declared rules are, by construction, either enforced by a hook or explicitly marked advisory — with no third category. Today every rule is in that third category except the ones the adopter happened to write a test for.

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

76. [2026-03-10] [LOW] `beadloom init` doesn't support combined bootstrap + import mode in one step

    **Severity:** low
    **Command:** `beadloom init --bootstrap --import doc/`
    **Context:** The project has both source code in `app/` and existing documentation in `doc/` (API specs, integration guides). The user wants to bootstrap from code AND import existing docs.
    **Issue:** `--bootstrap` and `--import` are mutually exclusive on the CLI. The user must run two commands: `beadloom init --bootstrap -y` then `beadloom init --import doc/`. The `--mode both` flag exists in help but it's unclear how it interacts with `--import DIRECTORY`.
    **Expected:** `beadloom init --bootstrap --import doc/ -y` should work in a single invocation: bootstrap the graph from code, then import and classify docs from the specified directory.

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

78. [2026-03-10] [LOW] Bootstrap should auto-validate generated rules and warn on immediate violations — see also #71

    **Severity:** low
    **Command:** `beadloom init --bootstrap -y`
    **Context:** After bootstrap, user expects a clean state but `beadloom lint --strict` fails (see issue #71).
    **Issue:** Bootstrap generates `rules.yml` and `services.yml` independently. It doesn't validate that the generated rules are satisfied by the generated graph. The user discovers violations only when they manually run `lint`.
    **Expected:** At the end of bootstrap, automatically run `lint` internally. If violations are found, either:
    - (a) Auto-fix the rules to match the generated graph (preferred), or
    - (b) Print a warning: `"⚠ 2 lint violations detected in the generated graph. Run 'beadloom lint' to see details and fix .beadloom/_graph/rules.yml"`

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

89. [2026-03-11] [MEDIUM] `sync-check` reports `untracked_files` for annotated and documented files

    **Severity:** medium
    **Command:** `beadloom sync-check`
    **Context:** After adding `# beadloom:domain=` / `# beadloom:feature=` annotations to ALL 55 source files AND enriching all 18 docs with detailed content mentioning every module, `sync-check` still reports 19 of 48 pairs as stale with reason `untracked_files`.
    **Issue:** Files like `app/core/broker.py` have both:
    - Code annotation: `# beadloom:domain=core`
    - Doc mention: `docs/services/core.md` describes `broker.py` in detail
    - Doc marker: `<!-- beadloom:track=app/core/broker.py -->`
    Yet sync-check reports: `core: untracked_files - broker.py` and marks ALL other pairs in the same node as stale (6 stale entries for one untracked file).
    **Pattern:** The affected files are always the ones listed in `beadloom doctor` as "untracked source files". These are files inside the node's `source` directory that exist on disk but apparently aren't indexed as individual tracked items. The multiplier effect (1 untracked file → N stale pairs) inflates the stale count significantly.
    **Expected:** If a file has a `# beadloom:domain=X` annotation AND the doc mentions it (or has a `beadloom:track` marker), sync-check should mark it as OK, not `untracked_files`. The annotation is an explicit signal that the file belongs to node X and should be tracked.
    **Impact:** On the field-tested project, this prevents reaching 100% sync-check OK even with comprehensive annotations and documentation. Max achievable: 60% (29/48).
    **Workaround:** None. Accept the stale warnings as false positives.

90. [2026-03-11] [MEDIUM] `<!-- beadloom:track=... -->` HTML comments in docs have no effect on sync-check

    **Severity:** medium
    **Command:** `beadloom sync-check`
    **Context:** During documentation enrichment, `<!-- beadloom:track=app/core/broker.py -->` HTML comments were added to docs following the convention observed in the `beadloom prime` output hint: `"New features: add # beadloom:feature=REF_ID annotations"`. AI agents naturally extend this to docs with `<!-- beadloom:track=... -->`.
    **Issue:** These HTML comments have no effect on the sync engine. Adding `<!-- beadloom:track=app/core/external-inspection-system/constants.py -->` before a section describing `constants.py` does NOT make sync-check recognize the file as tracked. The comments are inert — they don't participate in staleness detection, freshness tracking, or coverage calculation.
    **Expected:** Either:
    - (a) Recognize `<!-- beadloom:track=<path> -->` in docs as an explicit file-to-doc binding. When present, sync-check should create a tracked pair and monitor both the doc section and the source file for changes.
    - (b) If this convention is not supported, document it clearly in `beadloom prime` / `AGENTS.md` / `docs generate` output so AI agents don't waste effort adding markers that do nothing.
    Option (a) would be a powerful feature: it creates a lightweight, explicit doc-code binding without requiring the full annotation + reindex workflow. AI agents writing docs could simply add `<!-- beadloom:track=... -->` and sync-check would start monitoring.
    **Workaround:** Do not use `<!-- beadloom:track=... -->` comments. They have no functional effect.

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

96. [2026-05-28] [MEDIUM] Test suite is volume-heavy but brittle: implementation-coupled and rarely parametrized

    **Severity:** medium
    **Context:** Self-audit (2026-05-28). Test:source ratio ≈1.9:1 (~48K test LOC / ~25K src LOC), 2576 test functions.
    **Issue:** The volume reflects breadth, not depth: only ~4 uses of `@pytest.mark.parametrize` (test bodies are copy-pasted instead of data-driven), and ~193 accesses to private attributes (`._foo`) in tests — assertions welded to current internals that will break on refactor. `test_tui.py` alone is ~5989 LOC for a low-value surface. This brittleness will make the #91 architecture refactor far more painful than necessary.
    **Expected:** Before the #91 refactor: (a) convert copy-pasted test groups to `parametrize`; (b) replace private-attribute assertions with behavior / public-API assertions; (c) reassess whether the TUI warrants ~6K LOC of tests. Treat coverage as a means, not the `fail_under=80` number as the goal.

---

## Excluded Issues

> Issues excluded from the backlog with justification. Not planned for implementation.

20. [2026-02-14] [LOW] `.beadloom/README.md` MCP tools list stale after BDL-014 — Listed 8 tools, missing `get_status` and `prime`. The file is generated once by BDL-013 but never auto-updated. Unlike AGENTS.md which has `generate_agents_md()`, README.md has no regeneration mechanism.
    > **Won't fix.** Static guide, not agent-facing. Low severity, manual update sufficient.

31. [2026-02-16] [LOW] `bd dep remove` reports success but dependency persists — Running `bd dep remove beadloom-3v0 beadloom-53o` reports success, but `bd show beadloom-3v0` still shows the dependency. Workaround: `bd update --status in_progress --claim` ignores blocks.
    > **External.** Bug in `steveyegge/beads` CLI, not in beadloom.

35. [2026-02-17] [MEDIUM] Init doesn't offer `docs generate` — doc coverage 0% after bootstrap — After `beadloom init`, user must run `beadloom docs generate` + `beadloom reindex` separately. The init flow could offer doc skeleton generation as a final step.
    > **Deferred.** Enhancement to onboarding workflow. Current workaround exists. Planned for future init improvements.

36. [2026-02-17] [LOW] Existing docs not auto-linked to graph nodes — Target project had 20 existing docs in `docs/`. All reported as "unlinked from graph" by `doctor`. No auto-discovery mechanism to match existing docs to nodes by path or content similarity.
    > **Deferred.** Requires fuzzy doc-to-node matching — a standalone feature. Deferred to Phase 14+ (semantic analysis).

37. [2026-02-17] [INFO] `beadloom init` bootstrap quality metrics — Auto-generated graph captures ~35% of real architecture (Nodes 6→17, Edges 8→49, Symbols 23→380, Doc Coverage 0%→94% after manual improvement).
    > **Tracking.** Observation, not a bug. Baseline metric for future onboarding quality improvements.

97. [2026-05-29] [LOW] `bd close --suggest-next` reports still-blocked beads as "Newly unblocked" — During BDL-035, closing `beadloom-ji9.4` printed `Newly unblocked: beadloom-ji9.6`, but `bd ready` / `bd dep tree` show ji9.6 is still BLOCKED by ji9.2/.3/.5. `--suggest-next` appears to list beads where the closed issue was *a* blocker without checking whether *other* blockers remain — a false "ready" signal. Workaround: treat `--suggest-next` as candidates only; `bd ready` is authoritative.
    > **External.** Bug in `steveyegge/beads` CLI (1.0.4), not in beadloom. Captured during dogfooding; report upstream if desired.

98. [2026-05-30] [LOW] `test_git_activity.py` date-relative flake + internally inconsistent assertions — `_SAMPLE_GIT_LOG` hardcodes Feb-2026 commit dates, so `test_maps_files_to_correct_nodes` fails once "today" is >30 days later (`commits_30d` 3→0). Same class as the `test_hot_activity` flake fixed in commit a4c88fa. While investigating, the test also looks internally inconsistent (comment references "mno345 from Jan 10" absent from the sample; `core.commits_90d==3` with only 2 core-touching commits) — needs the 30d/90d semantics clarified, not a blind date swap. Found during BDL-036 Wave 1 assembly; pre-existing, unrelated to the wave's changes. Tracked as BDL-036 BEAD-10.
    > **Internal.** Beadloom test debt. Scoped as a follow-up bead within BDL-036 (blocks the test/exit-criterion bead).

---

## Closed Issues

### Verified fixed during the 2026-08-31 tracker cleanup

Each entry below was checked against current behaviour before being closed, not
assumed from the epic that was supposed to have fixed it. Two entries from the same
sweep were checked and found STILL LIVE — #147 (`lint` mutates the index) and #160
(AsyncAPI extraction has zero callers outside its own module) — and remain open.

175. ~~[2026-08-22] [CRITICAL] 🔴 A clean-database `beadloom ci` is structurally blind to doc staleness — the rebuild adopts the current tree as its own baseline~~ **CLOSED (verified 2026-08-31)**

    **Verified fixed:** a rebuilt index no longer declares everything fresh — 363 pairs come back `unverified` without a git work tree (measured 2026-08-31).

    **Severity:** critical (the freshness gate reports PASS for work it cannot have checked, and the blindness is *caused by* the practice this project recommends for a different defect)
    **Command:** `beadloom reindex` on a fresh DB, then `beadloom sync-check` / `beadloom ci`
    **Context:** found by the S2 review bead, reproduced by the coordinator. One modified source file (`graph/linter.py`), its paired doc untouched, measured by exit code:

    ```
    incremental reindex → sync-check   exit 2   (stale — correct)
    rm beadloom.db; reindex → sync-check exit 0   (blind)
                            → beadloom ci exit 0
    ```

    **Issue:** a fresh database holds no prior baseline, so the rebuild records the current hashes *as* the baseline. Nothing is stale relative to a baseline created a second ago. `sync-check` then reports every pair fresh and the gate exits 0.
    **Why it is worse than an ordinary false green:** the blindness is produced by following this project's own advice. Standing rule CLEAN-DB LINT told every agent to lint on a clean database, because incremental reindex did not refresh import edges (#142). That workaround silently made the *freshness* leg vacuous. **A workaround for one lying check created another** — and the coordinator ran the gate that way all through BDL-061 S1 and S2, reporting the results as authoritative verification each time.
    **Pre-existing at `main`** (`7c5fa7d`), not introduced by S2 — verified by the reviewer against `main`'s own code.
    **Expected:**
    - A rebuild must not silently establish a baseline. Either it preserves the prior baseline where one exists, or `sync-check` must report "no baseline — not checked" rather than "fresh". The distinction is the same one #174 and #146 turn on: *unverifiable* is not *clean*.
    - `beadloom ci` should know whether the index it just built has a usable baseline, and say so in the sync-check line rather than printing a count that means nothing.
    - Once fixed, delete the practice too: with #142 retired in BDL-061 S2, "lint on a clean DB" is no longer needed, and leaving the habit in place keeps the hazard alive.
    **Related:** #174 (the gate passes when a declared doc is deleted), #146, #172, #173. Same theme, and this entry is the one that explains why nobody noticed the others sooner.
    > **FIXED in BDL-061 (`beadloom-mr2l.47`, one fix with #174).** The load-bearing decision was WHERE the baseline lives: `.beadloom/beadloom.db` is a derived cache — git-ignored, per-machine, dropped by every rebuild and absent on every fresh CI checkout — so a baseline kept only there is destroyed by the act that most needs it. It now lives in **git**, which is committed by construction and cannot be lost. Each pair records its baseline's provenance (`baseline_source`: `index_build` / `carried` / `attested`, carried verbatim across a reindex and never promoted); a pair whose baseline was fabricated at index-build time and would otherwise read `ok` is corroborated against `HEAD`, and where git cannot answer it reads `unverified` — reported by name, never counted as fresh, `beadloom ci` prints the step **WARN**. MEASURED on the repro: edit `graph/linter.py`, leave its doc, `rm beadloom.db`, reindex → `stale` at exit 2 (was: 0 stale at exit 0). The practice is retired with the defect: nothing in `CONTEXT.md`, the guides or any role template now asks for a clean database before checking freshness.

174. ~~[2026-08-22] [CRITICAL] 🔴 The documentation gate is defeated by deleting documentation — `beadloom ci` exits 0 with every step PASS~~ **CLOSED (verified 2026-08-31)**

    **Verified fixed:** deleting a declared SPEC now yields `[missing]` and `sync-check` rc 2; restoring it returns rc 0 (measured 2026-08-31).

    **Severity:** critical (the product's central promise — "no code reaches `main` without current docs" — is satisfiable by removing the docs)
    **Command:** `beadloom ci`, `beadloom sync-check`, `beadloom doctor`
    **Context:** found by the S2 verification bead and reproduced by the coordinator through the real CLI before filing. Delete one SPEC that the graph declares, run the gate on a clean DB:

    ```
    rm docs/domains/graph/features/rule-engine/SPEC.md
    beadloom ci
      lint         PASS: 12 rules, 0 violations
      sync-check   PASS: 269 pair(s) fresh     ← was 275
      docs-audit   PASS: 13 mention(s) fresh
      doctor       PASS: 21 check(s) clean     ← was 20
      exit 0
    ```

    **Issue:** six declared pairs vanished and the gate called the result fresh. The `doctor` check count *rose* while a file was being deleted. Nothing anywhere reported that the declared surface had shrunk.
    **Why it outranks every other false-green in this log:** the others make a check unreliable about what it examined. This one lets the thing being examined disappear. The cheapest way to pass the gate is now to delete the document rather than update it — and an agent under time pressure, a careless rebase, or a merge that drops a file all produce green.
    **It is the exact shape of the `component`-node defect (#146), one level up.** That one said "clean" means "no pairs exist" rather than "docs are fresh", for a node kind. The same equation survives for whole DOCUMENTS. A pair whose doc is gone is not fresh — it is unverifiable, and those two must not print the same word. `sync-check` calling a pair `ok` when the file is gone is the same defect from the other side.
    **Expected — the third item is the one that makes it durable:**
    - A declared doc that does not exist is a failure, not an absence; *missing* and *stale* are different facts and should read differently.
    - The declared-pair **count** is part of the contract. A run whose count fell since the last run must say so — the silent 275 → 269 was the available signal and it was discarded.
    - **Nothing may pass by having less to check.** Audit every gate step against that sentence, not only `sync-check`: `doctor` reported 21 clean while a file vanished, and its `20 check(s) clean` separately counts 9 warnings and 1 "not verified". A count that grows when the tree shrinks is not a count of anything.
    **Related:** #146 (same equation, node kind), #172 (a rule that cannot match reads clean), #173 (the audit affirms one fact thirteen times). Together these four are one theme: *a green result that describes the checker's ignorance rather than the code's health.*
    > **FIXED in BDL-061 (`beadloom-mr2l.46`, one fix with #175 — both are "unverifiable is not clean", and they diverge only in the verdict each earns).** Three parts. (1) A pair whose doc or code file is gone is `missing`, not `ok`. (2) The DECLARED surface is checked against the tree: every doc a node names in its `docs:` list is cached in the new `declared_docs` table at reindex, so a declaration outlives the file it names and `declared_doc_missing` fails the gate by NAME after a reindex has removed the pairs — `missing` and `stale` read differently, because restoring a file and updating a doc are different actions. (3) The count is part of the contract: `sync-check --record-surface` writes the committed `.beadloom/sync-surface.json`, and a later run whose declared surface FELL says so with both numbers (warning, not a verdict — the cause that matters fails on its own). `doctor`'s count was audited too: `run_checks` returns one entry per FINDING, so `len(checks)` counted problems and rose 20 → 21 while a file was being deleted; the summary now counts the CHECKS that ran, by severity, and prints *clean* only when every check is OK.

172. ~~[2026-08-22] [HIGH] 🔴 `from:` and `to:` are matched against two different vocabularies, so a `src/`-prefixed `to:` silently disables the rule — and the reference taught the broken form~~ **CLOSED (verified 2026-08-31)**

    **Verified fixed:** the shipped `forbid_import` rule matches and no rule reports itself inert (`rule_liveness` count 0, measured 2026-08-31).

    **Severity:** high (the architecture gate printed a green count computed over rules incapable of firing; a required CI check, both git hooks, and the review role all read that count)
    **Command:** `beadloom lint --strict`, `beadloom ci`
    **Context:** found during BDL-061 S2 while fixing #142/#146/#147, and reproduced end-to-end through the real CLI. Two of this project's own twelve rules — `tui-no-direct-infra`, `onboarding-no-direct-infra` — could not match anything, while `lint --strict` reported `12 rules, 0 violations`.
    **Issue:** `from:` is matched against the **repo-relative source file path as indexed** (`src/beadloom/tui/app.py`, source root included). `to:` is matched against the **dotted import path with dots replaced by slashes** (`beadloom.infrastructure.db` → `beadloom/infrastructure/db`) — no source root, no extension, because an import names a module rather than a file. A `to:` written `src/beadloom/infrastructure/**` therefore matches nothing, ever. Two engineers wrote the `src/`-prefixed form into `rules.yml` and neither noticed, because **the rules reference itself documented that form**. The defect is in the documentation as much as in the four lines of YAML.
    **A second, independent defect in the same area:** a `to:` glob covering a package did not cover a *bare import of the package*. `from pkg.infrastructure import db` is indexed with `import_path == "pkg.infrastructure"` — the target is the package, not the module — so the most common Python reach-in form was invisible. The probe injected to reproduce this issue (`from beadloom.infrastructure import db` in the TUI) fired under **no** glob form until this was fixed, which is why the first reproduction attempt wrongly concluded all four rules were dead.
    **Measured:** repairing rule 1 alone surfaces 1 violation (`tui/data_providers.py:284`); repairing rules 1 and 2 surfaces 7 (1 tui + 6 onboarding). The two `ai_agents` rules already carried the correct dotted `to:` and their zero was truthful — 11 of 221 indexed targets match them.
    **Expected, and the third part is the one that matters:**
    - State the two vocabularies in the rules reference, in one sentence, with an example of each. (Done in this fix.)
    - Make a `to:` covering a package cover a bare import of it, while leaving sibling names (`pkg/infrastructure_docs`) unmatched.
    - **Report a rule that cannot match.** A glob matching zero candidate imports across the whole graph is a `rule_liveness` warning, as is an exemption that suppresses nothing. This is the S1 guard lesson — *a check that can never fail is not a check* — applied to the linter, and it is what makes the fix permanent rather than a one-time correction.
    **Related:** #142/#146/#147 make `lint` unreliable; this made a third of it inert. Same family, higher severity.
    > Fixed in BDL-061 S2 (`beadloom-mr2l.43`).

151. ~~[2026-08-18] [HIGH] 🔴 The published release lags `main`: role templates codified in BDL-059 are unreleased, so every fresh install reports `config-check` drift against projects scaffolded from `main`~~ **CLOSED (verified 2026-08-31)**

    **Verified fixed:** `main` and PyPI both at 3.0.2, verified on the downloaded wheel 2026-08-30.

    **Severity:** high (a downstream CI gate cannot pass, and the remedy the tool steers you toward is destructive)
    **Command:** `beadloom config-check` / `config-check --fix`
    **Context:** Dogfood on a downstream project wiring the Beadloom gate into GitHub Actions. With the segfault of #150 fixed, `beadloom ci` finally executed and reported `config-check FAIL: 3 drifted artifact(s)` for `.claude/agents/dev.md`, `.claude/agents/review.md`, `.claude/commands/coordinator.md`.
    **Issue:** the drifted content is the **cohesion-driven design** section in the dev/review roles and the **autonomy/permission posture** section in the coordinator — all three codified into Beadloom's OWN shipped templates by BDL-059 (`68e53ff`, `faa83bc`, present in `main`). The published PyPI **2.1.0 does not contain them**, and the version was not bumped afterwards. So the project's files match the *newer* composition while a fresh install checks them against the *older* one.
    **Diagnostic trap worth noting** — this cost the downstream investigation a wrong first diagnosis, recorded here because the shape is general: `config-check` returned **exit 1 in a sandbox clone and exit 0 in the working repo**, with the three files byte-identical (`cmp`) and both reporting version `2.1.0`. The difference was invisible from the outside: the working repo's `beadloom` was installed **from the source checkout**, the sandbox's **from PyPI**. Two installs that self-report the same version disagreed about what the correct output is. A version string that does not distinguish "released 2.1.0" from "`main` after BDL-059, still called 2.1.0" makes environment skew undiagnosable — the same silhouette as #150, where the discriminating variable was install *date* rather than install *source*.
    **🔴 The remedy is destructive here:** `config-check --fix` would rewrite the files back to the **older** templates — measured at **42 deletions, 0 insertions** in a sandbox clone — silently deleting a standing engineering paradigm the project relies on. The remedy string (`run `beadloom setup-agentic-flow` to recompose`) reads like a safe re-sync, so the operator is steered straight at it.
    **Expected:** cut a release containing BDL-059 (and bump the version so source-installs and released installs are distinguishable); make `config-check` name the template-set version it compared against, so a drift report can be read as "your files are newer than my templates" rather than "your files are wrong"; and have `--fix` show the diff before deleting hand-authored content.
    **Workaround adopted downstream:** run the gate as `beadloom ci` **minus** `config-check` (`reindex`/`lint --strict`/`sync-check`/`docs audit`/`doctor` as blocking steps), with `config-check` kept as a separate informational step whose comment names both the cause and an explicit **exit condition** — it rejoins the blocking gate as soon as a release containing BDL-059 exists.

146. ~~[2026-08-03] [HIGH] `component` nodes are absent from `sync-check` pairs entirely — their docs are NEVER checked for staleness, and the green result reads as "docs fresh" when it means "nothing was looked at"~~ **CLOSED (verified 2026-08-31)**

    **Verified fixed:** 43 of 367 sync-check pairs are component documents (measured 2026-08-31).

    **Severity:** high (false-green on a freshness gate; same class as #142 — the gate reports success for a check it never performed)
    **Command:** `beadloom sync-check` / `beadloom ci`
    **Context:** Dogfood on a downstream DDD project. A slice landed a new capability inside a `kind: component` node whose `services.yml` entry declares `docs:` and whose SPEC carries `<!-- beadloom:track= -->` markers. The dev wave reported "sync-check by node `<component>` — clean" and the coordinator accepted it. A later tech-writer wave discovered the node is not in the sync set **at all**: `sync-check --json` returns pairs for every `kind: feature` node plus the top `service`, and for **none** of the four `kind: component` nodes in the graph. "Clean" meant "zero pairs exist", not "docs match code".
    **Issue:** Pair construction appears to be keyed on node kind (feature/service) rather than on "node declares `docs:`". A component's docs can therefore rot indefinitely with a permanently green gate — and, worse, the operator/agent is actively misled, because the same command prints an OK line for feature nodes right next to the silent gap. There is no "N nodes declare docs but contribute no pairs" warning anywhere in `sync-check`, `doctor`, or `ci`.
    **Expected:** Build sync pairs for ANY node that declares `docs:` (kind-independent), or — if components are deliberately out of scope — say so explicitly in the output (`skipped: 4 component nodes`) and flag it in `doctor`. A freshness gate must never return green for files it did not examine.
    **Workaround:** Verify component docs by reading the code; do not trust `sync-check` for them. Detect the gap with `sync-check --json` and compare the set of `ref_id`s against the nodes that declare `docs:` in `services.yml`.
    > **Fixed in BDL-061 S2 (`beadloom-mr2l.5`), verified in `.6` and `.7`.** Pairing was never keyed on node kind — it read annotations only, which is why the kinds whose sources carry no `# beadloom:` comment looked exempt. `build_sync_state` now falls back to the files a node's `source:` OWNS when annotations yield none, `check_sync` no longer short-circuits on an empty `sync_state`, and `find_unchecked_doc_nodes` NAMES every node that still contributes no pair, with a reason (`no_indexed_code`, `files_owned_by_nested_nodes`, `no_source`) — advisory, never changing the exit code. Measured on this repository: 272 → 275 pairs, all 22 `component` nodes covered, 4 nodes named as not-checked where the gate previously printed nothing.
    > **Residue:** one of those reasons names the wrong cause. `graph-reads` is reported `no_indexed_code` for a file that IS indexed; what is absent is ANNOTATED symbols, because the module's annotations sit inside its docstring, which `extract_symbols` does not read. Bead `beadloom-mr2l.50`.

135. ~~[2026-06-18] [HIGH] `beadloom init` crashes with `UnicodeDecodeError` on a repo containing binary assets / a stray virtualenv~~ **CLOSED (verified 2026-08-31)**

    **Verified fixed:** 14 `UnicodeDecodeError` handlers in `onboarding/`; the ambient-decode work of BDL-061 covers this path.

    **Severity:** high (hard crash — "broken out of the box" on any repo with binary assets or a stray venv)
    **Command:** `beadloom init -y`
    **Context:** Dogfood on an adopter repo that contains a large binary-asset directory (image/model files — PNG, `.safetensors`, ~2 GB) with a stray virtualenv left inside it (`<assets>/tools/.venv*`).
    **Issue:** Auto-detect added the binary-asset directory to `scan_paths` (alongside `src`) because it found a few `.py` files under it (including inside the stray venv). The reindex code-indexer then called `file_path.read_text(encoding="utf-8")` on a non-UTF-8/binary file and raised `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xa4 in position 64` → full traceback, and `init` aborted half-done (`.beadloom/` was created, but the reindex step crashed). Call chain: `application/reindex/full.py:149` → `application/reindex/indexing.py:122` `_index_code_files` → `context_oracle/code_indexer.py:373` `extract_symbols` (`read_text(encoding="utf-8")` with no guard).
    **Expected:** (a) the indexer must **skip non-UTF-8/binary files gracefully** (try/except → warn + skip; never abort the whole `init` over one file); (b) auto-detect should exclude virtualenvs (`.venv*`, `site-packages`) and binary-asset directories from `scan_paths`; (c) support `exclude_paths` (overlaps the existing `exclude_paths` improvement request). A single binary file must never abort `init`.
    **Workaround:** manually narrow `.beadloom/config.yml` `scan_paths` to source-only, delete the stray venv(s), then `beadloom reindex`.

91. ~~[2026-05-28] [CRITICAL] Beadloom violates its own architecture rules; `lint --strict` is configured to pass anyway~~ **CLOSED (verified 2026-08-31)**

    **Verified fixed:** `lint --strict` exits 1 on a real violation — exercised repeatedly during BDL-062, most recently by `doc_area_coherence` finding four nodes.

    **Severity:** critical
    **Command:** `beadloom lint --strict` (exits 0) vs. actual graph state
    **Context:** Self-audit during the comprehensive architecture/code review (2026-05-28). The product's core value proposition is enforcing architecture boundaries and catching dependency cycles.
    **Issue:** `beadloom lint --strict` exits **0** on Beadloom itself despite **12 real violations** (verified live). Two compounding problems:
    - (1) **The coupling is real.** `infrastructure` is a god-package: `infrastructure/reindex.py` (~1296 LOC) orchestrates every domain and imports them at module level (`infrastructure/reindex.py:14-16` → `context_oracle`, `doc_sync`, `graph`). Meanwhile `graph/linter.py:98` and `graph/import_resolver.py:820,882` import back into `infrastructure.reindex`, creating cycles. The cycle is openly acknowledged in a code comment (`graph/linter.py:95-96`: *"Lazy import to avoid circular dependency…"*) and worked around with function-local lazy imports instead of being fixed. Per the layer rule, `infrastructure` sits BELOW domains yet imports all of them.
    - (2) **The alarm is silenced.** In `.beadloom/_graph/rules.yml`, `no-dependency-cycles` (line 39) and `architecture-layers` (line 45) are set `severity: warn`. `--strict` only fails on `error`-severity, so a graph full of cycles passes green.
    **Expected:** A tool that sells architecture enforcement must pass its own enforcement. (a) Break the `infrastructure` god-package — extract reindex orchestration into a `services`-layer module, or invert the dependency so `infrastructure` stops importing domains; (b) restore `no-dependency-cycles`/`architecture-layers` to `severity: error`. Until then this is a credibility hole reproducible by any skeptic in two commands.
    **Workaround:** None — structural issue, not a usage issue.

92. ~~[2026-05-28] [HIGH] `doctor` reports false "Version drift" on Beadloom itself (reads stale `importlib.metadata`, not `__version__`)~~ **CLOSED (verified 2026-08-31)**

    **Verified fixed:** `doctor` reports version drift 0 times on this repository (measured 2026-08-31).

    **Severity:** high
    **Command:** `beadloom doctor`
    **Context:** Self-audit (2026-05-28). Distinct from #73 (which is about doctor reading the user-authored `.claude/CLAUDE.md` on an *external* project). This is about doctor's notion of the "actual" version being wrong even on Beadloom's own repo.
    **Issue:** `doctor` reports *"Version drift: CLAUDE.md claims 1.9.0, actual is 1.7.0"* while `src/beadloom/__init__.py:3` is `__version__ = "1.9.0"` and `status` shows 1.9.0. Root cause: `_get_actual_version()` (`infrastructure/doctor.py:274-281`) returns `importlib.metadata.version("beadloom")` first — stale editable-install metadata — and only falls back to source `__version__` on `PackageNotFoundError`. A diagnostic that confidently emits a wrong diagnosis erodes trust in all of doctor's output.
    **Expected:** Treat the in-tree `__version__` as the source of truth for "actual version" (or compare directly against it). Installed-package metadata must not override the source version.
    **Workaround:** Reinstall the package to refresh metadata; ignore the warning.



### Residue closed by BDL-061 / BDL-062 (moved 2026-08-31)

Entries that were already struck through in Open Issues while still sitting in that
section. Moved verbatim, nothing rewritten — a third of the "open" list was not open.

211. ~~[2026-08-27] [HIGH] The 1.x description was fixed in two copies of four, and `beadloom --help` still shows the old one~~ **CLOSED (BDL-062 `.15`, released in 3.0.2)**

    **Severity:** high (`beadloom --help` is the sentence every CLI user reads first, and 3.0.1 was released specifically to replace this sentence)
    **Command:** `beadloom --help`
    **Context:** found by `beadloom-viaj.8` verifying the PUBLISHED 3.0.1 wheel in a fresh virtual environment — the check that was the reason for the release.

    **Measured on the published artifact**, not the local build:

    ```
    importlib.metadata.metadata('beadloom')['Summary']
      -> The architecture graph of your codebase, and the gate that holds ...   CORRECT
    beadloom --help, line 3
      -> Beadloom - Context Oracle + Doc Sync Engine.                           THE 1.x SENTENCE
    ```

    **Four copies of the product's one-line description exist. `.4` found two.**

    | Copy | State after 3.0.1 | Who reads it |
    |---|---|---|
    | `pyproject.toml` `description` | corrected | the PyPI project page |
    | `beadloom/__init__.py` docstring | corrected | `help(beadloom)` |
    | `services/commands/_root.py:44` | **still 1.x** | `beadloom --help` |
    | `onboarding/templates/docs/core/beadloom-readme.md.txt:9` | **still 1.x** | every project scaffolded by `beadloom init` |

    **The check that exists could not have caught it, and its own docstring predicted why.**
    `tests/test_package_description.py` asserts that the manifest and the package docstring
    AGREE, and states plainly that agreement is checkable while currency is not — "both copies
    were in perfect agreement while both were three majors out of date". The residual it did not
    name is the one that bit: **agreement over a subset of the copies.** Two were corrected
    together, the test compared exactly those two, and it went green over a product whose most
    visible surface still said the retired sentence.

    Worse for an adopter than for us: the fourth copy is a **template**, so every project
    `beadloom init` scaffolds from 3.0.1 onward is seeded with the 1.x sentence in its own
    documentation.

    **Expected:** the description has one home and the others are derived from it, or the check
    enumerates every copy rather than the two it was written against. `_root.py`'s Click group
    docstring cannot import the manifest cheaply, but it can read `beadloom.__doc__`, which is
    already one of the checked copies.

    **CLOSED in 3.0.2** (`beadloom-viaj.15`), and the closing measurement is on the PUBLISHED
    artifact rather than the local build, because that distinction is what this issue is about.
    Fresh virtual environment, `beadloom==3.0.2` installed from PyPI:

    ```
    beadloom --version           -> beadloom, version 3.0.2
    beadloom --help, line 3      -> Beadloom - the architecture graph of your codebase, ...  CORRECT
    importlib.metadata Summary   -> The architecture graph of your codebase, ...             CORRECT
    grep 'Context Oracle + Doc Sync Engine' over the installed package (269 files) -> 0 hits
    ```

    **The count in this entry was wrong, and that is the finding rather than a correction.** It said
    FOUR copies. Sweeping 372 files found **five**: the fifth is this repository's own
    `.beadloom/README.md`, which `init` had scaffolded from the same template. An issue about a
    check that read a smaller population than the fact had was itself written from a population
    somebody had listed by hand.

    **Three copies were removed rather than corrected**, which is why this is not a typo fix.
    `_root.py` derives `help=` from the package docstring; the scaffold template takes
    `{{beadloom_description}}` and `{{mcp_tool_list}}`, filled by `beadloom_readme_values()` from
    the package docstring and `MCP_TOOL_CATALOG`; and `.beadloom/README.md` is generator output.
    Two literal copies remain — the manifest and the package docstring — which the pre-existing
    agreement test already holds together.

    **Reading the scaffold end to end**, which nobody had done this cycle, found three more items of
    the same class: it named **8 of the 18** MCP tools as though that were the list (and states no
    number, so `mcp_tool_count` could never have bound to it), `Directory Contents` omitted
    `AGENTS.md`, and `Essential Commands` omitted `prime` and `ci`. Verified on the published wheel
    by scaffolding a project with it: all 18 tools, `AGENTS.md` present, both commands present.

    **What is still NOT checked, measured rather than asserted.** Setting the manifest and the
    package docstring to `A cloud-hosted spreadsheet for tracking invoices` and regenerating the
    scaffold leaves all 7 checks green. Currency has no test and this issue did not give it one. The
    check now guards a banned phrase, agreement across every copy the sweep finds, and the SIZE of
    the population — and that last is what closes the class, because a sixth copy stating the
    correct sentence turns the suite red until somebody records it.

    **What an adopter still has to do.** `.beadloom/README.md` is written once and never
    overwritten, so a project scaffolded on 3.0.0 or 3.0.1 keeps the 1.x sentence and the 8-tool
    list until that file is deleted and regenerated. Named in the 3.0.2 CHANGELOG under Upgrading.

195. ~~[2026-08-26] [HIGH] One node whose source lies outside the common source root collapses `doc-area-coherence` for the whole graph~~ **CLOSED (BDL-062 `.9`)**

    **Severity:** high (a rule the project declared blocking could stand down over its entire population while the Gate stayed green)
    **Command:** `beadloom lint --strict`
    **Context:** opened by BDL-062 `.4` while deciding whether the `vitepress-site` node should carry a document; **rewritten after the coordinator failed to reproduce it and both measurements were compared.**

    **The trigger.** `doc_area._placements` derived the source root as the longest directory prefix EVERY node/doc pair's source shares. That is a unanimity rule, and unanimity hands each individual source a veto. `vitepress-site`'s source is `site/`, which shares no prefix with `src/beadloom/...`, so attaching any document to it dropped the root from `src/beadloom` to nothing in one step — for all 85 other pairs. `min_support` guarded the dominant-mapping half; nothing guarded the prefix.

    **Two faces, and which one you see depends only on where the minority node's document sits.** Measured on the same tree, same commit, by two people who then disagreed:

    ```
    doc at site/vitepress-site/DOC.md   -> the doc path carries the outlier's own
                                           segment, an area depth is still found, a
                                           bogus convention is derived:
                                           84 compared, 7 nodes reported WRONG at error
                                           (bd-seam, beadloom, cli, cli-commands,
                                            guard-probes, mcp-server, tui)

    doc at guides/vitepress-site.md     -> no doc path carries any segment of the
                                           collapsed vocabulary, no area depth exists:
                                           0 compared, 86 unnamed,
                                           rule reports it CHECKED NOTHING
    ```

    **The second face is the worse one and it is why this was HIGH.** That report went out through `liveness_finding`, which hardcoded `severity="warn"` whatever the rule declared. This repository escalates `doc-area-coherence` to `error`; the escalation evaporated at exactly the moment the rule stopped working, and `lint --strict` exited 0 over a check that had run on nothing. Filtering `lint --format json` by `rule_type == doc_area_coherence` cannot see it either, because the stand-down carries `rule_type: rule_liveness` — filter by `rule_name` instead.

    **STRUCK — the evidence line in the original filing was false.** It read *"4 true findings become 6 false ones"*. There were no 4. The `services.yml` backup taken immediately before the probe shows the four misfiled nodes were **already corrected**, so the measured baseline was **0 doc-area findings**, and the 6 were manufactured from a clean graph. The original compared against `.2`'s pre-correction baseline rather than the one actually measured — a green count that was not a checked count, inside the issue filed about green counts that are not checked counts. Recorded rather than quietly replaced, because the wrong number was acted on.

    **Not exotic:** any project with a `site/`, `scripts/`, `tooling/` or a second package root meets this on first contact.

    > **CLOSED — the root tolerates a minority, and a total stand-down is no longer silent.**
    >
    > `_source_root` replaces `_common_prefix`. It descends one segment while there is **exactly one supported way down**, where supported means `min_support` sources agree on the next segment — the dial the dominant-mapping half already declares, not a second threshold. A genuine fork ends the descent (that is where the areas begin); no supported segment at all ends it too; and a source too short to have that depth is `rootless` rather than a veto. Measured on this repository, both faces now give the identical answer: **derivable, 8 dominant areas, 0 contradicting, `outside_root` 1**, against a baseline of the same 8 areas and `outside_root` 0. A pair outside the root is excluded from comparison and **counted** — `Convention.population()` ends `"; N sit outside the source root"`, and `examined` adds up to the pairs the graph offered.
    >
    > `liveness_finding` gained a keyword-only `severity`, defaulting to `warn` so every existing caller is byte-identical. A **total** stand-down passes the rule's declared severity; a **partial** inertness stays advisory. The distinction is the point: a dead glob beside nine live ones is a configuration smell, while a rule that checked none of its population is indistinguishable from a rule that never ran. This costs an adopter nothing — the rule ships `warn`, so a small graph still reports `warn` and no first `beadloom ci` goes red.
    >
    > `tests/test_source_root_minority.py::TestATotalStandDownCarriesTheDeclaredSeverity::test_the_gate_cannot_pass_while_the_rule_checked_nothing` runs the real linter and fails if a blocking rule stands down without `has_errors` being set. Both document paths are kept as permanent fixtures in `TestBothFacesOfTheCollapse`: one cause, two observables, and nothing but the doc path varies between them.
    >
    > **Residual, deliberately not fixed here and worth its own decision (#197):** `summary_facts` and `scenario_coverage` report their own total stand-down through the same seam and still hardcode `warn`. Only `doc_area_coherence` was measured, and escalating five rule types on one bead's evidence would be shipping four untested changes.

189. ~~[2026-08-23] [MEDIUM] `beadloom sync-update <doc> --check` WRITES — a check flag that re-baselines the thing it was asked to report on~~ **CLOSED (BDL-061 S3b, `.58`)**

    **Severity:** medium (it silences the warning it was asked to describe, and it is the defect class this epic exists to remove)
    **Command:** `beadloom sync-update <doc-path> --check`
    **Measured** on this repository while inspecting surface drift before deciding whether to re-attest. `beadloom sync-update docs/services/cli.md --check` printed `Re-baselined reference doc docs/services/cli.md.` and the following `sync-check --json` reported **6** surface-drift references where the previous run reported **7**. The flag asked for a report and got a write.
    **Cause:** `services/commands/docsync.py` — in the non-`--yes` path the reference-doc branch (`mark_reference_synced`) is reached at line ~983, *before* the `if check_only:` guard at line ~994. `--check` is therefore honoured only when the argument resolves to symbol pairs; when it resolves to a reference doc's path, the branch that handles it never sees the flag.
    **Why it matters beyond the one file:** a reviewer or an agent inspecting drift with `--check` — the flag whose whole contract is "tell me, do not change anything" — destroys the evidence it was inspecting, and the next `sync-check` reads clean for a reason nobody recorded. That is BDL-UX #147 (`lint` mutating the index) in a different command, and #163 (re-attesting can silence the check without evidence) reached by accident rather than by choice.
    **Expected:** move the `check_only` guard above the reference-doc branch, and have `--check` on a reference doc print its `watches` set and its drift status instead of re-baselining it.
    **Related:** #147 (a check that writes what it checks), #163 (re-attestation without evidence), BDL-057 (the reference surface).

    > **CLOSED — the guard runs first, and the answer is read-only.** `check_only` is now honoured above the reference-doc branch, and `doc_sync.engine.describe_reference_doc()` answers it: one `SELECT`, one recomputed aggregate hash, no `UPDATE`, no `commit`. `beadloom sync-update <doc> --check` prints `  [surface drift] <doc> watches cli, graph` and the `reference_state` row is byte-identical afterwards (asserted on `(doc_path, aggregate_hash, status)` before and after, not on the absence of the word "Re-baselined"). The non-`--check` path still re-baselines — asserted too, so the guard cannot silently disable the command it guards.
    > Checked while there, since the entry raised the class rather than the line: `check_sync()` contains zero `UPDATE`/`INSERT`/`commit` in its own body, so `--check` on a SYMBOL pair was already clean. Stated as a measured result rather than left as an absence.

188. ~~[2026-08-23] [HIGH] The orphan report and the migration guidance are computed on every scaffold and printed by nothing — NO CALLER, NO CAPABILITY~~ **CLOSED (BDL-061 S3b, `.58`)**

    **Severity:** high (two shipped criteria are met by the library and not by the command anybody runs)
    **Command:** `beadloom setup-agentic-flow`
    **Measured** on a temp project carrying a pre-BDL-048 layout (`.claude/commands/{dev,test,review,tech-writer,epic-init}.md`) and a hand-edited `.claude/commands/coordinator.md`. `orphaned_flow_files()` returns five entries, each naming the file, where the role now lives, and the exact `rm -f` command. `ScaffoldResult.migration_notes` returns the note naming `.beadloom/flow/commands/coordinator.md` as the place the edit belongs. The command's own output loop covers only `commands_written`, `commands_skipped` and `claude_md`, so **neither list reaches stdout**. `grep -rn 'orphans\|migration_notes\|orphaned_flow_files' src/` finds no reader anywhere outside `agentic_flow_setup.py` itself.
    **What the user sees instead:** `Skipped .claude/commands/coordinator.md (hand-edited; use --force)` — which advises the destructive flag and never mentions the project layer, the one place the edit could safely go.
    **Why it matters:** BDL-UX #137 is recorded as closed by the orphan report, and BDL-061 S3's criterion "a hand-edited vendored file is reported with migration guidance" is recorded as met. Both claims are true of `scaffold()` and false of `beadloom setup-agentic-flow`. This is CONTEXT's own standing rule NO CALLER, NO CAPABILITY: a function nothing calls reads as "the feature exists".
    **Expected:** print the orphan list (with its `rm -f` commands) and the migration notes after the write summary, the way `hooks.guards_registered` and `ignore.added` are printed.
    **Related:** #137 (the orphan report), #151 (the destructive `--fix` this guidance replaced), #186.

    > **CLOSED — `_echo_scaffold_findings()` is the caller.** `migration_notes` prints under *"Left alone (N) — your edits are the only copy of an intent"* with the `.beadloom/flow/<kind>/<name>.md` path, and `orphans` under *"Left by an older flow layout (N) — reported, never deleted"* with each `rm -f`. **`(hand-edited; use --force)` is gone** — the line advised the destructive flag and named nowhere safe, which was the actual harm; the migration note replaces it. Both assertions bite: removing the call takes both tests from passed to FAILED (measured).
    > `ScaffoldResult.flow_config_written` was added in the same pass and printed the same way, so the file every composed artifact is built from is named on the run that creates it (#187).

187. ~~[2026-08-23] [MEDIUM] A virgin `setup-agentic-flow` leaves `config-check` red — four errors on a repository nobody has touched~~ **CLOSED (BDL-061 S3b, `.58`)**

    **Severity:** medium (it is a first-contact experience, and it is the exact "green project goes red" shape the slice is built to avoid)
    **Command:** `beadloom setup-agentic-flow` then `beadloom config-check`
    **Measured** on a fresh TypeScript project (`package.json`, one `.ts` file, `beadloom init --yes --mode bootstrap`, then `setup-agentic-flow` with no flags). `config-check` exits **1** with four errors, one per role adapter: *"scaffolded agentic-flow file drifted from the shipped template … this repo has no .beadloom/flow.yml, so the role files are the plain vendored scaffold"*. Writing a three-key `.beadloom/flow.yml` and re-running gives `Agent-config in sync — no blocking drift`, rc **0**.
    **Cause:** `setup-agentic-flow` resolves the config through `resolve_flow_config` (auto-detecting `stack: typescript`) and composes the role adapters from it, but never **writes** a `flow.yml`. `config-check` without one takes the no-flow.yml branch and expects the plain vendored role files, which the composed ones are not.
    **Why it is not cosmetic:** the command's own closing advice is *"1) `beadloom config-check` keeps the scaffolded flow + CLAUDE.md auto-regions honest"*. Following it immediately produces four errors on an untouched repository, with a remediation that tells the reader to add a `flow.yml` — which is the right answer, arrived at through a failure.
    **Expected:** either persist the resolved selection as `.beadloom/flow.yml` on scaffold (it is the file the whole feature is configured by, and the command already knows every value), or have `config-check` compare against the same resolution the scaffold used. The first is the smaller change and makes the configuration visible.
    **Related:** #184 (the same command family answering an expected state with a failure shape), #186.

    > **CLOSED by the first of the two options — the selection is written down.** `flow_config.persist_flow_config()` writes the resolved config to `.beadloom/flow.yml` on a first scaffold and **never** over an existing one (that file is the adopter's policy — `language` and `overlays.suppress` have no flag and live only there). Measured end to end on a fresh TypeScript project: `init` → `setup-agentic-flow` → `config-check` **rc 0**, where it was rc 1 with four errors. The command names the file it wrote.
    > **A second defect fell out of the fix and is worth more than the first.** `scaffold()` re-resolved the config from disk with `resolve_flow_config(project_root)` — **ignoring the CLI flags** — while the command resolved its own for `generate_adapters`. So `beadloom setup-agentic-flow --architecture fsd` composed the four ROLE adapters as `fsd` and the slash commands and `CLAUDE.md` as `ddd`, in one run, silently. The caller's resolved config is now threaded in (`scaffold(config=…)`) and a test asserts the flag reaches both.

186. ~~[2026-08-23] [HIGH] 🔴 `config-check --fix` deletes a hand edit in a role adapter — one line after the check printed "It will NOT be rewritten"~~ **CLOSED (BDL-061 S3, `.59`)**

    **Severity:** high (it destroys unrecoverable user text, and it does so by following the command's own printed advice)
    **Command:** `beadloom config-check` then `beadloom config-check --fix`
    **Measured** by sha256 in a clean temp repository (`init` → `flow.yml` → `setup-agentic-flow`, then a four-line append to `.claude/agents/dev.md`):

        scaffolded  999889b630259ffc5a46380f333c27f10603d6e640d30f63cf11cd8a41e5e748
        edited      27a6ffbc81d249ac928001db2f6f3fd577f2792388b12c52eb3af585f521e7af
        after --fix 999889b630259ffc5a46380f333c27f10603d6e640d30f63cf11cd8a41e5e748

    **The contradiction is inside one command's output.** `config-check` reports: *"hand-edited: the body differs from the composition AND from what Beadloom last wrote. It will NOT be rewritten → move the additions to .beadloom/flow/roles/dev.md"*, and then closes with the generic *"Run `beadloom setup-rules --refresh` (or `config-check --fix`) to fix."* Doing what the last line says undoes what the line above promised.
    **Cause:** `config_sync.refresh_composed_adapters` calls `generate_adapters` unconditionally. Its sibling `refresh_agentic_flow_files` was deliberately made non-forcing for the slash commands and `CLAUDE.md` (BDL-UX #151); the role-adapter path did not get the same treatment, and BDL-061 `.10`/`.11` measured the fixed path rather than this one.
    **Why it is the sharpest of the three:** every other finding in this family is a message that is missing or wrong. This one is data loss, in the exact scenario BDL-UX #139 and #152 exist to end — a team putting its standing engineering practice in a role file.
    **Expected:** `refresh_composed_adapters` must skip an adapter whose flow-manifest state is `hand_edited` (leaving the finding standing), and the generic remediation line must not name `--fix` when the findings include a hand edit.
    **Related:** #151 (the destructive `--fix` this was supposed to have ended), #139, #152, #188.

    > **CLOSED by option (a) — `--fix` honours the sentence.** `refresh_composed_adapters` classifies each adapter first and hands the unowned ones to `generate_adapters(preserve=…)`, which neither writes **nor records** them (recording a digest we did not write would make the next run believe the edit was ours). Re-measured on a clean temp repository: scaffolded `77dfc84f…` → edited `26a0da67…` → **after `--fix` `26a0da67…`**, exit 1, the file named under *Declined to rewrite*. Option (b) — qualifying the sentence — was rejected: it is cheaper and honest, and it leaves a documented data-loss path in a command whose name promises repair.
    > Three things beyond the one file. (1) **`unverified` is declined too**, not just `hand_edited`: it is a `warn`, so overwriting one would have destroyed content and then printed "no blocking drift" at exit 0 with no red anywhere. The rule is one phrase — *`--fix` rewrites only what Beadloom can prove it wrote.* (2) **The run says what it did**: `apply_config_fixes` digests the artifact surface before and after the writers and names every file created or rewritten, with the count on the summary line — measured against the disk rather than trusting the writers, several of which over-report. (3) **The closing advice stops offering `--fix`** for a finding it will decline (`ConfigDrift.fixable`).
    > One pre-existing misclassification had to go first, measured not argued: on a repo scaffolded **before** adopting a `flow.yml`, all four `.claude/agents/*` read `hand_edited` (`_scaffold_vendored` writes those bytes and never records a digest). Declining them would have made `--fix` refuse for ever to recompose files Beadloom itself wrote. The vendored body is now an `alternate`, so it reads `stale` and recomposes — **unowned is not the same as somebody's only copy**.

183. ~~[2026-08-23] [HIGH] 🔴 Every adopter's `CLAUDE.md` states **Beadloom's** version as the project's own — and it reads as correct on the one repo where it is~~ **CLOSED (BDL-061 S3b, `.58`)**

    **Severity:** high (a false fact written into the file an agent treats as authoritative, in a section describing the adopter's project)
    **Command:** `beadloom setup-agentic-flow`, `beadloom init`
    **Context:** found by review `.11` and reproduced by the coordinator. `onboarding/scanner/claude_md.py:125` calls `application.doctor.get_actual_version()`, which returns **`beadloom.__version__`** — Beadloom's own version, correctly and deliberately so, since it exists to diagnose Beadloom's version drift (#92). That value is then rendered into the composed `CLAUDE.md` as `- **Current version:** …` inside the section describing *the adopter's project*. A JavaScript project at `0.4.1` gets `Current version: 2.2.0`.
    **Why it survived:** on this repository the fact is *true by coincidence* — we are Beadloom, so our project version and Beadloom's version are the same string. Every check, every review and every dogfood run has read a correct line. The defect is only visible from a project that is not Beadloom, and we have never rendered one.
    **This is the class BDL-UX #177 named, still open after #177's mechanism was fixed.** #177 was about our project-local *text* reaching adopters through a test that rewrote the shipped template; that leg is closed and now structurally prevented. This is our project-local *facts* reaching adopters through composition, and nothing prevents it. Closing #177 on the strength of the first leg was premature — the coordinator did that, and this entry is the correction.
    **Expected:**
    - Read the adopter's version from the adopter's project (`pyproject.toml`, `package.json`, `Cargo.toml`, a VCS tag), and render nothing rather than something false when it cannot be determined — *unknown is not zero*, the rule this epic has applied to every other reading.
    - Audit the whole composed output the same way, not just this line: **which other rendered facts are computed about Beadloom rather than about the project?** One was found by reading; nobody has swept the rest.
    - A test that renders `CLAUDE.md` for a **non-Beadloom** fixture project would have caught this and would catch the next one. There is no such fixture today, which is why a correct-looking line survived four slices of scrutiny.
    **Related:** #177 (same class, different mechanism), #92 (why `get_actual_version` is right about Beadloom), #139/#152.

    > **CLOSED — and the one-line fix was the least of it.** The deliverable is `tests/adopter_project.py`: five projects that are **not** Beadloom (TypeScript `0.4.1`, Rust `1.2.3`, Python `3.7.0`, Poetry `0.9.2`, and one declaring no version at all), rendered in `tests/test_adopter_projects.py`. Without a fixture the tool cannot be accidentally right about, the next instance survives exactly as this one did. Mutation-checked: restoring `get_actual_version()` and the hardcoded `DDD packages` takes 15 of 16 tests from passed to FAILED.
    > **THE SWEEP, stated with what was checked and not only with what was found.** Checked: the composed `CLAUDE.md`, all four composed slash commands, all four composed role adapters, both auto-regions, and every `doctor` check that reads an adopter's `CLAUDE.md`. **The four role adapters are CLEAN** — a checked result, not an absence. Found, beyond the version line:
    > - `- **Architecture:** DDD packages` was a **constant**. An `fsd` project was told it was DDD. It now follows the declared architecture and claims no methodology when none is declared.
    > - The `Stack` bullet matched the target's manifest against **Beadloom's own dependency names** (`sqlite`, `click`, `rich`, `tree-sitter`) and printed `Python 3.10+` — *our* floor — for a project on `>=3.12`. It now names the project's declared stack, its `requires-python` verbatim, and its own first six declared dependencies.
    > - `_get_actual_packages()` fell back to scanning `<adopter>/src/beadloom/` — our layout, looked for inside their tree. Deleted; `detect_source_packages()` scans theirs.
    > - The shipped `CLAUDE.md` template **seeded** the auto-region with our stack, our nine DDD packages and `Current version: 2.2.0` — the bytes an adopter holds until the first refresh. Now a neutral one-line placeholder.
    > - Our identifiers still shipped in the composed text: `BDL-037` and `BDL-UX-Issues #97` in the core, `BDL-036` twice and our issue-log filename three times in the coordinator command. That is #177's third "Expected" item, which its closure claimed and its check never covered.
    > **The biggest catch was not the renderer.** `application/doctor.py::_check_agent_instructions` **audits four claims in the adopter's `CLAUDE.md` against BEADLOOM's state**: version vs `get_actual_version()`, packages vs a scan for `src/beadloom/`, stack vs the literal `{python, sqlite}`, test framework vs the literal `pytest`. All four read OK here by the same coincidence. Fixing only the renderer would have turned **every adopter's `doctor` red on upgrade** (their correct `0.4.1` against our `2.2.0`) — the precise constraint this epic is built on, reached from the other side. Each check now reads the project, and a fact the project does not declare is `INFO … not verified`, never a drift verdict.
    > `get_actual_version()` is **unchanged**: it is right about Beadloom (#92) and the defect was always its caller.
    > **The general half, so the class does not need re-finding:** `beadloom_local_facts_in(text)` is a deny-list of this repository's own identifiers — our epic key, our issue numbers, our issue-log filename, bead ids, `src/beadloom`, our `__version__`, our package names — asserted over every composed artifact, and it names the offender it found rather than failing bare.

182. ~~[2026-08-23] [HIGH] 🔴 `symbols_changed` is computed per node, so one changed file marks every pair of that node stale — and the only way through is bulk re-attestation~~ **CLOSED (BDL-061 S6, `beadloom-mr2l.78`)** — `sync_state` gained `file_symbols_hash`, the symbol surface of a pair's OWN code file, beside the per-node `symbols_hash`. Only the file-level fact can make a pair `stale`; a pair whose sibling moved is `unverified` with the reason `sibling_symbols_changed` and NAMES the file that moved, and `sync-update` is not offered for it. *Stale, unverified and ok are three states*, and the epic's existing vocabulary supplies the second one — no fifth word was invented (#174/#175 `missing`/`unverified`, `.76` `excused`, `.77` `null`). Measured in two clean rooms off `e255a21` differing only in this change: appending one function to `application/architecture_view.py` produced **69 stale pairs, 67 naming a file nobody touched**; the same perturbation now produces **2 stale and 67 `unverified/sibling_symbols_changed`**, each carrying `details: architecture_view.py`. Both exit 2 — the gate still bites, on the pairs somebody can act on. A row with an empty `file_symbols_hash` keeps the node-level answer, and the file fact carries the same provenance as the node fact or is not written, so an existing index sees NO change on the reindex that adds the column and moves to file granularity at its first attestation.

    **This defect was filed three times** — #105 (2026-06-01), #133 (2026-06-15) and #182 (2026-08-23) — over eleven weeks, each time from a fresh measurement and each time without the earlier one being found. Three reports of one root is itself the finding: the log is searched by symptom (`symbols_changed`, `worktree`, `re-baseline`) and the three symptoms share no word.

    **Severity:** high (it manufactures the exact situation #163 warns about, on every doc pass, and the tool's own remediation is the unsafe act)
    **Command:** `beadloom sync-check`, `beadloom sync-update`
    **Context:** measured on BDL-061 S2b's doc pass. The gate reported **28 stale pairs** on `docs/domains/onboarding/README.md`. Exactly **one** of them had a changed file (`services/commands/docs.py`). The other 27 read `symbols_changed` while their files were untouched, because `symbols_hash` is stored per `ref_id` rather than per file: one file's symbols move, the node's hash moves, and every pair the node owns goes stale together.
    **Why it is worse than noise:** the writer is handed 28 pairs, told they are stale, and given `sync-update` as the remedy. Twenty-seven of them cannot be revised, because nothing about their files changed — so the only available action is to re-attest in bulk. That is precisely the "attested but never revised" hazard #163 was filed for, and here the tool *requires* it rather than merely permitting it. The honest pass on this repo was 1 revision and 27 deliberate re-attestations, and there was no better answer available.
    **Compounding:** because the 28 print as 28 near-identical gate lines (#167), the one pair that genuinely needed attention is indistinguishable from the 27 that did not — the signal is diluted by exactly the factor of the defect.
    **Expected:**
    - Compute the staleness fact at the granularity of the thing that changed. A pair is stale when *its* file's symbols moved, not when a sibling's did.
    - If per-node hashing is deliberate (it is cheaper), then the pairs that follow from it must be reported differently — `unaffected` or `sibling_changed`, never the same word as a pair whose own file moved. This is the same distinction the rest of this slice turned on: **unverifiable, unaffected and stale are three states and they must not print one word.**
    - Whatever the fix, `sync-update` should not be the recommended action for a pair nobody can revise.
    **Related:** #163 (re-attesting without evidence — this is the mechanism that forces it), #167 (28 identical lines), #146/#174/#175 (one word for several states).

177. ~~[2026-08-23] [HIGH] 🔴 Editing our own `CLAUDE.md` silently ships the edit to every adopter — the propagation loop~~ **CLOSED (BDL-061 S3, `.9`)** — the direction is reversed: the shipped core is authored package data, `.claude/CLAUDE.md` is COMPOSED from it plus this repo's own `.beadloom/flow/claude/CLAUDE.md`, and a local divergence is reported instead of flowing outward. Three corrections to the entry, all measured. (a) **The propagator was a TEST, not the pre-commit hook** — `tests/test_cli_setup_agentic_flow.py::TestSyncAgenticFlow::test_sync_round_trips_live_source` called `sync_agentic_flow(live)`, which rewrote the shipped template from the live file; in a clean room from HEAD one run moved its sha256 from `f360bc60…` to `6fcae821…` and the test PASSED while doing it. `pytest` runs inside `beadloom ci` and pre-push runs `beadloom ci`, hence "every commit". `sync_agentic_flow` now refreshes the AGENT assets only. (b) **The open question is answered, and worse than asked:** `config-check` was not "correct by design under the composition-result rule" — the `CLAUDE.md` body was verified by NOTHING. Measured on a scaffolded project: appending a paragraph → 0 drifts; deleting all of §7 → 0 drifts; replacing the whole file with `# gone` → 0 drifts, with the Gate printing `PASS: agent-config in sync`. It now compares against the composition result. (c) The third "Expected" item shipped: `test_no_bead_id_or_issue_number_in_the_shipped_templates` scans everything under `templates/` for a bead id. It was demonstrated to bite — a sabotage that re-enabled the snapshot put `beadloom-mr2l.42` back into the clean room's template and the test caught it.

    **Severity:** high (project-local context leaves the project without anyone deciding that it should, and the propagation happens inside a commit rather than at a review point)
    **Command:** the `install-hooks` pre-commit coherence step; `beadloom config-check`
    **Context:** the coordinator added a warning to `.claude/CLAUDE.md` §6 saying `setup-branch-protection` is not safe to re-run *in this repository right now*. Committing it left `src/beadloom/onboarding/templates/agentic_flow/CLAUDE.md.txt` modified — the hook had copied the paragraph into the shipped template **verbatim**, including the bead id `beadloom-mr2l.42` and the claim "`main`'s live protection has **seven**".
    **Issue:** both of those are facts about *this* repository. A bead id means nothing to an adopter, and the seven-contexts claim is simply false for them — a freshly scaffolded project gets nine contexts and a workflow that produces all nine, so the warning that is urgent for us is wrong for them. Caught only because `git status` was read after the commit; nothing announced the propagation.
    **The deeper problem is that there is no separation to enforce.** `.claude/CLAUDE.md` is simultaneously this project's instructions and the artifact we distribute, so every project-specific sentence is a shipping decision made by accident. This is exactly what BDL-061 S3 (`compose(core, architecture, stack, project)` with a project overlay) exists to fix, and this entry is the concrete case for it: the failure is not hypothetical drift, it is our own bead identifiers reaching adopters' onboarding text.
    **Expected:**
    - Until the overlay lands, the propagation must be **announced, not silent** — a hook that rewrites a distributed artifact should say so and require confirmation, the same standard we hold `sync-update` to (#163).
    - The direction should be explicit. Today a local edit flows *outward* by default; the safe default is that the shipped template is the source and a local divergence is reported, with promotion to the template a deliberate act.
    - Add a check that no project-local identifier — bead ids, our issue numbers, our repo's measured facts — appears in anything under `templates/`. Cheap, and it would have caught this at the commit.
    **Related:** #139/#152 (a project has no supported place for its own additions — the same gap from the adopter's side), #163 (re-attesting without evidence).
    **CORRECTION, one commit later: this is a LOOP, not an instance, and "fixed for this instance" was wrong.** The template was rewritten to an adopter-true paragraph and committed. The very next commit's pre-commit hook **re-propagated the project-local text over it**, restoring the bead id and the seven-contexts claim in the working tree. The hook enforces *template == our `CLAUDE.md`* in one direction, so the shipped artifact cannot diverge from this project's own instructions by construction — any correction survives exactly until the next commit. It reached `main` intact only because the re-propagation landed in the working tree and was never staged; a single `git add -A` would have shipped it. The severity is therefore not "a paragraph leaked once" but "the distributed artifact is permanently pinned to one project's local text, and the mechanism silently undoes attempts to separate them".
    **Open question, noticed while fixing this and deliberately not chased here:** after the two files were made to differ on purpose, `beadloom ci` still reported `config-check PASS: agent-config in sync`. That is plausibly correct by design — CONTEXT's decision is that `config-check` verifies the *composition result*, not file bytes — but it has not been verified, and "in sync" printed over two files that demonstrably differ is the exact shape this slice spent itself on. Whoever takes S3's composition work should establish which it is before relying on that green.
    **SECOND CORRECTION — the mechanism was misattributed, by the coordinator, twice.** It is not the pre-commit hook. `beadloom-mr2l.9` traced it to a **test**: `TestSyncAgenticFlow::test_sync_round_trips_live_source` rewrote the shipped template from this project's live `.claude/CLAUDE.md` (sha256 `f360bc60…` → `6fcae821…` in one clean-room run) and **passed while doing it**. `pytest` runs inside `beadloom ci`, and `beadloom ci` is what the pre-push hook runs — which is why it looked like a commit-time hook. The phenomenon was real and reproduced twice; the cause named in this entry was wrong both times.
    **That makes it a worse defect than filed, in a different way.** A test that mutates a tracked source file as a side effect and reports success is not a propagation policy anyone chose — it is an invisible write from the one part of the system whose entire job is to observe without changing. It also means the shipped artifact was, in effect, regenerated from one project's local text every time anyone ran the suite. Fixed in S3 (`beadloom-mr2l.9`); verified by the coordinator: running that test now leaves the template byte-identical (`046c1839…` before and after, `git status` clean).
    **The lesson worth keeping is about the diagnosis, not the code:** the coordinator observed the effect at commit time and named the nearest plausible cause twice without isolating it. REPORTS ARE NOT EVIDENCE applies to the coordinator's own reports.
    **THIRD FINDING, and it closes the entry: the role leg was still live after the `CLAUDE.md` leg was fixed.** `.10` found three tests writing to four tracked files (`TestSyncAgenticFlow` → `templates/agentic_flow/agents/*.md.txt`) and proved in a clean room that an edited live role file ships after a *failing* run as well as a passing one. It was invisible to `git status` for a reason worth stating plainly: **the write is undetectable whenever it happens to be byte-identical — and it ships whatever it is not.** So "is the tree dirty afterwards?" was never a sound test for this defect, which is why two rounds of looking at `git status` missed it.
    **Now structural rather than fixed case-by-case** — the shape this epic keeps having to reach for. `tests/tracked_write_guard.py` plus a `conftest` call-phase hook fails any test that writes a git-tracked file. Verified by the coordinator: a probe test that writes and restores `README.md` fails with the guard's own explanation, and `README.md` is left clean. A fourth instance of this defect can no longer be written without the suite rejecting it.
    **The MECHANISM is closed; the CLASS is not.** See #183: our project-local *facts* still reach adopters through composition — every adopter's `CLAUDE.md` renders Beadloom's version as the project's own. Marking this entry resolved on the strength of the test-write fix was premature.

152. ~~[2026-08-18] [MEDIUM] A project cannot extend a composed role adapter — overlays resolve only INSIDE the installed package~~ **CLOSED (BDL-061 S3, `.9`)** — proposal (a), with the drift-guard kept. A project layer at `.beadloom/flow/{roles,commands,claude}/<name>.md` composes AFTER the shipped overlays, and `config-check` verifies the **composition result**, so the addition is part of the expected output rather than drift. The minimum bar is also met and then some: `--fix` no longer deletes non-empty hand-authored content at all — a hand-edited file is reported with the project-layer path it belongs in and left exactly as it is.

    **Severity:** medium (structural; it is the reason a downstream project's gate ends up depending on an unreleased upstream change — see #151)
    **Command:** `beadloom setup-agentic-flow` / `config-check`
    **Context:** Dogfood on a downstream project that treats its role adapters as the project's agent contract and refines them with project-specific engineering standards.
    **Issue:** `role_composer.compose_role()` reads fragments from `roles_templates_root()` = `Path(__file__).parent / "templates" / "roles"` — `CORE` + one `architecture` overlay + `stack` overlays, all **inside the installed package**. `flow.yml` selects *which shipped overlays* compose; it cannot point at project-local ones. So a project that wants a standing paradigm in its `dev`/`review` roles has no supported place to put it: any local edit is reported as drift by `config-check`, and `--fix` removes it (no diff shown, no confirmation).
    **Observed consequence:** the downstream project's paradigm was therefore contributed **upstream into Beadloom's own core templates** (the only durable option). That worked — and then made the project's CI gate depend on the change being *published*, which it was not (#151). A project-level overlay would have decoupled the two entirely.
    **Expected / proposal:** (a) a project-local overlay directory (e.g. `.beadloom/roles/<role>.md.txt`) appended after the shipped overlays, so project additions survive recomposition **and** the composed part still gets drift-checked; or (b) marker-delimited hand-authored regions inside the generated file — the pattern already used for the auto-managed CLAUDE.md sections (`<!-- beadloom:auto-start -->`) — with `config-check` diffing only outside them. Minimum bar regardless: `--fix` should print the diff and refuse to delete non-empty hand-authored content without an explicit flag.

139. ~~[2026-07-29] [MEDIUM] Composed role adapters are byte-identical drift-guarded with no methodology/quality overlay slot~~ **CLOSED (BDL-061 S3, `.9`)** — a standing team practice now has a home: `.beadloom/flow/roles/<role>.md` is composed into the adapter and is part of the drift baseline, so `beadloom ci` stays green and the role subagents' own system prompts carry it (no per-launch injection needed). The workaround this entry recorded — keep it in CLAUDE.md prose — is retired; `.beadloom/flow/claude/CLAUDE.md` is the supported equivalent for the entry point itself.

    **Severity:** medium (blocks `beadloom ci` → blocks merge on a PR-gated main; forces a standing team practice OUT of the role adapters)
    **Command:** `beadloom config-check` / `beadloom setup-agentic-flow` / `beadloom ci`
    **Context:** A team adopting the vendored multi-agent flow wanted extra engineering paradigms to be **standing across all development** — BDD acceptance (Gherkin) and mutation testing — by hand-editing the four composed role adapters (`dev`/`test`/`review`/`tech-writer`) so each role's protocol carries the added discipline.
    **Issue:** The role adapters are drift-guarded **byte-identical** against `CORE + <arch> + <stack>` composition, and the overlay set is a fixed enum (architecture `ddd`/`fsd` × stack `python`/…). There is **no project-local "extra"/"append" overlay slot** for role adapters. So ANY hand-edit trips `config-check` → `beadloom ci` goes red. The only offered remedy (`config-check --fix` / `setup-agentic-flow`) **destructively recomposes to canonical**, stripping the added methodology. Net: a standing team practice cannot live in the role adapters at all — it can only sit in `CLAUDE.md` user-prose, so the role subagents' own system prompts never carry it (it reaches them only if the orchestrator injects it per-launch or the agent happens to read a project doc).
    **Expected:** A project-local, drift-**tolerated** extension point for role adapters — e.g. a `flow.yml` `overlays.custom:` / per-role `append:` slot (analogous to `CLAUDE.md`'s preserved user-prose regions), composed INTO the adapter and INCLUDED in the drift baseline — so a team can add standing practices to `dev`/`test`/`review`/`tech-writer` protocols without tripping `config-check`.
    **Workaround:** Keep the methodology in `CLAUDE.md` preserved user-prose (outside auto-regions — not drift-checked) + have the orchestrator inject the extra discipline into each subagent's launch prompt; revert the adapters to canonical (`git checkout <pre-edit> -- .claude/agents/*.md`) to restore a green `config-check`.

132. ~~[2026-06-15] [MEDIUM] `setup-agentic-flow --force` corrupts the vendored `CLAUDE.md` placeholder when run in Beadloom's own repo~~ **CLOSED (BDL-061 S3, `.9`)** — fixed by construction rather than by a guard: nothing writes the `CLAUDE.md` core any more. `sync_agentic_flow` no longer re-vendors it from the live copy, so `--force` cannot substitute a project name over `__BEADLOOM_PROJECT_NAME__`. The "do NOT run `--force` in the Beadloom repo" workaround is retired.

    **Severity:** medium
    **Command:** `beadloom setup-agentic-flow --force`
    **Context:** Observed during BDL-056 while recomposing the role adapters after editing the CORE tech-writer role.
    **Issue:** Running `--force` inside the Beadloom repo re-vendors the flow snapshot FROM the live composition. The live `.claude/CLAUDE.md` §0.1 has Beadloom's concrete project facts substituted in, so the re-vendor wrote `## 0.1 Project: beadloom` into the packaged `src/beadloom/onboarding/templates/agentic_flow/CLAUDE.md.txt`, **replacing the `__BEADLOOM_PROJECT_NAME__` placeholder**. That breaks the project-name substitution for every downstream adopter (the `TestClaudeMdRegionsPerProject` tests fail). It is a self-referential footgun: Beadloom is the source of the vendored template, so `--force` overwrites the template with the substituted instance.
    **Expected:** Re-vendoring should preserve the `__BEADLOOM_PROJECT_NAME__` placeholder (re-tokenize the project name on re-vendor), or `--force` should refuse to re-vendor the CLAUDE.md asset from a substituted live copy. Until fixed, do NOT run `setup-agentic-flow --force` in the Beadloom repo to recompose only role adapters — recompose the adapter files without re-vendoring CLAUDE.md, or revert the CLAUDE.md asset afterward.
    **Workaround:** After `--force`, `git checkout` the vendored `agentic_flow/CLAUDE.md.txt` (and the live `.claude/CLAUDE.md`) to restore the placeholder (done in BDL-056).

133. ~~[2026-06-15] [LOW] Per-worktree `beadloom.db` baseline causes mass false re-baseline when integrating parallel worktree waves~~ **CLOSED (BDL-061 S6, `beadloom-mr2l.78`)** — the same root as #182, judged and fixed together (as `.46`/`.47` did for their pair): the per-worktree baseline is the OCCASION, the per-node hash is the CAUSE. Integrating a wave changes some of a node's files, the node hash moves, and every pair the node owns — including modules the integration never touched — read `symbols_changed`, so the only remedy was the blanket `sync-update --yes --all` this entry recommends as a workaround. With the fact stored per file, only the pairs whose own file the integration changed are stale and the untouched pairs keep the baseline they were integrated with. The per-file baseline is CARRIED across a reindex rather than recomputed, because recomputing it would re-baseline against the tree just indexed, which is how the integration erased the drift it brought in. Pinned by the executable scenario `Integrating a parallel wave does not re-baseline untouched doc pairs` (`tests/acceptance/features/sibling_baseline.feature`, PRD US-6 criterion 4).

    **Severity:** low
    **Command:** `beadloom sync-check` (after integrating worktree-isolated dev beads)
    **Context:** BDL-057 coordinator integration. Two dev beads ran in isolated git worktrees (`isolation: worktree`); each has its OWN `.beadloom/beadloom.db` (a working-tree path). After file-checkout-integrating their code into the main branch, the main repo's `beadloom.db` still held pre-change baselines, so `sync-check` reported ~38 stale pairs (incl. modules the integration didn't touch) until a `sync-update --yes --all` + reindex fixpoint re-baselined.
    **Issue:** The doc-freshness baseline (`sync_state`) lives in the per-worktree DB, so it does not travel with the file-checkout integration. The integrator must re-run the mark-synced→reindex fixpoint to reconcile — extra friction, and a risk of masking genuine drift if done blindly. Relates to #118 (parallel-dev tree friction).
    **Expected:** Either document the "re-baseline after worktree integration" step in the coordinator merge flow, or make the baseline reconcilable from the integrated code state without a blanket `--all` (e.g. recompute only the pairs whose code actually changed in the integration diff).
    **Workaround:** After integrating worktree branches, run `beadloom sync-update --yes --all && beadloom reindex` to a stable `sync-check` 0 (the F4.1 fixpoint loop), then verify no genuine prose drift via the dev beads' API-CHANGE notes.

136. ~~[2026-06-18] [MEDIUM] Scaffolded flow is English-only and not overlay-aware~~ **CLOSED (BDL-061 S3, `.9`)** — all three parts. (a) `language:` is a `flow.yml` field, a peer of `architecture`/`stack`, validated for shape rather than against a closed list; every composition layer prefers a `<name>.<lang>.md.txt` fragment and a missing localisation falls back **with a note** rather than silently. (b) The hardcoded facts left the cores: `templates.md`'s "Python 3.10+" and testing/linting rows now come from `templates/commands/stack/<stack>/`, and "Modular architecture | CLI → Core → Storage" from `templates/commands/architecture/{ddd,fsd}/`. (c) The commands and `CLAUDE.md` are composable exactly like the role agents, so an adopter adapts them without breaking the drift-guard. The "ALL documents MUST be written in English" line is now the `doc-language` auto-region, rendered from `language:`.

    **Severity:** medium
    **Command:** `beadloom setup-agentic-flow` / `/templates` / `/task-init`
    **Context:** Adopting the flow on a non-CLI async-service project with DDD architecture whose documentation is maintained in a non-English language.
    **Issue:** The vendored `templates.md` + `task-init.md` hardcode: (a) **English** doc language ("ALL documents MUST be written in English") — `flow.yml` has `tools`/`architecture`/`stack`/`quality` but **no `language`** field; (b) **"Python 3.10+"** in the CONTEXT/RFC templates regardless of the project's actual Python version; (c) **"Modular architecture | CLI → Core → Storage"** in the CONTEXT template — that is Beadloom's OWN architecture, not derived from the project's `architecture: ddd|fsd` overlay. Because these files are drift-guarded byte-identical to upstream, an adopter cannot edit them without turning `beadloom ci` red, so they must override the defaults in CLAUDE.md prose. Same root cause as #77 (CLAUDE.md not adapted to the target stack), but for the vendored commands/templates after the BDL-052 configurator split.
    **Expected:** (a) add a `language` field to `flow.yml` (a peer of `architecture`/`stack`), threaded into the composed/vendored docs so docs scaffold in the project's language; (b) make the templates' architecture/stack facts overlay-derived (DDD/FSD layer names; the project's Python from `pyproject.toml`) instead of the hardcoded "CLI → Core → Storage" / "3.10+"; or at minimum (c) make the templates composable (CORE + overlays) like the role agents, so they adapt per-project without breaking the drift-guard.
    **Workaround:** override the defaults at project level in CLAUDE.md (a project-level rule beats the vendored default).

137. ~~[2026-06-18] [LOW] Cross-major flow re-init leaves orphaned command files and skips changed vendored commands as "hand-edited"~~ **CLOSED (BDL-061 S3, `.9`)** — the "at least a printed warning" option, plus the reason the surgical migration was needed in the first place. (a) `orphaned_flow_files()` reports every file a prior layout left in `.claude/commands/` — the four role files and `epic-init.md` — each with the exact `rm -f` command and, for a role, where it moved to; they are reported, never deleted. (b) A changed vendored command is no longer an undifferentiated "hand-edited; use --force": the flow manifest separates *stale* (Beadloom wrote it, the composition moved → recomposed in place) from *hand_edited* (reported with the `.beadloom/flow/commands/<name>.md` path, never rewritten), so a cross-major re-init recomposes what it owns without `--force`. (c) `--force` no longer clobbers a customised `CLAUDE.md` body either, because the customisation belongs in the project layer, which composes on top. **Closure amended (BDL-061 `.12`, 2026-08-23): (a) is true of the LIBRARY and not of the command.** `orphaned_flow_files()` computes the list and `beadloom setup-agentic-flow` prints nothing from it — measured, no caller anywhere in `src/`. (b) and (c) hold as written. The unprinted half is re-opened as #188; this entry is left closed for the parts that shipped rather than reverted wholesale, because the mechanism is right and only its output is missing.

    **Severity:** low
    **Command:** `beadloom setup-agentic-flow` (on a repo scaffolded by an older major flow version)
    **Context:** Re-initializing the agentic flow on a repo whose `.claude/` was scaffolded by an older layout (roles were slash commands in `commands/`); the current layout puts roles in `agents/`.
    **Issue:** `setup-agentic-flow` wrote the new `agents/*` and re-vendored `templates.md`, but (a) **left the old role files orphaned** in `.claude/commands/` (`dev.md`/`test.md`/`review.md`/`tech-writer.md` + the deprecated `epic-init.md`) — it does not remove files from a previous layout; and (b) **skipped** `coordinator`/`task-init`/`checkpoint` as "hand-edited; use --force" because their old-version content differed from the new canonical (a safety refusal). The adopter had to manually delete the orphans and delete+regenerate the changed commands — and `--force` also overwrites the base CLAUDE.md, so a surgical migration needs manual glue. Broader than the documented "orphaned adapters" limitation (which is about a dropped *tool*); this is a changed *role layout* across a major version.
    **Expected:** a migration path — e.g. `setup-agentic-flow --migrate` that removes superseded command files from a prior layout and re-vendors changed commands without clobbering the CLAUDE.md body; or at least a printed warning listing the orphaned/skipped files with the exact cleanup commands.
    **Workaround:** manually `rm` the orphaned `commands/*` role files + `epic-init.md`, delete the 3 skipped command files, then re-run `setup-agentic-flow` (so they are written fresh) — avoiding `--force` to preserve a customized CLAUDE.md.

122. ~~[2026-06-04] [HIGH] No data-access layer + `open_db` without context-managers (connection leaks)~~ **CLOSED (BDL-059 S2, #22)** — `infrastructure/repository.py` (typed graph-index reads; centralizes the 16× `SELECT ref_id, kind, summary FROM nodes`) + `infrastructure/db.py::connection()` context-manager; `tui/` now reads through the `application/graph_reads.py` facade (no raw SQLite in presentation). Leaks/ResourceWarnings addressed via the CM + S1 conftest yield/finally fixtures.

    **Severity:** high
    **Source:** REVIEW-2 §2 #1/#2 (verified at HEAD) · ROADMAP Technical-debt
    **Issue:** Raw `conn.execute("SELECT…")` is spread across **36 files** in all domains incl. `tui/data_providers.py` (presentation reads SQLite directly — a layer leak); the exact `SELECT ref_id, kind, summary FROM nodes` is hardcoded **16×**. `open_db` is called with **no `with`/`contextlib.closing` anywhere** → connection leaks on exceptions (SQLite write-lock risk) + ResourceWarnings in tests.
    **Expected:** Introduce `infrastructure/repository.py` (one place for queries); `tui` goes through the application layer only; wrap connections in a context-manager. Fixes both HIGHs at once. _(Note: the review's "53 open_db" figure is off — 27 in src / 232 total; the leak pattern is real.)_

123. ~~[2026-06-04] [HIGH] N+1 + non-indexable LIKE in `doc_sync/engine.py` `check_source_coverage`~~ **CLOSED (BDL-059 S2, #22)** — `check_source_coverage` de-N+1'd: ~5N per-node/child queries + `LIKE '%…%'` replaced by 5 set-based prefetch queries + an indexable `json_each` match; golden parity (frozen oracle + AST guard).

    **Severity:** high
    **Source:** REVIEW-2 §2 #3 (verified, `engine.py:451-525`) · ROADMAP Technical-debt
    **Issue:** Nested per-node and per-child queries plus `LIKE '%…%'` (cannot use an index) → quadratic on a large graph.
    **Expected:** Prefetch with a single JOIN / `IN (...)`; consider a normalized annotations table.

124. ~~[2026-06-04] [MEDIUM] Cycle detection re-explores from every node (no global visited)~~ **CLOSED (BDL-059 S3, #23)** — cycle detection rewritten WHITE/GREY/BLACK with path-as-set O(1) membership (`graph/rules/cycles.py`); golden-parity test reproduces the pre-refactor output byte-identically.

    **Severity:** medium
    **Source:** REVIEW-2 §2 #4 (verified, `rule_engine.py:1141-1209`) · ROADMAP Technical-debt
    **Issue:** `evaluate_cycle_rules` runs DFS from each node with no global `visited`; `neighbor in path` is O(n) list membership; bounded only by `max_depth=10`. Exponential risk on a dense microservice graph. (A per-rule `seen_cycles` dedup exists, but no global visited.)
    **Expected:** Tarjan/Johnson SCC, or DFS with WHITE/GREY/BLACK + a shared visited set; `path` as a set.

125. ~~[2026-06-04] [MEDIUM] God-domain `graph/` should split out `federation` + `rules`~~ **CLOSED (BDL-059 S3, #23)** — `rule_engine.py` (2249)→`graph/rules/` package + `federation.py` (1000)→`graph/federation/` package, by cohesion (public import paths byte-stable). The `domain-size-limit` graph warning (was #119) was resolved by the owner-decided recalibration 200→280 (documented in `rules.yml`) — recalibration, NOT gaming (an in-domain split can't lower a domain's symbol count).

    **Severity:** medium
    **Source:** REVIEW-2 §2 #5 (verified) · extends #119 · ROADMAP Technical-debt
    **Issue:** `graph/` is 6439 lines (rule_engine 1743 + federation 1000 + import_resolver 929) and mixes several concerns; `application/` is 233 symbols. Both trip the `domain-size-limit` warning (graph 202, application 233 vs 200).
    **Expected:** Extract `federation` and `rules` into their own packages (clears the graph-202 warning of #119); reduce `application/`.

126. ~~[2026-06-04] [MEDIUM] God-functions carry business logic in the wrong layer~~ **CLOSED (BDL-059 S4, #24)** — `cli.py:status` data-gathering moved to `application/status.py` (presentation/logic split); `cli.py` (3985)→`services/commands/` package; `scanner.py` (2770)→`onboarding/scanner/` package; `reindex.py` (1352)→`application/reindex/` package — the god-functions decomposed by responsibility.

    **Severity:** medium
    **Source:** REVIEW-2 §2 #6 (verified) · ROADMAP Technical-debt
    **Issue:** `cli.py:status` ~283 lines (business logic in the CLI layer); `scanner.bootstrap_project` ~260; `reindex.incremental_reindex` ~216; `scanner.interactive_init` ~203.
    **Expected:** Extract `cli.py:status` → `application/status.py`; decompose the scanner/reindex god-functions.

127. ~~[2026-06-04] [LOW] `Any` concentration + exception swallowing in onboarding~~ **CLOSED (BDL-047)** — the `doc_generator.py` `except sqlite3.OperationalError: pass` swallows are gone (the handlers now bind `as exc` and surface/raise the error instead of silently passing). **Remaining (out of this epic's scope):** `infrastructure/git_activity.py:251` still has an `except ValueError: pass` on date parsing, and the broader `Any` concentration in onboarding is the larger type-safety item — both now **CLOSED (BDL-059 S5, #25)** — `git_activity.py` broad except narrowed to specific types (subprocess/`OSError`/`TimeoutExpired`); onboarding scanner dicts → `TypedDict` (new `onboarding/scanner/types.py`), a net `Any` reduction, mypy --strict clean.

    **Severity:** low
    **Source:** REVIEW-2 §2 #7/#8 (verified) · ROADMAP Technical-debt
    **Issue:** 172 `Any` total, concentrated in onboarding (`doc_generator.py` 49, `scanner.py` 25, `config_reader.py` 19) — disables type-safety in the most error-prone layer. 7 spots of `except…: pass` (incl. `doc_generator.py:274,311` `except sqlite3.OperationalError: pass`) hide real DB errors.
    **Expected:** TypedDict/dataclass for parsed structures; narrow the exceptions and/or log at debug.

128. ~~[2026-06-04] [MEDIUM] L2 context cache not wired into `build_context`~~ **CLOSED (BDL-059 S5, #25)** — `build_context` now routes through the `SqliteCache` (transparent ETag cache; identical bundle on hit vs miss, proven by golden + HIT-never-recomputes tests).

    **Severity:** medium
    **Source:** REVIEW §4.4 (verified `builder.py`) · ROADMAP Technical-debt
    **Issue:** `build_context` issues `SELECT * FROM code_symbols` per bundle and never calls the existing L2 `bundle_cache` (`cache.py`) → latency risk on 50K-symbol monorepos.
    **Expected:** Wire `build_context` through the L2 cache; avoid the per-bundle full symbol scan.

129. ~~[2026-06-04] [MEDIUM] Test-suite hygiene gaps~~ **CLOSED (BDL-059 S1, #21)** — `pytest-randomly` added (immediately exposed + fixed a latent live-DB order-dependence via a session-scoped `live_repo_reindexed` conftest fixture); conftest yield/finally db fixtures (ResourceWarnings); a grammar-guard test that FAILS-not-skips when tree-sitter grammars are absent (gated `BEADLOOM_REQUIRE_LANGUAGE_GRAMMARS=1` in CI); tests decoupled from production internals (the private-attribute coupling reduced ahead of the S2–S5 refactors).

    **Severity:** medium
    **Source:** REVIEW-2 §3 + REVIEW §4.3 (verified) · ROADMAP Technical-debt
    **Issue:** (a) ResourceWarnings from unclosed SQLite connections — suite goes red under `filterwarnings=error::ResourceWarning`; (b) tree-sitter grammars are silently skipped if absent → TS/Go/Rust can pass CI untested; (c) almost no parametrization (10 across 3211 tests); (d) **372** private-attribute (`._x`) couplings block refactors; (e) TUI smoke tests without asserts; (f) no `pytest-randomly` (order-dependence undetected).
    **Expected:** conftest yield+finally db fixtures; make grammars mandatory in CI (or a guard test); parametrize hotspots (rule_engine, language suites); de-couple from private attrs before large refactors; add asserts to TUI tests; add `pytest-randomly`.

130. ~~[2026-06-04] [HIGH] Docs list rule types as dataclass names, not real YAML keys (internal contradiction)~~ **CLOSED (BDL-057)** — the SPEC-fill rewrote `architecture.md` to a correct YAML-key table (`deny, require, forbid, layers, forbid_cycles, forbid_import, check`), matching the dispatch (`rule_engine.py`); `getting-started.md` no longer lists rule types; `README.md` was already correct. No `forbid_edge`/`cycle_detection`/`import_boundary`/`cardinality` strings remain in `docs/`.

    **Severity:** high
    **Source:** REVIEW-2 §4 #1 (verified) · ROADMAP Technical-debt
    **Issue:** `getting-started.md:127` and `architecture.md` (×4: L83,113-119,153,253) list rule types as `require, deny, forbid_edge, layer, cycle_detection, import_boundary, cardinality` — these are **dataclass names**, not YAML keys. Real keys (dispatch `rule_engine.py:662-724`): `deny, require, forbid, forbid_cycles, forbid_import, layers, check`. `README.md:186` has the CORRECT list — an internal contradiction. A user who copies `forbid_edge:` gets a rule that silently never fires.
    **Expected:** Single source of truth for rule-type keys; fix getting-started.md + architecture.md to match the dispatch (and README).

131. ~~[2026-06-04] [LOW] Doc accuracy nits: non-existent flag, miscount, placeholders~~ **CLOSED (v2.1.0 release)** — all three fixed: `getting-started.md` drops the non-existent `--non-interactive` flag (now `--yes`/`-y` only); `architecture.md` DDD domain count corrected (six domains + application + two interface layers); `CONTRIBUTING.md` `your-org`→`zoologov` placeholder fixed + a Release Process section added.

    **Severity:** low
    **Source:** REVIEW-2 §4 #2/#3/#4 (verified) · ROADMAP Technical-debt
    **Issue:** `getting-started.md:29` documents a non-existent flag `--non-interactive` (only `-y/--yes` exists); `architecture.md:9` says "six DDD domains" but lists five; `CONTRIBUTING.md` has `your-org` placeholders and no release-process section (PyPI/versioning/tag).
    **Expected:** Drop `--non-interactive`; fix the domain count; replace placeholders with `zoologov/beadloom` + add a release section.

112. ~~[2026-06-02] [INFO/LOW] Incremental reindex displays `Symbols: 0` — per-run delta, not backfilled to the live total~~ **CLOSED (BDL-047)** — the incremental path now backfills `symbols_indexed` to the true live-DB symbol total (`SELECT count(*) FROM code_symbols`), mirroring the #88 nodes/edges fix, so a docs-only reindex no longer prints "Symbols: 0" on an intact index (`application/reindex.py:1330-1334`, comment cites #112).

    **Severity:** info / low (cosmetic display only — zero gate impact)
    **Command:** `beadloom reindex` (incremental path)
    **Context:** Observed during BDL-039 F3 tech-writer doc edits. After #88 was fixed, the incremental reindex now backfills `nodes`/`edges` to the true live-DB totals on the docs/code-only path. The `symbols_indexed` counter, however, still reports only the **per-run delta** (symbols touched this run), so a CLI run that changes only docs can print "Symbols: 0" while the DB actually holds all indexed symbols.
    **Issue:** Inconsistent reporting semantics between counters: `nodes`/`edges` show the live total (per #88), but `symbols_indexed` shows the run delta. A reader can misread "Symbols: 0" as "no symbols indexed."
    **Expected:** Either backfill `symbols_indexed` to the live DB symbol total on the incremental path (consistent with nodes/edges per #88), or label it explicitly as a delta ("Symbols indexed this run: 0").
    **Impact:** None on correctness or any gate — `sync-check` / `lint` / `doctor` / `beadloom ci` all read the DB, not this counter. Purely a cosmetic CLI-display artifact.

105. ~~[2026-06-01] [MEDIUM] Adding a new source file to a domain re-stales the domain doc against ALL its member files~~ **CLOSED (BDL-061 S6, `beadloom-mr2l.78`)** — the earliest filing of the defect #182 re-found eleven weeks later. Its **Expected** was right in 2026-06 and is what shipped: "`symbols_changed` should fire only for the pair(s) whose own code symbols changed". A file that ARRIVES on a node whose baseline is carried gets no file-level fact of its own, because its arrival is part of what moved the node hash — so a genuinely-new module is still reported, and its unrelated siblings are not.

    **Severity:** medium
    **Command:** `beadloom reindex && beadloom sync-check`
    **Context:** BDL-038 BEAD-01 added one new module (`src/beadloom/graph/contracts.py`) to the `graph` domain and edited one sibling (`federation.py`). Before the change `sync-check` was honest 0; after, it reported **8 stale pairs** for `domains/graph/README.md` — including files I never touched (`diff.py`, `snapshot.py`, `linter.py`, `rule_engine.py`, `import_resolver.py`, `cli.py`), all with reason `symbols_changed`. Verified by stashing the change: at HEAD the same pairs are clean.
    **Issue:** The domain doc's symbol-drift baseline appears to be keyed on the domain's **aggregate** symbol set, so adding any symbol anywhere in the domain invalidates the `symbols_hash` for **every** doc↔file pair in that node — not just the pair whose code actually changed. One new file → N false `symbols_changed` pairs.
    **Expected:** `symbols_changed` should fire only for the pair(s) whose own code symbols changed. A genuinely-new module should surface as a single `untracked_files` signal on the doc, not re-stale every unrelated sibling pair. (Compare #89: per-file granularity was the fix there too.)
    **Workaround:** Document the new module in the domain README, then `mark_synced_by_ref(conn, '<domain>', root)` to re-baseline all pairs, then re-run to fixpoint (see #106).

106. ~~[2026-06-01] [LOW] No non-interactive CLI to attest sync baseline (`mark_synced`) — only the interactive `sync-update`~~ **CLOSED (BDL-047 W1)** — `beadloom sync-update [REF] --yes` (and `--all` with `--yes`) now re-baselines freshness non-interactively (recomputes hashes + `symbols_hash`, sets `status='ok'`, no editor/prompt), wrapping `mark_synced_by_ref`. This is the primitive the F4.1 AI-tech-writer fixpoint loop uses; agents no longer reach past the CLI into the engine.

    **Severity:** low
    **Command:** `beadloom sync-update <ref>` (interactive: `click.confirm` + `click.edit`)
    **Context:** After a doc refresh, re-baselining the sync state requires `mark_synced` / `mark_synced_by_ref` (`doc_sync.engine`). The only CLI surface is `sync-update`, which opens an editor and prompts — unusable in an agent/CI flow. BEAD-01 had to call the engine directly via `uv run python -c "...mark_synced_by_ref..."`.
    **Issue:** There is no `beadloom sync-update <ref> --mark-synced` (or `beadloom sync-mark <ref>`) for non-interactive attestation. Agents must reach past the CLI into the engine.
    **Expected:** A non-interactive attest flag/command, e.g. `beadloom sync-update <ref> --mark-synced` or `beadloom sync-mark [--ref R | --all]`, that recomputes hashes + `symbols_hash` and sets `status='ok'` without an editor. Pairs with the F4.1 AI-tech-writer loop (STRATEGY-3) which must attest non-interactively. Re-running `reindex && sync-check` after attest to a stable 0 is mandatory (F4.1 loop invariant — clearing `symbols_changed` surfaces masked `untracked_files`, as it did for `contracts.py` here).



### Import extraction depth — #159 (2026-08-20)

- 159. ~~[HIGH] Imports below a file's top level were never extracted, so a third of the dependency graph was missing~~ **FIXED (2.2.0)** — all nine language extractors walked only `root.children`, so an import inside a function, a class body, an `if TYPE_CHECKING:` guard or a `try:` block was invisible. Those are exactly where an import is placed to defer cost or to break a cycle, so `no-dependency-cycles` and `forbid_import` were blind to the edges they exist to judge (the #142 family, one level deeper). Measured: **460 nested imports, 231 first-party** — about a third of the total; `depends_on` went 51 → 146 edges. Turning the lights on surfaced **six real violations at once**, all one pattern: `application/doctor.py`, `doc_sync/audit.py` and `doc_sync/surface.py` reaching UP into `beadloom.services` to introspect the live CLI/MCP surface. Fixed by inverting that through a new `infrastructure/surface_registry` port (services register their surface; lower layers read it) with **"unknown is not zero"** as the contract, so a missing surface reports "not verified" instead of a plausible count. The first attempt routed the MCP tool count through the port too, and the gate caught it immediately: `docs audit` lost its tool-count fact because the CLI process never imports the server. That consumer now reads the canonical `MCP_TOOL_CATALOG`.

### Prefix attribution — #144 + #157 (2026-08-20)

- 144. ~~[MEDIUM] `max_symbols` counts by source-path PREFIX without subtracting nested nodes — carving a subpackage into its own node does NOT relieve the parent~~ **FIXED (2.2.0)** — attribution is now ownership-based: a file belongs to exactly one node, the most specific one whose `source` covers it. Implemented once in `infrastructure/repository` (`get_owning_ref_id` / `owns_file` / `count_symbols_owned_by_node` / `count_files_owned_by_node` / `get_owned_symbols`) and consumed by `max_symbols`, `max_files`, the architecture view, node pages and `import_resolver`, so no two surfaces can disagree. Measured effect on this repo: `application` 284 → 150, `graph` 257 → 61, the root service 1154 → 0. Threshold recalibrated 290 → 180 because the METRIC changed meaning (see `docs/architecture.md`). The subtree-size signal the old metric also carried is tracked separately as #158 rather than folded into the new threshold.
- 157. ~~[HIGH] A package annotated in `__init__.py` gets a FILE source, so 5 nodes report 0 symbols and `max_symbols` can never fire on them~~ **FIXED (2.2.0)** — same root, same fix: a source naming a package's `__init__.py` covers its PACKAGE, since the façade only re-exports. The 228 previously-invisible symbols (cli-commands 71, federation 57, agent-prime 43, reindex 31, debt-report 26) are attributed again, and this repo's five façade sources were repointed at their package directories for clarity. A `doctor` check added mid-fix to *warn* about the condition was removed once ownership made it structurally impossible — a check that can never fire is worse than none.

### Dependency currency pass (2026-08-19)

- 150. ~~[HIGH] 🔴 `tree-sitter` has no upper bound → a fresh install pairs a newer core with the shipped grammars and SEGFAULTS with zero output~~ **FIXED** — pinned `tree-sitter>=0.25,<0.26` in `pyproject.toml` with the reasoning in-line, and guarded in `tests/test_grammar_guard.py`: `test_tree_sitter_core_requirement_is_bounded_above` fails if the pin ever loses its ceiling, `test_installed_tree_sitter_satisfies_the_declared_bound` fails if the environment running the suite sits outside the declared range. **Reproduction note (matters for the fix's shape):** the small case no longer crashes — under core 0.26.0 all ten grammars load through the production loader, `extract_symbols` parses TS/Swift/Obj-C/Kotlin/C++ fine, and a fresh `beadloom[languages]==2.1.0` install completes `init` + `reindex --full` on a 5-file project. The segfault appeared only under the full suite, inside `_index_code_files` during a repo-wide reindex. So the honest rule is **a grammar that loads proves nothing; only a full reindex does** — which is why the pin, not a load-time check, is the fix. Not done, carried forward: the from-scratch-resolver CI job (`uv venv` + install with no lockfile/cache + reindex a fixture) that #150 asked for — the existing suite runs in an environment that already holds a compatible pair.

  <details><summary>Original report (2026-08-18)</summary>

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

---

## Chronology (historical)

The dated record of what was opened, closed or verified. Kept at the end on purpose:
an agent reading this file needs the OPEN items, not the history, and preamble is the
part of a long document that is read least usefully (BDL-UX #156).

<summary><strong>Chronology</strong> — what was opened, closed or verified, newest first</summary>

- **2026-08-26** — (v3.0.0 release, `beadloom-mr2l.90`): **opened #192** — verifying the BUILT wheel against a project that is not us found that a virgin `beadloom init --yes` exits 0 over a graph of 2 nodes and 0 edges and then fails its own `beadloom ci` on `domain-needs-parent`, a rule the same command wrote one step earlier. It is not new; it had never been measured, because everything measured here runs on a repository whose graph has been hand-authored since BDL-008. The rest of what the release did was make the OPEN set adopter-visible. The CHANGELOG's Known limitations name eight items an adopter will meet, and three of them live only here rather than in the tracker: **#191** (`setup-agentic-flow` recomposes a hand-edited role adapter — the #139/#151/#186 shape in the sibling command, and the command an upgrader runs), **#187 of 2026-08-25** (`bd list --json` returns a filtered view as a bare list — External, and it stays open because it is `bd`'s default, not ours) and the `measurable-goal` recall cost. **Found while writing the release notes and not fixed here: this log has two issues numbered 187** — the closed `setup-agentic-flow`/`config-check` one of 2026-08-23 and the open External one of 2026-08-25 — so a reference to "#187" is ambiguous in both directions. Filed as a bead rather than renumbered, because renumbering breaks every reference already written in the CHANGELOG, the tracker and this file. Measured at release: **seventeen** beads of this epic open in the tracker (`bd list --status open --json`, excluding the epic row and the swarm placeholder).

- **2026-08-24** — (BDL-061 S6, `beadloom-mr2l.78`): CLOSED #182, #133 and #105 — three filings of one
  root over eleven weeks. `symbols_hash` was stored per pair and computed per node, so one changed file
  marked every pair the node owns `stale/symbols_changed` and the followers could only be cleared by the
  bulk re-attestation #163 was filed to prevent. `sync_state` now also carries `file_symbols_hash`, the
  pair's OWN file surface; only that can make a pair stale, and a follower is `unverified` with the
  reason `sibling_symbols_changed`, naming the file that moved. Measured in two clean rooms off
  `e255a21`: one function appended to `application/architecture_view.py` gave **69 stale / 67 of them
  naming an untouched file** before, and **2 stale + 67 unverified** after. No new verdict word was
  invented — `unverified` is the one #174/#175 already established for "the checker cannot know".

- **2026-08-20** — (post-2.2.0, turning the release's lessons into checks): Opened #162 (🔴 **doctor should audit the PRODUCED graph, not just the code** — island / unexplained-leaf / claim-without-evidence. The four defects this release fixed all shipped past dev+test+review+tech-writer and a 6/6 gate because every test verified a FUNCTION and none verified the CLAIM the graph makes; the audits that found them were written by hand in ten lines each), #163 (`sync-update` can re-attest a doc nobody read — a re-baseline silences `sync-check` with no evidence the prose still describes reality; plus prose that no symbol pair anchors can never go stale at all) and #164 (LOW — the beads git-hook prints `bd import -i`, a flag that does not exist, on a warning that was itself a false alarm; the #140 shape). Total 161→164, Open 43→46.

- **2026-08-20** — (v2.2.0 release): Opened #161 — `docs audit` verifies numeric FACTS but never checks that a documented identifier still EXISTS, so documentation can name a function the code no longer has and the gate stays green. Found the hard way: two functions removed while narrowing the `surface_registry` port stayed documented in this very release's branch, past a 6/6 gate, and were caught by a hand-written ten-line grep during an unrelated question. Also: #160 (AsyncAPI ingestion) deferred with its plan recorded in ROADMAP. Total 160→161, Open 42→43.

- **2026-08-19** — (BDL-060 S4 dogfood — the owner clicking nodes in the architecture map): CLOSED #159 (imports below a file's top level were never extracted — 460 nested, 231 first-party, about a third of all imports; making them visible took `depends_on` from 51 to 146 edges and surfaced SIX real boundary violations at once, all one pattern: domain/application code reaching UP into `services` to introspect the live CLI/MCP surface, fixed by inverting it through a `surface_registry` port). Opened #160 (🔴 **AsyncAPI ingestion is documented as a capability but wired to nothing** — `extract_payload_body` is called by ZERO code paths in `src/`; the function works and is tested, but no document ever reaches it, so the SPEC's "teams on AsyncAPI ingest the payload schema via…" describes a capability the product does not deliver. It survived dev + test + review + tech-writer beads and a green gate because each verified the FUNCTION and none asked whether anything calls it). Total 158→160, Closed 90→91.

- **2026-08-19** — (BDL-UX #144/#157 fixed together): CLOSED #144 and #157. Both had the SAME root — attribution by raw path prefix — so they were fixed once, in one place: **a file belongs to exactly one node, the most specific one whose `source` covers it** (`infrastructure/repository`), now shared by `max_symbols`/`max_files`, the architecture view's symbol badge, node-page symbol listings and `import_resolver`'s file→node attribution. Three things fell out that no single-surface patch would have reached: (1) a node whose source IS a file never owned that file, so its imports were credited to the enclosing directory's node; (2) derived `depends_on` edges between a node and its `part_of` ancestor are a category error and are no longer emitted — 5 of 14 edges were this noise, and they were manufacturing node-level cycles that do not exist at module level; (3) with honest ownership the dependency graph went 14 → 24 edges, surfacing real feature-level dependencies (`graph-loader → federation`, `mcp-server → reindex`, `site-generation → graph`) that prefix attribution had collapsed into their parents. Opened #158 (the subtree-size signal the new metric no longer carries). Total 157→158, Open 42→41, Closed 88→90.

- **2026-08-19** — (BDL-060.15 review): Opened #157 (HIGH — a package that carries its `# beadloom:feature=` annotation in `__init__.py` (the natural place after BDL-059's decomposition) gets its node `source` recorded as that FILE, so every symbol read sees an empty façade: **5 nodes, 228 symbols invisible** on Beadloom's own graph. All five readers agree on 0, so it must be fixed at the source, not in a reader. Consequence in the #146 family: `max_symbols` can never fire on those nodes — a size rule reporting clean because it is looking at nothing — which also distorts the very `domain-size-limit` recalibration the S4 review was assessing). Total 156→157, Open 41→42.

- **2026-08-19** — (dependency currency pass): CLOSED #150 — REPRODUCED on Beadloom's own tree and FIXED. The reporter's minimal case does not reproduce today (core 0.26.0 loads all ten grammar wheels and parses small files cleanly through `get_lang_config`/`extract_symbols`, and a fresh `pip install beadloom[languages]==2.1.0` resolves a pair that survives `beadloom init` + `reindex` on a 5-file project) — the crash needs VOLUME: the full test suite segfaulted inside `_index_code_files` partway through a real repo-wide reindex. That sharpens the issue rather than softening it: **loading a grammar is not evidence that the pairing is safe**, which is exactly why it survived a gate. Fixed by `tree-sitter>=0.25,<0.26` plus two guards in `tests/test_grammar_guard.py` (the declared pin must carry an upper bound; the INSTALLED core must fall inside it, so a local upgrade cannot pass the suite while claiming an untested range). Still open from #150's ask: the from-scratch-resolver CI job. Open 42->41, Closed 87->88.

- **2026-08-19** — (design input): Opened #156 — 🔴 **context rot** gives #153 a measurable root: recall of a long instruction file DEGRADES as context fills, i.e. exactly when a long session needs the rules most, so shrinking the scaffolded `CLAUDE.md` is mechanism and not tidiness; the design target is *"the smallest possible set of high-signal tokens"* at the *"right altitude"* between brittle hardcoding and vague guidance. Also: role agents should return a bounded distilled result (~1-2k tokens) as a stated contract; and 🔴 **selective escalation is a second graph-derived feature** — blast radius, boundary crossings and invariant-bearing nodes decide what must stop for a human, turning "escalate when unsure" into a harness rule. Improvements 19->20, Total 155->156.

- **2026-08-19** — (design input): Opened #155 — multi-agent failure modes and long-running-harness patterns from three current Anthropic publications. 🔴 Headline: **wave shape should be DERIVED FROM THE GRAPH** — parallel agents pay off on independent subgraphs (266 vs 21 vulnerabilities found) and rot on shared code with rich interdependencies; only Beadloom holds the code-level interdependence needed to decide. Also: conformity cascades (18/30 agents chose the same branch name; identical context ⇒ identical mistakes, and shared state is the vector); a review role fed the author's summary converges on it (hidden-profile groups scored 17–36% vs ~100%), so the reviewer must see diff+spec BEFORE advocacy; named long-running failure modes led by *premature victory declaration*; and state files in JSON because agents corrupt Markdown. Improvements 18→19, Total 154→155.

- **2026-08-19** — (design input): Opened #154 — oversight patterns for the #153 enforcement epic, drawn from Anthropic's public *Risk Report: August 2026*: separate asynchronous monitoring from blocking interventions and label which is which; claim raised DETECTABILITY rather than prevention; ship a machine-readable "does not cover" note with every gate; make "diff vs its own stated purpose" a check type (Beadloom holds the stated purpose); 🔴 spawning must narrow authority, never widen it (their incident: legacy instructions propagated `--dangerously-skip-permissions` to child agents, detected only by the damage); 🔴 shared agent context propagates DECISIONS — one agent's silent scope-narrowing spread to later agents while metrics looked green, found 3 days later by a human; 🔴 gates need a LIVENESS proof — their filter ran misconfigured for several model generations "without anyone noticing", the same defect as #61. Improvements 17→18, Total 153→154.

- **2026-08-19** — (dogfood — DDD project, one full working session through the scaffolded flow): Opened #153 (HIGH, EPIC PROPOSAL — the scaffolded multi-agent flow is advisory and therefore silently skipped: measured 0/6 beads reviewed, 1/6 mutation-gated, 0 `.feature`, 0 `/task-init`, while the ONE rule backed by a machine check blocked the agent 4 times in the same session. Root: `CLAUDE.md` is delivered as a user message the model may deem inapplicable, and compliance degrades with instruction count — cf. anthropics/claude-code#32163. Proposal: ship blocking `Stop`/`PreToolUse` hooks with the flow, derive their conditions FROM THE GRAPH, make strictness configurable per rule and work kind, give exclusions a named reason + exit condition, and let roles run as independent subagents). Improvements 16→17, Total 152→153.

- **2026-08-18** — (dogfood — DDD project, wiring the beadloom gate into GitHub Actions CI): Opened #150 (HIGH — `tree-sitter` unbounded upper pin pairs core 0.26 with 0.25-ABI grammars, so a FRESH install segfaults with zero output on every parsing command; invisible to anyone who does not reinstall, since existing environments keep a matching pair — measured on two isolated venvs, reproduces on macOS as SIGBUS too, so it is a dependency bug, not an environment one) #151 (HIGH — the published release lags `main`: BDL-059's role templates are unreleased, so a fresh install reports drift against projects scaffolded from `main`, and `--fix` would rewrite them back to the OLDER templates: 42 deletions / 0 insertions, deleting a standing engineering paradigm. Diagnosed only via an env-skew trap: exit 1 from a PyPI install vs exit 0 from a source install, same self-reported version 2.1.0, byte-identical files) and #152 (MEDIUM — structural: role overlays resolve only INSIDE the installed package, so a project has no supported place for its own additions; that is *why* the paradigm had to go upstream, which is what coupled a downstream gate to an unreleased change). Common thread with #142/#146/#147: a verb that reads as a check either changes state or reports success for work it did not do. Total 149→152, Open 39→42.

- **2026-08-05** — (dogfood — DDD project, exposing the READ-ONLY beadloom surface to an agent): Opened #147 (HIGH — plain `lint` MUTATES `beadloom.db`; measured by DB sha256 before/after, only `--no-reindex` is read-only, and `--strict` is additionally required for a non-zero exit on an error-severity violation, so a caller checking the exit code alone reads a real boundary break as clean), #148 (MEDIUM — `lint` output shape depends on TTY: the documented `N violations, M rules evaluated` summary is absent through a pipe, with no flag to select a stable contract), #149 (LOW — `graph --format c4 --level component --scope <leaf>` exits 0 with a single empty `C4Container`, giving no way to distinguish "no internals" from "here are the internals"). Common thread with #142/#146: the tool reports success for work it did not do, or changes state under a verb that reads as a check. Total 146→149, Open 36→39.

- **2026-08-03** — (dogfood — DDD project, splitting an oversized vertical-module node): **THIRD in-the-wild confirmation of #142** (incremental `reindex` does not refresh import edges): a slice added a runtime import that closed a `A → B → runtime-app → A` module cycle; `reindex && lint --strict` reported **0 violations** through the whole verification pass — the coordinator's own independent re-run included — and the cycle was only surfaced later by a full rebuild (`rm .beadloom/beadloom.db && reindex`) during an unrelated refactor. Note the compounding factor: the false-green survived a *deliberately sceptical* review because the documented loop (`reindex` → `lint`) is itself the thing that lies; there is no signal distinguishing "clean" from "stale import graph". Reinforces the #142 fix priority (Gate must full-reindex, or `lint` must refuse a stale graph). Opened #146 (HIGH — `component` nodes contribute NO sync-check pairs at all, so their docs are never freshness-checked and the gate's green reads as "fresh" when it means "not looked at"; found when a wave's "sync-check by node X — clean" turned out to mean "zero pairs exist"), #144 (MEDIUM — `max_symbols` counts by source-path PREFIX without subtracting nested nodes, so carving a subpackage into its own node does NOT relieve the parent — the natural remedy for an oversized node silently does nothing), #145 (MEDIUM — `ctx <ref> --json` returns the repo-wide `code_symbols` array, not the node's, so an agent sizing a node from its own context bundle reads garbage). Total 143→145, Open 33→35.

- **2026-07-23** — (dogfood — DDD project, enforcing boundaries between equal-rank vertical modules): Opened #143 (HIGH — no native module-boundary / mutual-isolation rule primitive. Enforcing that each vertical module's internals are reachable only via its public facade (not a sibling's `usecases/`/`adapters/`) requires hand-written **O(N²)** `forbid_import` path-glob rules — one per ordered module pair per internal layer. Root causes in the rule engine: (a) `forbid_import.from`/`.to` accept only a SINGLE glob string each — no list, and fnmatch has no brace-expansion, so `src/bob/{a,b}/**` is literal; (b) "all modules except X" is expressible only via first-char negation `[!x]`, which SILENTLY mis-groups two modules sharing an initial letter — e.g. two `c…` modules (`coding`/`capabilities`) become indistinguishable, so the isolation glob wrongly excludes BOTH → a real cross-module import goes uncaught; (c) `domain-root ↛ adapters` cannot be expressed cleanly because fnmatch `*` spans `/` (workaround `<mod>/[!au]*` drops root files starting a/u — accepted only because they're import-leaves). No existing rule type derives pairwise isolation from node tags: `LayerRule` is a linear top-down order (not mutual isolation), `ForbidEdgeRule`/`DenyRule` matchers select one from-group + one to-group (no same-tag-different-node correlation). Workaround adopted downstream: a ~60-line `scripts/gen_boundary_rules.py` emitting explicit-path rules into a marker-delimited region with a `--check` mode. Proposal: a `module_isolation` rule type `{tag: <module-tag>, internal_layers: [usecases, adapters]}` that the engine expands into pairwise isolation + internal-layering from each node's `source` path — removes both the O(N²) hand-generation and the char-class collision at the core). Total 142→143, Open 32→33.

- **2026-07-23** — (dogfood — DDD project, domain-first vertical-module migration): Opened #142 (MEDIUM — incremental `beadloom reindex` does NOT refresh import edges: after moving a file and adding a boundary-violating import, `reindex` prints "Imports: 0" and the `code_imports`/`depends_on` edges are stale, so `beadloom lint --strict` does NOT catch the fresh violation — the documented `reindex && lint` loop silently passes a real boundary break. `reindex --full` is required to re-derive import edges; only the full CI build catches it. Sibling of #112 (incremental `Symbols: 0`). Impact: `forbid_import`/layer rules give false-green during iterative dev; a boundary violation can slip through local pre-commit and only surface in CI. Fix: incremental reindex should re-extract imports for changed files, or `lint` should warn when import edges are staler than the working tree. **🔴 SEVERITY UPGRADE MEDIUM→HIGH (2026-07-28, confirmed in the wild): if pre-commit AND pre-push AND CI all run the INCREMENTAL path, a real `no-dependency-cycles`/`forbid_import` violation reaches the protected main branch with a fully GREEN gate — observed a module-cycle merged undetected across a whole PR, surfaced only later by a manual `reindex --full` on a downstream branch. The "green CI" guarantee is unsound while any gate stage uses incremental reindex. Fix priority: the Gate (`ci`) MUST full-reindex before `lint`, or lint must refuse to pass on a stale import graph.**). Total 141→142, Open 31→32.

- **2026-07-02** — (dogfood — DDD project, detailed-graph + AaC-rules foundation): Opened #139 (MEDIUM — `docs generate` writes STRAY files to the project ROOT: running it produced a root-level `architecture.md` + a root `domains/` dir with layer READMEs, alongside the correct `docs/**` output — a cwd/base-path bug that pollutes the repo root and shadows the real `docs/architecture.md`), #140 (HIGH — misleading remediation for `untracked_files` staleness: `sync-check`/`ci` tells the operator to run `beadloom sync-update <ref>`, but for a directory-source node with a freshly-generated skeleton there is no `sync_state` pair, so `sync-update` returns "No sync pairs found; nothing to re-baseline" and CANNOT clear it — `untracked_files` is a per-file coverage gap, not hash drift; the only fixes are file-level `# beadloom:feature=` annotations or `<!-- beadloom:track= -->` doc markers, which the remediation string never mentions → operator dead-end. Also: a linked EMPTY skeleton then fails on `missing_modules`, so `docs generate`'d skeletons cannot pass `beadloom ci` until hand-filled — generating+linking a skeleton makes the Gate RED with no green intermediate state), #141 (LOW — `docs generate` re-serializes/patches `.beadloom/_graph/services.yml` as an unprompted side-effect, writing outside its docs output dir). Total 138→141, Open 28→31.

- **2026-07-02** — (dogfood — DDD project docs audit): Opened #138 (MEDIUM — `docs generate` silently no-ops on a coarse graph: a project accumulated a ~4000-line `architecture.md` / ~100 sections because its graph had few nodes w/ blanket `beadloom:domain=` tags → 0 feature/component nodes → nothing to emit, exit 0, no warning; + `component`→`DOC.md` not generated (parity gap w/ feature SPEC); + no monolith-drift detector). Total 137→138, Open 27→28.

- **2026-06-18** — (dogfood — adopter flow re-init on a binary-asset, non-English project): Opened #135 (HIGH — `init` crashes with `UnicodeDecodeError` on binary/venv files), #136 (MEDIUM — scaffolded flow is English-only + templates not overlay-aware), #137 (LOW — cross-major flow re-init leaves orphaned/skipped command files). Total 134→137, Open 24→27.

- **2026-06-15** — (BDL-056/057 + v2.1.0 release): CLOSED #130 (rule-type dataclass names fixed in `architecture.md`, BDL-057 SPEC-fill), #131 (all sub-items fixed in v2.1.0: `--non-interactive` removed from getting-started, DDD domain count corrected, CONTRIBUTING `your-org`→`zoologov` + release section added), #121 (RU `docs audit` false positive now suppressed via `.beadloom/config.yml` `docs_audit.ignore` — BDL-057.6; root-cause classifier weakness tracked in ROADMAP P3 "Semantic docs audit"). Opened #132 (`setup-agentic-flow --force` in Beadloom's own repo corrupts the vendored `CLAUDE.md` `__BEADLOOM_PROJECT_NAME__` placeholder) and #133 (per-worktree `beadloom.db` baseline → mass false re-baseline when integrating parallel worktree waves; relates #118). Total 131→133, Open 24→23, Closed 84→87.

- **2026-06-10** — (BDL-047 / F4.1 AI tech-writer): CLOSED #106 (non-interactive `sync-update --yes`/`--all` — the F4.1 fixpoint primitive, W1), #112 (incremental reindex `symbols_indexed` now backfilled to the live DB total per #88), and #127 (the `doc_generator.py` `except sqlite3.OperationalError: pass` swallows are gone — note `git_activity.py:251` `except ValueError: pass` + the broader onboarding `Any` concentration remain, deferred). Total 131, Open 27→24, Closed 81→84.

- **2026-06-04** — (post-v1.10.0 ROADMAP revision): Opened #122–#131 — engineering/test/doc debt from the comprehensive product review (`archive/REVIEW-2.md` §2/§3/§4), spot-verified at HEAD. Tracked here; cross-referenced from `ROADMAP.md` (Technical debt section). Total 121→131, Open 17→27.

- **2026-06-02** — (BDL-045): Opened #121 (LOW — `docs audit` metric classification is English-keyword-based, so it mislabels numbers in non-English docs: `README.ru.md` "14 инструментов" (MCP) is reported as `cli_command_count 14→34`, a false positive — the English README's same "14" is correctly `mcp_tool_count` OK. The number is right; the classifier just can't read Russian. Either localize the keyword map or skip non-English files in the audit). Total 120→121, Open 16→17.

- **2026-06-02** — (BDL-043 fix): CLOSED #120 — `dashboard.data.json` 404'd on GitHub Pages (widgets blank): the generator wrote it to the VitePress srcDir root (`site/`), which VitePress does NOT copy to the built `dist/` (only `site/public/` is copied verbatim); the dev server masked it by serving srcDir. FIXED: emit to `site/public/dashboard.data.json` → copied to dist root → the widgets' `withBase("/dashboard.data.json")` fetch resolves in the static build. Another "works in dev, breaks in the static build" class (cf. the F4 dead-links + F4.4 mermaid render) — the dogfood must hit the DEPLOYED/built site, not just `docs:dev`. Total 119→120, Closed 80→81.

- **2026-06-02** — (BDL-041 F4.4 BEAD-05): VERIFIED #117 (dogfood SUCCESS — F4.4 render fixes: the two F4 Mermaid bugs are fixed and the generation-time guard passes the real 26-diagram site with 0 issues; `npm run docs:build` exit 0; dashboard mounts the 4 ECharts widgets via `<ClientOnly>` with honest text fallback; `dashboard.data.json` carries `trends` (2 real points, sparse-honest) + 7 `recommendations`; automated render-validation green (build exit 0, no page-HTML error markers), live UX pan/zoom + charts PENDING owner re-check in-browser on the fixed site). Opened #118 (process: parallel dev subagents in a SHARED working tree don't conflict on disjoint *files* but DO collide on the pre-commit *hook* — it lints the whole tree, so one agent's commit catches the other's in-progress WIP; BEAD-02 had to `--no-verify` staging only its `site/**`. Mitigation: use git-worktree isolation for true parallel, or run dev beads sequentially; `merge-slot` serializes *who* commits but does not isolate tree state). Opened #119 (LOW: `graph` domain now 202 symbols > 200 `domain-size-limit` — non-blocking warning; F2/F3/F4 grew it via contracts.py/sdl.py/site_mermaid_guard.py etc.; candidate future split). Total 116→119, Open 14→16, Closed 79→80.

- **2026-06-02** — (BDL-040 F4 BEAD-05): Dogfood — generated + built Beadloom's own VitePress site. CLOSED #113 (generator bug: `publish_docs` copied hidden/OS-junk like `docs/.DS_Store` into `site/docs/` — non-deterministic + pollution; FIXED: skip dot-prefixed path parts; RED→GREEN regression test). CLOSED #114 (lockfile: `site/package-lock.json` now committed → `npm ci` reproducible). CLOSED #116 (generator bug surfaced by the dogfood build: node-page doc links + `/docs/` nav target were dead in the built site — FIXED by rooting doc links at `/docs/` + emitting a generated `site/docs/index.md` landing page; node-free dead-link guards added; `npm run docs:build` now exit 0, no `ignoreDeadLinks`). VERIFIED #115 (dogfood SUCCESS — 57 files, honest-by-construction dashboard matched `beadloom ci`, build green). Total 115→116, Open 15→14, Closed 77→79.

- **2026-06-02** — (BDL-039 F3 BEAD-09): Opened #112 (incremental reindex displays `Symbols: 0` — per-run delta, not backfilled like nodes/edges per #88; cosmetic, zero gate impact). Total 111→112, Open 12→13.

- **2026-06-02** — (BDL-039 F3 BEAD-06): VERIFIED #109 #110 #111 (dogfood SUCCESS — the F3 gate BLOCKS all three break-classes: boundary violation, cross-service BREAKING, drifted agent-config — each with a non-zero exit + agent-actionable output). Committed anonymized fixtures under `tests/fixtures/f3_gate/`. See Closed §BDL-039. Total 108→111, Closed 73→76.

- **2026-06-01** — (BDL-038 F2 BEAD-08): VERIFIED #107 (live GraphQL contract mismatch caught before ship — the F2 success criterion) + #108 (paradigm-agnostic FSD round-trip + external native modules + nested company-landscape). See Closed §BDL-038. Closed 71→73.

- **2026-06-01** — (BDL-038 F2 BEAD-01): Opened #105 (domain doc re-stales against all member files when one file is added) + #106 (no non-interactive `mark_synced` CLI). Open 10→12.

- **2026-06-01** — (BDL-037 F1): CLOSED #100 #101 #102 #103 (federation dogfood findings — FIXED in BEAD-09, commit d48bfeb) and #104 (federation dogfood SUCCESS — VERIFIED, BEAD-05). See Closed §BDL-037. Open 15→10, Closed 66→71.

- **2026-05-30** — (BDL-036 Phase 0): CLOSED #91 #88 #92 #93 #94 #86 #89 #90 #71 #98 (honesty gate — see Closed §BDL-036). Opened #99 (repo-wide doc refresh — sync-check has ~30 pre-existing stale doc pairs unrelated to Phase 0; the sync-check *mechanism* is now honest, the doc *content* needs a dedicated pass). Still open: #72, #73, #95, #97 (external), #99. Exact category recount folded into #99.

- **2026-05-28** — : added #91–#96 from the comprehensive architecture/code review (see `.claude/development/REVIEW.md`); refined #88 root cause.

</details>
