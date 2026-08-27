# The Architecture Model: Domain vs Feature

Beadloom models a codebase as a small graph of **nodes** (declared in
`.beadloom/_graph/services.yml`) backed by **code annotations** in the source.
Three node kinds carry most of the modeling weight: **domain**, **feature**,
and **component**. Getting the boundary between them right is what keeps the
graph honest — neither so coarse that everything hides inside one domain, nor so
fine that every helper becomes a node. This guide is the policy.

## Domain

A **domain** is a DDD package — one directory under `src/beadloom/<pkg>/`
(for example `graph/`, `context_oracle/`, `onboarding/`). It is the unit of
**coarse ownership**: a bounded area of the system with a single owning
responsibility and a layer position (services to application to domains to
infrastructure). Domains are declared once in `services.yml` and each maps to
its source prefix.

Rule of thumb: if you would draw it as a box on the high-level architecture
diagram, it is a domain.

## Feature

A **feature** is a cohesive, independently-describable **capability** that lives
inside a domain and has its own `SPEC.md`. In practice a feature is one of:

- a **CLI command** (or a tight family of commands), or
- a **distinct subsystem** with its own contract — a clear input/output or
  protocol boundary distinct from its sibling modules.

The test is the **paragraph test**: if you can write a paragraph describing
**what it does** and **its contract** (inputs, outputs, invariants) that is
distinct from its sibling modules in the same domain, it is a feature and
deserves a node plus a `SPEC.md`. If the best you can write is "shared helpers
used by the rest of the domain", it is not a feature — it is plumbing.

Features are declared in `services.yml` with a `part_of` edge to their domain,
and every feature must have a `SPEC.md` describing that contract.

## Component

A **component** is an internal/infra **building block** — a tracked module that
is *not* a user-facing capability but still warrants a doc and a node. Think
`db`, `graph/loader`, the context-bundle builder, `git_activity`, the `bd`
seam: substantial machinery the rest of the system stands on, with a real
surface worth documenting, but no externally-visible "command" or contract of
its own. (The code indexer, by contrast, *is* a feature — it has a distinct
input/output contract: source files → `code_symbols` rows — so it earns a
`SPEC.md`, not a `DOC.md`.)

A component is declared in `services.yml` exactly like a feature — `kind:
component`, a `source: <file>`, a `part_of` edge to its domain, and a `docs:
<DOC.md>` — and it is attributed in code with a `# beadloom:component=<id>`
annotation (the mirror of `# beadloom:feature=`). The distinction from a
feature is intent, not weight: a feature is a *capability* (often a CLI command
or a distinct contract); a component is *plumbing important enough to track and
document* so it never silently rots.

## Plumbing / shared helpers (exempt)

Not every module earns a node. Truly trivial glue — pure helpers, config
readers, small adapters, docstring-only modules — stays **domain-level** with
**no node and no `SPEC.md`**. But such a module must **never be invisible**:
either it is listed in its domain README module-list, or it is named on the
**explicit exempt list** in `rules.yml` (see the coverage lint below). A module
that is none of {feature, component, exempt} is exactly the shadow code this
model exists to prevent.

## Annotations and declaration

The graph and the code are kept in agreement through annotations parsed by the
code indexer into `code_symbols.annotations` (a JSON object per symbol):

- `# beadloom:domain=<domain-ref-id>` — attributes a module to a domain. A
  module with only a `domain` annotation lands in that domain's
  `docs/domains/<domain>/README.md`.
- `# beadloom:feature=<feature-ref-id>` — attributes a module to a feature
  (in addition to its domain). This is what promotes a module from plumbing to
  a modeled capability.
- `# beadloom:component=<component-ref-id>` — attributes a module to a
  component (in addition to its domain). This promotes a module from plumbing
  to a tracked internal/infra building block.

The matching nodes are declared in `services.yml`:

- a `domain` node per package,
- a `feature` node per capability, with a `part_of` edge to its domain and a
  `SPEC.md`, and
- a `component` node per internal building block, with a `part_of` edge to its
  domain, a `source: <file>`, and a `docs: <DOC.md>`.

### A node's `source` may be a directory

A node's `source:` is usually a single file, but it may also be a **directory**
— *dir-source coverage*. When `source:` names a directory (e.g. the `tui`
service declares `source: src/beadloom/tui/`), the node covers **every** module
under that prefix at once, so those modules need no per-file `feature=` /
`component=` annotation to satisfy the coverage lint — the directory `source`
**is** their coverage. The `module-coverage` lint treats "the module's path is
under a node's `source`" the same way it treats "the module's path *is* a
node's `source`". This keeps a cohesive leaf package (like `tui/`) modeled as
one node without forcing a node per file.

After editing annotations or `services.yml`, run `beadloom reindex` (then
`beadloom sync-check`) so the index reflects reality.

## The `module-coverage` lint (no shadow code)

Beadloom enforces **complete coverage**: every source module is either a tracked
node or explicitly exempt — nothing untracked, nothing documented-once-then-left
to rot. The `module-coverage` lint (in `.beadloom/_graph/rules.yml`, evaluated by
the graph rule engine) is the check. It **supersedes** the older
`unregistered-feature-candidate` sprawl-lint with a stronger, whole-tree check.

