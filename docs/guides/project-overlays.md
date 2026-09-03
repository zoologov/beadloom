# Project Overlays, Suppressions and Migration

<!-- beadloom:watches=cli,flow.yml -->

Every file the agentic flow puts in your repository — the five role protocols, the
four slash commands and `CLAUDE.md` — is **composed** from layers rather than copied
from a template. The last layer is yours.

This guide is for the person who has something to add to those files, or who already
added it by hand and now has to move it. It covers:

- what composes into what, and in which order,
- where a project's own text goes and what survives an upgrade,
- how to stand a shipped core rule down so the decision is named, dated and reported,
- migrating a hand-edited vendored file, step by step,
- three limits of the check, stated because they are limits and not omissions.

The mechanism is specified in the
[flow-composer](../domains/onboarding/features/flow-composer/SPEC.md),
[flow-suppression](../domains/onboarding/features/flow-suppression/SPEC.md),
[flow-manifest](../domains/onboarding/features/flow-manifest/SPEC.md) and
[config-check](../domains/onboarding/features/config-check/SPEC.md) SPECs. This guide
is the task-shaped view of the same thing.

## Why the layers exist

Until BDL-061 S3 the flow was vendored: `setup-agentic-flow` wrote a copy of Beadloom's
own files and `config-check` compared them byte for byte against the shipped template.
That left an adopting team with two options, both bad. Hand-edit a role file and the
drift-guard reported it and `--fix` deleted the edit (BDL-UX #139, #152). Leave it
alone and the flow said nothing about the project it was running in.

The shipped core also carried this repository's own text, because there was nowhere
else to put it — a bead id and a claim about Beadloom's branch protection reached
every adopter twice, the second time over the correction (BDL-UX #177).

Composition answers both. The shipped core stays stack-neutral and is verified; the
project layer is a separate file that composes after it and is never overwritten.
Measured on the shipped artifact by composing it: the core `CLAUDE.md` went from **440 lines
to 371**. A project composing `ddd` + `python` gets **401** back; a project composing neither
keeps the 371, and its critical rules name no Python tooling. S3 landed the core at 376 and
S3b removed five more lines, so the reduction is measured against the shipped template of the
day rather than quoted from the bead that first reported it.

## The four layers

`compose(kind, name, config, project_root)` concatenates, in a fixed order:

| # | Layer | Comes from | Optional |
|---|-------|-----------|----------|
| 1 | `core` | the shipped, stack-neutral fragment | no |
| 2 | `architecture:<a>` | one methodology overlay — `ddd` or `fsd` | yes |
| 3 | `stack:<s>` | each stack overlay named in `flow.yml`, **sorted** | yes |
| 4 | `project` | a file in your repository under `.beadloom/flow/` | yes |

Layers 1–3 ship inside the `beadloom` wheel and change when you upgrade. Layer 4 is
yours and never does.

Four kinds of artifact compose, and each has its own project fragment:

| kind | written to | your fragment |
|------|-----------|---------------|
| `roles` | `.claude/agents/<role>.md`, `.cursor/agents/<role>.md` | `.beadloom/flow/roles/<role>.md` |
| `commands` | `.claude/commands/<cmd>.md` | `.beadloom/flow/commands/<cmd>.md` |
| `claude` | `.claude/CLAUDE.md` | `.beadloom/flow/claude/CLAUDE.md` |
| `docs` | the skeletons `beadloom docs generate` writes | `.beadloom/flow/docs/<kind>.md` |

Role names are `dev`, `explore`, `review`, `tech-writer`, `test`. Command names are
`coordinator`, `task-init`, `checkpoint`, `templates`. Doc kinds are `overview`,
`domain`, `service`, `feature` and `beadloom-readme`.

`explore` arrived with BDL-068 S1.5, and the role population is no longer a list
anyone maintains. `role_composer.roles_in()` reads it out of the shipped
`templates/roles/core/*.md.txt` fragments over a shape — a fragment is a role when
its front matter names its own file — so dropping a fragment in makes the role
exist for every reader at once, including `config-check`, the scaffold and the
Cursor orchestrator pointer. The order is sorted, which is why `test` is last:
`ROLE_NAMES` was `('dev', 'test', 'review', 'tech-writer')` before and is now
`('dev', 'explore', 'review', 'tech-writer', 'test')`. A project that composed a
`.beadloom/flow/roles/<role>.md` fragment for the four keeps it. `explore` gets a
project layer the same way the others do, and a project that wants none composes
none.

### The docs layer does one thing the others do not

A section you append to a doc template becomes a **required section** of that doc
kind. Append this:

```markdown
<!-- .beadloom/flow/docs/domain.md -->
## Runbook

Who to page when this domain misbehaves.
```

and every domain README `beadloom docs generate` writes carries a Runbook
section — and `beadloom sync-check` reports a domain README that loses it, once
a majority of them carry it. There is one source of truth: the composed
template. Nothing else has to be told.

## Declaring your mutation scope

`flow.yml` also records which code a mutation run is supposed to cover. Beadloom
runs no mutants — the tool is yours to choose — and it checks two things about
what you declare: that the scope could run one, and, once your runner has
written its counters, what a run over that scope actually produced.

```yaml
# .beadloom/flow.yml
mutation:
  targets:
    - src/acme/pricing/
```

`beadloom config-check` reports a target that is outside your `scan_paths`, is
not on disk, or holds no file in a language you index. All three are warnings,
and all three describe the same failure: a mutation score computed over an empty
denominator reads as evidence of test strength and is evidence of nothing.
Declare nothing and nothing is reported.

[`beadloom mutation`](../services/cli.md#beadloom-mutation) is the other half,
and it asks those same three questions of the targets a run says it covered.
Until it did, the failure above was describable and not detectable from a score:
a declared target that had moved scored `100.0% of 10 scored mutants` and exited
0, because the command producing the NUMBER never asked whether the target could
have produced a mutant. It needs no particular tool installed — `--stats` names
whatever counters your runner wrote, read by name — and a counter it does not
find is reported rather than read as zero. Declaring a scope you never run is
therefore not silent either: each declared target is reported as measured by no
run.

## Declaring a wave override

`flow.yml` also records the human decisions that outrank `beadloom waves`, which decides
from the graph which beads may run at the same time:

```yaml
# .beadloom/flow.yml
waves:
  overrides:
    - beads: [proj-1, proj-2]
      decision: parallel        # or: serial
      reason: "the two touch one vocabulary module and nothing else"
      until: "2026-09-01"
```

Every key is required, and required by its content: a key present but blank is a
configuration error, on the same rule that governs a suppression. An override that changed
no decision is reported as inert. See the [Parallel waves guide](parallel-waves.md).

`.beadloom/flow/` is source, belongs in git, and is never covered by the ignore block
`beadloom init` writes. So does `.beadloom/flow.yml`, and so does
`.beadloom/flow-manifest.json` — the record of what Beadloom wrote, which is one of
the two signals that let `config-check` tell its own output from your edit.

## Adding your own rules

Create the fragment and recompose:

```bash
mkdir -p .beadloom/flow/roles
cat > .beadloom/flow/roles/dev.md <<'EOF'

---

## Project rules — Acme

- Every schema change ships with a reversible migration and a rollback note.
- Feature flags default to off; a flag with no removal date is a review block.
EOF

beadloom setup-agentic-flow      # recompose every artifact
beadloom config-check            # rc 0
```

Three things to know about the result:

- **The fragment is appended verbatim.** Beadloom does not reformat, summarise or
  reorder it. Start it with a horizontal rule and a heading if you want the seam to
  read cleanly.
- **It cannot delete core text.** Overlays are append-only in bytes: concatenation is
  the only operation, and every shipped fragment — 41 of them today — was measured to
  end with a newline, so a project layer cannot even rewrite the core's last line. The
  test is parametrised over whatever the package ships rather than over a written-down
  list, so a fragment added tomorrow is measured too. To stand a core rule down,
  declare it — see the next section.
- **A fragment named after nothing is inert.** `.beadloom/flow/roles/dev.md` composes;
  `.beadloom/flow/roles/devs.md` composes into nothing and is not reported. The
  scanner looks for the names that compose, so a typo is silent.

For a project writing in a language other than English, set `language:` in `flow.yml`
and each layer prefers a `<name>.<lang>.md.txt` fragment. A localisation that has not
shipped falls back to the default **and says so** in the composition notes rather than
falling back silently.

## Standing a core rule down

A project layer can contradict a core rule in prose, but nothing records that a
decision was made. When a core rule genuinely does not apply, declare it in
`.beadloom/flow.yml`:

```yaml
overlays:
  suppress:
    - rule: "Anti-patterns / Shell"
      reason: "the team runs on Windows; the -f idiom does not apply"
      until: "a windows stack overlay ships"
```

`rule`, `reason` and `until` are all mandatory — an entry missing any of them is a
configuration error, not a silently accepted one. An unknown key under `overlays` is
also rejected, with the reminder that project *additions* are files under
`.beadloom/flow/` and never keys here.

Every declared suppression is appended to **each** composed artifact as a visible
notice, so a reader about to follow the core rule is told it was stood down, why, and
what retires it. The core text itself stays in place, which is what keeps drift on it
detectable.

### `rule` is a heading path, matched against what *you* compose

Each `/`-separated segment must be named by a heading somewhere in your composed
corpus: `CLAUDE.md`, the four slash commands and the five role protocols.
`Anti-patterns / Shell` is matched by `### Anti-patterns (shell)`.

The corpus is *yours*, not Beadloom's. Measured on a scaffolded TypeScript project,
that same entry is reported as dead, because the shell anti-patterns live in the
**Python stack overlay** the project does not compose:

```
! .beadloom/flow.yml: the suppression of 'Anti-patterns / Shell' matches no rule in
  the composed flow — it stands nothing down, and is rendered into every artifact as
  a decision nobody can act on
  -> name the rule by its heading path, or delete the entry from `overlays.suppress`
```

Suppress the rule your project actually composes, and check with `config-check` after
declaring it rather than assuming the name matched.

### Expiry is reported, never written into the file

`until:` may name a date or an event. When it names a date and that date has passed,
`config-check` reports it at `warn`:

```
! .beadloom/flow.yml: the suppression of 'Git / Trunk-based development' expired on
  2026-08-01 and is still standing the rule down
  -> renew the `until:` with a new exit condition, or remove the entry
```

The composed **bytes** do not change when a suppression expires. That is deliberate:
an earlier version stamped `— EXPIRED` into the text at compose time, which made the
file a function of the wall clock. Measured by review: one dated suppression took an
untouched repository from 0 findings and exit 0 to **9 errors and exit 1** three days
later, under a reason naming three causes that had not occurred. A composed artifact
is now a function of its inputs and of nothing else, and expiry is a finding at check
time.

## Migrating a hand-edited vendored file

If you edited `.claude/agents/dev.md` or `.claude/commands/coordinator.md` under an
older release, `config-check` now names the file and the place the edit belongs:

```
- .claude/agents/dev.md: hand-edited: the body differs from the composition AND from
  what Beadloom last wrote. It will NOT be rewritten
  -> move the additions to .beadloom/flow/roles/dev.md (the project layer composes
     after the shipped core, survives upgrades and does not trip this check), then
     re-run `beadloom setup-agentic-flow`
```

The migration itself:

1. **Diff your file against the composition** to see exactly what is yours.
   `beadloom config-check` names the file; `git diff` against the commit that
   scaffolded it, or a scaffold into a scratch directory, gives the base to compare
   with.
2. **Copy your additions into the project fragment** — `.beadloom/flow/roles/dev.md`
   for a role, `.beadloom/flow/commands/coordinator.md` for a slash command,
   `.beadloom/flow/claude/CLAUDE.md` for the entry point. Copy the text, not the
   surrounding core.
3. **Remove the additions from the vendored file.** Until you do, the file is still
   hand-edited and still reported.
4. **Recompose:** `beadloom setup-agentic-flow`. Your fragment is now layer 4 and the
   body is Beadloom's again.
5. **Verify:** `beadloom config-check` should exit 0.

> **`config-check --fix` will not do this for you, and will not undo it either.** It
> declines to rewrite any adapter whose body Beadloom cannot prove it wrote, names the
> file under *Declined to rewrite*, and leaves the finding standing — so running it on a
> hand-edited role adapter is safe but changes nothing. Move the text into the project
> layer first, then recompose with `setup-agentic-flow`. (Until BDL-UX #186 was closed
> it recomposed the file unconditionally and the edit was gone, one line after the check
> printed *"It will NOT be rewritten"*.)

`setup-agentic-flow` without `--force` never overwrites a hand-edited file — it prints
`Skipped .claude/commands/<name>.md (hand-edited; use --force)` and leaves it alone.
`--force` overwrites it, so use it only once the edit is safely in the project layer.

### Files an older layout left behind

A layout before BDL-048 kept the role protocols in `.claude/commands/`. Those files
are superseded by `.claude/agents/`, and `epic-init.md` is superseded by
`task-init.md`. Beadloom computes the list and the exact `rm -f` command for each, and
**never deletes them itself** (BDL-UX #137).

At present that list does not reach you: `setup-agentic-flow` computes it and does not
print it (BDL-UX #188). Until that is fixed, remove them by hand after upgrading:

```bash
rm -f .claude/commands/dev.md .claude/commands/test.md \
      .claude/commands/review.md .claude/commands/tech-writer.md \
      .claude/commands/epic-init.md
```

## What an upgrade does

Upgrading `beadloom` moves layers 1–3. Your layer 4 does not move, and recomposition
puts it back in the same place:

- A composed file that you never touched is recomposed onto the new core. Before that
  happens, `config-check` reports it `stale` at `error` with the remedy
  `beadloom setup-agentic-flow` — the drift is named as *recomposable*, never as a
  hand edit.
- A file you *did* hand-edit is reported `hand_edited` at `error` and is not rewritten,
  including across the upgrade. The migration above is the way out.
- A file Beadloom recorded writing and that is now gone is `missing` at `error`.
- A repository that predates the flow manifest, and a file nothing accounts for, are
  reported `unverified` at `warn` — named, not blocking, because a project that
  genuinely cannot be judged should not go red for upgrading.

After upgrading, run:

```bash
beadloom setup-agentic-flow    # recompose onto the new core, keeping your layer
beadloom config-check          # rc 0, or a named finding per file
```

> **Known issue on a fresh scaffold.** `setup-agentic-flow` composes the role adapters
> from the stack it auto-detects but does not write a `.beadloom/flow.yml`, and
> `config-check` without one expects the plain vendored role files. Measured on a new
> TypeScript project: `config-check` exits 1 with four errors immediately after a
> clean scaffold. Writing a `flow.yml` — which every project adopting the flow wants
> anyway — takes it to rc 0. Filed as BDL-UX #187.

## Three limits, stated

### The project layer's prose is not judged

`config-check` reports that a project layer is in effect and names each fragment. It
does **not** read what the fragment says:

```
! .beadloom/flow: project layer in effect (1 fragment(s):
  .beadloom/flow/claude/CLAUDE.md). It composes AFTER the shipped core and cannot
  delete core text — but its prose is not judged, so a rule it contradicts is stood
  down without the reason, exit condition or notice `overlays.suppress` requires
```

That is a real hole in "the guard cannot be silently disabled" and it is not closable
by a checker. "Pair on migrations" and "Do NOT run `beadloom ci`" are the same to any
mechanism that does not understand English. What is decidable is that a layer is in
effect, so that is what gets reported, at `warn`, with each fragment named — a green
verdict must not read as covering text nobody judged.

`overlays.suppress` is the route that *is* checked: it demands a reason and an exit
condition, renders a notice into every artifact, and is reported when it expires or
matches nothing. Prefer it whenever a fragment stands a core rule down.

### Ownership evidence is in band, so the floor is visibility

The `CLAUDE.md` body is judged only when the file is Beadloom's — it has a flow
manifest entry, or it carries the `<!-- beadloom:composed` stamp the shipped core
begins with. Deleting the manifest **and** stripping the stamp downgrades the body
from `error` to `warn`.

That is a limit rather than a plan. Every ownership signal available lives in the
repository the editor is editing, so any of them can be deleted. The achievable floor
is that the deletion is **visible** and the file is **named** — not that it blocks.
Raising it further needs a signal from outside the repository, and Beadloom has none.

What did change: a deletion no longer makes the check *quieter*. An absent manifest is
its own finding, a deleted canonical file is its own finding, and one deletion no
longer switches the checks off for every other file. All three composed kinds answer
alike in that degraded state.

### Your `CLAUDE.md` states Beadloom's version, not yours

The `project-info` auto-region renders `- **Current version:** <n>` from the installed
`beadloom` package rather than from your project. Measured on a scaffolded project
whose `package.json` declares a version of its own: the whole `## 0.1 Project:` section
renders as a single bullet naming the installed `beadloom` release instead.

The renderer also derives its stack, test, lint and type-check facts from
`pyproject.toml` only, so a non-Python project gets that one bullet and it is false.
Treat the section as unreliable until BDL-UX #183 closes; the rest of the file does
not depend on it.

## See also

- [Agentic Dev Flow](agentic-flow.md) — the flow these files carry, and the guards.
- [flow-composer SPEC](../domains/onboarding/features/flow-composer/SPEC.md) — layers,
  kinds and determinism.
- [flow-suppression SPEC](../domains/onboarding/features/flow-suppression/SPEC.md) —
  the declaration and its liveness checks.
- [flow-manifest SPEC](../domains/onboarding/features/flow-manifest/SPEC.md) — the five
  states and why the manifest belongs in git.
- [config-check SPEC](../domains/onboarding/features/config-check/SPEC.md) — severities,
  the ownership boundary, and what is still not checked.
- [CLI reference](../services/cli.md) — `beadloom setup-agentic-flow`,
  `beadloom config-check`.
