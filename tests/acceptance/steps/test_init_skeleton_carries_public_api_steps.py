"""Step implementations for `features/init_skeleton_carries_public_api.feature`.

BDL-069 S1 (`beadloom-8lmj`). Every step runs the real command against a git
repository built in a temporary directory, and the wizard is answered through its
own standard input rather than by patching its prompts: the defect lived in the
ORDER one entry point runs its steps in, and a patched prompt is a second place
that order could be restated wrongly.

**The expected symbols are written down here, not derived.** A table checked
against what the parser returns would agree with any parser, including one that
returned nothing, so each package declares the public and private names it holds
and the assertion reads them from this module.

The fixtures are built here rather than imported from `tests.adopter_project`,
for the reason `test_bootstrap_self_consistency_steps` records: the acceptance
suite is copied out of the repository and run standalone, where the `tests`
package is not importable.
"""

from __future__ import annotations

import re
import subprocess
from typing import TYPE_CHECKING, Any

import pytest
from click.testing import CliRunner
from pytest_bdd import given, scenarios, then, when

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../features/init_skeleton_carries_public_api.feature")

#: The project name in the manifest; no package is called this.
PROJECT = "myapp"

#: Each package's modules, and the names a reader of its document should meet.
#: `billing` keeps a public class in a SUBPACKAGE, because the table covers every
#: file under the node's source directory — the population the index holds for it
#: — and a reader that stopped at the top level would still pass on `ledger`.
PACKAGES: dict[str, dict[str, str]] = {
    "ledger": {
        "__init__.py": '"""The ledger."""\n',
        "core.py": (
            "class Journal:\n    pass\n\n\n"
            "def record(amount: int) -> int:\n    return amount\n\n\n"
            "def _balance() -> int:\n    return 0\n"
        ),
    },
    "billing": {
        "__init__.py": '"""Billing."""\n',
        "core.py": (
            "def charge(amount: int) -> int:\n    return amount\n\n\n"
            "def _round(amount: int) -> int:\n    return amount\n"
        ),
        "invoices/__init__.py": "",
        "invoices/issue.py": "class Invoice:\n    pass\n",
    },
}
PUBLIC_SYMBOLS: dict[str, set[str]] = {
    "ledger": {"Journal", "record"},
    "billing": {"charge", "Invoice"},
}
PRIVATE_SYMBOLS: dict[str, set[str]] = {
    "ledger": {"_balance"},
    "billing": {"_round"},
}

#: The package whose document the clone scenario deletes and regenerates.
THE_PACKAGE_REGENERATED = "billing"

#: Every prompt the wizard puts on this layout, answered with its default: the
#: mode, the graph review, and "Generate doc skeletons?". One spare line, so a
#: prompt added later meets its default instead of an end of input.
WIZARD_DEFAULTS = "\n" * 4

PUBLIC_API_HEADING = "## Public API"
_TABLE_ROW = re.compile(r"^\| `([^`]+)` \|")


@pytest.fixture()
def world() -> dict[str, Any]:
    return {}


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)  # noqa: S603, S607


def _commit(root: Path, message: str) -> None:
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", message)


def _repository(project: Path) -> Path:
    """A committed repository holding `PACKAGES` under `src/`, and nothing else."""
    for package, modules in PACKAGES.items():
        for module, text in modules.items():
            path = project / "src" / package / module
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
    (project / "pyproject.toml").write_text(
        f'[project]\nname = "{PROJECT}"\nversion = "0.1.0"\n', encoding="utf-8"
    )
    _git(project, "init", "-q", "-b", "main")
    _git(project, "config", "user.email", "test@example.invalid")
    _git(project, "config", "user.name", "Test")
    _commit(project, "the code before beadloom")
    return project


def _init(
    project: Path, monkeypatch: pytest.MonkeyPatch, *args: str, answers: str | None = None
) -> None:
    monkeypatch.chdir(project)
    result = CliRunner().invoke(main, ["init", *args, "--project", str(project)], input=answers)
    assert result.exit_code == 0, result.output


def _package_document(project: Path, package: str) -> Path:
    return project / "docs" / "domains" / package / "README.md"


def _public_api_names(text: str) -> set[str] | None:
    """The symbol names in the document's Public API table, or None without one."""
    lines = text.splitlines()
    if PUBLIC_API_HEADING not in lines:
        return None
    section = lines[lines.index(PUBLIC_API_HEADING) + 1 :]
    names: set[str] = set()
    for line in section:
        if line.startswith("## "):
            break
        match = _TABLE_ROW.match(line)
        if match:
            names.add(match.group(1))
    return names


