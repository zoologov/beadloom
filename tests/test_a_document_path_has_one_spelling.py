"""One spelling of a document path, and two readers that cannot disagree again.

BDL-061 S5, bead `beadloom-mr2l.75` (finding BDL-061.18-4). ``check_sync`` was
handed the **docs-dir-relative** path the indexer writes (``guides/ci.md``) and
``check_spaces`` the **project-relative** one (``docs/guides/ci.md``). Kind
agrees on both spellings because a stem carries no prefix, which is why every
shipped case worked and why the disagreement was invisible; roots do not agree,
and the WORKING exemption is the one knob where a declaration decides whether a
gate applies at all. A root-declared exemption therefore took ``sync-check`` from
rc 2 to rc 0 while the check built to catch a wrong declaration reported nothing.

Two properties are pinned here, and both are about the seam rather than about
either symptom:

* **Every pair freshness excuses is a document the report calls WORKING.** If the
  two readers ever classify one file differently, a pair is excused that the
  report does not name, and this invariant is the assertion that goes red.
* **The docs directory is one project's fact, read once.** ``check_sync`` used a
  hardcoded ``docs`` while its own module already resolved ``docs_dir`` from
  configuration for reference documents — two vocabularies inside one module.

The precedence rule the fix establishes is stated as a test rather than only in a
docstring: a root a project DECLARES for the WORKING space wins over the AS-IS
catch-all it overlaps, because a declaration that the catch-all silently shadows
is exactly the defect this bead closes, one layer down.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import yaml

from beadloom.application.doc_spaces import (
    FINDING_WORKING_CONTRADICTED,
    FINDING_WORKING_INERT,
    check_spaces,
)
from beadloom.doc_sync.engine import STATUS_EXEMPT, check_sync
from beadloom.infrastructure.db import create_schema, open_db
from beadloom.infrastructure.doc_roots import (
    DEFAULT_DOCS_DIR,
    SPACE_AS_IS,
    SPACE_WORKING,
    resolve_doc_spaces,
    resolve_docs_dir,
)

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Mapping
    from pathlib import Path


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _config(root: Path, block: Mapping[str, object], **top: object) -> None:
    payload: dict[str, object] = {"doc_roots": dict(block), **top}
    _write(root, ".beadloom/config.yml", yaml.safe_dump(payload))


def _project(root: Path, *, doc_rel: str, docs_dir: str = DEFAULT_DOCS_DIR) -> sqlite3.Connection:
    """A project whose one declared document is paired with code that moved.

    ``doc_rel`` is spelled the way ``index_docs`` spells a ``sync_state`` row —
    relative to the docs directory — because a fixture whose convention differs
    from the indexer's proves the fixture rather than the code.
    """
    _write(root, "src/billing.py", "def charge() -> None:\n    return None\n")
    _write(root, f"{docs_dir}/{doc_rel}", "# billing\n")
    (root / ".beadloom").mkdir(parents=True, exist_ok=True)
    conn = open_db(root / ".beadloom" / "beadloom.db")
    create_schema(conn)
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
        ("billing", "component", "billing", "src/billing.py"),
    )
    conn.execute(
        "INSERT INTO declared_docs (declared_path, doc_path, ref_id) VALUES (?, ?, ?)",
        (f"{docs_dir}/{doc_rel}", doc_rel, "billing"),
    )
    conn.execute(
        "INSERT INTO sync_state (doc_path, code_path, ref_id, code_hash_at_sync, "
        "doc_hash_at_sync, synced_at, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (doc_rel, "src/billing.py", "billing", "baseline", "baseline", "2026-01-01", "ok"),
    )
    conn.commit()
    return conn


def _statuses(rows: list[dict[str, object]], doc_path: str) -> list[object]:
    return [r["status"] for r in rows if r["doc_path"] == doc_path]


def _report_of(root: Path, *, declared: set[str]) -> object:
    return check_spaces(
        root,
        spaces=resolve_doc_spaces(root),
        known_refs=frozenset({"billing"}),
        documented_refs=frozenset({"billing"}),
        declared_doc_paths=frozenset(declared),
        beads_by_epic={},
    )


# --------------------------------------------------------------------------- #
# The seam: one file, two readers, one answer
# --------------------------------------------------------------------------- #


class TestTheTwoReadersClassifyOneFileAlike:
    """The invariant a future change has to break before the symptom returns.

    ``.66`` used this shape for the three composed artifacts — same deletion,
    three readers, they must answer alike. Here it is one document, the freshness
    reader and the report reader, and the answer is which space it is in.
    """

    @pytest.mark.parametrize(
        ("block", "docs_dir", "doc_rel"),
        [
            pytest.param({}, "docs", "ACTIVE.md", id="kind-route-shipped-default"),
            pytest.param(
                {
                    "working": {
                        "roots": ["docs/guides/*.md"],
                        "exempt_from_freshness": True,
                        "reason": "generated release notes, regenerated per tag",
                    }
                },
                "docs",
                "guides/ci.md",
                id="root-route-project-relative",
            ),
            pytest.param(
                {
                    "working": {
                        "roots": ["guides/*.md"],
                        "exempt_from_freshness": True,
                        "reason": "generated release notes, regenerated per tag",
                    }
                },
                "docs",
                "guides/ci.md",
                id="root-route-docs-dir-relative",
            ),
            pytest.param(
                {
                    "as_is": {"roots": ["documentation/**/*.md"]},
                    "working": {
                        "roots": ["documentation/guides/*.md"],
                        "exempt_from_freshness": True,
                        "reason": "generated release notes, regenerated per tag",
                    },
                },
                "documentation",
                "guides/ci.md",
                id="root-route-under-a-configured-docs-dir",
            ),
        ],
    )
    def test_every_excused_pair_is_a_document_the_report_calls_working(
        self, tmp_path: Path, block: Mapping[str, object], docs_dir: str, doc_rel: str
    ) -> None:
        root = tmp_path / "project"
        root.mkdir()
        _config(root, block, docs_dir=docs_dir)
        conn = _project(root, doc_rel=doc_rel, docs_dir=docs_dir)

        rows = check_sync(conn, root)
        spaces = resolve_doc_spaces(root)
        working = {p.relative_to(root).as_posix() for p in spaces.working_documents(root)}
        # Spelled by the test from the docs directory it wrote, so the comparison
        # is not built out of the code under test.
        excused = {f"{docs_dir}/{r['doc_path']}" for r in rows if r["status"] == STATUS_EXEMPT}
        conn.close()

        assert excused <= working

    def test_the_project_relative_spelling_is_what_the_classifier_is_handed(
        self, tmp_path: Path
    ) -> None:
        """The translation, stated as data: one docs-dir-relative path, one answer."""
        _config(tmp_path, {}, docs_dir="documentation")

        spaces = resolve_doc_spaces(tmp_path)

        assert spaces.docs_dir == "documentation"
        assert spaces.project_path("guides/ci.md") == "documentation/guides/ci.md"
        assert spaces.space_of(spaces.project_path("guides/ci.md")) is None


class TestADeclaredWorkingRootReachesFreshness:
    """Direction (a) of the finding: the spelling every neighbour root uses.

    A WORKING root written the way ``doc_roots`` writes every other root — project
    relative — had no effect on freshness at all, because the reader that applies
    it was holding a different spelling of the same file.
    """

    def test_a_project_relative_working_root_excuses_the_pair(self, tmp_path: Path) -> None:
        _config(
            tmp_path,
            {
                "working": {
                    "roots": ["docs/guides/*.md"],
                    "exempt_from_freshness": True,
                    "reason": "generated release notes, regenerated per tag",
                }
            },
        )
        conn = _project(tmp_path, doc_rel="guides/ci.md")

        rows = check_sync(conn, tmp_path)
        conn.close()

        assert _statuses(rows, "guides/ci.md") == [STATUS_EXEMPT]

    def test_a_declared_working_root_wins_over_the_as_is_catch_all(self, tmp_path: Path) -> None:
        """Precedence, and the reason for it.

        The shipped AS-IS root is the catch-all ``docs/**/*.md``. If it shadowed
        a root the project DECLARED for the WORKING space, the declaration would
        be silently inert — the same defect one layer down.
        """
        _config(
            tmp_path,
            {
                "working": {
                    "roots": ["docs/guides/*.md"],
                    "exempt_from_freshness": True,
                    "reason": "generated release notes, regenerated per tag",
                }
            },
        )
        _write(tmp_path, "docs/guides/ci.md", "# ci\n")
        _write(tmp_path, "docs/services/cli.md", "# cli\n")

        spaces = resolve_doc_spaces(tmp_path)

        assert spaces.space_of("docs/guides/ci.md") == SPACE_WORKING
        assert spaces.space_of("docs/services/cli.md") == SPACE_AS_IS
        assert [p.name for p in spaces.documents_in(tmp_path, SPACE_AS_IS)] == ["cli.md"]


class TestADocsDirRelativeRootMeansWhatItSays:
    """The measurement that raised the finding, re-run against the fix.

    ``.18`` measured a working root spelled ``guides/*.md`` silencing six pairs
    under ``docs/guides/`` while the report saw nothing. Under one vocabulary the
    string means a top-level ``guides/`` directory, so it excuses that document
    and no other — and when the project has no such directory the exemption
    reports itself as excusing nothing, which is the liveness leg doing its job
    rather than lying about a gate it had switched off.
    """

    def test_it_no_longer_silences_a_pair_under_the_docs_directory(self, tmp_path: Path) -> None:
        _config(
            tmp_path,
            {
                "as_is": {"roots": ["docs/**/*.md"]},
                "working": {
                    "roots": ["guides/*.md", "*.md"],
                    "exempt_from_freshness": True,
                    "reason": "generated release notes, regenerated per tag",
                },
            },
        )
        _write(tmp_path, "NOTES.md", "# notes\n")
        conn = _project(tmp_path, doc_rel="guides/ci.md")

        rows = check_sync(conn, tmp_path)
        conn.close()

        assert _statuses(rows, "guides/ci.md") == ["stale"]

    def test_an_exemption_that_matches_no_file_at_all_reports_itself(self, tmp_path: Path) -> None:
        _config(
            tmp_path,
            {
                "working": {
                    "roots": ["guides/*.md"],
                    "kinds": [],
                    "exempt_from_freshness": True,
                    "reason": "generated release notes, regenerated per tag",
                }
            },
        )
        conn = _project(tmp_path, doc_rel="guides/ci.md")
        conn.close()

        report = _report_of(tmp_path, declared={"docs/guides/ci.md"})

        assert [f.rule for f in report.findings] == [FINDING_WORKING_INERT]  # type: ignore[attr-defined]


