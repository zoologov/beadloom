<!-- beadloom:badge-start -->
> 📘 **reference** — overview/guide, not tied to a code symbol
> 
> _Validation by Beadloom `doc_sync` — same source as `sync-check`._
<!-- beadloom:badge-end -->

# CI Setup Guide

Beadloom integrates with CI/CD to check documentation freshness and enforce
architecture boundaries on every PR/MR.

## GitHub Actions

Add to your workflow (`.github/workflows/doc-sync.yml`):

```yaml
name: Doc Sync Check
on: [pull_request]
jobs:
  doc-sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: owner/beadloom/ci-templates@v0.5
        with:
          comment: true          # Post PR comment with sync report
          fail-on-stale: false   # Set to true to block merging on stale docs
```

### Configuration

| Input | Default | Description |
|-------|---------|-------------|
| `comment` | `true` | Post PR comment with doc sync summary |
| `fail-on-stale` | `false` | Fail the check if stale docs are found |
| `python-version` | `3.12` | Python version to use |

## GitLab CI

Include the template in your `.gitlab-ci.yml`:

```yaml
include:
  - local: ci-templates/beadloom-sync.gitlab-ci.yml

doc-sync:
  extends: .beadloom-sync-check
  variables:
    BEADLOOM_COMMENT: "true"
  allow_failure: true
```

### Prerequisites

- Set `BEADLOOM_GITLAB_TOKEN` as a CI/CD variable with API access
- The template automatically runs on merge requests

### Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `BEADLOOM_COMMENT` | `true` | Post MR comment with sync report |
| `BEADLOOM_GITLAB_TOKEN` | — | GitLab API token for MR comments |

Set `allow_failure: false` to block merging when docs are stale.

## Architecture Lint (v1.0+)

### GitHub Actions

Add to your workflow (`.github/workflows/beadloom-lint.yml`):

```yaml
name: Architecture Lint
on: [pull_request]
jobs:
  arch-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install beadloom
      - run: beadloom reindex
      - run: beadloom lint --strict --format json
```

### GitLab CI

```yaml
arch-lint:
  stage: test
  image: python:3.12-slim
  script:
    - pip install beadloom
    - beadloom reindex
    - beadloom lint --strict --format json
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
```

### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | No violations (or violations without `--strict`) |
| `1` | Violations found (with `--strict`) |
| `2` | Configuration error (invalid rules.yml, missing DB) |

### Output Formats

```bash
beadloom lint                     # Human-readable (rich) — default in TTY
beadloom lint --format json       # Structured JSON for scripts
beadloom lint --format porcelain  # Machine-readable, one line per violation
beadloom lint --format github     # GitHub Actions ::error annotations (inline on the PR)
beadloom lint --no-reindex        # Skip reindex (faster, uses existing DB)
```

Every violation carries an agent-actionable `remediation` ("how to fix"), surfaced
in `json` (a `remediation` key per violation) and rendered into the `github`
annotation message — so an agent or CI reviewer gets the fix, not just the
detection.

## Unified Gate (`beadloom ci`)

`beadloom ci` composes, in order, **reindex -> lint --strict -> sync-check ->
config-check -> doctor -> (optional) federate landscape gate** into a single
verdict with one exit code (0 = every step passed, 1 = any step failed). It never
short-circuits — every step runs and contributes findings — and it names every
step that ran with its honest result (PASS/FAIL/SKIP); a green is never a silently
skipped step. All steps share one agent-actionable finding shape
(`{kind, rule, severity, locations, why, remediation}`), so `--format` applies
uniformly: `rich` (default in a TTY), `json` (structured), or `github` (default
when piped — emits `::error` annotations so violations show inline on the PR).

| Step | What it enforces | Skipped when |
|------|------------------|--------------|
| `reindex` | rebuild the index from current code/graph | `--no-reindex` |
| `lint --strict` | architecture-boundary violations | — |
| `sync-check` | doc-code freshness (stale docs) | — |
| `config-check` | AgentConfigAsCode — generated agent-config matches the graph | — |
| `doctor` | graph integrity | — |
| `federate --fail-on` | cross-service landscape gate | no `--hub` exports given |

Beadloom dogfoods this gate on its own CI: the per-repo gate (`reindex` →
`lint --strict` → `sync-check` → `config-check` → `doctor`) shipped and runs on
every Beadloom PR. The cross-service landscape step is opt-in via `--hub`.

### AgentConfigAsCode (`config-check`)

`config-check` treats the generated agent-config as code: it regenerates
`AGENTS.md`, the auto-managed regions of `CLAUDE.md`, and the IDE rules adapters
**in memory** (reusing the exact `setup-rules --refresh` generator — no parallel
reimplementation) and diffs them against disk. It exits `1` on drift, `0` when
clean. `config-check --fix` regenerates the artifacts and re-checks.

