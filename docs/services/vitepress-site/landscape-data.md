# Landscape data (component)

A slice of the `entities` layer of the VitePress site's Feature-Sliced layout. The layout and the
layer rule are described in [the site's page](../vitepress-site.md).

**Source:** `src/beadloom/site_scaffold/.vitepress/theme/entities/landscape-data/`

---

## Overview

The landscape data file, `landscape.data.json`, which `beadloom docs site` writes, fetched once
per page load, and what its contracts mean for the viewer. The file's contract, written by
`landscape_view.py`, is in the
[Site Generation SPEC](../../domains/application/features/site-generation/SPEC.md#the-landscape-data-file).

- **As a graph** (`model/graph.js`). A service is a node and a contract is an edge from each of
  its producers to each of its consumers, drawn and walked as a `produces` edge. Each edge carries
  its contract's key, verdict, health and look, and a broken edge carries its verdict as a badge.
  The impact walk reads the consumer, the edge's target, as the end that depends
  (`CONTRACT_DEPENDENT_ENDS`), for every protocol: a change to a service reaches the consumers of
  what it produces and never its producers.
- **Health** (`model/contracts.js`). A verdict falls into healthy, broken or neutral, the buckets
  the generator uses. A drifting contract is broken and is drawn apart from the other broken ones.
  A contract is declared when its protocol is one the reconciler reads a surface for (`amqp`,
  `graphql`); any other is a plain dependency.
- **Verified.** A contract is verified when its `verdict_basis` is `surface`: the verdict compared
  what the consumer reads with what the producer declares. A service that takes part in a broken
  contract, or in one that is neither broken nor verified, runs a risk (`contractRisksOf`). A file
  that carries no `verdict_basis` gives no contract as verified.

## Public API

- `useLandscapeData()` returns `{ data, error }`.
- `landscapeGraphOf(data)` returns `{ nodes, edges, contracts }`; `CONTRACT_EDGE_KIND`,
  `CONTRACT_DEPENDENT_ENDS`.
- `HEALTH`, `DRIFT`, `healthOf(verdict)`, `lookOf(verdict)`.
- `DECLARED_PROTOCOLS`, `isDeclaredContract(contract)`, `PLAIN_DEPENDENCY`,
  `protocolLabelOf(contract)`, `takesPart(contract, id)`.
- `isVerifiedContract(contract)`, `CONTRACT_RISKS`, `contractRisksOf(id, contracts)`.

## Depends on

- `site-shared`.
