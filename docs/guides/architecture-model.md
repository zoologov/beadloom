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

The lint's severity is **`warn` for now**: it appears in `beadloom lint` output
but does **not** make `beadloom lint --strict` exit non-zero. (Once every module
is classified, S3b promotes it to `error` so any new shadow module fails CI.)
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
`onboarding/config_reader.py`, `onboarding/presets.py` — and grows only by
deliberate, reviewable edits in `rules.yml`. Everything else must become a
feature or a component.
