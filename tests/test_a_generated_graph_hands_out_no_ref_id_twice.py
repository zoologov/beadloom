"""BDL-069 S2, closing half of BDL-UX #214 — two nodes, one `ref_id`, one survivor.

Measured on the published 4.0.0 wheel, on a project named `myapp` holding
`src/myapp/` — the ordinary single-package Python src-layout:

    beadloom init --yes --mode bootstrap  ->  rc 0, `Graph: 2 nodes, 0 edges`
    services.yml  ->  ref_id `myapp` twice: kind `service` (the root, no source)
                      and kind `domain` (source `src/myapp/`)
    beadloom status  ->  `Nodes: 1`, and the one kept is the root

The node that carries the source is the one lost, so the package the project is
named after is absent from every answer the graph gives. The root `ref_id` comes
from the manifest name and the cluster `ref_id` from the source directory, and on
`src/<project>/` those are the same string.

**This repository cannot reproduce it.** `beadloom` holds `src/beadloom/` with
seven packages under it, so no cluster is named after the project. Every fixture
here is a project that is NOT this one — `myapp`, `ledger`, `core` — which is why
a fix that worked by recognising our own tree would fail these.

The loader half of #214 (report the reduction rather than perform it silently) is
`beadloom-39ap` and is not asserted here. What these cases hold is that no writer
produces the collision for it to report.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest
import yaml

from beadloom.application.reindex import incremental_reindex
from beadloom.graph.linter import lint
from beadloom.onboarding.scanner import bootstrap_project
from beadloom.onboarding.scanner.doc_classify import import_docs
from beadloom.onboarding.scanner.ref_ids import RefIdAllocator

if TYPE_CHECKING:
    from pathlib import Path


def _services_yml(project: Path) -> dict[str, Any]:
    """The graph the bootstrap wrote, read back off disk.

    Read back rather than taken from the return value, because the return value
    is what the command REPORTS and the file is what every later reader sees.
    `init` reporting `Graph: 2 nodes` over a file holding one distinct ref_id is
    the defect itself.
    """
    text = (project / ".beadloom" / "_graph" / "services.yml").read_text(encoding="utf-8")
    data: dict[str, Any] = yaml.safe_load(text)
    return data


def _imported_yml(project: Path) -> dict[str, Any]:
    text = (project / ".beadloom" / "_graph" / "imported.yml").read_text(encoding="utf-8")
    data: dict[str, Any] = yaml.safe_load(text)
    return data


def _single_package_project(root: Path, name: str = "myapp") -> Path:
    """A project named `myapp` whose only package is `src/myapp/`.

    The most common Python layout there is, and the one the defect was reported
    on. The manifest carries the name, so `_detect_project_name` returns `myapp`
    and `_cluster_with_children` returns the one cluster `myapp`.
    """
    project = root / name
    (project / "src" / name).mkdir(parents=True)
    (project / "src" / name / "__init__.py").write_text("X = 1\n", encoding="utf-8")
    (project / "src" / name / "core.py").write_text(
        "def go() -> int:\n    return 1\n", encoding="utf-8"
    )
    (project / "pyproject.toml").write_text(
        f'[project]\nname = "{name}"\nversion = "0.1.0"\n', encoding="utf-8"
    )
    return project


def _package_that_imports_a_sibling(root: Path) -> Path:
    """`ledger` holding `src/ledger/` and `src/shared/`, the first importing the second.

    The collision is the same one, and this fixture adds what the naive fix
    misses: `_quick_import_scan` builds its edges by recomputing the cluster's
    ref_id from the directory name. A cluster written under a different ref_id
    than its name then gets an edge whose `src` names no node at all.
    """
    project = root / "ledger"
    (project / "src" / "ledger").mkdir(parents=True)
    (project / "src" / "shared").mkdir(parents=True)
    (project / "src" / "shared" / "__init__.py").write_text("Y = 2\n", encoding="utf-8")
    (project / "src" / "shared" / "money.py").write_text(
        "def cents() -> int:\n    return 0\n", encoding="utf-8"
    )
    (project / "src" / "ledger" / "__init__.py").write_text("X = 1\n", encoding="utf-8")
    (project / "src" / "ledger" / "book.py").write_text(
        "from shared import money\n\n\ndef total() -> int:\n    return money.cents()\n",
        encoding="utf-8",
    )
    (project / "pyproject.toml").write_text(
        '[project]\nname = "ledger"\nversion = "0.1.0"\n', encoding="utf-8"
    )
    return project


class TestTheAllocator:
    """`RefIdAllocator` — the ref_id a node is written under, handed out once."""

    def test_a_free_name_is_handed_out_unchanged(self) -> None:
        """Nothing is renamed that does not have to be.

        Every project this defect does not touch must write exactly the graph it
        wrote before, so the ordinary answer is the name that was asked for.
        """
        allocator = RefIdAllocator()

        assert allocator.take("myapp") == "myapp"

    def test_the_second_asker_is_qualified_rather_than_numbered(self) -> None:
        """`myapp` and `myapp-domain` — the qualifier says what the second node IS.

        A number would be unique and say nothing. The qualifier a caller passes
        is the node's kind, which is the one fact that genuinely distinguishes a
        root service from the package under it.
        """
        allocator = RefIdAllocator()
        allocator.take("myapp")

        assert allocator.take("myapp", qualifier="domain") == "myapp-domain"

    def test_a_qualified_name_that_is_also_taken_is_numbered(self) -> None:
        """The fallback, and it must terminate: a sibling really can be named that.

        A project holding `src/myapp/` and `src/myapp-domain/` reaches this, and
        so does a third asker for the same name.
        """
        allocator = RefIdAllocator()
        allocator.take("myapp")
        allocator.take("myapp-domain")

        assert allocator.take("myapp", qualifier="domain") == "myapp-domain-2"
        assert allocator.take("myapp", qualifier="domain") == "myapp-domain-3"

    def test_a_name_the_graph_already_holds_is_not_handed_out(self) -> None:
        """The importer adds to a graph it did not write, and must not shadow it.

        `import_docs` seeds the allocator with the ref_ids already on disk. A doc
        named after an existing node would otherwise write a second node under
        that node's ref_id, which is the same defect through the other writer.
        """
        allocator = RefIdAllocator({"myapp", "orders"})

        assert allocator.take("myapp", qualifier="adr") == "myapp-adr"
        assert allocator.take("orders") == "orders-2"

    def test_a_name_with_no_qualifier_falls_straight_to_a_number(self) -> None:
        """A caller with nothing to say about the node says nothing."""
        allocator = RefIdAllocator()
        allocator.take("setup")

        assert allocator.take("setup") == "setup-2"

    def test_the_names_handed_out_are_the_ones_it_reports_as_taken(self) -> None:
        """Anti-vacuity: an allocator that recorded nothing would pass every case above.

        Each of those asks for one name at a time; this one asks what the
        allocator believes it has done.
        """
        allocator = RefIdAllocator({"seeded"})
        handed = {allocator.take("a"), allocator.take("a", qualifier="domain")}

        assert handed == {"a", "a-domain"}
        assert allocator.taken == {"seeded", "a", "a-domain"}


class TestTheBootstrapWritesNoRefIdTwice:
    """The first emitter: `bootstrap_project`, on projects that are not this one."""

    def test_the_single_package_layout_writes_two_distinct_ref_ids(
        self, tmp_path: Path
    ) -> None:
        """BDL-UX #214 itself. Before the fix: two nodes, one `ref_id`, one survivor."""
        project = _single_package_project(tmp_path)

        bootstrap_project(project)

        nodes = _services_yml(project)["nodes"]
        refs = [n["ref_id"] for n in nodes]
        assert len(refs) == len(set(refs)), refs

    def test_the_project_keeps_its_own_name_and_the_package_is_qualified(
        self, tmp_path: Path
    ) -> None:
        """Which of the two is renamed, stated rather than left to the order they are written in.

        The root's ref_id is the project's public name: `doc_generator` titles the
        architecture document with it and `generate_rules` names it as the parent
        every domain must have. So the root keeps `myapp` and the package under it
        is written as `myapp-domain`.
        """
        project = _single_package_project(tmp_path)

        bootstrap_project(project)

        nodes = {n["ref_id"]: n for n in _services_yml(project)["nodes"]}
        assert nodes["myapp"]["kind"] == "service"
        assert nodes["myapp"]["source"] == ""
        assert nodes["myapp-domain"]["source"] == "src/myapp/"

    def test_the_node_that_carries_the_source_survives_the_load(
        self, tmp_path: Path
    ) -> None:
        """The defect's cost: the package the project is named after vanished.

        `beadloom status` reported `Nodes: 1` over a file the same command said
        held 2, and the one it dropped was the one with a `source`. Asserted
        through the reindex, which is the reader `status` counts.
        """
        project = _single_package_project(tmp_path)

        report = bootstrap_project(project)
        result = incremental_reindex(project)

        assert result.nodes_loaded == report["nodes_generated"], (
            result.nodes_loaded,
            report["nodes_generated"],
        )

    def test_the_package_is_part_of_the_root(self, tmp_path: Path) -> None:
        """`domain-needs-parent` over a population that contains the domain.

        The rule is not touched by this bead and did not misbehave: it fired when
        the node existed and reported an empty population when it did not. What
        changes is that the domain is now in the graph, so the edge has to be
        there — the top-level attachment loop used to skip exactly this cluster,
        because attaching it would have been a self-edge.
        """
        project = _single_package_project(tmp_path)

        bootstrap_project(project)

        graph = _services_yml(project)
        edges = graph.get("edges") or []
        assert {"src": "myapp-domain", "dst": "myapp", "kind": "part_of"} in edges, edges

    @pytest.mark.parametrize(
        "make_project",
        [_single_package_project, _package_that_imports_a_sibling],
        ids=["single-package", "package-importing-a-sibling"],
    )
    def test_every_edge_names_a_node_the_bootstrap_wrote(
        self, tmp_path: Path, make_project: Any
    ) -> None:
        """A renamed cluster is renamed for every edge-builder, not only for the node.

        Three later passes recompute a cluster's ref_id from its directory name —
        the manifest dependency loop, the import scan and the root attachment. A
        rename that reached the node and not them replaces a lost node with a
        dangling edge, which the loader drops just as quietly.
        """
        project = make_project(tmp_path)

        bootstrap_project(project)

        graph = _services_yml(project)
        written = {n["ref_id"] for n in graph["nodes"]}
        dangling = [
            e
            for e in (graph.get("edges") or [])
            if e["src"] not in written or e["dst"] not in written
        ]
        assert not dangling, (dangling, sorted(written))

    def test_the_import_edge_between_two_packages_survives_the_rename(
        self, tmp_path: Path
    ) -> None:
        """Anti-vacuity for the case above: an edge dropped is not an edge repaired.

        `src/ledger/book.py` imports `shared`, so the scan has an edge to make.
        A fix that renamed the cluster and left the scan recomputing the old name
        would emit no edge at all and pass the dangling-edge check.
        """
        project = _package_that_imports_a_sibling(tmp_path)

        bootstrap_project(project)

        edges = _services_yml(project).get("edges") or []
        assert {"src": "ledger-domain", "dst": "shared", "kind": "depends_on"} in edges, edges

    def test_the_bootstrapped_graph_passes_the_rules_the_same_run_wrote(
        self, tmp_path: Path
    ) -> None:
        """End to end, on the layout `lint` had nothing to say about.

        `domain-needs-parent` went inert rather than red — the node it was
        written for was not in the graph to be judged. Green here has to mean the
        domain is present AND parented, so the case asserts both.
        """
        project = _single_package_project(tmp_path)

        bootstrap_project(project)
        result = lint(project, reindex=incremental_reindex)

        nodes = _services_yml(project)["nodes"]
        root = next(n["ref_id"] for n in nodes if n["kind"] == "service")
        domains = [n["ref_id"] for n in nodes if n["kind"] == "domain"]

        assert not result.has_errors, [
            (v.rule_name, v.from_ref_id, v.message) for v in result.violations
        ]
        # Anti-vacuity: the rule reported an empty population for two major
        # releases. A domain under a ref_id of its own is a domain the loader
        # keeps, so the rule that passed here passed over something.
        assert domains == ["myapp-domain"], nodes
        assert root not in domains, nodes

    def test_a_project_not_named_after_a_package_is_written_exactly_as_before(
        self, tmp_path: Path
    ) -> None:
        """The other side of the fix: nothing renames a graph that had no collision.

        `ledger` holding `src/ledger/` and `src/shared/` collides; a project named
        `ledger-app` over the same directories does not, and must write `ledger`
        and `shared` under their own names.
        """
        project = _package_that_imports_a_sibling(tmp_path)
        (project / "pyproject.toml").write_text(
            '[project]\nname = "ledger-app"\nversion = "0.1.0"\n', encoding="utf-8"
        )

        bootstrap_project(project)

        refs = {n["ref_id"] for n in _services_yml(project)["nodes"]}
        assert refs == {"ledger-app", "ledger", "shared"}, refs


