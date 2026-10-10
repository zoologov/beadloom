"""The ``imports:`` block of ``.beadloom/config.yml``: the aliases a project declares.

BDL-080 S3a (``beadloom-cwzc``), RFC D5 (b). A project declares what its bundler maps
and no tsconfig carries — Babel ``module-resolver``, Vite ``resolve.alias`` — as
``imports: {aliases: {"@shared": src/shared}}``. A key the block does not read, an alias
that is a pattern, and a folder that is not in the project are each refused by name: a
mistyped folder would otherwise leave every import under that alias unresolved without a
word.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.application.import_aliases import import_aliases, read_import_aliases

if TYPE_CHECKING:
    from pathlib import Path


def _project(tmp_path: Path, config: str | None, folders: tuple[str, ...] = ()) -> Path:
    (tmp_path / ".beadloom").mkdir()
    for folder in folders:
        (tmp_path / folder).mkdir(parents=True)
    if config is not None:
        (tmp_path / ".beadloom" / "config.yml").write_text(config, encoding="utf-8")
    return tmp_path


def test_no_config_declares_no_alias_and_refuses_nothing(tmp_path: Path) -> None:
    assert read_import_aliases(_project(tmp_path, None)) == ((), ())


def test_no_imports_block_declares_no_alias(tmp_path: Path) -> None:
    assert read_import_aliases(_project(tmp_path, "scan_paths: [src]\n")) == ((), ())


def test_an_empty_block_declares_no_alias(tmp_path: Path) -> None:
    assert read_import_aliases(_project(tmp_path, "imports:\n")) == ((), ())


def test_the_declared_aliases_are_read_as_folder_pairs(tmp_path: Path) -> None:
    root = _project(
        tmp_path,
        "imports:\n  aliases:\n    '@shared': ./src/shared\n    '~': src\n    '@root': .\n",
        folders=("src/shared",),
    )
    assert read_import_aliases(root) == (
        (("@shared", "src/shared"), ("~", "src"), ("@root", "")),
        (),
    )
    assert import_aliases(root) == (("@shared", "src/shared"), ("~", "src"), ("@root", ""))


def test_an_alias_written_with_a_trailing_slash_is_the_alias_without_it(
    tmp_path: Path,
) -> None:
    root = _project(tmp_path, "imports:\n  aliases:\n    '@/': src\n", folders=("src",))
    assert read_import_aliases(root) == ((("@", "src"),), ())


def test_an_alias_may_name_a_file(tmp_path: Path) -> None:
    root = _project(tmp_path, "imports:\n  aliases:\n    'env': src/env.ts\n", folders=("src",))
    (root / "src" / "env.ts").write_text("export {}\n", encoding="utf-8")
    assert read_import_aliases(root) == ((("env", "src/env.ts"),), ())


def test_an_unknown_key_is_refused_by_name_with_the_keys_the_block_reads(
    tmp_path: Path,
) -> None:
    aliases, refusals = read_import_aliases(_project(tmp_path, "imports:\n  alias: {}\n"))
    assert aliases == ()
    assert [refusal.where for refusal in refusals] == ["imports.alias"]
    assert "`aliases:`" in refusals[0].why


@pytest.mark.parametrize("block", ["imports: '@'\n", "imports:\n  aliases: [src]\n"])
def test_a_block_or_an_aliases_that_is_not_a_mapping_is_refused(
    tmp_path: Path, block: str
) -> None:
    aliases, refusals = read_import_aliases(_project(tmp_path, block))
    assert aliases == ()
    assert len(refusals) == 1
    assert "not a mapping" in refusals[0].why


@pytest.mark.parametrize(
    ("entry", "said"),
    [
        ("'@/*': src", "a pattern"),
        ("'./x': src", "relative"),
        ("'@shared': ''", "an empty string"),
        ("'@shared': 3", "a number"),
        ("'@shared': '../outside'", "outside the project"),
        ("'@shared': /abs/src", "outside the project"),
        ("'@shared': src/missing", "names nothing"),
        ("'@shared': src/*", "a pattern"),
    ],
)
def test_an_unusable_entry_is_refused_by_its_alias_and_the_usable_ones_are_kept(
    tmp_path: Path, entry: str, said: str
) -> None:
    root = _project(
        tmp_path, f"imports:\n  aliases:\n    '~': src\n    {entry}\n", folders=("src",)
    )
    aliases, refusals = read_import_aliases(root)
    assert aliases == (("~", "src"),)
    assert len(refusals) == 1
    assert refusals[0].where.startswith("imports.aliases.")
    assert said in refusals[0].why


def test_an_unreadable_config_is_one_refusal_and_no_alias(tmp_path: Path) -> None:
    aliases, refusals = read_import_aliases(_project(tmp_path, "imports: [\n"))
    assert aliases == ()
    assert [refusal.where for refusal in refusals] == [".beadloom/config.yml"]
