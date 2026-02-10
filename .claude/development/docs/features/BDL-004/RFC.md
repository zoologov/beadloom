# RFC-0004: Phase 3 — Team Adoption

> **Status:** Accepted
> **Date:** 2026-02-10
> **Phase:** 3 (Strategy v0.5)
> **Depends on:** BDL-003 (v0.4.0 — lower the barrier complete)

---

## 1. Summary

Phase 3 goal: **Make Beadloom useful for the whole team, not just the person who set it up.**

Currently Beadloom works for individual developers. Phase 3 adds team workflows: CI checks on PRs, architecture health visibility, external tracker linking, and zero-friction MCP setup for any editor.

Deliverables:

| # | Item | Effort | Priority |
|---|------|--------|----------|
| 3.1 | CI integration (GitHub Action + GitLab CI) | M | P0 |
| 3.2 | Architecture health dashboard + trend data | S | P1 |
| 3.3 | Issue tracker linking (`beadloom link`) | S | P2 |
| 3.4 | MCP templates (Cursor, Claude Code, Windsurf) | S | P1 |

## 2. Motivation

### 2.1 Problem: CI gap

`beadloom sync-check` works locally with `--porcelain` output and exit code 2 on stale docs. But there's no ready-to-use CI integration. Users must write their own workflow YAML, parse output, and format PR/MR comments. Teams use different platforms (GitHub, GitLab), so CI integration must be platform-agnostic at the core.

### 2.2 Problem: No health visibility

`beadloom status` shows raw counts (nodes, edges, docs, stale). But a tech lead needs to answer: "Is our architecture documentation getting better or worse?" — there's no trend data, no health score, no per-domain breakdown.

### 2.3 Problem: No tracker integration

Teams track work in Jira/GitHub Issues/Linear. Graph nodes have no way to link to external trackers. This means Beadloom's knowledge graph lives in isolation from the team's issue flow.

The DB already supports arbitrary metadata via `nodes.extra` JSON field, and `graph_loader.py` passes unknown YAML fields to `extra` automatically. But there's no CLI command to manage links and no display in `ctx` output.

### 2.4 Problem: MCP setup varies by editor

`setup-mcp` creates `.mcp.json` at project root — works for Claude Code. But Cursor uses `.cursor/mcp.json`, Windsurf uses `~/.codeium/windsurf/mcp_config.json`. Users must manually figure out the right path and format for their editor.

## 3. Design

### 3.1 CI Integration — GitHub Action + GitLab CI

**Architecture: platform-agnostic core + platform-specific templates.**

The intelligence lives in the CLI (`--json`, `--report`). CI templates are thin wrappers that run the CLI and post results via platform API.

#### 3.1.1 New CLI Flags for `sync-check`

Currently `sync-check` has `--porcelain` (TAB-separated). We add two new output modes:

**`--json`** — structured data for programmatic consumption:

```json
{
  "summary": {
    "total": 10,
    "ok": 8,
    "stale": 2
  },
  "pairs": [
    {
      "status": "stale",
      "ref_id": "AUTH-001",
      "doc_path": "docs/auth/login-spec.md",
      "code_path": "src/auth/login.py"
    }
  ]
}
```

**`--report`** — ready-to-post Markdown report (the key enabler for multi-platform CI):

```markdown
## Beadloom Doc Sync Report

| Status | Count |
|--------|-------|
| OK | 8 |
| Stale | 2 |

### Stale Documents

| Node | Doc | Changed Code |
|------|-----|-------------|
| AUTH-001 | `docs/auth/login-spec.md` | `src/auth/login.py` |
| BILLING-003 | `docs/billing/invoice.md` | `src/billing/invoice.py` |

> Run `beadloom sync-update AUTH-001` to review and update.
```

Both GitHub Action and GitLab CI template just capture `--report` output and post it. Zero parsing needed in CI scripts.

#### 3.1.2 GitHub — Composite Action

`ci-templates/action.yml`. Users add one step:

```yaml
- uses: owner/beadloom/ci-templates@v0.5
  with:
    comment: true          # Post PR comment with stale summary
    fail-on-stale: false   # Exit 1 if stale docs found (default: false)
```

**action.yml** (composite action):

