# The Architecture Model: Domain vs Feature

Beadloom models a codebase as a small graph of **nodes** (declared in
`.beadloom/_graph/services.yml`) backed by **code annotations** in the source.
Two node kinds carry most of the modeling weight: **domain** and **feature**.
Getting the boundary between them right is what keeps the graph honest — neither
so coarse that everything hides inside one domain, nor so fine that every helper
becomes a node. This guide is the policy.

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

## Plumbing / shared helpers

Not every module is a feature. Pure helpers, config readers, small adapters and
other **shared plumbing** stay **domain-level**: they get **no node and no
`SPEC.md`**. But they must **never be invisible** — every such module **MUST be
listed in its domain README module-list** so a reader can see the full surface
of the domain. Plumbing that is neither a feature node nor named in the README
is exactly the sprawl this model exists to prevent.

## Annotations and declaration

The graph and the code are kept in agreement through annotations parsed by the
code indexer into `code_symbols.annotations` (a JSON object per symbol):

- `# beadloom:domain=<domain-ref-id>` — attributes a module to a domain. A
  module with only a `domain` annotation lands in that domain's
  `docs/domains/<domain>/README.md`.
- `# beadloom:feature=<feature-ref-id>` — attributes a module to a feature
  (in addition to its domain). This is what promotes a module from plumbing to
  a modeled capability.

The matching nodes are declared in `services.yml`:

- a `domain` node per package, and
- a `feature` node per capability, with a `part_of` edge to its domain and a
  `SPEC.md`.

After editing annotations or `services.yml`, run `beadloom reindex` (then
`beadloom sync-check`) so the index reflects reality.

## The `unregistered-feature-candidate` lint (advisory)

Because "is this a feature?" is a human judgment, Beadloom does not auto-promote
modules. Instead the `unregistered-feature-candidate` lint (in
`.beadloom/_graph/rules.yml`, evaluated by the graph rule engine) **flags
candidates** so the sprawl is visible:

For each `domain` node it groups the indexed symbols by file and flags any file
whose annotations carry a `domain` key (matching that domain) but **no**
`feature` key, **and** whose indexed-symbol count is at least `min_symbols`
(default `5`, configurable in the rule). Each finding names the file and its
symbol count, e.g.:

```
onboarding/branch_protection.py (5 symbols): domain-only, no feature
  — candidate unregistered feature.
```

The lint is **advisory**: its severity is `warn`, so it appears in
`beadloom lint` output but does **not** make `beadloom lint --strict` exit
non-zero. It names candidates; it does not decide them. The intended response to
a finding is one of:

1. **Model it as a feature** — add a `feature` node, a `# beadloom:feature=`
   annotation, and a `SPEC.md`; or
2. **Accept it as domain-level plumbing** — list it in the domain README and add
   its path to the rule's `exclude:` list (a list of `fnmatch` file-path globs).
   For example, `config_reader.py` and `presets.py` in `onboarding` are accepted
   helpers and are silenced via `exclude`.

This keeps the graph honest: substantial capabilities become first-class
features with contracts, accepted plumbing stays visible in the README, and the
lint surfaces anything that has quietly grown into a feature without being
modeled as one.
