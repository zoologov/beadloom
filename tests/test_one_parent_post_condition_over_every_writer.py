"""One parent post-condition, over every writer that creates graph nodes.

BDL-067 `.21`, major 3 of the review of `.20`. Two modules carried the same
private name, the same loop body and the same post-condition, differing only in
where `parented` came from, a `str()` call and the ORDER of their parameters.
They had already drifted once and were repaired by editing both: the review of
`.16` found one covering every kind and the other only `domain`, so "the two
writers now disagree about their own shared invariant".

The repair that mattered is not the second edit. It is that the invariant now
has one implementation, and that a THIRD writer of nodes fails a test on the day
it is written instead of being discovered by the next review. So nothing here is
a list of the two writers we happen to have:

- the writers are DERIVED from the source — every function that reaches the one
  commit point every graph YAML routes through (`write_yaml_atomic`) and builds
  a payload holding `nodes`, which is what "creates graph nodes" means;
- each of them is asserted to reach the shared post-condition, by importing it
  from the module that owns it rather than by carrying a same-named private
  copy;
- and the package is asserted to hold exactly one definition of it.

`tests/test_init_branches_that_reach_the_bootstrap.py` derives the same commit
point for a different question — which branches of `init` reach a writer — and
is the module to read next; this one asks what a writer must DO once reached.

The last class here is the smaller finding in the same major, made checkable:
`doc_classify` stated the binding between the two functions by naming
`bootstrap._missing_domain_parent_edges`, a symbol `.17` had renamed away, so
the only thing tying two copies of one invariant together was a cross-reference
that resolved to nothing. The consolidation replaces that prose binding with an
import, and the one cross-reference that remains is checked.
"""

from __future__ import annotations

import ast
import inspect
import io
import re
import tokenize
from pathlib import Path

import pytest

import beadloom
from beadloom.application.source_derivation import (
    FoundFunction,
    called_names,
    definitions_named,
    function_named,
    imports_in,
    module_tree,
    writers_that_build,
)
from beadloom.infrastructure.atomic_io import write_yaml_atomic
from beadloom.onboarding.scanner.parent_edges import missing_parent_edges, parented_by

#: The single commit point for every graph YAML in the product, read off the
#: function object so a rename fails here rather than leaving a scan that
#: silently finds no writer at all.
THE_GRAPH_COMMIT_POINT = write_yaml_atomic.__name__

#: The post-condition every writer of nodes must reach, read off the function
#: object for the same reason.
THE_POST_CONDITION = missing_parent_edges.__name__

#: The module that owns it. A writer reaches the post-condition by importing
#: from here; a writer that grows its own same-named copy does not.
THE_OWNING_MODULE = missing_parent_edges.__module__

#: The writers that create nodes, as they stand today. Asserted against the
#: DERIVED set rather than used as one: a third writer must fail here, and the
#: failure asks the question the review of `.16` had to ask by hand — does this
#: writer hold the parent post-condition, or has the invariant just acquired a
#: third implementation?
THE_WRITERS_THAT_CREATE_NODES = frozenset({"bootstrap_project", "import_docs"})

#: The package whose docstrings are read for cross-references. Narrow on
#: purpose: a reference to a sibling module's symbol is resolvable here, and a
#: sweep of the whole product would spend its failures on prose that names
#: attributes of objects rather than symbols of modules.
THE_PACKAGE = "onboarding/scanner"


def _package_root() -> Path:
    return Path(inspect.getfile(beadloom)).parent


def _writers_that_create_nodes(root: Path | None = None) -> dict[str, FoundFunction]:
    """Every function under *root* that commits a graph file holding nodes.

    The derivation is `source_derivation.writers_that_build`; what this module
    supplies is the two names that make it a question about GRAPH NODES — the
    commit point every graph YAML routes through, and the key a payload has to
    build to be creating nodes rather than patching them. Both are read off the
    product's own objects above, so a rename fails here rather than leaving a
    scan that quietly finds no writer at all.

    *root* is the product's own package unless a caller says otherwise.
    `TestTheWriterScanReportsAThirdWriter` points it at a directory holding one
    synthetic module, which is how the scan itself is tested before the two
    classes above are trusted to it.
    """
    return writers_that_build(
        root or _package_root(), key="nodes", commit_point=THE_GRAPH_COMMIT_POINT
    )


