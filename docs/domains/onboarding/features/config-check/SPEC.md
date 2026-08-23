# Config Check (AgentConfigAsCode)

Drift detection for generated agent-config artifacts, in the onboarding domain.

**Source:** `src/beadloom/onboarding/config_sync.py`

---

## Specification

### Purpose

Treat the agent-config artifacts that Beadloom generates as code: detect drift
between the generated output and the committed files, and re-render them on
demand. This is the `config-check` step in `beadloom ci` and the seam behind
`--fix`.

### Owned artifacts

`check_config_drift` regenerates each managed artifact in memory and diffs it
against disk, returning one `ConfigDrift` per drifted artifact, sorted by path:

- `.beadloom/AGENTS.md` — fully generated, with a preserved `custom` block
  between the `beadloom:custom-start` / `custom-end` markers.
- the auto-managed sections of `.claude/CLAUDE.md` — between the
  `beadloom:auto-start` / `auto-end` markers.
- the thin IDE adapter files (`.cursorrules`, …).
- the **body** of `.claude/CLAUDE.md`, the `.claude/commands/*` files and the
  `.claude/agents/*` adapters — each against its **composition result**, not
  against fixed bytes (BDL-061 S3).
- `.beadloom/flow.yml` itself (unknown tool / architecture / stack / language,
  a suppression missing its reason or exit condition).

A repo that never adopted the flow is never reported for it. A repo that DID
adopt it and is missing a canonical file is reported, because the gate is not
satisfied by having less to check (see *Deletion is not a pass*).
`apply_config_fixes` is the `--fix` seam: it runs every writer
(`refresh_claude_md`, `generate_agents_md`, `setup_rules_auto`,
`refresh_agentic_flow_files`, `refresh_composed_adapters`) and reports what
changed — see *`--fix` may only rewrite what Beadloom wrote*.

### The composition result, not file bytes

Byte-guarding a generated file against a fixed template makes extension
impossible: any project addition is drift and `--fix` deletes it, which is what
BDL-UX #139 and #152 record. Comparing against the *composition* — CORE + the
`flow.yml` overlays + the project layer in `.beadloom/flow/` — keeps both
properties at once: a project extension is part of the expected output, while a
change to a shipped fragment still differs from it and is reported.

### What was NOT checked before, measured

