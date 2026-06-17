# beadloom:domain=graph
# beadloom:component=asyncapi
"""Source-only AsyncAPI payload-schema ingestion adapter (S3, G1b).

Teams that already describe their AMQP messages with an AsyncAPI document
shouldn't be left out of the strict body diff. This adapter is a *source* only:
it extracts the message **payload JSON-Schema** out of an AsyncAPI doc into the
SAME internal minimal-JSON-Schema body the rest of S3 reasons over
(:mod:`beadloom.graph.amqp_body`). It does NOT model AsyncAPI itself — operations,
bindings, servers and the like are out of scope; the internal model stays the
minimal honest body.

Both AsyncAPI 2.x and 3.x layouts are handled:

- **2.x** — ``channels.<channel>.{publish,subscribe}.message.payload``;
- **3.x** — ``channels.<channel>.messages.<message>.payload`` (with ``$ref`` into
  ``components.messages`` resolved one hop).

The single responsibility: *given an AsyncAPI document and an optional channel,
return the message payload as our body model* — or ``None`` when there is no
extractable payload. AsyncAPI docs are YAML or JSON, both read by the core
``yaml.safe_load`` (JSON is a YAML subset), so this needs NO optional extra; an
unparseable/empty/payload-less doc degrades honestly to ``None`` (the caller then
keeps name-level AMQP — never a fabricated body — DATA-STRICTNESS).
"""

from __future__ import annotations

from collections.abc import Mapping

import yaml

_REF = "$ref"
_PAYLOAD = "payload"
_MESSAGE = "message"
_MESSAGES = "messages"
_CHANNELS = "channels"
_COMPONENTS = "components"
# AsyncAPI 2.x operation objects that carry a message.
_OPERATIONS = ("subscribe", "publish")


def extract_payload_body(
    document: str, channel: str | None = None
) -> dict[str, object] | None:
    """Extract a message payload JSON-Schema from an AsyncAPI doc, or ``None``.

    *document* is the raw AsyncAPI text (YAML or JSON). *channel* selects which
    channel's message to extract; when ``None`` the first channel (in declaration
    order) is used. Returns the payload as a plain JSON-Schema dict (the internal
    body shape) or ``None`` when the doc is unparseable, has no channels, or the
    selected channel carries no message payload — honest degradation, never a
    fabricated body.
    """
    doc = _load(document)
    if doc is None:
        return None
    channels = doc.get(_CHANNELS)
    if not isinstance(channels, Mapping) or not channels:
        return None
    selected = _select_channel(channels, channel)
    if selected is None:
        return None
    payload = _payload_of_channel(selected, doc)
    if isinstance(payload, Mapping):
        return dict(payload)
    return None


def _load(document: str) -> Mapping[str, object] | None:
    """Parse the AsyncAPI text (YAML/JSON); ``None`` if unparseable or not a map."""
    if not document.strip():
        return None
    try:
        parsed = yaml.safe_load(document)
    except yaml.YAMLError:
        return None
    return parsed if isinstance(parsed, Mapping) else None


def _select_channel(
    channels: Mapping[str, object], channel: str | None
) -> Mapping[str, object] | None:
    """Pick the requested channel (or the first declared) as a mapping."""
    if channel is not None:
        value = channels.get(channel)
        return value if isinstance(value, Mapping) else None
    for value in channels.values():
        if isinstance(value, Mapping):
            return value
    return None


def _payload_of_channel(
    channel: Mapping[str, object], doc: Mapping[str, object]
) -> object:
    """Find the message payload on a channel (2.x operations or 3.x messages)."""
    for operation_name in _OPERATIONS:
        operation = channel.get(operation_name)
        if isinstance(operation, Mapping):
            payload = _payload_of_message(operation.get(_MESSAGE), doc)
            if payload is not None:
                return payload
    messages = channel.get(_MESSAGES)
    if isinstance(messages, Mapping):
        for message in messages.values():
            payload = _payload_of_message(message, doc)
            if payload is not None:
                return payload
    return None


def _payload_of_message(
    message: object, doc: Mapping[str, object]
) -> object | None:
    """Resolve a message (inline or one-hop ``$ref``) to its payload."""
    resolved = _resolve_ref(message, doc) if isinstance(message, Mapping) else None
    if not isinstance(resolved, Mapping):
        return None
    payload = resolved.get(_PAYLOAD)
    return payload if isinstance(payload, Mapping) else None


def _resolve_ref(
    message: Mapping[str, object], doc: Mapping[str, object]
) -> Mapping[str, object] | None:
    """Resolve a one-hop local ``$ref`` into ``components.messages``; else inline.

    Only a local ``#/components/messages/<name>`` reference is followed (the
    common AsyncAPI shape). A foreign/remote ``$ref`` is not fetched — honest
    degradation to ``None`` rather than a network read or a fabricated payload.
    """
    ref = message.get(_REF)
    if not isinstance(ref, str):
        return message
    parts = ref.lstrip("#/").split("/")
    if len(parts) == 3 and parts[0] == _COMPONENTS and parts[1] == _MESSAGES:
        components = doc.get(_COMPONENTS)
        messages = components.get(_MESSAGES) if isinstance(components, Mapping) else None
        target = messages.get(parts[2]) if isinstance(messages, Mapping) else None
        return target if isinstance(target, Mapping) else None
    return None