def _definitions_of_the_post_condition(root: Path) -> list[str]:
    """Every definition of the post-condition under *root*, by relative path."""
    return definitions_named(root, THE_POST_CONDITION)


def _function_named(name: str, path: Path) -> ast.FunctionDef | ast.AsyncFunctionDef:
    """The function called *name* in the file at *path*."""
    return function_named(name, module_tree(path))


class TestTheWritersAreDerivedFromTheSource:
    """The instrument, before anything is trusted to it."""

    def test_the_scan_finds_a_writer_to_judge(self) -> None:
        """Anti-vacuity: an empty scan would pass every assertion below it."""
        assert _writers_that_create_nodes(), (
            f"no function both calls {THE_GRAPH_COMMIT_POINT!r} and builds a "
            "payload holding `nodes`, so every assertion below asserts nothing"
        )

    def test_the_scan_finds_the_writers_the_sweep_found_by_hand(self) -> None:
        found = set(_writers_that_create_nodes())

        assert found == THE_WRITERS_THAT_CREATE_NODES, (
            "the set of functions that create graph nodes has changed. Added: "
            f"{sorted(found - THE_WRITERS_THAT_CREATE_NODES)}; gone: "
            f"{sorted(THE_WRITERS_THAT_CREATE_NODES - found)}. A new one holds "
            f"the parent post-condition by calling {THE_POST_CONDITION!r} — it "
            "does not get its own copy."
        )

    def test_a_writer_that_only_patches_nodes_is_not_counted(self) -> None:
        """The discriminator, stated as the case it exists to exclude.

        `update_node_in_yaml` commits a graph file and reads `nodes` out of it,
        and it must not be asked to hold a post-condition about nodes it did not
        create. If this ever fails, the scan has started counting patchers and
        the class above is asserting the wrong population.
        """
        assert "update_node_in_yaml" not in _writers_that_create_nodes()


#: A third writer of nodes, written the way a third writer gets written: it
#: builds the payload, commits it through the one commit point, and nobody
#: remembered the post-condition. Spelled through the two derived names rather
#: than typed out, so a rename moves the mutant with the product instead of
#: leaving a synthetic module that no longer has the shape it is named after.
A_THIRD_WRITER_OF_NODES = """
from beadloom.infrastructure.atomic_io import COMMIT


def write_the_service_map(project_root, nodes):
    payload = {"nodes": nodes, "edges": []}
    COMMIT(project_root / ".beadloom" / "_graph" / "third.yml", payload)
""".replace("COMMIT", THE_GRAPH_COMMIT_POINT)

#: A function that commits a graph file and creates no node: it reads `nodes`
#: out of a file somebody else wrote and puts the same list back. This is the
#: shape of `update_node_in_yaml`, `_patch_docs_field` and `link`, and the scan
#: must not ask any of them to hold a post-condition about nodes they did not
#: create.
A_FUNCTION_THAT_ONLY_PATCHES_NODES = """
import yaml

from beadloom.infrastructure.atomic_io import COMMIT


def patch_the_summary(path, ref_id, summary):
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    for node in data.get("nodes", []):
        if node["ref_id"] == ref_id:
            node["summary"] = summary
    COMMIT(path, data)
""".replace("COMMIT", THE_GRAPH_COMMIT_POINT)

#: A third writer that builds the payload and hands the commit to a helper. The
#: scan cannot see it, and that is the ceiling this module states rather than
#: discovers: the two halves it matches on are in two functions, so neither
#: function carries both.
A_WRITER_THAT_HANDS_THE_COMMIT_TO_A_HELPER = """
from beadloom.infrastructure.atomic_io import COMMIT


def write_the_domain_map(project_root, nodes):
    _commit(project_root / ".beadloom" / "_graph" / "third.yml", {"nodes": nodes})


def _commit(path, payload):
    COMMIT(path, payload)
""".replace("COMMIT", THE_GRAPH_COMMIT_POINT)

