# Executable Acceptance Scenarios (BDD)

<!-- beadloom:watches=cli,graph,flow.yml -->

This guide is for the person who has to state what a piece of work must do, and wants that
statement to be something a machine can execute rather than a checkbox somebody ticks.

It covers:

- the decision the mechanism rests on, and what it rules out,
- the shape of a scenario and how it binds to a bead and to a graph node,
- what `scenario-coverage` reports, in both directions,
- how to say that a piece of work has no behaviour, without saying nothing,
- what the rule does **not** check, and the numbers this repository ships with.

The reference material lives elsewhere and is not repeated here: the parser and the reference
syntax are in the [scenario-binding SPEC](../domains/graph/features/scenario-binding/SPEC.md),
and the rule's legs, liveness and configuration keys are in the
[rule-engine SPEC](../domains/graph/features/rule-engine/SPEC.md).

---

## The decision: the `.feature` file is the source of truth

A PRD states intent. A scenario states the same thing in a form that either runs or does not.
When the two disagree, one of them has to be authoritative, and BDL-061 made the `.feature` file
authoritative for two reasons:

- **An executable artifact cannot silently lie.** A criterion written only in a document stays
  green forever, because nothing executes a document. A criterion written as a scenario that
  runs goes red the day the behaviour stops.
- **A generator between the statement and the executable is a synchronisation problem of its
  own.** Generating scenarios from a document — or the document from the scenarios — replaces
  one drift with another, and adds a build step whose output nobody reads.

So the document **references** the scenario by name, and the reference is checked in the
direction that matters: a scenario a document claims exists and the suite does not contain is
reported. The document is free to say more than the suite; it is not free to promise an
acceptance criterion that nothing executes.

## The shape of a scenario

```gherkin
@bead:proj-42 @node:billing
Feature: an invoice that cannot be paid twice

  Scenario: paying an already-paid invoice is refused
    Given an invoice that has been paid
    When the customer pays it again
    Then the second payment is refused
    And the invoice's balance is unchanged
```

Two tags carry the binding:

| Tag | Meaning | Checked against |
|-----|---------|-----------------|
| `@bead:<id>` | the work the scenario was written for | nothing — see *Honest limits* below |
| `@node:<ref_id>` | the graph node whose behaviour this pins | the graph: an unknown ref_id is reported |

Tags follow Gherkin's own inheritance. A tag on `Feature:` or on `Rule:` applies to every
scenario beneath it, so a file that pins one node names it once. A scenario's own tags are added
to the inherited ones.

Beadloom does not invent a tag syntax: `@bead:` and `@node:` are ordinary Gherkin tags, so every
parser, runner and editor already reads them. If your runner turns tags into selectors — as
`pytest-bdd` turns them into pytest markers — tell it that these two are data rather than
selection. This repository does it in ten lines in `tests/acceptance/conftest.py`, through
`pytest_bdd_apply_tag`, because it runs with `--strict-markers` and no one can keep a list of
every bead id registered in advance.

**Write the scenario first, and see it fail.** A scenario that has never been red is a claim, not
a check. The dev role protocol says so in the shipped role core, and the reason is the same one
that makes the `.feature` file authoritative.

## Where the suite lives

The default layout is the one this repository uses:

```
tests/acceptance/features/**/*.feature   # the scenarios
tests/acceptance/steps/                  # the step implementations
```

It is a default and not an imposition. The rule names its own glob, so a project with a
`qa/gherkin/` layout is read exactly as this one is:

```yaml
# .beadloom/_graph/rules.yml
rules:
  - name: scenario-coverage
    description: "Behaviour-bearing nodes carry an executable scenario; a scenario names its bead"
    severity: warn
    scenario_coverage:
      for: { kind: feature }
      features: "qa/gherkin/**/*.feature"
      references:
        - "docs/prd/**/*.md"
```

`for` is the population — which graph nodes are expected to carry behaviour. `features` is the
suite. `references` are the documents whose scenario references are checked against it.

**Gherkin is localised and so is the parser.** The `en` and `ru` keyword sets ship, and
`# language: xx` is honoured. A file declaring any other dialect is reported as *unreadable*,
naming the dialects that do parse — never counted as a file that declares no scenarios. A team
writing its scenarios in Russian would otherwise have had every node reported uncovered by a
parser that read nothing.

## What the rule reports

`scenario-coverage` runs four legs, and each answers a different question. All findings are
`warn`: a new check must not turn an adopter's green project red on upgrade.

| Leg | Reports |
|-----|---------|
| coverage | a node in `for` that no scenario names, and that no declaration excuses |
| suite | a scenario naming no bead; a `@node:` that is not in the graph; a file nothing could read; a file in the suite declaring no scenario |
| reference | a scenario a `references` document claims exists and the suite does not contain |
| declaration | a `non_behavioural` entry that excuses nothing, or one whose node has a scenario anyway |

Every coverage finding carries the population it is a fraction of — `none of 92 scenarios in 20
files carries @node:agent-prime` — so a shrinking suite cannot improve a number by making the
denominator smaller without saying so.

**The scenarios have to RUN.** Nothing in the rule executes them: it reads structure — keywords,
tags, names. A suite that parses and never runs would satisfy every finding above while
asserting nothing. That is why this repository ships `pytest-bdd` in its `dev` extra, runs every
`.feature` file as part of the ordinary suite, and holds a test that binds the number of
executed scenarios to the project's own parser count, so a feature file with no step module
reddens instead of quietly counting as coverage. Measured on this repository, 2026-08-24: 33
scenarios in 7 files, the newest being `doc_spaces.feature` (BDL-061 S5).

