# beadloom:domain=doc-sync
"""The identity gate: whose project is this, and may our own surfaces describe it.

BDL-062 `.3` added :mod:`beadloom.doc_sync.audit_self_surface` so that
``mcp_tool_count`` and ``cli_command_count`` — both read out of the **running
package** — are declared only for the project that IS that package. Measured
before the gate existed: a project named ``invoice-svc`` was told it had 18 MCP
tools and 43 CLI commands, and both numbers were counted in the denominator of
"N of 9 declared facts verified".

`.5` covers the module's own edge cases, which the bead's tests reached through
:class:`~beadloom.doc_sync.audit.FactRegistry` and therefore only along the
happy path. Every one of them is the same question asked of a manifest that
cannot be read as intended, and the answer must always be the same: **unknown is
not a match.** A gate that resolved an unreadable manifest to anything but
"unknown" would hand our own counts to whichever project happened to defeat the
parser, which is the defect the module exists to prevent rather than a tidier
version of it.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from beadloom.doc_sync.audit_self_surface import (
    RUNNING_DISTRIBUTION,
    declared_project_name,
    foreign_project_reason,
)

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    """An empty directory whose NAME is this distribution's.

    Named ``beadloom`` on purpose in every test below. The module deliberately
    has no directory-name fallback, so a clone sitting in a directory called
    ``beadloom`` must still be unknown — and a fixture in a neutrally named
    directory could not tell a missing fallback from a present one.
    """
    root = tmp_path / RUNNING_DISTRIBUTION
    root.mkdir()
    return root


# --------------------------------------------------------------------------- #
# a manifest that cannot be read as intended leaves the project unknown
# --------------------------------------------------------------------------- #


class TestAnUnreadableManifestLeavesTheProjectUnknown:
    """Every failure to parse resolves to ``None``, never to a name."""

    def test_no_manifest_at_all_declares_no_name(self, project: Path) -> None:
        assert declared_project_name(project) is None

    def test_the_directory_name_is_not_a_fallback(self, project: Path) -> None:
        """The property the module's docstring claims, asserted rather than trusted."""
        assert project.name == RUNNING_DISTRIBUTION

        assert foreign_project_reason(project) is not None

    def test_a_pyproject_that_is_not_utf8_declares_no_name(self, project: Path) -> None:
        """``read_text`` raises on the first non-UTF-8 byte.

        The bytes below spell a perfectly good ``name = "beadloom"`` in
        Latin-1 with one high byte in the comment above it. An identity check
        that fell over here would crash the audit; one that guessed would hand
        this project our surface counts.
        """
        (project / "pyproject.toml").write_bytes(b'# caf\xe9\n[project]\nname = "beadloom"\n')

        assert declared_project_name(project) is None
        assert foreign_project_reason(project) is not None

    def test_a_directory_where_the_manifest_should_be_declares_no_name(
        self, project: Path
    ) -> None:
        """``is_file()`` is the guard; a directory named ``pyproject.toml`` is not one."""
        (project / "pyproject.toml").mkdir()

        assert declared_project_name(project) is None

    def test_a_malformed_package_json_declares_no_name(self, project: Path) -> None:
        (project / "package.json").write_text('{"name": ', encoding="utf-8")

        assert declared_project_name(project) is None

    def test_a_package_json_that_is_not_an_object_declares_no_name(self, project: Path) -> None:
        """Valid JSON is not a manifest. A list has no ``name`` to read."""
        (project / "package.json").write_text('["beadloom"]', encoding="utf-8")

        assert declared_project_name(project) is None

    def test_a_package_json_with_an_empty_name_declares_no_name(self, project: Path) -> None:
        (project / "package.json").write_text(json.dumps({"name": ""}), encoding="utf-8")

        assert declared_project_name(project) is None

    def test_a_cargo_toml_without_a_name_declares_no_name(self, project: Path) -> None:
        (project / "Cargo.toml").write_text('[package]\nversion = "1.0.0"\n', encoding="utf-8")

        assert declared_project_name(project) is None


