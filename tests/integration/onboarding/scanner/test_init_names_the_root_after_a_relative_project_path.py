"""``init --project .`` names the root service after the folder ``.`` names (BDL-080 S3e).

Measured by S3T (``beadloom-hvnv``) on scratch copies of the Java, Kotlin and Swift adopter
fixtures: ``init --yes --project .`` exited 1 with ``domain-needs-parent`` on every domain,
because a manifest that names no project (``pom.xml``, ``build.gradle.kts``,
``Package.swift`` are not read for a name) left the name to the folder, and
``Path('.').name`` is ``''``. The root service was written as ``''`` and the rule that
every domain is part of the root named a node no domain could be part of. An absolute
path, or no ``--project`` at all, named it correctly.
"""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

import pytest
import yaml
from click.testing import CliRunner

from beadloom.services.cli import main
from tests.support.adopter_portals import JAVA

if TYPE_CHECKING:
    from pathlib import Path

pytest.importorskip("tree_sitter_java")


def test_init_with_a_relative_project_path_names_the_root_after_its_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "ledger-copy"
    shutil.copytree(JAVA.source, project)
    monkeypatch.chdir(project)

    result = CliRunner().invoke(main, ["init", "--yes", "--project", "."])

    graph = yaml.safe_load(
        (project / ".beadloom" / "_graph" / "services.yml").read_text(encoding="utf-8")
    )
    assert graph["nodes"][0]["ref_id"] == "ledger-copy"
    assert result.exit_code == 0, result.output
