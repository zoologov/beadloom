"""The roles state the cohesion rule and FSD's graph mapping (BDL-080 S2b, RFC D3).

Before this bead the ``fsd`` overlay mapped a layer to a ``domain``, a slice to a
``feature`` and a segment to a ``component`` — a graph `beadloom init` no longer
writes and the site's own slices do not have — and neither overlay stated the
cohesion rule. What is pinned here is what a role reads:

* cohesion is a DECLARED duty, carried by the dev, explore and review cores under
  every architecture, so it does not ride on a launch prompt;
* the ``fsd`` overlay maps a slice to a ``component`` tagged with its layer, names
  the slice's public API and its size signal, and puts Steiger in the commands a
  bead completes with;
* the ``ddd`` overlay states the cohesion rule for Python packages.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.onboarding.role_composer import compose_role
from beadloom.onboarding.role_duties import duty_report

if TYPE_CHECKING:
    from pathlib import Path

_COHESION_ROLES = ("dev", "explore", "review")


def _project(tmp_path: Path, architecture: str, stack: str) -> Path:
    (tmp_path / ".beadloom").mkdir()
    (tmp_path / ".beadloom" / "flow.yml").write_text(
        f"tools: [claude]\narchitecture: [{architecture}]\nstack: [{stack}]\n",
        encoding="utf-8",
    )
    return tmp_path


class TestCohesionIsADeclaredDuty:
    @pytest.mark.parametrize(("architecture", "stack"), [("ddd", "python"), ("fsd", "vuejs")])
    def test_the_duty_is_declared_for_three_roles_and_reaches_each(
        self, tmp_path: Path, architecture: str, stack: str
    ) -> None:
        report = duty_report(_project(tmp_path, architecture, stack))

        declared = {d.duty: d.roles for d in report.declarations}
        assert tuple(sorted(declared["cohesion"])) == _COHESION_ROLES
        carriers = sorted(
            artifact.rsplit("/", 1)[-1].removesuffix(".md")
            for artifact, duty in report.carried
            if duty == "cohesion"
        )
        assert carriers == list(_COHESION_ROLES)
        assert [f for f in report.findings if f.duty == "cohesion"] == []

    def test_the_explorer_writes_a_size_finding_on_the_rows_why_cell(self) -> None:
        text = compose_role("explore", architecture="ddd", stack=["python"])

        assert "max_symbols" in text
        assert "`Why` cell with the rule's name and the count it printed" in text


class TestTheFsdOverlayMapsASliceToAComponent:
    @pytest.mark.parametrize("role", ["dev", "review", "tech-writer"])
    def test_the_old_layer_domain_mapping_is_gone(self, role: str) -> None:
        text = compose_role(role, architecture="fsd", stack=["vuejs"])

        assert "beadloom:domain=<layer>" not in text
        assert "`beadloom:feature` (slice)" not in text
        assert "one doc per **layer**" not in text

    def test_a_slice_is_a_component_tagged_with_its_layer_part_of_the_frontend(self) -> None:
        text = compose_role("dev", architecture="fsd", stack=["vuejs"])

        assert "a `component` node tagged with its layer (`fsd-features`)" in text
        assert "`part_of` the frontend service" in text
        assert "`// beadloom:component=<slice-ref>`" in text

    def test_shared_and_app_hold_segment_components(self) -> None:
        text = compose_role("dev", architecture="fsd", stack=["vuejs"])

        assert "`shared` and `app` have segments, not slices" in text

    @pytest.mark.parametrize("role", ["dev", "review"])
    def test_the_public_api_and_the_cohesion_signal_are_stated(self, role: str) -> None:
        text = compose_role(role, architecture="fsd", stack=["vuejs"])

        assert "slice_public_api" in text
        assert "max_symbols" in text

    def test_steiger_is_among_the_commands_a_bead_completes_with(self) -> None:
        text = compose_role("dev", architecture="fsd", stack=["vuejs"])

        assert "npx steiger" in text
        assert "npm run lint:fsd" in text
        assert "Not run by this gate:" in text


class TestTheDddOverlayStatesCohesionForPythonPackages:
    def test_the_paragraph_names_the_package_and_its_init(self) -> None:
        text = compose_role("dev", architecture="ddd", stack=["python"])

        assert "### Cohesion (DDD, Python packages)" in text
        assert "re-exported from its `__init__`" in text
