# Scenario Binding

Read the acceptance suite and the documents that reference it, and say what each scenario binds
itself to.

**Source:** `src/beadloom/graph/scenarios.py`

---

## Specification

### Purpose

The `.feature` file is the **source of truth** for behaviour (BDL-061 CONTEXT): it holds the
text of an acceptance criterion, and a PRD or BRIEF states the intent and references the
scenario by name. An executable artifact cannot silently lie — it either runs or it does not —
whereas a generator sitting between a statement and an executable becomes a synchronisation
problem of its own.

This module is the reader that makes the decision checkable. It answers two questions and
evaluates nothing:

- *Which graph node and which bead does this scenario claim?* — from Gherkin tags.
- *Which scenario does this document claim exists?* — from a reference line in a TO-BE document.

The verdicts are `scenario-coverage`'s, in
[`rule-engine`](../rule-engine/SPEC.md).

### The binding is carried by Gherkin tags

```gherkin
@bead:beadloom-mr2l.13 @node:rule-engine
Feature: behaviour that carries no executable claim is reported

  Scenario: a behaviour-bearing node with no scenario is reported
    Given a graph with the feature nodes "billing" and "shipping"
    ...
```

| Tag | Meaning |
|-----|---------|
| `@bead:<id>` | the work the scenario was written for |
| `@node:<ref_id>` | the graph node whose behaviour the scenario pins |

Tags follow Gherkin's own inheritance: a tag on `Feature:` or `Rule:` applies to every scenario
beneath it, so one file binds to a node once. A scenario's own tags are added to the inherited
ones, de-duplicated, in order of first appearance.

**Why tags and not a header comment** (the RFC sketched a comment): a tag is part of the Gherkin
language. Every parser, runner and IDE already understands it and `pytest-bdd` exposes it for
selection, whereas a comment is understood by nobody but us.

### Entry points

```python
def parse_feature(text: str, *, path: str) -> tuple[tuple[Scenario, ...], str | None]
def load_suite(project_root: Path, glob: str) -> ScenarioSuite
def parse_scenario_references(text: str, *, path: str) -> tuple[ScenarioReference, ...]
def load_references(project_root: Path, globs: Sequence[str]) -> ReferenceSet
```

`parse_feature` returns `(scenarios, reason)`. A `reason` that is not `None` means the file's
scenarios are **unknown**, and the empty tuple beside it is "nothing could be read" rather than
"nothing is there".

`ScenarioSuite` keeps three populations apart because they need different remedies:

| Field | Meaning |
|-------|---------|
| `files` | what the glob matched — the denominator of any statement about the suite |
| `scenarios` | what was read |
| `empty_files` | parsed cleanly, declared no scenario |
| `unreadable` | could not be parsed at all, with the reason (`UnreadableDocument`) |

`UnreadableDocument` carries `path` and `reason`. It shipped as `UnreadableFeatureFile` in
2.2.0, when only the suite reader used it; that name is kept as an alias.

### Where the suite lives

The default is `tests/acceptance/features/**/*.feature`, with step implementations in
`tests/acceptance/steps/` — the layout proven in the dogfood project (Q3). It is a **default**,
not a convention imposed: the rule names its own glob, and an adopter's layout is read exactly
as ours is.

### Dialects

Gherkin is localised, and a team writing its scenarios in Russian is the population #136 exists
for. The parser ships `en` and `ru` keyword sets and honours the `# language: xx` directive.

A file declaring any other dialect is reported as **unreadable, naming the dialects that do
parse** — never counted as a file with no scenarios. The same is true of a file that does not
decode as UTF-8. This is `.46`/`.47`'s rule: unverifiable is not clean.

### Structure the parser refuses

| Input | Result | Why |
|-------|--------|-----|
| a second `Feature:` in one file | unreadable | the Gherkin specification allows one per file and `pytest-bdd` refuses the whole file; accepting it would count scenarios as covering their nodes while nothing executed |
| `Scenario:` inside a `"""` or ``` ``` ``` payload | not a scenario | quoting Gherkin is not declaring it |
| `Scenario:` in a `#` comment | not a scenario | — |
| `Examples:` / `Примеры:` | not a scenario | the scenario keyword is a prefix of the table keyword in both shipped dialects |

### Referencing a scenario from a document

A **reference** is a line whose text, once markdown list markers, checkboxes, quote markers,
emphasis and backticks are stripped, *begins* with a scenario keyword and a colon:

```markdown
- [ ] Scenario: `a behaviour-bearing node with no scenario is reported`
```

Four deliberate exclusions keep the check about claims rather than sentences:

- **Prose is not a reference.** `proved by one scenario: the inert one` does not begin with the
  keyword, and does not match.
- **A fenced block is a form, not a claim.** `templates.md` ships the scenario shape inside a
  fence; the reader skips fenced blocks so a template is never read as a promise.
- **An indented block is a form too.** Markdown has two code syntaxes, and the reason for
  skipping one applies identically to the other: four spaces of indentation (tabs expanded) is a
  form. A line that is indented AND opens with a bullet or a quote marker is a deeply nested
  list item, not code, and is read as a reference — an author who bulleted a reference meant one.
- **A prose-shaped keyword needs a mark.** `Example:` (en) and `Пример:` (ru) are Gherkin
  scenario keywords and also ordinary words that open an explanatory paragraph in any PRD. A
  bare line starting with one is prose; bulleted, quoted or backticked, it is a reference.
  Measured (`.62`): `Example: a nested import inside a function is still an import.` yielded the
  reference `a nested import inside a function`, which the rule then demanded a scenario for.
  This repository has 33 references before and after the change, so nothing an author wrote
  stopped being read.

`load_references` returns a `ReferenceSet`: the `references`, the `dead_globs` that matched **no
document**, and the `unreadable` documents that matched and could not be decoded. A reference
check whose documents moved reports nothing and reads exactly like one that found no problem
(BDL-UX #172), and an undecodable document is the sharper case of the same thing — before `.62`
a cp1251 PRD naming one scenario yielded no reference, no dead glob and no finding, so the rule
stated that document's intent was fully met. `scenario-coverage` reports each unreadable
document as a finding naming the reason.

### Honest limits

- **The bead's existence is not verified.** Reading the tracker from the rule engine would make
  a domain depend on the application layer. What is checked is that a scenario *names* a bead;
  the `@node:` reference **is** verified against the graph.
- **Only structure is parsed** — keywords, tags, names. Steps are not interpreted, so a scenario
  that binds correctly and asserts nothing is invisible here. That is the mutation duty's job.

## Testing

| Suite | What it covers |
|-------|----------------|
| `tests/test_scenario_binding.py` | parsing, inheritance, dialects, references, dead globs, and a cross-check of Beadloom's own suite against `gherkin-official`, the parser `pytest-bdd` uses |
| `tests/acceptance/features/scenario_binding.feature` | the binding stated as scenarios that run |
