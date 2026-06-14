<!-- beadloom:badge-start -->
> 📘 **reference** — overview/guide, not tied to a code symbol
> 
> _Validation by Beadloom `doc_sync` — same source as `sync-check`._
<!-- beadloom:badge-end -->

# Getting Started

This guide takes you from zero to a working Beadloom setup — including the
configurable, multi-agent dev flow.

## What Beadloom does

Beadloom keeps the architecture you *intended* and the code you *actually
shipped* from drifting apart. It stores a queryable map of your system —
domains, services, features, components, and the contracts between them — as
plain YAML in Git, then continuously checks the real code against it:

- **Docs that can't go stale.** Beadloom tracks which docs describe which code and flags the ones that fall behind — on every commit, in CI, or on demand.
- **Boundaries that are enforced.** You write architecture rules in YAML; `beadloom lint` blocks violations in CI, no matter who (or which AI tool) wrote the code.
- **Contracts checked across services.** Federate per-repo graphs into one landscape and Beadloom reconciles what each service *says it provides* against what its consumers *actually use* — catching a broken contract before it ships.
- **Context for AI agents.** `beadloom prime` hands an agent a compact (<2K-token) picture of the architecture, and `setup-agentic-flow` composes a full multi-agent workflow (dev → test → review → tech-writer) for Claude Code and Cursor.
- **A self-governing model.** No shadow code: every source module must be a tracked graph node or explicitly exempt, enforced as a CI error.

## Requirements

