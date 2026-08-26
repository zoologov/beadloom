# PLAN: BDL-062 — Graph metadata is an unchecked surface

> **Status:** Approved
> **Created:** 2026-08-26

---

## Beads

| # | Role | Title | Depends on |
|---|---|---|---|
| .1 | dev | `graph_summary_facts` rule — a numeric claim in a node summary is checked | — |
| .2 | dev | `doc_area_coherence` rule — convention derived from the graph, not hardcoded | — |
| .3 | dev | The audit stops describing itself; three populations, not one | — |
| .4 | dev | The corrections: five drifts, three undocumented nodes, package description | .1, .2, .3 |
| .5 | test | Bite tests for all three rules + an adopter fixture that is not Beadloom | .4 |
| .6 | review | Read-only verification, clean room | .5 |
| .7 | tech-writer | README (en + ru) + guides state what 3.x is | .6 |
| .8 | chore | Release 3.0.1 | .7 |

`.1`, `.2`, `.3` are independent and run as one wave. `.4` follows because it is what the
rules make red today — the corrections are verified by the rules, not by inspection.

## Waves

```
wave 1   .1 ─┐
         .2 ─┼─→  .4  →  .5  →  .6  →  .7  →  .8
         .3 ─┘
        (dev)     dev    test   review  t-w    release
```

## Per-bead acceptance

**.1 `graph_summary_facts`** — Queries `nodes.summary` from the indexed graph; consumes the
audit's fact set; reuses the audit's `_VERSION_RE` and `FACT_KEYWORDS` rather than growing a
second notion of "a version". Reports four states — `agrees` / `disagrees` /
`no claim` / `unverifiable` — and `unverifiable` never folds into pass. **Acceptance: the
rule is RED on `main`@`cdc16de`, naming `beadloom` (v1.5.0 ≠ 3.0.0) and `mcp-server`
(14 ≠ 18).** Capture that output before `.4` corrects anything.

**.2 `doc_area_coherence`** — Derives the segment→segment mapping from the graph under test.
No layout literal anywhere in the rule. Configurable majority threshold; the output states
the sample size and the threshold, so 69/73 is legible to a reader. **When no dominant
mapping exists the rule reports it checked nothing and the gate line says so.** Ships `warn`;
this repository escalates to `error` in config. Acceptance: names exactly `doctor`,
`watcher`, `debt-report`, `reindex` here, and reports `unverifiable` on a fixture with a flat
docs tree.

**.3 The audit stops describing itself** — `mcp_tool_count` and `cli_command_count` derive
from the audited project or are declared not applicable, with the reason. `docs audit`
reports **verified / not applicable / declared-but-unverified** as separate populations;
`version` at zero mentions lands in the third and becomes visible. JSON gains fields, keeps
existing ones (a test pins that — 3.0.1 is a patch). Acceptance: on a synthetic non-Beadloom
fixture, no declared fact carries a value read from Beadloom's own source; on this
repository, output is unchanged.

**.4 The corrections** — root summary (version + `Doc Sync v2 Engine`); `mcp-server` 14→18;
`doctor`/`watcher`/`debt-report`/`reindex` `docs:` to `docs/domains/application/…` **with the
files moved, not just the declaration**; `cli-commands`/`status`/`vitepress-site` each get a
SPEC or a recorded reason; `pyproject.toml:8` + `src/beadloom/__init__.py` description.
Acceptance: `beadloom ci` green, and reverting any single correction turns it red.

**.5 test** — A bite test per rule. An adopter fixture that is genuinely not Beadloom
(FAKES PROVE FAKES: a fixture that cannot exhibit the self-fact leak proves nothing about
it). A no-dominant-convention fixture for `.2`'s unverifiable path. A JSON back-compat test
for `.3`.

**.6 review** — Clean room (`git archive HEAD` + only the branch's files). Confirms the
`unverifiable` paths are reachable and reported, not merely coded — NO CALLER NO CAPABILITY.

**.7 tech-writer** — README.md and README.ru.md and the guides describe 3.x: guards, waves,
doc spaces, federation. Every count in prose re-derived, not copied. The stale "14 tools"
class is checked across all docs, not fixed where remembered.

**.8 release** — version bump, CHANGELOG, tag, PyPI, and verification from the published
artifact in a fresh venv — not the local build.

## Not in this plan

Positioning and the model, both deferred with reasons in CONTEXT.md. Neither blocks any
bead above.