#: A third writer that calls the post-condition by its public name and defines
#: its own. This is the shape the import check exists for and the only one it
#: catches alone: the name is called, so a check that asked no more than that
#: reports the module clean while the call reaches a body of its own.
A_WRITER_CARRYING_ITS_OWN_COPY = """
from beadloom.infrastructure.atomic_io import COMMIT


def POST_CONDITION(nodes, root_ref_id, parented):
    return []


def write_the_service_map(project_root, nodes):
    payload = {"nodes": nodes, "edges": POST_CONDITION(nodes, "root", set())}
    COMMIT(project_root / ".beadloom" / "_graph" / "third.yml", payload)
""".replace("COMMIT", THE_GRAPH_COMMIT_POINT).replace(
    "POST_CONDITION", THE_POST_CONDITION
)

#: The same copy under the spelling the two writers actually had — private, with
#: a leading underscore. Two checks catch it and it takes both to say so: the
#: call check does not match a private name, and the definition scan strips the
#: underscore before comparing, which is the only reason it counts.
A_WRITER_CARRYING_A_PRIVATE_COPY = A_WRITER_CARRYING_ITS_OWN_COPY.replace(
    THE_POST_CONDITION, f"_{THE_POST_CONDITION}"
)


class TestTheWriterScanReportsAThirdWriter:
    """The scan itself, before the classes above are trusted to it.

    BDL-067 `.22`, covering `.21`. The two classes above say what the writers of
    nodes must do, and both of them ask the scan which functions those are. A
    scan that could not SEE a third writer would leave both of them green on the
    day one arrived — the equality case only fails if the new writer is found —
    and nothing established that it can. That is the same gap one level down as
    the one this epic keeps meeting, and it is closed the way
    `tests/test_init_branches_that_reach_the_bootstrap.py` closes it for a fourth
    branch of `init`: by mutants of the real shape, read by the real scan.

    The synthetic modules are written into a directory of their own, so what the
    scan says about each one is a difference that module makes and nothing else.
    """

    def _scanning(self, tmp_path: Path, source: str) -> dict[str, FoundFunction]:
        (tmp_path / "third_writer.py").write_text(source, encoding="utf-8")
        return _writers_that_create_nodes(tmp_path)

    def test_a_third_writer_of_nodes_is_found(self, tmp_path: Path) -> None:
        """The failure this module exists to produce, produced on demand.

        Found means named: `test_the_scan_finds_the_writers_the_sweep_found_by
        _hand` compares the derived set against the declared one, so a writer the
        scan sees is a writer somebody has to answer for.
        """
        found = self._scanning(tmp_path, A_THIRD_WRITER_OF_NODES)

        assert set(found) == {"write_the_service_map"}, found

    def test_a_function_that_only_patches_nodes_is_not_found(
        self, tmp_path: Path
    ) -> None:
        """Anti-vacuity for the case above: a scan that found everything passes it.

        `test_a_writer_that_only_patches_nodes_is_not_counted` states the same
        exclusion over the real `update_node_in_yaml`. This states it over a
        shape the scan has never seen, which is what a third patcher will be.
        """
        assert self._scanning(tmp_path, A_FUNCTION_THAT_ONLY_PATCHES_NODES) == {}

    def test_a_writer_that_hands_the_commit_to_a_helper_is_not_found(
        self, tmp_path: Path
    ) -> None:
        """The ceiling, stated as a case rather than as a sentence in a docstring.

        The scan matches both halves in ONE function body, so a writer that
        builds the payload and delegates the commit is invisible here. It is not
        invisible to the suite: the helper becomes a seventh direct caller of the
        commit point and fails `test_the_writer_seed_finds_the_writers_the_sweep
        _found_by_hand` in `tests/test_init_branches_that_reach_the_bootstrap.py`,
        whose failure text asks whether the new writer creates nodes. The cost of
        the ceiling is therefore a worse question, not a missed one — and if that
        other case is ever relaxed to containment, this one is the record of what
        was relying on it.
        """
        found = self._scanning(tmp_path, A_WRITER_THAT_HANDS_THE_COMMIT_TO_A_HELPER)

        assert found == {}, found

    def test_a_writer_calling_its_own_copy_is_found_and_imports_nothing(
        self, tmp_path: Path
    ) -> None:
        """The discriminator between the call check and the import check.

        Both are asserted here because either alone is satisfied by the state
        this major found: the writer DOES call the post-condition by name, so a
        call-only check reports it clean, and it does not import it from the
        module that owns it, which is what makes the call reach a copy.
        """
        found = self._scanning(tmp_path, A_WRITER_CARRYING_ITS_OWN_COPY)
        where = found["write_the_service_map"]

        assert THE_POST_CONDITION in called_names(
            _function_named("write_the_service_map", where.path)
        )
        assert (THE_OWNING_MODULE, THE_POST_CONDITION) not in imports_in(where.path)

    def test_a_private_copy_is_caught_by_the_call_check_and_counted_as_a_definition(
        self, tmp_path: Path
    ) -> None:
        """`_missing_parent_edges` is how both copies were actually spelled.

        Both halves, because the two checks answer it differently and only
        together do they cover the two spellings a copy can have. The call check
        matches the public name, so a private copy fails it outright — which is
        why the case above had to be written with the public one to reach the
        import check at all. And the definition scan strips the leading
        underscore before comparing: a scan that did not would have counted the
        one shared definition and neither of the two private ones it exists to
        find.
        """
        (tmp_path / "third_writer.py").write_text(
            A_WRITER_CARRYING_A_PRIVATE_COPY, encoding="utf-8"
        )
        where = _writers_that_create_nodes(tmp_path)["write_the_service_map"]

        assert THE_POST_CONDITION not in called_names(
            _function_named("write_the_service_map", where.path)
        )
        assert _definitions_of_the_post_condition(tmp_path) == ["third_writer.py"]


