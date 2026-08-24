"""``missing_sections`` — the staleness reason that compares STRUCTURE (BDL-061 S4b).

The five reasons ``sync-check`` shipped with all compare CONTENT: a hash moved,
a symbol set moved, a file appeared, a module went unmentioned, a declared doc
vanished. None of them can see that a document lost the sections it was
generated with, so a README could be edited down to a title and every count
still read fresh.

The check is deliberately **peer-relative**, which is the whole design and the
reason it is worth having. A required section that NO document of its kind uses
says something about the project's convention, not about any one document, and
reporting it once beats reporting it seventy times — the same decision `.13`
took when a features glob matching zero files reports the glob rather than every
node. A section its peers DO carry and this document does not is an outlier, and
that is the finding.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.doc_sync.doc_shape import (
    REASON_MISSING_SECTIONS,
    REASON_SECTION_NOT_IN_USE,
    STATUS_INCOMPLETE,
    check_section_shape,
)
from beadloom.doc_sync.engine import BLOCKING_STATUSES, check_sync
from beadloom.infrastructure.db import create_schema, open_db

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

_REQUIREMENTS = {
    "domain": ("Source", "Dependencies", "Features"),
    "feature": ("Source", "Dependencies", "Parent"),
}

_FULL_DOMAIN_DOC = """\
# billing

> Invoices

## Source

`src/billing/`

## Dependencies

- Depends on: ledger

## Features

- invoicing
"""


def _doc_without(section: str) -> str:
    """The full domain document with one section's heading and body removed."""
    blocks = _FULL_DOMAIN_DOC.split("\n\n")
    return "\n\n".join(b for b in blocks if not b.startswith(f"## {section}"))


def _project(tmp_path: Path, docs: dict[str, tuple[str, str]]) -> sqlite3.Connection:
    """A project whose ``docs`` map ``ref_id -> (node kind, document text)``."""
    (tmp_path / ".beadloom").mkdir(parents=True, exist_ok=True)
    conn = open_db(tmp_path / ".beadloom" / "beadloom.db")
    create_schema(conn)
    for ref_id, (kind, text) in docs.items():
        rel = f"domains/{ref_id}/README.md"
        path = tmp_path / "docs" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            (ref_id, kind, "", f"src/{ref_id}/"),
        )
        conn.execute(
            "INSERT INTO docs (path, kind, ref_id, hash) VALUES (?, ?, ?, 'h')",
            (rel, "domain" if kind == "domain" else "feature", ref_id),
        )
    conn.commit()
    return conn


class TestOutlierIsReported:
    def test_a_document_missing_a_section_its_peers_carry_is_reported(
        self, tmp_path: Path
    ) -> None:
        conn = _project(
            tmp_path,
            {
                "billing": ("domain", _FULL_DOMAIN_DOC),
                "shipping": ("domain", _FULL_DOMAIN_DOC),
                "ledger": ("domain", _doc_without("Features")),
            },
        )
        rows = check_section_shape(conn, tmp_path, _REQUIREMENTS)
        conn.close()

        missing = [r for r in rows if r["reason"] == REASON_MISSING_SECTIONS]
        assert len(missing) == 1
        assert missing[0]["ref_id"] == "ledger"
        assert missing[0]["details"] == "Features"
        assert missing[0]["status"] == STATUS_INCOMPLETE

    def test_the_finding_names_every_missing_section(self, tmp_path: Path) -> None:
        stripped = _doc_without("Features")
        stripped = "\n\n".join(
            b for b in stripped.split("\n\n") if not b.startswith("## Dependencies")
        )
        conn = _project(
            tmp_path,
            {
                "billing": ("domain", _FULL_DOMAIN_DOC),
                "shipping": ("domain", _FULL_DOMAIN_DOC),
                "ledger": ("domain", stripped),
            },
        )
        rows = check_section_shape(conn, tmp_path, _REQUIREMENTS)
        conn.close()

        missing = [r for r in rows if r["reason"] == REASON_MISSING_SECTIONS]
        assert missing[0]["details"] == "Dependencies, Features"

    def test_a_complete_document_is_not_reported(self, tmp_path: Path) -> None:
        conn = _project(
            tmp_path,
            {
                "billing": ("domain", _FULL_DOMAIN_DOC),
                "ledger": ("domain", _FULL_DOMAIN_DOC),
            },
        )
        rows = check_section_shape(conn, tmp_path, _REQUIREMENTS)
        conn.close()
        assert [r for r in rows if r["reason"] == REASON_MISSING_SECTIONS] == []