It checks **only** the auto-managed regions (between `beadloom:auto-start` /
`beadloom:auto-end` markers) — never user-authored prose — so it cannot
false-positive on hand-written content. This is principle 7 in practice: local
rules files are verified-fresh, never hand-maintained.

```bash
beadloom config-check          # exit 1 on agent-config drift, 0 when clean
beadloom config-check --fix    # regenerate drifted artifacts, then re-check
```

### GitHub Actions (composite Action)

A thin composite Action wraps `beadloom ci` (all logic lives in the CLI).
Reference it from a satellite repo at a pinned ref:

```yaml
name: Beadloom Gate
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
jobs:
  beadloom-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: zoologov/beadloom/.github/actions/beadloom-gate@v1
        with:
          format: github        # GitHub annotations on the PR (default)
          # fail-on: default    # only with hub-exports; safe-default fail-set
          # hub-exports: ""     # space-separated satellite export paths
          # no-reindex: false   # skip reindex if the caller reindexes
          # project: .          # project root
```

| Input | Default | Description |
|-------|---------|-------------|
| `fail-on` | `""` | Federate fail-set (comma-separated, or `default`). Applied only with `hub-exports`. |
| `hub-exports` | `""` | Space-separated satellite export artifact path(s); enables the federate landscape gate. |
| `format` | `github` | `rich` \| `json` \| `github`. |
| `no-reindex` | `false` | Skip the reindex step. |
| `project` | `.` | Project root passed to `beadloom ci --project`. |

The Action injects no secrets. It only installs uv, syncs deps, and runs `beadloom ci`.

### GitLab CI

```yaml
beadloom-gate:
  stage: test
  image: python:3.12-slim
  script:
    - pip install beadloom
    - beadloom ci --format json
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
```

### Landscape gate (`federate --fail-on`)

`federate` is reporting-only by default (exit `0` regardless of drift). Pass
`--fail-on <csv>` to turn it into a CI gate: it **always writes
`.beadloom/federated.json` + `.beadloom/federated.txt` and prints the report
first**, THEN exits `1` if any edge or contract verdict (matched
case-insensitively) is in the fail-set — so CI always has the artifact to upload
even when the gate blocks. The failing verdicts (each with its `src → dst` /
`contract_key` identity, plus the missing GraphQL names for a `BREAKING`) are
printed to stderr.

- A bare `--fail-on`, or the token `default`, uses the **safe-default fail-set**
  `breaking,drift,orphaned_consumer,undeclared_producer` (plus the edge-level
  `undeclared`, the AMQP equivalent of `undeclared_producer`).
- The fail-set can **never** include a no-false-gate verdict —
  `external` / `expected` / `dead` / `unmapped` / `confirmed` / `ok` /
  `cleanup_candidate`. These are intentional, honest-unknown, or healthy states;
  passing one is rejected with a clear error (exit `2`). This is principle 3 — a
  noisy gate gets disabled, so the gate refuses to arm a false one.

`beadloom ci --hub <export> ... --fail-on default` runs this same gate as the
final CI step.

### Pull-based hub pattern (multi-repo)

The per-repo gate above is for a single repository. To gate the *cross-service*
landscape, a dedicated hub job pulls the latest `beadloom export` artifact from
each satellite repo and runs the federate gate. Each satellite publishes its
export tagged with the producing commit SHA (the export records `commit_sha` /
`exported_at` provenance), so the hub can report per-satellite staleness.

No registry/SaaS is Beadloom-built — the per-repo gate is what ships and is
dogfooded. The hub side is a **documented pattern, run by the satellites' own
ops**: publish a commit-SHA-tagged export from each repo, then a hub CI job
pulls **≥ 2** of them (however your CI already moves artifacts — release assets,
package registry, object storage) and runs `federate --fail-on`. Point `--hub`
at each pulled export.

```yaml
# Hub repo: aggregate satellite exports and gate the federated landscape.
federate-gate:
  stage: test
  image: python:3.12-slim
  script:
    - pip install beadloom
    # Pull each satellite's latest export (adapt to your artifact store).
    - ./scripts/pull-satellite-exports.sh exports/    # -> exports/*.json
    - beadloom ci --no-reindex
        --hub exports/service-a.json
        --hub exports/service-b.json
        --fail-on default
        --format json
  rules:
    - if: $CI_PIPELINE_SOURCE == "schedule"
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
```

The GitHub composite Action expresses the same pattern via `hub-exports`
(space-separated paths) and `fail-on`.

## Custom Integration

For other CI platforms, use the CLI directly:

```bash
# Structured JSON output for programmatic consumption
beadloom sync-check --json

# Ready-to-post Markdown report
beadloom sync-check --report

# Machine-readable TAB-separated output
beadloom sync-check --porcelain
```

Exit codes:
- `0` — all documentation is up to date
- `1` — error (database not found, etc.)
- `2` — stale documentation found
