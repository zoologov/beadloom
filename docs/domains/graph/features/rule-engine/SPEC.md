# Rule Engine

Architecture-as-Code rule engine: parse `rules.yml`, validate rule definitions, and evaluate them against the architecture graph and code imports.

**Source:** `src/beadloom/graph/rules/` (the `rules/` package). `src/beadloom/graph/rule_engine.py` is a thin backwards-compatible re-export shim; new code imports from `beadloom.graph.rules`.

The package is decomposed by responsibility (BDL-059 S3, cohesion-driven):

- `rules/types.py` — constants, rule dataclasses, `NodeMatcher`, `Violation` (the model), plus the vocabulary the model is matched in: `import_path_as_path` / `matches_import_target` / `MATCHING_FORM_HINT`, and `exit_condition_deadline` (the `until:` grammar).
- `rules/loader.py` — `load_rules` / `load_rules_with_tags` / `validate_rules` (YAML → typed rules + DB validation).
- `rules/evaluators.py` — per-rule-type evaluation (deny / require / import-boundary / forbid-edge / layer / cardinality / unregistered-feature / module-coverage) + shared node/edge lookup helpers.
- `rules/liveness.py` — rule liveness: whether a rule *can* fire at all, for every rule type (BDL-061.48). It answers about the CONFIGURATION, never about the code.
- `rules/exemptions.py` — what a `forbid_import` exemption is doing: which crossings it covers, how many it swallows, and whether its exit condition has passed (BDL-061.49).
- `rules/cycles.py` — cycle detection (WHITE/GREY/BLACK colored DFS, path-as-set membership) + edge-liveness SQL helpers.
- `rules/__init__.py` — `evaluate_all` orchestration + the remediation post-pass + stable public re-exports.

---

## Specification

### Purpose

Enforce architectural constraints declaratively. Rules are defined in a YAML file and evaluated against the graph database (nodes, edges, code_imports, code_symbols, file_index, and sync_state tables). **Nine** rule types exist — `load_rules` has dispatched nine since BDL-051 S3a; this table listed seven until BDL-061.48 counted them against the loader:

| Type | Keyword | Semantics |
|------|---------|-----------|
| **deny** | `deny` | Forbid imports between matched nodes |
| **require** | `require` | Mandate specific edge relationships |
| **forbid_cycles** | `forbid_cycles` | Detect circular dependencies via DFS |
| **forbid_import** | `forbid_import` | Forbid file-level imports between glob-matched paths |
| **forbid_edge** | `forbid` | Forbid specific edge patterns between tagged node groups |
| **layer** | `layers` | Enforce layered architecture direction |
| **cardinality** | `check` | Enforce complexity limits per node |
| **unregistered_feature_candidate** | `unregistered_feature_candidate` | Flag substantial domain-only modules that model no feature |
| **module_coverage** | `module_coverage` | Require every `src/` module to be a tracked node or explicitly exempt |

### Constants

```python
VALID_NODE_KINDS: frozenset[str] = frozenset({
    "domain", "feature", "service", "entity", "adr"
})

VALID_EDGE_KINDS: frozenset[str] = frozenset({
    "part_of", "depends_on", "uses", "implements", "touches_entity", "touches_code"
})

SUPPORTED_SCHEMA_VERSIONS: frozenset[int] = frozenset({1, 2, 3})
```

### Data Structures

All dataclasses are frozen (immutable).

#### `NodeMatcher`

Matches graph nodes by `ref_id`, `kind`, `tag`, and/or `exclude`. In deny rules, at least one of `ref_id`, `kind`, or `tag` must be non-`None`. In require rules, an empty matcher (`has_edge_to: {}`) is allowed and matches **any** node — used for "must have at least one edge of this kind" semantics.

| Field     | Type                        | Description                                                        |
|-----------|-----------------------------|--------------------------------------------------------------------|
| `ref_id`  | `str \| None`               | Exact ref_id to match, or `None` for any.                          |
| `kind`    | `str \| None`               | Node kind to match, or `None` for any.                             |
| `tag`     | `str \| None`               | Tag the node must have, or `None` for any.                         |
| `exclude` | `tuple[str, ...] \| None`   | Ref_ids to exclude from matching, or `None` for no exclusions.     |

```python
def matches(self, node_ref_id: str, node_kind: str, *, tags: set[str] | None = None) -> bool
```

Returns `False` immediately if `node_ref_id` is in `exclude`. Otherwise returns `True` if all non-`None` fields (`ref_id`, `kind`, `tag`) match the given node. The `tags` parameter is optional for backward compatibility; when `tags` is `None` and `self.tag` is set, the tag check is skipped.

In YAML, `exclude` accepts either a single string or a list of strings; both are normalized to a tuple internally by `_parse_node_matcher()`.

#### `DenyRule`

Forbids imports between nodes matched by `from_matcher` and `to_matcher`.

| Field          | Type              | Description                                       |
|----------------|-------------------|---------------------------------------------------|
| `name`         | `str`             | Unique rule name.                                 |
| `description`  | `str`             | Human-readable description.                       |
| `from_matcher` | `NodeMatcher`     | Matches the source (importing) node.              |
| `to_matcher`   | `NodeMatcher`     | Matches the target (imported) node.               |
| `unless_edge`  | `tuple[str, ...]` | Edge kinds that exempt the import from violation. |