class TestAConventionIsReportedOnce:
    def test_a_section_no_document_uses_is_reported_once_not_per_document(
        self, tmp_path: Path
    ) -> None:
        """One configuration mismatch must not print as N document findings."""
        without_source = _doc_without("Source")
        conn = _project(
            tmp_path,
            {
                "billing": ("domain", without_source),
                "ledger": ("domain", without_source),
                "shipping": ("domain", without_source),
            },
        )
        rows = check_section_shape(conn, tmp_path, _REQUIREMENTS)
        conn.close()

        unused = [r for r in rows if r["reason"] == REASON_SECTION_NOT_IN_USE]
        assert len(unused) == 1
        assert unused[0]["details"] == "Source (0/3)"
        assert "domain" in unused[0]["ref_id"]
        assert [r for r in rows if r["reason"] == REASON_MISSING_SECTIONS] == []

    def test_a_section_a_minority_carries_does_not_report_the_majority(
        self, tmp_path: Path
    ) -> None:
        """Measured on this repository: ``## Parent`` is in 1 feature SPEC of 36.

        A presence-of-one rule would have reported the 35 documents that follow
        the project's actual convention, which inverts the finding the check
        exists to make.
        """
        without_features = _doc_without("Features")
        conn = _project(
            tmp_path,
            {
                "billing": ("domain", _FULL_DOMAIN_DOC),
                "ledger": ("domain", without_features),
                "shipping": ("domain", without_features),
                "payroll": ("domain", without_features),
            },
        )
        rows = check_section_shape(conn, tmp_path, _REQUIREMENTS)
        conn.close()

        assert [r for r in rows if r["reason"] == REASON_MISSING_SECTIONS] == []
        unused = [r for r in rows if r["reason"] == REASON_SECTION_NOT_IN_USE]
        assert "Features (1/4)" in unused[0]["details"]

    def test_a_tie_is_not_yet_a_convention(self, tmp_path: Path) -> None:
        """Half the documents doing something is not a shape to hold the rest to."""
        conn = _project(
            tmp_path,
            {
                "billing": ("domain", _FULL_DOMAIN_DOC),
                "ledger": ("domain", _doc_without("Features")),
            },
        )
        rows = check_section_shape(conn, tmp_path, _REQUIREMENTS)
        conn.close()
        assert [r for r in rows if r["reason"] == REASON_MISSING_SECTIONS] == []

    def test_a_kind_with_no_documents_reports_nothing(self, tmp_path: Path) -> None:
        """No population is not a violation of every rule about that population."""
        conn = _project(tmp_path, {"billing": ("domain", _FULL_DOMAIN_DOC)})
        rows = check_section_shape(conn, tmp_path, _REQUIREMENTS)
        conn.close()
        assert [r for r in rows if "feature" in str(r["ref_id"])] == []


class TestASectionIsMatchedByItsName:
    def test_a_wider_heading_still_carries_the_section(self, tmp_path: Path) -> None:
        """``## Features and components`` is not a document that lost Features.

        Measured: string equality reported two domain READMEs of this repository
        that carry the section under a wider title.
        """
        widened = _FULL_DOMAIN_DOC.replace(
            "## Features", "## Features and components"
        )
        conn = _project(
            tmp_path,
            {
                "billing": ("domain", _FULL_DOMAIN_DOC),
                "shipping": ("domain", _FULL_DOMAIN_DOC),
                "ledger": ("domain", widened),
            },
        )
        rows = check_section_shape(conn, tmp_path, _REQUIREMENTS)
        conn.close()
        assert [r for r in rows if r["reason"] == REASON_MISSING_SECTIONS] == []

    def test_a_promoted_or_demoted_heading_still_carries_the_section(
        self, tmp_path: Path
    ) -> None:
        deeper = _FULL_DOMAIN_DOC.replace("## Features", "#### Features")
        conn = _project(
            tmp_path,
            {
                "billing": ("domain", _FULL_DOMAIN_DOC),
                "shipping": ("domain", _FULL_DOMAIN_DOC),
                "ledger": ("domain", deeper),
            },
        )
        rows = check_section_shape(conn, tmp_path, _REQUIREMENTS)
        conn.close()
        assert [r for r in rows if r["reason"] == REASON_MISSING_SECTIONS] == []

    def test_a_word_inside_a_longer_word_does_not_count(self, tmp_path: Path) -> None:
        """``## Featureset`` is a different heading, not a loose match."""
        renamed = _FULL_DOMAIN_DOC.replace("## Features", "## Featureset")
        conn = _project(
            tmp_path,
            {
                "billing": ("domain", _FULL_DOMAIN_DOC),
                "shipping": ("domain", _FULL_DOMAIN_DOC),
                "ledger": ("domain", renamed),
            },
        )
        rows = check_section_shape(conn, tmp_path, _REQUIREMENTS)
        conn.close()
        missing = [r for r in rows if r["reason"] == REASON_MISSING_SECTIONS]
        assert [r["ref_id"] for r in missing] == ["ledger"]


