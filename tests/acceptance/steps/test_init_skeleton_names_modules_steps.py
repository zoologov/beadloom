"""Step implementations for `features/init_skeleton_names_modules.feature`.

BDL-069 S1 (`beadloom-qylh`), the first adopter blocker of BDL-UX #282. Every
step runs the real command against a git repository built in a temporary
directory: `init` writes the skeletons, `ci` judges them, and nothing between the
two is patched or edited except where a scenario says so in its own words.

**The module names are chosen so the template cannot supply them.** The rule
matches a module's stem as a whole word, case-insensitively, anywhere in the
document. A fixture holding `source.py` or `features.py` would be satisfied by
the skeleton's own headings (`## Source`, `## Features`) and pass without the
skeleton naming a single module. `core`, `journal` and `invoice` appear in no
line the templates write, which is what lets these scenarios go red.

The fixtures are built here rather than imported from `tests.adopter_project`,
for the reason `test_bootstrap_self_consistency_steps` records: the acceptance
suite is copied out of the repository and run standalone, where the `tests`
package is not importable.
"""

from __future__ import annotations

import json
import re
import subprocess
from typing import TYPE_CHECKING, Any

import pytest
from click.testing import CliRunner
from pytest_bdd import given, scenarios, then, when

from beadloom.infrastructure.db import readonly_connection
from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../features/init_skeleton_names_modules.feature")

#: Two packages under `src/`, the layout BDL-UX #282 was measured on. `ledger`
#: carries a second module so a skeleton that named only the first one it met
#: would still leave a module out.
TWO_PACKAGES: dict[str, dict[str, str]] = {
    "ledger": {
        "__init__.py": '"""The ledger."""\n',
        "core.py": (
            "class Ledger:\n    def post(self, amount: int) -> int:\n        return amount\n"
        ),
        "journal.py": "def record(entry: str) -> str:\n    return entry\n",
    },
    "billing": {
        "__init__.py": '"""Billing."""\n',
        "core.py": (
            "from ledger.core import Ledger\n\n\n"
            "def charge(amount: int) -> int:\n    return Ledger().post(amount)\n"
        ),
        "invoice.py": "def issue(number: int) -> int:\n    return number\n",
    },
}

#: The repository name for the two-package layout. The manifest names the
#: project something none of its packages is called.
TWO_PACKAGE_PROJECT = "myapp"

#: The single-package layout. Until `beadloom-cgco` its domain node was lost to
#: the root, so the rule reached no document at all and was green for that
#: reason. It is covered here because the node now survives and meets the rule.
SINGLE_PACKAGE_PROJECT = "inventory"
SINGLE_PACKAGE: dict[str, dict[str, str]] = {
    SINGLE_PACKAGE_PROJECT: {
        "__init__.py": '"""Inventory."""\n',
        "core.py": "def count(items: list[str]) -> int:\n    return len(items)\n",
    },
}

#: The document and the module the third scenario takes back out of it.
THE_PACKAGE_EDITED = "ledger"
THE_MODULE_REMOVED = "journal"


@pytest.fixture()
def world() -> dict[str, Any]:
    return {}


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)  # noqa: S603, S607


def _repository(root: Path, name: str, packages: dict[str, dict[str, str]]) -> Path:
    """A committed repository holding *packages* under `src/`, and nothing else."""
    project = root / name
    for package, modules in packages.items():
        (project / "src" / package).mkdir(parents=True)
        for module, text in modules.items():
            (project / "src" / package / module).write_text(text, encoding="utf-8")
    (project / "pyproject.toml").write_text(
        f'[project]\nname = "{name}"\nversion = "0.1.0"\n', encoding="utf-8"
    )
    _git(project, "init", "-q", "-b", "main")
    _git(project, "config", "user.email", "test@example.invalid")
    _git(project, "config", "user.name", "Test")
    _git(project, "add", "-A")
    _git(project, "commit", "-q", "-m", "the code before beadloom")
    return project


@given("a git repository holding two Python packages under src")
def _given_two_packages(world: dict[str, Any], tmp_path: Path) -> None:
    world["project"] = _repository(tmp_path, TWO_PACKAGE_PROJECT, TWO_PACKAGES)


@given("a git repository whose only Python package is named after the repository")
def _given_a_single_package(world: dict[str, Any], tmp_path: Path) -> None:
    world["project"] = _repository(tmp_path, SINGLE_PACKAGE_PROJECT, SINGLE_PACKAGE)