```yaml
name: "Beadloom Doc Sync Check"
description: "Check documentation freshness and post PR/MR summary"
inputs:
  comment:
    description: "Post PR comment with sync report"
    default: "true"
  fail-on-stale:
    description: "Fail the check if stale docs are found"
    default: "false"
  python-version:
    description: "Python version to use"
    default: "3.12"
runs:
  using: "composite"
  steps:
    - uses: astral-sh/setup-uv@v5
    - run: uv tool install beadloom
      shell: bash
    - run: beadloom reindex
      shell: bash
    - id: sync-check
      run: |
        beadloom sync-check --report > /tmp/beadloom-report.md 2>&1 || true
        beadloom sync-check --porcelain > /dev/null 2>&1 || true
        echo "exit_code=$?" >> "$GITHUB_OUTPUT"
      shell: bash
    - if: inputs.comment == 'true' && github.event_name == 'pull_request'
      uses: actions/github-script@v7
      with:
        script: |
          const fs = require('fs');
          const body = fs.readFileSync('/tmp/beadloom-report.md', 'utf8');
          if (body.trim()) {
            await github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
              body: body
            });
          }
    - if: inputs.fail-on-stale == 'true' && steps.sync-check.outputs.exit_code == '2'
      run: exit 1
      shell: bash
```

#### 3.1.3 GitLab — CI Template

`ci-templates/beadloom-sync.gitlab-ci.yml`:

```yaml
.beadloom-sync-check:
  image: python:3.12-slim
  before_script:
    - pip install uv
    - uv tool install beadloom
    - beadloom reindex
  script:
    - beadloom sync-check --report > beadloom-report.md || true
    - |
      if [ "$BEADLOOM_COMMENT" = "true" ] && [ -n "$CI_MERGE_REQUEST_IID" ]; then
        curl --request POST \
          --header "PRIVATE-TOKEN: $BEADLOOM_GITLAB_TOKEN" \
          --header "Content-Type: application/json" \
          --data "$(jq -n --arg body "$(cat beadloom-report.md)" '{body: $body}')" \
          "$CI_API_V4_URL/projects/$CI_PROJECT_ID/merge_requests/$CI_MERGE_REQUEST_IID/notes"
      fi
    - beadloom sync-check --porcelain > /dev/null 2>&1
  variables:
    BEADLOOM_COMMENT: "true"
  artifacts:
    paths:
      - beadloom-report.md
    when: always
  rules:
    - if: $CI_MERGE_REQUEST_IID
```

**Usage in `.gitlab-ci.yml`:**

```yaml
include:
  - local: ci-templates/beadloom-sync.gitlab-ci.yml
  # or remote:
  # - remote: https://raw.githubusercontent.com/owner/beadloom/main/ci-templates/beadloom-sync.gitlab-ci.yml

doc-sync:
  extends: .beadloom-sync-check
  variables:
    BEADLOOM_COMMENT: "true"
  allow_failure: true  # or false for fail-on-stale behavior
```

#### 3.1.4 Documentation

New `docs/ci-setup.md` with:
- GitHub Actions setup (one-liner `uses:`)
- GitLab CI setup (include template)
- Configuration options table
- Example PR/MR comment screenshots
- Advanced: custom `--json` parsing for custom integrations

### 3.2 Architecture Health Dashboard + Trend Data

**Enhance `beadloom status` with Rich formatting and trend data.**

No new command — the existing `status` is the right place. We add structured output using Rich panels and tables instead of plain text.

#### 3.2.1 Health Snapshot Schema

New DB table for trend tracking:

```sql
CREATE TABLE IF NOT EXISTS health_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    taken_at        TEXT NOT NULL,
    nodes_count     INTEGER NOT NULL,
    edges_count     INTEGER NOT NULL,
    docs_count      INTEGER NOT NULL,
    coverage_pct    REAL NOT NULL,
    stale_count     INTEGER NOT NULL,
    isolated_count  INTEGER NOT NULL,
    extra           TEXT DEFAULT '{}'
);
```

**Population:** `reindex` pipeline saves a snapshot at the end of each run. One row per reindex.

**Not a breaking schema change** — `CREATE TABLE IF NOT EXISTS` is additive. No SCHEMA_VERSION bump needed.

#### 3.2.2 Enhanced Status Output

```
╭─ Beadloom v0.5.0 ─────────────────────────────────╮
│ Last reindex: 2026-02-10T19:35:03Z                 │
╰────────────────────────────────────────────────────╯

  Nodes:  12     Edges:  8     Docs:  6     Symbols:  90

  ┌─ By Kind ──────┐  ┌─ Doc Coverage ─────────────────┐
  │ domain     5    │  │ Overall:  8/12 (67%)  ▲ +8%    │
  │ service    3    │  │ domain:   4/5  (80%)           │
  │ feature    2    │  │ service:  2/3  (67%)           │
  │ entity     2    │  │ feature:  2/2  (100%)          │
  └────────────────┘  │ entity:   0/2  (0%)            │
                      └────────────────────────────────┘

  ┌─ Health ───────────────────────────────────────────┐
  │ Stale docs:     2  ▼ +1 since last reindex         │
  │ Isolated nodes: 1  ▲ -2 since last reindex         │
  │ Empty summaries: 0                                  │
  └────────────────────────────────────────────────────┘
```