#### `RequireRule`

Requires that matched nodes have at least one outgoing edge to a target node.

| Field         | Type           | Description                                        |
|---------------|----------------|----------------------------------------------------|
| `name`        | `str`          | Unique rule name.                                  |
| `description` | `str`          | Human-readable description.                        |
| `for_matcher` | `NodeMatcher`  | Matches nodes that must satisfy the rule.          |
| `has_edge_to` | `NodeMatcher`  | Matches the required target node.                  |
| `edge_kind`   | `str \| None`  | If set, restricts to edges of this specific kind.  |

#### `CycleRule`

Detects circular dependencies in the graph using an iterative WHITE/GREY/BLACK colored DFS: each search frame holds its live path as a set (GREY membership) for O(1) cycle-closing tests, and reports each unique normalized cycle once (`max_depth`-bounded).

| Field         | Type                       | Description                                        |
|---------------|----------------------------|----------------------------------------------------|
| `name`        | `str`                      | Unique rule name.                                  |
| `description` | `str`                      | Human-readable description.                        |
| `edge_kind`   | `str \| tuple[str, ...]`   | Edge kind(s) to check for cycles.                  |
| `max_depth`   | `int`                      | Maximum DFS depth (default 10).                    |
| `severity`    | `str`                      | `"error"` or `"warn"`.                             |

#### `ImportBoundaryRule`

Controls file-level import boundaries using fnmatch glob patterns against `code_imports`.

> **The two globs are matched against two different vocabularies.** `from:` is matched against the **repo-relative source file path as indexed** — `src/beadloom/tui/app.py`, source root included. `to:` is matched against the **dotted import path with dots replaced by slashes** — `beadloom.infrastructure.db` becomes `beadloom/infrastructure/db`: no source root, no file extension, because an import names a module, not a file. A `to:` written as `src/beadloom/infrastructure/**` therefore matches nothing, **ever** — the defect that left two of this project's own twelve rules (`tui-no-direct-infra`, `onboarding-no-direct-infra`) unable to fire while `lint --strict` printed `12 rules, 0 violations` (BDL-UX #172; this reference taught the broken form, which is why the fix belongs here and not only in `rules.yml`). Write `beadloom/infrastructure/**`, or `**/infrastructure/**` if the package root varies.

