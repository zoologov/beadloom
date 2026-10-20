# S3e — the site, graph output, snapshot, federation and AsyncAPI entries, re-measured

- **Date:** 2026-10-20
- **Bead:** `beadloom-8pzg`
- **Version:** Beadloom 9.0.0 as S2 ships it: a git worktree of `features/BDL-083` at
  `cdaf3f78428061e51479723f59d666d952bf774e`. `git diff --quiet 41245dc7 cdaf3f78 -- src
  pyproject.toml uv.lock docs` exits 0, so the code and the documents measured are those of
  `main` at `41245dc7`.
- **Machine:** macOS 27.0 (Darwin 27.0.0), arm64, CPython 3.12.12 from `uv sync --frozen` in
  the worktree.
- **Index:** the worktree's own, built by `beadloom reindex --full` inside it. The main
  checkout's index was not read or written. The throwaway projects for #160 lived in the
  scratchpad and were deleted afterwards.
- **Room:** one room, this machine. No Linux leg and no other interpreter was entered. None of
  the three entries depends on the platform, and that is a reading of the code, not a
  measurement on another leg.

### #343

- **Command:** `beadloom snapshot compare stage-1 wave-12`
- **Where:** the worktree, after `beadloom reindex --full` and two labelled saves
  (`beadloom snapshot save --label stage-1`, `beadloom snapshot save --label wave-12`). The
  entry's own context is an outside monorepo; the defect sits in the argument declaration and
  does not depend on the project.
- **Printed:**

  ```
  $ beadloom snapshot list
    #2 [wave-12]  2026-10-20 07:42:53  nodes=144 edges=704 symbols=3497
    #1 [stage-1]  2026-10-20 07:42:52  nodes=144 edges=704 symbols=3497
  $ beadloom snapshot compare stage-1 wave-12
  Error: Invalid value for 'OLD_ID': 'stage-1' is not a valid integer.      (exit 2)
  $ beadloom snapshot compare 1 2
  No changes between snapshot #1 and #2.                                    (exit 0)
  ```

  `src/beadloom/services/commands/snapshot.py:100-101` still declares both arguments
  `type=int`, and `snapshot compare --help` names them `OLD_ID NEW_ID` with no mention of a
  label.
- **Outcome:** live.
- **Evidence:** On 2026-10-20, on Beadloom 9.0.0 (`cdaf3f78`, code identical to `main` at
  `41245dc7`), `snapshot compare stage-1 wave-12` exited 2 with "'stage-1' is not a valid
  integer" while `snapshot list` printed both labels, and `compare 1 2` succeeded.
- **Bead:** none exists (`bd list --all --limit 0`, 1330 rows, no title carries `#343`).
  Proposed: `[BDL-UX #343] snapshot compare accepts the label snapshot list prints, as well as
  the number`.

### #160

- **Command:** `beadloom reindex` / `beadloom federate` on a project described with AsyncAPI.
- **Where:** three places. The worktree, for the code path and the documents. A throwaway
  producer satellite with an AsyncAPI 2.6 document and an AMQP contract edge. A throwaway
  consumer satellite whose declared body conflicts with that document. The two satellites were
  federated in a throwaway hub.
- **What the documentation claims, on the S2 version:**
  - `docs/domains/graph/features/federation/SPEC.md:358`: "teams on AsyncAPI ingest the payload
    schema via the source-only `asyncapi.extract_payload_body` adapter". The issue log quotes
    this sentence at line 353, and it has moved down to line 358.
  - `docs/domains/graph/features/federation/SPEC.md:320`: the paragraph "**AsyncAPI ingestion
    (source-only).**" and the signature under "`# asyncapi.py — source-only ingestion`".
  - `docs/domains/graph/README.md:25`, `:115` and `:154`: "Teams using **AsyncAPI** can ingest
    the message payload JSON-Schema via the source-only `asyncapi.extract_payload_body` adapter".
  - `docs/domains/graph/components/asyncapi/DOC.md`: "Teams that already describe their AMQP
    messages with an AsyncAPI document shouldn't be left out of the strict body diff", and "the
    caller then keeps name-level AMQP". There is no caller.
  - The node summary in `.beadloom/_graph/asyncapi.yml`: "Source-only AsyncAPI ingestion
    adapter".

  None of the five carries "unwired", "building block" or any equivalent. The downgrade the
  entry asked for "if this slips much further" has not been made.
- **What is wired:** `src/beadloom/graph/asyncapi.py` (142 lines,
  `extract_payload_body(document, channel=None)`), with its two test files
  `tests/unit/graph/asyncapi/test_asyncapi_ingest.py` and `test_asyncapi_fidelity.py`. Called
  directly on the fixture's document, it returns the right body:
  `{'type': 'object', 'properties': {'plan_id': {'type': 'string'}}, 'required': ['plan_id']}`.