class TestTheDocsDirectoryIsOneFactReadOnce:
    """``check_sync`` hardcoded ``docs`` while its own module resolved ``docs_dir``.

    A project that keeps its documentation elsewhere had freshness hashing files
    that do not exist, so every pair read ``missing`` — the same two-vocabulary
    defect as the finding, on the other half of the same path.
    """

    def test_the_shipped_default_is_the_docs_directory(self, tmp_path: Path) -> None:
        assert resolve_docs_dir(tmp_path) == DEFAULT_DOCS_DIR

    def test_freshness_reads_the_configured_docs_directory(self, tmp_path: Path) -> None:
        _config(
            tmp_path,
            {"as_is": {"roots": ["documentation/**/*.md"]}},
            docs_dir="documentation",
        )
        conn = _project(tmp_path, doc_rel="services/cli.md", docs_dir="documentation")

        rows = check_sync(conn, tmp_path)
        conn.close()

        assert _statuses(rows, "services/cli.md") == ["stale"]

    def test_a_working_document_under_the_configured_docs_directory_is_excused(
        self, tmp_path: Path
    ) -> None:
        _config(
            tmp_path,
            {"as_is": {"roots": ["documentation/**/*.md"]}},
            docs_dir="documentation",
        )
        conn = _project(tmp_path, doc_rel="ACTIVE.md", docs_dir="documentation")

        rows = check_sync(conn, tmp_path)
        conn.close()

        assert _statuses(rows, "ACTIVE.md") == [STATUS_EXEMPT]