> **A `to:` glob covering a package also covers a bare import of the package itself.** `from pkg.infrastructure import db` is indexed with `import_path == "pkg.infrastructure"` — the target is the package, not the module — so `pkg/infrastructure/**` is matched against `pkg/infrastructure/` as well, and the most common Python reach-in form is caught. Sibling names are unaffected: `pkg/infrastructure_docs` still does not match. (Also BDL-UX #172: the probe injected to reproduce that bead — `from beadloom.infrastructure import db` in the TUI — fired under *no* glob form before this.)

| Field         | Type                            | Description                                        |
|---------------|---------------------------------|----------------------------------------------------|
| `name`        | `str`                           | Unique rule name.                                  |
| `description` | `str`                           | Human-readable description.                        |
| `from_glob`   | `str`                           | Glob matched against the **source file path** (`src/pkg/tui/app.py`). |
| `to_glob`     | `str`                           | Glob matched against the **dotted import path, dots → slashes** (`pkg/infrastructure/db`). |
| `severity`    | `str`                           | `"error"` or `"warn"`.                             |
| `exempt`      | `tuple[ImportExemption, ...]`   | Named, expiring exceptions (default empty).        |

#### `ImportExemption`

One recorded exception to an `ImportBoundaryRule`. An exemption baselines a pre-existing crossing instead of narrowing the rule that catches it: the boundary keeps its full scope, so a **new** crossing still fails, while what is tolerated today is visible, attributed and dated.

| Field       | Type   | Description                                                                    |
|-------------|--------|--------------------------------------------------------------------------------|
| `to_glob`   | `str`  | Matched like the rule's `to` (dotted import path). Default `"*"` — any target.   |
| `from_glob` | `str`  | Matched like the rule's `from` (source file path). Default `"*"` — any source.   |
| `reason`    | `str`  | **Mandatory.** Why this crossing is tolerated.                                   |
| `until`     | `str`  | **Mandatory.** The condition that retires the entry — a date or an event (see below). |

`load_rules` raises `ValueError` when an entry omits `reason` or `until`, or sets neither `from` nor `to` (an entry matching both would exempt the whole rule). A deadline already in the past is **not** a load error: rejecting a config for the passage of time would break a project that changed nothing, so it is reported by the run instead.

**What `until` is (BDL-061.49).** It answers one question — *what retires this entry* — and there are two honest answers, so the grammar admits both:

- a **deadline**: the value LEADS with an ISO `YYYY-MM-DD` date, optionally followed by the prose that explains it (`2026-09-01 — when the repository read seam lands`). It is parsed, and once that day has passed while the entry is still suppressing something, the run reports it;
- an **event**: anything else (`the rule is re-scoped — BDL-UX #150 follow-up`). Not parseable, and deliberately still legal: what retires a real baseline is usually a landed change, not a day. An event is reported as prose, never treated as satisfied.

The spelling is pinned to a leading `YYYY-MM-DD` by a pattern rather than delegated to `date.fromisoformat`, because that parser widened in Python 3.11 (`20260101` and week dates parse there and raise on 3.10) — the same `until:` must not be enforceable on one supported interpreter and prose on another. A date in the MIDDLE of a sentence is an event: a deadline is the first thing an exit condition says, or it is not one. `exit_condition_deadline` is the single definition, shared with the `guards.<name>.exclusions[].until` of `flow.yml`, so the two surfaces cannot promise different things.

**Every exemption is visible, whatever it does.** The three channels are exhaustive over what an entry can be doing, and this is the guarantee the `rules.yml` comment used to overstate:

| The entry | What the run says |
|-----------|-------------------|
| suppresses nothing | a **dead** finding (`rule_liveness`, `warn`): "suppresses nothing … delete it" |
| suppresses something, past its deadline | an **expired** finding (`rule_liveness`, `warn`) naming the date and how many crossings it is still excusing |
| suppresses something, within its deadline or on an event | counted: `LintResult.violations_suppressed`, the `", N crossings suppressed by an exemption"` clause on the summary line, and one entry per crossing in `--format json`'s `suppressed` array |

A blanket `from: "*" / to: "*"` entry therefore cannot hide either: it suppresses crossings (counted) or it suppresses none (dead).

**Severity is `warn`, and expiry never changes what is suppressed.** A finding here is a statement about the CONFIGURATION, not about the code — the distinction BDL-061.48 drew for inert rules — and it is honoured harder in this case: a crossing does **not** reappear at `error` severity because a calendar day passed, because a build that reddens with no commit behind it is worse than the silence being fixed. A project that wants a hard deadline has `lint --fail-on-warn`.

**Named limit.** The suppressed count appears wherever a run could read as clean — `rich`, `--format json`, and the `0 violations, N rules evaluated` line the CLI prints when a piped run has nothing to report. It does **not** appear in `porcelain` output that already carries violations (one line per violation is the format's contract), nor in the Gate's own `N rules, 0 violations` step summary, which belongs to `application/gate.py`.

#### Rule liveness (a rule that cannot fire)

**A rule that cannot match is indistinguishable from a rule that passed.** Both contribute `0` violations and `1` to `N rules evaluated`. Every rule type therefore reports its own inertness instead of counting as clean — `rules/liveness.py` for the eight matcher/graph-based types, `evaluate_import_boundary_rules` for `forbid_import` (whose diagnosis falls out of the import scan it already runs).

**What "cannot fire" means, per rule type.** This table is the contract: a liveness check narrower than the invariant it names is the defect this section exists to close (BDL-UX #172, BDL-061.48).

| Rule type | Inert when | Reported by |
|-----------|------------|-------------|
| `deny` | its `from` or `to` matcher selects **0** nodes (an unknown `ref_id` is named as such; otherwise the tag or kind nobody carries is named) | `liveness.py` |
| `require` | its `for` selects **0** nodes — **or** its `has_edge_to` selects 0, in which case every node it matches would fail, which is equally broken | `liveness.py` |
| `forbid_cycles` | the graph holds **0** *live* (`active`) edges of the declared `edge_kind`(s), so there is no chain to walk | `liveness.py` |
| `forbid_import` | its `from` glob matches **0** indexed source files, or its `to` glob matches **0** indexed import paths | `evaluators.py` (a stale `exempt` entry: `exemptions.py`) |
| `forbid` (edge) | its `from`/`to` selects **0** nodes, or the graph holds **0** edges of its `edge_kind` | `liveness.py` |
| `layers` | fewer than **2** of its layers are populated (direction needs two layers to point between), or no live `edge_kind` edge runs between two layered nodes | `liveness.py` |
| `check` (cardinality) | its `for` selects **0** nodes, **or** no threshold is set at all (`max_symbols`, `max_files` and `min_doc_coverage` all unset), so nothing is compared | `liveness.py` |
| `unregistered_feature_candidate` | its `for` selects **0** nodes, or none of the nodes it selects declares a `source`, so it has no files to inspect | `liveness.py` |
| `module_coverage` | its `source_root` holds **0** modules, on disk or in the index — "complete coverage" of nothing | `liveness.py` |

`forbid_import` additionally reports a stale `exempt` entry — dead or expired, at most one finding per entry (`rules/exemptions.py`, from the counts the import scan already produced). That is a statement about an exemption, not about the rule, so it is **not** counted in `LintResult.rules_inert`; what those entries suppressed is counted separately, as `LintResult.violations_suppressed`. Two counters, because they answer two questions: *which of my rules cannot check anything* and *what did my checks catch and excuse*.

**Severity is always `warn`, whatever the rule declares.** A liveness finding is a statement about the *configuration*, never about the code: `error` would conflate "your architecture is broken" with "your check is broken", and would turn an adopter's green pipeline red on upgrade the moment they update Beadloom (BDL-061 CONTEXT). Being `warn` is not the same as being quiet — the finding is printed by default, appears in `--json` under `kind: "rule_liveness"`, and `LintResult.rules_inert` qualifies the rule count on the summary line (`13 rules evaluated, 2 of them unable to check anything`), so a green run cannot advertise checks that never looked.

**Two deliberate limits, named rather than left to be discovered:**

- Liveness is **silent on an empty graph** (no nodes) and, for `forbid_import`, on an index with no imports at all. That is a fact about the index, not about the rules — lint's header already says `0 files scanned` — and firing there would flood every fresh clone and every language Beadloom does not extract imports from.
- `deny` liveness is **matcher-based only**. An index with no *resolved* imports makes every `deny` rule inert too; that is again the index's property and lint's header states it (`0 imports resolved`).

#### `ForbidEdgeRule`

Forbids graph edges between matched nodes (operates on `edges` table, unlike DenyRule which checks `code_imports`).

| Field          | Type              | Description                                        |
|----------------|-------------------|----------------------------------------------------|
| `name`         | `str`             | Unique rule name.                                  |
| `description`  | `str`             | Human-readable description.                        |
| `from_matcher` | `NodeMatcher`     | Matches the source node.                           |
| `to_matcher`   | `NodeMatcher`     | Matches the target node.                           |
| `edge_kind`    | `str \| None`     | If set, restricts to edges of this kind.           |
| `severity`     | `str`             | `"error"` or `"warn"`.                             |

#### `LayerDef`

Defines a single architecture layer for use in `LayerRule`.

| Field  | Type   | Description       |
|--------|--------|-------------------|
| `name` | `str`  | Layer name.       |
| `tag`  | `str`  | Tag identifying nodes in this layer. |

#### `LayerRule`

Enforces dependency direction between ordered architecture layers.

| Field        | Type                  | Description                                             |
|--------------|-----------------------|---------------------------------------------------------|
| `name`       | `str`                 | Unique rule name.                                       |
| `description`| `str`                 | Human-readable description.                             |
| `layers`     | `tuple[LayerDef, ...]`| Ordered layers (top to bottom).                         |
| `enforce`    | `str`                 | `"top-down"` — higher layers may depend on lower, not reverse. |
| `allow_skip` | `bool`                | If `False`, forbids skipping intermediate layers (default `True`). |
| `edge_kind`  | `str`                 | Edge kind to check (default `"uses"`).                  |
| `severity`   | `str`                 | `"error"` or `"warn"`.                                  |

#### `CardinalityRule`

Enforces complexity limits per node (architectural smell detection).

| Field              | Type              | Description                                    |
|--------------------|-------------------|------------------------------------------------|
| `name`             | `str`             | Unique rule name.                              |
| `description`      | `str`             | Human-readable description.                    |
| `for_matcher`      | `NodeMatcher`     | Matches nodes to check.                        |
| `max_symbols`      | `int \| None`     | Maximum symbols a node OWNS (nested nodes excluded). |
| `max_files`        | `int \| None`     | Maximum files per node.                        |
| `min_doc_coverage` | `float \| None`   | Minimum documentation coverage: the fraction of the node's sync pairs NOT known to be behind (`stale`/`missing` excluded; a pair the freshness engine could not check is not counted against the docs — BDL-UX #175). |
| `severity`         | `str`             | `"error"` or `"warn"` (default `"warn"`).      |

#### `Rule` (type alias)

```python
Rule = DenyRule | RequireRule | CycleRule | ImportBoundaryRule | ForbidEdgeRule | LayerRule | CardinalityRule
```

#### `Violation`

| Field              | Type           | Description                                     |
|--------------------|----------------|-------------------------------------------------|
| `rule_name`        | `str`          | Name of the violated rule.                      |
| `rule_description` | `str`          | Description of the violated rule.               |
| `rule_type`        | `str`          | `"deny"`, `"require"`, `"cycle"`, `"forbid_import"`, `"forbid"`, `"layer"`, `"cardinality"`, or `"rule_liveness"` (a rule that cannot fire — see above). |
| `severity`         | `str`          | `"error"` or `"warn"`.                          |
| `file_path`        | `str \| None`  | Source file path (for deny/import violations).   |
| `line_number`      | `int \| None`  | Line number (for deny/import violations).        |
| `from_ref_id`      | `str \| None`  | Source node ref_id.                              |
| `to_ref_id`        | `str \| None`  | Target node ref_id.                              |
| `message`          | `str`          | Human-readable explanation of the violation.     |

### rules.yml Schema

Schema supports versions 1, 2, and 3. Version 3 adds the optional top-level `tags:` block for bulk tag assignments.

```yaml
version: 3

# Optional (v3): bulk tag assignments — tag_name: [ref_id, ...]
tags:
  layer-service: [cli, mcp-server, tui]
  layer-domain: [context-oracle, doc-sync, graph, onboarding]

rules:
  # --- deny: forbid imports between matched nodes ---
  - name: <unique-rule-name>
    description: "<description>"
    deny:
      from: { ref_id: ..., kind: ..., tag: ..., exclude: [...] }  # NodeMatcher
      to:   { ref_id: ..., kind: ..., tag: ..., exclude: [...] }  # NodeMatcher
      unless_edge: [<edge_kind>, ...]    # optional, defaults to []

  # --- require: mandate specific edge relationships ---
  - name: <unique-rule-name>
    description: "<description>"
    require:
      for:         { ref_id: ..., kind: ..., exclude: [...] }  # NodeMatcher
      has_edge_to: { ref_id: ..., kind: ... }  # NodeMatcher (or {} for any node)
      edge_kind: <edge_kind>                   # optional

  # --- forbid_cycles: detect circular dependencies ---
  - name: <unique-rule-name>
    description: "<description>"
    severity: warn                             # optional, default: error
    forbid_cycles:
      edge_kind: depends_on                    # string or list of edge kinds

  # --- forbid_import: file-level import boundaries ---
  # NOTE the two vocabularies: `from` matches the SOURCE FILE PATH (source root
  # included), `to` matches the DOTTED IMPORT PATH with dots -> slashes (no source
  # root, no extension). A `src/`-prefixed `to` can never match (BDL-UX #172).
  - name: <unique-rule-name>
    description: "<description>"
    forbid_import:
      from: "src/pkg/module_a/**"              # file path glob
      to: "pkg/module_b/**"                    # import path glob
      exempt:                                  # optional, baselines existing crossings
        - to: "pkg/module_b/atomic_io"         # `from` optional; at least one required
          reason: "<why this crossing is tolerated>"   # mandatory
          until: "<a YYYY-MM-DD deadline, or the event that retires it>"  # mandatory

  # --- forbid (forbid_edge): forbid graph edges between tagged groups ---
  - name: <unique-rule-name>
    description: "<description>"
    forbid:
      from: { tag: ui-layer }                  # NodeMatcher with tag
      to: { tag: native-layer }
      edge_kind: uses                          # optional

  # --- layers: enforce layered architecture ---
  - name: <unique-rule-name>
    description: "<description>"
    severity: warn
    layers:
      - name: services
        tag: layer-service
      - name: domains
        tag: layer-domain
      - name: infrastructure
        tag: layer-infra
    enforce: top-down                          # higher layers may depend on lower
    allow_skip: true                           # optional, default: true
    edge_kind: depends_on                      # optional, default: uses

  # --- check (cardinality): enforce complexity limits ---
  - name: <unique-rule-name>
    description: "<description>"
    severity: warn
    check:
      for: { kind: domain }                    # NodeMatcher
      max_symbols: 180                         # optional (Beadloom's domain-size-limit; counts OWNED symbols since BDL-UX #144)
      max_files: 50                            # optional
      min_doc_coverage: 0.8                    # optional
```

Each rule must contain exactly one of: `deny`, `require`, `forbid_cycles`, `forbid_import`, `forbid`, `layers`, or `check`.

### Loading and Parsing

```python
def load_rules(rules_path: Path) -> list[Rule]
```

1. Read and parse `rules_path` with `yaml.safe_load`.
2. Validate top-level `version` field is in `SUPPORTED_SCHEMA_VERSIONS` ({1, 2, 3}). Raise `ValueError` on mismatch or absence.
3. If version 3, parse optional top-level `tags:` block for bulk tag assignments.
4. Iterate `rules` list. For each entry:
   a. Require a non-empty string `name` field.
   b. Enforce unique names (tracked via `seen_names` set). Raise `ValueError` on duplicate.
   c. Require exactly one of `deny`, `require`, `forbid_cycles`, `forbid_import`, `forbid`, `layers`, or `check`. Raise `ValueError` if none or multiple are present.
   d. Parse the corresponding block into the appropriate rule dataclass.
5. `NodeMatcher` parsing validates: for deny rules, at least one of `ref_id`, `kind`, or `tag` must be present. For require rules, `has_edge_to` accepts an empty dict `{}` (matches any node) via `allow_empty=True`. `kind` (if present) is validated against `VALID_NODE_KINDS`. `exclude` accepts a string or list, normalized to a tuple.

### Validation Against Database

```python
def validate_rules(rules: list[Rule], conn: sqlite3.Connection) -> list[str]
```

Collects all `ref_id` values from all matchers across all rules (deny, require, forbid_edge, cardinality and unregistered-feature-candidate). Queries the `nodes` table for each. Returns a list of warning strings for any `ref_id` not found in the database. This is advisory (warnings, not errors).

**Its return value is consumed, not dropped.** Until BDL-061.48 `linter.py` called this function as a bare statement and discarded the list, so a rule naming `no-such-node-at-all` produced the exact right diagnosis and threw it away while `lint --strict` printed `13 rules evaluated, 0 violations` at exit 0. The unknown-`ref_id` question is now answered per rule by `liveness.py` (which names the ref_id in the finding, attributed to the rule that references it) and by this function for any rule kind the liveness pass does not model — one finding per rule, never two.

### Evaluation

#### Deny Rule Evaluation

```python
def evaluate_deny_rules(conn: sqlite3.Connection, rules: list[DenyRule]) -> list[Violation]
```

Algorithm:
1. Query all rows from `code_imports` where `resolved_ref_id IS NOT NULL`.
2. For each import row `(file_path, line_number, import_path, resolved_ref_id)`:
   a. Determine the source node by calling `_get_file_node(file_path, conn)`, which inspects `code_symbols.annotations` JSON for keys (`domain`, `service`, `feature`) whose values match a `nodes.ref_id`.
   b. Skip if no source node is found.
   c. Skip self-references (source == target).
   d. Look up full `(ref_id, kind)` for both source and target via `_get_node`.
   e. For each deny rule, check whether `from_matcher` matches the source and `to_matcher` matches the target.
   f. If both match, check for exemption: if `unless_edge` is non-empty, query `edges` table for any edge of those kinds between source and target. If found, skip.
   g. Otherwise, emit a `Violation`.

#### Require Rule Evaluation

```python
def evaluate_require_rules(conn: sqlite3.Connection, rules: list[RequireRule]) -> list[Violation]
```

Algorithm:
1. Fetch all `(ref_id, kind)` from the `nodes` table.
2. For each rule, iterate all nodes. If `for_matcher` matches a node:
   a. Query all outgoing edges from that node (`edges WHERE src_ref_id = ?`).
   b. For each edge, optionally filter by `edge_kind`. Look up the target node via `_get_node`.
   c. If any target matches `has_edge_to`, the node satisfies the rule.
   d. If no matching edge is found, emit a `Violation`.

#### Combined Evaluation

```python
def evaluate_all(conn: sqlite3.Connection, rules: list[Rule], *, project_root: Path | None = None) -> list[Violation]
```

Owned by `rules/__init__.py`. Partitions rules by type into `DenyRule`, `RequireRule`, `CycleRule`, `ImportBoundaryRule`, `ForbidEdgeRule`, `LayerRule`, `CardinalityRule`, `UnregisteredFeatureCandidateRule`, and `ModuleCoverageRule` lists. Calls the corresponding `evaluate_*` function for each type. Enriches each `Violation` with a deterministic `remediation` hint (via `_remediation_for`, a post-pass), then concatenates and sorts by `(rule_name, file_path or "")`. `project_root` (default: cwd) roots the on-disk module enumeration the `module-coverage` rule uses.

### Internal Helpers

| Function              | Description                                                                                    |
|-----------------------|------------------------------------------------------------------------------------------------|
| `_parse_node_matcher` | Parse a dict into a `NodeMatcher`, validating `kind` against `VALID_NODE_KINDS`. Accepts `allow_empty=True` for require rule targets. Normalizes `exclude` (string or list) to tuple. |
| `_parse_deny_rule`    | Parse a deny block into a `DenyRule` with validated matchers and `unless_edge`.                 |
| `_parse_require_rule` | Parse a require block into a `RequireRule` with validated matchers and optional `edge_kind`.    |
| `_parse_cycle_rule`   | Parse a forbid_cycles block into a `CycleRule` with edge_kind and optional max_depth.          |
| `_parse_import_boundary_rule` | Parse a forbid_import block into an `ImportBoundaryRule` with from/to glob patterns.  |
| `_parse_forbid_edge_rule`     | Parse a forbid block into a `ForbidEdgeRule` with from/to matchers and optional edge_kind. |
| `_parse_layer_rule`   | Parse a layers block into a `LayerRule` with ordered `LayerDef` entries.                       |
| `_parse_cardinality_rule`     | Parse a check block into a `CardinalityRule` with threshold fields.                      |
| `_get_file_node`      | Look up the owning node for a file via `code_symbols.annotations` JSON.                        |
| `_get_node`           | Return `(ref_id, kind)` tuple for a node, or `None`.                                          |
| `_edge_exists`        | Return `True` if an edge of any of the specified kinds exists between two nodes.               |

---

## API

### Public Functions

```python
def load_rules(rules_path: Path) -> list[Rule]: ...
def load_rules_with_tags(rules_path: Path) -> tuple[list[Rule], dict[str, list[str]]]: ...
def validate_rules(rules: list[Rule], conn: sqlite3.Connection) -> list[str]: ...
def evaluate_rule_liveness(conn: sqlite3.Connection, rules: list[Rule], *, project_root: Path | None = None) -> list[Violation]: ...
def inert_rule_names(conn: sqlite3.Connection, rules: list[Rule], *, project_root: Path | None = None) -> set[str]: ...
def evaluate_deny_rules(conn: sqlite3.Connection, rules: list[DenyRule]) -> list[Violation]: ...
def evaluate_require_rules(conn: sqlite3.Connection, rules: list[RequireRule]) -> list[Violation]: ...
def evaluate_cycle_rules(conn: sqlite3.Connection, rules: list[CycleRule]) -> list[Violation]: ...
def evaluate_import_boundary_rules(conn: sqlite3.Connection, rules: list[ImportBoundaryRule]) -> list[Violation]: ...
def evaluate_forbid_edge_rules(conn: sqlite3.Connection, rules: list[ForbidEdgeRule]) -> list[Violation]: ...
def evaluate_layer_rules(conn: sqlite3.Connection, rules: list[LayerRule]) -> list[Violation]: ...
def evaluate_cardinality_rules(conn: sqlite3.Connection, rules: list[CardinalityRule]) -> list[Violation]: ...
def evaluate_all(conn: sqlite3.Connection, rules: list[Rule], *, project_root: Path | None = None) -> list[Violation]: ...
```

### Public Classes

```python
@dataclass(frozen=True)
class NodeMatcher:
    ref_id: str | None = None
    kind: str | None = None
    tag: str | None = None
    exclude: tuple[str, ...] | None = None
    def matches(self, node_ref_id: str, node_kind: str, *, tags: set[str] | None = None) -> bool: ...

@dataclass(frozen=True)
class DenyRule:
    name: str
    description: str
    from_matcher: NodeMatcher
    to_matcher: NodeMatcher
    unless_edge: tuple[str, ...]
    severity: str = "error"

@dataclass(frozen=True)
class RequireRule:
    name: str
    description: str
    for_matcher: NodeMatcher
    has_edge_to: NodeMatcher
    edge_kind: str | None = None
    severity: str = "error"

@dataclass(frozen=True)
class CycleRule:
    name: str
    description: str
    edge_kind: str | tuple[str, ...]
    max_depth: int = 10
    severity: str = "error"

@dataclass(frozen=True)
class ImportBoundaryRule:
    name: str
    description: str
    from_glob: str
    to_glob: str
    severity: str = "error"

@dataclass(frozen=True)
class ForbidEdgeRule:
    name: str
    description: str
    from_matcher: NodeMatcher
    to_matcher: NodeMatcher
    edge_kind: str | None = None
    severity: str = "error"

@dataclass(frozen=True)
class LayerDef:
    name: str
    tag: str

@dataclass(frozen=True)
class LayerRule:
    name: str
    description: str
    layers: tuple[LayerDef, ...]
    enforce: str = "top-down"
    allow_skip: bool = True
    edge_kind: str = "uses"
    severity: str = "error"

@dataclass(frozen=True)
class CardinalityRule:
    name: str
    description: str
    for_matcher: NodeMatcher
    max_symbols: int | None = None
    max_files: int | None = None
    min_doc_coverage: float | None = None
    severity: str = "warn"

Rule = DenyRule | RequireRule | CycleRule | ImportBoundaryRule | ForbidEdgeRule | LayerRule | CardinalityRule

@dataclass(frozen=True)
class Violation:
    rule_name: str
    rule_description: str
    rule_type: str
    severity: str
    file_path: str | None
    line_number: int | None
    from_ref_id: str | None
    to_ref_id: str | None
    message: str
```

### CLI

```
beadloom lint [--format {rich,json,porcelain}] [--strict] [--no-reindex]
```

| Flag           | Default | Description                                                        |
|----------------|---------|--------------------------------------------------------------------|
| `--format`     | `rich`  | Output format: `rich` (colored tables), `json`, or `porcelain`.    |
| `--strict`     | `False` | Exit with code `1` if any violations are found.                    |
| `--no-reindex` | `False` | Read the index as-is. This is the READ-ONLY form: the default reindexes first and therefore WRITES `beadloom.db`. |

**Exit codes:**

| Code | Meaning                                   |
|------|-------------------------------------------|
| `0`  | No violations (or violations without `--strict`). |
| `1`  | Violations detected (with `--strict`).    |
| `2`  | Configuration error (missing/invalid `rules.yml`). |

---

## Invariants

- Rule names are unique within a single `rules.yml` file.
- Each rule contains exactly one of `deny`, `require`, `forbid_cycles`, `forbid_import`, `forbid`, `layers`, or `check` (never multiple, never none).
- Self-references (`source_ref_id == target_ref_id`) are skipped during deny evaluation and never produce violations.
- `evaluate_all` output is deterministically sorted by `(rule_name, file_path or "")`.
- `NodeMatcher.matches` returns `False` if `node_ref_id` is in `exclude`. Otherwise returns `True` only when all non-`None` fields match. An empty matcher (`NodeMatcher()`) matches any node.
- All `kind` values in matchers are validated against `VALID_NODE_KINDS` at parse time.
- All edge kind values (`unless_edge`, `edge_kind`) are validated against `VALID_EDGE_KINDS` at parse time.
- Rules support `error` and `warn` severity levels (default varies by rule type).

---

## Constraints

- `rules.yml` must declare a version in `SUPPORTED_SCHEMA_VERSIONS` ({1, 2, 3}). Unsupported versions are rejected with `ValueError`.
- `NodeMatcher` must have at least one of `ref_id`, `kind`, or `tag` in deny rules; providing none raises `ValueError`. In require rules, `has_edge_to` accepts empty `{}` for "any node" matching.
- Deny rules depend on the `code_imports` table being populated (typically via a prior `reindex` step).
- Without a reindex callback `lint()` opens the index **read-only** and leaves `beadloom.db` byte-identical; a missing index raises `LintError` (exit 2) instead of reporting `0 violations` against a database it had just created (BDL-UX #147). "No rules file" still returns an empty result without touching the index at all.
- Plain `lint` keeps exit 0 when error-severity violations are found without `--strict` — the exit code is unchanged so an adopter's pipeline does not turn red on upgrade — but the omission is now named on stderr.
- Require rules depend on the `nodes` and `edges` tables.
- `validate_rules` is advisory: it returns warnings but does not raise exceptions. A caller that ignores its return value has silently disabled it (BDL-UX #172).
- Rule liveness never changes an exit code: it is `warn`-only by design, so `beadloom ci` and `lint --strict` stay green over an inert rule while naming it.
- The `_get_file_node` helper relies on `code_symbols.annotations` being valid JSON with keys like `domain`, `service`, or `feature` whose values correspond to `nodes.ref_id`.

---

## Testing

### Parsing Tests

- **Valid deny rule.** Parse a well-formed deny rule YAML. Assert returned `DenyRule` has correct matchers and `unless_edge`.
- **Valid require rule.** Parse a well-formed require rule YAML. Assert returned `RequireRule` has correct matchers and `edge_kind`.
- **Missing version.** Assert `ValueError` on `rules.yml` without `version`.
- **Wrong version.** Assert `ValueError` on `version: 2`.
- **Duplicate name.** Assert `ValueError` when two rules share a name.
- **Both deny and require.** Assert `ValueError` when a rule has both blocks.
- **Neither deny nor require.** Assert `ValueError` when a rule has neither block.
- **Invalid node kind.** Assert `ValueError` for `kind: "unknown"` in a matcher.
- **Invalid edge kind.** Assert `ValueError` for `unless_edge: ["unknown"]`.
- **Matcher missing both fields.** Assert `ValueError` when `NodeMatcher` has neither `ref_id` nor `kind` (in deny rules).
- **Empty matcher in require rules.** Assert `has_edge_to: {}` parses successfully and matches any node.
- **Empty matcher detects violations.** Assert nodes without outgoing edges of the required kind produce violations.
- **Empty matcher satisfied.** Assert adding any `part_of` edge satisfies the empty-matcher rule.
- **Empty for-matcher rejected in deny.** Assert empty matchers are still rejected in deny rule positions.

### Deny Evaluation Tests

- **Violation detected.** Insert nodes, a code_import, and code_symbols annotation creating a forbidden path. Assert one `Violation` with correct `rule_name`, `file_path`, `line_number`, `from_ref_id`, `to_ref_id`.
- **Exemption via unless_edge.** Add an edge of the exempted kind. Assert no violations.
- **Self-reference skipped.** Import where source and target resolve to the same node. Assert no violations.
- **No matching import.** Imports that do not match `from_matcher` or `to_matcher`. Assert no violations.

### Require Evaluation Tests

- **Violation detected.** Create a node matching `for_matcher` with no outgoing edge to the required target. Assert one `Violation`.
- **Satisfied.** Create a node with a matching outgoing edge. Assert no violations.
- **Edge kind filter.** Require a specific `edge_kind`. Assert violation when edge exists but with wrong kind.

### Validation Tests

- **Unknown ref_id warning.** Create rules referencing a `ref_id` not in `nodes`. Assert `validate_rules` returns a warning string.
- **All ref_ids exist.** Assert empty warning list.

### Liveness Tests (`tests/test_rule_liveness_all_types.py`)

One **pair** per rule type — an inert rule that must be reported, and a live rule of the same type on the same fixture that must not be. The live half is the non-vacuity guard: without it, "everything is inert" would satisfy every other assertion.

- **Every rule type reports its own inertness.** Nine rules, one of each type, all inert on a populated graph. Assert the reported set equals all nine names — a gap says *which* type is missing rather than "some count differs".
- **Exactly once.** Assert one finding per inert rule (an audit that affirms one fact twice is BDL-UX #173).
- **Always `warn`.** Nine `severity: error` rules, all inert. Assert every finding is `warn` and `has_errors` is `False` — the adopter-safety invariant, asserted rather than assumed.
- **Silent on an empty index.** Assert the same nine rules produce nothing against an empty schema.
- **End to end.** Drive the reproduction from `beadloom-mr2l.7` (a `require` naming `no-such-node-at-all`) through the real CLI; assert the unknown ref_id is named, `lint --strict` exits **0**, and the JSON payload carries `kind: "rule_liveness"` and `summary.rules_inert == 1`. Exit codes and `--json` only, never piped line counts (BDL-UX #148).

### Exit-condition Tests (`tests/test_exit_condition_expiry.py`)

Both surfaces that require an exit condition are covered in ONE file on purpose: `forbid_import.exempt[].until` and `guards.<name>.exclusions[].until` share one grammar, and a file per surface is how the two would drift into promising different things.

- **The grammar.** A bare ISO date is a deadline; a date LEADING a sentence is a deadline; a date mid-sentence, `2026-1-1`, `20260101`, `2026-W01-1` and prose are all events. The rejected spellings include the two `date.fromisoformat` accepts on Python 3.11+ and rejects on 3.10 — the assertion that keeps the grammar interpreter-independent.
- **Expiry, with its non-vacuity twin.** Same fixture, same exemption, only the date differs: a past deadline is reported, a future one is not. `until` equal to *today* is not expired (a deadline names the last day it covers); yesterday is.
- **Expiry does not enforce.** The crossing under an expired exemption is still suppressed — no `forbid_import` violation, `has_errors` `False`. A build must not redden because a day passed.
- **One entry, one finding.** A dead *and* expired entry is reported once (the dead half already says "delete it").
- **The count.** Two crossings behind one exemption count as two; a rule with no exemptions counts zero (the counter must be able to say zero); the clean summary line grows the clause only when the count is non-zero.
- **The reviewer's probe, end to end.** A wildcard exemption dated `1999-01-01` over a real error-severity crossing: `lint --strict` exits **0** and the JSON payload carries the finding and `summary.violations_suppressed`; `--fail-on-warn` exits **1**. Exit codes and `--json` only, never piped line counts (BDL-UX #148).
- **This repository's own entries.** Every `until:` in `.beadloom/_graph/rules.yml` that names a date is asserted to be in the future — the suite reddens the day one of our own baselines outlives its deadline.

### Combined Evaluation Tests

- **Mixed rules.** Combine deny and require rules. Assert violations from both types are returned and sorted correctly by `(rule_name, file_path)`.
- **Empty rules list.** Assert `evaluate_all` returns an empty list.
