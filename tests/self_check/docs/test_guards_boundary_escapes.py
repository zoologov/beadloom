"""Self-checks of this repository's documents and published site (BDL-074 A3).

Moved out of ``tests/test_guards_boundary_escapes.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from beadloom.application.guards.contract import GuardProbes
from tests.test_guards_boundary_escapes import (
    _cli,
    _NoBeads,
    _project,
)

_ROOT = Path(__file__).resolve().parents[3]


_SPEC = _ROOT / "docs" / "domains" / "application" / "features" / "flow-guards" / "SPEC.md"


@pytest.fixture()
def stub_probes(monkeypatch):
    """Wire a tracker that answers, so a verdict comes from the guard and not the probe."""
    from beadloom.services.commands import guard as guard_cmd

    monkeypatch.setattr(
        guard_cmd, "_probes", lambda _root: GuardProbes(tracker=_NoBeads())
    )


class TestADeclaredProjectMustBeAProject:
    """``project_root.py``: "it does not create ``.beadloom/`` where it stands".

    That was true of discovery and false through ``--project``: an existing
    directory that was not a Beadloom project was honoured verbatim, no
    ``flow.yml`` was found, the project's declared ``block`` became the shipped
    default ``warn``, and the firing record manufactured ``.beadloom/`` there —
    the coordinator's measured F9 failure, reachable through an explicit flag.
    ``.28`` filed it as minor ``m3``; ``.29``'s residual list did not name it.
    """


    def test_the_spec_names_the_marker_requirement_in_its_residual_list(self) -> None:
        """The list ``.29`` left this out of, now carrying it."""
        spec = _SPEC.read_text(encoding="utf-8")

        assert "--project" in spec
        assert "must carry" in spec


class TestTheRowsThisRoundAddedAreNowEnumerated:
    """The diff between ``.30``'s independent enumeration and the shipped table.

    A table that enumerates itself proves nothing, so these rows were derived
    from the code and the CLI surface first and compared afterwards. Four are
    argv-reachable and are now rows of ``_EXIT_PATHS``; the fifth is injected
    and is a row of ``_INJECTED_FAILURES``.
    """

    def test_a_context_key_supplied_twice_takes_the_last_and_the_spec_says_so(
        self, tmp_path, stub_probes
    ) -> None:
        """Last-wins was an unstated rule. It is stated now, and read back here."""
        root = _project(tmp_path)

        result = _cli(
            [
                "guard",
                "bead-claimed",
                "--project",
                str(root),
                "--json",
                "--context",
                "path=src/a.py",
                "--context",
                "path=app.py",
            ]
        )

        assert json.loads(result.stdout)["context"]["path"] == "app.py"
        assert "the last occurrence wins" in _SPEC.read_text(encoding="utf-8")
