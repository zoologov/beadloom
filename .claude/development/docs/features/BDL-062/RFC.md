# RFC: BDL-062 — Graph metadata is an unchecked surface

> **Status:** Approved
> **Created:** 2026-08-26

---

## Summary

Three mechanisms and one correction pass. The mechanisms make the graph's own metadata a
checked surface; the correction pass fixes what they find today. Released as 3.0.1.

## Why the rules live in the lint engine, not in `docs audit`

The audit's scanner is markdown by construction:

```python
DEFAULT_SCAN_GLOBS = ("*.md", "docs/**/*.md", ".beadloom/*.md")
FACT_KEYWORDS = {"version": [], "mcp_tool_count": ["MCP", "tool", ...], ...}
```

It finds facts by keyword proximity in prose. Teaching it YAML means teaching it a second
parsing model for a second file shape — the wrong seam.

The lint engine already reads the graph, and reads it in the form that matters:

```
nodes(ref_id, kind, summary, source, extra, lifecycle)
docs(id, path, kind, ref_id, metadata, hash, space)
```

`summary`, `source` and the node's documents are all **already indexed**. This settles the
generality question directly: the rules never touch `services.yml`, `rules.yml`, or any
other file by name. They query the indexed graph, and indexing is what normalizes every
`_graph/*.yml` in any project into those two tables. A project with one graph file or
twelve, ddd or fsd, Python or TypeScript, reaches the rules through the same schema.

The audit keeps its job — computing facts about the project. The rules consume that fact
set. Neither grows a copy of the other.

## R1 — `graph_summary_facts`

**Claim checked:** a numeric or version claim in a node's `summary` agrees with the same
fact computed from the project.

Fact values come from the audit's collector (`version`, `node_count`, `edge_count`,
`language_count`, `test_count`, `framework_count`, `rule_type_count`, plus whatever
`docs_audit.extra_facts` declares). The rule extracts candidate claims from each summary —
a version literal via the audit's existing `_VERSION_RE`, and `N <keyword>` forms via the
audit's existing `FACT_KEYWORDS` — and compares.

Reusing the audit's regex and keyword table is deliberate: a second, subtly different
notion of "a version" in the codebase is how the next drift class starts.

Verdicts, and the distinction the epic exists to defend:

| State | Meaning | Gate |
|---|---|---|
| `agrees` | claim found, matches computed fact | pass |
| `disagrees` | claim found, differs | **error**, names node + both values |
| `no claim` | summary states no checkable fact | pass, counted separately |
| `unverifiable` | the fact could not be computed for this project | **reported**, never folded into pass |

`unverifiable` is the load-bearing row. A project with no resolvable version must not get
the same word as a project whose summaries were all checked.

**Today this rule is red**: `beadloom` root (`v1.5.0` ≠ `3.0.0`), `mcp-server` (`14 tools`
≠ 18). That redness is the acceptance test, captured before the correction lands.

## R2 — `doc_area_coherence`

**Claim checked:** a node documents itself where its own graph says nodes like it are
documented.

No layout is hardcoded — that was the flaw in the first sketch of this rule, and it would
have shipped our ddd tree as everyone's. Instead the rule **derives the convention from the
graph it is given**:

1. For each node with both a `source` path and a `docs` path, extract the distinguishing
   path segment from each (the segment below the source root; the segment below the docs
   root).
2. Build the observed segment→segment mapping and its agreement counts.
3. A mapping is *dominant* when it covers a configurable majority of the sampled pairs.
4. Nodes contradicting a dominant mapping are violations. Nodes under no dominant mapping
   are not.

On this repository: **69 agree, 4 differ** — `doctor`, `watcher`, `debt-report`, `reindex`,
all `source: src/beadloom/application/…` documented under `docs/domains/infrastructure/…`.
A clean signal against a strong majority.

**When there is no dominant mapping the rule reports that it checked nothing**, and the
gate line says so. A flat docs tree, a project mid-migration, a graph of six nodes — all
legitimately unverifiable, and none of them is clean. This is the `rule_liveness` contract
from BDL-061 applied to a rule whose applicability is data-dependent rather than
configuration-dependent.

Severity: **warn** on first ship. It is a convention check, and a convention check that
blocks an adopter's first `beadloom ci` on their own house style is a rule they will
disable. It earns `error` on this repository via config, where the convention is ours.

## R3 — the audit stops describing itself

```python
from beadloom.infrastructure.mcp_tools import MCP_TOOL_CATALOG
from beadloom.infrastructure.surface_registry import get_cli_group
```

`_collect_mcp_tool_count` takes no `project_root`. `_collect_cli_command_count` counts the
running Click group. Both are unconditional, so both describe Beadloom in every project.

Fix: derive them from the project under audit, or do not declare them.

- `mcp_tool_count` — from the audited project's own graph/config where it declares an MCP
  surface; otherwise not applicable.
- `cli_command_count` — same, from the project's declared CLI surface.
- When the running project *is* Beadloom, the existing values are what the derivation
  returns, so this repository's audit output is unchanged. That equality is a test.

And the denominator changes shape. Today a fact that cannot be computed is "silently
omitted" (the collector's own docstring), which is the S4 defect wearing different
clothes — nine declared, two computed from the wrong project, `version` resting at
`not_covered` with zero mentions and nothing saying that is unusual.

After R3 the audit reports three populations, not one: **verified**, **not applicable to
this project** (with the reason), and **declared but unverified** (named, not counted as
fine). `version` at zero mentions belongs to the third and will be visible.

## R4 — the corrections

Mechanical, once R1–R3 exist to hold them:

- `services.yml:5` root summary — the version claim, and `Doc Sync v2 Engine`, a subsystem
  name that no longer describes the product.
- `services.yml:131` `mcp-server` — 14 → 18.
- `doctor`, `watcher`, `debt-report`, `reindex` — `docs:` moved to `docs/domains/application/…`,
  files moved with them. Moving the declaration without the file trades one drift for another.
- `cli-commands`, `status`, `vitepress-site` — no `docs:` at all. Each gets a SPEC or a
  recorded reason it has none.
- `pyproject.toml:8` and `src/beadloom/__init__.py` — the 1.x description, live on the PyPI
  project page. This is the one item that genuinely requires a release to take effect.

## Risks

**R1 false positives on prose numbers.** A summary reading "supports 3 kinds of node" could
collide with an unrelated count. Mitigated by reusing the audit's keyword proximity rather
than matching bare integers, and by `warn` for the first release of the rule on any project
but this one.

**R2's majority threshold is a judgement.** Set it too low and a small graph gets a
convention invented for it; too high and real conventions go unchecked. It ships
configurable, with the chosen default stated in the rule's output alongside the sample size
— a reader can see 69/73 and judge the verdict themselves.

**R3 changes audit output shape.** The three-population report is a breaking change to
anything parsing `docs audit --json`. 3.0.1 is a patch release; the JSON gains fields and
keeps the existing ones, and that constraint is a test.

## Alternatives rejected

- **Add `_graph/*.yml` to the audit's scan globs.** Rejected above: it makes a markdown
  keyword scanner parse YAML.
- **Hardcode `docs/domains/<package>/`.** Ships our layout as everyone's; breaks fsd.
- **Fix the five drifts and skip the rules.** This is the fifth time this epic family has
  found the same class by hand. Hand-finding does not scale to the sixth.
