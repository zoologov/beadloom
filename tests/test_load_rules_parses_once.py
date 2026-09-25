"""``load_rules`` parses a rules file once per content, and never serves a stale one.

Written for BDL-073 B4 (bead ``beadloom-m19h``). One ``beadloom init`` parsed
``rules.yml`` twice — the re-index ingested it into the index and the lint verdict
read the same file from disk again — and one suite run made 1581 parses, 783 of
them of a file whose content had not changed. ``load_rules`` now remembers what it
parsed, per path, and answers from memory while the file still holds the same text.

The key is the content, not the path and not the file's timestamp:

* a path-only key serves the old rules after an edit — the TUI's lint panel lives
  in one long process while its user edits ``rules.yml``;
* a ``(path, st_mtime_ns, st_size)`` key serves the old rules after an edit that
  keeps the size and lands inside one timestamp tick, which a coarse-clock
  filesystem makes a window of milliseconds rather than nanoseconds. The last
  class below writes that collision on purpose, by resetting the timestamp.
"""

from __future__ import annotations

import os
import sqlite3
from typing import TYPE_CHECKING

import pytest
import yaml
from click.testing import CliRunner

from beadloom.graph.rules import loader
from beadloom.infrastructure.db import create_schema
from beadloom.services.cli import main
from beadloom.tui.data_providers import LintDataProvider

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

#: The name of the autouse fixture in ``tests/conftest.py`` that forgets every parse
#: before each test. Named here so a rename breaks this file rather than the property.
FORGETTING_FIXTURE = "_load_rules_forgets_between_tests"


class _CountingYaml:
    """Stands in for the ``yaml`` module inside the loader, counting its parses."""

    def __init__(self) -> None:
        self.parses = 0

    def safe_load(self, text: str) -> object:
        self.parses += 1
        return yaml.safe_load(text)


@pytest.fixture
def counted(monkeypatch: pytest.MonkeyPatch) -> _CountingYaml:
    """Count every parse ``load_rules`` makes, and nothing any other module makes."""
    counter = _CountingYaml()
    monkeypatch.setattr(loader, "yaml", counter)
    return counter


def _rule_named(name: str) -> str:
    """A one-rule file whose byte length does not depend on *name*'s letters."""
    return (
        "version: 1\n"
        "rules:\n"
        f"  - name: {name}\n"
        "    description: every domain belongs to a service\n"
        "    require:\n"
        "      for: { kind: domain }\n"
        "      has_edge_to: { kind: service }\n"
        "      edge_kind: part_of\n"
    )


def _small_project(root: Path) -> Path:
    """Two packages, one importing the other: enough for ``init`` to write rules."""
    for package, body in (
        ("billing", "def charge() -> int:\n    return 1\n"),
        ("orders", "from app.billing import charge\n"),
    ):
        (root / "src" / "app" / package).mkdir(parents=True)
        (root / "src" / "app" / package / "__init__.py").write_text(body, encoding="utf-8")
    return root


class TestOneInitParsesItsRulesOnce:
    """The re-index and the lint verdict of one ``init`` share one parse."""

    @pytest.mark.parametrize("form", [["init", "--yes"], ["init", "--bootstrap"]])
    def test_one_init_parses_rules_yml_once(
        self, tmp_path: Path, counted: _CountingYaml, form: list[str]
    ) -> None:
        project = _small_project(tmp_path / "shop")

        result = CliRunner().invoke(main, [*form, "--project", str(project)])

        assert result.exit_code == 0, result.output
        assert (project / ".beadloom" / "_graph" / "rules.yml").is_file()
        assert counted.parses == 1