class TestEveryWriterOfNodesReachesTheOnePostCondition:
    """The invariant is edited once, because there is one of it."""

    @pytest.mark.parametrize("writer", sorted(THE_WRITERS_THAT_CREATE_NODES))
    def test_the_writer_calls_the_shared_post_condition(self, writer: str) -> None:
        where = _writers_that_create_nodes()[writer]

        assert THE_POST_CONDITION in called_names(_function_named(writer, where.path)), (
            f"{writer} creates graph nodes and never calls {THE_POST_CONDITION!r}, "
            "so nothing states that the nodes it writes carry a parent"
        )

    @pytest.mark.parametrize("writer", sorted(THE_WRITERS_THAT_CREATE_NODES))
    def test_the_writer_imports_it_rather_than_carrying_a_copy(
        self, writer: str
    ) -> None:
        """Calling a same-named local function would pass the case above.

        That is exactly the state this major found: two modules, one name, two
        bodies. The import is what makes the call reach the shared definition.
        """
        where = _writers_that_create_nodes()[writer]

        assert (THE_OWNING_MODULE, THE_POST_CONDITION) in imports_in(where.path), (
            f"{where.path} calls {THE_POST_CONDITION!r} without importing it from "
            f"{THE_OWNING_MODULE!r}, so it is calling a copy of its own"
        )

    def test_the_package_defines_the_post_condition_once(self) -> None:
        """A second definition is how the two copies got there in the first place."""
        defined_in = _definitions_of_the_post_condition(_package_root())

        assert len(defined_in) == 1, (
            f"{THE_POST_CONDITION!r} is defined in more than one place: "
            f"{defined_in}. One post-condition, one implementation."
        )


