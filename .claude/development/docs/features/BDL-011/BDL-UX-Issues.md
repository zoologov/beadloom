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

## Open Issues (dogfooding on cdeep — Django + Vue, 44 nodes; dreamteam — React Native + TS, 6 nodes)

5. [2026-02-13] [HIGH] `doctor` shows all docs as "unlinked from graph" on freshly bootstrapped projects — `bootstrap_project()` generates graph nodes without `docs:` field. Generated doc files have no `beadloom:domain=X` annotations. Result: 44 "unlinked" warnings + 44 "no doc linked" infos + **0% doc coverage** in `status`. Reproducible on both cdeep (44 warns) and dreamteam (24 warns). Fix: `generate_skeletons()` should write `docs:` paths back into `services.yml` after creating files.

6. [2026-02-13] [HIGH] `lint` rules too strict for hierarchical projects — `domain-needs-parent` rule requires `part_of` to root node, but sub-domains are `part_of` their parent domain. Produces 25+ false positives on cdeep. Also `service-needs-parent` catches root node itself (1 false positive on dreamteam). Fix: `generate_rules()` should either (a) target only top-level nodes, or (b) change to "every domain/service must have at least one `part_of` edge" — requires rule engine `has_edge_to: any` support.

7. [2026-02-13] [MEDIUM] Dependencies section always empty in skeletons — `depends_on` edges are created by import resolver during `reindex`, but `generate_skeletons()` runs before reindex. All skeletons show "Depends on: (none)". Also `docs polish --format json` shows empty depends_on despite context oracle knowing real edges. Fix: `generate_polish_data()` should read edges from SQLite (post-reindex) instead of only from YAML.

8. [2026-02-13] [MEDIUM] `docs polish` text format nearly useless — Outputs a single line (AI instruction prompt) with no node data. JSON format works well but text format should include at least a node list with symbols and deps. `wc -l` = 1 line for 44-node project.

9. [2026-02-13] [LOW] Summaries are generic — "Domain: accounts (78 files)" / "Service: valhalla (5 files)" just repeat the directory name and file count. Could detect patterns (Django app, React component, service) or include top-level symbol names.

10. [2026-02-13] [LOW] `ref_id` naming for Expo router dirs — `(tabs)` becomes a ref_id with parentheses. While valid, it looks unusual in graphs and docs. The `services/(tabs).md` filename also looks odd. Consider stripping parens or using a naming convention.

11. [2026-02-13] [MEDIUM] `uv tool install beadloom` doesn't include language parsers — tree-sitter-typescript/go/rust are in `[project.optional-dependencies] languages`. Fresh install gives 0 symbols on TS projects. User must know to run `uv tool install beadloom[languages]`. The bootstrap output says "0 symbols" with no hint about missing parsers. Fix: either make language parsers required deps, or detect missing parsers and print a warning during reindex.

12. [2026-02-13] [LOW] `reindex` says "No changes detected" after installing missing parsers — Incremental reindex checks file hashes, not parser availability. After adding tree-sitter-typescript, `beadloom reindex` still shows 0 symbols. User must know to run `beadloom reindex --full`. Fix: detect when new languages become available and trigger full reindex.

13. [2026-02-13] [INFO] Bootstrap reports "5 skeletons" but architecture.md pre-existed — On dreamteam, `docs/ARCHITECTURE.md` (72KB, hand-written) already existed. macOS case-insensitive FS correctly prevented overwrite, but the "5 skeletons" count in bootstrap output implies it was created. Minor: count should distinguish "created" vs "skipped".

14. [2026-02-13] [MEDIUM] Preset auto-detect misclassifies mobile apps as microservices — dreamteam is a React Native (Expo) mobile app, but `detect_preset()` sees `services/` dir and picks `microservices`. In mobile context, `services/mapbox/` and `services/valhalla/` are internal API modules, not independent services. Result: all dirs under `app/` and `services/` become top-level service nodes instead of features/domains within a monolith. Fix: `detect_preset()` should check for mobile indicators (app.json, expo, react-native in package.json) and prefer `monolith` for single-app projects.
