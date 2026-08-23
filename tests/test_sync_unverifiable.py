"""Unverifiable is not clean — the one equation behind BDL-UX #174 and #175.

Two measured defects, one sentence. A pair whose doc was DELETED and a pair with
NO BASELINE to compare against are both states in which the checker cannot know
whether the docs are current — and both used to print the same word as a pair
that was checked and found fresh (``ok`` / ``PASS: N pair(s) fresh``).

What these tests pin, in the vocabulary the fix introduces:

- ``missing``     — the thing to check is gone (doc file, code file, or a doc the
  graph DECLARES that does not exist on disk). A failure, not an absence: it
  fails ``sync-check`` (exit 2) and the gate.
- ``unverified``  — there is nothing to compare against (the index was rebuilt,
  so its baseline is the current tree, and git cannot supply one either).
  Reported by name, never counted as fresh, and never silently green.

The git leg is exercised against a REAL git repository (FAKES PROVE FAKES): the
baseline the fix relies on is git history, so a double would only prove the
double's contract.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

from beadloom.application.gate import run_ci_gate
from beadloom.application.reindex import reindex
from beadloom.doc_sync.engine import check_sync, find_missing_declared_docs
from beadloom.infrastructure.db import open_db
from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

_CODE = "# beadloom:domain=myapp\ndef process():\n    return True\n"
_CODE_PLUS = _CODE + "\n\ndef undocumented_public_symbol():\n    return 42\n"


def _git(project: Path, *args: str) -> None:
    subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        cwd=project,
        check=True,
        capture_output=True,
        text=True,
    )


def _make_project(root: Path) -> Path:
    """A minimal project: one node, one declared doc, one annotated source file."""
    graph_dir = root / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)
    (graph_dir / "domains.yml").write_text(
        "nodes:\n"
        "  - ref_id: myapp\n"
        "    kind: domain\n"
        '    summary: "My App domain"\n'
        "    source: src/myapp/\n"
        "    docs:\n"
        "      - docs/domains/myapp/README.md\n",
        encoding="utf-8",
    )
    docs_dir = root / "docs" / "domains" / "myapp"
    docs_dir.mkdir(parents=True)
    (docs_dir / "README.md").write_text(
        "# My App\n\nThis domain contains the handler module.\n", encoding="utf-8"
    )
    src_dir = root / "src" / "myapp"
    src_dir.mkdir(parents=True)
    (src_dir / "__init__.py").write_text("", encoding="utf-8")
    (src_dir / "handler.py").write_text(_CODE, encoding="utf-8")
    return root


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    """A reindexed, NON-git project (no baseline of any kind but the index)."""
    root = _make_project(tmp_path / "proj")
    reindex(root)
    return root


@pytest.fixture()
def git_project(tmp_path: Path) -> Path:
    """The same project inside a real git repository, committed and reindexed."""
    root = _make_project(tmp_path / "gitproj")
    _git(root, "init")
    _git(root, "config", "user.email", "t@t.t")
    _git(root, "config", "user.name", "t")
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "baseline")
    reindex(root)
    return root


def _results(project_root: Path) -> list[dict[str, object]]:
    conn = open_db(project_root / ".beadloom" / "beadloom.db")
    try:
        return check_sync(conn, project_root=project_root)
    finally:
        conn.close()


def _statuses(results: list[dict[str, object]]) -> set[str]:
    return {str(r["status"]) for r in results}


# ---------------------------------------------------------------------------
# BDL-UX #174 — a doc that is gone is MISSING, never fresh
# ---------------------------------------------------------------------------


class TestDeletedDocIsNotFresh:
    def test_pair_whose_doc_file_is_gone_reports_missing(self, project: Path) -> None:
        (project / "docs" / "domains" / "myapp" / "README.md").unlink()

        results = _results(project)

        assert results, "the pair must still be reported, not silently dropped"
        assert _statuses(results) == {"missing"}
        # Both sides of the same fact: the PAIR lost its doc, and the graph's
        # DECLARATION is no longer satisfied. The second survives a reindex.
        assert {str(r["reason"]) for r in results} == {
            "doc_missing",
            "declared_doc_missing",
        }

    def test_pair_whose_code_file_is_gone_reports_missing(self, project: Path) -> None:
        (project / "src" / "myapp" / "handler.py").unlink()

        results = _results(project)

        assert "missing" in _statuses(results)
        assert any(str(r["reason"]) == "code_missing" for r in results)

    def test_declared_doc_deleted_is_found_by_name_after_a_reindex(
        self, project: Path
    ) -> None:
        """The case that survives a reindex: the pair vanishes, the DECLARATION does not."""
        (project / "docs" / "domains" / "myapp" / "README.md").unlink()
        reindex(project)

        conn = open_db(project / ".beadloom" / "beadloom.db")
        try:
            missing = find_missing_declared_docs(conn, project)
            results = check_sync(conn, project_root=project)
        finally:
            conn.close()

        assert [m["doc_path"] for m in missing] == ["docs/domains/myapp/README.md"]
        assert [m["ref_id"] for m in missing] == ["myapp"]
        # and it reaches the caller through the ordinary sync-check result set
        assert any(
            str(r["reason"]) == "declared_doc_missing" and str(r["status"]) == "missing"
            for r in results
        )

    def test_gate_fails_when_a_declared_doc_is_deleted(self, project: Path) -> None:
        (project / "docs" / "domains" / "myapp" / "README.md").unlink()

        result = run_ci_gate(project, fail_on=None, hub_exports=[], no_reindex=False)

        step = next(s for s in result.steps if s.name == "sync-check")
        assert step.status == "FAIL"
        assert result.ok is False
        assert any(
            "docs/domains/myapp/README.md" in str(f.get("locations", ""))
            or "docs/domains/myapp/README.md" in str(f.get("why", ""))
            for f in step.findings
        )

    def test_cli_sync_check_exits_2_when_a_declared_doc_is_deleted(
        self, project: Path
    ) -> None:
        (project / "docs" / "domains" / "myapp" / "README.md").unlink()
        reindex(project)

        result = CliRunner().invoke(
            main, ["sync-check", "--project", str(project), "--json"]
        )

        assert result.exit_code == 2


# ---------------------------------------------------------------------------
# BDL-UX #175 — a rebuilt index has no baseline; it must not print "fresh"
# ---------------------------------------------------------------------------


class TestRebuiltIndexHasNoBaselineOfItsOwn:
    def test_rebuild_after_a_code_edit_is_still_caught_in_a_git_repo(
        self, git_project: Path
    ) -> None:
        """The exact #175 repro: edit code, drop the DB, rebuild — still stale."""
        (git_project / "src" / "myapp" / "handler.py").write_text(
            _CODE_PLUS, encoding="utf-8"
        )
        (git_project / ".beadloom" / "beadloom.db").unlink()
        reindex(git_project)

        results = _results(git_project)

        assert "ok" not in _statuses(results), (
            "a rebuild must not adopt the edited tree as its own baseline"
        )
        assert any(str(r["status"]) == "stale" for r in results)
        assert any(str(r.get("baseline")) == "git:HEAD" for r in results)

    def test_rebuild_without_git_reports_unverified_not_fresh(
        self, project: Path
    ) -> None:
        (project / "src" / "myapp" / "handler.py").write_text(_CODE_PLUS, encoding="utf-8")
        (project / ".beadloom" / "beadloom.db").unlink()
        reindex(project)

        results = _results(project)

        assert "ok" not in _statuses(results)
        assert any(
            str(r["status"]) == "unverified" and str(r["reason"]) == "no_baseline"
            for r in results
        )
        assert all(str(r.get("baseline")) != "index" for r in results)

    def test_a_clean_git_tree_is_verified_against_head_not_merely_assumed(
        self, git_project: Path
    ) -> None:
        (git_project / ".beadloom" / "beadloom.db").unlink()
        reindex(git_project)

        results = _results(git_project)

        assert _statuses(results) == {"ok"}
        assert {str(r["baseline"]) for r in results} == {"git:HEAD"}

    def test_an_attested_pair_is_no_longer_unverified(self, project: Path) -> None:
        """``sync-update`` supplies the baseline a rebuild destroyed."""
        from beadloom.doc_sync.engine import mark_synced

        (project / ".beadloom" / "beadloom.db").unlink()
        reindex(project)
        conn = open_db(project / ".beadloom" / "beadloom.db")
        try:
            mark_synced(
                conn,
                "domains/myapp/README.md",
                "src/myapp/handler.py",
                project,
            )
            results = check_sync(conn, project_root=project)
        finally:
            conn.close()

        assert _statuses(results) == {"ok"}
        assert {str(r["baseline"]) for r in results} == {"index"}

    def test_a_second_reindex_does_not_launder_the_fabricated_baseline(
        self, git_project: Path
    ) -> None:
        """The durability half: a rebuilt baseline stays rebuilt until it is earned.

        Without this, the FIRST gate run after a fresh clone catches the drift and
        the SECOND reports it fresh — the index has absorbed the edit and the
        provenance has been promoted by the mere act of copying it.
        """
        (git_project / ".beadloom" / "beadloom.db").unlink()
        (git_project / "src" / "myapp" / "handler.py").write_text(
            _CODE_PLUS, encoding="utf-8"
        )
        reindex(git_project)
        first = _results(git_project)
        assert any(str(r["status"]) == "stale" for r in first)

        reindex(git_project)
        second = _results(git_project)

        assert any(str(r["status"]) == "stale" for r in second), (
            "the drift is still there and still undocumented; a second rebuild "
            "must not turn it green"
        )
        assert "ok" not in _statuses(second)

    def test_a_carried_baseline_still_detects_drift(self, project: Path) -> None:
        """No regression: the incremental path keeps its stronger baseline."""
        _results(project)  # first run initialises the two-phase baseline
        (project / "src" / "myapp" / "handler.py").write_text(_CODE_PLUS, encoding="utf-8")
        reindex(project)

        results = _results(project)

        assert any(str(r["status"]) == "stale" for r in results)

    def test_gate_says_not_verified_rather_than_pass(self, project: Path) -> None:
        (project / ".beadloom" / "beadloom.db").unlink()

        result = run_ci_gate(project, fail_on=None, hub_exports=[], no_reindex=False)

        step = next(s for s in result.steps if s.name == "sync-check")
        assert step.status == "WARN"
        assert "not verified" in step.summary.lower()
        # unverifiable does not turn a green project red — it stops it reading green.
        assert step.passed is True


