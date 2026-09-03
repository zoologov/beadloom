"""Every caller of the skeleton writer, and the shape all of them call it in.

BDL-067 `.22`, covering `.21`. The sixth review's prediction has three limbs and
this module is the second: the next divergence will be a FOURTH CALLER of
`generate_skeletons`. `.21` closed one way for a caller to be wrong — the
`nodes`/`edges` parameters came off the function, so a whole-tree document can no
longer be rendered from part of the tree by any caller, and
`test_the_skeleton_writer_cannot_be_handed_a_subset_of_the_tree` states that over
the SIGNATURE where it cannot go stale.

Two degrees of freedom survive that fix, and neither had a case:

- WHICH path a call site hands over. The signature says "one argument"; it does
  not say the argument is the project root, and `generate_skeletons(project_root
  / "docs")` type-checks.
- WHEN the call is made. `generate_skeletons` is a graph WRITER: it patches a
  `docs:` field into the graph YAML for every skeleton it creates
  (`tests/test_doc_generator.py::TestPatchDocsField`, which is where that fact is
  measured — it is cited here rather than re-measured). So a caller that
  re-indexes and then generates leaves the index describing a graph file that has
  changed since. `.18` moved the call for exactly that reason, and its own
  comment in `init_flow` states the rule; nothing bound the rule to the source.

WHAT THE ORDER RULE IS, as the source actually holds it — measured, not assumed.
The two orders in the product are not the same and both are correct:

    non_interactive_init   skeletons, then the reindex      (`.18`'s move)
    interactive_init       the reindex, then skeletons, then a SECOND reindex
                           guarded by `files_created > 0` — which is exactly
                           when the patch happens, since a skipped document
                           gets no `docs:` field written back

So the claim here is the one both shapes share and a fourth caller can break:
**a caller that re-indexes at all re-indexes AFTER the skeletons.** A caller that
re-indexes only before them is the `.18` defect with a new author.

`docs_generate` re-indexes neither before nor after, and is accepted: it is a
standalone command that takes no verdict and reads no index afterwards. That is
recorded as the vacuous cell rather than hidden inside a passing parametrisation.

The instrument is not a second implementation. What runs after a call in its
branch is `statement_trail` in
`src/beadloom/application/source_derivation/branches.py`, imported rather than
written again: two derivations of one fact are two things that can disagree, and
this epic has spent three waves on pairs that did. It lived in
`tests/test_init_branches_that_reach_the_bootstrap.py` until BDL-068 `.1` lifted
it, and this module is the third caller that made it worth lifting.
"""

from __future__ import annotations

import ast
import inspect
from dataclasses import dataclass
from pathlib import Path

import pytest

import beadloom
from beadloom.application.reindex import reindex
from beadloom.application.source_derivation import callee_name, statement_trail
from beadloom.onboarding.doc_generator import generate_skeletons

#: The writer this module is about, read off the function object so a rename
#: fails at import here rather than leaving a scan that finds no call site and
#: reports every claim below as satisfied.
THE_SKELETON_WRITER = generate_skeletons.__name__

#: The modules a re-index can be imported from: the one it is defined in, and
#: the package that re-exports it — which is the one every caller actually names.
#: Both are derived from the function object, and the re-export is PROBED in
#: `test_the_re_index_is_reachable_through_the_module_the_callers_import` rather
#: than assumed: a scan that knew only the defining module would find no import
#: in the product at all and report every caller as one that never re-indexes.
THE_REINDEX = reindex.__name__
THE_REINDEX_MODULES = frozenset(
    {reindex.__module__, reindex.__module__.rsplit(".", 1)[0]}
)

#: The parameter the writer takes, read off its signature. The claim below is
#: that every call site hands it the project root; the name of the thing it
#: hands over is the only evidence a source-level check has, and it is evidence
#: rather than proof — which is said out loud in the case that uses it.
THE_ONLY_PARAMETER = next(iter(inspect.signature(generate_skeletons).parameters))

#: The functions that call it today. Asserted against the DERIVED set rather
#: than used as one: a fifth call site fails here, and the failure asks the two
#: questions this module exists to ask — does it hand over the project root, and
#: does it re-index after rather than only before?
THE_CALLERS = frozenset(
    {"docs_generate", "init", "non_interactive_init", "interactive_init"}
)

#: The caller that re-indexes nowhere, named so its vacuity is visible. `docs
#: generate` is a standalone command: it patches the graph, prints a count and
#: ends, and nothing in that branch reads the index afterwards.
THE_CALLER_THAT_NEVER_RE_INDEXES = "docs_generate"