## Work with no behaviour says so

A chore, a vocabulary module, a pure data model: some nodes in the population have nothing an
observer could see. Declaring that is a decision; leaving the finding unaddressed is a gap.

```yaml
    scenario_coverage:
      for: { kind: feature }
      non_behavioural:
        - node: rule-vocabulary
          reason: "a frozen enum of rule-type names; it has no behaviour to observe"
```

Three properties are deliberate:

- **The reason is mandatory**, and there is deliberately **no `until`**. This is a
  classification, not an expiring debt — a vocabulary module does not become behaviour-bearing
  on a calendar date. What keeps it honest is that a declaration which excuses nothing is itself
  a finding, so a stale one is reported rather than silently carried.
- **A live declaration is stated out loud, once per run**: `1 of 2 node(s) in this rule's
  population are excused as non-behavioural, so every coverage figure below is a fraction of 1`.
  The excused nodes leave the population and the coverage fraction improves; a run that did not
  say the denominator moved would be reporting an improvement it manufactured.
- **`for.exclude` is rejected on this rule type.** An `exclude` entry carries no reason, is never
  reported and never expires, so a matcher excluded down to nothing would report only that it
  selects no node. The loader raises, names the excluded nodes and routes the author to
  `non_behavioural`. The requirement is scoped to `scenario_coverage`: `exclude` is shared by
  every rule type and demanding a reason everywhere would redden adopters over rules this has
  nothing to do with.

## Honest limits

Each of these is a property of the design, stated here rather than discovered by a reader who
trusted the check.

- **The bead id is not verified against the tracker.** Reading the tracker from the rule engine
  would make a domain depend on the application layer. What is checked is that a scenario *names*
  a bead; `@bead:no-such-bead-anywhere` is accepted. The limit travels on the finding's own
  remediation text rather than living only here.
- **Only structure is parsed.** A scenario that binds correctly and asserts nothing counts as
  coverage. Whether its assertions would notice a defect is the mutation duty's question, not
  this rule's.
- **An empty suite stands the whole rule down.** When the `features` glob matches no file, the
  rule reports the glob and returns: the suite, declaration, coverage and reference legs are all
  skipped. Measured on this repository, repointing `features:` at a directory that does not exist
  takes `beadloom lint` from **68** findings to exactly **1**, and that 1 is the liveness finding
  naming the dead glob. The reason for the silence is that one configuration error printed as N
  architecture findings buries the finding that would fix it. Because all four legs stand down,
  and only then, the rule is also **counted** in `LintResult.rules_inert`, so the summary line
  cannot advertise a check that looked at nothing.
- **A reference is a line, not a sentence.** The reference reader takes a line that *begins* with
  a scenario keyword after markdown stripping. `Example:` is a scenario keyword in Gherkin, so a
  prose line opening with it is read as a claim that a scenario exists, and an indented code
  block is read while a fenced one is not. Both are filed as `beadloom-mr2l.62` with a failing
  test pinned to each, so the fix reddens the suite. Zero of the 26 reference findings on this
  repository come from that class today.

## What this repository ships with, and why the number is not zero

`beadloom lint` reports **59** `scenario-coverage` findings here — measured 2026-08-26 during
BDL-062, with `--json`, on the shipped `rules.yml`:

| Findings | What they are |
|----------|---------------|
| 32 | no scenario in the suite binds to a `feature` node the graph declares |
| 26 | scenarios a planning document names and the suite does not contain |
| 1 | the rule stating the reach of its own population (see below) |

The population is the honest one: `for: {kind: feature}` selects all **42** declared feature
nodes, of which 10 are covered (`doc-quality`, `doc-shape`, `doc-templates`, `docs-audit`,
`flow-guards`, `review-brief`, `rule-engine`, `scenario-binding`, `sync-check`, `wave-plan`).
The suite holds 92 scenarios in 20 files. The uncovered count falls whenever a bead binds a
scenario to a node its work touched, and the population grows whenever a feature node is
declared, so the two move independently and neither is a target. A hand-picked `ref_id` list
would report 0 by construction, which is the false
green the whole mechanism exists to remove. `component`, `domain`, `service` and `site` nodes are
outside the population by the architecture model's own definition — a feature is a capability, a
component is plumbing. Reclassifying a feature as a component is therefore a **silent** exit from
the population, with no finding of any kind; that is filed as `beadloom-mr2l.63` with both
options priced.

Two mechanisms ship **inert on this repository**, and that is stated rather than implied by a
green count:

- **`non_behavioural` has no live instance here.** The shipped `rules.yml` declares none, so the
  excused-population line and the dead-declaration finding are proved by unit rows and by an
  acceptance scenario, and by nothing on this corpus.
- **`for.exclude` rejection has no live instance here** either, for the same reason: nothing in
  this repository's rules uses `exclude` on this rule type.

## Related

- [Scenario Binding SPEC](../domains/graph/features/scenario-binding/SPEC.md) — the parser, the
  dialects, the reference syntax and the structures it refuses.
- [Rule Engine SPEC](../domains/graph/features/rule-engine/SPEC.md) — the rule's configuration
  keys, its four legs and the liveness model.
- [Document kinds and the writing standard](document-kinds.md) — the other half of S4: the shape
  and the quality of the documents that reference these scenarios.
- [Project Overlays](project-overlays.md) — `flow.yml`, the project layer, and the mutation scope
  that answers "would these assertions have noticed".
