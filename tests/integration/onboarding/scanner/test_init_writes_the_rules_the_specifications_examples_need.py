"""``init`` on the specification's examples writes what they need to lint as it reads them.

BDL-082 S2a (RFC D2, D5; PRD goals 2 and 5). The acceptance scenarios of
``init_reads_slice_groups_and_pages_first.feature`` hold the group and pages-first cases; these
hold what only the whole path shows: the public-API rule ``init`` writes judges the segments of
``shared`` (S1T measured goal 5 holding for the rule until ``init`` tagged it with
``fsd-shared`` and ``fsd-app``), code at a group's top reaches the shape rule because the
group has no node, and the ``--bootstrap`` branch names the code it could not read.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

from beadloom.context_oracle import code_indexer
from beadloom.services.cli import main
from tests.support.fsd_spec_examples import GROUP, write_example

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping
    from pathlib import Path

#: ``/docs/reference/public-api``: a segment of ``shared`` is entered through its index, and in
#: ``shared/ui`` through a per-component index as well.
_SHARED: Mapping[str, str] = {
    **GROUP,
    "src/shared/api/index.ts": "export { http } from './http'\n",
    "src/shared/api/http.ts": "export const http = 1\n",
    "src/shared/ui/button/index.ts": "export { Button } from './Button'\n",
    "src/shared/ui/button/Button.ts": "export const Button = 1\n",
    "src/pages/home/ui/home.ts": (
        "import { form } from '@/features/auth/login'\n"
        "import { http } from '@/shared/api/http'\n"
        "import { Button } from '@/shared/ui/button'\n"
        "export function home() { return [form, http, Button] }\n"
    ),
}


def _init(root: Path, flag: str = "--yes") -> tuple[int, str]:
    result = CliRunner().invoke(main, ["init", flag, "--project", str(root)])
    assert result.exception is None or isinstance(result.exception, SystemExit), result.output
    return result.exit_code, result.output


def _findings(root: Path) -> list[tuple[str, str | None, int | None, str | None]]:
    """``lint --strict``'s findings of the ``fsd-*`` rules: rule, file, line, unit reached."""
    result = CliRunner().invoke(
        main, ["lint", "--strict", "--format", "json", "--project", str(root)]
    )
    return [
        (str(v["rule_name"]), v.get("file_path"), v.get("line_number"), v.get("to_ref_id"))
        for v in json.loads(result.stdout)["violations"]
        if str(v["rule_name"]).startswith("fsd-")
        and v["rule_type"] not in {"rule_liveness", "layer_declaration", "layer_population"}
    ]


def test_an_import_past_a_shared_segments_index_is_a_finding_after_init(tmp_path: Path) -> None:
    pytest.importorskip("tree_sitter_typescript")
    root = write_example(tmp_path / "probe", _SHARED)
    _init(root)

    found = _findings(root)

    # The sidestep into `shared/api` (line 2) is reported; the per-component index of
    # `shared/ui` (line 3) is an entry, not a sidestep, and the slice of the group (line 1)
    # is entered through its own index.
    assert [f for f in found if f[0] == "fsd-public-api"] == [
        ("fsd-public-api", "src/pages/home/ui/home.ts", 2, "shared-api")
    ]


def test_code_at_a_groups_top_is_left_to_the_shape_rule(tmp_path: Path) -> None:
    pytest.importorskip("tree_sitter_typescript")
    root = write_example(
        tmp_path / "probe", {**GROUP, "src/features/auth/shared.ts": "export const s = 1\n"}
    )
    _init(root)

    found = _findings(root)

    assert ("fsd-slice-shape", "src/features/auth/shared.ts", None, None) in found


@pytest.fixture
def without_typescript(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    real = code_indexer.get_lang_config
    code_indexer.clear_cache()
    monkeypatch.setattr(
        code_indexer,
        "get_lang_config",
        lambda ext: None if ext in {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"} else real(ext),
    )
    yield
    code_indexer.clear_cache()


@pytest.mark.usefixtures("without_typescript")
def test_the_bootstrap_branch_names_the_code_it_could_not_read(tmp_path: Path) -> None:
    root = write_example(tmp_path / "probe", GROUP)

    code, output = _init(root, "--bootstrap")

    assert "⚠ 8 TypeScript files, no parser installed — install beadloom[languages]" in (output)
    # Information, not a verdict: with no import read, the rules find nothing to report.
    assert code == 0, output


def test_a_project_whose_code_is_all_read_prints_no_such_line(tmp_path: Path) -> None:
    pytest.importorskip("tree_sitter_typescript")
    root = write_example(tmp_path / "probe", GROUP)

    _, output = _init(root)

    assert "no parser installed" not in output
