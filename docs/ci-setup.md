# CI Setup Guide

Beadloom integrates with CI/CD to check documentation freshness on every PR/MR.

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
      - uses: owner/beadloom@v0.5
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