**Trend indicators:** `▲ +8%` (improved), `▼ +1` (worsened). Computed by comparing current snapshot with previous one in `health_snapshots`.

#### 3.2.3 Implementation

New module: `src/beadloom/health.py`

```python
@dataclass(frozen=True)
class HealthSnapshot:
    """Point-in-time health metrics."""
    taken_at: str
    nodes_count: int
    edges_count: int
    docs_count: int
    coverage_pct: float
    stale_count: int
    isolated_count: int

def take_snapshot(conn: sqlite3.Connection) -> HealthSnapshot:
    """Compute and save current health metrics."""
    ...

def get_latest_snapshots(conn: sqlite3.Connection, n: int = 2) -> list[HealthSnapshot]:
    """Get the N most recent snapshots for trend comparison."""
    ...

def compute_trend(current: HealthSnapshot, previous: HealthSnapshot | None) -> dict[str, str]:
    """Compute trend indicators (arrows + deltas)."""
    ...
```

`reindex` calls `take_snapshot()` at the end of the pipeline.
`status` calls `get_latest_snapshots(2)` + `compute_trend()` to show deltas.

### 3.3 Issue Tracker Linking

**New command: `beadloom link`**

```bash
# Add a link
beadloom link AUTH-001 https://github.com/org/repo/issues/42

# Add with label
beadloom link AUTH-001 https://jira.company.com/browse/AUTH-42 --label jira

# List links for a node
beadloom link AUTH-001

# Remove a link
beadloom link AUTH-001 --remove https://github.com/org/repo/issues/42
```

#### 3.3.1 Storage

Links are stored in the `extra` JSON field on nodes:

```json
{
  "links": [
    {"url": "https://github.com/org/repo/issues/42", "label": "github"},
    {"url": "https://jira.company.com/browse/AUTH-42", "label": "jira"}
  ]
}
```

The `link` command:
1. Reads the YAML graph file where the node is defined (from `nodes.source` column)
2. Adds/removes `links` field on the YAML node
3. Runs `reindex` to update DB

This keeps YAML as the source of truth — links are versioned in Git alongside the graph.

#### 3.3.2 Auto-detection of label

If `--label` not specified, detect from URL pattern:

| Pattern | Label |
|---------|-------|
| `github.com/*/issues/*` | github |
| `github.com/*/pull/*` | github-pr |
| `*.atlassian.net/*` or `jira.*` | jira |
| `linear.app/*` | linear |
| Everything else | link |

#### 3.3.3 Display in context

`build_context()` includes links in the focus node section:

```json
{
  "focus": {
    "ref_id": "AUTH-001",
    "kind": "feature",
    "summary": "User login flow",
    "links": [
      {"url": "https://github.com/org/repo/issues/42", "label": "github"}
    ]
  }
}
```

`ctx` CLI also shows links:

```
Focus: AUTH-001 (feature)
  User login flow
  Links: github#42, jira/AUTH-42
```

### 3.4 MCP Templates

**Extend `setup-mcp` with `--tool` flag:**

```bash
beadloom setup-mcp                    # Default: .mcp.json (Claude Code)
beadloom setup-mcp --tool claude-code # Same as default
beadloom setup-mcp --tool cursor      # .cursor/mcp.json
beadloom setup-mcp --tool windsurf    # ~/.codeium/windsurf/mcp_config.json
```

#### 3.4.1 Tool-specific paths

| Tool | Config Path | Scope |
|------|------------|-------|
| `claude-code` | `{project}/.mcp.json` | Project |
| `cursor` | `{project}/.cursor/mcp.json` | Project |
| `windsurf` | `~/.codeium/windsurf/mcp_config.json` | Global |

#### 3.4.2 Config format

All tools use the same MCP JSON structure (MCP is a standard), just at different paths:

```json
{
  "mcpServers": {
    "beadloom": {
      "command": "/path/to/beadloom",
      "args": ["mcp-serve"]
    }
  }
}
```

For global configs (Windsurf), we add a `--project` arg:

