# ACTIVE: BDL-051 (EPIC) — Beadloom governs itself

> **Last updated:** 2026-06-11

---

## Current Focus

- **Phase:** S2 MERGED (PR #8). ai_agents domain live. S2+S4 MERGED. S3 EXPANDED (owner): component kind + COVERAGE-lint + classify-all. EPIC COMPLETE — S1/S2/S3a/S3b/S4 all merged; tech-writer .13 done (filling SPEC/DOCs); all 17 beads + epic closed. Merging the .13 docs PR. POLICY: [skip ai-techwriter] on slice-PRs (per-slice agent ~15min — untenable); all docs in tech-writer .13. Reinforces BDL-052 (non-blocking).
- **Branch:** `features/BDL-051` (trunk-based; each slice is its own PR via ci.yml).
- **Coordinator:** main loop (multi-agent).
- **Parent:** `beadloom-mukc`

## Beads

| Bead | Role | Status |
|------|------|--------|
| beadloom-mukc.1 | dev — S1 def + sprawl lint | ✓ done |
| beadloom-mukc.2 | test — S1 lint | ✓ done |
| beadloom-mukc.3 | review — S1 | ✓ done |
| beadloom-mukc.4 | dev — S2 ai_agents move + retire vendoring | ✓ done |
| beadloom-mukc.5 | test — S2 | ✓ done |
| beadloom-mukc.6 | review — S2 | ✓ done |
| beadloom-mukc.7 | dev — S3a component kind + coverage-lint + exempt | ✓ done |
| beadloom-mukc.8 | test — S3a | ✓ done |
| beadloom-mukc.9 | review — S3a | ✓ done |
| beadloom-mukc.14 | dev — S3b classify ALL modules + nodes + SPEC skeletons | ✓ done |
| beadloom-mukc.15 | test — S3b | ✓ done |
| beadloom-mukc.16 | review — S3b | ✓ done |
| beadloom-mukc.10 | dev — S4 ACTIVE-table fix + adopt | ✓ done |
| beadloom-mukc.11 | test — S4 | ✓ done |
| beadloom-mukc.12 | review — S4 | ✓ done |
| beadloom-mukc.13 | tech-writer (epic close) | ✓ done |

## Waves (trunk-based: one slice-PR at a time)

W1 (S1) `.1→.2→.3` → W2 (S2) `.4→.5→.6` → W3 (S3) `.7→.8→.9` → W4 (S4) `.10→.11→.12` → W5 `.13` → close.

## Key decisions (from PRD/RFC/CONTEXT)

- 4 trunk-based slices; S1 def+sprawl-lint gates all.
- Sprawl-lint `unregistered-feature-candidate` (warn): per-domain files with `domain=`/no-`feature=`/≥N symbols (N=5).
- ai_agents: move `tools/ai_techwriter → src/beadloom/ai_agents/ai_techwriter/`; **retire vendoring** (ships in package; `python -m beadloom.ai_agents.ai_techwriter`); recipe/provisioner → package-data; boundary rule.
- onboarding features: config-check, branch-protection, agentic-flow-setup, ai-techwriter-setup.
- ACTIVE-table maintenance in MCP checkpoint/complete_bead + coordinator adoption. Orchestration stays main-loop (G4).

## Progress Log

- 2026-06-11: PRD/RFC/CONTEXT/PLAN approved; epic `beadloom-mukc` + 13 beads + DAG; branch `features/BDL-051`. W1 (S1) launched (.1 dev).

- 2026-06-11: **S1 MERGED** (#7). Gate caught a config-drift (AGENTS.md stale after new rule) my local sync/lint missed → fixed via config-check --fix (lesson: run full `beadloom ci` pre-push). ai-techwriter on the slice ran ~16min (wide domain-doc drift) → established [skip-on-slices] policy, docs → .13.

- 2026-06-11: **S2 / BEAD-04 dev impl complete (NOT committed).** `git mv tools/ai_techwriter → src/beadloom/ai_agents/ai_techwriter/` (history preserved) + `ai_agents/__init__.py`; recipe.yaml + provision-runner.sh now ride as package data (importlib.resources; `provider.default_recipe_path` rewritten; pyproject `force-include` + verified in built wheel). All imports/CI/templates → `beadloom.ai_agents.ai_techwriter`; console script `beadloom-ai-techwriter`. **Vendoring RETIRED**: removed HARNESS_MODULES/vendor_harness/sync_vendored_harness + `templates/ai_techwriter/harness/*.py.txt`; setup-ai-techwriter now emits workflow+guide+operator recipe/provisioner (no Python vendored); tests updated to no-vendoring reality. Graph: `ai_agents` domain + `ai-techwriter` feature nodes+edges+README+SPEC; per-module `domain=`/`feature=` annotations. Boundary: `core-no-import-ai-agents` + `application-no-import-ai-agents` forbid_import rules (error severity; fnmatch `[!a]*` / `a[!i]*` exclude ai_agents self-imports). Full `beadloom ci` rc0 (only pre-existing S3-deferred warn-level sprawl/size warnings), doctor rc0, lint --strict rc0, sync-check rc0 (fixpoint), config-check --fix regenerated CLAUDE.md/AGENTS.md packages list. 3696 pytest pass, ruff+mypy clean. Handoff → .5 (test).

- 2026-06-11: S3 EXPANDED (owner decision): introduce `component` node kind + a COVERAGE-lint (every src module = node OR explicit exempt — no shadow code) + classify ALL ~80 modules. Split into S3a (.7/.8/.9 taxonomy+lint) + S3b (.14/.15/.16 classify-all). .13 tech-writer ← .16. RFC/PLAN updated. S2(#8)+S4(#9) merged.

- 2026-06-11: **S3a / BEAD-07 dev impl complete (NOT committed).** TDD (RED→GREEN), 18 new tests (component kind ×3 + ModuleCoverage dataclass/parse/eval/serialize/severity ×15). (1) `component` added to `VALID_NODE_KINDS` (round-trips through loader→nodes table; nodes has NO kind CHECK since BDL-038 U1, so no DB migration for the kind). `# beadloom:component=` parses automatically (parse_annotations is generic key=value). (2) New `ModuleCoverageRule` (rule_type `module_coverage`, name `module-coverage`) SUPERSEDES `unregistered-feature-candidate` in rules.yml: a module under `source_root` with ≥`min_symbols` symbols is COVERED iff feature|component annotation OR path == a node's `source` (file-source, not dir) OR matches `exempt` glob; else WARN finding. Old UFC rule code/tests kept intact (no longer wired in rules.yml). (3) Exempt seeded minimal: `**/__init__.py`, onboarding/config_reader.py, onboarding/presets.py (visible in rules.yml; criterion documented). (4) `_serialize_rule` + rules-table rule_type CHECK extended (`module_coverage`); reindex round-trips. (5) `docs/guides/architecture-model.md`: `component` kind section + coverage-lint section + exempt criterion. On real repo: 49 modules flagged WARN; `lint --strict` rc0 (warn doesn't fail — S3b promotes to error). **Full `beadloom ci` rc0** (config-check + sync-update --all fixpoint after rule_engine.py/db.py/reindex.py edits). 3795 pytest pass, ruff+mypy clean. Handoff → .8 (test).

- 2026-06-11: ALL beads + epic CLOSED (reconciled — earlier bd closes hadn't persisted across branch/merge; closed in dep order). tech-writer .13 filled 21 SPEC/DOC + architecture-model fixes + READMEs + CHANGELOG + ROADMAP (BDL-051 SHIPPED, speed→BDL-052). beadloom ci rc 0.
