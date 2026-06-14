"""Tests for symbol-level scope narrowing (BDL-052 S4 / Thread C).

`narrow_by_changed_symbols` narrows the tech-writer's stale set from
"changed FILE -> all its doc pairs" to "doc references a CHANGED SYMBOL",
killing the god-file fan-out. Pure helpers (no subprocess) are unit-tested
directly; the wired path patches the git/sync-update seams (no network).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.ai_agents.ai_techwriter import scope, symbol_scope
from beadloom.ai_agents.ai_techwriter.models import DriftItem
from beadloom.ai_agents.ai_techwriter.symbol_scope import (
    changed_symbols,
    doc_referenced_symbols,
    narrow_by_changed_symbols,
    python_symbol_ranges,
)

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


# --------------------------------------------------------------------------- #
# python_symbol_ranges (pure)
# --------------------------------------------------------------------------- #


def test_symbol_ranges_top_level_def_and_class() -> None:
    src = (
        "import os\n"  # 1
        "\n"  # 2
        "def alpha():\n"  # 3
        "    return 1\n"  # 4
        "\n"  # 5
        "class Beta:\n"  # 6
        "    def method(self):\n"  # 7
        "        return 2\n"  # 8
        "\n"  # 9
        "def gamma():\n"  # 10
        "    return 3\n"  # 11
    )
    ranges = python_symbol_ranges(src)
    assert ranges["alpha"] == (3, 4)
    assert ranges["gamma"] == (10, 11)
    # The class spans its whole body (including the nested method lines).
    assert ranges["Beta"][0] == 6
    assert ranges["Beta"][1] >= 8


def test_symbol_ranges_empty_for_no_symbols() -> None:
    assert python_symbol_ranges("x = 1\ny = 2\n") == {}


# --------------------------------------------------------------------------- #
# changed_symbols (pure)
# --------------------------------------------------------------------------- #


def test_changed_symbols_one_edited_body() -> None:
    new = "def alpha():\n    return 1\n\ndef beta():\n    return 99\n"
    # Line 5 (beta's body) changed.
    assert changed_symbols(new_content=new, changed_lines={5}) == {"beta"}


def test_changed_symbols_multiple_hunks() -> None:
    new = "def alpha():\n    return 1\n\ndef beta():\n    return 2\n"
    assert changed_symbols(new_content=new, changed_lines={2, 5}) == {"alpha", "beta"}


def test_changed_symbols_change_outside_any_symbol_is_empty() -> None:
    new = "import os\n\ndef alpha():\n    return 1\n"
    # Line 1 (an import) changed -- no symbol body touched.
    assert changed_symbols(new_content=new, changed_lines={1}) == set()


def test_changed_symbols_no_content_returns_empty() -> None:
    assert changed_symbols(new_content=None, changed_lines={1}) == set()
    assert changed_symbols(new_content="def a():\n    return 1\n", changed_lines=set()) == set()


# --------------------------------------------------------------------------- #
# doc_referenced_symbols (pure)
# --------------------------------------------------------------------------- #


def test_doc_referenced_symbols_word_match() -> None:
    doc = "The `alpha` helper is described here. Also gamma.\n"
    refd = doc_referenced_symbols(doc, {"alpha", "beta", "gamma"})
    assert refd == {"alpha", "gamma"}


def test_doc_referenced_symbols_substring_does_not_match() -> None:
    # `alphabet` must NOT count as a reference to `alpha`.
    doc = "We discuss the alphabet only.\n"
    assert doc_referenced_symbols(doc, {"alpha"}) == set()


# --------------------------------------------------------------------------- #
# narrow_by_changed_symbols (wired; git seam patched)
# --------------------------------------------------------------------------- #


class _FakeGit:
    """Patchable stand-in for the git/file seams used by narrowing.

    ``files`` maps a code path -> (content_at_since, current_content,
    changed_line_numbers).
    """

    def __init__(self, files: dict[str, tuple[str | None, str | None, set[int]]]) -> None:
        self.files = files

    def show(self, project_root: Path, rel_path: str, ref: str) -> str | None:
        entry = self.files.get(rel_path)
        return entry[0] if entry else None

    def read(self, project_root: Path, rel_path: str) -> str | None:
        entry = self.files.get(rel_path)
        if entry is not None:
            return entry[1]
        # Not a registered code file (e.g. a doc) -> read from disk.
        target = project_root / rel_path
        return target.read_text(encoding="utf-8") if target.is_file() else None

    def changed_lines(self, project_root: Path, rel_path: str, since: str) -> set[int]:
        entry = self.files.get(rel_path)
        return entry[2] if entry else set()


def _patch_git(monkeypatch: pytest.MonkeyPatch, fake: _FakeGit) -> list[str]:
    """Patch the git/file seams + capture which refs got sync-update'd."""
    baselined: list[str] = []
    monkeypatch.setattr(symbol_scope, "git_file_at_ref", fake.show)
    monkeypatch.setattr(symbol_scope, "read_working_file", fake.read)
    monkeypatch.setattr(symbol_scope, "git_changed_line_numbers", fake.changed_lines)

    def fake_update(project_root: Path, ref_id: str) -> object:
        baselined.append(ref_id)

        class _R:
            ok = True

        return _R()

    monkeypatch.setattr(symbol_scope, "beadloom_sync_update", fake_update)
    return baselined