```json
{
  "mcpServers": {
    "beadloom": {
      "command": "/path/to/beadloom",
      "args": ["mcp-serve", "--project", "/absolute/path/to/project"]
    }
  }
}
```

#### 3.4.3 Documentation

Add a `docs/mcp-setup.md` guide with step-by-step instructions for each editor, including screenshots of where MCP settings live and verification steps.

## 4. Implementation Plan

### 4.1 File Changes

| File | Change |
|------|--------|
| `src/beadloom/health.py` | NEW — HealthSnapshot, take_snapshot, get_latest_snapshots, compute_trend |
| `src/beadloom/db.py` | Add `health_snapshots` table to schema |
| `src/beadloom/reindex.py` | Call take_snapshot() at end of pipeline |
| `src/beadloom/cli.py` | Add `--json` to sync-check; enhance `status` with Rich + trends; add `link` command; extend `setup-mcp` with `--tool` |
| `src/beadloom/context_builder.py` | Include links from `extra` in focus node |
| `src/beadloom/mcp_server.py` | Include links in get_context response |
| `ci-templates/action.yml` | NEW — Composite GitHub Action |
| `ci-templates/beadloom-sync.gitlab-ci.yml` | NEW — GitLab CI template |
| `docs/ci-setup.md` | NEW — CI setup guide (GitHub + GitLab) |
| `docs/mcp-setup.md` | NEW — MCP setup guide per editor |
| `docs/cli-reference.md` | Update with new commands and flags |
| `tests/test_health.py` | NEW — snapshot, trend, schema tests |
| `tests/test_cli_status.py` | Extend with Rich output, trend display tests |
| `tests/test_cli_sync_check.py` | Extend with --json output tests |
| `tests/test_cli_link.py` | NEW — link add/remove/list/auto-label tests |
| `tests/test_cli_mcp.py` | Extend with --tool flag tests |
| `tests/test_context_builder.py` | Extend with links display test |

### 4.2 Execution Order

| # | Bead | Depends on | Status |
|---|------|------------|--------|
| 3.2 | Health dashboard + trends | — | TODO |
| 3.4 | MCP templates | — | TODO |
| 3.3 | Issue tracker linking | — | TODO |
| 3.1 | CI integration (GitHub + GitLab) | — | TODO |

3.2, 3.4, 3.3, 3.1 are all independent — can be parallelized.
3.1 adds `--json` and `--report` flags to sync-check as part of its own scope.

### 4.3 What Stays Unchanged

- Graph loader (`graph_loader.py`) — already passes unknown fields to `extra`
- Presets (`presets.py`) — unchanged
- Onboarding (`onboarding.py`) — unchanged
- Doc sync engine (`sync_engine.py`) — unchanged
- BFS traversal algorithm — unchanged
- MCP tools list — no new tools (status already exists)

### 4.4 DB Schema Change

**Additive only** — one new table `health_snapshots`. No changes to existing tables.
`CREATE TABLE IF NOT EXISTS` makes it safe — old databases get the table on first use.
No SCHEMA_VERSION bump needed.

## 5. Success Criteria

- [ ] `action.yml` works as composite GitHub Action with PR comments
- [ ] GitLab CI template posts MR comments with sync report
- [ ] `beadloom sync-check --json` returns structured JSON output
- [ ] `beadloom sync-check --report` returns ready-to-post Markdown
- [ ] `beadloom status` shows Rich-formatted dashboard with per-kind coverage
- [ ] `beadloom status` shows trend data (deltas from previous reindex)
- [ ] `health_snapshots` table populated on every `reindex`
- [ ] `beadloom link AUTH-001 <url>` adds link to YAML and DB
- [ ] `beadloom link AUTH-001` lists links
- [ ] `beadloom link AUTH-001 --remove <url>` removes link
- [ ] `beadloom ctx AUTH-001` shows links in output
- [ ] `beadloom setup-mcp --tool cursor` creates `.cursor/mcp.json`
- [ ] `beadloom setup-mcp --tool windsurf` creates global config
- [ ] All tests pass (`uv run pytest`)
- [ ] `mypy --strict` passes
- [ ] `ruff check` passes

## 6. Non-Goals

- No CircleCI / Jenkins / other CI templates beyond GitHub + GitLab
- No TUI or graph visualization (Phase 4)
- No architecture rules / lint (Phase 5)
- No new MCP tools (existing 5 tools are sufficient)
- No link URL reachability validation (nice-to-have, not now)
- No historical trend charts (simple deltas are enough)