def _documents(project: Path) -> dict[str, bytes]:
    docs = project / "docs"
    return {
        str(path.relative_to(docs)): path.read_bytes()
        for path in sorted(docs.rglob("*"))
        if path.is_file()
    }


@given("a git repository holding two Python packages with public and private symbols")
def _given_a_repository(world: dict[str, Any], tmp_path: Path) -> None:
    world["project"] = _repository(tmp_path / PROJECT)


@given(
    "three copies of a git repository holding two Python packages with public and private symbols"
)
def _given_three_copies(world: dict[str, Any], tmp_path: Path) -> None:
    world["copies"] = [_repository(tmp_path / name / PROJECT) for name in ("a", "b", "c")]


@given("beadloom init has been run without prompts on it and the result committed")
def _given_an_initialised_repository(
    world: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    project = world["project"]
    _init(project, monkeypatch, "--yes", "--mode", "bootstrap")
    _commit(project, "beadloom init")


@given("a clone of that repository, which carries no index")
def _given_a_clone(world: dict[str, Any], tmp_path: Path) -> None:
    clone = tmp_path / "clone"
    subprocess.run(  # noqa: S603
        ["git", "clone", "-q", str(world["project"]), str(clone)],  # noqa: S607
        check=True,
        capture_output=True,
    )
    # Anti-vacuity: a clone carrying an index would regenerate from it, and the
    # scenario would pass for the reason the defect was hidden by.
    assert not (clone / ".beadloom" / "beadloom.db").exists()
    world["clone"] = clone


@when("beadloom init is run without prompts on it")
def _when_init_without_prompts(world: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    _init(world["project"], monkeypatch, "--yes", "--mode", "bootstrap")


@when("beadloom init is run without prompts on the first copy")
def _when_init_first(world: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    _init(world["copies"][0], monkeypatch, "--yes", "--mode", "bootstrap")


@when("beadloom init is run with the bootstrap flag on the second copy")
def _when_init_bootstrap(world: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    _init(world["copies"][1], monkeypatch, "--bootstrap")


@when("the beadloom init wizard is run with every default answer on the third copy")
def _when_the_wizard(world: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    _init(world["copies"][2], monkeypatch, answers=WIZARD_DEFAULTS)


@when("one package document is deleted from the clone")
def _when_a_document_is_deleted(world: dict[str, Any]) -> None:
    _package_document(world["clone"], THE_PACKAGE_REGENERATED).unlink()


@when("beadloom docs generate is run on the clone")
def _when_docs_generate(world: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    clone = world["clone"]
    monkeypatch.chdir(clone)
    result = CliRunner().invoke(main, ["docs", "generate", "--project", str(clone)])
    assert result.exit_code == 0, result.output


def _assert_every_package_has_a_table(project: Path) -> None:
    for package in PACKAGES:
        text = _package_document(project, package).read_text(encoding="utf-8")
        assert _public_api_names(text) is not None, (package, text)


@then("every package document carries a Public API table")
def _then_a_table(world: dict[str, Any]) -> None:
    _assert_every_package_has_a_table(world["project"])


@then("every package document of the first copy carries a Public API table")
def _then_a_table_in_the_first_copy(world: dict[str, Any]) -> None:
    # Without it, three documents that all lack the table are identical too.
    _assert_every_package_has_a_table(world["copies"][0])


@then("each table names every public symbol of its package and no private one")
def _then_the_right_names(world: dict[str, Any]) -> None:
    for package in PACKAGES:
        text = _package_document(world["project"], package).read_text(encoding="utf-8")
        names = _public_api_names(text) or set()
        assert names == PUBLIC_SYMBOLS[package], (package, text)
        assert not (PRIVATE_SYMBOLS[package] & set(re.findall(r"`([^`]+)`", text))), text


@then("the three copies hold the same documents, byte for byte")
def _then_the_same_documents(world: dict[str, Any]) -> None:
    first, *others = (_documents(copy) for copy in world["copies"])
    assert first, "the first copy holds no document, so nothing was compared"
    for other in others:
        assert other == first


@then("the clone's regenerated document is byte-identical to the original's")
def _then_the_same_regenerated_document(world: dict[str, Any]) -> None:
    original = _package_document(world["project"], THE_PACKAGE_REGENERATED).read_bytes()
    regenerated = _package_document(world["clone"], THE_PACKAGE_REGENERATED).read_bytes()
    # Anti-vacuity: the original must itself carry the table, or two documents
    # without it would compare equal.
    assert _public_api_names(original.decode("utf-8")) is not None, original
    assert regenerated == original
