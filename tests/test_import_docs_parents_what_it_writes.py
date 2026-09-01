"""`import_docs` is the second writer of `domain` nodes, and it holds the invariant.

BDL-067 `.14`, the review of `.13`'s major 1. `.1` stated the domain-parent
post-condition over `bootstrap_project`'s output and the statement was correct;
`import_docs` writes `domain` nodes too, into `.beadloom/_graph/imported.yml`, and
never received it. Every document the classifier could not place became a domain
with no `part_of` edge in the same run that wrote `domain-needs-parent` at error
severity, so `init --yes --mode both` exited 0 and the adopter's next
`lint --strict` exited 1 on three nodes — BDL-UX #192's signature, on a branch this
epic had declared covered.

These cases are stated over what `import_docs` LEAVES ON DISK rather than over what
it returns, because its return value describes the documents it classified and says
nothing about the graph it wrote. The distinction is the finding: a post-condition
read off the reported half of a writer's output is how the unreported half went four
waves unguarded.

The fixtures are projects that are not Beadloom, and one of them is named
`orders (web)` — a name `_sanitize_ref_id` would rewrite. An edge that recomputed
its destination from the project name instead of reading the root node would point
at nothing there, and only there.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
import yaml

from beadloom.onboarding.scanner.doc_classify import import_docs

if TYPE_CHECKING:
    from pathlib import Path

#: A document whose text matches none of `classify_doc`'s three patterns, so it
#: falls through to the `other` branch and is written as a `domain`. That
#: fallthrough is where the defect lived, so the fixture has to reach it.
UNCLASSIFIABLE = "# Payments\n\nHow money moves through the shop.\n"

#: A project name that survives `_sanitize_ref_id` only by losing characters.
PARENTHESISED_NAME = "orders (web)"


def _write_graph(project: Path, data: dict[str, Any], name: str = "services.yml") -> Path:
    graph_dir = project / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True, exist_ok=True)
    path = graph_dir / name
    path.write_text(
        yaml.safe_dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return path


def _write_docs(project: Path, names: tuple[str, ...] = ("payments.md",)) -> Path:
    docs = project / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    for name in names:
        (docs / name).write_text(UNCLASSIFIABLE, encoding="utf-8")
    return docs


def _imported(project: Path) -> dict[str, Any]:
    path = project / ".beadloom" / "_graph" / "imported.yml"
    assert path.exists(), "import_docs wrote no graph file"
    data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data


def _bootstrapped_graph(root_ref_id: str = "orders-web") -> dict[str, Any]:
    """The shape `bootstrap_project` leaves: one root service, one parented domain."""
    return {
        "nodes": [
            {"ref_id": root_ref_id, "kind": "service", "summary": f"Root: {root_ref_id}"},
            {"ref_id": "src", "kind": "domain", "summary": "Source directory: src"},
        ],
        "edges": [{"src": "src", "dst": root_ref_id, "kind": "part_of"}],
    }


class TestEveryImportedNodeIsAttachedToTheRoot:
    """The post-condition, stated over the file `import_docs` writes."""

    def test_an_unclassifiable_document_is_not_left_a_parentless_domain(
        self, tmp_path: Path
    ) -> None:
        """The exact node the reviewer measured: `payments`, kind domain, no edge."""
        _write_graph(tmp_path, _bootstrapped_graph())
        import_docs(tmp_path, _write_docs(tmp_path))

        data = _imported(tmp_path)
        parented = {e["src"] for e in data.get("edges", []) if e["kind"] == "part_of"}
        orphans = [n["ref_id"] for n in data["nodes"] if n["ref_id"] not in parented]
        assert not orphans, f"nodes written with no part_of edge: {orphans}"
        # Anti-vacuity: an import that wrote nothing satisfies the claim above.
        assert any(n["kind"] == "domain" for n in data["nodes"]), data["nodes"]

    def test_the_edge_names_the_root_by_the_ref_id_the_graph_holds(
        self, tmp_path: Path
    ) -> None:
        """Read off the node, not recomputed from the project directory name.

        The root ref is written unsanitised while cluster refs are sanitised, so a
        destination recomputed from the name resolves to nothing for a project
        whose name carries parentheses — and for no other project, which is why
        this is the fixture.
        """
        project = tmp_path / PARENTHESISED_NAME
        project.mkdir()
        _write_graph(project, _bootstrapped_graph(root_ref_id=PARENTHESISED_NAME))
        import_docs(project, _write_docs(project))

        data = _imported(project)
        assert {e["dst"] for e in data["edges"]} == {PARENTHESISED_NAME}, data["edges"]

    def test_a_node_whose_ref_id_is_the_roots_own_gets_no_edge_to_itself(
        self, tmp_path: Path
    ) -> None:
        """An edge from a node to itself is not a parent.

        The classic collision: a document named after the project. The duplicate
        ref_id is a separate defect with a separate fix (`beadloom-7c6k`); what
        must not happen here is a self-edge.
        """
        _write_graph(tmp_path, _bootstrapped_graph())
        import_docs(tmp_path, _write_docs(tmp_path, names=("orders-web.md", "payments.md")))

        data = _imported(tmp_path)
        assert "orders-web" in {n["ref_id"] for n in data["nodes"]}, data["nodes"]
        assert not [e for e in data["edges"] if e["src"] == e["dst"]], data["edges"]

    def test_a_node_that_already_has_a_parent_is_not_attached_a_second_time(
        self, tmp_path: Path
    ) -> None:
        """A ref_id the bootstrap already parented keeps the parent it was given."""
        _write_graph(tmp_path, _bootstrapped_graph())
        import_docs(tmp_path, _write_docs(tmp_path, names=("src.md", "payments.md")))

        data = _imported(tmp_path)
        assert not [e for e in data["edges"] if e["src"] == "src"], data["edges"]

    def test_every_kind_the_classifier_writes_is_attached_not_only_domains(
        self, tmp_path: Path
    ) -> None:
        """The rules require a parent for `feature` too, and will require more.

        A post-condition that tracked today's two ruled kinds would go stale the
        next time `generate_rules` gains a rule, which is the shape of mistake
        this bead exists to stop repeating.
        """
        _write_graph(tmp_path, _bootstrapped_graph())
        docs = _write_docs(tmp_path)
        (docs / "checkout.md").write_text(
            "# Checkout\n\nUser story: a shopper pays.\n", encoding="utf-8"
        )
        import_docs(tmp_path, docs)

        data = _imported(tmp_path)
        kinds = {n["kind"] for n in data["nodes"]}
        assert "feature" in kinds, kinds
        parented = {e["src"] for e in data["edges"]}
        assert {n["ref_id"] for n in data["nodes"]} <= parented, data


class TestWhenThereIsNoRootToAttachTo:
    """No parent is named rather than one guessed, and the import still runs."""

    def test_a_graph_with_no_root_service_leaves_the_nodes_unattached(
        self, tmp_path: Path
    ) -> None:
        """A guessed destination is a claim the graph does not make.

        Nothing is red here: a graph with no root carries no `rules.yml` this
        command wrote either, and `init` reports what the rules say rather than
        what this function wishes they said.
        """
        _write_graph(tmp_path, {"nodes": [{"ref_id": "src", "kind": "domain"}]})
        import_docs(tmp_path, _write_docs(tmp_path))

        assert "edges" not in _imported(tmp_path)

    def test_two_unparented_services_are_two_candidates_and_neither_is_chosen(
        self, tmp_path: Path
    ) -> None:
        _write_graph(
            tmp_path,
            {
                "nodes": [
                    {"ref_id": "orders-web", "kind": "service"},
                    {"ref_id": "orders-api", "kind": "service"},
                ]
            },
        )
        import_docs(tmp_path, _write_docs(tmp_path))

        assert "edges" not in _imported(tmp_path)

    def test_an_empty_graph_directory_is_not_an_error(self, tmp_path: Path) -> None:
        """`init --yes --mode import` on a virgin project writes no bootstrap."""
        import_docs(tmp_path, _write_docs(tmp_path))

        assert "edges" not in _imported(tmp_path)

    def test_a_graph_file_that_is_not_readable_yaml_is_skipped(
        self, tmp_path: Path
    ) -> None:
        """A hand edit that will not parse must not turn the import into a crash."""
        _write_graph(tmp_path, _bootstrapped_graph())
        (tmp_path / ".beadloom" / "_graph" / "hand.yml").write_text(
            "nodes: [\n", encoding="utf-8"
        )
        import_docs(tmp_path, _write_docs(tmp_path))

        assert {e["dst"] for e in _imported(tmp_path)["edges"]} == {"orders-web"}


class TestTheRootIsTheNodeNoPartOfEdgeLeaves:
    """Which service is the root is read from the edges, not from position."""

    @pytest.mark.parametrize("root_first", [True, False])
    def test_a_child_service_is_not_mistaken_for_the_root(
        self, tmp_path: Path, root_first: bool
    ) -> None:
        nodes = [
            {"ref_id": "orders-web", "kind": "service"},
            {"ref_id": "orders-api", "kind": "service"},
        ]
        _write_graph(
            tmp_path,
            {
                "nodes": nodes if root_first else list(reversed(nodes)),
                "edges": [{"src": "orders-api", "dst": "orders-web", "kind": "part_of"}],
            },
        )
        import_docs(tmp_path, _write_docs(tmp_path))

        assert {e["dst"] for e in _imported(tmp_path)["edges"]} == {"orders-web"}
