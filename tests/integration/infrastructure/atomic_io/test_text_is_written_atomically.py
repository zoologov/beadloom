"""``write_text_atomic`` commits a text whole or not at all (BDL-080 S3c).

The FSD rules ``init`` writes carry comments, which ``yaml.dump`` cannot write, so they
are written as text through the same commit discipline as ``write_yaml_atomic``: a temp
file in the target's folder, ``fsync``, one rename.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from beadloom.infrastructure.atomic_io import write_text_atomic


def test_the_text_is_written_as_given(tmp_path: Path) -> None:
    target = tmp_path / "rules.yml"

    write_text_atomic(target, "# why\nversion: 3\n")

    assert target.read_text(encoding="utf-8") == "# why\nversion: 3\n"
    assert [p.name for p in tmp_path.iterdir()] == ["rules.yml"]


def test_a_failed_commit_leaves_the_prior_file_and_no_temp_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "rules.yml"
    target.write_text("prior\n", encoding="utf-8")

    def _boom(self: Path, other: Path) -> Path:
        raise OSError("disk full")

    monkeypatch.setattr(Path, "replace", _boom)

    with pytest.raises(OSError, match="disk full"):
        write_text_atomic(target, "new\n")

    assert target.read_text(encoding="utf-8") == "prior\n"
    assert [p.name for p in tmp_path.iterdir()] == ["rules.yml"]