For every `src/beadloom/**.py` module with at least `min_symbols` indexed
symbols (default `1`, i.e. "has ≥ 1 public symbol"), the module is **covered**
when any of:

- one of its symbols carries a `# beadloom:feature=` annotation, or
- one of its symbols carries a `# beadloom:component=` annotation, or
- the module's path **is** a node's `source` (it *is* a node), or
- its path matches an entry on the rule's **`exempt`** list (a list of `fnmatch`
  file-path globs).

A module that is none of these produces one finding naming the file and its
symbol count:

```
src/beadloom/onboarding/branch_protection.py (6 symbols): not covered by any
  node and not exempt — classify as a feature/component or add to exempt.
```

(That file now carries `# beadloom:feature=branch-protection` and produces no
finding; the shape of the message is what the example shows.)

The lint's severity is **`error`** in this repository's `rules.yml`, so a new
shadow module makes `beadloom lint --strict` exit non-zero and fails the Gate. It
ran at `warn` while the tree was being classified and was raised once every
module had been. An adopter's own `rules.yml` chooses, and `warn` is the sane
setting until their tree is classified — a check that fails a first run on a tree
nobody has swept yet is a check that gets deleted rather than answered.
The intended response to a finding is one of:

1. **Model it as a feature** — a user-facing capability: add a `feature` node, a
   `# beadloom:feature=` annotation, and a `SPEC.md`; or
2. **Model it as a component** — an internal/infra building block: add a
   `component` node, a `# beadloom:component=` annotation, and a doc; or
3. **Exempt it** — only when it is genuinely trivial glue. Add its path to the
   rule's `exempt:` list. The list lives in `rules.yml` (it is **visible**, not a
   silent escape hatch).

### Exempt criterion

A module may be exempted only when **all** of:

- it has **fewer than N public symbols** (small surface), **and**
- it does **not back a CLI command**, **and**
- it is **internal-only** (a docstring-only module is enough).

The list is seeded **minimally** with the genuinely-trivial — `**/__init__.py`,
`**/__main__.py`, `onboarding/config_reader.py`, `onboarding/presets.py` — and
grows only by deliberate, reviewable edits in `rules.yml`. One entry is not
trivial glue and carries its reason in the file: `graph/rule_engine.py` is a
back-compat re-export shim with no symbols of its own, and the `rule-engine` node
is sourced at the package where the engine lives, so the exemption covers only
the shim's lack of code and not its membership. Everything else must become a
feature or a component.

## Two rules that read the graph's own metadata

`module-coverage` asks whether every module reaches a node. Two further rules ask
the questions on the other side of the same edge: whether a node's `summary` says
anything true, and whether a node's document sits where this graph puts documents.
Both were added in BDL-062 and both live in `.beadloom/_graph/rules.yml` beside the
boundary rules, because they query the same indexed schema and are therefore
generic over any project's graph.

### `graph-summary-facts` — a number in a summary is checked

A node's `summary:` is the sentence every other surface quotes: `beadloom ctx`,
`beadloom prime`, the generated site, the agent adapters. Until this rule nothing
compared it against anything. Measured on this repository at the time it landed,
the root node named a release three majors behind the one the project computes and
`mcp-server` named a tool total four short of its own catalogue. Both had been wrong
across three major releases without a single check going red.

```yaml
  - name: graph-summary-facts
    description: "A number or version stated in a node summary agrees with the project"
    severity: error
    summary_facts: {}
```

