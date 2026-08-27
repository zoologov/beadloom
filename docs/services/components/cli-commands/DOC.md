# CLI Commands (component)

The Click command groups the CLI service is assembled from.

**Source:** `src/beadloom/services/commands/`

**Dependencies:** `click`, `rich`, the `application` layer, and — through
`_root` — nothing above it.

---

## Overview

`services/cli.py` used to be one module holding every command. BDL-059 S4 split
it by responsibility: each module here owns one nameable group of commands and
registers them onto the shared `main` Click group defined in `_root.py`.
`beadloom.services.cli` imports the modules to wire them, so
`from beadloom.services.cli import main` still resolves to the same object it
always did.

The node's `source` is the **directory**, not a file. A component whose source
is a package `__init__.py` records that file as its whole surface, and every
symbol reader then sees an empty façade (BDL-UX #157). Pointing at the directory
keeps all fourteen modules inside the node for `module-coverage` and for the
symbol counts.

## Presentation only

These modules parse arguments, call one application or domain entry point, and
render. No command holds a query or a decision: `status` renders what
`application.status.gather_status` read, `guard` renders what
`application.guards.invocation.run_invocation` decided, `review-brief` renders
what `application.review_brief` assembled. A command that starts computing an
answer belongs in the layer below, and `architecture-layers` (severity `error`)
is what holds that line.

## The modules

| Module | Commands |
|---|---|
| `_root.py` | the shared `main` group and the missing-parser warning helper — no command of its own. The summary `beadloom --help` prints is `help=_HELP`, derived from the package docstring rather than written as the group's own docstring: it was a third hand-written copy of the product description and shipped the 1.x sentence through both 3.0 patch releases (BDL-UX #211) |
| `query.py` | `ctx`, `graph`, `why`, `search`, `prime` |
| `index_ops.py` | `reindex`, `doctor`, `diff`, `link` |
| `status.py` | `status` |
| `docsync.py` | `sync-check`, `sync-update`, `install-hooks`, `active-sync` |
| `federation.py` | `export`, `federate`, `lint`, `ci` |
| `docs.py` | `docs generate`, `docs polish`, `docs site`, `docs audit`, `docs quality`, `docs spaces` |
| `setup.py` | `setup-mcp`, `setup-rules`, `setup-ai-techwriter`, `setup-agentic-flow`, `setup-branch-protection`, `config-check`, `mcp-serve`, `init` |
| `dashboard.py` | `tui`, `ui`, `watch` |
| `snapshot.py` | `snapshot save`, `snapshot list`, `snapshot compare` |
| `guard.py` | `guard` |
| `waves.py` | `waves` |
| `review_brief.py` | `review-brief` |

Every module carries `# beadloom:component=cli-commands`, so a module added here
without one is reported by `module-coverage` rather than joining the graph
silently.

## Related

- `cli` — the registration shell this component is wired into
  ([docs/services/cli.md](../../cli.md))
- `guard-probes`, `bd-seam` — the other two `services`-layer components
