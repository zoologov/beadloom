"""BDL-061 bead `.85` — an attestation covers only what the run had grounds for.

Bead `.78` moved the freshness FACT to the file; the CLAIM stayed on the ref, so
``sync-update <ref> --yes`` re-baselined every pair the ref owned. These tests
pin the split: the node-level ``symbols_hash`` is carried forward for every pair
(a fact about the index), while ``baseline_source = attested`` is written only
for the pairs the run has grounds for (a claim about a document somebody read).

Against the real reindex pipeline and the real CLI — the subject is what
``sync_state`` records, and a hand-built table would prove the fixture.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from click.testing import CliRunner

from beadloom.application.reindex import reindex
from beadloom.doc_sync.engine import (
    BASELINE_SOURCE_ATTESTED,
    BASELINE_SOURCE_INDEX_BUILD,
    attest_ref,
    check_sync,
    pairs_of_ref,
)
from beadloom.infrastructure.db import open_db
from beadloom.services.cli import main

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

_FILES = ("alpha", "beta", "gamma")
_DOCS = ("widgets.md", "widgets-guide.md")
_MOVER = "src/widgets/alpha.py"


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)  # noqa: S603, S607


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    """One node, two documents, three annotated code files — six pairs."""
    root = tmp_path / "proj"
    root.mkdir()
    _write(
        root,
        ".beadloom/_graph/graph.yml",
        yaml.dump(
            {
                "nodes": [
                    {
                        "ref_id": "widgets",
                        "kind": "domain",
                        "summary": "widgets",
                        "source": "src/widgets",
                        "docs": list(_DOCS),
                    }
                ]
            }
        ),
    )
    modules = "\n".join(f"- `{name}.py` — what {name} does." for name in _FILES)
    for doc in _DOCS:
        _write(root, f"docs/{doc}", f"# {doc}\n\n## Modules\n\n{modules}\n")
    for name in _FILES:
        _write(
            root,
            f"src/widgets/{name}.py",
            f"# beadloom:domain=widgets\ndef {name}():\n    pass\n",
        )
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "Test")
    _write(root, ".gitignore", ".beadloom/beadloom.db\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "baseline")
    reindex(root)
    return root


def _move_alpha(root: Path) -> None:
    _write(
        root,
        _MOVER,
        "# beadloom:domain=widgets\ndef alpha_renamed(extra):\n    return extra\n",
    )
    reindex(root)


def _conn(root: Path) -> sqlite3.Connection:
    return open_db(root / ".beadloom" / "beadloom.db")


def _rows(root: Path) -> dict[tuple[str, str], dict[str, str]]:
    conn = _conn(root)
    try:
        return {
            (str(r["doc_path"]), str(r["code_path"])): {
                "baseline_source": str(r["baseline_source"] or ""),
                "symbols_hash": str(r["symbols_hash"] or ""),
                "synced_at": str(r["synced_at"] or ""),
            }
            for r in conn.execute("SELECT * FROM sync_state")
        }
    finally:
        conn.close()


def _run(root: Path, *args: str) -> Any:
    return CliRunner().invoke(main, ["sync-update", *args, "--project", str(root)])


class TestTheFactMovesAndTheClaimDoesNot:
    """``attest_ref`` writes one thing for every pair and another for a few."""

    def test_scoped_attestation_claims_only_the_scoped_pairs(self, project: Path) -> None:
        _move_alpha(project)
        conn = _conn(project)
        try:
            scope = {(doc, _MOVER) for doc in _DOCS}
            result = attest_ref(conn, "widgets", project, scope=scope)
        finally:
            conn.close()
        assert set(result.attested) == scope
        assert len(result.carried) == 4
        rows = _rows(project)
        claimed = {
            pair for pair, row in rows.items()
            if row["baseline_source"] == BASELINE_SOURCE_ATTESTED
        }
        assert claimed == scope

    def test_the_node_hash_is_carried_forward_for_every_pair(self, project: Path) -> None:
        """The FACT is not the claim: an unclaimed pair still learns what moved.

        Left behind, the ``sibling_symbols_changed`` verdict would stand forever
        on a pair whose mover has been re-baselined and can no longer be named.
        """
        _move_alpha(project)
        conn = _conn(project)
        try:
            attest_ref(conn, "widgets", project, scope={(doc, _MOVER) for doc in _DOCS})
        finally:
            conn.close()
        hashes = {row["symbols_hash"] for row in _rows(project).values()}
        assert len(hashes) == 1

    def test_an_unclaimed_pair_keeps_its_synced_at(self, project: Path) -> None:
        _move_alpha(project)
        before = {pair: row["synced_at"] for pair, row in _rows(project).items()}
        conn = _conn(project)
        try:
            attest_ref(conn, "widgets", project, scope={(doc, _MOVER) for doc in _DOCS})
        finally:
            conn.close()
        after = _rows(project)
        for pair, stamp in before.items():
            if pair[1] == _MOVER:
                continue
            assert after[pair]["synced_at"] == stamp

    def test_no_scope_attests_the_whole_ref(self, project: Path) -> None:
        conn = _conn(project)
        try:
            result = attest_ref(conn, "widgets", project, scope=None)
        finally:
            conn.close()
        assert len(result.attested) == 6
        assert result.carried == ()


class TestTheWithheldClaimIsObservable:
    """A pair nobody read stays on the harder check, which is the point."""

    def test_an_unclaimed_pair_is_still_corroborated_against_git(
        self, project: Path
    ) -> None:
        """``check_sync`` asks git about an ``index_build`` baseline and trusts an
        attested one. A bulk re-attestation used to switch that off for four
        documents to clear one."""
        _move_alpha(project)
        result = _run(project, "widgets", "--yes")
        assert result.exit_code == 0, result.output
        rows = _rows(project)
        unclaimed = {
            pair for pair, row in rows.items()
            if row["baseline_source"] == BASELINE_SOURCE_INDEX_BUILD
        }
        assert unclaimed == {
            (doc, f"src/widgets/{name}.py")
            for doc in _DOCS
            for name in ("beta", "gamma")
        }


class TestTheCommandSurface:
    """What an operator types, and what the run tells them it did."""

    def test_a_run_with_no_grounds_attests_nothing_and_says_so(
        self, project: Path
    ) -> None:
        result = _run(project, "widgets", "--yes")
        assert result.exit_code == 0, result.output
        assert "Nothing to attest for widgets" in result.output
        assert "--all-pairs" in result.output
        assert all(
            row["baseline_source"] != BASELINE_SOURCE_ATTESTED
            for row in _rows(project).values()
        )

    def test_all_pairs_attests_the_whole_ref_deliberately(self, project: Path) -> None:
        result = _run(project, "widgets", "--yes", "--all-pairs")
        assert result.exit_code == 0, result.output
        assert "attested 6 pair(s)" in result.output
        assert all(
            row["baseline_source"] == BASELINE_SOURCE_ATTESTED
            for row in _rows(project).values()
        )

    def test_pair_names_a_document_and_the_error_lists_the_real_ones(
        self, project: Path
    ) -> None:
        result = _run(project, "widgets", "--yes", "--pair", "nope.md")
        assert result.exit_code != 0
        assert "no doc pair named nope.md" in result.output
        assert "widgets-guide.md" in result.output

    def test_pair_and_all_pairs_are_mutually_exclusive(self, project: Path) -> None:
        result = _run(
            project, "widgets", "--yes", "--pair", "widgets.md", "--all-pairs"
        )
        assert result.exit_code != 0
        assert "mutually exclusive" in result.output

    def test_pair_requires_yes(self, project: Path) -> None:
        result = _run(project, "widgets", "--pair", "widgets.md")
        assert result.exit_code != 0
        assert "require --yes" in result.output


class TestTheFixpointStillCloses:
    """The automated loop must still reach zero stale pairs, or the Gate hangs."""

    def test_all_yes_clears_every_stale_pair(self, project: Path) -> None:
        _move_alpha(project)
        result = _run(project, "--yes", "--all")
        assert result.exit_code == 0, result.output
        conn = _conn(project)
        try:
            statuses = [
                r["status"] for r in check_sync(conn, project_root=project)
                if r.get("code_path")
            ]
        finally:
            conn.close()
        assert "stale" not in statuses

    def test_the_ref_still_owns_every_pair_after_a_scoped_attestation(
        self, project: Path
    ) -> None:
        _move_alpha(project)
        _run(project, "widgets", "--yes")
        conn = _conn(project)
        try:
            assert len(pairs_of_ref(conn, "widgets")) == 6
        finally:
            conn.close()


class TestAPairIsNamedByBothSides:
    """A document several agents change at once cannot be claimed as a whole.

    Measured on this branch: `domains/doc-sync/README.md` was stale against one
    agent's `engine.py` and another's `surface.py` in the same run, so naming the
    document alone would have recorded a reading of a change nobody had seen.
    """

    def test_code_narrows_a_document_to_the_file_that_was_read(
        self, project: Path
    ) -> None:
        result = _run(
            project,
            "widgets",
            "--yes",
            "--pair",
            "widgets.md",
            "--code",
            "src/widgets/beta.py",
        )
        assert result.exit_code == 0, result.output
        claimed = {
            pair for pair, row in _rows(project).items()
            if row["baseline_source"] == BASELINE_SOURCE_ATTESTED
        }
        assert claimed == {("widgets.md", "src/widgets/beta.py")}

    def test_code_alone_claims_that_file_under_every_document(
        self, project: Path
    ) -> None:
        result = _run(project, "widgets", "--yes", "--code", "src/widgets/beta.py")
        assert result.exit_code == 0, result.output
        claimed = {
            pair for pair, row in _rows(project).items()
            if row["baseline_source"] == BASELINE_SOURCE_ATTESTED
        }
        assert claimed == {(doc, "src/widgets/beta.py") for doc in _DOCS}

    def test_an_unknown_code_path_is_refused_rather_than_selecting_nothing(
        self, project: Path
    ) -> None:
        """A typo that selected nothing would print "nothing to attest", which
        reads exactly like a ref that needed no work."""
        result = _run(project, "widgets", "--yes", "--code", "src/widgets/nope.py")
        assert result.exit_code != 0
        assert "no code pair named src/widgets/nope.py" in result.output
        assert "src/widgets/alpha.py" in result.output
