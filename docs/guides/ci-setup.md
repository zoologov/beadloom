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

`--fail-on-warn` exits 1 on any finding a rule decided, warnings included. It does
**not** exit 1 on a layer rule's population or declaration statement at `warn`:
those report how far the rule reached rather than anything it found wrong, and
they appear on a graph nobody changed. Anything at `error` severity exits 1 under
both flags, so `--fail-on-warn` never reads softer than `--strict` on one run. A
pipeline that wants them to block reads the `layer_population` and
`layer_declaration` records out of `--format json` itself.

### Output Formats

```bash
beadloom lint                     # Human-readable (rich) — default in TTY
beadloom lint --format json       # Structured JSON for scripts
beadloom lint --format porcelain  # Machine-readable: one record per violation,
                                  # led by a `# `-marked line per layer rule
beadloom lint --format github     # GitHub Actions ::error annotations (inline on the PR)
beadloom lint --no-reindex        # Read the index as-is (read-only; see the note below)
```

Every violation carries an agent-actionable `remediation` ("how to fix"), surfaced
in `json` (a `remediation` key per violation) and rendered into the `github`
annotation message — so an agent or CI reviewer gets the fix, not just the
detection.

**`--no-reindex` answers about the index, not about the tree.** It is the
read-only form — it leaves `beadloom.db` byte-identical and refuses a missing
index at exit 2 instead of creating one — but it judges whatever the index
happens to hold. With an index older than the working tree it reports
`0 violations` over a live error-severity crossing that plain `lint --strict`
catches on the same tree (measured). Use it only where the caller has just
reindexed; otherwise let the default reindex first, which is why the default
writes the index.

## Unified Gate (`beadloom ci`)

`beadloom ci` composes, in order, **reindex -> lint --strict -> sync-check ->
docs audit -> docs-quality -> issue-log -> readme-pair -> doc-spaces -> scope-check ->
config-check -> doctor -> (optional) federate landscape gate** into a single verdict with one
exit code (0 = every step passed, 1 = any step failed). The order is `run_ci_gate`'s, listed
once in the [application README](../domains/application/README.md#api). It never
short-circuits — every step runs and contributes findings — and it names every step that ran
with its honest result (PASS/WARN/FAIL/SKIP/ERROR), and a green is never a silently skipped step.
`ERROR` is a step that raised (BDL-083 S1e, BDL-UX #318): it fails the gate, the steps after
it still run, and the verdict reads `FAIL — 1 step(s) crashed: docs-audit — gate blocked`.
All steps share one agent-actionable finding shape
(`{kind, rule, severity, node, locations, why, remediation}`), so `--format` applies
uniformly: `rich` (default in a TTY), `json` (structured), or `github` (default
when piped — emits `::error` annotations so violations show inline on the PR).
`--tee FILE` writes a copy of the rendered report to `FILE` as well.

| Step | What it enforces | Skipped when |
|------|------------------|--------------|
| `reindex` | rebuild the index from current code/graph | `--no-reindex` |
| `lint --strict` | architecture-boundary violations | — |
| `sync-check` | doc-code freshness (stale docs) | — |
| `docs audit` | stale numeric facts stated in documentation | — |
| `docs-quality` | the writing standard over planning documents — **warn only** | no planning document matched (NAMED skip) |
| `issue-log` | the issue log's numbers: duplicates, unwritten claims, unclaimed numbers | no log declared under `issue_log:` (NAMED skip) |
| `readme-pair` | the declared document pairs, compared by shape | no pair declared under `document_pairs:` (NAMED skip) |
| `doc-spaces` | recorded intent that never reached a document of reality — **warn only** | no TO-BE document matched (NAMED skip) |
| `scope-check` | the branch's paths against the axes its work item declares — **warn only** | no branch, work item, index or `## Axes` section (NAMED skip) |
| `config-check` | AgentConfigAsCode — generated agent-config matches the graph | — |
| `doctor` | graph integrity | — |
| `federate --fail-on` | cross-service landscape gate | no `--hub` exports given |

`scope-check` judges `<base>...HEAD`, where the base is the merge-base with the branch this one
was cut from, else the trunk, and its line names it (BDL-083 S1d). In pull-request CI the
branch is read from `GITHUB_HEAD_REF` or `CI_MERGE_REQUEST_SOURCE_BRANCH_NAME` before the
checkout's own name, so the step runs on a detached checkout where it used to skip (BDL-UX
#300).

Beadloom dogfoods this gate on its own CI: every step above runs on every Beadloom PR. The
cross-service landscape step is opt-in via `--hub`.

### The JSON report

`beadloom ci --format json` prints one object. Its top-level keys are `ok`, `steps`,
`crashed`, `not_run`, `ownership` and `room`:

