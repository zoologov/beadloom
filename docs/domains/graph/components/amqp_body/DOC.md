# AMQP Body (component)

Internal building block of the graph domain.

**Source:** `src/beadloom/graph/amqp_body.py`

---

## Overview

The strict AMQP message-body JSON-Schema model + native body-diff (BDL-060 S3,
G1b). The name-level AMQP contract (F1/BDL-038) only knew a `message_type` flowed
between a producer and a consumer; this component deepens it with an optional
`body` — a minimal JSON-Schema describing the payload (`type`, `properties`,
`required`, `enum`, nested objects and array `items`) — and the NATIVE diff that
decides whether a producer body breaks a consumer that reads it. It is the AMQP
sibling of the GraphQL `graphql_breaking` component: a pure, structured
comparison that names the offending field path; Beadloom computes the verdict
itself (no external schema tool).

A consumer-read field breaks when, vs the producer body, it is:

- **absent** — the producer no longer declares the property;
- **type-incompatible** — the producer property's `type` (or its structural
  shape: object vs array vs scalar) no longer matches what the consumer reads;
- **required-by-consumer-but-now-optional/removed** — the consumer requires the
  field but the producer no longer requires it (or dropped it);
- **enum-narrowed** — the producer dropped an enum value the consumer relies on.

Nested objects (`properties`) and array `items` recurse with the same rigor, the
path named `parent.child` / `field[]` / `field[].child`. Additive producer
fields, a producer that widens requiredness, and an enum-widened producer are
benign.

## Public surface

- `BodySchema` — a frozen, recursive JSON-Schema body node (`type`, `properties`,
  `required`, `enum`, `items`) with `to_payload()` → a deterministic sorted dict.
- `parse_body(payload) -> BodySchema` — tolerant parse (a non-mapping yields an
  empty unknown node — honest degradation, never a fabricated field).
- `serialize_body(payload_or_schema) -> dict` — deterministic, sorted body
  payload (properties + `required` sorted recursively) for the federation wire.
- `breaking_body_descriptors(producer_body, consumer_body) -> list[str]` —
  sorted, deduped field paths the producer body breaks for the consumer that
  reads it; empty when every read field is satisfied.

## Data strictness

The model is the minimal honest JSON-Schema body — never a fabricated field or
type. An unknown (`""`) type on either side is treated as compatible (we never
claim a break we cannot prove). The verdict layer (`contracts`) invokes the diff
ONLY when both producer and consumer declared a body; absent that depth the AMQP
verdict degrades honestly to the both-sides name-presence check (BDL-038 parity).