The `CLAUDE.md` **body** was verified by nothing. `_claude_md_drift` diffed only
the marker-bounded auto-regions, so on a freshly scaffolded project: appending a
project-local paragraph returned `[]`; deleting the whole of section 7 returned
`[]`; replacing the entire file with the single line `# gone` returned `[]` —
and the Gate printed `config-check PASS: agent-config in sync` over it
(BDL-UX #177, #178's shape on a second surface).

### States and severities

`_state_drift` maps the flow-manifest classification onto a severity, because a
check that prints one word over several situations is the failure this epic
exists to remove:

| state | severity | what happens |
|-------|----------|--------------|
| `clean` | — | no finding |
| `stale` | `error` | recompose (`beadloom setup-agentic-flow`) |
| `hand_edited` | `error` | reported, **never rewritten** — `--fix` declines it by name; the message names `.beadloom/flow/<kind>/<name>.md` |
| `missing` | `error` | Beadloom composed it and it is gone — restore with `beadloom setup-agentic-flow` |
| `unverified` | `warn` | nothing accounts for it (no manifest, no provenance stamp), so a hand edit cannot be told apart from an upgrade — reported, does not block, and `--fix` declines it |

`unverified` is a warning so that no adopter's green project turns red on
upgrade. `hand_edited` stays an error because the drift-guard's job did not
change; only its remedy did — `--fix` moves nothing and deletes nothing, it
tells you where the edit belongs.

It is worth stating the other direction, which the original rationale did not:
`unverified = warn` also turns some projects **green**. A repo that hand-edited a
role file before this release has no manifest entry for it, so what used to block
now warns. That is the trade `--fix`-no-longer-restores buys, and BDL-061 `.57`'s
manifest-presence rule largely closes it — once a project has a manifest at all, a
file missing from it is not "pre-manifest", it is unaccounted for.

### A DOWNGRADE ACROSS AN UPGRADE IS ITSELF A FINDING

The constraint this project has always stated runs one way: *no adopter's green
project turns red on upgrade*. The inverse was never written because nobody
expected to need it, and then review `.11` measured it happening. Both
directions now hold, and the second is the sharper of the two:

> **An upgrade that WEAKENS a verdict is worse than one that strengthens it.** A
> red is loud and the adopter correlates it with the release. A downgrade is
> silent — a project that was correctly failing now passes, nobody is told, and
> the evidence that it ever failed is gone.

So a severity Beadloom reduced *for want of evidence* is a finding in its own
right. Every such finding carries `ConfigDrift.weakened_from` — the severity it
would have had if the evidence existed — and the command prints, on the passing
path as well as the blocking one:

```
  This pass is WEAKER than it would be: N finding(s) are `warn` only because
  Beadloom cannot prove what it wrote — each would be an `error` with the
  evidence. A verdict that got quieter across an upgrade is a finding, not a pass.
    -> restore `.beadloom/flow-manifest.json` (re-run `beadloom setup-agentic-flow`)
       to get the blocking verdict back.
```

Two properties of the mechanism are deliberate. **The exit code does not
change** — a `warn` must not block, or fixing the silence would itself be the
red-on-upgrade this whole section exists to prevent; what changes is that the
reduction is stated, counted and given a remedy. And **nothing is recorded**:
the downgrade is computed from the finding's own state rather than from a stored
history of past verdicts, because `config-check` writing on every run to keep
such a history would be BDL-UX #147/#189 all over again in the one command whose
job is to look without touching.

Set on: an `unverified` composed body, an `unverified` artifact state, a missing
file no manifest accounts for, and an absent or unreadable manifest. Not set on
`stale`, `hand_edited` or `missing` — those are errors on their own evidence.

### `--fix` may only rewrite what Beadloom wrote

The table above says a hand-edited file "will NOT be rewritten", and the check
prints that sentence. Until BDL-061 `.59` it was false for exactly the file it
was printed about: `refresh_composed_adapters` called `generate_adapters`
unconditionally, so `--fix` restored the composed body byte-for-byte and the
re-check then printed `Agent-config in sync — no blocking drift` at exit 0,
mentioning nothing. Measured on this repo and on `main`: `77dfc84f…` →
`f40b584e…` (the edit) → `77dfc84f…` (gone).

The destruction pre-dated the slice; the **promise** did not. Before S3, `--fix`
overwrote silently and claimed nothing. A reader who trusts the sentence is
exactly the reader who runs `--fix` feeling safe, so the sentence is now the
behaviour:

- `--fix` rewrites an adapter only when its state is `clean`, `stale` or
  `missing` — bodies Beadloom can prove it wrote. `hand_edited` and `unverified`
  are **declined**, named in the output with the reason, and left byte-identical.
  A preserved path is not recorded in the flow manifest either: recording a
  digest we did not write would make the next run believe the edit was ours.
- `unverified` is declined for the stronger reason — there we cannot even tell
  whose the body is. Its own remediation says *review it, then
  `setup-agentic-flow --force`*: a deliberate act by somebody who has looked.
  `--fix` has not looked. It matters because `unverified` is a `warn`, so
  overwriting one would have destroyed content and then reported "no blocking
  drift" at exit 0, with no red anywhere to catch it.
- **Say what it did.** `apply_config_fixes` digests the artifact surface before
  and after the writers run and reports the difference, so the run names every
  file it created or rewrote (and the summary line carries the count) rather
  than trusting each writer's account of itself — several over-report, and #186
  is a case of the output being believed over the bytes. The surface is
  enumerated from the artifact names, so a file the run *creates* is in frame;
  `.beadloom/flow-manifest.json` is deliberately out of frame as Beadloom's own
  record of its writes rather than authored content.
- `ConfigDrift.fixable` stops the closing advice offering `config-check --fix`
  for a finding it will decline — doing what the last line said used to undo what
  the line above it promised.

One consequence had to be fixed first, and it is measured rather than argued: on
a repo scaffolded **before** it adopted a `flow.yml`, all four `.claude/agents/*`
read `hand_edited`, because `_scaffold_vendored` wrote those bytes and never
recorded a digest (probe: `fsd`+`vuejs` → four hand-edits on files nobody
touched; `ddd`+`python` reads `clean` only by coincidence, since the vendored
bytes *are* that composition). Declining those would mean `--fix` refusing for
ever to recompose files Beadloom itself wrote — the mirror of the defect. The
plain vendored body is therefore offered as an `alternate`, so it classifies
`stale` and recomposes. **Unowned is not the same as somebody's only copy.**

### Deletion is not a pass

Three deletions used to make this check quieter rather than louder, each measured
on a scaffolded temp project with the same hand edit throughout (BDL-061 `.10`,
review `.11` MAJOR 2 and MAJOR 3). All three are findings now:

| deletion | before | now |
|----------|--------|-----|
| `rm .beadloom/flow-manifest.json` | error → warn, exit 1 → 0 | still `hand_edited`/error: the artifact's own provenance stamp accounts for it, and the absent manifest is separately reported `unverified` |
| …and the `<!-- beadloom:composed` line too | 0 findings | the body cannot be *judged* — ownership is unprovable — so it is reported `unverified`/`warn`, by name, plus the missing manifest |
| `rm .claude/agents/dev.md` | every OTHER file stopped being checked, silently | the others are still checked; the deleted file is its own `missing` finding |
| `rm .claude/CLAUDE.md`, manifest intact | 0 findings | `missing`/`error`, like the other two kinds |
| a manifest that is present and usable but does not mention `.claude/CLAUDE.md` | 0 findings, nothing in the output near the file | `unverified`/`warn`, by name |

`_flow_scaffold` replaced an all-or-nothing precondition that had no `skip`
verdict — CONTEXT: "a guard that silently does not apply is indistinguishable
from one that passed". Adoption still needs positive evidence (a manifest entry,
or a `flow.yml` beside at least one canonical file, or the full scaffold), so a
project with one stray file is never told it is missing eight.

