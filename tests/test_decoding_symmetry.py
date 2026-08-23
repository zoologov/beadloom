"""Both sides of a comparison are decoded by the same, stated rule (BDL-061.40).

Four call sites where a comparison decoded its two sides by *different* rules:
the current content was read with an explicit ``encoding="utf-8"`` while the
at-ref / subprocess content was decoded by whatever the image says (``text=True``
consults ``locale.getpreferredencoding(False)``). The asymmetry is the defect —
and it is what made three of the four invisible, because on a UTF-8 machine the
two rules agree and every test passes.

The direction is what makes this P0 rather than cosmetic: none of these blocks,
they **answer wrongly**. ``sync-check --since`` reports drift in a file nobody
touched; ``diff --since`` fabricates a change set for the review role; the
dashboard shows a contributor who does not exist; a federation export silently
drops its commit provenance while looking like a legitimate "unknown HEAD".

Re-measured here before any fix (standing rule 6 — .37's verdicts are another
agent's measurements), on this repo and on purpose-built repos:

===============================  =========  ==================================
site                             ambient    measured, before the fix
===============================  =========  ==================================
doc_sync/engine.py               latin-1    hashes differ for an unchanged file
doc_sync/engine.py               ascii      UnicodeDecodeError, uncaught
graph/diff.py                    latin-1    yaml ReaderError, uncaught
graph/diff.py                    ascii      UnicodeDecodeError, uncaught
infrastructure/git_activity.py   latin-1    'Ð\\x98Ð²Ð°Ð½ ...' — a real name
infrastructure/git_activity.py   ascii      UnicodeDecodeError past the handler
graph/federation/export.py       latin-1    None (a dishonest "unknown HEAD")
graph/federation/export.py       ascii      UnicodeDecodeError, uncaught
===============================  =========  ==================================

Two instruments, because one alone would prove too little (standing rule 4):

* the **ambient codec** rows drive the real module through
  :class:`tests.ambient_codec.AmbientTextMode`, which re-implements CPython's
  documented text-mode rule with the codec as a parameter — an ambient non-UTF-8
  codec cannot be arranged on this machine (PEP 538/540 coercion);
* the **undecodable bytes** rows use no double at all: real ``git``, real bytes
  that no codec can read as UTF-8, reproduced on this UTF-8 macOS.

Each ``errors=`` choice below is a decision with a reason, not a default; the
reasons are in the production docstrings and are pinned by the tests named
``test_the_stated_cost_*``.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from typing import TYPE_CHECKING, Any

import pytest
import yaml

from beadloom.doc_sync.engine import check_sync, check_sync_since, mark_synced
from beadloom.graph import diff as graph_diff
from beadloom.graph.diff import compute_diff
from beadloom.graph.federation import export as federation_export
from beadloom.infrastructure import git_activity
from beadloom.infrastructure.db import open_db
from tests.ambient_codec import AMBIENT_CODECS, under_ambient_codec
from tests.filesystem_names import as_the_process_receives

if TYPE_CHECKING:
    from pathlib import Path

#: A byte that is not valid UTF-8 in any position, and that a non-UTF-8 codec
#: either mangles (latin-1) or refuses (ascii).
UNDECODABLE = b"\xff"

#: The character every document in this repo uses and no ASCII codec can read.
EM_DASH = "—"

pytestmark = pytest.mark.skipif(
    sys.platform == "win32",
    reason="POSIX-only fixtures (raw bytes in git objects, PATH replacement); .36 #3",
)


def _git(repo: Path, *args: str, **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
    """Real git, bytes out — the fixtures must not decode what they are testing."""
    return subprocess.run(  # noqa: S603 — fixed argv, no shell
        ["git", "-C", str(repo), *args],  # noqa: S607
        check=True,
        capture_output=True,
        **kwargs,  # input= / env= passthrough
    )


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@t.t")
    _git(repo, "config", "user.name", "t")


def _path_without_git(tmp_path: Path) -> str:
    """A ``PATH`` on which ``git`` does not exist.

    Replaced, never prepended: ``execvp`` remembers ``EACCES`` and keeps
    searching, so a shadowing entry does not make the binary unreachable — the
    vacuous-test trap .37 caught in its own harness.
    """
    empty = tmp_path / "empty-path"
    empty.mkdir(exist_ok=True)
    return str(empty)


def _path_with_unexecutable_git(tmp_path: Path) -> str:
    """A ``PATH`` whose only ``git`` cannot be executed — a ``PermissionError``.

    This is the case that separates ``except OSError`` from ``except
    FileNotFoundError``: a sabotage narrowing the handler back to the subclass
    survives every "git is missing" row, so without this one the widening would
    be untested (measured — the first version of these sabotages passed 5/5).
    """
    bindir = tmp_path / "unexecutable-path"
    bindir.mkdir(exist_ok=True)
    stub = bindir / "git"
    stub.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    stub.chmod(0o644)
    return str(bindir)


# ---------------------------------------------------------------- 1. sync-check


def _build_since_project(tmp_path: Path) -> Path:
    """A repo with one baselined doc-code pair and one baseline commit.

    After this, ``HEAD`` is the baseline, the working tree is identical to it,
    and every honest answer to "did anything drift since HEAD?" is "no".

    The **code** carries the em dash and the **doc** is deliberately pure ASCII.
    The first version of this fixture put one in both, and the latin-1 row passed
    even unfixed: a misdecoded doc hash makes ``doc_changed`` true as well, and
    ``stale = code_drifted and not doc_changed`` cancels the lie out. A row that
    cannot fail is not a row (standing rule 5).
    """
    project = tmp_path / "proj"
    (project / ".beadloom" / "_graph").mkdir(parents=True)
    (project / ".beadloom" / "_graph" / "graph.yml").write_text(
        yaml.dump(
            {
                "nodes": [
                    {
                        "ref_id": "F1",
                        "kind": "feature",
                        "summary": f"Feature 1 {EM_DASH} with an em dash",
                        "docs": ["docs/spec.md"],
                    }
                ]
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    (project / "docs").mkdir()
    (project / "docs" / "spec.md").write_text(
        "## Spec\n\nDocuments handler(), the entry point.\n", encoding="utf-8"
    )
    (project / "src").mkdir()
    (project / "src" / "api.py").write_text(
        f'# beadloom:feature=F1\ndef handler():\n    """Handles {EM_DASH} things."""\n',
        encoding="utf-8",
    )

    _init_repo(project)
    _git(project, "add", "-A")
    _git(project, "commit", "-qm", "baseline")

    from beadloom.application.reindex import reindex
    from beadloom.doc_sync.engine import build_sync_state

    reindex(project)
    conn = open_db(project / ".beadloom" / "beadloom.db")
    for pair in build_sync_state(conn):
        conn.execute(
            "INSERT OR REPLACE INTO sync_state "
            "(doc_path, code_path, ref_id, code_hash_at_sync, doc_hash_at_sync, "
            "synced_at, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                pair.doc_path,
                pair.code_path,
                pair.ref_id,
                pair.code_hash,
                pair.doc_hash,
                "2025-01-01",
                "ok",
            ),
        )
    conn.commit()
    conn.close()
    return project


class TestSyncCheckSinceIsNotAmbient:
    """``sync-check --since`` runs inside ``beadloom ci``; its answer is the Gate's."""

    @pytest.mark.parametrize("ambient", AMBIENT_CODECS)
    def test_an_unchanged_pair_is_ok_under_every_ambient_codec(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, ambient: str
    ) -> None:
        """MEASURED before the fix: latin-1 -> stale, ascii -> UnicodeDecodeError.

        Nothing changed between HEAD and the working tree, so "stale" is not a
        stricter answer — it is a wrong one, about a file nobody touched.
        """
        from beadloom.doc_sync import engine

        project = _build_since_project(tmp_path)
        under_ambient_codec(monkeypatch, engine, ambient)
        conn = open_db(project / ".beadloom" / "beadloom.db")
        results = check_sync_since(conn, project_root=project, since="HEAD")
        conn.close()

        assert results, "fixture produced no pairs — the test would be vacuous"
        assert all(r["status"] == "ok" for r in results), (ambient, results)

    def test_a_source_file_that_is_not_utf8_does_not_crash_the_gate(
        self, tmp_path: Path
    ) -> None:
        """Real git, real bytes, this machine's own UTF-8 locale — no double.

        The working-tree side read with ``read_text(encoding="utf-8")`` and the
        default ``errors="strict"``, so one latin-1 byte in one source file made
        ``sync-check`` raise ``UnicodeDecodeError`` — before ``--since`` was even
        involved, and equally in ``mark_synced``. Both sides now round-trip the
        bytes instead, so the pair still has an answer.

        The bad byte is introduced *after* ``reindex`` and amended into the
        baseline commit deliberately: ``context_oracle/code_indexer.py`` reads
        sources with the same strict rule and raises during indexing, which is a
        real defect of the same family and belongs to .42's sweep — building it
        into the fixture would test that call site instead of this one.
        """
        project = _build_since_project(tmp_path)
        (project / "src" / "api.py").write_bytes(
            b"# beadloom:feature=F1\n# caf\xe9\ndef handler():\n    pass\n"
        )
        _git(project, "commit", "-qam", "baseline with a latin-1 byte", "--amend")

        conn = open_db(project / ".beadloom" / "beadloom.db")
        mark_synced(conn, "spec.md", "src/api.py", project)
        since_results = check_sync_since(conn, project_root=project, since="HEAD")
        plain_results = check_sync(conn, project_root=project)
        conn.close()

        assert since_results, "fixture produced no pairs — the test would be vacuous"
        assert all(r["status"] == "ok" for r in since_results), since_results
        code_rows = [r for r in plain_results if r["code_path"]]
        assert code_rows, "fixture produced no code pairs"
        assert all(r["status"] == "ok" for r in code_rows), plain_results

    def test_a_missing_git_is_an_invalid_ref_not_a_traceback(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A handler as wide as the call: ``git`` absent is an ``OSError``."""
        from beadloom.doc_sync.engine import _validate_git_ref

        project = _build_since_project(tmp_path)
        monkeypatch.setenv("PATH", _path_without_git(tmp_path))
        assert _validate_git_ref(project, "HEAD") is False


# --------------------------------------------------------------------- 2. diff


def _build_diff_project(tmp_path: Path) -> Path:
    project = tmp_path / "diffproj"
    (project / ".beadloom" / "_graph").mkdir(parents=True)
    (project / ".beadloom" / "_graph" / "graph.yml").write_text(
        yaml.dump(
            {
                "nodes": [
                    {
                        "ref_id": "D1",
                        "kind": "domain",
                        "summary": f"Domain one {EM_DASH} summarised",
                        "source": "src/",
                    },
                    {"ref_id": "D2", "kind": "domain", "summary": "Domain two"},
                ],
                "edges": [{"src": "D1", "dst": "D2", "kind": "uses"}],
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    _init_repo(project)
    _git(project, "add", "-A")
    _git(project, "commit", "-qm", "baseline")
    return project


class TestGraphDiffIsNotAmbient:
    """``diff --since`` is the review role's instrument; a fabricated diff is a lie."""

    @pytest.mark.parametrize("ambient", AMBIENT_CODECS)
    def test_an_unchanged_graph_has_no_changes_under_every_ambient_codec(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, ambient: str
    ) -> None:
        """MEASURED before the fix on this repo: latin-1 -> yaml ReaderError,
        ascii -> UnicodeDecodeError, both uncaught out of ``beadloom diff``."""
        project = _build_diff_project(tmp_path)
        under_ambient_codec(monkeypatch, graph_diff, ambient)

        result = compute_diff(project, since="HEAD")

        assert not result.has_changes, (ambient, result.nodes, result.edges)

    def test_graph_yaml_that_is_not_utf8_is_a_stated_error(self, tmp_path: Path) -> None:
        """The honest answer is a refusal that names the file, not a diff.

        YAML is UTF-8 by definition, so a byte that is not UTF-8 is not a graph
        this can compare; the one thing it must never do is report the whole
        graph as "added" because one side failed to decode. ``compute_diff``
        already documents ``ValueError``, and the CLI turns it into exit 1.
        """
        project = _build_diff_project(tmp_path)
        (project / ".beadloom" / "_graph" / "graph.yml").write_bytes(
            b"nodes:\n  - ref_id: D1\n    kind: domain\n    summary: caf\xe9\n"
        )

        with pytest.raises(ValueError, match=r"graph\.yml") as excinfo:
            compute_diff(project, since="HEAD")
        assert "utf-8" in str(excinfo.value).lower()

    def test_graph_yaml_that_is_not_utf8_at_the_ref_is_a_stated_error(
        self, tmp_path: Path
    ) -> None:
        """The same refusal from the *other* side of the comparison.

        Kept separate from the working-tree row because they are decoded by two
        different calls: a sabotage that decoded the at-ref bytes with a bare
        ``.decode()`` passed the disk-side row untouched (measured), since the
        message it raises names no file.
        """
        project = _build_diff_project(tmp_path)
        graph_yml = project / ".beadloom" / "_graph" / "graph.yml"
        good = graph_yml.read_bytes()
        graph_yml.write_bytes(b"nodes:\n  - ref_id: D1\n    kind: domain\n    summary: caf\xe9\n")
        _git(project, "commit", "-qam", "a graph that is not utf-8", "--amend")
        graph_yml.write_bytes(good)  # the working-tree side is clean

        with pytest.raises(ValueError, match=r"HEAD:\.beadloom/_graph/graph\.yml"):
            compute_diff(project, since="HEAD")

    def test_a_missing_git_is_an_invalid_ref_not_a_traceback(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        project = _build_diff_project(tmp_path)
        monkeypatch.setenv("PATH", _path_without_git(tmp_path))

        with pytest.raises(ValueError, match="Invalid git ref"):
            compute_diff(project, since="HEAD")


# ----------------------------------------------------------- 3. git contributors


def _build_activity_repo(tmp_path: Path, author: str) -> Path:
    repo = tmp_path / "activity"
    (repo / "src").mkdir(parents=True)
    _init_repo(repo)
    (repo / "src" / "a.py").write_text("x = 1\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(
        repo,
        "commit",
        "-qm",
        "c1",
        env={**os.environ, "GIT_AUTHOR_NAME": author, "GIT_AUTHOR_EMAIL": "a@a.a"},
    )
    return repo


def _commit_with_raw_author(repo: Path, author_bytes: bytes, marker: str) -> None:
    """Add a commit whose author name is *not* valid UTF-8, on top of ``main``.

    ``git commit`` re-encodes an ident taken from the environment (MEASURED:
    ``GIT_AUTHOR_NAME`` carrying byte 0xff came back out as ``0xc3 0xbf``), so
    the object is written directly with ``hash-object --literally`` — the object
    store, not the porcelain, is what ``git log`` prints from.

    The timestamp is *now* because ``analyze_git_activity`` asks git for
    ``--since=90 days ago``: a fixed epoch produced an empty log and a test that
    could not have failed for the reason it names.
    """
    parent = _git(repo, "rev-parse", "HEAD").stdout.decode().strip()
    (repo / "src" / f"{marker}.py").write_text("y = 2\n", encoding="utf-8")
    _git(repo, "add", "-A")
    tree = _git(repo, "write-tree").stdout.decode().strip()
    when = f"{int(time.time())} +0000".encode()
    body = (
        b"tree " + tree.encode() + b"\n"
        b"parent " + parent.encode() + b"\n"
        b"author " + author_bytes + b" <a@a.a> " + when + b"\n"
        b"committer " + author_bytes + b" <a@a.a> " + when + b"\n"
        b"\n" + marker.encode() + b"\n"
    )
    sha = (
        _git(repo, "hash-object", "-w", "-t", "commit", "--stdin", "--literally", input=body)
        .stdout.decode()
        .strip()
    )
    _git(repo, "update-ref", "refs/heads/main", sha)


class TestContributorNamesAreNotAmbient:
    """A mojibake contributor is shown in the dashboard as a real person."""

    @pytest.mark.parametrize("ambient", AMBIENT_CODECS)
    def test_a_non_ascii_author_reads_the_same_under_every_ambient_codec(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, ambient: str
    ) -> None:
        """MEASURED before the fix: latin-1 -> 'Ð\\x98Ð²Ð°Ð½ Ð\\x9fÐµÑ\\x82Ñ\\x80Ð¾Ð²',
        ascii -> UnicodeDecodeError past ``except (OSError, SubprocessError)``."""
        repo = _build_activity_repo(tmp_path, as_the_process_receives("Иван Петров"))
        under_ambient_codec(monkeypatch, git_activity, ambient)

        activities = git_activity.analyze_git_activity(repo, {"N": "src"})

        assert activities["N"].top_contributors == ["Иван Петров"], ambient

    def test_an_undecodable_author_neither_raises_nor_becomes_unstorable(
        self, tmp_path: Path
    ) -> None:
        """Real git, real bytes: byte 0xff in the author name of a real commit.

        Two properties, and the second is why ``errors="replace"`` was chosen
        over ``surrogateescape``: the name must survive the trip into the index.
        MEASURED: ``sqlite3`` encodes parameters as strict UTF-8, so a lone
        surrogate raises ``UnicodeEncodeError`` at
        ``reindex/enrichment.py``'s ``UPDATE nodes SET extra = ?`` — which would
        turn a *display* defect into a ``reindex`` crash inside ``beadloom ci``.
        """
        repo = _build_activity_repo(tmp_path, "Ada")
        _commit_with_raw_author(repo, b"Ivan" + UNDECODABLE, "one")

        activities = git_activity.analyze_git_activity(repo, {"N": "src"})

        names = activities["N"].top_contributors
        assert names, "no contributor was read at all"
        for name in names:
            name.encode("utf-8")  # must not raise: the value reaches sqlite3

    def test_the_stated_cost_two_undecodable_names_can_merge(self, tmp_path: Path) -> None:
        """The accepted, bounded cost of ``errors="replace"``, pinned so it is visible.

        ``replace`` is not injective, so two authors differing *only* in an
        undecodable byte render as one. That loss is confined to names that are
        already not valid UTF-8, and it never reaches a gate, a verdict or an
        exit code — unlike the ``surrogateescape`` alternative, which is
        injective but is not storable (see the test above). If someone switches
        the handler, this reddens and the storage question must be answered
        again rather than rediscovered in CI.
        """
        repo = _build_activity_repo(tmp_path, "Ada")
        _commit_with_raw_author(repo, b"Ivan" + UNDECODABLE, "one")
        _commit_with_raw_author(repo, b"Ivan" + b"\xfe", "two")

        activities = git_activity.analyze_git_activity(repo, {"N": "src"})

        names = activities["N"].top_contributors
        assert "Ivan�" in names
        assert names.count("Ivan�") == 1, (
            "two authors that differ only in an undecodable byte render as one",
            names,
        )

    def test_a_missing_git_degrades_to_no_activity(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        repo = _build_activity_repo(tmp_path, "Ada")
        monkeypatch.setenv("PATH", _path_without_git(tmp_path))
        assert git_activity.analyze_git_activity(repo, {"N": "src"}) == {}


# ---------------------------------------------------------- 4. export provenance


class TestFederationProvenanceIsNotAmbient:
    """``None`` means "unknown HEAD" (#103). It must not also mean "we misread a path".

    What the ambient rows prove after BDL-061.42, stated because it changed:
    ``export`` now reads git as BYTES and decodes a *path* with ``os.fsdecode``,
    so the injected codec has nothing left to corrupt on this route and the rows
    can no longer fail by mis-decoding. They still bite for the defect they were
    written about — reintroducing ``text=True`` puts the ambient codec back in
    charge and reddens all three — and the row that can fail on its own evidence
    is the real-bytes one below, plus the same path under a genuinely non-UTF-8
    filesystem, which only the ``tests-locale`` legs can run. That combination is
    what caught .42's own defect: with the path decoded as UTF-8 and the
    filesystem's codec ASCII, ``Path(toplevel).resolve()`` raised
    ``UnicodeEncodeError`` out of ``beadloom export``.
    """

    @pytest.mark.parametrize("ambient", AMBIENT_CODECS)
    def test_the_head_sha_survives_a_non_ascii_project_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, ambient: str
    ) -> None:
        """MEASURED before the fix, repo at ``.../проект``: latin-1 -> None,
        ascii -> UnicodeDecodeError.

        The mechanism is the comparison in ``_is_git_toplevel``: ``git rev-parse
        --show-toplevel`` prints a *path*, and a path misdecoded compares unequal
        to ``project_root``, so the export takes the honest-unknown branch for a
        dishonest reason and silently loses its provenance.
        """
        repo = tmp_path / as_the_process_receives("проект")
        _init_repo(repo)
        (repo / "a.txt").write_text("x\n", encoding="utf-8")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-qm", "c1")
        expected = _git(repo, "rev-parse", "HEAD").stdout.decode().strip()

        under_ambient_codec(monkeypatch, federation_export, ambient)

        assert federation_export.current_commit_sha(repo) == expected, ambient

    def test_an_undecodable_remote_url_yields_a_name_not_a_crash(
        self, tmp_path: Path
    ) -> None:
        """Real git, real bytes: ``errors="surrogateescape"`` round-trips exactly.

        Here the round-trip is the point — every value ``_run_git`` returns is
        either ASCII or compared against a filesystem path, and surrogateescape
        is ``os.fsdecode``'s own rule, so both sides of that comparison are
        decoded by the same rule by construction.
        """
        repo = tmp_path / "remoted"
        _init_repo(repo)
        _git(repo, "remote", "add", "origin", "git@example.com:team/repo\udcff.git")

        name = federation_export._repo_from_git_remote(repo)

        assert name is not None
        assert name.encode("utf-8", "surrogateescape") == b"repo" + UNDECODABLE

    def test_a_missing_git_is_an_unknown_head(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The handler that enumerated ``(FileNotFoundError, OSError)`` — a
        redundancy .37 read as the tell — still answers "unknown"."""
        repo = tmp_path / "gone"
        _init_repo(repo)
        monkeypatch.setenv("PATH", _path_without_git(tmp_path))
        assert federation_export.current_commit_sha(repo) is None

    def test_a_git_that_cannot_be_executed_is_an_unknown_head(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """``PermissionError`` is an ``OSError`` and not a ``FileNotFoundError``.

        The redundant enumeration was not only redundant: it was *narrow in the
        direction that matters*, and only this row says so.
        """
        repo = tmp_path / "unexecutable"
        _init_repo(repo)
        monkeypatch.setenv("PATH", _path_with_unexecutable_git(tmp_path))
        assert federation_export.current_commit_sha(repo) is None