# ---------------------------------------------------------------------------
# The count is part of the contract — a surface that shrank must say so
# ---------------------------------------------------------------------------


class TestDeclaredSurfaceLedger:
    def test_absent_ledger_reports_not_recorded_rather_than_nothing(
        self, project: Path
    ) -> None:
        from beadloom.doc_sync.surface_ledger import compare_surface, read_ledger

        verdict = compare_surface(read_ledger(project), declared_pairs=1, declared_docs=1)

        assert verdict.recorded is False
        assert "not recorded" in verdict.message

    def test_a_shrunken_surface_is_named_with_both_numbers(self, project: Path) -> None:
        from beadloom.doc_sync.surface_ledger import (
            compare_surface,
            read_ledger,
            write_ledger,
        )

        write_ledger(project, declared_pairs=275, declared_docs=90)
        verdict = compare_surface(
            read_ledger(project), declared_pairs=269, declared_docs=89
        )

        assert verdict.shrank is True
        assert "275" in verdict.message
        assert "269" in verdict.message

    def test_an_unchanged_surface_is_silent(self, project: Path) -> None:
        from beadloom.doc_sync.surface_ledger import (
            compare_surface,
            read_ledger,
            write_ledger,
        )

        write_ledger(project, declared_pairs=10, declared_docs=4)
        verdict = compare_surface(read_ledger(project), declared_pairs=10, declared_docs=4)

        assert verdict.shrank is False
        assert verdict.message == ""

    def test_cli_records_the_ledger_from_the_live_run(self, project: Path) -> None:
        from beadloom.doc_sync.surface_ledger import read_ledger

        result = CliRunner().invoke(
            main, ["sync-check", "--project", str(project), "--record-surface"]
        )

        assert result.exit_code == 0
        ledger = read_ledger(project)
        assert ledger is not None
        assert ledger.declared_docs == 1
        assert ledger.declared_pairs >= 1

    def test_gate_reports_a_shrunken_surface(self, project: Path) -> None:
        from beadloom.doc_sync.surface_ledger import write_ledger

        write_ledger(project, declared_pairs=99, declared_docs=99)

        result = run_ci_gate(project, fail_on=None, hub_exports=[], no_reindex=False)

        step = next(s for s in result.steps if s.name == "sync-check")
        assert any("99" in str(f.get("why", "")) for f in step.findings)
        assert "SHRANK" in step.summary
        assert step.status == "WARN"

    def test_the_count_is_not_suppressed_by_the_failure_that_caused_it(
        self, project: Path
    ) -> None:
        """The run that deleted a doc is exactly the run whose count fell."""
        from beadloom.doc_sync.surface_ledger import write_ledger

        write_ledger(project, declared_pairs=99, declared_docs=99)
        (project / "docs" / "domains" / "myapp" / "README.md").unlink()

        result = run_ci_gate(project, fail_on=None, hub_exports=[], no_reindex=False)

        step = next(s for s in result.steps if s.name == "sync-check")
        assert step.status == "FAIL"
        assert "missing" in step.summary
        assert "SHRANK" in step.summary, (
            "the failure must not swallow the count that fell with it"
        )