- Python 3.10+
- uv (recommended) or pip
- Optional: a git repo (for the hooks and the agentic flow), `bd` (the [beads](https://github.com/steveyegge/beads) tracker, for the agentic flow)

## Install

```bash
uv tool install beadloom        # recommended
pipx install beadloom           # alternative
pip install beadloom            # also works
```

Optional extras (language parsers, TUI, file watcher):

```bash
uv tool install "beadloom[languages]"   # TS/JS, Go, Rust, Kotlin, Java, Swift, C/C++, Objective-C
uv tool install "beadloom[tui]"         # interactive terminal dashboard
uv tool install "beadloom[watch]"       # file watcher for auto-reindex
uv tool install "beadloom[all]"         # everything
```

## Initialize

```bash
cd your-project
beadloom init --bootstrap     # scan code → generate an initial graph
```

`--bootstrap` scans your code structure and proposes domains, services, and
features. Use `--yes` (or `--non-interactive`) to skip prompts (CI / automation).
`init` creates:

- `.beadloom/_graph/services.yml` — the architecture graph (nodes + edges)
- `.beadloom/_graph/rules.yml` — auto-generated architecture lint rules
- `.beadloom/config.yml` — project configuration
- `docs/` — documentation skeletons for each graph node
- `.mcp.json` (or equivalent) — MCP config for the detected editor

It also runs a full reindex: code symbols are extracted, imports resolved, and
`depends_on` edges inferred from code.

> No documentation is required to start — Beadloom bootstraps a skeleton from
> code structure alone. You fill it in by hand or with any AI agent (see
> `beadloom docs polish`), and Beadloom keeps it current.

## Configuration

Everything lives under `.beadloom/` in your repo.

### `.beadloom/config.yml`

| Key | Default | Description |
|-----|---------|-------------|
| `scan_paths` | `["src", "lib", "app"]` | Source directories to scan |
| `languages` | all supported | File extensions to parse (e.g. `[".py", ".ts"]`) |
| `docs_dir` | `docs/` | Documentation root directory |
| `sync.hook_mode` | `warn` | Pre-commit hook mode: `warn` or `block` |

### `.beadloom/flow.yml` — the agentic dev flow

Declare *what your project is*, once. `setup-agentic-flow` reads this to compose
the role workflow:

```yaml
tools:        [claude, cursor]   # generate adapters for one or both
architecture: [ddd]              # ddd | fsd (exactly one)
stack:        [python]           # python, fastapi, javascript, typescript, vuejs
quality:      [clean-code, tdd]
```

Then:

```bash
# Compose roles from CORE + architecture overlay + stack overlays,
# and write the per-tool adapter set(s):
beadloom setup-agentic-flow

# Override the flow.yml selection from flags:
beadloom setup-agentic-flow --tool cursor --architecture fsd --stack typescript,vuejs
```

This writes `.claude/agents/*` (Claude Code) and/or `.cursor/agents/*` (Cursor)
at parity. `config-check` byte-guards every generated adapter against its
composition, so the workflow never silently drifts from the graph.

### Git hooks — pre-commit + the pre-push Gate

```bash
beadloom install-hooks
```

Installs **both** hooks by default:

- **pre-commit** (lighter) — runs `sync-check`, lint, and the ACTIVE/tracker coherence step (`warn` or `block` via `--mode`).
- **pre-push Beadloom Gate** (authoritative) — runs the full `beadloom ci` (reindex → `lint --strict` → sync-check → config-check → doctor) and **blocks the push on red**. It is fail-safe (a no-op when `beadloom` isn't on `PATH`); `git push --no-verify` is the documented escape hatch.

Select one with `--pre-commit` / `--pre-push`; remove with `--remove`.

### MCP + IDE rules

```bash
beadloom setup-mcp                 # .mcp.json (Claude Code) / .cursor/mcp.json (Cursor) / Windsurf config
beadloom setup-mcp --tool cursor   # target a specific editor
beadloom setup-rules               # thin IDE adapter files pointing at .beadloom/AGENTS.md
```

The MCP server (`beadloom mcp-serve`) exposes 18 tools — 14 graph read/write
tools plus four process tools (`task_init`, `bead_context`, `checkpoint`,
`complete_bead`) that drive the agentic flow.

## Usage examples

### A. The core loop

```bash
beadloom prime              # compact (<2K-token) project context for an agent
beadloom ctx sync-check     # full context bundle for a node (add --json to parse)
beadloom why sync-check     # impact analysis: upstream deps + downstream dependents
beadloom graph              # Mermaid architecture diagram
beadloom search "stale"     # FTS5 search across nodes, docs, and code symbols
beadloom status             # node/edge/doc counts, coverage, health trends
```

Validate before you commit:

```bash
$ beadloom sync-check
✓ 149/149 doc-code pairs in sync

$ beadloom lint --strict    # exit 1 on error-severity violations (for CI)
✓ All architecture rules satisfied

$ beadloom ci               # the unified gate, one exit code
reindex        PASS
lint           PASS
sync-check     PASS
config-check   PASS
doctor         PASS
✓ CI gate passed
```

> `sync-check` exits 2 when docs are stale. `beadloom sync-update <ref> --yes`
> walks you through (or auto-applies) the fix until the stale count reaches 0.

### B. The agentic dev flow walkthrough

With `flow.yml` configured and `setup-agentic-flow` run, a feature flows through
gated waves. The process roles live in your editor adapters (`.claude/commands/*`
for Claude Code); the four work roles are subagents:

1. **`/task-init`** — scaffold the work item (PRD/RFC/CONTEXT/PLAN/ACTIVE or BRIEF) and create the beads (tracked in `bd`).
2. **`/coordinator`** — orchestrate the waves, gated by bead dependencies:
   - **dev** — implement the bead (TDD), update its `SPEC.md`/`DOC.md`.
   - **test** — write/extend tests, verify coverage.
   - **review** — read-only quality + boundary check (`beadloom diff`, `lint`).
   - **tech-writer** — refresh the docs the change touched (`sync-update`).
3. **Push** — the **pre-push Beadloom Gate** runs `beadloom ci`; a red gate blocks the push ("no code reaches `main` without current docs and clean boundaries").
4. **PR** — opening the PR triggers CI *and* the AI tech-writer (below); a human merges once green.

Each agent starts from `beadloom prime` / `beadloom ctx <ref>` instead of
grepping the codebase from scratch, so it works inside your architecture.

### C. The AI tech-writer

On a pull request, a packaged harness repairs drifted docs **on the PR branch**:

```bash
# Run it manually against the drift since a git ref (the push's parent commit);
# --platform selects the CI adapter, --dry-run reports the wiring without a model/PR:
python -m beadloom.ai_agents.ai_techwriter --platform github --since "$(git rev-parse origin/main)" --dry-run
```

It is **symbol-scoped** (a doc is rewritten only when a symbol it references
actually changed), bounded-parallel, and verdict-classified — `ok` / `flagged` /
`infra` — so a genuine unresolved doc drift blocks the PR, but a dead runner or
exhausted quota never freezes merges. CI is the true enforcement; the refresh is
a proposal a human merges.

### D. Federation — hub + satellites

Inside one repo the dangerous bugs hide *between* services. Each service
("satellite") exports its graph; a hub composes them and reconciles contracts:

```bash
# In each service repo — emit a deterministic, commit-stamped artifact:
beadloom export --out service-a.json

# At the hub — compose >=2 artifacts into one landscape and reconcile contracts:
beadloom federate service-a.json service-b.json service-c.json

# Arm the CI landscape gate (writes the artifact, THEN exits 1 on a bad verdict):
beadloom federate service-*.json --fail-on default
#   default fail-set = breaking,drift,orphaned_consumer,undeclared_producer
```

`federate` writes `.beadloom/federated.json` + `.beadloom/federated.txt` and
assigns each contract a verdict (`CONFIRMED` / `BREAKING` / `ORPHANED_CONSUMER`
/ `UNDECLARED_PRODUCER` / `EXTERNAL` / `DRIFT`) over AMQP and GraphQL, plus
per-satellite staleness. `beadloom ci --hub <export> --fail-on default` folds the
landscape gate into the unified CI verdict.

## Publish a knowledge base

```bash
beadloom docs site --out site            # generate a VitePress content tree
(cd site && npm install && npm run docs:build)   # build the static site
```

The site is a metrics dashboard, an interactive architecture view, a
cross-service landscape map, and your hand-written docs with a freshness badge
on each. `docs site` reads the graph read-only and never writes into your
source `docs/` tree.

## Keep docs in sync

```bash
beadloom sync-check          # doc↔code freshness (exit 2 = stale)
beadloom sync-update <ref>   # review/apply the fix for a node (--yes to auto-apply)
beadloom docs audit          # detect stale cross-references in prose docs (--stale-only, --json)
```

## Limits

- Code indexer parses Python, TypeScript/JavaScript, Go, Rust out of the box; Kotlin, Java, Swift, C/C++, Objective-C via `beadloom[languages]`. Import analysis spans 9 languages.
- Documentation is indexed from `docs/` (configurable via `config.yml`).
- The graph is YAML under `.beadloom/_graph/`; rules in `.beadloom/_graph/rules.yml`.
- Maximum documentation chunk size: 2000 characters.

## Next steps

- [Architecture](architecture.md) — system design, the node-kind model, the rules engine, the agentic-flow configurator.
- [CI Setup](guides/ci-setup.md) — GitHub Actions / GitLab CI integration.
- [VitePress Site](guides/vitepress-site.md) — publish the knowledge base.