class TestHonestLimits:
    def test_a_document_absent_from_disk_is_not_reported_as_incomplete(
        self, tmp_path: Path
    ) -> None:
        """A missing file is a ``missing`` pair, not a document with no sections.

        Three documents, not two: with only two the majority rule would mask the
        defect this test exists to catch — a deleted file read as an empty one
        drops the section below a majority and the run goes quiet for the wrong
        reason. Measured by sabotage S3.
        """
        conn = _project(
            tmp_path,
            {
                "billing": ("domain", _FULL_DOMAIN_DOC),
                "shipping": ("domain", _FULL_DOMAIN_DOC),
                "ledger": ("domain", _FULL_DOMAIN_DOC),
            },
        )
        (tmp_path / "docs" / "domains" / "ledger" / "README.md").unlink()
        rows = check_section_shape(conn, tmp_path, _REQUIREMENTS)
        conn.close()
        assert [r for r in rows if r["ref_id"] == "ledger"] == []

    def test_a_node_kind_with_no_requirements_is_not_checked(
        self, tmp_path: Path
    ) -> None:
        conn = _project(tmp_path, {"beadloom": ("service", "# beadloom\n")})
        rows = check_section_shape(conn, tmp_path, {"domain": ("Source",)})
        conn.close()
        assert rows == []

    def test_the_new_status_does_not_block_the_gate(self) -> None:
        """`warn`: no adopter's green project turns red on upgrade."""
        assert STATUS_INCOMPLETE not in BLOCKING_STATUSES


class TestWiredIntoCheckSync:
    def test_check_sync_reports_missing_sections_when_requirements_are_given(
        self, tmp_path: Path
    ) -> None:
        conn = _project(
            tmp_path,
            {
                "billing": ("domain", _FULL_DOMAIN_DOC),
                "shipping": ("domain", _FULL_DOMAIN_DOC),
                "ledger": ("domain", _doc_without("Features")),
            },
        )
        results = check_sync(
            conn, project_root=tmp_path, section_requirements=_REQUIREMENTS
        )
        conn.close()
        assert any(r["reason"] == REASON_MISSING_SECTIONS for r in results)

    def test_check_sync_without_requirements_reports_no_shape_rows(
        self, tmp_path: Path
    ) -> None:
        """Structure is not checked unless a caller supplies the shape to check."""
        conn = _project(
            tmp_path,
            {
                "billing": ("domain", _FULL_DOMAIN_DOC),
                "shipping": ("domain", _FULL_DOMAIN_DOC),
                "ledger": ("domain", _doc_without("Features")),
            },
        )
        results = check_sync(conn, project_root=tmp_path)
        conn.close()
        assert all(r["status"] != STATUS_INCOMPLETE for r in results)


class TestSurfacedByTheGateAndTheCli:
    @pytest.fixture
    def _repo(self, tmp_path: Path) -> Path:
        conn = _project(
            tmp_path,
            {
                "billing": ("domain", _FULL_DOMAIN_DOC),
                "shipping": ("domain", _FULL_DOMAIN_DOC),
                "ledger": ("domain", _doc_without("Features")),
            },
        )
        conn.close()
        return tmp_path

    def test_the_gate_reports_the_finding_without_failing(self, _repo: Path) -> None:
        from beadloom.application.gate import _step_sync_check

        step = _step_sync_check(_repo)

        assert step.passed is True
        assert any(
            f.get("rule") == REASON_MISSING_SECTIONS for f in step.findings
        ), step.findings
        assert all(
            f.get("severity") == "warning"
            for f in step.findings
            if f.get("rule") == REASON_MISSING_SECTIONS
        )

    def test_the_cli_prints_the_finding(self, _repo: Path) -> None:
        from click.testing import CliRunner

        from beadloom.services.cli import main

        result = CliRunner().invoke(
            main, ["sync-check", "--project", str(_repo)]
        )

        assert "missing_sections" in result.output or "Features" in result.output


class TestForAProjectThatIsNotBeadloom:
    def test_an_adopters_own_project_layer_defines_the_required_sections(
        self, tmp_path: Path
    ) -> None:
        """The shape checked is the shape THEIR templates compose to, not ours."""
        from beadloom.onboarding.composer import PROJECT_FLOW_DIRNAME
        from beadloom.onboarding.doc_templates import required_sections_by_node_kind
        from tests.adopter_project import typescript_project

        project = typescript_project(tmp_path / "acme")
        fragment = project.root / PROJECT_FLOW_DIRNAME / "docs" / "domain.md"
        fragment.parent.mkdir(parents=True)
        fragment.write_text("## Runbook\n\nWho to page.\n", encoding="utf-8")

        requirements = required_sections_by_node_kind(
            config=_adopter_config(), project_root=project.root
        )
        assert "Runbook" in requirements["domain"]

        with_runbook = _FULL_DOMAIN_DOC + "\n## Runbook\n\nPage the on-call.\n"
        conn = _project(
            project.root,
            {
                "billing": ("domain", with_runbook),
                "shipping": ("domain", with_runbook),
                "ledger": ("domain", _FULL_DOMAIN_DOC),
            },
        )
        rows = check_section_shape(conn, project.root, requirements)
        conn.close()

        missing = [r for r in rows if r["reason"] == REASON_MISSING_SECTIONS]
        assert [r["ref_id"] for r in missing] == ["ledger"]
        assert missing[0]["details"] == "Runbook"


def _adopter_config() -> object:
    from beadloom.onboarding.flow_config import FlowConfig

    return FlowConfig(tools=("claude",), architecture="ddd", stack=("typescript",))