class TestTheExemptionExcusesFreshnessAndNothingElse:
    """A document that is gone is gone, whatever space it is in.

    ``exempt`` says "this document was never a description of the code, so
    holding it against the code compares two unrelated things". It says nothing
    about whether the document exists. Reporting an absent file as excused would
    make deleting it quieter than leaving it — BDL-UX #174's equation, reached
    through the one verdict that is deliberately non-blocking.
    """

    def test_a_declared_working_document_that_is_gone_is_missing_not_exempt(
        self, tmp_path: Path
    ) -> None:
        conn = _project(tmp_path, doc_rel="ACTIVE.md")
        (tmp_path / "docs" / "ACTIVE.md").unlink()

        rows = check_sync(conn, tmp_path)
        conn.close()

        assert _statuses(rows, "ACTIVE.md") == ["missing"]

    def test_a_working_document_whose_code_is_gone_is_missing_not_exempt(
        self, tmp_path: Path
    ) -> None:
        conn = _project(tmp_path, doc_rel="ACTIVE.md")
        (tmp_path / "src" / "billing.py").unlink()

        rows = check_sync(conn, tmp_path)
        conn.close()

        assert _statuses(rows, "ACTIVE.md") == ["missing"]

    def test_a_working_document_that_is_present_is_still_excused(
        self, tmp_path: Path
    ) -> None:
        """The control: the exemption still does its one job."""
        conn = _project(tmp_path, doc_rel="ACTIVE.md")

        rows = check_sync(conn, tmp_path)
        conn.close()

        assert _statuses(rows, "ACTIVE.md") == [STATUS_EXEMPT]


class TestTheGateDefeatIsNowReported:
    """The P0 sentence, executable: declaring the docs tree WORKING is loud.

    The declaration is still honoured — WORKING is exempt BY declaration, and
    refusing to honour it would make the remedy for a wrong declaration a wave of
    stale documents. What changes is that the report classifies the same files
    the same way, so every document the graph declares as a node's documentation
    is reported as contradicted instead of silently excused.
    """

    def test_declaring_the_docs_tree_working_is_reported_as_contradicted(
        self, tmp_path: Path
    ) -> None:
        _config(
            tmp_path,
            {
                "working": {
                    "roots": ["docs/**/*.md"],
                    "exempt_from_freshness": True,
                    "reason": "generated release notes, regenerated per tag",
                }
            },
        )
        conn = _project(tmp_path, doc_rel="guides/ci.md")

        rows = check_sync(conn, tmp_path)
        conn.close()
        report = _report_of(tmp_path, declared={"docs/guides/ci.md"})

        assert _statuses(rows, "guides/ci.md") == [STATUS_EXEMPT]
        assert [f.rule for f in report.findings] == [FINDING_WORKING_CONTRADICTED]  # type: ignore[attr-defined]
