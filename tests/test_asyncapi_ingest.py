"""Golden tests for the source-only AsyncAPI body ingestion adapter (S3, G1b).

Teams that already describe their AMQP messages with an AsyncAPI document
shouldn't be left out: this adapter extracts the message **payload JSON-Schema**
out of an AsyncAPI doc (v2 ``channels.<ch>.{publish,subscribe}.message.payload``
or v3 ``channels.<ch>.messages.<m>.payload`` / ``components.messages``) into our
internal minimal-JSON-Schema ``body`` model. AsyncAPI is purely a SOURCE — the
internal model stays the same body we'd hand-author; the adapter never fabricates
a field.

Honest degradation (DATA-STRICTNESS): a doc with no extractable payload (missing
channel, no payload, malformed) yields ``None`` (no body) — the caller then keeps
name-level AMQP, never a faked body.
"""

from __future__ import annotations

import json

from beadloom.graph.asyncapi import extract_payload_body


def _doc_v2() -> str:
    return json.dumps(
        {
            "asyncapi": "2.6.0",
            "channels": {
                "plan.uploads": {
                    "subscribe": {
                        "message": {
                            "payload": {
                                "type": "object",
                                "properties": {
                                    "plan_version_id": {"type": "string"},
                                    "account_id": {"type": "string"},
                                },
                                "required": ["plan_version_id"],
                            }
                        }
                    }
                }
            },
        }
    )


def _doc_v3_yaml() -> str:
    return """
asyncapi: 3.0.0
channels:
  planUploads:
    address: plan.uploads
    messages:
      startUpload:
        payload:
          type: object
          properties:
            plan_version_id:
              type: string
            metadata:
              type: object
              properties:
                size:
                  type: number
          required:
            - plan_version_id
"""


class TestAsyncApiExtraction:
    def test_v2_channel_payload_extracted(self) -> None:
        body = extract_payload_body(_doc_v2(), channel="plan.uploads")
        assert body is not None
        assert body["type"] == "object"
        assert sorted(body["properties"].keys()) == ["account_id", "plan_version_id"]  # type: ignore[union-attr]
        assert body["required"] == ["plan_version_id"]

    def test_v3_channel_message_payload_extracted(self) -> None:
        body = extract_payload_body(_doc_v3_yaml(), channel="planUploads")
        assert body is not None
        props = body["properties"]
        assert "metadata" in props  # type: ignore[operator]
        assert props["metadata"]["properties"]["size"]["type"] == "number"  # type: ignore[index]

    def test_first_channel_used_when_unspecified(self) -> None:
        body = extract_payload_body(_doc_v2())
        assert body is not None
        assert "plan_version_id" in body["properties"]  # type: ignore[operator]

    def test_extracted_body_feeds_the_diff(self) -> None:
        # The whole point: an ingested AsyncAPI body is a normal body the
        # body-diff reasons over.
        from beadloom.graph.amqp_body import breaking_body_descriptors

        producer = extract_payload_body(_doc_v2(), channel="plan.uploads")
        consumer = {
            "type": "object",
            "properties": {
                "plan_version_id": {"type": "string"},
                "account_id": {"type": "string"},
                "extra": {"type": "string"},
            },
        }
        assert producer is not None
        assert breaking_body_descriptors(producer, consumer) == ["extra"]


class TestAsyncApiHonestDegradation:
    def test_missing_channel_yields_none(self) -> None:
        assert extract_payload_body(_doc_v2(), channel="nope") is None

    def test_no_payload_yields_none(self) -> None:
        doc = json.dumps({"asyncapi": "2.6.0", "channels": {"c": {"subscribe": {}}}})
        assert extract_payload_body(doc, channel="c") is None

    def test_malformed_doc_yields_none(self) -> None:
        assert extract_payload_body("not: [valid") is None
        assert extract_payload_body("") is None

    def test_no_channels_yields_none(self) -> None:
        assert extract_payload_body(json.dumps({"asyncapi": "2.6.0"})) is None
