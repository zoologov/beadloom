"""Doc skeletons come from composed TEMPLATES, not from string literals (BDL-061 S4b).

Until this bead the shape of every generated document lived inside
``doc_generator.py`` as an f-string. An adopter had nothing to adapt, and
nothing held the shape after generation. The templates now compose through the
same ``compose(core, architecture, stack, project)`` mechanism S3 built for the
role files, so a project extends a document the same way it extends a role.

Two properties are pinned here because both have been broken elsewhere in this
epic: the extraction is **behaviour-preserving** (the bytes a skeleton gets are
the bytes the literals produced), and the composition works for a project that
is **not Beadloom** (``tests/adopter_project.py``, the axis S3b added after four
slices of measuring ourselves).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.onboarding.composer import PROJECT_FLOW_DIRNAME, compose
from beadloom.onboarding.doc_generator import beadloom_readme_values
from beadloom.onboarding.doc_templates import (
    DOC_ARTIFACT_KIND,
    DOC_KIND_FOR_NODE_KIND,
    DOC_KINDS,
    DocTemplateError,
    render_doc,
    required_sections,
)
from beadloom.onboarding.flow_config import FlowConfig
from tests.adopter_project import beadloom_local_facts_in, typescript_project

if TYPE_CHECKING:
    from pathlib import Path


def _config(**kwargs: object) -> FlowConfig:
    base = {
        "tools": ("claude",),
        "architecture": "ddd",
        "stack": ("python",),
    }
    base.update(kwargs)
    return FlowConfig(**base)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# The templates exist as package data and compose through the S3 mechanism
# ---------------------------------------------------------------------------


class TestDocTemplatesCompose:
    def test_every_doc_kind_has_a_shipped_core_fragment(self) -> None:
        """A doc kind with no core fragment is a compose error, not an empty file."""
        for kind in DOC_KINDS:
            composition = compose(DOC_ARTIFACT_KIND, kind.name, config=_config())
            assert composition.text.strip(), f"{kind.name} composed to nothing"

    def test_node_kinds_map_onto_doc_kinds(self) -> None:
        """Every graph node kind the generator writes a doc for has a template."""
        names = {kind.name for kind in DOC_KINDS}
        assert set(DOC_KIND_FOR_NODE_KIND.values()) <= names
        assert set(DOC_KIND_FOR_NODE_KIND) == {"domain", "service", "feature"}

    def test_project_layer_appends_to_a_doc_template(self, tmp_path: Path) -> None:
        """An adopter extends a document the same way they extend a role."""
        fragment = tmp_path / PROJECT_FLOW_DIRNAME / DOC_ARTIFACT_KIND / "domain.md"
        fragment.parent.mkdir(parents=True)
        fragment.write_text("## Runbook\n\nWho to page.\n", encoding="utf-8")

        composition = compose(
            DOC_ARTIFACT_KIND, "domain", config=_config(), project_root=tmp_path
        )

        assert [f.layer for f in composition.fragments][-1] == "project"
        assert "## Runbook" in composition.text

    def test_a_doc_composition_carries_no_flow_suppression_notice(
        self, tmp_path: Path
    ) -> None:
        """A suppression stands down a rule addressed to an agent, not a document.

        ``Composition.text`` appends the notice for the role/command artifacts,
        where it is the whole point. Appending it to a generated README would
        publish flow configuration as documentation.
        """
        from beadloom.onboarding.flow_suppression import FlowSuppression

        config = _config(
            suppressions=(
                FlowSuppression(
                    rule="Anti-patterns / Shell",
                    reason="the team runs on Windows",
                    until="a windows overlay ships",
                ),
            )
        )
        doc = compose(DOC_ARTIFACT_KIND, "domain", config=config)
        role = compose("roles", "dev", config=config)

        assert "Anti-patterns / Shell" not in doc.text
        assert "Anti-patterns / Shell" in role.text


# ---------------------------------------------------------------------------
# Rendering: placeholders are substituted, and an unknown one is loud
# ---------------------------------------------------------------------------


class TestRenderDoc:
    def test_placeholders_are_substituted(self) -> None:
        text = render_doc(
            "domain",
            {
                "ref_id": "billing",
                "summary": "Invoices and dunning",
                "source": "src/billing/",
                "symbols_section": "",
                "depends_on": "(none)",
                "used_by": "(none)",
                "features": "- invoicing",
            },
            config=_config(),
        )
        assert text.startswith("# billing\n")
        assert "> Invoices and dunning" in text
        assert "`src/billing/`" in text
        assert "{{" not in text

    def test_a_placeholder_with_no_value_is_an_error(self) -> None:
        """A silently-empty substitution is how a document ships half-written."""
        with pytest.raises(DocTemplateError) as excinfo:
            render_doc("domain", {"ref_id": "billing"}, config=_config())
        assert "summary" in str(excinfo.value)

    def test_an_unknown_doc_kind_is_an_error(self) -> None:
        with pytest.raises(DocTemplateError):
            render_doc("not-a-kind", {}, config=_config())


# ---------------------------------------------------------------------------
# Required sections are DERIVED from the composed template
# ---------------------------------------------------------------------------


class TestRequiredSections:
    def test_domain_sections_come_from_the_template(self) -> None:
        assert required_sections("domain", config=_config()) == (
            "Source",
            "Dependencies",
            "Features",
        )

    def test_feature_sections_come_from_the_template(self) -> None:
        assert required_sections("feature", config=_config()) == (
            "Source",
            "Dependencies",
            "Parent",
        )

    def test_a_conditional_section_is_not_required(self) -> None:
        """``## Public API`` is rendered only when the node HAS public symbols.

        It reaches the document through a placeholder, so it is not a literal
        heading in the template and cannot be required of a node that has none.
        """
        assert "Public API" not in required_sections("domain", config=_config())

    def test_the_project_layer_adds_a_required_section(self, tmp_path: Path) -> None:
        """PLAN's criterion: a project overlay can add required sections.

        Derived rather than declared twice — the section is required *because*
        the composed template carries it.
        """
        fragment = tmp_path / PROJECT_FLOW_DIRNAME / DOC_ARTIFACT_KIND / "domain.md"
        fragment.parent.mkdir(parents=True)
        fragment.write_text("## Runbook\n\nWho to page.\n", encoding="utf-8")

        sections = required_sections("domain", config=_config(), project_root=tmp_path)

        assert "Runbook" in sections


# ---------------------------------------------------------------------------
# Behaviour preservation: the bytes did not move
# ---------------------------------------------------------------------------


_EXPECTED_DOMAIN_README = """\
# billing

