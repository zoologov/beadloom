"""``docs site`` writes the portal scaffold, and never over a file that is not its own.

BDL-076 B1 (``beadloom-dfwt``). The theme, the viewer, ``package.json``, the
lockfile, the VitePress config and the browser tests ship in the wheel, and
``docs site`` writes them next to the generated content. The output directory
is the adopter's, so the writer has to tell its own files from theirs:

- every file it writes carries one marker line, naming the version that wrote it
  and the SHA-256 of the rest of the file;
- a file whose marker is intact is rewritten whenever the shipped body differs —
  an upgrade is the common case, an editable install the other;
- a file with no marker, or whose body no longer matches its marker, is never
  overwritten, and is reported with where the change belongs;
- a file the installed version no longer ships is removed, when its marker is
  intact, so a spec retired upstream does not keep running;
- ``.beadloom/site/`` is copied last, so an adopter changes the portal without
  editing a generated file.

The shipped scaffold is replaced here by a small directory, so each rule is seen
on files whose content the test chose.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from beadloom.application.site.scaffold import (
    MARKABLE_SUFFIXES,
    ScaffoldError,
    ScaffoldReport,
    mark,
    read_marker,
    write_scaffold,
)

if TYPE_CHECKING:
    from pathlib import Path

_V1 = "7.0.0"
_V2 = "7.1.0"

_SHIPPED = {
    ".vitepress/config.mjs": "export default { title: site.title };\n",
    ".vitepress/theme/app/index.js": "export const app = 1;\n",
    ".vitepress/theme/widgets/Panel.vue": "<template><div /></template>\n",
    ".vitepress/theme/shared/ui/panel.css": ".panel { color: red; }\n",
    "package.json": '{\n  "name": "portal",\n  "engines": { "node": ">=20" }\n}\n',
    "e2e/viewer.spec.js": "test('x', () => {});\n",
}


def _ship(root: Path, files: dict[str, str]) -> Path:
    for rel, body in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    return root


@pytest.fixture()
def shipped(tmp_path: Path) -> Path:
    return _ship(tmp_path / "shipped", _SHIPPED)


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    root = tmp_path / "shop"
    (root / ".beadloom").mkdir(parents=True)
    return root


def _write(project: Path, source: Path, version: str = _V1) -> ScaffoldReport:
    return write_scaffold(project / "site", project_root=project, version=version, source=source)


# --- the marker ------------------------------------------------------------------


@pytest.mark.parametrize("rel", sorted(_SHIPPED))
def test_a_marked_file_gives_back_its_version_and_its_body(rel: str) -> None:
    body = _SHIPPED[rel]
    marker = read_marker(mark(rel, body, _V1))
    assert marker is not None
    assert (marker.version, marker.body, marker.intact) == (_V1, body, True)


def test_a_marked_json_file_is_still_json() -> None:
    marked = mark("package.json", _SHIPPED["package.json"], _V1)
    assert json.loads(marked)["engines"] == {"node": ">=20"}


def test_a_marked_file_names_where_a_change_belongs() -> None:
    marked = mark(".vitepress/theme/app/index.js", "export const a = 1;\n", _V1)
    assert ".beadloom/site/.vitepress/theme/app/index.js" in marked.splitlines()[0]


def test_an_edit_below_the_marker_breaks_it() -> None:
    marked = mark("e2e/viewer.spec.js", "test('x', () => {});\n", _V1)
    marker = read_marker(marked + "// mine\n")
    assert marker is not None
    assert marker.intact is False


def test_a_file_without_the_marker_has_none() -> None:
    assert read_marker("export const a = 1;\n") is None


def test_a_suffix_that_cannot_hold_a_marker_is_refused() -> None:
    assert ".svg" not in MARKABLE_SUFFIXES
    with pytest.raises(ScaffoldError):
        mark("logo.svg", "<svg/>", _V1)


# --- the first run -----------------------------------------------------------------


def test_the_first_run_writes_every_shipped_file_marked(project: Path, shipped: Path) -> None:
    report = _write(project, shipped)
    assert sorted(report.written) == sorted(_SHIPPED)
    for rel, body in _SHIPPED.items():
        marker = read_marker((project / "site" / rel).read_text(encoding="utf-8"))
        assert marker is not None
        assert (marker.version, marker.body, marker.intact) == (_V1, body, True)
    assert report.kept == ()


def test_a_second_run_on_the_same_version_changes_nothing(project: Path, shipped: Path) -> None:
    _write(project, shipped)
    before = {rel: (project / "site" / rel).stat().st_mtime_ns for rel in _SHIPPED}
    report = _write(project, shipped)
    assert sorted(report.unchanged) == sorted(_SHIPPED)
    assert (report.written, report.updated, report.kept, report.retired) == ((), (), (), ())
    after = {rel: (project / "site" / rel).stat().st_mtime_ns for rel in _SHIPPED}
    assert before == after


# --- an upgrade ------------------------------------------------------------------------


def test_an_upgrade_rewrites_every_file_beadloom_wrote(project: Path, shipped: Path) -> None:
    _write(project, shipped)
    (shipped / "e2e/viewer.spec.js").write_text("test('y', () => {});\n", encoding="utf-8")
    report = _write(project, shipped, version=_V2)
    assert sorted(report.updated) == sorted(_SHIPPED)
    spec = read_marker((project / "site/e2e/viewer.spec.js").read_text(encoding="utf-8"))
    assert spec is not None
    assert (spec.version, spec.body) == (_V2, "test('y', () => {});\n")


def test_a_changed_body_on_the_same_version_is_rewritten(project: Path, shipped: Path) -> None:
    """An editable install changes the shipped body without changing the version."""
    _write(project, shipped)
    (shipped / ".vitepress/theme/app/index.js").write_text("export const app = 2;\n", "utf-8")
    report = _write(project, shipped)
    assert report.updated == (".vitepress/theme/app/index.js",)


def test_a_file_the_new_version_no_longer_ships_is_retired(project: Path, shipped: Path) -> None:
    _write(project, shipped)
    (shipped / "e2e/viewer.spec.js").unlink()
    report = _write(project, shipped, version=_V2)
    assert report.retired == ("e2e/viewer.spec.js",)
    assert not (project / "site/e2e/viewer.spec.js").exists()


def test_a_retired_path_that_was_edited_by_hand_is_left_alone(
    project: Path, shipped: Path
) -> None:
    _write(project, shipped)
    spec = project / "site/e2e/viewer.spec.js"
    spec.write_text(spec.read_text(encoding="utf-8") + "// mine\n", encoding="utf-8")
    (shipped / "e2e/viewer.spec.js").unlink()
    report = _write(project, shipped, version=_V2)
    assert report.retired == ()
    assert spec.exists()


def test_generated_content_is_never_retired(project: Path, shipped: Path) -> None:
    """The content ``docs site`` writes each run carries no marker and is not the scaffold's."""
    data = project / "site/public/architecture.data.json"
    data.parent.mkdir(parents=True)
    data.write_text('{"schema_version": 2}\n', encoding="utf-8")
    report = _write(project, shipped)
    assert report.retired == ()
    assert data.exists()


