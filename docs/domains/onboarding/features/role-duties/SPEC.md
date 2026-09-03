# Role Duties

Checks that a duty declared for a role is carried by that role's composed core,
in both directions (BDL-068 S4, `beadloom-0mdo.27`).

**Source:** `src/beadloom/onboarding/role_duties.py`

---

## Specification

### Purpose

Close one class, stated as narrowly as the evidence supports: **a duty an agent is
obliged to perform is written somewhere the performer does not read.** It was measured
four times across two epics before it was named. The clean-room rule lives in the
coordinator's prose and in the wave planner, and occurs zero times in the role cores the
roles receive; every agent said the right words because the coordinator typed them into
every launch prompt.

Three sub-shapes were read as one finding four times, and the distinction decides what is
checkable. This feature covers **only the first**: the duty does not reach the performer.
The second (the duty reaches the performer and nothing can check performance) is
`mutation-scope` plus the mutation runner; the third (a guarantee stated over one channel
and defeated by another) is `review-brief`'s reachability report. A check built over all
three would be a check over nothing.

### Duties are declared, never inferred

A detector that read English role prose looking for obligations would repeat a class this
project has filed three times: the docs-audit keyword-proximity classifier binds
"supports 11 languages" to a count of the languages the project is *written* in
(BDL-UX #205), reads a version cited as an example as a claim (#190), and verifies nothing
in a non-English document while counting it scanned (#209).

So a duty carries a marker, exactly the way a scenario carries `@bead:` and `@node:`:

| Marker | Written in | Means |
|---|---|---|
| `<!-- beadloom:duty=<id> roles=<a,b> -->` | any composed flow artifact | this duty is owed by these roles |
| `<!-- beadloom:carries=<id> -->` | a fragment that composes into an artifact | this text is that duty |

Both ids are matched exactly. A near spelling is two findings — undelivered and
undeclared — rather than a silent pass.

### The four findings

`duty_report(project_root)` composes every agent-addressed artifact for the project's
`flow.yml` plus its project layer, reads both marker kinds out of each **fragment** (so a
finding can name the file to open rather than the artifact the text ended up in), and
reports:

| Kind | Fires when | Analogue |
|---|---|---|
| `undelivered` | a duty is declared for a role whose composed core carries no `carries` marker for it | a node carrying no scenario |
| `undeclared` | an artifact carries a duty no composed artifact declares | — |
| `unknown-role` | a declaration names a role no CORE fragment ships | a scenario naming a dead node |
| `malformed` | a `duty=` marker carries no `roles=` list, so it names no performer | — |

Carriage is recorded for **every** composed artifact, not only the role files. Delivery to
a role is still judged against that role's own artifact, but a `carries` marker in a slash
command is a duty text somebody wrote, and dropping it because its artifact is not a role
would be this check committing the class it exists to report.

### The limit, stated in the output

A duty carried only by a coordinator's launch prompt is unreachable by any file-based
check, because **a prompt is not an artifact**. This check covers composed artifacts and
nothing else, and `DutyReport.not_inspected` says so on every run — clean or not, because a
check that speaks only when it finds something hands the reader a clean list, and a clean
list is trusted and stopped at. That limit is the argument for moving a duty out of the
prompt and into a composed core, not a reason to leave it there.

Beside the launch prompt, `not_inspected` names every fragment that carries a duty marker
and that no composition read — another architecture's overlay, an unconfigured stack, a
project fragment for a role that does not exist. It is derived by **subtraction** from the
fragments the compositions actually read, so an overlay added later is covered without
anyone editing a list.

One class is excluded from the subtraction base: `templates/agentic_flow/agents/*.md.txt`,
the byte-identical vendored snapshot of the live `.claude/agents/*.md`. It carries every
marker its composed role carries, so it appeared five times over the moment a role core
first declared a duty (`beadloom-67t1`), under a reason saying the duties in it reach no
role — false twice, because the marker is inspected in its composed form and the file is
dropped verbatim into an adopter's roles directory by the plain scaffold path. Excluding
output is not the authored list this derivation exists to avoid; it is the derivation
declining to report its own input back to itself.

### Modules

- **role_duties.py** — `duty_report()`, `DutyReport`, `DutyDeclaration`, `DutyFinding`,
  `NotInspected`, and the two marker spellings `DUTY_MARKER` / `CARRIES_MARKER`.

### Where the findings surface

`config_sync._duty_drifts()` maps every finding to a `ConfigDrift`, so they ride the same
channel as the rest of the agent-config drift and block the Gate. They carry
`severity="error"` where a suppression finding warns, because the two differ in who can
introduce them: a suppression is an adopter's line in `flow.yml` and a release must not
turn their green project red, while a duty finding needs a `roles=` declaration somebody
wrote on purpose. Beadloom ships both sides of its own duties, so a mismatch introduced by
a release is caught by this repository's own Gate before it reaches anyone.

They are never `fixable`: the repair is the duty's **text** in a role core, and `--fix`
writes compositions, not prose. Offering it would be the BDL-UX #186 shape — recommending
the command that will decline.

`beadloom config-check` prints the not-inspected population whenever a project declares at
least one duty, and stays silent for one that declares none: there is no verdict to
qualify, and a standing paragraph about an unused mechanism is the noise that gets a check
switched off.

## Acceptance

`tests/acceptance/features/role_duties.feature` — both directions, the dead role, the
anti-vacuity case, the launch-prompt limit, the fragment no composition includes, and the
finding reaching `config-check`. Boundary guards in `tests/test_role_duties.py`.

## Related

- `role-composer` — the composition every check here reads, and `ROLE_NAMES`, the derived
  role population a declaration's `roles=` list is judged against
- `flow-composer` — `compose()`, whose `Composition.fragments` supply the provenance and
  the subtraction base for `not_inspected`
- `config-check` — the channel the findings block through