The last two rows were found by the coordinator probing `.57`'s own claim to have
closed the first three, and they are the reason the rule is stated as *nothing an
editor deletes makes the check quieter* rather than as a list of three deletions.

#### The honest floor, stated because it is a limit and not a plan

Even after all of this, deleting the manifest **and** stripping the provenance
stamp downgrades the `CLAUDE.md` body from `error` to `warn`. That is not an
oversight to be fixed later: every ownership signal available is *in band* — it
lives in the repository the editor is editing — so any of them can be deleted.
The achievable floor is that the deletion is **visible** and the file is **named**,
not that it blocks. Raising it further needs a signal outside the repo, and
Beadloom has none and is not going to invent one.

The three composed kinds answer alike in that degraded state — `CLAUDE.md`, the
agents and the commands each read `unverified` at `warn`. That symmetry is pinned
by a test, because the defect it replaced was exactly one of the three going quiet
while the other two spoke.

### The project layer is named, not judged

Overlays are append-only in **bytes**: nothing under `.beadloom/flow/` can delete
core text. They are not append-only in **effect** — a fragment may contradict a
core rule in plain prose ("ignore section 0; do not run `beadloom ci`") while the
declared route for standing a rule down (`overlays.suppress`) demands a reason, an
exit condition and a notice. Whether a fragment contradicts the core is not
decidable, and this check does not pretend it is: "Pair on migrations" and "Do NOT
run `beadloom ci`" are indistinguishable to any checker.

What *is* decidable, and was missing, is that a project layer is in effect at all.
`config-check` now reports it at `warn`, naming each fragment, so a green verdict
is not read as covering text nobody judged. That is CONTEXT's own standard — "new
checks ship as `warn` and name what they did not verify" — applied to the
composer's input.

### Suppression liveness

An `overlays.suppress` entry that names a rule appearing nowhere in the composed
flow, or whose `until:` date has passed, is reported at `warn`. See the
flow-suppression SPEC; the deadline logic is `exit_condition_deadline`, shared
with the `rules.yml` import exemptions rather than restated.

### Ownership boundary

The `CLAUDE.md` body is **judged** only when the file is Beadloom's: it has a flow
manifest entry, or it carries the `<!-- beadloom:composed` provenance stamp the
shipped core begins with. A project's own hand-written `CLAUDE.md` is not ours
to police — the same boundary `_is_beadloom_adapter` draws for IDE adapter
files, and the reason the BDL-UX #73 false-positive class does not return.