- **What is not wired:** everything between an AsyncAPI document and a contract body.
  - `grep -rni "asyncapi\|extract_payload_body" src/`, excluding the module itself, finds
    nothing (exit 1). The one dynamic import under `src/`, in
    `application/source_derivation/termination.py`, imports standard-library modules only.
  - The loader has no `body_from` key, and nothing reads an AsyncAPI document.
  - `beadloom why asyncapi` prints "No downstream dependents", and `beadloom doctor` names no
    island. That check is `beadloom-uxqc` (#162), still open.
- **Printed (end to end):**

  ```
  # producer: contract {protocol: amqp, exchange: plans, routing_key: plan.upload,
  #   message_type: start_upload, direction: produces, body_from: asyncapi.yaml}
  #   + asyncapi.yaml whose payload is {plan_id: string, required [plan_id]}
  $ beadloom reindex   -> exit 0, no warning about body_from or AsyncAPI
  $ beadloom export    -> contract: {"body_from": "asyncapi.yaml", "direction": "produces",
                          "exchange": "plans", "message_type": "start_upload",
                          "protocol": "amqp", "routing_key": "plan.upload"}     (no "body")
  # consumer: same identity, body {plan_id: integer, size: number, required both}
  $ beadloom federate --fail-on default <producer> <consumer>
  ## Contracts (1)
  - CONFIRMED: 1                                                            (exit 0)
  # control: the SAME payload declared inline as body: on the producer
  $ beadloom federate --fail-on default <control> <consumer>
  ## Contracts (1)
  - BREAKING: 1                     missing ['plan_id', 'size']             (exit 1)
  ```

  The key the deferred plan names (`body_from:`) is carried verbatim into the export and never
  resolved. The payload the AsyncAPI document describes therefore never reaches the body diff,
  and a contract the native diff calls BREAKING gates green as CONFIRMED. Nothing on the way
  says that the document was ignored.
- **Outcome:** live.
- **Evidence:** On 2026-10-20, on Beadloom 9.0.0 (`cdaf3f78`, code identical to `main` at
  `41245dc7`), no module under `src/` references `beadloom.graph.asyncapi`. A producer that
  points at an AsyncAPI document exported no `body` and federated `CONFIRMED` (exit 0) against
  a consumer that the same payload, declared inline, makes `BREAKING` (exit 1). Five documents
  still describe the adapter as ingestion.
- **Bead:** `beadloom-g79p`
  (`[BDL-UX #160] AsyncAPI ingestion is documented as a capability but wired to nothing`),
  status `deferred`, P2. It has no parent, so it is not under `beadloom-ba9w` as D9 asks of a
  live entry's bead. The implementation plan the entry points to ("`ROADMAP.md` under P1 →
  ⏸ Deferred … wire the AsyncAPI ingestion path") is no longer in `.claude/development/ROADMAP.md`
  or in its archive. `git log -S` shows it was removed by `eb8309ab` (BDL-066), so the issue log
  and the bead are now the only places that hold it. **Ruling needed from the owner:** either
  re-parent `beadloom-g79p` under `beadloom-ba9w` and wire the adapter, or downgrade the five
  claims to "unwired building block" now. The second costs only a document edit, and while it
  waits the claim stays false.

### #149

- **Command:** `beadloom graph --format c4 --level component --scope <ref_id>`
- **Where:** the worktree, on two leaf nodes (`asyncapi`, `snapshot`), with a node that has
  internals (`graph`) and an unknown ref as controls. The entry's own context is a downstream
  integration; the behaviour lives in `src/beadloom/graph/c4.py` and does not depend on it.
- **Printed:**

  ```
  $ beadloom graph --format c4 --level component --scope asyncapi
  C4Container
                                                                            (exit 0)
  $ beadloom graph --format c4 --level component --scope snapshot
  C4Container
                                                                            (exit 0)
  $ beadloom graph --format c4-plantuml --level component --scope asyncapi
  @startuml
  !include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Component.puml


  @enduml                                                                   (exit 0)
  $ beadloom graph --format c4 --level component --scope graph   -> 33 lines,
      System_Boundary(graph_boundary, "graph") { Component(amqp_body, ...) ... }
  $ beadloom graph --format c4 --level component --scope no-such-node
  Error: --scope ref_id 'no-such-node' not found in graph                   (exit 1)
  ```

  The output is emptier than the entry recorded. It is not "a single box": it is the bare
  `C4Container` header with no element and no boundary, and the PlantUML form is an empty
  `@startuml`/`@enduml` pair. Nothing goes to stderr. `_filter_component` (`c4.py:503-513`)
  checks that the scope exists, keeps the nodes whose `boundary == scope`, and does not look at
  whether that list is empty.
- **Outcome:** live.
- **Evidence:** On 2026-10-20, on Beadloom 9.0.0 (`cdaf3f78`, code identical to `main` at
  `41245dc7`), `graph --format c4 --level component --scope asyncapi` (a leaf) exited 0 and
  printed only `C4Container`, and the PlantUML form printed an empty diagram. The unknown ref
  `no-such-node` exited 1 with a message.
- **Bead:** none exists (`bd list --all --limit 0`, no title carries `#149`). Proposed:
  `[BDL-UX #149] graph --format c4 --level component --scope <leaf> names the node as having no
  internals and exits non-zero, instead of printing an empty diagram`.

## Summary

| Entry | Outcome | Bead |
|---|---|---|
| #343 | live | proposed: `[BDL-UX #343] snapshot compare accepts the label snapshot list prints, as well as the number` |
| #160 | live | `beadloom-g79p` (deferred, P2, no parent; owner's ruling needed: wire it under `beadloom-ba9w`, or downgrade the five claims now) |
| #149 | live | proposed: `[BDL-UX #149] graph --format c4 --level component --scope <leaf> names the node as having no internals and exits non-zero, instead of printing an empty diagram` |

Counts: 0 closed, 3 live, 0 won't-fix candidates, 0 not reproducible, 0 not this area.