@dataclass(frozen=True)
class SkeletonCallSite:
    """One call to the skeleton writer, and what its branch does around it."""

    #: The function the call sits in.
    caller: str
    #: The file, relative to the package root, so a failure names a place.
    where: str
    #: Line number in that file.
    lineno: int
    #: The call as the source writes it, e.g. `generate_skeletons(project_root)`.
    source: str
    #: The argument names, positional then keyword, as the source spells them.
    arguments: tuple[str, ...]
    #: Whether a re-index can run before this call in this branch.
    re_indexes_before: bool
    #: Whether a re-index can run after it.
    re_indexes_after: bool


def _package_root() -> Path:
    return Path(inspect.getfile(beadloom)).parent


def _reindex_names_in(tree: ast.Module) -> set[str]:
    """The local names bound to a re-index function in this file.

    Derived from the file's own imports: `from beadloom.application.reindex
    import reindex as do_reindex` binds `do_reindex`, and every caller in the
    product spells it that way. A caller that imports the module and calls
    `reindex.reindex(...)` binds nothing here and would read as not re-indexing
    — the ceiling is stated in `test_a_caller_that_re_indexes_under_a_name_this_
    scan_cannot_see`.
    """
    return {
        alias.asname or alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module in THE_REINDEX_MODULES
        for alias in node.names
    }


def _argument_names(call: ast.Call) -> tuple[str, ...]:
    """Every argument as the source spells it, positional first."""
    return tuple(ast.unparse(argument) for argument in call.args) + tuple(
        f"{keyword.arg}={ast.unparse(keyword.value)}" for keyword in call.keywords
    )


def _calls_a_reindex(statement: ast.stmt, names: set[str]) -> bool:
    """Whether *statement* can reach a re-index, anywhere inside it.

    Anywhere, deliberately: `interactive_init`'s second re-index sits inside an
    `if files_created > 0`, which is the guard that makes it correct rather than
    a reason to discount it. The instrument answers "could this branch
    re-index", not "does it on every path" — the same limit
    `tests/test_init_branches_that_reach_the_bootstrap.py` declares for its
    verdict walk, and stated here rather than left to be rediscovered.
    """
    return any(
        isinstance(node, ast.Call) and callee_name(node) in names
        for node in ast.walk(statement)
    )


