"""Targeted false-positive suppression for ``docs audit`` (BDL-057.6).

The detector flags some mentions that are not stale prose — e.g. a "12 supported
languages" claim (parser breadth) that the detector compares against the
in-repo ``language_count`` ground truth, or an HTTP status "404" matched as a
``cli_command_count``. ``docs_audit.ignore`` in ``.beadloom/config.yml`` lets a
maintainer suppress EXACTLY those ``{path, fact, value}`` triples without
rewording correct prose and without masking genuine stale facts elsewhere.
"""

from __future__ import annotations

from pathlib import Path

from beadloom.doc_sync.audit import (
    Fact,
    IgnoreRule,
    _load_ignore_from_config,
    compare_facts,
)
from beadloom.doc_sync.scanner import Mention


def _mention(path: str, fact: str, value: object, line: int = 1) -> Mention:
    return Mention(
        fact_name=fact,
        value=value,  # type: ignore[arg-type]
        file=Path(path),
        line=line,
        context=f"{value}",
    )


class TestIgnoreInCompareFacts:
    def test_ignore_drops_matching_false_positive(self) -> None:
        facts = {"language_count": Fact(name="language_count", value=1, source="graph DB")}
        mentions = [_mention("docs/domains/context-oracle/README.md", "language_count", 12)]
        # Without ignore: stale.
        assert compare_facts(facts, mentions).findings[0].status == "stale"
        # With a matching ignore rule: suppressed (no finding at all).
        rule = IgnoreRule(
            path="docs/domains/context-oracle/README.md",
            fact="language_count",
            value="12",
        )
        result = compare_facts(facts, mentions, ignore=[rule])
        assert result.findings == []
        assert result.unmatched == []

    def test_ignore_is_targeted_to_value(self) -> None:
        """An ignore on value '404' must NOT suppress a genuine stale '14'."""
        facts = {
            "cli_command_count": Fact(name="cli_command_count", value=38, source="graph DB")
        }
        mentions = [
            _mention("docs/guides/vitepress-site.md", "cli_command_count", 404),
            _mention("README.ru.md", "cli_command_count", 14),
        ]
        rule = IgnoreRule(
            path="docs/guides/vitepress-site.md", fact="cli_command_count", value="404"
        )
        result = compare_facts(facts, mentions, ignore=[rule])
        # The 404 FP is gone; the genuine 14 stays flagged.
        assert len(result.findings) == 1
        assert result.findings[0].mention.value == 14
        assert result.findings[0].status == "stale"

    def test_ignore_is_targeted_to_path(self) -> None:
        """An ignore scoped to one file must not affect the same fact elsewhere."""
        facts = {
            "language_count": Fact(name="language_count", value=1, source="graph DB")
        }
        mentions = [
            _mention("docs/domains/context-oracle/README.md", "language_count", 12),
            _mention("docs/other.md", "language_count", 12),
        ]
        rule = IgnoreRule(
            path="docs/domains/context-oracle/README.md",
            fact="language_count",
            value="12",
        )
        result = compare_facts(facts, mentions, ignore=[rule])
        stale = [f for f in result.findings if f.status == "stale"]
        assert len(stale) == 1
        assert str(stale[0].mention.file).endswith("docs/other.md")


class TestLoadIgnoreFromConfig:
    def _write(self, project: Path, body: str) -> None:
        (project / ".beadloom").mkdir(parents=True, exist_ok=True)
        (project / ".beadloom" / "config.yml").write_text(body, encoding="utf-8")

    def test_missing_config_returns_empty(self, tmp_path: Path) -> None:
        assert _load_ignore_from_config(tmp_path) == []

    def test_loads_targeted_rules(self, tmp_path: Path) -> None:
        self._write(
            tmp_path,
            "docs_audit:\n"
            "  ignore:\n"
            "    - path: docs/domains/context-oracle/README.md\n"
            "      fact: language_count\n"
            "      value: 12\n"
            "    - path: docs/guides/vitepress-site.md\n"
            "      fact: cli_command_count\n"
            "      value: 404\n",
        )
        rules = _load_ignore_from_config(tmp_path)
        assert IgnoreRule(
            path="docs/domains/context-oracle/README.md",
            fact="language_count",
            value="12",
        ) in rules
        assert IgnoreRule(
            path="docs/guides/vitepress-site.md",
            fact="cli_command_count",
            value="404",
        ) in rules

    def test_malformed_entries_skipped(self, tmp_path: Path) -> None:
        self._write(
            tmp_path,
            "docs_audit:\n"
            "  ignore:\n"
            "    - path: docs/a.md\n"  # missing fact + value
            "    - not-a-mapping\n",
        )
        assert _load_ignore_from_config(tmp_path) == []