# --- a file that is not beadloom's --------------------------------------------------


def test_a_hand_edited_file_is_kept_and_reported(project: Path, shipped: Path) -> None:
    _write(project, shipped)
    config = project / "site/.vitepress/config.mjs"
    edited = config.read_text(encoding="utf-8").replace("site.title", "'Mine'")
    config.write_text(edited, encoding="utf-8")
    report = _write(project, shipped, version=_V2)
    assert config.read_text(encoding="utf-8") == edited
    assert [kept.path for kept in report.kept] == [".vitepress/config.mjs"]
    kept = report.kept[0]
    assert "by hand" in kept.reason
    assert ".beadloom/site/.vitepress/config.mjs" in kept.remediation
    assert ".vitepress/config.mjs" not in report.updated


def test_a_file_without_the_marker_is_never_overwritten(project: Path, shipped: Path) -> None:
    ours = project / "site/package.json"
    ours.parent.mkdir(parents=True)
    ours.write_text('{ "name": "our-own-portal" }\n', encoding="utf-8")
    report = _write(project, shipped)
    assert ours.read_text(encoding="utf-8") == '{ "name": "our-own-portal" }\n'
    assert [kept.path for kept in report.kept] == ["package.json"]
    assert "marker" in report.kept[0].reason
    assert "package.json" not in report.written


# --- the override directory ------------------------------------------------------


def test_the_override_directory_is_copied_last(project: Path, shipped: Path) -> None:
    overrides = project / ".beadloom/site"
    _ship(
        overrides,
        {
            ".vitepress/theme/shared/ui/panel.css": ".panel { color: teal; }\n",
            "guide.md": "# Our guide\n",
        },
    )
    report = _write(project, shipped)
    site = project / "site"
    css = site / ".vitepress/theme/shared/ui/panel.css"
    assert css.read_text(encoding="utf-8") == ".panel { color: teal; }\n"
    assert (site / "guide.md").read_text(encoding="utf-8") == "# Our guide\n"
    assert sorted(report.overridden) == [".vitepress/theme/shared/ui/panel.css", "guide.md"]
    assert ".vitepress/theme/shared/ui/panel.css" not in report.written
    # A second run copies the override again and reports nothing kept: the file
    # the override wrote carries no marker, and it is not the scaffold's to judge.
    again = _write(project, shipped)
    assert again.kept == ()
    assert css.read_text(encoding="utf-8") == ".panel { color: teal; }\n"


def test_a_file_shipped_again_after_its_override_is_removed_replaces_the_copy(
    project: Path, shipped: Path
) -> None:
    overrides = project / ".beadloom/site"
    _ship(overrides, {".vitepress/theme/app/index.js": "export const app = 'ours';\n"})
    _write(project, shipped)
    (overrides / ".vitepress/theme/app/index.js").unlink()
    report = _write(project, shipped)
    # The copy the override left carries no marker, so it is kept and reported
    # rather than replaced: nothing distinguishes it from a file written by hand.
    assert [kept.path for kept in report.kept] == [".vitepress/theme/app/index.js"]


# --- the shipped tree ----------------------------------------------------------------


def test_build_output_and_dependencies_are_never_shipped(project: Path, shipped: Path) -> None:
    _ship(
        shipped,
        {
            "node_modules/vue/index.js": "export {};\n",
            ".vitepress/cache/deps/x.js": "export {};\n",
            ".vitepress/dist/index.html": "<html></html>\n",
        },
    )
    report = _write(project, shipped)
    excluded = ("node_modules/", ".vitepress/cache/", ".vitepress/dist/")
    assert not any(rel.startswith(excluded) for rel in report.written)
