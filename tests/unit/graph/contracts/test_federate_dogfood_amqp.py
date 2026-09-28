"""Regression: real core-monolith <-> integration-service AMQP both-sides.

Captures the BDL-037 BEAD-05 dogfood scenario as a durable fixture so the
real RabbitMQ contract stays confirmed both-sides if reconciliation changes.

The four message types and their directions are verified facts from the real
repos (read-only): core-monolith `message_queue/payload.py` +
`integration_inbound.py`, integration-service `outbox_payloads.py` +
`openspec/specs/plan-version-upload-*`. core produces the upload/folder
commands and consumes the ``*_completed`` reverse; integration-service mirrors.

These are export-shaped dicts (post-``beadloom export``): contract edges use the
allowed ``uses`` kind and carry the producer/consumer role in
``contract.direction`` (see BDL-UX-Issues #101) with one channel node per
message_type (see #102). The hub reconciler keys on ``contract.direction`` +
``message_type``, so this asserts the same shape a real export produces.
"""

from __future__ import annotations

from beadloom.graph.federation import aggregate_exports

# (message_type, core direction, integration direction)
_CONTRACT = [
    ("start_plan_version_upload", "produces", "consumes"),
    ("ensure_plans_folder_path", "produces", "consumes"),
    ("plan_version_upload_completed", "consumes", "produces"),
    ("ensure_plans_folder_path_completed", "consumes", "produces"),
]


def _channel(message_type: str) -> str:
    return "q-" + message_type.replace("_", "-")


def _contract_edge(repo_service: str, message_type: str, direction: str) -> dict[str, object]:
    """An export-shaped contract edge: kind=uses, role in contract.direction."""
    return {
        "src": repo_service,
        "dst": _channel(message_type),
        "kind": "uses",
        "lifecycle": "active",
        "contract": {
            "protocol": "amqp",
            "message_type": message_type,
            "direction": direction,
        },
    }


def _satellite(repo: str, role_index: int) -> dict[str, object]:
    """Build one satellite export (role_index 0 = core direction, 1 = integration)."""
    edges = [_contract_edge(repo, mt, c[role_index]) for mt, *c in _CONTRACT]
    def _n(ref_id: str, kind: str, summary: str) -> dict[str, object]:
        return {
            "ref_id": ref_id,
            "kind": kind,
            "summary": summary,
            "lifecycle": "active",
            "source": None,
        }

    nodes = [_n(repo, "service", repo)]
    nodes += [_n(_channel(mt), "feature", mt) for mt, *_ in _CONTRACT]
    return {
        "schema_version": 1,
        "repo": repo,
        "commit_sha": "deadbeef",
        "exported_at": "2026-06-01T00:00:00+00:00",
        "generator": "beadloom dogfood",
        "nodes": nodes,
        "edges": edges,
    }


def _federate_real_contract() -> object:
    return aggregate_exports(
        [_satellite("core-monolith", 0), _satellite("integration-service", 1)],
        now="2026-06-01T00:00:00+00:00",
    )


class TestRealAmqpContractBothSides:
    def test_all_four_message_types_confirmed_both_sides(self) -> None:
        fed = _federate_real_contract()
        confirmed = {c["message_type"] for c in fed.contracts if c["confirmed"]}
        assert confirmed == {mt for mt, *_ in _CONTRACT}

    def test_each_contract_has_both_directions(self) -> None:
        fed = _federate_real_contract()
        for contract in fed.contracts:
            assert sorted(contract["directions"]) == ["consumes", "produces"], contract

    def test_no_undeclared_or_drift(self) -> None:
        fed = _federate_real_contract()
        verdicts = {str(e["verdict"]) for e in fed.edges}
        assert verdicts == {"ok"}, verdicts

    def test_both_repos_present_in_each_contract(self) -> None:
        fed = _federate_real_contract()
        for contract in fed.contracts:
            assert sorted(contract["repos"]) == ["core-monolith", "integration-service"]
