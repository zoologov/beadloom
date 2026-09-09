# Role Map

Checks that every role this flow composes is named in the document that enumerates
roles, in both directions (BDL-068 S6, `beadloom-0mdo.59`, BDL-UX #252).

**Source:** `src/beadloom/onboarding/role_map.py`

---

## Specification

### Purpose

Close one class: **a role that exists does not reach the document that lists roles.**
`Explore` shipped in BDL-068 S1 as a composed role and was invoked by `/coordinator` and
`/task-init`. Measured on 2026-09-09 before the fix: the role template existed, the two
slash-command templates named `explore` four times each, `.claude/agents/explore.md` was
composed — and the shipped `CLAUDE.md` template and this repository's composed copy of it
named it zero times. Its section 0.0 draws the role map and its section 4 is the Agent
Roles table, and both listed four roles while five were composed. An agent reading the
entry point, as that document instructs, learned that the fifth did not exist.

### It is the third direction of the same graph

`role-duties` built the edge for BDL-UX #228: *a duty declared for a role does not reach
that role's core*, checked both ways. This is the neighbouring edge one level up: *a role
that exists does not reach the document that lists roles*. It was never built because
nobody had added a role since the map was written. `Explore` is the first new role in this
flow's life and exposed the gap by being the first thing that could.

`config-check` already **counted** `explore` — it printed `On disk: 5 role file(s)` — and
answered two other questions with it: composed adapters against the compositions this flow
would write, and whether a declared duty reaches the composed core of every role it names.
Neither asks whether a composed role is named in the map.

### The population is derived, never listed

The roles come from `ROLE_NAMES`, which `role-composer` derives from the shipped CORE
fragments over a shape: a fragment is a role when its front matter names its own file.
`templates/roles/core/` also holds `_landing`, `_rooms`, `_tracker` and `_writing` and
their `.ru` localisations, and a directory listing would read all of them as roles.
Dropping a sixth `<name>.md.txt` into that directory therefore makes the sixth role appear
in this check by the same act that makes it appear in every other reader.

### A name is read as a role only inside a construct that designates one

A bare word search would read `test` in "Committing with failing tests" and `review` in
"0 required reviews" as roles — the keyword-proximity class this project has filed three
times (BDL-UX #190, #205, #209). Two kinds of construct are read, and they carry different
weight because they were written with different intent.

| Kind | Shapes | Weight |
|---|---|---|
| designation | `subagent_type: <names>`, `agents/<name>.md`, `agents/{<names>}.md` | claims each name IS a role |
| inferred roster | a run joined by `·`, or a run of backticked names joined by `,` or `\|` | a guess about punctuation |

An inferred roster is recognised only when it already names **two** composed roles. That
threshold is what makes the shape safe to infer: a run of backticked words is ordinary
markdown, and only one that already enumerates part of the population is plausibly
enumerating all of it. Backticks are required for the comma form, because without them
`Types: feat, fix, refactor, docs, test, chore` reads as a roster. Only `|` joins a
`subagent_type` run, because a comma swallows `, run_in_background=True` and reports `run`
as a role this flow does not ship.

### The three findings

`role_map_report(project_root)` composes `CLAUDE.md` for the project's `flow.yml` plus its
project layer, reads both construct kinds out of each **fragment** (so a finding names the
file and line to open rather than the artifact the text ended up in), and reports one
finding per role, naming every site.

| Kind | Fires when | Severity |
|---|---|---|
| `unmapped` | a composed role no construct in the map names | `error` |
| `partial` | a composed role omitted from a roster that names two other composed roles | `error` from a designation, `warn` from an inferred roster |
| `unbacked` | a name a **designation** claims is a role and no CORE fragment ships | `error` |

`unbacked` is never raised from an inferred roster. A punctuated run's other tokens are
ordinary words, and reporting them would turn an adopter's ``we deploy to `dev`, `staging```
into a release-introduced error in their own prose. The same reasoning sets `partial`'s
severity from the kind of roster that omitted the role.

### The limit, stated in the output

`RoleMapReport.not_judged` names every line that mentions two or more roles in a shape no
construct reads. Some of them should enumerate every role and some should not — a wave
order `dev → test → review → tech-writer` names four roles and `Explore` is not a wave —
and this derivation cannot tell them apart, so it names them instead of deciding. Measured
on the shipped template after the fix: 16 designations, 6 of them rosters, and 5 not-judged
lines. It prints on a clean run too, because a check that speaks only when it finds
something hands the reader a clean list, and a clean list is trusted and stopped at.

The corpus is `CLAUDE.md` and nothing else. A role named in a slash command and absent from
the map is outside this check and inside `role-duties`, which reads every composed
artifact.

### Modules

- **role_map.py** — `role_map_report()`, `RoleMapReport`, `RoleReference`,
  `RoleMapFinding`, `UnjudgedLine`.

The `roles` keyword argument is the only seam. It defaults to the derived population, which
is the value production passes; a caller varies it to ask the question of a population
other than the running flow's, which is how the check is demonstrated red on a sixth role
without writing a sixth fragment into a templates directory every concurrent run in the
same working tree also reads.

### Where the findings surface

`config_sync._role_map_drifts()` maps every finding to a `ConfigDrift`, so they ride the
same channel as the rest of the agent-config drift. They are never `fixable`: the repair is
a sentence in the map, and `--fix` writes compositions rather than prose. Offering it would
be the BDL-UX #186 shape — recommending the command that will decline.

`beadloom config-check` prints the corpus it read and the not-judged population on every
run of a project that has a `flow.yml`.

## Acceptance

`tests/acceptance/features/role_map.feature` — both directions, the prose that is not a
designation, the severity split between a designation and an inferred roster, the
not-judged population, the finding reaching `config-check`, and the shipped flow's own map
checked against the roles it composes.

## Related

- `role-composer` — `ROLE_NAMES` and `roles_in`, the derived role population this check is
  the map's side of
- `role-duties` — the two directions one level down: a duty declared for a role against
  that role's composed core
- `flow-composer` — `compose()`, whose `Composition.fragments` supply the provenance every
  finding's site comes from
- `config-check` — the channel the findings block through
