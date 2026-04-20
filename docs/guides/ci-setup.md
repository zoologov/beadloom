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
beadloom lint --no-reindex        # Skip reindex (faster, uses existing DB)
```

## Unified Gate (`beadloom ci`)

`beadloom ci` composes reindex -> lint -> sync-check -> config-check -> (optional)
federate landscape gate into a single verdict with one exit code (0 = every step
passed, 1 = any step failed). It names every step that ran and its honest result
(PASS/FAIL/SKIP). `--format github` emits GitHub annotations so violations show
inline on the PR.

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

### Pull-based hub pattern (multi-repo)

The per-repo gate above is for a single repository. To gate the *cross-service*
landscape, a dedicated hub job pulls the latest `beadloom export` artifact from
each satellite repo and runs the federate gate. No registry/SaaS is required —
fetch the exports however your CI already moves artifacts (release assets,
package registry, object storage), then point `--hub` at each one.

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
