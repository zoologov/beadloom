<!-- beadloom:badge-start -->
> ✅ **fresh**
> 
> last synced 2026-06-14T12:30:18.610981+00:00 · coverage 100% (`contracts`)
> 
> _Validation by Beadloom `doc_sync` — same source as `sync-check`._
<!-- beadloom:badge-end -->

# Contracts (component)

Internal building block of the graph domain.

**Source:** `src/beadloom/graph/contracts.py`

---

## Overview

The first-class cross-service contract model and its protocol-agnostic
reconciliation. Owns the `Contract` model, the language-neutral `contract_key`
derivation, the `ContractVerdict` enum, and `reconcile_contracts` (which
`federation.py` delegates to). Promotes the contract out of the edge-buried
`extra.contract` blob into a first-class object computed at the federation hub.

## Public surface

- `reconcile_contracts(edges)` — group AMQP + GraphQL contract-bearing edges
  into first-class `Contract`s by key, attaching the producer `exposed` surface
  and consumer `references`.
- `classify(contract)` — derive the contract-level `ContractVerdict`.
- `contract_key(payload)` — the protocol-prefixed, language-neutral key
  (`amqp:<exchange>/<routing>:<message_type>`, `graphql:<schema>`).
- `cross_landscape_keys(edges)` / `edge_group_key(...)` — grouping helpers for
  landscape-scoped reconciliation.
- `Contract` / `ContractEndpoint` — the model (with `Contract.to_report_dict`
  for projecting back to the F1 flat shape).
- `ContractVerdict` — the contract-level intent-vs-reality enum.

## Collaborators

`federation.py` delegates all contract reconciliation + classification here.
Consumes `produces` / `consumes` edges (and their `extra.contract` payloads)
from the graph; the verdicts feed the federation gate and the landscape map.
See the [federation SPEC](../../features/federation/SPEC.md).

> Component doc (BDL-051). Public surface verified against `contracts.py`.