| Key | Shape |
|-----|-------|
| `ok` | `true` when every step passed |
| `steps` | one `{name, status, passed, skipped, summary, error, findings}` per step; `error` is `<class>: <message>` for an `ERROR` step and `null` otherwise |
| `crashed` | the names of the steps that raised, in step order, `[]` when none did |
| `not_run` | `{performed, not_performed, ...}`: the verifications the project's pipeline declares that no step performed |
| `room` | `{current, entered, not_entered, ..., not_derived}`: the room the run was taken in; `not_derived` is `null`, or the reason the census derived no room (BDL-083 S2a) |
| `ownership` | `{reason, rule, base, claimed, none_owned, claims, findings}`: who owns what the run found |

`room`, `not_run` and `ownership` are qualifications of the verdict, not steps, and none of
them moves the exit code. Each is derived after the steps. A room census or a coverage report
that raised is `{"reason": "the <report> raised <class>: <message>"}` in place of `room` or
`not_run`, where `<report>` is `room census` or `coverage report`. An ownership report that
raised keeps its object with that sentence in `reason` (BDL-083 S1 fix 1). A key is absent when
nothing asked for that report, which is a different answer from a report that raised.

In `ownership`, a finding is `owned` by a claimed bead whose commits on `<base>..HEAD` changed a
file the finding is about, and `unattributed` otherwise. A commit is a bead's when its message
carries the git trailer `Bead: <bead-id>` in its final paragraph (BDL-083 D10). Each `claims`
entry is `{bead, commits, unread_bead_lines}`: `commits` counts the commits the trailer binds,
and `unread_bead_lines` holds one `{placement, stated, count, commits}` row per place a
`Bead: <id>` line stands where git reads no trailer, `[]` when there is none. `placement` takes
the vocabulary `outside_final` (outside the message's final paragraph) or `unread_final` (in a
final paragraph git does not read as a trailer block), and `stated` is the sentence the text
report prints for it. Each `findings` entry is `{rule, verdict, node, beads, where, files,
uncommitted}`. The MCP `complete_bead` tool returns the same object as `owners`
([MCP reference](../services/mcp.md)).

### The git hooks

`beadloom install-hooks` writes two hooks, and an installed hook keeps the text it was
written with: re-run the command after upgrading.

