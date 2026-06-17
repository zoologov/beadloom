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
  and consumer `references` (GraphQL), the typed `exposed_fields` /
  `referenced_fields` (GraphQL Tier-A, BDL-060 S2), and the `exposed_body` /
  `referenced_body` JSON-Schema (AMQP, BDL-060 S3).
- `classify(contract)` — derive the contract-level `ContractVerdict`. The
  `BREAKING` verdict is computed natively from depth on both sides: the typed
  GraphQL surface (`graphql_breaking`) or the AMQP body JSON-Schema (`amqp_body`,
  via `Contract.body_breaking_fields`), else the BDL-038 name-presence check.
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