class TestThePostConditionItself:
    """What the shared helper promises, stated over the helper.

    These cases were written against `bootstrap._missing_parent_edges` (BDL-067
    `.1` and `.17`) and moved here with the function: they belong to the
    invariant, not to either of the two writers that hold it.
    """

    def test_a_parentless_node_gets_one_edge_to_the_root(self) -> None:
        nodes = [
            {"ref_id": "orders (web)", "kind": "service"},
            {"ref_id": "src", "kind": "domain"},
        ]

        missing = missing_parent_edges(nodes, "orders (web)", set())

        assert missing == [{"src": "src", "dst": "orders (web)", "kind": "part_of"}]

    def test_a_node_that_already_has_a_parent_is_left_alone(self) -> None:
        """The classifier's parent wins — the root is the fallback, not an override."""
        nodes = [
            {"ref_id": "platform", "kind": "domain"},
            {"ref_id": "platform-orders", "kind": "domain"},
        ]

        parented = {"platform", "platform-orders"}

        assert missing_parent_edges(nodes, "supply-chain", parented) == []

    def test_a_node_whose_ref_id_is_the_roots_own_gets_no_self_edge(self) -> None:
        """`part_of` from a node to itself is not a parent, and it is reachable.

        The classic `src/<project>/` layout hands the root service and the single
        domain the same ref_id.
        """
        nodes = [{"ref_id": "ledger", "kind": "service"}, {"ref_id": "ledger", "kind": "domain"}]

        assert missing_parent_edges(nodes, "ledger", set()) == []

    def test_nodes_of_every_kind_are_attached_not_only_domains(self) -> None:
        """The review of `.16`, minor 2: the two copies disagreed here.

        A post-condition that tracked the current rule set would go stale the
        next time a rule is added, which is how this epic's first fix came to
        need a second one.
        """
        nodes = [
            {"ref_id": "models", "kind": "entity"},
            {"ref_id": "rest", "kind": "feature"},
        ]

        missing = missing_parent_edges(nodes, "ledger", set())

        assert {e["src"] for e in missing} == {"models", "rest"}
        assert {e["dst"] for e in missing} == {"ledger"}

    def test_one_ref_id_written_twice_is_attached_once(self) -> None:
        """Both writers can emit a ref_id twice; two identical edges are one edge."""
        nodes = [{"ref_id": "billing", "kind": "domain"}] * 2

        assert missing_parent_edges(nodes, "ledger", set()) == [
            {"src": "billing", "dst": "ledger", "kind": "part_of"}
        ]

    def test_the_callers_set_is_not_written_into(self) -> None:
        """`parented` is the caller's fact about the graph, not scratch space.

        `import_docs` reads it out of the graph on disk and would otherwise get
        it back describing nodes that are only about to be written.
        """
        parented = {"platform"}

        missing_parent_edges([{"ref_id": "billing", "kind": "domain"}], "ledger", parented)

        assert parented == {"platform"}

    def test_a_ref_id_that_is_not_a_string_is_named_as_one(self) -> None:
        """An imported document can be named `2024` and YAML loads that as an int."""
        missing = missing_parent_edges([{"ref_id": 2024, "kind": "domain"}], "ledger", set())

        assert missing == [{"src": "2024", "dst": "ledger", "kind": "part_of"}]


class TestWhatCountsAsAParent:
    """`parented_by` — the other half of the invariant, also stated once.

    The post-condition asks its caller which ref_ids already have a parent, and
    both callers answer it by reading edges. `bootstrap_project` reads the edges
    it is about to write and `_existing_graph` reads the edges already on disk,
    so the SOURCE differs and the question does not: only a `part_of` edge is a
    parent, because `part_of` is what `domain-needs-parent` requires. Left at
    each call site it was a comprehension nobody could test — the bootstrap
    writes no `depends_on` edge before it holds the post-condition, so the kind
    filter could be deleted and every end-to-end case would stay green.
    """

    def test_a_part_of_edge_parents_its_source(self) -> None:
        assert parented_by([{"src": "billing", "dst": "ledger", "kind": "part_of"}]) == {
            "billing"
        }

    def test_a_depends_on_edge_does_not_count_as_a_parent(self) -> None:
        """`domain-needs-parent` requires `part_of`; any other kind leaves it violated."""
        assert parented_by([{"src": "billing", "dst": "audit", "kind": "depends_on"}]) == set()

    def test_an_edge_with_no_source_names_nobody(self) -> None:
        """A hand-edited graph file can hold a half-written edge."""
        half_written = [{"dst": "ledger", "kind": "part_of"}, {"src": "", "kind": "part_of"}]

        assert parented_by(half_written) == set()

    def test_a_source_that_is_not_a_string_is_named_as_one(self) -> None:
        """It is compared against ref_ids `missing_parent_edges` names as strings."""
        assert parented_by([{"src": 2024, "dst": "ledger", "kind": "part_of"}]) == {"2024"}

    def test_no_edges_parent_nobody(self) -> None:
        assert parented_by([]) == set()


