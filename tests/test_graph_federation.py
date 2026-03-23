"""Tests for beadloom.graph.federation — cross-repo node identity (@repo:ref_id).

Covers the ``FederatedRef`` value type and the ``parse_ref`` parser:
- plain ref      -> local (repo=None)
- ``@repo:id``   -> foreign (repo set)
- malformed @... -> FederationRefError (never silently dropped)
"""

from __future__ import annotations

import pytest

from beadloom.graph.federation import (
    FederatedRef,
    FederationRefError,
    parse_ref,
)


class TestFederatedRef:
    def test_is_frozen(self) -> None:
        ref = FederatedRef(repo=None, ref_id="routing")
        with pytest.raises(Exception):  # noqa: B017 - dataclass FrozenInstanceError
            ref.ref_id = "other"  # type: ignore[misc]

    def test_local_is_not_foreign(self) -> None:
        ref = FederatedRef(repo=None, ref_id="routing")
        assert ref.is_foreign is False

    def test_foreign_is_foreign(self) -> None:
        ref = FederatedRef(repo="integration-service", ref_id="plans")
        assert ref.is_foreign is True

    def test_qualified_local(self) -> None:
        ref = FederatedRef(repo=None, ref_id="routing")
        assert ref.qualified == "routing"

    def test_qualified_foreign(self) -> None:
        ref = FederatedRef(repo="integration-service", ref_id="plans")
        assert ref.qualified == "@integration-service:plans"


class TestParseRefLocal:
    def test_plain_ref_is_local(self) -> None:
        ref = parse_ref("routing")
        assert ref == FederatedRef(repo=None, ref_id="routing")
        assert ref.is_foreign is False

    def test_plain_ref_with_dashes_and_numbers(self) -> None:
        ref = parse_ref("PROJ-123")
        assert ref == FederatedRef(repo=None, ref_id="PROJ-123")

    def test_plain_ref_with_internal_colon_stays_local(self) -> None:
        """A colon without a leading ``@`` is just part of a local ref_id."""
        ref = parse_ref("a:b")
        assert ref == FederatedRef(repo=None, ref_id="a:b")
        assert ref.is_foreign is False


class TestParseRefForeign:
    def test_foreign_ref(self) -> None:
        ref = parse_ref("@integration-service:plans")
        assert ref == FederatedRef(repo="integration-service", ref_id="plans")
        assert ref.is_foreign is True

    def test_foreign_ref_id_may_contain_dashes(self) -> None:
        ref = parse_ref("@core-monolith:PROJ-7")
        assert ref.repo == "core-monolith"
        assert ref.ref_id == "PROJ-7"

    def test_foreign_ref_id_keeps_extra_colons(self) -> None:
        """Only the first colon separates repo from ref_id; ref_id may hold more."""
        ref = parse_ref("@repo:ns:thing")
        assert ref.repo == "repo"
        assert ref.ref_id == "ns:thing"


class TestParseRefMalformed:
    @pytest.mark.parametrize(
        "raw",
        [
            "@:x",       # empty repo
            "@repo:",    # empty ref_id
            "@repo",     # no colon at all
            "@",         # just the marker
            "@:",        # both empty
        ],
    )
    def test_malformed_raises(self, raw: str) -> None:
        with pytest.raises(FederationRefError):
            parse_ref(raw)

    def test_empty_string_raises(self) -> None:
        with pytest.raises(FederationRefError):
            parse_ref("")