class TestTheImporterWritesNoRefIdTwice:
    """The second emitter: `import_docs`, which adds to a graph it did not write."""

    def _bootstrapped(self, tmp_path: Path) -> Path:
        project = _single_package_project(tmp_path)
        bootstrap_project(project)
        return project

    def _write_doc(self, project: Path, rel: str, body: str = "") -> None:
        path = project / "docs" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body or f"# {path.stem}\n\nSystem design notes.\n", encoding="utf-8")

    def test_a_document_named_after_a_node_does_not_take_that_nodes_ref_id(
        self, tmp_path: Path
    ) -> None:
        """`docs/myapp.md` on a project whose root node is `myapp`.

        The same collision through the other writer, and the one the graph on
        disk cannot defend itself against: `imported.yml` is written after
        `services.yml` and a reader keyed by ref_id keeps one of the two.
        """
        project = self._bootstrapped(tmp_path)
        self._write_doc(project, "myapp.md")

        import_docs(project, project / "docs")

        imported = {n["ref_id"] for n in _imported_yml(project)["nodes"]}
        bootstrapped = {n["ref_id"] for n in _services_yml(project)["nodes"]}
        assert not (imported & bootstrapped), sorted(imported & bootstrapped)

    def test_two_documents_with_one_file_name_become_two_nodes(
        self, tmp_path: Path
    ) -> None:
        """`docs/api/setup.md` and `docs/cli/setup.md` — the ref_id is the stem.

        Nothing about the directory reaches the ref_id, so a project that
        documents each area the same way lost one document per repeated name.
        """
        project = self._bootstrapped(tmp_path)
        self._write_doc(project, "api/setup.md")
        self._write_doc(project, "cli/setup.md")

        import_docs(project, project / "docs")

        nodes = _imported_yml(project)["nodes"]
        refs = [n["ref_id"] for n in nodes]
        assert len(refs) == len(set(refs)), refs
        assert len(refs) == 2, nodes

    def test_each_imported_node_still_names_the_document_it_came_from(
        self, tmp_path: Path
    ) -> None:
        """Anti-vacuity: a rename that lost the `docs:` field would pass the case above."""
        project = self._bootstrapped(tmp_path)
        self._write_doc(project, "api/setup.md")
        self._write_doc(project, "cli/setup.md")

        import_docs(project, project / "docs")

        docs = sorted(n["docs"][0] for n in _imported_yml(project)["nodes"])
        assert docs == ["docs/api/setup.md", "docs/cli/setup.md"], docs

    def test_every_imported_node_is_parented_to_the_root_it_found(
        self, tmp_path: Path
    ) -> None:
        """The post-condition `parent_edges` holds, over ref_ids that are now unique.

        Stated here because the qualified ref_id is what the edge must name: an
        edge written for the ref_id the document ASKED for would name nothing.
        """
        project = self._bootstrapped(tmp_path)
        self._write_doc(project, "myapp.md")

        import_docs(project, project / "docs")

        data = _imported_yml(project)
        parented = {e["src"] for e in (data.get("edges") or [])}
        assert parented == {n["ref_id"] for n in data["nodes"]}, data
        assert {e["dst"] for e in data["edges"]} == {"myapp"}, data["edges"]

    def test_the_imported_graph_and_the_bootstrapped_one_load_as_one_graph(
        self, tmp_path: Path
    ) -> None:
        """Both writers, one directory, and the count the reader keeps.

        `init --yes --mode both` runs them in this order, and the number of nodes
        it reports is the sum of what the two files hold. That number is only
        true if no ref_id appears in both.
        """
        project = self._bootstrapped(tmp_path)
        self._write_doc(project, "myapp.md")
        self._write_doc(project, "api/setup.md")
        self._write_doc(project, "cli/setup.md")

        import_docs(project, project / "docs")
        result = incremental_reindex(project)

        written = [
            n["ref_id"]
            for data in (_services_yml(project), _imported_yml(project))
            for n in data["nodes"]
        ]
        assert len(written) == len(set(written)), sorted(written)
        assert result.nodes_loaded == len(written), (result.nodes_loaded, written)


class TestTheFixtureIsNotThisRepository:
    """Guard: a fix that recognised Beadloom's own tree would pass everything above."""

    def test_the_fixture_project_names_are_not_ours(self, tmp_path: Path) -> None:
        project = _single_package_project(tmp_path)
        manifest = (project / "pyproject.toml").read_text(encoding="utf-8")

        assert "beadloom" not in manifest
        assert json.dumps(sorted(p.name for p in (project / "src").iterdir())) == '["myapp"]'