# ---------------------------------------------------------------------------
# Nothing may pass by having less to check — the doctor count audit
# ---------------------------------------------------------------------------


class TestDoctorCountsWhatItClaims:
    def test_the_fixture_really_does_produce_a_doctor_warning(self, project: Path) -> None:
        """Non-vacuity guard: without a warning the next test proves nothing."""
        from beadloom.application.doctor import Severity, run_checks

        _orphan(project)
        conn = open_db(project / ".beadloom" / "beadloom.db")
        try:
            checks = run_checks(conn, project_root=project)
        finally:
            conn.close()

        assert [c for c in checks if c.severity is Severity.WARNING]

    def test_warnings_are_never_counted_as_clean_checks(self, project: Path) -> None:
        """``21 check(s) clean`` counted 9 warnings — and rose when a file vanished."""
        _orphan(project)

        result = run_ci_gate(project, fail_on=None, hub_exports=[], no_reindex=False)
        step = next(s for s in result.steps if s.name == "doctor")

        assert "clean" not in step.summary, (
            f"a run with warnings is not clean — got {step.summary!r}"
        )
        assert "warning(s)" in step.summary

    def test_the_doctor_count_does_not_rise_when_a_declared_doc_is_deleted(
        self, project: Path
    ) -> None:
        before = _doctor_summary(project)
        (project / "docs" / "domains" / "myapp" / "README.md").unlink()
        reindex(project)
        after = _doctor_summary(project)

        assert before != after or "clean" not in after
        assert _leading_int(after) <= _leading_int(before), (
            "a count that grows when the tree shrinks is not a count of anything"
        )


