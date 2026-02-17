"""Tests for auto_link_docs() -- BEAD-11.

Covers:
- Exact ref_id match (docs/{ref_id}/README.md)
- Stem match (docs/{ref_id}.md)
- No match scenario
- Multiple nodes -- partial matching
- Already-has-docs skip behaviour
- Nested docs (docs/domains/{ref_id}/README.md)
- Case sensitivity
- Empty docs directory
- Integration with non_interactive_init()
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import yaml

from beadloom.onboarding.scanner import auto_link_docs

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_graph(tmp_path: Path, nodes: list[dict[str, Any]]) -> None:
    """Write a minimal graph YAML with the given nodes."""
    graph_dir = tmp_path / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True, exist_ok=True)
    data = {"nodes": nodes}
    (graph_dir / "services.yml").write_text(
        yaml.dump(data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def _read_graph(tmp_path: Path) -> dict[str, Any]:
    """Read the graph YAML back."""
    yml = tmp_path / ".beadloom" / "_graph" / "services.yml"
    data: dict[str, Any] = yaml.safe_load(yml.read_text(encoding="utf-8"))
    return data


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAutoLinkDocsExactMatch:
    """Exact ref_id path matches (score=100)."""

    def test_exact_ref_id_readme(self, tmp_path: Path) -> None:
        """docs/{ref_id}/README.md -> linked."""
        doc = tmp_path / "docs" / "auth" / "README.md"
        doc.parent.mkdir(parents=True)
        doc.write_text("# Auth docs\n")

        nodes: list[dict[str, Any]] = [
            {"ref_id": "auth", "kind": "domain", "source": "src/auth/"},
        ]
        _make_graph(tmp_path, nodes)

        linked = auto_link_docs(tmp_path, nodes)

        assert linked == 1
        graph = _read_graph(tmp_path)
        auth_node = graph["nodes"][0]
        assert auth_node["docs"] == ["docs/auth/README.md"]

    def test_exact_ref_id_md(self, tmp_path: Path) -> None:
        """docs/{ref_id}.md -> linked."""
        doc = tmp_path / "docs" / "billing.md"
        doc.parent.mkdir(parents=True)
        doc.write_text("# Billing docs\n")

        nodes: list[dict[str, Any]] = [
            {"ref_id": "billing", "kind": "domain", "source": "src/billing/"},
        ]
        _make_graph(tmp_path, nodes)

        linked = auto_link_docs(tmp_path, nodes)

        assert linked == 1
        graph = _read_graph(tmp_path)
        assert graph["nodes"][0]["docs"] == ["docs/billing.md"]


class TestAutoLinkDocsStemMatch:
    """Stem-based matches (score=80)."""

    def test_stem_match(self, tmp_path: Path) -> None:
        """docs/{ref_id}.md via stem scan -> linked."""
        doc = tmp_path / "docs" / "subdirectory" / "auth.md"
        doc.parent.mkdir(parents=True)
        doc.write_text("# Auth\n")

        nodes: list[dict[str, Any]] = [
            {"ref_id": "auth", "kind": "domain", "source": "src/auth/"},
        ]
        _make_graph(tmp_path, nodes)

        linked = auto_link_docs(tmp_path, nodes)

        assert linked == 1
        graph = _read_graph(tmp_path)
        assert graph["nodes"][0]["docs"] == ["docs/subdirectory/auth.md"]


class TestAutoLinkDocsNoMatch:
    """Docs exist but no matching nodes -> 0 linked."""

    def test_no_match(self, tmp_path: Path) -> None:
        doc = tmp_path / "docs" / "unrelated.md"
        doc.parent.mkdir(parents=True)
        doc.write_text("# Unrelated\n")

        nodes: list[dict[str, Any]] = [
            {"ref_id": "auth", "kind": "domain", "source": "src/auth/"},
        ]
        _make_graph(tmp_path, nodes)

        linked = auto_link_docs(tmp_path, nodes)

        assert linked == 0
        graph = _read_graph(tmp_path)
        assert "docs" not in graph["nodes"][0]


class TestAutoLinkDocsMultipleNodes:
    """Multiple nodes, some match, some don't -> correct count."""

    def test_partial_match(self, tmp_path: Path) -> None:
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "auth.md").write_text("# Auth\n")
        (docs_dir / "billing.md").write_text("# Billing\n")

        nodes: list[dict[str, Any]] = [
            {"ref_id": "auth", "kind": "domain", "source": "src/auth/"},
            {"ref_id": "billing", "kind": "domain", "source": "src/billing/"},
            {"ref_id": "payments", "kind": "domain", "source": "src/payments/"},
        ]
        _make_graph(tmp_path, nodes)

        linked = auto_link_docs(tmp_path, nodes)

        assert linked == 2
        graph = _read_graph(tmp_path)
        ref_to_docs = {n["ref_id"]: n.get("docs") for n in graph["nodes"]}
        assert ref_to_docs["auth"] == ["docs/auth.md"]
        assert ref_to_docs["billing"] == ["docs/billing.md"]
        assert ref_to_docs["payments"] is None


