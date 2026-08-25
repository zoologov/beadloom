"""Step implementations for the attestation-scope suite (BDL-061, bead `.85`).

Against the real reindex pipeline and the real CLI: the subject is what
``sync_state`` RECORDS after ``sync-update``, so a hand-built table would prove
the fixture rather than the command (FAKES PROVE FAKES).

The module is named ``test_*`` so default pytest collection picks the scenarios
up — the acceptance suite runs inside ``uv run pytest``, not beside it.
"""

from __future__ import annotations

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

scenarios("../features/attestation_scope.feature")

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
def world(tmp_path: Path) -> dict[str, Any]:
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
    return {"root": root, "result": None}


def _attested(root: Path) -> set[tuple[str, str]]:
    """The pairs whose stored baseline claims somebody looked."""
    from beadloom.doc_sync.engine import BASELINE_SOURCE_ATTESTED
    from beadloom.infrastructure.db import open_db

    conn = open_db(root / ".beadloom" / "beadloom.db")
    try:
        return {
            (str(r["doc_path"]), str(r["code_path"]))
            for r in conn.execute(
                "SELECT doc_path, code_path, baseline_source FROM sync_state"
            )
            if str(r["baseline_source"] or "") == BASELINE_SOURCE_ATTESTED
        }
    finally:
        conn.close()


def _all_pairs() -> set[tuple[str, str]]:
    return {(doc, f"src/widgets/{name}.py") for doc in _DOCS for name in _FILES}


def _invoke(world: dict[str, Any], *args: str) -> None:
    world["result"] = CliRunner().invoke(
        main, ["sync-update", *args, "--project", str(world["root"])]
    )
    assert world["result"].exit_code == 0, world["result"].output


@given("two documents paired with three code files of one node")
def given_six_pairs(world: dict[str, Any]) -> None:
    assert _attested(world["root"]) == set()


@given("one of those code files has changed its symbols")
def given_one_changed(world: dict[str, Any]) -> None:
    _write(
        world["root"],
        _MOVER,
        "# beadloom:domain=widgets\ndef alpha_renamed(extra):\n    return extra\n",
    )
    reindex(world["root"])


@when("the ref is re-baselined non-interactively")
def when_rebaselined(world: dict[str, Any]) -> None:
    _invoke(world, "widgets", "--yes")


@when("the operator attests one document by name")
def when_attest_one_doc(world: dict[str, Any]) -> None:
    _invoke(world, "widgets", "--yes", "--pair", "widgets-guide.md")


@when("the operator attests every pair of the ref deliberately")
def when_attest_whole_ref(world: dict[str, Any]) -> None:
    _invoke(world, "widgets", "--yes", "--all-pairs")


@then("only the pairs whose own file changed are recorded as attested")
def then_only_mover_attested(world: dict[str, Any]) -> None:
    assert _attested(world["root"]) == {(doc, _MOVER) for doc in _DOCS}


@then("the run says how many pairs it left unclaimed")
def then_run_reports_unclaimed(world: dict[str, Any]) -> None:
    output = world["result"].output
    assert "4 pair(s)" in output, output
    assert "--all-pairs" in output, output


@then("only that document's pairs are recorded as attested")
def then_only_named_doc_attested(world: dict[str, Any]) -> None:
    assert _attested(world["root"]) == {
        ("widgets-guide.md", f"src/widgets/{name}.py") for name in _FILES
    }


@then("every pair of the ref is recorded as attested")
def then_every_pair_attested(world: dict[str, Any]) -> None:
    assert _attested(world["root"]) == _all_pairs()