def _orphan(project_root: Path) -> None:
    """Add a doc no node owns, so ``doctor`` genuinely has something to warn about."""
    (project_root / "docs" / "orphan.md").write_text(
        "# Orphan\n\nNo node owns me.\n", encoding="utf-8"
    )
    reindex(project_root)


def _doctor_summary(project_root: Path) -> str:
    result = run_ci_gate(project_root, fail_on=None, hub_exports=[], no_reindex=True)
    return next(s for s in result.steps if s.name == "doctor").summary


def _leading_int(summary: str) -> int:
    return int(summary.split()[0])


# ---------------------------------------------------------------------------
# The git baseline itself — the branches a pair-level test cannot reach
# ---------------------------------------------------------------------------


class TestGitBaselineReader:
    """`changed_paths` answers about a REAL repository (FAKES PROVE FAKES)."""

    def test_outside_a_work_tree_the_answer_is_unknown_not_empty(
        self, tmp_path: Path
    ) -> None:
        from beadloom.doc_sync.git_baseline import changed_paths

        assert changed_paths(tmp_path) is None

    def test_a_repository_with_no_commit_has_no_baseline_to_offer(
        self, tmp_path: Path
    ) -> None:
        from beadloom.doc_sync.git_baseline import changed_paths

        root = tmp_path / "fresh"
        root.mkdir()
        _git(root, "init")
        (root / "a.py").write_text("x = 1\n", encoding="utf-8")

        assert changed_paths(root) is None, "no HEAD is not 'nothing changed'"

    def test_modified_untracked_deleted_and_renamed_are_all_changed(
        self, git_project: Path
    ) -> None:
        from beadloom.doc_sync.git_baseline import changed_paths

        (git_project / "src" / "myapp" / "handler.py").write_text(
            _CODE_PLUS, encoding="utf-8"
        )
        (git_project / "src" / "myapp" / "brand_new.py").write_text("", encoding="utf-8")
        (git_project / "docs" / "domains" / "myapp" / "README.md").unlink()
        _git(git_project, "mv", "src/myapp/__init__.py", "src/myapp/renamed.py")

        changed = changed_paths(git_project)

        assert changed is not None
        assert "src/myapp/handler.py" in changed
        assert "src/myapp/brand_new.py" in changed
        assert "docs/domains/myapp/README.md" in changed
        # a rename counts at BOTH endpoints: the old path stopped being what
        # HEAD says it is, and the new one is not in HEAD at all
        assert "src/myapp/renamed.py" in changed
        assert "src/myapp/__init__.py" in changed

    def test_paths_are_relative_to_the_project_not_the_repository(
        self, tmp_path: Path
    ) -> None:
        """A Beadloom project inside a monorepo is the ordinary case."""
        from beadloom.doc_sync.git_baseline import changed_paths

        repo = tmp_path / "monorepo"
        repo.mkdir()
        project = _make_project(repo / "services" / "myapp")
        (repo / "unrelated.txt").write_text("not ours\n", encoding="utf-8")
        _git(repo, "init")
        _git(repo, "config", "user.email", "t@t.t")
        _git(repo, "config", "user.name", "t")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-m", "baseline")
        (project / "src" / "myapp" / "handler.py").write_text(
            _CODE_PLUS, encoding="utf-8"
        )
        (repo / "unrelated.txt").write_text("changed elsewhere\n", encoding="utf-8")

        changed = changed_paths(project)

        assert changed == frozenset({"src/myapp/handler.py"}), (
            "repository-relative paths must be re-rooted, and a change outside "
            "the project is not this project's"
        )