class TestAutoLinkDocsAlreadyHasDocs:
    """Already has docs field -> skip (don't overwrite)."""

    def test_skip_existing_docs(self, tmp_path: Path) -> None:
        doc = tmp_path / "docs" / "auth.md"
        doc.parent.mkdir(parents=True)
        doc.write_text("# Auth\n")

        nodes: list[dict[str, Any]] = [
            {
                "ref_id": "auth",
                "kind": "domain",
                "source": "src/auth/",
                "docs": ["docs/existing/auth.md"],
            },
        ]
        _make_graph(tmp_path, nodes)

        linked = auto_link_docs(tmp_path, nodes)

        assert linked == 0


class TestAutoLinkDocsNestedDocs:
    """Nested docs: docs/domains/{ref_id}/README.md -> linked."""

    def test_domains_nested(self, tmp_path: Path) -> None:
        doc = tmp_path / "docs" / "domains" / "auth" / "README.md"
        doc.parent.mkdir(parents=True)
        doc.write_text("# Auth domain\n")

        nodes: list[dict[str, Any]] = [
            {"ref_id": "auth", "kind": "domain", "source": "src/auth/"},
        ]
        _make_graph(tmp_path, nodes)

        linked = auto_link_docs(tmp_path, nodes)

        assert linked == 1
        graph = _read_graph(tmp_path)
        assert graph["nodes"][0]["docs"] == ["docs/domains/auth/README.md"]

    def test_features_nested(self, tmp_path: Path) -> None:
        doc = tmp_path / "docs" / "features" / "search" / "README.md"
        doc.parent.mkdir(parents=True)
        doc.write_text("# Search feature\n")

        nodes: list[dict[str, Any]] = [
            {"ref_id": "search", "kind": "feature", "source": "src/search/"},
        ]
        _make_graph(tmp_path, nodes)

        linked = auto_link_docs(tmp_path, nodes)

        assert linked == 1
        graph = _read_graph(tmp_path)
        assert graph["nodes"][0]["docs"] == ["docs/features/search/README.md"]

    def test_services_nested(self, tmp_path: Path) -> None:
        doc = tmp_path / "docs" / "services" / "api-gateway" / "README.md"
        doc.parent.mkdir(parents=True)
        doc.write_text("# API Gateway\n")

        nodes: list[dict[str, Any]] = [
            {"ref_id": "api-gateway", "kind": "service", "source": "src/api-gateway/"},
        ]
        _make_graph(tmp_path, nodes)

        linked = auto_link_docs(tmp_path, nodes)

        assert linked == 1
        graph = _read_graph(tmp_path)
        assert graph["nodes"][0]["docs"] == ["docs/services/api-gateway/README.md"]


class TestAutoLinkDocsCaseSensitivity:
    """ref_ids are case-sensitive (on case-sensitive filesystems).

    On macOS (HFS+), the filesystem is case-insensitive, so ``Auth.md``
    and ``auth.md`` resolve to the same file.  We test the matching logic
    at the string level instead: a ref_id that shares no substring with
    any doc filename should not match.
    """

    def test_no_match_different_name(self, tmp_path: Path) -> None:
        """Doc with completely different name does not match."""
        doc = tmp_path / "docs" / "Authentication.md"
        doc.parent.mkdir(parents=True)
        doc.write_text("# Authentication\n")

        # "billing" has no relationship to "Authentication" filename.
        nodes: list[dict[str, Any]] = [
            {"ref_id": "billing", "kind": "domain", "source": "src/billing/"},
        ]
        _make_graph(tmp_path, nodes)

        linked = auto_link_docs(tmp_path, nodes)

        assert linked == 0


class TestAutoLinkDocsEmptyDocs:
    """Empty docs directory -> 0 linked."""

    def test_empty_docs_dir(self, tmp_path: Path) -> None:
        (tmp_path / "docs").mkdir()

        nodes: list[dict[str, Any]] = [
            {"ref_id": "auth", "kind": "domain", "source": "src/auth/"},
        ]
        _make_graph(tmp_path, nodes)

        linked = auto_link_docs(tmp_path, nodes)

        assert linked == 0


