"""A foreign repository whose package document does not name one of its modules.

Shared by the step modules of BDL-069 `beadloom-h7b3` and `beadloom-yn6i`, which
state their Given in the same words. `init` writes the documents, one module's
name is taken back out of one of them, and the index takes the edit in — the state
an adopter reaches by editing.

**The package holds three code files**, so its document is paired three times.
Two would be enough to print two identical lines; three makes a count of pairs and
a count of documents differ by more than one, so a summary that counted either
cannot pass for the other.

This module lives beside the step modules rather than in the `tests` package, for
the reason `test_bootstrap_self_consistency_steps` records: the acceptance suite is
copied out of the repository and run standalone, where `tests` is not importable.
"""

from __future__ import annotations

import json
import re
import subprocess
from typing import TYPE_CHECKING, Any

from click.testing import CliRunner

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

    import pytest
    from click.testing import Result

#: The package whose document is edited. `journal` and `core` appear in no line
#: the skeleton templates write, so the rule can only be satisfied by the
#: document naming them.
PACKAGE = "ledger"
MODULE_REMOVED = "journal"
PACKAGES: dict[str, dict[str, str]] = {
    PACKAGE: {
        "__init__.py": '"""The ledger."""\n',
        "core.py": (
            "class Ledger:\n    def post(self, amount: int) -> int:\n        return amount\n"
        ),
        "journal.py": "def record(entry: str) -> str:\n    return entry\n",
    },
    "billing": {
        "__init__.py": '"""Billing."""\n',
        "invoice.py": "def issue(number: int) -> int:\n    return number\n",
    },
}

#: The document as the index and every finding spell it: relative to `docs/`.
DOC_PATH = f"domains/{PACKAGE}/README.md"


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)  # noqa: S603, S607


def names(text: str, module: str) -> bool:
    """Whether *text* names *module* as a word."""
    return re.search(rf"\b{re.escape(module)}\b", text, re.IGNORECASE) is not None


def run(project: Path, *args: str) -> Result:
    """One `beadloom` command against *project*, as an adopter would type it."""
    return CliRunner().invoke(main, [*args, "--project", str(project)])


def stale_pairs(project: Path) -> list[dict[str, Any]]:
    """Every stale pair `sync-check --json` reports."""
    result = run(project, "sync-check", "--json")
    # `.stdout`, not `.output`: Click merges stderr into `.output`, and a notice
    # written there would turn a correct report into a JSON decode error.
    pairs: list[dict[str, Any]] = json.loads(result.stdout)["pairs"]
    return [pair for pair in pairs if pair["status"] == "stale"]


def build(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """The committed repository, initialised, with one module unnamed and reindexed."""
    project = tmp_path / "myapp"
    for package, modules in PACKAGES.items():
        (project / "src" / package).mkdir(parents=True)
        for module, text in modules.items():
            (project / "src" / package / module).write_text(text, encoding="utf-8")
    (project / "pyproject.toml").write_text(
        '[project]\nname = "myapp"\nversion = "0.1.0"\n', encoding="utf-8"
    )
    _git(project, "init", "-q", "-b", "main")
    _git(project, "config", "user.email", "test@example.invalid")
    _git(project, "config", "user.name", "Test")
    _git(project, "add", "-A")
    _git(project, "commit", "-q", "-m", "the code before beadloom")

    monkeypatch.chdir(project)
    result = CliRunner().invoke(
        main, ["init", "--yes", "--mode", "bootstrap", "--project", str(project)]
    )
    assert result.exit_code == 0, result.output

    readme = project / "docs" / DOC_PATH
    text = readme.read_text(encoding="utf-8")
    # Anti-vacuity: a name the document never held cannot be taken out of it.
    assert names(text, MODULE_REMOVED), text
    kept = [line for line in text.splitlines() if not names(line, MODULE_REMOVED)]
    readme.write_text("\n".join(kept) + "\n", encoding="utf-8")
    # The index takes the edit in, as `beadloom ci` does before it judges. Without
    # this the first check reads the edit as a changed document (`hash_changed`),
    # which re-attesting does clear, and every step after it would be exercising a
    # different reason from the one the Given names.
    reindexed = run(project, "reindex")
    assert reindexed.exit_code == 0, reindexed.output
    reasons = {pair["reason"] for pair in stale_pairs(project)}
    assert reasons == {"missing_modules"}, reasons
    return project
