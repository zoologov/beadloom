# RFC: BDL-051 (EPIC) — Beadloom governs itself

> **Status:** Approved
> **Created:** 2026-06-11
> **PRD:** ./PRD.md

---

## Summary

Three threads, delivered as **four trunk-based slices** (each its own PR via `ci.yml`):

1. **Slice 1 (A-core): feature definition + sprawl lint** — document Domain vs Feature; add a `rule_engine` check that flags unregistered-feature candidates / domain sprawl.
2. **Slice 2 (B): `ai_agents` domain** — move `tools/ai_techwriter/` → `src/beadloom/ai_agents/ai_techwriter/`, model it per the new definition, **retire the vendoring machinery** (the harness now ships inside the installed package). Immediately dogfoods Slice 1's discipline on a real new domain.
3. **Slice 3 (A-remodel): re-model `onboarding` + audit all domains** — register the genuine hidden features as nodes+SPECs; make the lint clean (or warn-only on accepted cases).
4. **Slice 4 (C): adopt the packaged flow** — `checkpoint`/`complete_bead` maintain the `ACTIVE.md` status table; the coordinator drives Beadloom's own loop through the process-tools.

## Decisions on the open questions

1. **Sprawl-lint heuristic** → a new **cardinality-family check** in `rules.yml` + `rule_engine`, computed from `code_symbols` annotations (no fragile CLI-mapping in v1):
   - `unregistered-feature-candidate` (severity `warn`): for each `domain`, list **source files annotated `# beadloom:domain=X` with NO `# beadloom:feature=` and ≥ N public symbols** (default N=5, configurable). Message names each candidate file + its symbol count: *"`onboarding/branch_protection.py` (12 symbols) is domain-only — candidate unregistered feature."* This is the concrete, computable form of "a substantial module attributed to a domain but to no feature."
   - Keep `domain-size-limit` (it's the symptom); the new check is the diagnosis. CLI-command→module mapping is a possible later refinement, noted, not built now.
2. **`ai_agents` placement → RETIRE the vendoring.** Today `setup-ai-techwriter` vendors `tools/ai_techwriter/*.py.txt` into a target repo because `python -m tools.ai_techwriter` wouldn't resolve from a pip-installed beadloom. Once the harness lives at `src/beadloom/ai_agents/ai_techwriter/`, it **ships inside the installed `beadloom` package** → adopters run `python -m beadloom.ai_agents.ai_techwriter` (or a console entry) directly. So: delete `HARNESS_MODULES` + the `*.py.txt` assets + `sync_vendored_harness` + the byte-identical drift-guard test; `recipe.yaml` + `provision-runner.sh` ship as **package data** (importlib.resources) and the scaffold just emits the CI workflow that calls the installed module. Net: a real simplification (removes the BDL-047/048 vendoring complexity) + the harness is finally governed.
3. **onboarding re-model (concrete)** → new feature nodes: **config-check** (`config_sync.py`), **branch-protection** (`branch_protection.py`), **agentic-flow-setup** (`agentic_flow_setup.py`), **ai-techwriter-setup** (`ai_techwriter_setup.py`). Stay domain-level (listed in README, no SPEC): `config_reader.py`, `presets.py` (pure helpers). `scanner.py` keeps `agent-prime`. Audit the other 5 domains the same way; fix or annotate an explicit accept.
4. **Process-tools adoption → BOTH.** Wire ACTIVE-table maintenance into the **MCP tools** (`checkpoint`/`complete_bead` in `mcp_server.py`) so it's correct by construction for any consumer; AND have the **coordinator command** call the process-tools in Beadloom's own loop (the dogfood). 
5. **Slice order** → 1 (define+lint) → 2 (ai_agents, proves the lint on a fresh domain) → 3 (onboarding re-model + audit, guided by the lint) → 4 (flow adoption). Each a PR; each green on `ci.yml`.

## Thread A — graph modeling discipline

- **Definition (G1):** documented in `BDL-AI-AGENTS-ARCHITECTURE.md` is the wrong home — put it in a short **`docs/guides/architecture-model.md`** (or the contributing/`templates` guidance): Domain = DDD package; Feature = cohesive capability with a `SPEC.md` (a CLI command or a distinct subsystem/contract); plumbing stays domain-level but is listed in the domain README. Cross-link from `task_init`/templates so new work models correctly.
- **Lint (G2):** `graph/rule_engine.py` gains the `unregistered-feature-candidate` check (parse `code_symbols.annotations` → group source files by `domain` with/without `feature`, count symbols per file). Declared in `.beadloom/_graph/rules.yml`. `beadloom lint` reports candidates; `--strict` exit semantics unchanged (warn doesn't fail unless promoted). Unit-tested against a synthetic graph + against the real onboarding sprawl (should flag the 4 candidates).
- **Re-model (G3):** add the feature nodes to `services.yml` + `# beadloom:feature=` annotations on the modules + generate their `SPEC.md` skeletons (then tech-writer fills). `beadloom reindex` + `sync-check`. Audit the 6 domains; the lint drives the list.

## Thread B — `ai_agents` domain (the move)

- **Move:** `tools/ai_techwriter/{models,commands,scope,packet,seams,runs_store,runner,provider,cli,__main__,recipe.yaml,...}` → `src/beadloom/ai_agents/ai_techwriter/`. Annotate `# beadloom:domain=ai_agents` (+ per-file `# beadloom:feature=ai-techwriter`). Declare `ai_agents` (domain) + `ai-techwriter` (feature) in `services.yml` with a `SPEC.md`.
- **Invocation:** `ci.yml` + `.gitlab-ci.yml` + the scaffolded templates call `python -m beadloom.ai_agents.ai_techwriter` (or add a `[project.scripts]` console entry `beadloom-ai-techwriter`). Update all internal imports.
- **Retire vendoring (decision 2):** remove `HARNESS_MODULES`/`*.py.txt`/`sync_vendored_harness`/drift-guard from `onboarding/ai_techwriter_setup.py`; `recipe.yaml`/`provision-runner.sh` become package data; `setup-ai-techwriter` emits only the workflow + guide + recipe/provisioner (no Python vendoring).
- **Boundaries (G5):** an `ai_agents` boundary rule in `rules.yml` (what it may import — it consumes `application`/`context_oracle`/`graph` read APIs + shells `beadloom`/`bd`; it must not be imported BY the core). `lint --strict` enforces it.
- **No regression:** the BDL-049/050 model (PR-triggered, `--target pr-branch`, verdict, loop-guard, AI_TW_PAT) is byte-unchanged in behavior; only the module path moves. The slice's own PR (via `ci.yml`) re-runs the live ai-techwriter on the new path = the dogfood.

## Thread C — full migration to the packaged flow

- **ACTIVE-table maintenance (G7):** a deterministic helper updates the `| <bead-id> | role | status |` row in the epic's `ACTIVE.md` (parse the markdown table, flip the matching bead's status cell). `complete_bead` → set `✓ done` on PASS; `checkpoint(bead, status?)` → set `in progress` / append the progress-log line. In `services/mcp_server.py` (the tools) so it's correct for any MCP client.
- **Adoption (G6):** the coordinator (main loop) calls `task_init`/`bead_context`/`complete_bead`/`checkpoint` for the deterministic steps of Beadloom's own epics going forward. Honest boundary: orchestration (Agent-spawn) stays main-loop.

## Component / file impact

| Component | Change | Thread |
|-----------|--------|--------|
| `docs/guides/architecture-model.md` (NEW) | Domain vs Feature definition | A |
| `graph/rule_engine.py` + `.beadloom/_graph/rules.yml` | `unregistered-feature-candidate` lint | A |
| `.beadloom/_graph/services.yml` | new feature nodes (onboarding ×4, ai_agents domain + ai-techwriter) | A,B |
| `src/beadloom/onboarding/*.py` | `# beadloom:feature=` annotations | A |
| `docs/domains/onboarding/features/*/SPEC.md` (NEW) | new feature SPECs | A |
| `src/beadloom/ai_agents/ai_techwriter/**` (MOVED from `tools/`) | + annotations + SPEC | B |
| `onboarding/ai_techwriter_setup.py` | retire vendoring; recipe/provisioner → package data | B |
| `.github/workflows/ci.yml` + `.gitlab-ci.yml` + templates | invocation path → `beadloom.ai_agents.ai_techwriter` | B |
| `pyproject.toml` | package-data for recipe/provisioner; optional console script | B |
| `services/mcp_server.py` | `checkpoint`/`complete_bead` ACTIVE-table maintenance | C |
| docs/guides + CHANGELOG + ROADMAP (+ renumber speed → BDL-052) | tech-writer | A/B/C |

## Alternatives considered

- **Keep `tools/ai_techwriter` + add `tools` to `scan_paths`** (Thread B, lighter). Rejected: `tools/` as installed product is odd; moving into the package also lets us retire vendoring — net simpler.
- **Auto-promote every domain-only module to a feature.** Rejected: features are a human modeling judgment; the lint is advisory (flags candidates), it doesn't decide.
- **A bespoke sprawl metric (features:modules ratio).** Rejected for v1 in favor of the concrete per-file "domain-only ≥N symbols" check — actionable (names files), not a vague ratio.
- **One mega-PR.** Rejected: trunk-based wants small slices; 4 PRs each independently green.

## Risks & mitigations

- **The `ai_agents` move breaks the running ai-techwriter** (import/path/vendoring). → the slice's PR re-runs the live agent on the new path (dogfood); keep the BDL-049/050 body byte-identical; migrate the recipe/provisioner package-data carefully + test `importlib.resources` access.
- **Retiring vendoring breaks adopters' scaffold.** → `setup-ai-techwriter` now emits a workflow calling the installed module; add a test that a scaffolded repo's workflow references `beadloom.ai_agents.ai_techwriter` + that the recipe ships as package data.
- **Sprawl-lint false positives** (helpers flagged). → `warn` severity + an explicit allow-list / "accepted domain-level" annotation; tune N.
- **ACTIVE-table parser fragility** (markdown table formats). → tolerant parser keyed on the bead-id cell; best-effort (never crash the tool); unit-test the table-update.
- **Lint clean-up churn across 6 domains.** → Slice 3 scopes the audit; accept-and-annotate where re-modeling isn't worth it (documented).

## Rollout

Epic, 4 slices (each a PR on `ci.yml`): **S1** define+lint (dev→test→review) → **S2** ai_agents move + retire vendoring (dev→test→review; PR dogfoods the live agent on the new path) → **S3** onboarding re-model + domain audit (dev→test→review) → **S4** process-tools ACTIVE-fix + adoption (dev→test→review). A single **tech-writer** pass at the end (or per-slice docs). Beadloom green on its own `ci.yml` after each slice; the epic itself is driven through the process-tools (Thread C dogfood) once S4 lands.
