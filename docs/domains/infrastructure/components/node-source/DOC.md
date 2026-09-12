# Node Source (component)

Internal building block of the infrastructure domain.

**Source:** `src/beadloom/infrastructure/node_source.py`

---

## Overview

Answers one question: does a file lie under a node's declared `source`? A file lies
under it when its path IS the source, which is the single-file case, or continues it
past a `/`. `src/ledger/` therefore holds `src/ledger/core.py` and does not hold
`src/ledger_archive/core.py` or `src/ledger.py`, though both start with the same
characters. A source that declares nothing holds nothing, although the empty string
is a prefix of every string.

The rule was written three times, in three domains, before BDL-069
`beadloom-rqma.4`. `doc_generator._symbols_for_node` and
`git_activity._map_file_to_node` matched by path component. `reindex`'s route
attribution matched by string prefix, so a node was given the HTTP routes of a
sibling whose name it prefixes, and a root declaring `source: ''` was given every
route in the project. All three call this component now, and a test runs one table
of source shapes against each of them.

The three copies also disagreed on spelling before they disagreed on siblings.
`git_activity` did not strip surrounding whitespace and `doc_generator` did not
collapse a leading `./`, measured by that table against the three bodies. One
normalisation now applies to all three.

## Public surface

- `NodeSource(declared)` — a node's declared source, normalised once: surrounding
  whitespace, `.` segments and a trailing `/` removed. `None`, `''` and `/` all
  declare nothing.
- `NodeSource.path` — the normalised source, or `''`. `git_activity` ranks the nodes
  that hold a file by its length, most specific first.
- `NodeSource.holds(file_path)` — whether `file_path` is the source or continues it
  past a `/`. Always `False` for a source that declares nothing, including for a path
  that starts with `/`.

## Invariants

- **Only the declared source is normalised.** The file path is compared as given, in
  the form the indexer, the route scan and `git log` produce: project-relative, with
  `/` separators. A person types the source, and a program produces the path. Building
  a `PurePosixPath` was measured at 2.67 µs against 63.5 ns for the comparison itself.
  The polish reader asks once per file per node, which was 27 144 times over this
  repository on the day it was measured, so normalising inside `holds` would have cost
  about 72 ms there. That figure is computed from the two measurements, not timed.
- **This is not ownership.** `infrastructure.repository.source_covers` answers which
  node OWNS a file: a package facade covers its package there, and the most specific
  source wins. A caller asking that question calls that function. The polish reader
  keeps a facade source to the facade because the skeleton's disk reader does.

## Placement

The component lives in `infrastructure` because `git_activity` does, and the lowest
layer imports nothing above it. `onboarding` may not import `infrastructure`
(`onboarding-no-direct-infra`, severity `error`), so `doc_generator` reaches this
module through an exemption in `.beadloom/_graph/rules.yml` that states its reason.
`beadloom lint` counts that crossing among the suppressed ones on every run.

Placing it in a domain was measured as well. `lint --strict` reported no finding for
an `infrastructure -> graph` import, because `architecture-layers` evaluates only
edges whose two ends carry a layer tag, and a tag is not inherited through `part_of`.
On this repository's index that leaves most of the graph's dependencies unevaluated,
and the measured count is recorded in `beadloom-t6zq`, where the gap is filed.
Choosing a place because the check cannot see it would have been the wrong reason.

## Collaborators

- `onboarding/doc_generator.py` — `_symbols_for_node`, the symbols `docs polish` and
  the MCP `generate_docs` tool hand an agent.
- `application/reindex/enrichment.py` — `_extract_and_store_routes`, the routes
  stored in `nodes.extra`.
- `infrastructure/git_activity.py` — `_map_file_to_node`, which file of a commit
  counts toward which node's activity.

> Component doc (BDL-069 `beadloom-rqma.4`). Public surface verified against
> `node_source.py`.
