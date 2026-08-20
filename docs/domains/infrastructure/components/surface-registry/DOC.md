# surface-registry

Port for the live CLI / MCP surface. The services layer registers how to reach
it; the checks underneath read it without ever importing upward.

## Why it exists

Several checks compare a **documented claim** against **runtime truth**:

- `doctor` verifies `CLAUDE.md` / `AGENTS.md` claims about the number of CLI
  commands and MCP tools,
- `docs audit` does the same for numbers written in prose,
- `sync-check` hashes the CLI's command/option tree to detect surface drift
  behind a `watches=cli` doc.

Getting that truth means asking the **services** layer — the outermost one —
from the domain and application layers underneath. Four call sites did that
directly with `from beadloom.services… import …` placed inside a function. The
intent was right and the direction was wrong, and it stayed invisible because
nested imports were not extracted into the graph: the boundary and cycle rules
meant to catch exactly this could not see it (BDL-UX #159). Once they could, it
surfaced as six violations at once — two layering breaks, three
`no-domain-depends-on-service` denials and two cycles.

## Contract

```python
register_cli_group(provider)      # services/cli.py, on import

get_cli_group()  -> group | None  # None = surface unknown
reset_surface_providers()         # tests only
```

Only the CLI needs a port. The MCP tool list already has a canonical lower-layer
source — `infrastructure/mcp_tools.MCP_TOOL_CATALOG`, pinned equal to the
server's live registry by a test — so its consumers read that directly and no
registration is involved. The CLI's command/option tree has no such static
mirror: `sync-check` hashes the LIVE Click group to detect surface drift, so it
must be handed the real thing.

Providers are stored as callables and invoked on each read, so a surface built
after registration is still seen. A provider that raises degrades to `None`
rather than propagating into a check.

## Unknown is not zero

`get_cli_group()` returns `None` when nothing is registered, which is
deliberately **distinct from a real but empty surface**. A caller must choose
explicitly between reporting "not verified" and reporting a number:

- `doctor` emits an `INFO` check saying the surface was not available, instead
  of announcing "0 commands registered".
- `docs audit` records no fact at all, instead of a `0` that would report every
  documented count as drifted.
- `sync-check`'s `cli_signature()` digests a stable sentinel, so `watches=cli`
  docs are not silently re-baselined against an empty CLI.

A check that cannot see its subject and reports a plausible number anyway is the
failure mode this codebase exists to prevent — the same shape as #146 and #157.

## Collaborators

Registered by `services/cli.py`. Read by `application/doctor.py`,
`doc_sync/audit.py` and `doc_sync/surface.py`. Nothing here imports
`beadloom.services`.
