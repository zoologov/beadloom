"""The ``activity:`` block of ``.beadloom/config.yml``: the patterns a project excludes.

BDL-078 ``beadloom-btkd.1``. A project adds its own generated files to the
built-in lock files: ``activity: {exclude: [...]}``. A key the block does not
read, or an entry that is not a pattern, is refused by name — a mistyped
``exlude:`` would otherwise count every generated line as work without a word.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.application.activity_settings import read_activity_exclusions

if TYPE_CHECKING:
    from pathlib import Path


def _project(tmp_path: Path, config: str | None) -> Path:
    (tmp_path / ".beadloom").mkdir()
    if config is not None:
        (tmp_path / ".beadloom" / "config.yml").write_text(config, encoding="utf-8")
    return tmp_path


def test_no_config_excludes_nothing_and_refuses_nothing(tmp_path: Path) -> None:
    assert read_activity_exclusions(_project(tmp_path, None)) == ((), ())


def test_no_activity_block_excludes_nothing(tmp_path: Path) -> None:
    assert read_activity_exclusions(_project(tmp_path, "scan_paths: [src]\n")) == ((), ())


def test_an_empty_block_excludes_nothing(tmp_path: Path) -> None:
    assert read_activity_exclusions(_project(tmp_path, "activity:\n")) == ((), ())


def test_the_declared_patterns_are_read_in_order(tmp_path: Path) -> None:
    root = _project(tmp_path, "activity:\n  exclude:\n    - '*.pb.go'\n    - 'web/dist/*'\n")
    assert read_activity_exclusions(root) == (("*.pb.go", "web/dist/*"), ())


def test_an_unknown_key_is_refused_by_name_with_the_keys_the_block_reads(
    tmp_path: Path,
) -> None:
    root = _project(tmp_path, "activity:\n  exlude:\n    - '*.pb.go'\n")
    patterns, refusals = read_activity_exclusions(root)
    assert patterns == ()
    assert [refusal.where for refusal in refusals] == ["activity.exlude"]
    assert "`exclude:`" in refusals[0].why


def test_a_block_that_is_not_a_mapping_is_refused(tmp_path: Path) -> None:
    patterns, refusals = read_activity_exclusions(_project(tmp_path, "activity: '*.lock'\n"))
    assert patterns == ()
    assert [refusal.where for refusal in refusals] == ["activity"]


def test_an_exclude_that_is_not_a_list_is_refused(tmp_path: Path) -> None:
    root = _project(tmp_path, "activity:\n  exclude: '*.pb.go'\n")
    patterns, refusals = read_activity_exclusions(root)
    assert patterns == ()
    assert [refusal.where for refusal in refusals] == ["activity.exclude"]
    assert "a string" in refusals[0].why


def test_an_entry_that_is_not_a_pattern_is_refused_and_the_rest_are_kept(
    tmp_path: Path,
) -> None:
    root = _project(tmp_path, "activity:\n  exclude:\n    - '*.pb.go'\n    - 7\n    - ''\n")
    patterns, refusals = read_activity_exclusions(root)
    assert patterns == ("*.pb.go",)
    assert [refusal.where for refusal in refusals] == [
        "activity.exclude[1]",
        "activity.exclude[2]",
    ]


def test_an_unreadable_config_is_refused_and_excludes_nothing(tmp_path: Path) -> None:
    patterns, refusals = read_activity_exclusions(_project(tmp_path, "activity: [\n"))
    assert patterns == ()
    assert len(refusals) == 1