class TestTheMemoAnswersForTheContent:
    """What is served from memory is what a fresh parse would return."""

    def test_an_unchanged_file_is_parsed_once(
        self, tmp_path: Path, counted: _CountingYaml
    ) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(_rule_named("rule-a"), encoding="utf-8")

        first = loader.load_rules(rules_path)
        second = loader.load_rules(rules_path)

        assert counted.parses == 1
        assert second == first
        assert [rule.name for rule in second] == ["rule-a"]

    def test_an_edited_file_is_parsed_again(self, tmp_path: Path, counted: _CountingYaml) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(_rule_named("rule-a"), encoding="utf-8")
        loader.load_rules(rules_path)

        rules_path.write_text(_rule_named("rule-bb"), encoding="utf-8")

        assert [rule.name for rule in loader.load_rules(rules_path)] == ["rule-bb"]
        assert counted.parses == 2

    def test_an_edit_inside_one_timestamp_tick_is_parsed_again(
        self, tmp_path: Path, counted: _CountingYaml
    ) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(_rule_named("rule-a"), encoding="utf-8")
        before = rules_path.stat()
        loader.load_rules(rules_path)

        rules_path.write_text(_rule_named("rule-b"), encoding="utf-8")
        os.utime(rules_path, ns=(before.st_atime_ns, before.st_mtime_ns))
        after = rules_path.stat()
        assert (after.st_mtime_ns, after.st_size) == (before.st_mtime_ns, before.st_size)

        assert [rule.name for rule in loader.load_rules(rules_path)] == ["rule-b"]
        assert counted.parses == 2

    def test_a_file_that_does_not_parse_is_not_remembered(
        self, tmp_path: Path, counted: _CountingYaml
    ) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text("rules: []\n", encoding="utf-8")

        for _ in range(2):
            with pytest.raises(ValueError, match="missing required 'version'"):
                loader.load_rules(rules_path)

        assert counted.parses == 2

    def test_two_paths_are_remembered_side_by_side(
        self, tmp_path: Path, counted: _CountingYaml
    ) -> None:
        first_path = tmp_path / "first.yml"
        second_path = tmp_path / "second.yml"
        first_path.write_text(_rule_named("rule-a"), encoding="utf-8")
        second_path.write_text(_rule_named("rule-b"), encoding="utf-8")

        for _ in range(2):
            assert [rule.name for rule in loader.load_rules(first_path)] == ["rule-a"]
            assert [rule.name for rule in loader.load_rules(second_path)] == ["rule-b"]

        assert counted.parses == 2


class TestTheLintPanelSeesAnEditedRulesFile:
    """The TUI refreshes in one long process; an edit made while it is open shows."""

    @pytest.fixture
    def panel(self, tmp_path: Path) -> Iterator[LintDataProvider]:
        """A lint panel over an index holding one domain that belongs to nothing."""
        db_path = tmp_path / ".beadloom" / "beadloom.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path))
        create_schema(conn)
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("payments", "domain", "Payments"),
        )
        conn.commit()
        yield LintDataProvider(conn=conn, project_root=tmp_path)
        conn.close()

    @staticmethod
    def _rule_names(panel: LintDataProvider) -> set[str | None]:
        panel.refresh()
        return {row["rule_name"] for row in panel.get_violations()}

    def test_a_rule_renamed_between_two_refreshes_is_seen(
        self, tmp_path: Path, panel: LintDataProvider
    ) -> None:
        rules_path = tmp_path / ".beadloom" / "_graph" / "rules.yml"
        rules_path.parent.mkdir(parents=True)
        rules_path.write_text(_rule_named("rule-a"), encoding="utf-8")
        assert self._rule_names(panel) == {"rule-a"}

        rules_path.write_text(_rule_named("rule-bb"), encoding="utf-8")

        assert self._rule_names(panel) == {"rule-bb"}

    def test_a_same_size_edit_inside_one_timestamp_tick_is_seen(
        self, tmp_path: Path, panel: LintDataProvider
    ) -> None:
        rules_path = tmp_path / ".beadloom" / "_graph" / "rules.yml"
        rules_path.parent.mkdir(parents=True)
        rules_path.write_text(_rule_named("rule-a"), encoding="utf-8")
        before = rules_path.stat()
        assert self._rule_names(panel) == {"rule-a"}

        rules_path.write_text(_rule_named("rule-b"), encoding="utf-8")
        os.utime(rules_path, ns=(before.st_atime_ns, before.st_mtime_ns))

        assert self._rule_names(panel) == {"rule-b"}


class TestNoTestSeesAnotherTestsParse:
    """The memo is forgotten before every test, so no test is served another's rules.

    It matters twice. A test would otherwise be answered from a parse some earlier
    test made of a path it also reads — this repository's own ``rules.yml`` is one.
    And mutmut forks each mutant's run from a parent that has already run the clean
    suite in-process: a memo inherited across that fork answers the child without
    executing the mutated parse, and the mutant survives a test that would kill it.
    """

    def test_the_forgetting_fixture_applies_to_every_test(
        self, request: pytest.FixtureRequest
    ) -> None:
        assert FORGETTING_FIXTURE in request.fixturenames

    def test_every_test_starts_with_nothing_remembered(self) -> None:
        assert loader._PARSED == {}
