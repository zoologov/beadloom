# BDL-011 — UX Feedback Log

> Collected during implementation of Plug & Play Onboarding.
> Format: `[DATE] [SEVERITY] Description — Context`

---

## Closed Issues

1. ~~[2026-02-13] [MEDIUM] `doctor` warns about auto-generated skeleton docs as "unlinked from graph"~~ **FIXED** — Root cause was `generate_skeletons()` writing to wrong paths (`docs/features/` instead of `docs/domains/{parent}/features/`). Fixed by using `docs:` paths from graph + correct convention fallback. Doctor now shows 0 warnings.

2. ~~[2026-02-13] [LOW] `lint` produces no output on success~~ **FIXED** — When formatter returns empty (porcelain with 0 violations), CLI now prints `"0 violations, N rules evaluated"` as confirmation.

3. ~~[2026-02-13] [LOW] `docs generate` creates skeleton files for services including the root~~ **FIXED** — Root detection changed from "empty source" to "no `part_of` edge as src". Root node is now correctly skipped regardless of source path.

4. ~~[2026-02-13] [INFO] MCP server description says "8 tools" / CLI "18 commands"~~ **FIXED** in BEAD-11 — services.yml updated to 20 commands, 9 tools.

---

## Open Issues (dogfooding on cdeep — Django + Vue monolith, 44 nodes)

5. [2026-02-13] [HIGH] `doctor` shows all docs as "unlinked from graph" on freshly bootstrapped projects — `bootstrap_project()` generates graph nodes without `docs:` field. Generated doc files have no `beadloom:domain=X` annotations. Result: 44 "unlinked" warnings + 44 "no doc linked" infos + **0% doc coverage** in `status`. Fix: `generate_skeletons()` should write `docs:` paths back into `services.yml` after creating files.

6. [2026-02-13] [HIGH] `lint` rules too strict for hierarchical projects — `domain-needs-parent` rule requires `part_of` to root node (`cdeep`), but sub-domains like `apps-accounts` are `part_of apps` (their parent domain), not `part_of cdeep`. Produces 25+ false positive violations. Fix: `generate_rules()` should generate `has_edge_to: {kind: domain}` for sub-domains, or change to "every domain must have at least one `part_of` edge" (requires rule engine enhancement to support `has_edge_to: any`).

7. [2026-02-13] [MEDIUM] Dependencies section always empty in skeletons for new projects — `depends_on` edges are created by import resolver during `reindex`, but `generate_skeletons()` runs before reindex in the bootstrap pipeline. All skeletons show "Depends on: (none), Used by: (none)". `docs polish --format json` also shows empty depends_on despite context oracle knowing 7 depends_on edges for `apps-accounts`. Fix: `generate_polish_data()` should read edges from SQLite (post-reindex) instead of only from YAML.

8. [2026-02-13] [MEDIUM] `docs polish` text format nearly useless — Outputs a single line (AI instruction prompt) with no node data. JSON format works well but text format should include at least a node list with key symbols and deps for human review. Currently: `wc -l` = 1 line for 44-node project.

9. [2026-02-13] [LOW] Summaries are generic — Auto-generated summaries like "Domain: accounts (78 files)" just repeat the directory name and file count. Could detect key patterns (Django app → "Django app: accounts", Vue feature → "Vue feature module") or include top-level symbol names for richer first impression.

10. [2026-02-13] [LOW] `service-needs-parent` rule applies to root node — Rule requires ALL services to have `part_of cdeep`, but `cdeep` itself is a service (root). The root node is excluded from doc generation but not from rule evaluation. Produces 1 false positive. Fix: either exclude root from rule target, or `generate_rules()` should add `exclude: {ref_id: root}` (requires rule engine enhancement).
