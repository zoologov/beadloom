"""Tests for beadloom.infrastructure.atomic_io — atomic YAML writes.

BDL-060 S1 (G6): a crash mid-write must never corrupt the source-of-truth
graph YAML. ``write_yaml_atomic`` writes to a temp file in the SAME directory,
then ``os.replace``s it onto the target (atomic on POSIX). The serialization
options are passed through verbatim so output bytes are identical to the prior
direct ``yaml.dump`` -> ``write_text`` path (behavior-preserving).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
import yaml

from beadloom.infrastructure.atomic_io import write_yaml_atomic

if TYPE_CHECKING:
    from pathlib import Path

# Representative graph-YAML payload (nodes + edges, the shape graph/onboarding
# writers serialize).
_SAMPLE: dict[str, Any] = {
    "nodes": [
        {"ref_id": "alpha", "kind": "domain", "summary": "Alpha domain"},
        {"ref_id": "beta", "kind": "component", "summary": "Béta — unicode"},
    ],
    "edges": [{"src": "beta", "dst": "alpha", "kind": "part_of"}],
}


class TestByteParity:
    """write_yaml_atomic produces identical bytes to the prior direct dump."""

    def test_matches_direct_dump_default_options(self, tmp_path: Path) -> None:
        target = tmp_path / "services.yml"
        expected = yaml.dump(_SAMPLE, default_flow_style=False, allow_unicode=True)

        write_yaml_atomic(
            target, _SAMPLE, default_flow_style=False, allow_unicode=True
        )

        assert target.read_text(encoding="utf-8") == expected

    def test_matches_direct_dump_sort_keys_false(self, tmp_path: Path) -> None:
        target = tmp_path / "graph.yml"
        expected = yaml.dump(_SAMPLE, default_flow_style=False, sort_keys=False)

        write_yaml_atomic(
            target, _SAMPLE, default_flow_style=False, sort_keys=False
        )

        assert target.read_text(encoding="utf-8") == expected


class TestAtomicity:
    """A crash mid-write leaves the PRIOR file content intact."""

    def test_replace_is_the_commit_point(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        target = tmp_path / "services.yml"
        prior = "nodes:\n- ref_id: prior\n"
        target.write_text(prior, encoding="utf-8")

        from pathlib import Path

        def _boom(*_args: object, **_kwargs: object) -> None:
            raise OSError("simulated crash at commit")

        # Path.replace is the single commit point — fail it.
        monkeypatch.setattr(Path, "replace", _boom)

        with pytest.raises(OSError, match="simulated crash"):
            write_yaml_atomic(
                target, _SAMPLE, default_flow_style=False, allow_unicode=True
            )

        # Prior content is intact — the target was never partially written.
        assert target.read_text(encoding="utf-8") == prior

    def test_no_temp_file_leaks_after_success(self, tmp_path: Path) -> None:
        target = tmp_path / "services.yml"

        write_yaml_atomic(
            target, _SAMPLE, default_flow_style=False, allow_unicode=True
        )

        # Only the target remains — no temp siblings left behind.
        siblings = [p.name for p in tmp_path.iterdir()]
        assert siblings == ["services.yml"]

    def test_no_temp_file_leaks_after_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        target = tmp_path / "services.yml"
        target.write_text("nodes:\n- ref_id: prior\n", encoding="utf-8")

        from pathlib import Path

        def _boom(*_args: object, **_kwargs: object) -> None:
            raise OSError("simulated crash at commit")

        # Path.replace is the single commit point — fail it.
        monkeypatch.setattr(Path, "replace", _boom)

        with pytest.raises(OSError, match="simulated crash"):
            write_yaml_atomic(
                target, _SAMPLE, default_flow_style=False, allow_unicode=True
            )

        # The temp file is cleaned up even when the commit fails.
        siblings = sorted(p.name for p in tmp_path.iterdir())
        assert siblings == ["services.yml"]