The rule owns neither the extraction nor the comparison. `DocScanner.scan_line`
reads the summary and `compare_facts` judges it — the same version pattern, the
same keyword table, the same clause-scoped proximity and the same per-fact
tolerances the [documentation audit](./ci-setup.md#unified-gate-beadloom-ci) uses
on prose. A second, subtly different notion of "a version" beside the first is how
the next drift class starts, so `summary_facts` takes no configuration keys at all.

Each summary lands in one of four answers, and the fourth is why the rule exists:

| Answer | What it means | Reported as |
|--------|---------------|-------------|
| agrees | a claim was found and it matches | counted, no finding |
| disagrees | a claim was found and it differs | a finding at the rule's severity, naming the node, both values and the fact's provenance |
| no claim | the summary states nothing checkable | counted **apart** from agreement |
| unverifiable | a claim was found for a fact this project could not compute | a `rule_liveness` finding carrying the registry's own reason verbatim |

**`unverifiable` never folds into a pass.** A project whose version cannot be
resolved and a project whose every summary checked out must not be described by the
same word. Every finding also carries the population it is a fraction of, so a rule
that found two claims in eighty-four summaries cannot report "no violations" as
though it had cleared eighty-four of anything.

Severity ships `error`, unlike the convention check below. A number that contradicts
the project it describes is wrong in every house style, so there is no adopter
preference to respect, and the value is in the adopter's own graph rather than in
Beadloom's.

Measured here: two summaries state a checkable fact and both agree, the rest state
none.

### `doc-area-coherence` — the convention is read off the graph

A node should document itself where its own graph documents nodes like it. The
interesting part is not the check but where the convention comes from: **no layout
is written down in the rule, anywhere.** A literal such as `docs/domains/<package>/`
would ship one project's tree as every adopter's, would be wrong for a
feature-sliced project the day it was installed, and would turn a check about the
graph into a check about Beadloom. An AST test over the module's non-docstring
string constants fails the moment a directory name is written into it.

```yaml
  # As this repository declares it. The shipped default is `warn` — see below.
  - name: doc-area-coherence
    description: "A node is documented where this graph documents nodes from its source area"
    severity: error
    doc_area_coherence:
      threshold: 0.6
      min_support: 2
```

Both sides of a pair are reduced to one comparable segment, and both are derived:

- **The source area** is the segment directly below the *source root*, and the root
  is found by descending one segment for as long as there is exactly one
  **supported** way down. On a package-per-domain tree that root comes out as
  `src/<package>` and the area is the package; on a feature-sliced tree it is `src`
  and the area is `features` or `entities`. Neither spelling is known to the rule.
  A root is the level above where the areas begin, which is why the descent is
  governed by support rather than by a majority: support answers *is there one
  shared way down*, a majority answers *which way down is most popular*, and only
  the first question has a root for its answer.
- **The docs area** is the doc-path segment at the *area depth*, and that depth is
  itself derived in two passes. The first asks each doc path where in it a source
  area is named, using the vocabulary the source side already produced, and takes
  the depth that answer lands at most often. The second reads **every** doc path's
  segment at that depth, whatever it is called there — which is what lets the rule
  see a document filed under a directory that names no source area at all, the
  commonest shape of the drift it exists to catch.

A mapping from one source area to one docs area is **dominant** when it covers at
least `threshold` of that area's observed pairs *and* rests on at least
`min_support` of them. The support condition is not decoration: without it every
area holding a single documented node is unanimous at one observation, and a graph
of six areas holding one node each reports a clean sweep having compared nothing
that could disagree.

**A graph with no dominant mapping reports that it checked nothing**, and is counted
in `LintResult.rules_inert` so the summary line cannot advertise a check that looked
at nothing. A flat docs tree, a project mid-migration and a graph too small to hold
a convention are all legitimately unverifiable, and none of them is clean.

Severity ships `warn`. A convention check is a check about house style, and one that
fails an adopter's first `beadloom ci` on their own house style is a rule they will
switch off. This repository raises it to `error`, where the layout has been settled
since BDL-051.

Two populations deliberately do not compare and neither is dropped. A source too
short to have a segment below the root is *rootless* — a node whose source **is** the
root. A source lying outside the root altogether is excluded from the comparison and
counted, which is why every finding's population clause ends with how many sit
outside the source root. Under an earlier unanimity rule either one held a veto over
the whole derivation; now each holds a count.

Measured here: 79 of the 85 pairs compare, all 79 agree and none contradicts. The
six that do not compare are three sources that are the root itself and three doc
paths with no segment at the derived depth.

### A total stand-down is not a partial gap

The two answers are deliberately not symmetric, and the asymmetry is the point.

**Partial inertness stays advisory.** A dead glob, an exemption that excuses nothing,
a matcher selecting no node while the rule's other legs still fire — each is a
configuration smell rather than a boundary breach, and each reports `warn` whatever
the rule declares. Promoting them would turn an adopter's green pipeline red on an
upgrade that changed none of their code.

**A rule that could check *none* of its population is a different fact.** When a rule
verified nothing, "the rule found nothing wrong" and "the rule never ran" are the
same output, and a project that deliberately raised that rule to `error` has had its
escalation evaporate at exactly the moment it mattered. `doc-area-coherence` and
`graph-summary-facts` therefore pass their own declared severity on a total
stand-down, while a project that settled its layout and said so keeps the answer it
asked for.

**What the two rules cost an adopter differs, and the difference is the severity they
ship.** `doc-area-coherence` ships `warn`, so it still reports `warn` and no
adopter's run changes. `graph-summary-facts` ships `error`, so a project that enables
it over summaries stating no checkable number now goes red rather than green. That is
a real cost and it was measured before the change was made: a graph
`beadloom init --mode bootstrap` produced from a two-module project had **0 of 3**
summaries stating a checkable fact, so the stand-down is a reachable first run rather
than a corner. It is still the better answer, because the alternative shipped in
3.0.0 was worse — the rule read no number and said so at `warn`, so "every number
checks out" and "no number was read" left `lint --strict` with the same exit code.
The escape hatch is one key: `severity: warn` on the rule, in the same `rules.yml`
entry that enabled it.

The rule's **per-node** `unverifiable` answer stays `warn` whatever the rule is
declared as, and deliberately so. A claim naming a fact the project declined to
compute is a gap in what the project computes, not a summary contradicting it, and
the rule read every other summary in the graph — that is the partial case, and it
names its node while a total stand-down names none (BDL-062 `.14`).
