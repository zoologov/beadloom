# GraphQL Breaking (component)

Internal building block of the graph domain.

**Source:** `src/beadloom/graph/graphql_breaking.py`

---

## Overview

The NATIVE typed GraphQL breaking analysis (BDL-060 S2, G1a). Given a consumer's
referenced typed fields and a producer's exposed typed fields, it names the
consumer references the producer breaks. This is native rigor — Beadloom computes
the verdict itself; it does not delegate to an external GraphQL registry/tool.

A consumer reference breaks when, vs the producer surface, it is:

- **absent** — the producer no longer exposes the field;
- **type-incompatible** — the producer's return type changed (a different named
  type, or a nullability *narrowing*: producer became nullable where the consumer
  relied on non-null);
- **arg-broken** — the producer requires a non-null arg the consumer does not
  supply, or narrowed a supplied arg to non-null / a different named type.

Purely additive producer changes are benign: a new unreferenced field, a new
*nullable* arg, or *widening* a return type from nullable to non-null.

## Public surface

- `breaking_field_descriptors(exposed_fields, referenced_fields) -> list[str]` —
  sorted, deduped descriptors naming each broken reference: `"<field>"` for an
  absent/retyped field, `"<field>(<arg>)"` for an arg break. Empty when every
  reference is satisfied.

## Collaborators

Invoked by `contracts.Contract.breaking_fields` ONLY when both sides carry a real
typed surface (the typed `fields` block from `graphql_surface`); otherwise the
contract verdict degrades to the name-presence check. Feeds the `BREAKING`
`ContractVerdict` and the landscape gate's named-missing remediation.

> Component doc (BDL-060 S2). Public surface verified against `graphql_breaking.py`.