class TestAutoLinkDocsNoDocs:
    """No docs directory at all -> 0 linked."""

    def test_no_docs_dir(self, tmp_path: Path) -> None:
        nodes: list[dict[str, Any]] = [
            {"ref_id": "auth", "kind": "domain", "source": "src/auth/"},
        ]

        linked = auto_link_docs(tmp_path, nodes)

        assert linked == 0


class TestAutoLinkDocsParentDirMatch:
    """Parent directory name matches ref_id (score=60)."""

    def test_parent_dir_match(self, tmp_path: Path) -> None:
        doc = tmp_path / "docs" / "auth" / "architecture.md"
        doc.parent.mkdir(parents=True)
        doc.write_text("# Auth Architecture\n")

        nodes: list[dict[str, Any]] = [
            {"ref_id": "auth", "kind": "domain", "source": "src/auth/"},
        ]
        _make_graph(tmp_path, nodes)

        linked = auto_link_docs(tmp_path, nodes)

        assert linked == 1
        graph = _read_graph(tmp_path)
        # Parent-dir match
        assert "docs/auth/" in graph["nodes"][0]["docs"][0]


class TestAutoLinkDocsPartialMatch:
    """Partial stem match (score=40) -- ref_id contained in filename."""

    def test_partial_stem_match(self, tmp_path: Path) -> None:
        doc = tmp_path / "docs" / "auth-service.md"
        doc.parent.mkdir(parents=True)
        doc.write_text("# Auth Service\n")

        nodes: list[dict[str, Any]] = [
            {"ref_id": "auth", "kind": "domain", "source": "src/auth/"},
        ]
        _make_graph(tmp_path, nodes)

        linked = auto_link_docs(tmp_path, nodes)

        assert linked == 1
        graph = _read_graph(tmp_path)
        assert graph["nodes"][0]["docs"] == ["docs/auth-service.md"]

    def test_short_ref_id_no_false_positive(self, tmp_path: Path) -> None:
        """ref_ids shorter than 3 chars don't trigger partial matching."""
        doc = tmp_path / "docs" / "db-migration.md"
        doc.parent.mkdir(parents=True)
        doc.write_text("# DB Migration\n")

        nodes: list[dict[str, Any]] = [
            {"ref_id": "db", "kind": "domain", "source": "src/db/"},
        ]
        _make_graph(tmp_path, nodes)

        linked = auto_link_docs(tmp_path, nodes)

        # "db" is only 2 chars, partial matching requires >= 3.
        assert linked == 0


class TestAutoLinkDocsScoringPriority:
    """Higher-scored matches win."""

    def test_exact_beats_stem(self, tmp_path: Path) -> None:
        """Exact ref_id match (score=100) wins over stem match (score=80)."""
        docs_dir = tmp_path / "docs"
        # Create both exact-path and stem-only matches.
        exact = docs_dir / "auth" / "README.md"
        exact.parent.mkdir(parents=True)
        exact.write_text("# Auth README\n")
        stem = docs_dir / "subdir" / "auth.md"
        stem.parent.mkdir(parents=True)
        stem.write_text("# Auth doc\n")

        nodes: list[dict[str, Any]] = [
            {"ref_id": "auth", "kind": "domain", "source": "src/auth/"},
        ]
        _make_graph(tmp_path, nodes)

        linked = auto_link_docs(tmp_path, nodes)

        assert linked == 1
        graph = _read_graph(tmp_path)
        # Exact match should win.
        assert graph["nodes"][0]["docs"] == ["docs/auth/README.md"]


class TestAutoLinkDocsNonInteractiveInitIntegration:
    """auto_link_docs is called during non_interactive_init()."""

    def test_auto_link_called_in_non_interactive(self, tmp_path: Path) -> None:
        """non_interactive_init() includes docs_linked in result."""
        from beadloom.onboarding.scanner import non_interactive_init

        # Create source tree.
        src = tmp_path / "src"
        auth = src / "auth"
        auth.mkdir(parents=True)
        (auth / "login.py").write_text("def login(): pass\n")

        # Create pre-existing doc that matches.
        doc = tmp_path / "docs" / "auth.md"
        doc.parent.mkdir(parents=True)
        doc.write_text("# Auth docs\n")

        result = non_interactive_init(tmp_path)

        assert result["mode"] == "bootstrap"
        assert "docs_linked" in result
        # Should have linked at least the auth doc.
        assert result["docs_linked"] >= 1
