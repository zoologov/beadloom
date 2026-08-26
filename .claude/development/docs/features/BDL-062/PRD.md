# PRD: BDL-062 — Graph metadata is an unchecked surface

> **Status:** Approved
> **Created:** 2026-08-26

---

## Problem

Beadloom sells the absence of drift. Its own graph has drifted, and every check passed
while it did.

This is measured, not suspected. On `main` at `cdc16de` — the 3.0.0 release commit — with
`beadloom ci` green:

| Where | Declares | Actually |
|---|---|---|
| `services.yml:5` root node | `Doc Sync v2 Engine (v1.5.0)` | 3.0.0 — two majors behind |
| `services.yml:131` `mcp-server` | `14 tools` | 18 (`MCP_TOOL_CATALOG`) |
| 4 nodes (`doctor`, `watcher`, `debt-report`, `reindex`) | `docs: docs/domains/infrastructure/…` | `source: src/beadloom/application/…` |
| 3 nodes (`cli-commands`, `status`, `vitepress-site`) | — | no `docs:` at all |
| `pyproject.toml:8`, `__init__.py` | `Context Oracle + Doc Sync Engine` | the 1.x product description, live on the PyPI page |

The cause is structural. **No rule reads the `summary` field** — grepping every rule in
`src/beadloom/graph/rules/` for `summary` returns one unrelated docstring line. And
`sync-check` compares a doc/code pair's *content freshness*; it never asks whether the pair
is *in the right place*. So a node can name a version from eighteen months ago, or document
itself under a package it does not live in, and the gate has nothing to say.

`docs audit` is the painful part: it **already computes both stale facts**. `version` and
`mcp_tool_count` are two of its nine declared facts. It verifies `mcp_tool_count` against
thirteen mentions in prose and never looks at the graph, because its scan surface is
markdown by construction (`DEFAULT_SCAN_GLOBS = ("*.md", "docs/**/*.md", ".beadloom/*.md")`).
The mechanism exists. The surface was never connected.

And `version` sits at `not_covered` with **zero mentions** — a fact declared, verified by
nothing, reported in a shape that reads as fine until you open the JSON. BDL-061 S4 taught
the audit to say "2 of 9 verified". It never taught it to ask why the other seven are not.

### A second defect, found while verifying the first

Two of the nine facts are not about the project being audited:

```python
from beadloom.infrastructure.mcp_tools import MCP_TOOL_CATALOG
from beadloom.infrastructure.surface_registry import get_cli_group

def _collect_mcp_tool_count(self, facts):   # takes no project_root
```

`mcp_tool_count` and `cli_command_count` count **Beadloom**, unconditionally, with no
project parameter and no config gate. In any adopter's repository `beadloom docs audit`
declares two facts about the tool as facts about their documentation — and counts them in
the denominator of "N of 9 verified". If an adopter's README states a tool count for their
own MCP server, it is checked against ours.

This ships today, in 3.0.0, independent of anything else in this feature.

## Goals

- The graph's own metadata is checked by the same machinery that checks prose.
- A fact nothing verifies says so, instead of resting silently at `not_covered`.
- A node documenting itself outside its own area is named.
- An adopter's audit describes the adopter's project, or declines to.
- The five factual drifts above are corrected and released as 3.0.1.
- README (en + ru) and the guides state what 3.0.0 actually is.

## Non-goals

- **Positioning.** Whether the lead should say "source of truth about your code", who the
  README addresses first, and whether one name covers three products — an owner decision,
  not a patch. Tracked separately.
- **The model.** `application` as a join layer carrying `kind: domain`, `services.yml` at
  84 nodes in one file, `onboarding` no longer matching its contents — an epic, not a fix.
- Changing what facts the audit computes beyond making the existing nine honest.

## Success criteria

1. Reverting any one of the five corrections turns `beadloom ci` red, with the failing line
   naming the node and the disagreeing value. (TESTS MUST BITE)
2. The new rules run against `_graph/*.yml` generically — no hardcoded doc layout, no
   assumption of a ddd tree; an fsd project with a different area naming passes or reports
   `unverifiable`, never a silent pass.
3. `docs audit` in a project that is not Beadloom declares no fact whose value came from
   Beadloom's own source. Proven on a synthetic adopter fixture, not asserted.
4. When a graph has no dominant `docs:`↔`source:` convention, the coherence rule reports
   that it checked nothing, and `beadloom ci` says so. (unverifiable ≠ clean)
5. 3.0.1 on PyPI; the package description on the project page describes 3.x.

## Out of scope for the release

The three mechanism beads may land after 3.0.1 if the factual corrections are ready first;
the release is not gated on the rules. The rules are gated on nothing — they exist so the
sixth instance is caught by a machine rather than by the owner reading YAML.