def _god_file_docs(n: int) -> list[DriftItem]:
    """n stale doc pairs all pointing at the same god-file `cli.py`."""
    return [
        DriftItem(
            ref_id=f"ref{i}",
            doc_path=f"docs/d{i}.md",
            reasons=("symbols_changed",),
            code_files=("src/cli.py",),
        )
        for i in range(n)
    ]


def _write_docs(project: Path, items: list[DriftItem], bodies: dict[str, str]) -> None:
    for item in items:
        target = project / item.doc_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(bodies.get(item.ref_id, ""), encoding="utf-8")


GOD_FILE_OLD = "def untouched():\n    return 2\n"
GOD_FILE_NEW = (
    "def added():\n    return 1\n\n"  # lines 1-2
    "def untouched():\n    return 2\n"  # lines 4-5
)


def test_god_file_one_symbol_narrows_to_one_doc(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    items = _god_file_docs(15)
    # Only ref0's doc references the changed symbol `added`; the rest mention
    # only `untouched` (which did not change).
    bodies = {"ref0": "Docs for `added`.\n"}
    for i in range(1, 15):
        bodies[f"ref{i}"] = "Docs for `untouched`.\n"
    _write_docs(tmp_path, items, bodies)

    fake = _FakeGit({"src/cli.py": (GOD_FILE_OLD, GOD_FILE_NEW, {1, 2})})  # body of `added`
    baselined = _patch_git(monkeypatch, fake)

    kept = narrow_by_changed_symbols(items, tmp_path, since="HEAD~1")

    assert [k.ref_id for k in kept] == ["ref0"]
    # The other 14 were deterministically baselined clean.
    assert set(baselined) == {f"ref{i}" for i in range(1, 15)}


def test_doc_referencing_changed_symbol_is_kept(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    items = _god_file_docs(1)
    _write_docs(tmp_path, items, {"ref0": "Docs for `added` symbol.\n"})
    fake = _FakeGit({"src/cli.py": (GOD_FILE_OLD, GOD_FILE_NEW, {1})})
    baselined = _patch_git(monkeypatch, fake)
    kept = narrow_by_changed_symbols(items, tmp_path, since="HEAD~1")
    assert [k.ref_id for k in kept] == ["ref0"]
    assert baselined == []


def test_conservative_fallback_no_since_keeps_all(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    items = _god_file_docs(3)
    _write_docs(tmp_path, items, {})
    fake = _FakeGit({"src/cli.py": (GOD_FILE_OLD, GOD_FILE_NEW, {1})})
    baselined = _patch_git(monkeypatch, fake)
    kept = narrow_by_changed_symbols(items, tmp_path, since=None)
    assert len(kept) == 3
    assert baselined == []


def test_conservative_fallback_non_attributable_reason_kept(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # untracked_files / missing_modules are not symbol-attributable -> keep.
    items = [
        DriftItem(
            ref_id="ref0",
            doc_path="docs/d0.md",
            reasons=("untracked_files",),
            code_files=("src/cli.py",),
        )
    ]
    _write_docs(tmp_path, items, {"ref0": "Docs for `untouched`.\n"})
    fake = _FakeGit({"src/cli.py": (GOD_FILE_OLD, GOD_FILE_NEW, {1})})
    baselined = _patch_git(monkeypatch, fake)
    kept = narrow_by_changed_symbols(items, tmp_path, since="HEAD~1")
    assert [k.ref_id for k in kept] == ["ref0"]
    assert baselined == []


def test_conservative_fallback_non_python_file_kept(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    items = [
        DriftItem(
            ref_id="ref0",
            doc_path="docs/d0.md",
            reasons=("hash_changed",),
            code_files=("src/config.yaml",),
        )
    ]
    _write_docs(tmp_path, items, {"ref0": "no symbols here\n"})
    fake = _FakeGit({"src/config.yaml": ("a: 1\n", "a: 2\n", {1})})
    baselined = _patch_git(monkeypatch, fake)
    kept = narrow_by_changed_symbols(items, tmp_path, since="HEAD~1")
    assert [k.ref_id for k in kept] == ["ref0"]
    assert baselined == []


def test_conservative_fallback_unattributable_change_kept(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A changed line that maps to no symbol body (e.g. an import) is ambiguous
    # attribution -> keep the pair (never under-refresh).
    items = _god_file_docs(1)
    _write_docs(tmp_path, items, {"ref0": "Docs for `untouched`.\n"})
    src = "import os\n\ndef untouched():\n    return 2\n"
    fake = _FakeGit({"src/cli.py": (None, src, {1})})  # line 1 = import
    baselined = _patch_git(monkeypatch, fake)
    kept = narrow_by_changed_symbols(items, tmp_path, since="HEAD~1")
    assert [k.ref_id for k in kept] == ["ref0"]
    assert baselined == []


# --------------------------------------------------------------------------- #
# discover_scope wiring (default-on when since is given)
# --------------------------------------------------------------------------- #


def test_discover_scope_applies_narrowing_when_since(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    items = _god_file_docs(2)
    bodies = {"ref0": "Docs for `added`.\n", "ref1": "Docs for `untouched`.\n"}
    _write_docs(tmp_path, items, bodies)
    report = {
        "pairs": [
            {
                "status": "stale",
                "ref_id": it.ref_id,
                "doc_path": it.doc_path,
                "code_path": "src/cli.py",
                "reason": "symbols_changed",
            }
            for it in items
        ]
    }
    monkeypatch.setattr(
        scope, "beadloom_sync_check_json", lambda project_root, *, since=None: report
    )
    fake = _FakeGit({"src/cli.py": (GOD_FILE_OLD, GOD_FILE_NEW, {1})})
    _patch_git(monkeypatch, fake)
    kept = scope.discover_scope(tmp_path, since="HEAD~1")
    assert [k.ref_id for k in kept] == ["ref0"]


def test_discover_scope_no_since_skips_narrowing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    items = _god_file_docs(2)
    report = {
        "pairs": [
            {
                "status": "stale",
                "ref_id": it.ref_id,
                "doc_path": it.doc_path,
                "code_path": "src/cli.py",
                "reason": "symbols_changed",
            }
            for it in items
        ]
    }
    monkeypatch.setattr(
        scope, "beadloom_sync_check_json", lambda project_root, *, since=None: report
    )
    kept = scope.discover_scope(tmp_path, since=None)
    assert [k.ref_id for k in kept] == ["ref0", "ref1"]
