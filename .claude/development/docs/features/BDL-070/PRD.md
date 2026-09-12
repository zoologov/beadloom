# PRD: BDL-070 — The layer a node is in, answered once and reported over its population

> **Status:** Approved
> **Created:** 2026-09-12

---

## Problem

`architecture-layers` is this project's only machine check that dependencies run in the declared
direction. It carries `severity: error`, so a violation fails `lint --strict` and the Gate. It
evaluates an edge only when **both** ends carry a layer tag in `nodes.extra.tags`, and a tag is not
inherited through `part_of` — so a component sits in no layer however deep inside one it is.
`evaluate_layer_rules` says so in its own docstring: *"Nodes that do not belong to any layer are
silently skipped."*

**Measured by `beadloom-rqma.4` on this repository's index:** 12 nodes carry a layer tag; there are
353 active `depends_on` edges; **16 of them are evaluated**. By `part_of` ancestry, 345 of the 353
have a layer at both ends.

**Probed, on a `git archive` copy of HEAD:** an import of a `graph`, `context_oracle` or `doc_sync`
module from `infrastructure/git_activity.py` produced the edge `git-activity -> doc-sync`, and
`lint --strict` reported no layer finding. So *"`lint --strict` is green"* does not today mean
*"no infrastructure module imports a domain"*, which is what the layering declares.

**The green line names no population.** `LintResult` counts `rules_evaluated` for the whole run and
has no per-rule population field, so the rule reports 16 of 353 in exactly the same words it would
use for 353 of 353.

### Three answers to "what layer is this node in", and they disagree

Derived by hand for this work item, because `beadloom impact` found no seed for the target and said
so rather than reporting an empty population:

| Site | How it decides | Disagreement |
|---|---|---|
| `graph/rules/evaluators.py:588` | the node's own tags, first tag matching the rule's order | no ancestry |
| `graph/rules/liveness.py:285` (`_layer_reasons`) | the same rule, computed a second time | decides whether the rule is inert |
| `application/architecture_view.py:82`, `:193` | **walks `part_of` to the nearest tagged ancestor**, over four hardcoded `layer-*` tags and ranks | flags an edge at `dst_rank <= src_rank` (`:268`), so it flags same-layer edges that `evaluators.py:632` allows |

The inheritance this work item proposes **already exists** in `architecture_view.py`, in another
domain, reading a different declaration and reaching a different verdict.

### The declaration is doubled too

`.beadloom/_graph/rules.yml:44`–`:58` declares the rule. `rules.yml:3`–`:7` carries a *second*,
independent `tags:` catalog mapping each layer tag to a node list. It names **10** nodes; the graph
YAML tags **12** — it omits `cli-commands` and `guard-probes`. Nothing in `src/` reads it: the only
callers of `load_rules_with_tags` are `tests/test_rule_engine.py:1111` and `:1131`. And
`validate_rules` (`graph/rules/loader.py:1060`) has no `LayerRule` in its isinstance chain, so a
layer tag matching no node is not reported there.

### The claim has already shipped

`src/beadloom/onboarding/templates/roles/architecture/ddd/dev.md.txt:13` is a **shipped role
template**. It tells every adopter's dev agent that `architecture-layers` at `severity: error` means
*"a green `lint --strict` genuinely enforces direction"*. That sentence is false today, and it is
outside what `beadloom impact` can read.

## Impact

**Every adopter**, and this repository. A rule that evaluates 4.5% of its edges and reports like a
rule that evaluated all of them is the exact class BDL-068 and BDL-069 exist to remove — with the
aggravation that this one is the *architecture* check, the thing Beadloom's positioning rests on.
The shipped role template turns it from a silent gap into an assertion an agent is told to rely on.

If this is not fixed: the project keeps a `severity: error` check whose green is not evidence, three
implementations of one fact continue to drift apart, and the first adopter who reorganises their
graph gets a green Gate over a layering violation.

## Goals

- [ ] `architecture-layers` states its population on every run — edges evaluated, edges skipped for
      an untagged end — and states it before any verdict changes.
- [ ] One implementation answers "what layer is this node in", reading the declaration rather than
      hardcoding it; the other two call it.
- [ ] A layer is derived through `part_of` ancestry, so the evaluated population is the edges the
      layering actually declares rather than the edges someone remembered to tag.
- [ ] The layer declaration is single, validated, and owned by a node.
- [ ] No shipped artifact claims the rule checks more than it checks.

## Non-goals

- **Changing what the layering *is*.** The four layers, their order and `enforce: top-down` are not
  under review. This work changes which edges the rule can see, not which direction is legal.
- **Rewriting `architecture_view.py`'s product behaviour.** It stops owning a second definition of
  layer membership; what it renders is not otherwise this work item's subject.
