"""AsyncAPI ingestion fidelity + honest degradation (S3, G1b — .10).

Strengthens :mod:`tests.test_asyncapi_ingest`: proves the 2.x and 3.x payload
extraction preserves nested objects, arrays and ``required`` faithfully, follows
a 3.x one-hop ``$ref`` into ``components.messages``, honours the ``publish``
operation as well as ``subscribe``, and degrades honestly (``None`` — no body,
no crash, no fabricated field) on every malformed/absent shape: a foreign/remote
``$ref``, a non-mapping channel/payload, a list document, a payload-less message.
"""

from __future__ import annotations

import json

from beadloom.graph.amqp_body import breaking_body_descriptors
from beadloom.graph.asyncapi import extract_payload_body


def _v2_publish() -> str:
    return json.dumps(
        {
            "asyncapi": "2.6.0",
            "channels": {
                "plan.uploads": {
                    "publish": {
                        "message": {
                            "payload": {
                                "type": "object",
                                "properties": {"plan_version_id": {"type": "string"}},
                                "required": ["plan_version_id"],
                            }
                        }
                    }
                }
            },
        }
    )


def _v3_ref() -> str:
    """A 3.x doc whose channel message is a $ref into components.messages."""
    return json.dumps(
        {
            "asyncapi": "3.0.0",
            "channels": {
                "planUploads": {
                    "address": "plan.uploads",
                    "messages": {"startUpload": {"$ref": "#/components/messages/StartUpload"}},
                }
            },
            "components": {
                "messages": {
                    "StartUpload": {
                        "payload": {
                            "type": "object",
                            "properties": {
                                "plan_version_id": {"type": "string"},
                                "lines": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {"sku": {"type": "string"}},
                                        "required": ["sku"],
                                    },
                                },
                            },
                            "required": ["plan_version_id"],
                        }
                    }
                }
            },
        }
    )


class TestExtractionFidelity:
    def test_v3_ref_resolved_one_hop(self) -> None:
        body = extract_payload_body(_v3_ref(), channel="planUploads")
        assert body is not None
        assert sorted(body["properties"].keys()) == ["lines", "plan_version_id"]  # type: ignore[union-attr]

    def test_v3_ref_preserves_nested_array_of_objects(self) -> None:
        body = extract_payload_body(_v3_ref(), channel="planUploads")
        assert body is not None
        lines = body["properties"]["lines"]  # type: ignore[index]
        assert lines["type"] == "array"  # type: ignore[index]
        item = lines["items"]  # type: ignore[index]
        assert item["properties"]["sku"]["type"] == "string"  # type: ignore[index]
        assert item["required"] == ["sku"]  # type: ignore[index]

    def test_v2_publish_operation_extracted(self) -> None:
        body = extract_payload_body(_v2_publish(), channel="plan.uploads")
        assert body is not None
        assert body["required"] == ["plan_version_id"]

    def test_required_preserved_feeds_a_required_break(self) -> None:
        # Fidelity proof: an ingested AsyncAPI required list drives the body-diff.
        producer = _v3_ref_no_required()
        consumer = extract_payload_body(_v3_ref(), channel="planUploads")
        assert consumer is not None
        producer_body = extract_payload_body(producer, channel="planUploads")
        assert producer_body is not None
        # Producer dropped `plan_version_id` from required -> required-now-optional.
        assert breaking_body_descriptors(producer_body, consumer) == ["plan_version_id"]


def _v3_ref_no_required() -> str:
    doc = json.loads(_v3_ref())
    doc["components"]["messages"]["StartUpload"]["payload"]["required"] = []
    doc["components"]["messages"]["StartUpload"]["payload"]["properties"]["lines"][
        "items"
    ]["required"] = ["sku"]
    return json.dumps(doc)


class TestHonestDegradation:
    def test_foreign_remote_ref_yields_none(self) -> None:
        # A remote/foreign $ref is never fetched -> no fabricated body, just None.
        doc = json.dumps(
            {
                "asyncapi": "3.0.0",
                "channels": {
                    "c": {"messages": {"m": {"$ref": "https://example.com/msg.json"}}}
                },
            }
        )
        assert extract_payload_body(doc, channel="c") is None

    def test_dangling_local_ref_yields_none(self) -> None:
        doc = json.dumps(
            {
                "asyncapi": "3.0.0",
                "channels": {
                    "c": {"messages": {"m": {"$ref": "#/components/messages/Missing"}}}
                },
                "components": {"messages": {}},
            }
        )
        assert extract_payload_body(doc, channel="c") is None

    def test_non_mapping_channel_yields_none(self) -> None:
        doc = json.dumps({"asyncapi": "2.6.0", "channels": {"c": "oops"}})
        assert extract_payload_body(doc, channel="c") is None

    def test_non_mapping_payload_yields_none(self) -> None:
        doc = json.dumps(
            {
                "asyncapi": "2.6.0",
                "channels": {"c": {"subscribe": {"message": {"payload": "scalar"}}}},
            }
        )
        assert extract_payload_body(doc, channel="c") is None

    def test_list_document_yields_none(self) -> None:
        assert extract_payload_body(json.dumps([1, 2, 3])) is None

    def test_scalar_document_yields_none(self) -> None:
        assert extract_payload_body(json.dumps("just a string")) is None

    def test_whitespace_only_document_yields_none(self) -> None:
        assert extract_payload_body("   \n  \t ") is None

    def test_empty_channels_mapping_yields_none(self) -> None:
        assert extract_payload_body(json.dumps({"channels": {}})) is None

    def test_extraction_never_fabricates_absent_fields(self) -> None:
        # A payload with one property must ingest EXACTLY that property — never an
        # invented one (DATA-STRICTNESS).
        doc = json.dumps(
            {
                "asyncapi": "2.6.0",
                "channels": {
                    "c": {
                        "subscribe": {
                            "message": {
                                "payload": {
                                    "type": "object",
                                    "properties": {"only": {"type": "string"}},
                                }
                            }
                        }
                    }
                },
            }
        )
        body = extract_payload_body(doc, channel="c")
        assert body is not None
        assert list(body["properties"].keys()) == ["only"]  # type: ignore[union-attr]
