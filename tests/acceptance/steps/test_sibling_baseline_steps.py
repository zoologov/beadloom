"""Step implementations for the sibling-baseline suite (BDL-061 S6, #182 / #133).

Against the real reindex pipeline and the real CLI. The subject is what the
INDEX records across a rebuild, so a hand-built `sync_state` would prove the
fixture rather than the pipeline (FAKES PROVE FAKES).

The module is named ``test_*`` so default pytest collection picks the scenarios
up — the acceptance suite runs inside ``uv run pytest``, not beside it.
"""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from click.testing import CliRunner
from pytest_bdd import given, scenarios, then, when

from beadloom.application.reindex import reindex
from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../features/sibling_baseline.feature")

_FILES = ("alpha", "beta", "gamma")


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)  # noqa: S603, S607


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    """One node, one document, three annotated code files, freshly baselined."""
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
                        "docs": ["widgets.md"],
                    }
                ]
            }
        ),
    )
    modules = "\n".join(f"- `{name}.py` — what {name} does." for name in _FILES)
    _write(root, "docs/widgets.md", f"# widgets\n\n## Modules\n\n{modules}\n")
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
    return {"root": root, "result": None, "human": None}


def _change_symbols(root: Path, name: str) -> None:
    _write(
        root,
        f"src/widgets/{name}.py",
        f"# beadloom:domain=widgets\ndef {name}_renamed(extra):\n    return extra\n",
    )


def _run(world: dict[str, Any]) -> None:
    root = world["root"]
    world["result"] = CliRunner().invoke(
        main, ["sync-check", "--json", "--project", str(root)]
    )
    world["human"] = CliRunner().invoke(main, ["sync-check", "--project", str(root)])


def _pairs(world: dict[str, Any]) -> list[dict[str, Any]]:
    """The doc-code pairs only — the structural `incomplete` rows are a different
    population and carry no code file to attribute a verdict to."""
    return [p for p in json.loads(world["result"].stdout)["pairs"] if p["code_path"]]


@given("a document paired with three code files of one node")
def given_three_pairs(world: dict[str, Any]) -> None:
    _run(world)
    assert len(_pairs(world)) == len(_FILES)
    assert {p["status"] for p in _pairs(world)} == {"ok"}


@given("one of those code files has changed its symbols")
def given_one_changed(world: dict[str, Any]) -> None:
    _change_symbols(world["root"], "alpha")
    reindex(world["root"])


@when("the doc-freshness check runs")
def when_check(world: dict[str, Any]) -> None:
    _run(world)


@when("a parallel wave's change to one of those files is integrated and reindexed")
def when_integrated(world: dict[str, Any]) -> None:
    """A file-checkout integration: the code lands, then the index is rebuilt."""
    world["before"] = _baselines(world)
    _change_symbols(world["root"], "alpha")
    reindex(world["root"])
    _run(world)


def _baselines(world: dict[str, Any]) -> dict[str, tuple[str, str]]:
    from beadloom.infrastructure.db import open_db

    conn = open_db(world["root"] / ".beadloom" / "beadloom.db")
    try:
        return {
            str(r["code_path"]): (str(r["code_hash_at_sync"]), str(r["doc_hash_at_sync"]))
            for r in conn.execute(
                "SELECT code_path, code_hash_at_sync, doc_hash_at_sync FROM sync_state"
            )
        }
    finally:
        conn.close()


@then("only the pair whose own file changed is reported stale")
def then_only_changed_stale(world: dict[str, Any]) -> None:
    stale = [p for p in _pairs(world) if p["status"] == "stale"]
    assert [p["code_path"] for p in stale] == ["src/widgets/alpha.py"]


@then("the other pairs report that a sibling moved")
def then_others_sibling(world: dict[str, Any]) -> None:
    others = [p for p in _pairs(world) if p["code_path"] != "src/widgets/alpha.py"]
    assert {p["status"] for p in others} == {"unverified"}
    assert {p["reason"] for p in others} == {"sibling_symbols_changed"}


@then("the pairs that report a sibling moved name the file that moved")
def then_names_mover(world: dict[str, Any]) -> None:
    others = [p for p in _pairs(world) if p["reason"] == "sibling_symbols_changed"]
    assert others
    for pair in others:
        assert "alpha.py" in pair["details"]
    # And in the shape a reader actually sees, not only in the machine one: the
    # human line for these rows used to claim "no baseline", which is a
    # different fact about a different pair.
    lines = [ln for ln in world["human"].output.splitlines() if "beta.py" in ln]
    assert lines
    assert all("alpha.py" in ln for ln in lines)
    assert all("no baseline" not in ln for ln in lines)


@then("the check does not recommend sync-update for those pairs")
def then_no_sync_update(world: dict[str, Any]) -> None:
    for line in world["human"].output.splitlines():
        if "beta.py" in line or "gamma.py" in line:
            assert "sync-update" not in line


@then("the untouched pairs keep the baseline they were integrated with")
def then_untouched_not_rebaselined(world: dict[str, Any]) -> None:
    after = _baselines(world)
    before = world["before"]
    for path, baseline in before.items():
        if path == "src/widgets/alpha.py":
            continue
        assert after[path] == baseline