- **The other rule kinds.** `deny`, `require`, `forbid_edge`, `cardinality` also read tags through
  their own `_cached_tags` closures. They are named in the RFC because one shared lookup touches
  them, but their own populations are not this item's goal.
- **Federation.** `graph/federation/export.py:103` does not select `extra`, so layer membership does
  not cross the federation boundary. Stated so the absence is a measurement, not an oversight.
- **A per-rule population for every rule.** `scenario-coverage` already states its own; generalising
  that to all rules is a larger change and is not proposed here.

## User Stories

### US-1: A person reads a green line and knows what it covered

**As** a developer or an agent reading `lint --strict`, **I want** the layer rule to say how many
edges it judged and how many it skipped, **so that** a green line is a measurement rather than a
silence.

**Acceptance criteria** (each references a scenario in `tests/acceptance/features/`):
- [ ] Scenario: `the layer rule states how many edges it evaluated and how many it skipped`
- [ ] Scenario: `a graph where every node is tagged reports no skipped edges`
- [ ] Scenario: `the population reaches a reader that calls the evaluators without lint`

### US-2: One answer to the layer question

**As** a maintainer, **I want** layer membership computed in one place that reads the declaration,
**so that** two instruments cannot report different layerings of one graph.

**Acceptance criteria** (each references a scenario in `tests/acceptance/features/`):
- [ ] Scenario: `the rule engine and the architecture view agree on every node's layer`
- [ ] Scenario: `a layer declared only in rules.yml is honoured without being hardcoded`

### US-3: The rule sees the edges the layering declares

**As** an adopter, **I want** a node inside a tagged domain to belong to that domain's layer,
**so that** a green Gate means no module crosses the layering.

**Acceptance criteria** (each references a scenario in `tests/acceptance/features/`):
- [ ] Scenario: `a component inherits its layer from the nearest tagged ancestor`
- [ ] Scenario: `an import from infrastructure into a domain is reported`
- [ ] Scenario: `a node with its own tag keeps it rather than inheriting`

### US-4: The declaration cannot quietly disagree with itself

**As** a maintainer, **I want** one validated layer declaration, **so that** a tag naming no node,
or a catalog nobody reads, is reported rather than kept.

**Acceptance criteria** (each references a scenario in `tests/acceptance/features/`):
- [ ] Scenario: `a layer tag matching no node is reported by validate_rules`
- [ ] Scenario: `the layer declaration has exactly one reader in the shipped code`

### US-5: Nothing shipped claims more than the rule does

**As** an adopter's dev agent, **I want** the role template to describe what the rule actually
checks, **so that** I do not treat a green `lint --strict` as proof it is not.

**Acceptance criteria:**
- [ ] Scenario: `the shipped role template's claim about the layer rule matches the rule's own report`

## Acceptance Criteria (overall)

Behaviour-bearing criteria are scenarios; the suite holds their text and this list references them
by name. `beadloom lint` reports a referenced scenario the suite does not contain.

- [ ] Scenario: `the layer rule states how many edges it evaluated and how many it skipped`
- [ ] Scenario: `the population reaches a reader that calls the evaluators without lint`
- [ ] Scenario: `the rule engine and the architecture view agree on every node's layer`
- [ ] Scenario: `a component inherits its layer from the nearest tagged ancestor`
- [ ] Scenario: `an import from infrastructure into a domain is reported`
- [ ] Scenario: `a layer tag matching no node is reported by validate_rules`
- [ ] Scenario: `the shipped role template's claim about the layer rule matches the rule's own report`

**Ordering, which is a constraint rather than a preference.** BDL-069's CONTEXT holds that no
adopter's Gate may change verdict on upgrade. The population report changes no verdict and ships
first; inheritance changes verdicts and ships after, in a release that says so.

**Non-behavioural criteria** stay checkboxes and are labelled, so the absence of a scenario is a
stated decision rather than a gap:

- [ ] The `agent-prime -> reindex` edge is resolved — fixed, or recorded as an accounted exception
      with its reason — **before** inheritance ships — non-behavioural: the resolution is a decision
      about one edge in this repository's own graph, and no adopter-visible behaviour distinguishes
      "fixed" from "exempted with a reason".
- [ ] `rules.yml` is owned by a node — non-behavioural: ownership changes which node's `Owns unread`
      column names the file, and no command's output changes.

## Open product question, carried into the RFC

Whether `architecture_view.py:268`'s `dst_rank <= src_rank` or `evaluators.py:632`'s allowance of
same-layer edges is the correct rule is a **product decision about the layering**, not a merge
detail. Unifying the two implementations forces it. The RFC must name which one survives and why.