Not judged is not the same as not mentioned. When neither signal is present in a
project that **did** adopt the flow (`_flow_scaffold(...).adopted`), the file is
reported `unverified` at `warn` and named — silence there was the check falling
back to permissive at exactly the moment it lost its evidence. It is `warn` and
not `error` because `scaffold()` deliberately refuses to overwrite a pre-existing
`CLAUDE.md` it did not write (it emits a migration note instead), so an adopter
can genuinely have adopted the flow while owning that file, and calling it
hand-edited would be the false red on upgrade this slice exists to prevent.

A project that never adopted the flow is still not policed and not mentioned —
adoption is what separates "no stamp, and this is your file" from "no stamp, and
this is a file we should be able to account for".

## Invariants

- User-authored `custom` blocks and prose outside the managed markers are
  preserved across regeneration.
- An absent target is not drift **unless the project adopted the flow**: then it
  is `missing`, because "the role protocol is gone" and "the role protocol is
  intact" must not print the same word.
- Nothing an editor can delete makes this check quieter. Ownership rests on two
  independent signals (the manifest and the artifact's provenance stamp), and the
  absence of either is itself reported.
- `--fix` never destroys content while reporting success. It rewrites only bodies
  Beadloom can prove it wrote, and every file a run changes is named in that
  run's output. A destructive act that reports success is the same class as a
  check that reports clean without checking (BDL-UX #172/#174/#175), and worse,
  because those only misinformed.
- The remedy a finding offers is a remedy that applies to it: `--fix` is never
  named as the fix for a finding `--fix` declines.
- Composition is a function of its inputs and of nothing else — no clock, no
  ambient state. That is what licenses checking against a composition rather than
  against stored bytes.
- The generator derives everything from the on-disk graph (`rules.yml`) and
  project metadata; the `conn` parameter exists only for signature symmetry with
  the gate orchestrator.

## API

Module `src/beadloom/onboarding/config_sync.py`:

- `check_config_drift(project_root, conn) -> list[ConfigDrift]` — report every
  drifted artifact, sorted by path.
- `ConfigDrift` — `file` (project-relative path), `reason` (agent-actionable
  explanation), `severity` (`error` blocks the Gate, `warn` does not),
  `remediation` (the concrete next move, or `None` for the caller's generic
  advice) and `fixable` (whether `--fix` can repair it; `False` when repairing
  would mean deleting the body on disk).
- `apply_config_fixes(project_root) -> FixReport` — run every `--fix` writer and
  report, by measurement, what changed.
- `FixReport` — `rewritten`, `created` (measured against the disk) and `declined`;
  `.changed` is the union of the first two.
- `DeclinedRewrite` — `file`, `reason`, `remediation` for one refusal.
- `refresh_composed_adapters(project_root) -> AdapterRefresh` — re-render the
  composed role adapters, minus the ones it declines (`rewritten` + `declined`).
- `refresh_agentic_flow_files(project_root) -> list[str]` — recompose the
  scaffolded flow files through the scaffold's own non-forcing path, so a
  hand-edited file survives `--fix`. Its list is the scaffold's self-report and
  includes files it re-read and left identical; `apply_config_fixes` measures
  instead of relying on it.

## Testing

Tests: `tests/test_config_sync.py`, `tests/test_flow_composition.py`,
`tests/test_cli_config_check.py`, `tests/test_s3_config_check_residual.py`
(the adversarial half), `tests/test_bead57_config_check_sight.py`.

## What is still not checked, measured

Stated here rather than only in a test file, because "new checks name what they
did not verify" applies to this one too. All eight of the blind spots `.10`
measured at `7d6221f` were closed by `.57`; what remains is the honest residue of
how they were closed:

- **A project fragment's prose is not judged** — only its presence is reported.
  There is no mechanism, and no proposal for one, that distinguishes a standing
  practice from a countermand.
- **Ownership of a `CLAUDE.md` still needs evidence.** Delete both the manifest
  and the provenance stamp and the *body* is no longer compared — named and
  reported `unverified` rather than silently passed, but not verified either, and
  therefore not blocking. See *The honest floor* above; this is a limit of
  in-band evidence, not a gap waiting on a bead.
- **A suppression is matched against headings**, so a core rule stated in body
  prose and never given a heading cannot be named by an `overlays.suppress` entry
  without reading as dead.
- **`.beadloom/flow/` is scanned for the fragments that compose**, so a file
  dropped there under a name nothing composes is inert and unreported.
