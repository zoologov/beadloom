# AI Agents

Governed AI-agent harnesses that ship **inside** the installed `beadloom`
package. This domain hosts deterministic, seam-isolated harnesses that
orchestrate an external AI agent (Goose + a model) over Beadloom's own read
APIs and the `beadloom` / `bd` shell commands.

Introduced in BDL-051 / S2, when the AI tech-writer harness moved here from the
former `tools/ai_techwriter` repo-tooling package so it is graph-tracked,
lint-governed, and shipped as part of the wheel — adopters run it directly via
`python -m beadloom.ai_agents.ai_techwriter` (no vendoring).

## Boundary

`ai_agents` is a **leaf consumer**: it MAY consume `application` /
`context_oracle` / `graph` / `doc_sync` read APIs + the stdlib + the `beadloom`
/ `bd` shells, but it MUST NOT be imported BY the core domains or services. The
`core-no-import-ai-agents` / `application-no-import-ai-agents` `forbid_import`
rules in `.beadloom/_graph/rules.yml` enforce this (`lint --strict`).

## Features

- **ai-techwriter** — the deterministic, PR-triggered documentation-refresh
  harness (see `features/ai-techwriter/SPEC.md`).

## Specification

### Sub-packages

- **ai_techwriter/** — the AI tech-writer harness package. Annotated
  `# beadloom:feature=ai-techwriter`; the substantive modules are documented in
  the feature SPEC. The Goose recipe (`recipe.yaml`) and the runner provisioner
  (`provision-runner.sh`) ride alongside the package as **package data**, read
  via `importlib.resources` (the recipe by `provider.default_recipe_path()`).