class TestNoProseNamesASiblingSymbolThatIsGone:
    """The binding between two modules must resolve, or it binds nothing.

    `doc_classify` stated the whole relationship between the two copies of this
    invariant by naming `bootstrap._missing_domain_parent_edges` in prose. `.17`
    renamed that symbol and left the reference, so for three waves the only thing
    connecting two implementations of one post-condition was a cross-reference to
    a name that existed nowhere in `src/` or `tests/` — which the review of `.20`
    found by looking rather than by running anything.

    This is narrow by construction: only `` `module.symbol` `` where `module` is
    another module of the same package, so what it reads is a claim about this
    package's own source and not about prose in general. Comments are read as
    well as docstrings, because the surviving cross-reference between the two
    writers of nodes is a comment: reading only docstrings would leave the one
    binding this class exists for outside it.
    """

    #: `` `bootstrap.py` `` is a file, not a symbol reference.
    NOT_A_SYMBOL = frozenset({"py"})

    REFERENCE = re.compile(r"`([a-z_][a-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)`")

    def _prose_in(self, path: Path) -> list[str]:
        """Every docstring and every comment in the file at *path*."""
        text = path.read_text(encoding="utf-8")
        prose = [
            doc
            for node in ast.walk(ast.parse(text, filename=str(path)))
            if isinstance(
                node, ast.Module | ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef
            )
            for doc in [ast.get_docstring(node)]
            if doc
        ]
        prose.extend(
            token.string
            for token in tokenize.generate_tokens(io.StringIO(text).readline)
            if token.type == tokenize.COMMENT
        )
        return prose

    def _references(self, package: Path | None = None) -> list[tuple[Path, str, str]]:
        package = package if package is not None else _package_root() / THE_PACKAGE
        modules = {path.stem for path in package.glob("*.py")}
        found: list[tuple[Path, str, str]] = []
        for path in sorted(package.glob("*.py")):
            for prose in self._prose_in(path):
                for match in self.REFERENCE.finditer(prose.replace("\n", " ")):
                    module, symbol = match.group(1), match.group(2)
                    if module in modules and symbol not in self.NOT_A_SYMBOL:
                        found.append((path, module, symbol))
        return found

    def _symbols_of(self, module: str, package: Path | None = None) -> set[str]:
        root = package if package is not None else _package_root() / THE_PACKAGE
        path = root / f"{module}.py"
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        return {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
        } | {
            target.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name)
        }

    def _dangling_in(self, package: Path | None = None) -> list[str]:
        """Every sibling reference in *package* naming a symbol it has not got.

        The package is a parameter for the reason `_writers_that_create_nodes`
        takes one: the same scan has to run over a tree built to dangle, or
        nothing ever demonstrates that it can reject.
        """
        return [
            f"{path.name} names `{module}.{symbol}`"
            for path, module, symbol in self._references(package)
            if symbol not in self._symbols_of(module, package)
        ]

    def test_the_scan_finds_a_reference_to_check(self) -> None:
        """Anti-vacuity: no references found would pass the case below it."""
        assert self._references(), (
            f"no prose in {THE_PACKAGE} names a sibling module's symbol, so the "
            "case below asserts nothing"
        )

    def test_every_sibling_reference_resolves(self) -> None:
        dangling = self._dangling_in()

        assert dangling == [], (
            f"these docstrings name a symbol the module does not have: {dangling}"
        )