@when("beadloom init is run in bootstrap mode without prompts")
def _when_init(world: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    project = world["project"]
    monkeypatch.chdir(project)
    result = CliRunner().invoke(
        main, ["init", "--yes", "--mode", "bootstrap", "--project", str(project)]
    )
    assert result.exit_code == 0, result.output


@when("beadloom ci is run on the repository")
def _when_ci(world: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    project = world["project"]
    monkeypatch.chdir(project)
    world["ci"] = CliRunner().invoke(main, ["ci", "--format", "github", "--project", str(project)])


def _package_documents(project: Path) -> list[tuple[str, Path, str]]:
    """``(doc path in the index, source directory, document text)`` per package node.

    Read out of the INDEX the gate judged, not out of the graph file, because the
    claim is about the population the freshness check ran over. A node the loader
    dropped would be absent from both sides of the assertion and satisfy it.
    """
    with readonly_connection(project / ".beadloom" / "beadloom.db") as conn:
        rows = conn.execute(
            "SELECT n.source, d.path FROM nodes n JOIN docs d ON d.ref_id = n.ref_id "
            "WHERE n.source LIKE 'src/%/'"
        ).fetchall()
    return [
        (
            str(doc_path),
            project / str(source),
            (project / "docs" / str(doc_path)).read_text(encoding="utf-8"),
        )
        for source, doc_path in rows
    ]


def _names(text: str, module: str) -> bool:
    return re.search(rf"\b{re.escape(module)}\b", text, re.IGNORECASE) is not None


@when("one module's name is taken back out of its package document")
def _when_a_module_name_is_removed(world: dict[str, Any]) -> None:
    project = world["project"]
    readme = project / "docs" / "domains" / THE_PACKAGE_EDITED / "README.md"
    text = readme.read_text(encoding="utf-8")
    # Anti-vacuity, and the reason this scenario was red before the fix: a name
    # the document never held cannot be taken out of it, and a gate that goes red
    # over such a document says nothing about where its green came from.
    assert _names(text, THE_MODULE_REMOVED), text
    kept = [line for line in text.splitlines() if not _names(line, THE_MODULE_REMOVED)]
    readme.write_text("\n".join(kept) + "\n", encoding="utf-8")


@then("the gate exits 0")
def _then_the_gate_is_green(world: dict[str, Any]) -> None:
    result = world["ci"]
    assert result.exit_code == 0, result.output


@then("the gate does not exit 0")
def _then_the_gate_is_red(world: dict[str, Any]) -> None:
    result = world["ci"]
    assert result.exit_code != 0, result.output


@then("every package document names each module of its package")
def _then_each_module_is_named(world: dict[str, Any]) -> None:
    documents = _package_documents(world["project"])
    # Anti-vacuity: an index holding no package document satisfies the claim.
    assert documents, "the index holds no package document, so nothing was checked"
    for doc_path, source_dir, text in documents:
        modules = sorted(p.stem for p in source_dir.glob("*.py") if p.name != "__init__.py")
        assert modules, f"{source_dir} holds no module, so {doc_path} was not tested"
        unnamed = [module for module in modules if not _names(text, module)]
        assert not unnamed, (doc_path, unnamed, text)


@then("each package document is paired with every code file of its package")
def _then_one_pair_per_code_file(world: dict[str, Any]) -> None:
    """A pair is a document AND a code file, so two files give two pairs over one README.

    Stated here because naming the modules is a change to the document and a
    count of pairs taken over documents would read the same before and after.
    """
    project = world["project"]
    with readonly_connection(project / ".beadloom" / "beadloom.db") as conn:
        pairs = conn.execute("SELECT doc_path, code_path FROM sync_state").fetchall()
    by_doc: dict[str, set[str]] = {}
    for doc_path, code_path in pairs:
        by_doc.setdefault(str(doc_path), set()).add(str(code_path))

    documents = _package_documents(project)
    assert documents, "the index holds no package document, so nothing was checked"
    for doc_path, source_dir, _text in documents:
        files = {str(p.relative_to(project)) for p in source_dir.glob("*.py")}
        assert len(files) > 1, f"{source_dir} holds one file, so one pair proves nothing"
        assert by_doc.get(doc_path) == files, (doc_path, by_doc.get(doc_path), files)


@then("the freshness check names that module as missing from that document")
def _then_sync_check_names_the_module(world: dict[str, Any]) -> None:
    project = world["project"]
    result = CliRunner().invoke(main, ["sync-check", "--json", "--project", str(project)])
    # `.stdout`, not `.output`: Click merges stderr into `.output`, and a notice
    # written there would turn a correct report into a JSON decode error.
    report = json.loads(result.stdout)
    doc_path = f"domains/{THE_PACKAGE_EDITED}/README.md"
    named = [
        pair
        for pair in report["pairs"]
        if pair["doc_path"] == doc_path
        and pair["reason"] == "missing_modules"
        and THE_MODULE_REMOVED in str(pair.get("details", "")).split(", ")
    ]
    assert named, report["pairs"]
    # The edit touched one document, so the other package's document is still
    # the skeleton init wrote, and nothing about it may have gone stale.
    others = [p for p in report["pairs"] if p["doc_path"] != doc_path and p["status"] != "ok"]
    assert not others, others
