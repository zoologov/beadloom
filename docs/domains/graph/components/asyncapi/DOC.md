# AsyncAPI (component)

Internal building block of the graph domain.

**Source:** `src/beadloom/graph/asyncapi.py`

---

## Overview

The source-only AsyncAPI payload-schema ingestion adapter (BDL-060 S3, G1b).
Teams that already describe their AMQP messages with an AsyncAPI document
shouldn't be left out of the strict body diff. This adapter is a *source* only:
it extracts the message **payload JSON-Schema** out of an AsyncAPI doc into the
SAME internal minimal-JSON-Schema body the rest of S3 reasons over (the
`amqp_body` component). It does NOT model AsyncAPI itself — operations, bindings,
servers and the like are out of scope; the internal model stays the minimal
honest body.

Both AsyncAPI layouts are handled:

- **2.x** — `channels.<channel>.{publish,subscribe}.message.payload`;
- **3.x** — `channels.<channel>.messages.<message>.payload`, with a one-hop local
  `$ref` into `components.messages` resolved.

## Public surface

- `extract_payload_body(document, channel=None) -> dict | None` — parse the raw
  AsyncAPI text (YAML or JSON) and return the selected channel's message payload
  as a plain JSON-Schema dict (the internal body shape), or `None` when there is
  no extractable payload. When `channel` is `None`, the first declared channel is
  used.

## Optional dependency / honest degradation

AsyncAPI docs are YAML or JSON, both read by the core `yaml.safe_load` (JSON is a
YAML subset), so this needs **no optional extra**. An unparseable/empty/
payload-less doc — or a foreign/remote `$ref` that would require a network fetch —
degrades honestly to `None`; the caller then keeps name-level AMQP and never a
fabricated body (the DATA-STRICTNESS invariant).