> Invoices and dunning

## Source

`src/billing/`

## Dependencies

- Depends on: ledger
- Used by: api

## Features

- invoicing

<!-- enrich with: beadloom docs polish -->
"""


_EXPECTED_DOMAIN_README_WITH_SYMBOLS = """\
# billing

> Invoices and dunning

## Source

`src/billing/`

## Public API

| Symbol | Kind |
|--------|------|
| `Invoice` | class |

## Dependencies

- Depends on: ledger
- Used by: api

## Features

- invoicing

<!-- enrich with: beadloom docs polish -->
"""


class TestExtractionIsBehaviourPreserving:
    def test_domain_readme_bytes_are_unchanged(self) -> None:
        from beadloom.onboarding.doc_generator import _render_domain_readme

        node = {
            "ref_id": "billing",
            "summary": "Invoices and dunning",
            "source": "src/billing/",
        }
        edges = [
            {"src": "billing", "dst": "ledger", "kind": "depends_on"},
            {"src": "api", "dst": "billing", "kind": "depends_on"},
            {"src": "invoicing", "dst": "billing", "kind": "part_of"},
        ]
        assert _render_domain_readme(node, edges) == _EXPECTED_DOMAIN_README

    def test_domain_readme_with_symbols_bytes_are_unchanged(self) -> None:
        from beadloom.onboarding.doc_generator import _render_domain_readme

        node = {
            "ref_id": "billing",
            "summary": "Invoices and dunning",
            "source": "src/billing/",
        }
        edges = [
            {"src": "billing", "dst": "ledger", "kind": "depends_on"},
            {"src": "api", "dst": "billing", "kind": "depends_on"},
            {"src": "invoicing", "dst": "billing", "kind": "part_of"},
        ]
        symbols = [{"symbol_name": "Invoice", "kind": "class"}]
        assert (
            _render_domain_readme(node, edges, symbols)
            == _EXPECTED_DOMAIN_README_WITH_SYMBOLS
        )


# ---------------------------------------------------------------------------
# The adopter axis: a project that is not Beadloom
# ---------------------------------------------------------------------------


class TestRenderedForAProjectThatIsNotBeadloom:
    def test_generated_docs_state_the_adopter_name_and_nothing_of_ours(
        self, tmp_path: Path
    ) -> None:
        """No fact computed about Beadloom may appear in an adopter's document."""
        project = typescript_project(tmp_path / "acme")

        # Rendered through the value map the generator uses, not a hand-built
        # one: `.15` gave the scaffold two derived placeholders, and a test that
        # supplied its own set would stop exercising what an adopter is given.
        text = render_doc(
            "beadloom-readme",
            beadloom_readme_values(project.name),
            config=_config(),
        )

        assert project.name in text
        assert beadloom_local_facts_in(text) == []

    def test_a_non_python_adopter_composes_every_doc_kind(
        self, tmp_path: Path
    ) -> None:
        """The stack overlay axis must not make a doc kind uncomposable."""
        config = _config(stack=("typescript",))
        for kind in DOC_KINDS:
            composition = compose(
                DOC_ARTIFACT_KIND,
                kind.name,
                config=config,
                project_root=tmp_path,
            )
            assert composition.text.strip()
