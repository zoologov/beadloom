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