# --------------------------------------------------------------------------- #
# a manifest that can be read is read, in the documented order
# --------------------------------------------------------------------------- #


class TestTheNameIsReadFromWhicheverManifestDeclaresIt:
    """``pyproject.toml``, then ``package.json``, then ``Cargo.toml``."""

    def test_a_pyproject_name_is_read(self, project: Path) -> None:
        (project / "pyproject.toml").write_text(
            '[project]\nname = "invoice-svc"\n', encoding="utf-8"
        )

        assert declared_project_name(project) == "invoice-svc"

    def test_a_poetry_name_is_read_from_the_same_file(self, project: Path) -> None:
        (project / "pyproject.toml").write_text(
            '[tool.poetry]\nname = "warehouse"\n', encoding="utf-8"
        )

        assert declared_project_name(project) == "warehouse"

    def test_a_package_json_is_read_when_the_pyproject_declares_nothing(
        self, project: Path
    ) -> None:
        """A polyglot repository: an unnamed pyproject must not stop the search."""
        (project / "pyproject.toml").write_text("[build-system]\n", encoding="utf-8")
        (project / "package.json").write_text(json.dumps({"name": "orders-web"}), encoding="utf-8")

        assert declared_project_name(project) == "orders-web"

    def test_a_scoped_npm_name_drops_its_scope(self, project: Path) -> None:
        """``@acme/orders-web`` is the package ``orders-web``.

        Keeping the scope would make every scoped package unknown, and unknown
        costs the project its two surface facts rather than only its identity.
        """
        (project / "package.json").write_text(
            json.dumps({"name": "@acme/orders-web"}), encoding="utf-8"
        )

        assert declared_project_name(project) == "orders-web"

    def test_a_cargo_name_is_read_when_neither_of_the_others_declares_one(
        self, project: Path
    ) -> None:
        (project / "package.json").write_text("{}", encoding="utf-8")
        (project / "Cargo.toml").write_text('[package]\nname = "ledger-core"\n', encoding="utf-8")

        assert declared_project_name(project) == "ledger-core"

    def test_the_pyproject_wins_when_two_manifests_disagree(self, project: Path) -> None:
        (project / "pyproject.toml").write_text(
            '[project]\nname = "invoice-svc"\n', encoding="utf-8"
        )
        (project / "package.json").write_text(json.dumps({"name": "orders-web"}), encoding="utf-8")

        assert declared_project_name(project) == "invoice-svc"


# --------------------------------------------------------------------------- #
# the reason, which is what a reader is shown
# --------------------------------------------------------------------------- #


class TestTheReasonSaysWhichOfTheTwoThingsWentWrong:
    """ "Nobody declared a name" and "somebody declared another name" differ."""

    def test_this_distribution_gets_no_reason_at_all(self, project: Path) -> None:
        (project / "pyproject.toml").write_text(
            f'[project]\nname = "{RUNNING_DISTRIBUTION}"\n', encoding="utf-8"
        )

        assert foreign_project_reason(project) is None

    def test_another_project_is_told_both_names(self, project: Path) -> None:
        (project / "pyproject.toml").write_text(
            '[project]\nname = "invoice-svc"\n', encoding="utf-8"
        )

        reason = foreign_project_reason(project)

        assert reason is not None
        assert "invoice-svc" in reason
        assert RUNNING_DISTRIBUTION in reason

    def test_an_unnamed_project_is_told_that_nothing_declared_a_name(self, project: Path) -> None:
        """A different remedy from the case above, so it must be a different sentence."""
        reason = foreign_project_reason(project)

        assert reason is not None
        assert "declares a project name" in reason
        assert "invoice-svc" not in reason

    def test_the_running_distribution_is_derived_rather_than_written_out(self) -> None:
        """A rename of the package must not leave the gate comparing against a ghost."""
        assert RUNNING_DISTRIBUTION == "beadloom"
        assert foreign_project_reason.__module__.split(".")[0] == RUNNING_DISTRIBUTION