def _call_sites_in(source: str, where: str) -> list[SkeletonCallSite]:
    """Every call to the skeleton writer in *source*, with its branch read."""
    tree = ast.parse(source, filename=where)
    names = _reindex_names_in(tree)
    sites: list[SkeletonCallSite] = []
    for function in ast.walk(tree):
        if not isinstance(function, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        parents: dict[ast.AST, ast.AST] = {
            child: parent
            for parent in ast.walk(function)
            for child in ast.iter_child_nodes(parent)
        }
        for node in ast.walk(function):
            if not (
                isinstance(node, ast.Call)
                and callee_name(node) == THE_SKELETON_WRITER
            ):
                continue
            trail = statement_trail(_statement_holding(node, parents), parents)
            sites.append(
                SkeletonCallSite(
                    caller=function.name,
                    where=where,
                    lineno=node.lineno,
                    source=ast.unparse(node),
                    arguments=_argument_names(node),
                    re_indexes_before=any(
                        _calls_a_reindex(statement, names)
                        for block, index in trail
                        for statement in block[:index]
                    ),
                    re_indexes_after=any(
                        _calls_a_reindex(statement, names)
                        for block, index in trail
                        for statement in block[index + 1 :]
                    ),
                )
            )
    return sites


def _statement_holding(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> ast.stmt:
    """The statement *node* is part of, so the trail is walked from a statement.

    A call is an expression; `statement_trail` walks blocks, whose members are
    statements. Climbing to the enclosing statement first is what makes the two
    agree.
    """
    current = node
    while current in parents and not isinstance(current, ast.stmt):
        current = parents[current]
    assert isinstance(current, ast.stmt), f"no enclosing statement for {node!r}"
    return current


def _the_call_sites() -> list[SkeletonCallSite]:
    """Every call site in the product, derived from its source."""
    root = _package_root()
    return [
        site
        for path in sorted(root.rglob("*.py"))
        for site in _call_sites_in(
            path.read_text(encoding="utf-8"), str(path.relative_to(root))
        )
    ]


@pytest.fixture(scope="module")
def call_sites() -> list[SkeletonCallSite]:
    return _the_call_sites()


#: A caller with the shape `.18` established: write the skeletons, then re-index
#: what they patched. The mutants below are edits of this one, so what the scan
#: says about each is a difference that edit makes and nothing else.
A_CALLER_THAT_RE_INDEXES_AFTER = """
from beadloom.application.reindex import reindex as do_reindex


def scaffold(project_root):
    bootstrap_project(project_root)
    result = SKELETONS(project_root)
    do_reindex(project_root)
    return result
""".replace("SKELETONS", THE_SKELETON_WRITER)

#: The same caller with the two lines swapped: it re-indexes and then patches the
#: graph, so the index it leaves behind describes a file that has changed since.
#: This is `.18`'s defect with a new author, and it is what must fail.
A_CALLER_THAT_RE_INDEXES_ONLY_BEFORE = """
from beadloom.application.reindex import reindex as do_reindex


def scaffold(project_root):
    bootstrap_project(project_root)
    do_reindex(project_root)
    return SKELETONS(project_root)
""".replace("SKELETONS", THE_SKELETON_WRITER)

#: The wizard's shape: a re-index before, and a second one after under a guard.
#: The scan must accept it — a check that called every re-index-before a defect
#: would fail the product as it stands and be no more informative than one that
#: called none of them.
A_CALLER_THAT_RE_INDEXES_BEFORE_AND_AFTER = """
from beadloom.application.reindex import reindex as do_reindex


def scaffold(project_root):
    bootstrap_project(project_root)
    do_reindex(project_root)
    result = SKELETONS(project_root)
    if result["files_created"] > 0:
        do_reindex(project_root)
    return result
""".replace("SKELETONS", THE_SKELETON_WRITER)

#: A caller that hands over part of the tree. The parameter that used to let it
#: pass a node list is gone, so this is the shape the mistake has left: the same
#: single argument, a different path.
A_CALLER_THAT_HANDS_OVER_PART_OF_THE_TREE = A_CALLER_THAT_RE_INDEXES_AFTER.replace(
    f"{THE_SKELETON_WRITER}(project_root)",
    f"{THE_SKELETON_WRITER}(project_root / 'docs')",
)


class TestTheScanItself:
    """The instrument, before anything is trusted to it.

    A scan that found no call site would make every claim below pass over an
    empty set, which is the failure mode this epic keeps meeting one level down.
    """

    def test_it_finds_call_sites_to_judge(
        self, call_sites: list[SkeletonCallSite]
    ) -> None:
        assert call_sites, (
            f"no call to {THE_SKELETON_WRITER!r} was found in the product, so "
            "every case below asserts nothing"
        )

    def test_it_finds_the_callers_the_product_has(
        self, call_sites: list[SkeletonCallSite]
    ) -> None:
        """Equality, so a fifth caller fails here and gets asked the questions."""
        found = {site.caller for site in call_sites}

        assert found == THE_CALLERS, (
            f"the set of functions calling {THE_SKELETON_WRITER!r} has changed. "
            f"Added: {sorted(found - THE_CALLERS)}; gone: "
            f"{sorted(THE_CALLERS - found)}. A new caller hands over the project "
            "root and re-indexes after the call, not only before it."
        )

    def test_it_reads_the_two_orders_the_product_actually_uses(self) -> None:
        """Both shapes are correct and they are not the same shape.

        Stated over the synthetic pair rather than over the product, so the two
        readings are a difference the source text makes. If these ever agree,
        the scan has stopped distinguishing before from after and every case in
        the class below is satisfied by anything.
        """
        [after] = _call_sites_in(A_CALLER_THAT_RE_INDEXES_AFTER, "synthetic.py")
        [both] = _call_sites_in(A_CALLER_THAT_RE_INDEXES_BEFORE_AND_AFTER, "synthetic.py")

        assert (after.re_indexes_before, after.re_indexes_after) == (False, True)
        assert (both.re_indexes_before, both.re_indexes_after) == (True, True)

    def test_it_reports_a_caller_that_re_indexes_only_before(self) -> None:
        """The failure this module exists to produce, produced on demand."""
        assert A_CALLER_THAT_RE_INDEXES_ONLY_BEFORE != A_CALLER_THAT_RE_INDEXES_AFTER, (
            "the anchor the mutation edits is gone, so this case is judging the "
            "unmutated caller and the swap it names never happened"
        )

        [site] = _call_sites_in(A_CALLER_THAT_RE_INDEXES_ONLY_BEFORE, "synthetic.py")

        assert (site.re_indexes_before, site.re_indexes_after) == (True, False)

    def test_it_reads_the_argument_a_call_site_hands_over(self) -> None:
        """Anti-vacuity for the shape case: the scan must see a wrong one."""
        [good] = _call_sites_in(A_CALLER_THAT_RE_INDEXES_AFTER, "synthetic.py")
        [bad] = _call_sites_in(A_CALLER_THAT_HANDS_OVER_PART_OF_THE_TREE, "synthetic.py")

        assert good.arguments == (THE_ONLY_PARAMETER,)
        assert bad.arguments != good.arguments

    def test_the_re_index_is_reachable_through_the_module_the_callers_import(
        self,
    ) -> None:
        """The scan's premise, probed rather than assumed.

        `reindex` is defined in `...reindex.full` and re-exported by the package
        beside it, and every caller in the product imports the package. A scan
        that accepted only the defining module would match no import anywhere and
        report the whole product as re-indexing nowhere, which is a green run
        over a claim nobody made.
        """
        from importlib import import_module

        assert [
            module
            for module in THE_REINDEX_MODULES
            if getattr(import_module(module), THE_REINDEX, None) is reindex
        ], THE_REINDEX_MODULES

    def test_a_caller_that_re_indexes_under_a_name_this_scan_cannot_see(self) -> None:
        """The ceiling, stated as a case rather than as a sentence in a docstring.

        The re-index names are read off each file's `from ... import` statements,
        so a caller that imports the module and reaches the function through it
        reads as one that never re-indexes — and is then accepted vacuously. No
        caller in the product does this; the day one does, the acceptance below
        is silent, and this case is the record of why.
        """
        through_the_module = """
from beadloom.application import reindex as reindex_module


def scaffold(project_root):
    reindex_module.reindex(project_root)
    return SKELETONS(project_root)
""".replace("SKELETONS", THE_SKELETON_WRITER)

        [site] = _call_sites_in(through_the_module, "synthetic.py")

        assert site.re_indexes_before is False


class TestEveryCallSiteHandsOverTheWholeTree:
    """One argument is what the signature enforces; WHICH one is not.

    `test_the_skeleton_writer_cannot_be_handed_a_subset_of_the_tree` in
    `tests/test_init_one_table_over_every_axis.py` states the signature claim and
    is not repeated here. This is the other half: the renderer builds
    `docs/architecture.md` for the project at the path it is given, so a caller
    that hands over a subdirectory gets a whole-tree document about a tree that
    is not the adopter's.
    """

    def test_every_call_site_passes_exactly_the_project_root(
        self, call_sites: list[SkeletonCallSite]
    ) -> None:
        """Evidence rather than proof, and said so.

        A source-level check can compare the spelling of the argument, not the
        value it holds. Every caller in the product names the project root
        `project_root`, so a call site that hands over something else is visible
        as a different spelling — which is the most a scan can say and more than
        nothing was saying before.
        """
        wrong = [
            f"{site.where}:{site.lineno} {site.source}"
            for site in call_sites
            if site.arguments != (THE_ONLY_PARAMETER,)
        ]

        assert wrong == [], (
            f"{THE_SKELETON_WRITER} renders a document about the whole project "
            "at the path it is given, and these call sites give it something "
            f"else: {wrong}"
        )


class TestEveryCallerThatReIndexesReIndexesAfterTheSkeletons:
    """The order rule, over the callers rather than over the one `.18` fixed.

    `generate_skeletons` patches `docs:` into the graph YAML of every node it
    writes a document for, so an index taken before it and not after it describes
    a graph file that has changed since. `.18` measured that from the other side:
    with the call inside the bootstrap block, `--yes --mode both` judged an index
    that predated the last graph file the command wrote, `init` returned 0 and
    the adopter's next `lint --strict` returned 1.

    The claim is conditional because the product holds two correct shapes and
    only one of them puts the call first. What both share is that the LAST
    re-index in the branch comes after the patch.
    """

    def test_there_is_a_caller_that_re_indexes(
        self, call_sites: list[SkeletonCallSite]
    ) -> None:
        """Anti-vacuity: a product where nobody re-indexes satisfies the rule."""
        assert [site for site in call_sites if site.re_indexes_after], call_sites

    def test_no_caller_re_indexes_only_before_the_skeletons(
        self, call_sites: list[SkeletonCallSite]
    ) -> None:
        stale = [
            f"{site.where}:{site.lineno} in {site.caller}"
            for site in call_sites
            if site.re_indexes_before and not site.re_indexes_after
        ]

        assert stale == [], (
            f"these call sites re-index and then let {THE_SKELETON_WRITER} patch "
            f"the graph, so the index they leave is already stale: {stale}"
        )

    def test_the_caller_that_re_indexes_nowhere_is_the_one_that_is_declared(
        self, call_sites: list[SkeletonCallSite]
    ) -> None:
        """A vacuous cell named, so it cannot grow quietly.

        A caller that re-indexes neither before nor after passes the case above
        by having nothing to order. One does — `docs generate` takes no verdict
        and reads no index afterwards — and a second one appearing is a thing to
        decide rather than to inherit.
        """
        never = {
            site.caller
            for site in call_sites
            if not site.re_indexes_before and not site.re_indexes_after
        }

        assert never == {THE_CALLER_THAT_NEVER_RE_INDEXES}, never