class TestNothingPassesByHavingLessToCheck:
    """The audit the bead asked for: every gate-visible counter, not just sync-check."""

    def test_doctor_reports_a_pair_whose_doc_is_gone(self, project: Path) -> None:
        from beadloom.application.doctor import Severity, run_checks

        conn = open_db(project / ".beadloom" / "beadloom.db")
        try:
            check_sync(conn, project_root=project)  # establishes the statuses
            (project / "docs" / "domains" / "myapp" / "README.md").unlink()
            check_sync(conn, project_root=project)
            checks = run_checks(conn, project_root=project)
        finally:
            conn.close()

        sync_checks = [c for c in checks if c.name == "stale_sync"]
        assert sync_checks
        assert all(c.severity is Severity.WARNING for c in sync_checks), (
            "'No stale sync entries' over a deleted document is the same false "
            "green the verdict exists to end"
        )

    def test_the_status_counter_does_not_treat_a_missing_doc_as_fresh(
        self, project: Path
    ) -> None:
        conn = open_db(project / ".beadloom" / "beadloom.db")
        try:
            check_sync(conn, project_root=project)
            before = conn.execute(
                "SELECT count(*) FROM sync_state WHERE status IN ('stale', 'missing')"
            ).fetchone()[0]
            (project / "docs" / "domains" / "myapp" / "README.md").unlink()
            check_sync(conn, project_root=project)
            after = conn.execute(
                "SELECT count(*) FROM sync_state WHERE status IN ('stale', 'missing')"
            ).fetchone()[0]
        finally:
            conn.close()

        assert before == 0
        assert after > 0, "deleting the doc must move the not-fresh count UP"