class TestTheProseScanCanRejectAReferenceAndNotOnlyFindOne:
    """The scan above, run over prose built to dangle — BDL-068 `.7`.

    `.1` REFUSED to lift this scanner into production and said why, measured:
    replacing its finding computation with ``dangling = []``, so the check could
    never report anything, left the module at 27 passed. Its only assertion about
    a dangling reference was an equality with the empty list over the real tree,
    and no case anywhere fed it a body that dangles. Its anti-vacuity case proves
    the scan FINDS references; nothing proved it could REJECT one. That is the
    defect class this epic exists to remove, and `.1` handed the closing here.

    Four shapes, because the scan is narrow by construction and the narrowness is
    what makes its silence worth trusting: a reference to a sibling module's
    missing symbol is reported; the same reference to a symbol that exists is
    not; a reference to something that is not a sibling module is not read at
    all; and a comment dangles as loudly as a docstring, because the surviving
    cross-reference between the two writers of nodes was a comment.
    """

    #: The module referred to. `handled` exists and `renamed_away` does not,
    #: which is `.17`'s shape exactly — a symbol renamed, the reference left.
    _THE_SIBLING = "sibling"
    _THE_SIBLING_BODY = "def handled():\n    return None\n"

    _A_DOCSTRING_NAMING_A_SYMBOL_THAT_IS_GONE = (
        '"""This module mirrors `sibling.renamed_away`."""\n'
    )
    _A_DOCSTRING_NAMING_A_SYMBOL_THAT_EXISTS = (
        '"""This module mirrors `sibling.handled`."""\n'
    )
    _A_COMMENT_NAMING_A_SYMBOL_THAT_IS_GONE = (
        "# kept in step with `sibling.renamed_away`\n"
    )
    _A_REFERENCE_TO_SOMETHING_THAT_IS_NOT_A_SIBLING_MODULE = (
        '"""Reads `payload.get` off the mapping it was handed."""\n'
    )

    def _a_package_whose_prose_says(self, tmp_path: Path, prose: str) -> Path:
        package = tmp_path / "scanned"
        package.mkdir()
        (package / f"{self._THE_SIBLING}.py").write_text(
            self._THE_SIBLING_BODY, encoding="utf-8"
        )
        (package / "caller.py").write_text(
            prose + "\n\ndef run():\n    return None\n", encoding="utf-8"
        )
        return package

    def test_a_docstring_naming_a_symbol_the_sibling_lost_is_reported(
        self, tmp_path: Path
    ) -> None:
        """The case `.1` measured to be missing, and the reason it refused the lift."""
        scan = TestNoProseNamesASiblingSymbolThatIsGone()
        package = self._a_package_whose_prose_says(
            tmp_path, self._A_DOCSTRING_NAMING_A_SYMBOL_THAT_IS_GONE
        )

        assert scan._dangling_in(package) == ["caller.py names `sibling.renamed_away`"]

    def test_a_comment_dangles_as_loudly_as_a_docstring(self, tmp_path: Path) -> None:
        """The surviving cross-reference this check exists for was a comment."""
        scan = TestNoProseNamesASiblingSymbolThatIsGone()
        package = self._a_package_whose_prose_says(
            tmp_path, self._A_COMMENT_NAMING_A_SYMBOL_THAT_IS_GONE
        )

        assert scan._dangling_in(package) == ["caller.py names `sibling.renamed_away`"]

    def test_a_reference_that_resolves_is_not_reported(self, tmp_path: Path) -> None:
        """The other direction: silent where the symbol is where the prose says."""
        scan = TestNoProseNamesASiblingSymbolThatIsGone()
        package = self._a_package_whose_prose_says(
            tmp_path, self._A_DOCSTRING_NAMING_A_SYMBOL_THAT_EXISTS
        )

        assert scan._dangling_in(package) == []

    def test_prose_naming_something_that_is_not_a_sibling_module_is_not_read(
        self, tmp_path: Path
    ) -> None:
        """Why the narrowness earns the silence.

        `payload.get` is an attribute of a mapping, not a symbol of a sibling
        module, so it is outside the scan rather than a finding somebody has to
        be excused from — which is what a sweep of all prose would have produced.
        """
        scan = TestNoProseNamesASiblingSymbolThatIsGone()
        package = self._a_package_whose_prose_says(
            tmp_path, self._A_REFERENCE_TO_SOMETHING_THAT_IS_NOT_A_SIBLING_MODULE
        )

        assert scan._references(package) == []
