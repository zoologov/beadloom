# Status

Read the index and return the counts, coverage, health and trend figures the
`beadloom status` command renders.

**Source:** `src/beadloom/application/status.py`

**Parent:** [application](../../README.md)

**Dependencies:** `infrastructure.db` (`get_meta`), `infrastructure.health`
(`get_latest_snapshots`, `compute_trend`), `context_oracle.builder`
(`build_context`, `estimate_tokens`).

---

## Specification

### Purpose

`beadloom status` answers "what is in the index, and how healthy is it". That
question is two jobs: reading the figures, and painting them. This module owns
the first. `services/commands/status.py` owns the second and holds no query, so
the same figures are available to a caller that renders nothing — the JSON
output path and the TUI both read them here.

Every figure comes from the already-opened index connection. `project_root` is
accepted for symmetry with the other application read APIs and no figure is
derived from it, so the answer cannot depend on where the process was started.

### What is counted

| Group | Figures |
|---|---|
| Index | nodes, edges, docs, chunks, code symbols, the recorded `last_reindex_at` and `beadloom_version` |
| Coverage | nodes with at least one linked document, as a count and a percentage, plus the same split per node kind |
| Health | not-fresh sync pairs, isolated nodes, empty summaries |
| Trend | the delta between the two most recent health snapshots, or nothing when fewer than two exist |
| Context | average and largest context-bundle size in estimated tokens, and which node owns the largest |

### Not-fresh is two verdicts, not one

The stale figure counts `sync_state` rows whose status is `stale` **or**
`missing`. A pair whose document has been deleted is not one less thing to worry
about, and counting only `stale` reported a deleted document as health
(BDL-UX #174).

### An unmeasurable bundle is skipped, never guessed

`compute_context_metrics` builds a bundle per node and estimates its size with
the chars/4 heuristic. A node whose bundle cannot be built — `LookupError` or a
`sqlite3.Error` — is left out of the sample rather than recorded as zero, and a
graph in which no bundle could be built reports zeros with an empty
`largest_bundle_ref_id` rather than naming a node it never measured.

## Invariants

- No figure is written. The module issues `SELECT` only.
- `StatusData` is a frozen dataclass, so a renderer cannot change what it was
  handed.
- Coverage is `0.0` on an empty graph rather than a division by zero.

## API

| Entry point | Answers |
|---|---|
| `gather_status(conn, project_root)` | the whole payload, as a `StatusData` |
| `compute_context_metrics(conn, nodes_count, symbols_count)` | the bundle-size figures alone |
| `StatusData` | the frozen value the two above return |

## Structure

One module. The queries, the trend read and the bundle measurement are one
responsibility — reading the index for the status display — and splitting them
would leave three fragments no caller wants separately.

## Testing

`tests/test_s4_cli_decomposition.py::TestStatusLogicLayering` holds the layer
placement (the figures live in `application`, not in the command) and reads the
counts off a built index.

## Related

- `beadloom status` — the command (`src/beadloom/services/commands/status.py`)
- `health` — the snapshot store the trend is computed from
  (`docs/domains/infrastructure/components/health/DOC.md`)