- **pre-push** first runs `beadloom landing-check --stdin` over the refs git hands it
  (BDL-083 S2g, BDL-UX #354, RFC D12). The merge slot is tracker state exported into
  `.beads/issues.jsonl`, so the trunk says what the last landed export says. A push whose
  export at the pushed commit still holds the slot for a bead its commits carry (by their
  `Bead:` trailer) is refused with exit 1, before the Gate runs, with `Landing lock: REFUSED --
  ...` and the four commands that land the release: `bd merge-slot release --holder <bead>`,
  `bd export -o .beads/issues.jsonl`, a commit of the export by path, `git push`.
  Through 9.0.0 that push went through, and the next clone's `bd merge-slot acquire` was refused naming a
  closed bead. A landing therefore runs acquire → commit → release → `bd export` → the export
  landed → push. A hold by a bead the push does not carry reads `clean`, and a check that gave
  no verdict or could not judge the push reads `NOT CHECKED` and never blocks.
- **pre-push** then runs `beadloom ci --format rich --tee <temporary file>` and reads the verdict
  line from the copy, because a report captured and reprinted by the shell was lost on a
  non-blocking pipe (BDL-UX #226). A red verdict blocks the push. A run that leaves no
  verdict line is reported as `the Gate did not run: beadloom ci exited N without a verdict`
  and blocks the push too, whatever `N` was. Without `beadloom` on the `PATH` git runs the
  hook with, it exits 1 with a sentence saying the push was not judged (BDL-UX #326). Through
  9.0.0 that case exited 0 in silence. `git push --no-verify` skips the hook.
- **pre-commit** judges the paths the commit stages. Its legs, in order: ruff over the staged
  Python files, run from the outermost directory holding a `pyproject.toml` above them, with
  ruff's own exit code read so `ruff did not run (exit N)` is told apart from violations
  (BDL-UX #327), the type check over the declared typed surface, the architecture lint over
  the nodes that own a staged path (`beadloom lint --staged --strict`, BDL-083 S1a),
  `sync-check --staged`, the declared-axes verdict, and the ACTIVE/tracker coherence step.
  `--mode warn` reports an error and `--mode block` refuses the commit on it. A leg that could
  not run reads `NOT CHECKED` and blocks in neither mode, and the declared-axes verdict warns in
  both.

### What `docs audit` reports: three populations, not one

The `docs audit` step compares numbers and versions stated in prose against the same
facts computed from the project. Its headline is not the finding count but the
coverage line beside it, and that line names **three** populations rather than
folding them together:

| Population | What it means | Where a fact goes |
|------------|---------------|-------------------|
| **verified** | at least one document states the fact and the run judged it | inside the denominator, counted as checked |
| **not applicable to this project** | the registry declined to compute a value here, with a stated reason | **outside** the denominator entirely — neither verified nor unverified |
| **declared but unverified** | the project computes the fact and no document states it, or the scanner cannot read a claim of it | inside the denominator, named rather than counted as clean |

The third population is the one a finding count cannot express: a run that reports
`19 mention(s) fresh` may have restated one fact nineteen times while eight others
were never touched. Naming it is what stops a green audit reading as a clean bill of
health.

The second exists because a denominator that shrinks in silence is worse than one
that is wrong. A collector that could not compute a fact used to omit it, so an
unregistered CLI surface turned `3 of 9 declared fact(s) verified` into `3 of 8`
with nothing saying which fact left. A decline is now a value carrying its own
reason, and the reason names the escape hatch: declare the project's own value under
`docs_audit.extra_facts` in `.beadloom/config.yml`.

Two facts are about the **running package** rather than about every project — the MCP
tool catalogue and the CLI command surface — and are computed only when the audited
project declares itself to be that package. Every other project sees them under *not
applicable* with the reason, instead of being told it has a surface it does not have.

```bash
beadloom docs audit                          # the report, with every population named
beadloom docs audit --json                   # `verified_facts`, `unverified_facts`, `not_applicable`
beadloom docs audit --fail-if unverified>3   # turn coverage into a gate of your own
```

Coverage does not fail or warn the step by default. Silence in the documentation
about a fact is not a defect in the code, and a warning every project would carry on
every run would spend the channel `sync-check` needs for a real missing baseline.

### Two steps are warn-only, and one severity rule spans every rule

**Two steps are warn-only by design, and stay so.** `docs-quality` and `doc-spaces`
set `passed` unconditionally: every finding is a warning and the exit code does not
move. A check that turns an adopter's green project red on upgrade is a check that
gets disabled, and a disabled check reports nothing at all. The consequence is worth
stating rather than discovering: a project can carry findings from either step and
still push through a green Gate. What those steps guarantee is that the findings are
**printed by name** with the population behind them, and that a step which could not
decide reports `WARN` rather than `PASS`.

**A rule that checked nothing reports that, and how loudly depends on how much it
missed.** `lint --strict` counts the rules that were unable to check anything and
prints the count beside the rules it evaluated, so a green line cannot advertise a
check that looked at nothing. The severity of saying so is deliberately not uniform.
**Partial** inertness — a dead glob, an exemption that excuses nothing, a matcher
selecting no node while the rule's other legs still fire — always reports `warn`,
because it is a configuration smell rather than a boundary breach and promoting it
would redden an adopter's pipeline on an upgrade that changed none of their code. A
**total** stand-down, where a rule could check none of its population, is a different
fact: "found nothing wrong" and "never ran" are then the same output, and a project
that raised the rule to `error` has had its escalation evaporate exactly when it
mattered. `doc-area-coherence` and `graph-summary-facts` therefore report a total
stand-down at the severity the project declared. What that costs depends on the
severity each ships: `doc-area-coherence` ships `warn`, so an adopter is unaffected,
while `graph-summary-facts` ships `error` and will fail the gate for a project whose
node summaries state no checkable number. Set `severity: warn` on that rule if the
report is wanted without the block (BDL-062 `.14`).

**What `--no-reindex` costs the verdict.** Skipping the reindex step makes every
later step describe the index rather than the working tree: `lint` can pass over a
crossing that exists on disk, and `sync-check` compares against whatever baseline
the index already holds. Use the input only when something else in the same job
has just reindexed. The opposite mistake is just as costly and less obvious: a
gate run against a database built **from scratch** re-baselines every doc-code
pair as it indexes, so its `sync-check` step reports every pair fresh by
construction. On a fresh CI checkout, drift is detected with
`sync-check --since <git-ref>` rather than by the stored baseline — that is what
the AI tech-writer harness passes the push parent for.

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

Since BDL-083 S2 the verdict is the same in a checkout, a `git worktree` and a clean room of the
same files: the composition takes the project's name from `.beadloom/config.yml`
`project_name:` or a root manifest, never from the directory, and every run names the file it
compared, the flow configuration it composed from, the layers and the name's source (S2c). On
a project whose `flow.yml` declares `claude` and `cursor`, a tool whose files lack a layer the
other tool's carry exits 1 (S2h). The [CLI reference](../services/cli.md#beadloom-config-check)
has the measurements.

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
| `no-reindex` | `false` | Skip the reindex step, so every later step judges the existing index rather than the checked-out tree. |
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
