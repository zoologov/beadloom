"""Tests for the orphaned-adapter derivation (BDL-068 S6, `beadloom-ec1a`).

Every reader of role adapters takes its population from ``config.tools``, so
dropping a tool from ``flow.yml`` removes that tool's files from the check
instead of reporting them. Measured on 2026-09-09 with a control: the same edit
is an ``error`` on ``.claude/agents/dev.md`` and exit 0 on
``.cursor/agents/dev.md`` in a project whose flow declares ``claude`` only.

These tests hold the DERIVATION -- its population, its provenance gate and its
divergence flag. The findings the adopter sees are held by
``tests/acceptance/features/orphaned_adapters.feature``.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from beadloom.onboarding.flow_config import FlowConfig, load_flow_config
from beadloom.onboarding.flow_manifest import FLOW_MANIFEST_RELPATH, digest
from beadloom.onboarding.role_adapters import (
    TOOL_AGENT_DIRS,
    generate_adapters,
    orphaned_adapters,
)
from beadloom.onboarding.role_composer import ROLE_NAMES

if TYPE_CHECKING:
    from pathlib import Path


def _config(*tools: str) -> FlowConfig:
    return FlowConfig(tools=tools, architecture="ddd", stack=("python",), quality=())


@pytest.fixture()
def both_tools(tmp_path: Path) -> Path:
    """A project whose adapters were written for `claude` and `cursor`."""
    project = tmp_path / "acme"
    project.mkdir()
    generate_adapters(_config("claude", "cursor"), project)
    return project


def _manifest(project: Path) -> dict[str, str]:
    payload = json.loads((project / FLOW_MANIFEST_RELPATH).read_text(encoding="utf-8"))
    return dict(payload["written"])


def _record(project: Path, relpath: str, body: str) -> None:
    path = project / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    manifest_path = project / FLOW_MANIFEST_RELPATH
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["written"][relpath] = digest(body)
    manifest_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


class TestPopulation:
    """Which files the derivation claims, and which it refuses to."""

    def test_a_dropped_tools_adapters_are_orphans(self, both_tools: Path) -> None:
        found = orphaned_adapters(both_tools, _config("claude"))
        assert {o.file for o in found} == {f".cursor/agents/{role}.md" for role in ROLE_NAMES}

    def test_a_declared_tools_adapters_are_not(self, both_tools: Path) -> None:
        assert orphaned_adapters(both_tools, _config("claude", "cursor")) == ()

    def test_every_orphan_names_the_tool_that_wrote_it(self, both_tools: Path) -> None:
        found = orphaned_adapters(both_tools, _config("claude"))
        assert {o.tool for o in found} == {"cursor"}

    def test_a_file_the_manifest_does_not_record_is_not_claimed(self, tmp_path: Path) -> None:
        project = tmp_path / "acme"
        project.mkdir()
        generate_adapters(_config("claude"), project)
        hand_authored = project / ".cursor" / "agents" / "dev.md"
        hand_authored.parent.mkdir(parents=True)
        hand_authored.write_text("# our own Cursor role\n", encoding="utf-8")

        assert orphaned_adapters(project, _config("claude")) == ()

    def test_a_recorded_adapter_the_adopter_deleted_is_not_reported(
        self, both_tools: Path
    ) -> None:
        for path in (both_tools / ".cursor" / "agents").iterdir():
            path.unlink()

        assert orphaned_adapters(both_tools, _config("claude")) == ()

    def test_a_role_this_release_no_longer_composes_is_still_an_orphan(
        self, both_tools: Path
    ) -> None:
        _record(both_tools, ".cursor/agents/legacy.md", "# an older role\n")

        found = orphaned_adapters(both_tools, _config("claude"))
        assert ".cursor/agents/legacy.md" in {o.file for o in found}

    def test_the_cursor_orchestrator_pointer_is_not_an_orphaned_adapter(
        self, both_tools: Path
    ) -> None:
        found = orphaned_adapters(both_tools, _config("claude"))
        assert ".cursor/rules/beadloom-flow.md" in _manifest(both_tools)
        assert ".cursor/rules/beadloom-flow.md" not in {o.file for o in found}

    def test_a_file_outside_every_tool_directory_is_not_an_orphan(self, both_tools: Path) -> None:
        _record(both_tools, "docs/notes.md", "# notes\n")

        found = orphaned_adapters(both_tools, _config("claude"))
        assert "docs/notes.md" not in {o.file for o in found}

    def test_the_population_is_derived_from_the_supported_tool_set(self) -> None:
        # Not a second list: the derivation sweeps every directory
        # `generate_adapters` can write into, minus the ones this flow declares.
        assert set(TOOL_AGENT_DIRS) >= {"claude", "cursor"}


class TestDivergence:
    """Whether the body still matches what Beadloom recorded writing."""

    def test_an_untouched_orphan_has_not_diverged(self, both_tools: Path) -> None:
        found = orphaned_adapters(both_tools, _config("claude"))
        assert found
        assert not any(orphan.diverged for orphan in found)

    def test_an_edited_orphan_has_diverged(self, both_tools: Path) -> None:
        path = both_tools / ".cursor" / "agents" / "dev.md"
        path.write_text(path.read_text(encoding="utf-8") + "\n## OUR RULE\n", encoding="utf-8")

        found = orphaned_adapters(both_tools, _config("claude"))
        diverged = {o.file for o in found if o.diverged}
        assert diverged == {".cursor/agents/dev.md"}

    def test_an_unreadable_orphan_is_reported_rather_than_skipped(self, both_tools: Path) -> None:
        # Unreadable is not "unchanged". A body we cannot read cannot be
        # compared, and dropping it would answer clean about a file nothing has
        # looked at -- the class BDL-UX #174 named.
        path = both_tools / ".cursor" / "agents" / "dev.md"
        path.write_bytes(b"\xff\xfe not utf-8")

        found = orphaned_adapters(both_tools, _config("claude"))
        assert ".cursor/agents/dev.md" in {o.file for o in found}


class TestOrdering:
    """A report read by a human is deterministic or it is diff noise."""

    def test_orphans_are_sorted_by_path(self, both_tools: Path) -> None:
        found = orphaned_adapters(both_tools, _config("claude"))
        assert [o.file for o in found] == sorted(o.file for o in found)


class TestAgainstTheRealScaffold:
    """The derivation over the config the shipped loader produces."""

    def test_it_reads_a_flow_yml_written_by_the_command(self, tmp_path: Path) -> None:
        from beadloom.onboarding.flow_config import (
            FLOW_CONFIG_RELPATH,
            persist_flow_config,
        )

        project = tmp_path / "acme"
        project.mkdir()
        persist_flow_config(project, _config("claude", "cursor"))
        generate_adapters(load_flow_config(project), project)
        # The adopter's own edit, in their own file: `persist_flow_config`
        # never rewrites an existing flow.yml, which is why this is not one.
        config_path = project / FLOW_CONFIG_RELPATH
        config_path.write_text(
            config_path.read_text(encoding="utf-8").replace("- cursor\n", ""),
            encoding="utf-8",
        )

        found = orphaned_adapters(project, load_flow_config(project))
        assert {o.file for o in found} == {f".cursor/agents/{role}.md" for role in ROLE_NAMES}
