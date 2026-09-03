"""Every branch of `init` that writes a graph file, read out of the source.

BDL-067 `.7`, covering `.6`. The defect `.6` fixed was that the default wizard
took no verdict over the graph it had just written. The defect *this* module
exists for is one level up, and it is the reason the wizard shipped unguarded
through four green waves: the suite could not tell a monkeypatch **binding**
from a **branch** of `init`.

`init --yes` and the default wizard both reach `bootstrap_project` through the
name `init_flow` bound at import time, so one `monkeypatch.setattr` sabotages
both; `init --bootstrap` imports the function inside the command body and needs
its own patch. Two bindings, three branches. The behavioural module
(`tests/test_init_verdict_over_its_own_rules.py`) counted the bindings, a
comment called them "the two ways `init` reaches the bootstrap", and the branch
a human adopter meets first was never run.

`.6` corrected that count by hand, which leaves the same defect available at a
larger number: `THE_BRANCHES` is a tuple somebody maintains, and a fourth branch
added to the command joins the code without joining the tuple. So nothing here
is written out by hand. The command's own source is parsed, every call that
reaches a graph write is found, and each one is asserted to be followed by the
Gate's verdict. A fourth branch fails these tests on the day it is written,
whether or not anyone remembers this file.

BDL-067 `.15` WIDENED THE SEED, and the reason is the claim the paragraph above
used to make about a *writer*. Until `.15` the reachability scan started at
`bootstrap_project` alone, so it enumerated the branches that reach ONE writer
and its docstring promised the branches that reach the graph. `import_docs` —
the second function that creates `domain` nodes, in `.beadloom/_graph/
imported.yml` — was outside the instrument for the whole of this epic, which is
how `.14`'s defect reached a fifth wave with 112 green tests over it. The scan is
now seeded from the one commit point every graph YAML routes through
(`infrastructure.atomic_io.write_yaml_atomic`, which says so in its own
docstring), so "writes a graph file" is derived from the source rather than
listed here, and a THIRD writer joins the instrument on the day it is written.
The seed's soundness is itself checked: `TestNoGraphFileIsWrittenPastTheCommitPoint`
fails if a writer ever serialises YAML to disk without going through it, because
such a writer would be invisible to every scan below.

The instrument is tested before it is trusted (`TestTheEnumeratorItself`): a
scan that silently found nothing would make every assertion below pass while
asserting nothing, which is the exact failure mode this bead is about. The
synthetic commands there are mutants of the real shape — a fourth branch with no
verdict, a fourth branch with one, a verdict written after the `return` that
makes it unreachable, and (from `.15`) a fourth branch that writes a graph file
WITHOUT bootstrapping, which the old seed reported as clean and the new one
reports. That last case is where the two seeds disagree, so it is stated as a
difference between them rather than as a story about one.

Known limits, stated rather than discovered later:

- Reachability is matched on the callee's *name*, not on a resolved import, so
  two same-named functions in the package are one name here. The set it produces
  is asserted to contain the names that actually matter. `.15` widened the scan
  from `beadloom.onboarding` to the whole `beadloom` package, which removes the
  older limit that a branch reaching a writer through another package would not
  be seen — `link` and `update_node_in_yaml` are writers outside onboarding —
  and it was measured not to change the bootstrap-seeded call sites.
- A verdict call anywhere in a following statement counts, including inside an
  `if` whose condition is some unrelated path. The enumerator answers "could
  this branch report", not "does it report on every path".
- **The check is syntactic, and that is its ceiling.** It reads a verdict call
  after a branch; it cannot read what the verdict SEES. `--yes --mode both`
  carried the call and passed this module while judging an index written before
  the run's last graph file, and reported clean over a tree the adopter's next
  `lint --strict` failed. Nothing here could have caught that, and nothing here
  can. The behavioural half is `tests/test_init_agrees_across_its_modes.py`,
  which runs the modes and compares the verdict against the Gate; this module is
  cited there and that module is cited here so neither is read as the whole
  claim.
"""

from __future__ import annotations

import inspect
import sys
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import NoReturn

import pytest

import beadloom
from beadloom.application.source_derivation import (
    CallSite,
    call_sites_in,
    callables_that_reach,
    direct_callers_of,
    functions_that_serialise_yaml_to_disk,
    never_returns,
)
from beadloom.infrastructure.atomic_io import write_yaml_atomic
from beadloom.onboarding.scanner.bootstrap import bootstrap_project
from beadloom.services.commands import setup as init_command
from tests.test_init_verdict_over_its_own_rules import THE_BRANCHES

#: The name of the function that takes the Gate's verdict, read off the function
#: object instead of written out: a rename fails at import here rather than
#: leaving a scan that quietly finds no verdict anywhere and reports every branch
#: as unguarded.
THE_VERDICT = init_command._verdict_on_the_generated_graph.__name__

#: The narrow seed: one writer, and the one this epic started from.
THE_BOOTSTRAP = bootstrap_project.__name__

#: The wide seed, and the reason `.15` exists. Every graph YAML in the product
#: is committed by this one function — `infrastructure/atomic_io.py` states that
#: as its purpose and `TestNoGraphFileIsWrittenPastTheCommitPoint` checks it — so
#: "this function writes a graph file" is answerable from the source instead of
#: from a list. Read off the function object for the same reason `THE_VERDICT`
#: is: a rename must fail at import rather than leave a scan that finds nothing.
THE_GRAPH_COMMIT_POINT = write_yaml_atomic.__name__

#: The command under examination, by the name it has in its module.
THE_COMMAND = "init"

#: The functions that call the commit point directly, as BDL-067 `.14`'s sweep
#: of `src/` enumerated them by hand. It is asserted against the DERIVED set
#: rather than used as one: the scan has to rediscover these six on its own, and
#: a seventh must fail here so that somebody asks whether `init` reaches it.
#: Exactly two of them create nodes (`bootstrap_project`, `import_docs`) and both
#: carry the domain-parent post-condition; the other four patch a node that
#: already exists or write rules, and cannot produce an unparented node.
THE_WRITERS_THE_SWEEP_FOUND = frozenset(
    {
        "bootstrap_project",  # services.yml — creates nodes
        "import_docs",  # imported.yml — creates nodes
        "generate_rules",  # rules.yml — no nodes
        "update_node_in_yaml",  # patches summary/source on an existing node
        "_patch_docs_field",  # adds `docs:` to an existing node
        "link",  # adds/removes `links:` on an existing node
    }
)


@dataclass(frozen=True)
class DeferredBranch:
    """A branch that writes a graph file and deliberately takes no verdict.

    One exists, and a declared exception is only worth the check that follows it,
    so both halves are here: `because` is the reason a human has to agree with,
    and `tells_the_adopter` is a string the branch's own remaining source must
    contain. A deferral that stopped telling the adopter what to do next stops
    being a deferral and becomes a silent skip, and fails
    `test_every_deferred_branch_hands_the_work_back_to_the_adopter`.
    """

    #: The `if` conditions the branch sits under, as `init`'s source spells them.
    guard: tuple[str, ...]
    #: Why judging this branch would report a state nobody is in yet.
    because: str
    #: What the branch must still tell the adopter, since it judges nothing.
    tells_the_adopter: str


#: No branch of `init` defers any more, and that is the whole of BDL-067 `.17`'s
#: part 2(a). The one entry here was `--import`, deferred because it re-indexed
#: nothing and told the adopter to run `beadloom reindex` — so there was no index
#: of its own output for a verdict to read. `.17` gave that branch the reindex
#: instead of the instruction, which removes the reason rather than the check.
#:
#: The carve-out was safe only until the next `init` on the same tree. The
#: wizard's re-init does not delete `.beadloom/`, so `imported.yml` survived into
#: a later bootstrap that wrote `domain-needs-parent` and met nodes an earlier run
#: had left unparented — reported by a run that had written neither (the review of
#: `.16`, major 2). A deferral is a decision about ONE branch, and this epic's
#: standing lesson is that a decision about one branch is the shape the next
#: neighbour is found in.
#:
#: The machinery stays. An empty tuple makes the two cases below vacuous, so both
#: are stated as functions and exercised against a synthetic declaration in
#: `TestTheDeferralChecksStillBite`: a deferral declared tomorrow is checked by
#: code that was checked today.
THE_DEFERRED_BRANCHES: tuple[DeferredBranch, ...] = ()


def _deferrals_naming_a_branch_that_is_gone(
    sites: tuple[CallSite, ...], declared: tuple[DeferredBranch, ...]
) -> set[tuple[str, ...]]:
    """Declared guards that no unjudged branch of the source has."""
    unjudged = {site.guard for site in sites if not site.reaches_marker}
    return {branch.guard for branch in declared} - unjudged


def _deferrals_that_tell_the_adopter_nothing(
    sites: tuple[CallSite, ...], declared: tuple[DeferredBranch, ...]
) -> list[str]:
    """Declared deferrals whose branch no longer carries its own instruction."""
    by_guard = {site.guard: site for site in sites}
    silent: list[str] = []
    for branch in declared:
        site = by_guard.get(branch.guard)
        if site is None:
            silent.append(f"no branch under {branch.guard}: {branch.because}")
        elif branch.tells_the_adopter not in site.follows:
            silent.append(
                f"the branch under {branch.guard} takes no verdict and no longer "
                f"tells the adopter {branch.tells_the_adopter!r}: {site.follows!r}"
            )
    return silent


def _package_root() -> Path:
    """The product's own source tree, which is what every scan here reads."""
    return Path(inspect.getfile(beadloom)).parent


def _call_sites_in(source: str, reaching: frozenset[str]) -> tuple[CallSite, ...]:
    """The derivation's reading of `init`, bound to this command's own names.

    `source_derivation.call_sites_in` answers "where, in this command, does a
    call from *reaching* sit, and can *marker* still run after it". What this
    module supplies is which command, which marker, and the module terminator
    names are resolved through — all three read off the product's own objects, so
    a rename fails at import here rather than leaving a scan that finds nothing.
    """
    return call_sites_in(
        source,
        reaching,
        command=THE_COMMAND,
        marker=THE_VERDICT,
        resolving_in=init_command,
    )


def _the_commands_source() -> str:
    """The source file `init` is defined in, as the imported module resolves it."""
    return Path(inspect.getfile(init_command)).read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def reaching() -> frozenset[str]:
    """The names that end in a bootstrap, derived from the package's source."""
    return callables_that_reach(_package_root(), THE_BOOTSTRAP)


@pytest.fixture(scope="module")
def writing() -> frozenset[str]:
    """The names that end in a graph-file write, derived the same way.

    A superset of `reaching`: the bootstrap is one writer among six, so every
    branch the narrow seed finds is found here too, and the branches that reach
    some OTHER writer are found only here.
    """
    return callables_that_reach(_package_root(), THE_GRAPH_COMMIT_POINT)


@pytest.fixture(scope="module")
def call_sites(reaching: frozenset[str]) -> tuple[CallSite, ...]:
    """Every bootstrap-reaching call in the real `init`, in source order."""
    return _call_sites_in(_the_commands_source(), reaching)


@pytest.fixture(scope="module")
def writer_call_sites(writing: frozenset[str]) -> tuple[CallSite, ...]:
    """Every call in the real `init` that ends in a graph-file write."""
    return _call_sites_in(_the_commands_source(), writing)


#: A command with the shape the real one has: two flag branches that return, and
#: a fallthrough wizard. The mutants below are edits of this, so what the
#: enumerator says about them is a difference this text makes and nothing else.
A_COMMAND_LIKE_INIT = """
def init(*, non_interactive, bootstrap, rescan, project):
    project_root = project
    if non_interactive:
        result = non_interactive_init(project_root)
        click.echo(result)
        VERDICT(project_root)
        return
    if bootstrap:
        result = bootstrap_project(project_root)
        VERDICT(project_root)
        return
    result = interactive_init(project_root)
    if result["mode"] == "cancelled":
        sys.exit(0)
    if result["mode"] in ("bootstrap", "both"):
        VERDICT(project_root)
""".replace("VERDICT", THE_VERDICT)

#: A fourth branch, written the way a fourth branch gets written: it bootstraps
#: and returns, and nobody remembered the verdict. This is what must fail.
A_FOURTH_BRANCH_WITHOUT_A_VERDICT = A_COMMAND_LIKE_INIT.replace(
    "    result = interactive_init(project_root)",
    "    if rescan:\n"
    "        result = bootstrap_project(project_root)\n"
    "        return\n"
    "    result = interactive_init(project_root)",
)

#: The same fourth branch, guarded. The enumerator must accept it — a test that
#: called every fourth branch a defect would be no more informative than one that
#: called none of them.
A_FOURTH_BRANCH_WITH_A_VERDICT = A_COMMAND_LIKE_INIT.replace(
    "    result = interactive_init(project_root)",
    "    if rescan:\n"
    "        result = bootstrap_project(project_root)\n"
    f"        {THE_VERDICT}(project_root)\n"
    "        return\n"
    "    result = interactive_init(project_root)",
)

#: A verdict that is present in the branch and cannot run: the `return` is above
#: it. Reading the file for the call name alone would call this branch guarded.
A_VERDICT_BELOW_THE_RETURN = A_COMMAND_LIKE_INIT.replace(
    f"        {THE_VERDICT}(project_root)\n        return\n",
    f"        return\n        {THE_VERDICT}(project_root)\n",
    1,
)

#: BDL-067 `.21`. The same defect as `A_VERDICT_BELOW_THE_RETURN`, leaving
#: through `sys.exit` instead of `return` — the shape the real `init` had, and
#: the reason this module reported the wizard's `cancel` answer as guarded. It
#: is written as a mutant rather than measured on `init` because `init` no
#: longer contains a `sys.exit`: `.21` removed the one it had rather than
#: leaving the instrument to be the only thing standing between an adopter and
#: a graph nobody checked. The mutant is what keeps the classifier honest after
#: the call site it was written for is gone.
A_VERDICT_BELOW_A_SYS_EXIT = A_VERDICT_BELOW_THE_RETURN.replace(
    "        return\n", "        sys.exit(0)\n", 1
)


#: BDL-067 `.15`. A fourth branch that writes a graph file WITHOUT bootstrapping
#: — the shape `import_docs` already has in the real command — and takes no
#: verdict. It is the case the two seeds disagree about, and it is written here
#: as a synthetic mutant rather than measured on `init` itself because the real
#: deferral is a decision: this one is the same shape with the decision removed.
A_FOURTH_BRANCH_THAT_WRITES_WITHOUT_BOOTSTRAPPING = A_COMMAND_LIKE_INIT.replace(
    "    result = interactive_init(project_root)",
    "    if rescan:\n"
    "        result = import_docs(project_root, project_root)\n"
    "        return\n"
    "    result = interactive_init(project_root)",
)


#: BDL-067 `.17`. The same fourth branch, deferring OUT LOUD: it writes a graph
#: file, takes no verdict, and tells the adopter what to run instead. This is the
#: shape a declared deferral has to have, and `TestTheDeferralChecksStillBite`
#: uses it because `THE_DEFERRED_BRANCHES` is now empty and the real command has
#: no such branch left to read the check against.
A_FOURTH_BRANCH_THAT_DEFERS_AND_SAYS_SO = A_COMMAND_LIKE_INIT.replace(
    "    result = interactive_init(project_root)",
    "    if rescan:\n"
    "        result = import_docs(project_root, project_root)\n"
    "        click.echo('Next: run beadloom reindex')\n"
    "        return\n"
    "    result = interactive_init(project_root)",
)


class TestTheEnumeratorItself:
    """The instrument, before anything is trusted to it.

    An enumerator that found nothing would make every assertion in the next two
    classes pass over an empty set. That is the shape of the defect this bead
    closes, so it is asserted against here rather than assumed away.
    """

    def test_it_finds_the_callables_init_reaches_the_bootstrap_through(
        self, reaching: frozenset[str]
    ) -> None:
        """The three known ones, derived — not a list this test wrote down."""
        assert {THE_BOOTSTRAP, "non_interactive_init", "interactive_init"} <= reaching

    def test_it_reads_the_baseline_shape_as_three_branches(
        self, reaching: frozenset[str]
    ) -> None:
        """Two guarded branches and a fallthrough, which is `init`'s shape."""
        sites = _call_sites_in(A_COMMAND_LIKE_INIT, reaching)

        assert [site.guard for site in sites] == [("non_interactive",), ("bootstrap",), ()]

    def test_it_reports_a_fourth_branch_that_bootstraps_without_a_verdict(
        self, reaching: frozenset[str]
    ) -> None:
        """The failure this whole module exists to produce, produced on demand."""
        assert A_FOURTH_BRANCH_WITHOUT_A_VERDICT != A_COMMAND_LIKE_INIT, (
            "the anchor the mutation edits is gone, so this case is judging the "
            "unmutated command and the mutation it names never happened"
        )

        sites = _call_sites_in(A_FOURTH_BRANCH_WITHOUT_A_VERDICT, reaching)

        assert [site.guard for site in sites if not site.reaches_marker] == [("rescan",)]

    def test_it_accepts_a_fourth_branch_that_does_take_the_verdict(
        self, reaching: frozenset[str]
    ) -> None:
        assert A_FOURTH_BRANCH_WITH_A_VERDICT != A_COMMAND_LIKE_INIT, (
            "the anchor the mutation edits is gone"
        )

        sites = _call_sites_in(A_FOURTH_BRANCH_WITH_A_VERDICT, reaching)

        assert [site.guard for site in sites if not site.reaches_marker] == []
        assert ("rescan",) in [site.guard for site in sites]

    def test_it_does_not_count_a_verdict_the_return_above_it_makes_unreachable(
        self, reaching: frozenset[str]
    ) -> None:
        """Presence of the call is not the claim. Reaching it is."""
        assert A_VERDICT_BELOW_THE_RETURN != A_COMMAND_LIKE_INIT, (
            "the anchor the mutation edits is gone"
        )

        sites = _call_sites_in(A_VERDICT_BELOW_THE_RETURN, reaching)

        assert [site.guard for site in sites if not site.reaches_marker] == [("non_interactive",)]

    def test_it_does_not_count_a_verdict_a_sys_exit_above_it_makes_unreachable(
        self, reaching: frozenset[str]
    ) -> None:
        """The same claim as the case above, for the other way out.

        Measured by the review of `.20` against this module's own helpers:
        `A_VERDICT_BELOW_THE_RETURN` reported `[('non_interactive', False), ...]`
        and the same shape with `sys.exit(0)` reported `[('non_interactive',
        True), ...]`. One defect, read two ways, according to which word the
        branch used to leave.
        """
        assert A_VERDICT_BELOW_A_SYS_EXIT != A_VERDICT_BELOW_THE_RETURN, (
            "the anchor the mutation edits is gone, so this case is judging the "
            "`return` mutant and the exit it names never happened"
        )

        sites = _call_sites_in(A_VERDICT_BELOW_A_SYS_EXIT, reaching)

        assert [site.guard for site in sites if not site.reaches_marker] == [
            ("non_interactive",)
        ]

    def test_the_two_ways_out_are_read_the_same_way(
        self, reaching: frozenset[str]
    ) -> None:
        """Anti-vacuity for the case above: the difference must be the WORD.

        The two mutants differ in one statement and in nothing else, so if they
        ever read differently again, the classifier has started answering a
        question about spelling rather than about control flow.
        """
        by_return = _call_sites_in(A_VERDICT_BELOW_THE_RETURN, reaching)
        by_exit = _call_sites_in(A_VERDICT_BELOW_A_SYS_EXIT, reaching)

        assert [site.reaches_marker for site in by_return] == [
            site.reaches_marker for site in by_exit
        ]

    def test_the_writer_seed_finds_the_writers_the_sweep_found_by_hand(
        self, writing: frozenset[str]
    ) -> None:
        """The scan rediscovers BDL-067 `.14`'s enumeration of `src/`.

        Equality rather than containment, deliberately. A seventh function that
        commits a graph file fails here, and the failure asks the one question
        `.14`'s sweep had to be run by hand to answer: does `init` reach it, and
        does that branch take a verdict? Containment would let the seventh writer
        arrive in silence, which is the defect this module is named after one
        level down.
        """
        committing = direct_callers_of(_package_root(), THE_GRAPH_COMMIT_POINT)

        assert committing == THE_WRITERS_THE_SWEEP_FOUND, (
            "the set of functions that commit a graph file has changed. Added: "
            f"{sorted(committing - THE_WRITERS_THE_SWEEP_FOUND)}; gone: "
            f"{sorted(THE_WRITERS_THE_SWEEP_FOUND - committing)}. A new writer "
            "needs the domain-parent post-condition if it creates nodes, and "
            "every branch of `init` that reaches it needs a verdict."
        )

    def test_the_writer_seed_reports_a_branch_the_bootstrap_seed_calls_clean(
        self,
        reaching: frozenset[str],
        writing: frozenset[str],
    ) -> None:
        """BDL-067 `.15`, stated as the difference between the two seeds.

        The same synthetic command, read twice. Seeded from `bootstrap_project`
        the fourth branch is invisible — it writes `imported.yml` and never
        bootstraps — and the module would have reported the command clean while
        its docstring claimed to cover "a fourth branch". Seeded from the commit
        point it is found. That gap is what let `import_docs` sit outside the
        instrument for the whole epic.
        """
        assert (
            A_FOURTH_BRANCH_THAT_WRITES_WITHOUT_BOOTSTRAPPING != A_COMMAND_LIKE_INIT
        ), "the anchor the mutation edits is gone"

        by_bootstrap = _call_sites_in(
            A_FOURTH_BRANCH_THAT_WRITES_WITHOUT_BOOTSTRAPPING, reaching
        )
        by_writer = _call_sites_in(
            A_FOURTH_BRANCH_THAT_WRITES_WITHOUT_BOOTSTRAPPING, writing
        )

        assert ("rescan",) not in [site.guard for site in by_bootstrap], (
            "the narrow seed now sees the writer branch, so this case no longer "
            "states the difference it was written for"
        )
        assert [site.guard for site in by_writer if not site.reaches_marker] == [
            ("rescan",)
        ]


class TestTheTerminatorClassifierItself:
    """`_ends_the_branch` is the walk's only claim about control flow.

    A terminator it fails to recognise does not fail anything: it is read as a
    statement the branch continues past, so a verdict written below it counts and
    the branch reads guarded. That is not a hypothetical — it is exactly what
    happened, and the two cases here are the two ways the classifier can answer.
    """

    def test_sys_exit_really_does_not_return(self) -> None:
        """Probed, not assumed. The classifier's premise is a runtime fact."""
        with pytest.raises(SystemExit):
            sys.exit(0)

        assert never_returns("sys.exit", init_command)

    def test_a_callable_annotated_no_return_is_a_terminator(self) -> None:
        """The derivation, over a callable this module did not name anywhere.

        This is what makes the set derived rather than listed: a helper written
        tomorrow joins it by carrying the annotation.
        """

        def stop() -> NoReturn:
            raise SystemExit(1)

        assert never_returns("stop", SimpleNamespace(stop=stop))

    def test_a_call_the_command_continues_past_is_not_a_terminator(self) -> None:
        """Anti-vacuity: a classifier that said yes to everything would pass."""
        assert not never_returns("click.echo", init_command)

    def test_a_name_the_command_module_does_not_have_is_not_a_terminator(self) -> None:
        """An unresolvable name is read as continuing, and that is the ceiling.

        Stated as a case rather than as a sentence in a docstring: a way out
        this module cannot resolve is read as a branch that carries on, so the
        behavioural axis in `tests/test_every_wizard_answer_is_judged.py` is
        what covers the forms this one cannot enumerate.
        """
        assert not never_returns("nothing_by_this_name.exit", init_command)


class TestNoGraphFileIsWrittenPastTheCommitPoint:
    """The wide seed is only sound while the commit point is the only way out.

    `write_yaml_atomic` is documented as the single commit point for every graph
    YAML, and the scans above are seeded from that documented fact. A writer that
    serialised YAML and wrote it itself would be invisible to all of them — the
    enumerator would report clean over a command that writes a graph file on an
    unjudged branch, which is the failure mode this module exists to prevent.
    So the fact is checked rather than trusted.
    """

    #: The one function that legitimately does both. It writes
    #: `.beadloom/flow.yml` — the role-configurator's file, read by
    #: `setup-agentic-flow` — which is not a graph file and holds no node, so no
    #: scan here needs to reach it.
    THE_DECLARED_EXCEPTION = frozenset({"persist_flow_config"})

    def _functions_that_serialise_yaml_to_disk(self) -> dict[str, str]:
        """The derivation's answer, each function named with where it is."""
        root = _package_root()
        return {
            name: f"{where.path.relative_to(root)}:{where.lineno}"
            for name, where in functions_that_serialise_yaml_to_disk(root).items()
        }

    def test_the_scan_finds_something_to_judge(self) -> None:
        """Anti-vacuity: a scan that matched nothing would pass the next case."""
        assert direct_callers_of(_package_root(), THE_GRAPH_COMMIT_POINT), (
            f"no function calls {THE_GRAPH_COMMIT_POINT!r}, so the wide seed is "
            "empty and every writer-seeded assertion below asserts nothing"
        )

    def test_every_yaml_written_to_disk_goes_through_the_commit_point(self) -> None:
        found = self._functions_that_serialise_yaml_to_disk()
        bypassing = {
            name: where
            for name, where in found.items()
            if name not in self.THE_DECLARED_EXCEPTION
            and name != THE_GRAPH_COMMIT_POINT
        }

        assert not bypassing, (
            "these functions serialise YAML and write it themselves, so the "
            f"commit-point seed cannot see them: {bypassing}. If any of them "
            "writes under `.beadloom/_graph/`, route it through "
            f"{THE_GRAPH_COMMIT_POINT!r}; if none does, declare it here with the "
            "file it writes and why that file is not a graph file."
        )

    def test_the_declared_exception_still_exists(self) -> None:
        """A carve-out for a function nobody has fails nothing and hides that."""
        found = self._functions_that_serialise_yaml_to_disk()

        assert set(found) >= self.THE_DECLARED_EXCEPTION, (
            "declared exceptions that no longer serialise YAML to disk: "
            f"{sorted(self.THE_DECLARED_EXCEPTION - set(found))}"
        )


class TestEveryBranchOfInitThatWritesAGraphFileTakesAVerdict:
    """The claim the class below makes about the bootstrap, made about the graph.

    BDL-067 `.15`. `init` writes graph files through more than one function, and
    the branch that reaches the second one was outside every scan in this module
    until now.
    """

    def test_the_scan_finds_branches_to_judge(
        self, writer_call_sites: tuple[CallSite, ...]
    ) -> None:
        """Anti-vacuity: an empty scan would pass every assertion below it."""
        assert writer_call_sites, (
            f"no call reaching {THE_GRAPH_COMMIT_POINT} was found in "
            f"`{THE_COMMAND}` — the enumeration below would assert nothing"
        )

    def test_it_sees_branches_the_bootstrap_seeded_scan_does_not(
        self,
        call_sites: tuple[CallSite, ...],
        writer_call_sites: tuple[CallSite, ...],
    ) -> None:
        """Measured on the real command, so the widening is not just intended.

        If this ever stops holding, the two seeds have converged and one of them
        is redundant — which is a thing to decide, not to discover.
        """
        narrow = {(site.callee, site.lineno) for site in call_sites}
        wide = {(site.callee, site.lineno) for site in writer_call_sites}

        assert narrow < wide, (
            "the writer seed no longer sees more of `init` than the bootstrap "
            f"seed: narrow={sorted(narrow)}, wide={sorted(wide)}"
        )

    def test_no_branch_writes_a_graph_file_without_a_verdict_or_a_declared_deferral(
        self, writer_call_sites: tuple[CallSite, ...]
    ) -> None:
        """A third writer reached from an unjudged branch fails here.

        The deferral is named by its guard rather than by the function it calls,
        because the decision is about the branch: `import_docs` runs under
        `--yes --mode both` too, and there it is judged.
        """
        deferred = {branch.guard for branch in THE_DEFERRED_BRANCHES}
        unguarded = [
            f"{site.callee} at line {site.lineno} under {site.guard or '<no flag>'}"
            for site in writer_call_sites
            if not site.reaches_marker and site.guard not in deferred
        ]

        assert unguarded == [], (
            "a branch of `init` writes a file into `.beadloom/_graph/` and never "
            f"checks it against the rules on disk beside it: {unguarded}"
        )

    def test_no_deferral_is_declared_for_a_branch_the_source_does_not_have(
        self, writer_call_sites: tuple[CallSite, ...]
    ) -> None:
        """A carve-out for a branch that was deleted excuses nothing and hides that."""
        stale = _deferrals_naming_a_branch_that_is_gone(
            writer_call_sites, THE_DEFERRED_BRANCHES
        )

        assert stale == set(), (
            "these deferrals name a branch that either no longer exists or now "
            f"takes a verdict: {sorted(stale)}"
        )

    def test_every_deferred_branch_hands_the_work_back_to_the_adopter(
        self, writer_call_sites: tuple[CallSite, ...]
    ) -> None:
        """A deferral that says nothing is a silent skip under a better name.

        Vacuous today, and deliberately kept: `THE_DEFERRED_BRANCHES` is empty
        since BDL-067 `.17`, so there is nothing to judge here until somebody
        declares a deferral again. `TestTheDeferralChecksStillBite` runs the same
        function over a synthetic declaration so that the check is known to work
        on the day it is next needed.
        """
        silent = _deferrals_that_tell_the_adopter_nothing(
            writer_call_sites, THE_DEFERRED_BRANCHES
        )

        assert silent == [], silent

    def test_no_branch_defers(
        self, writer_call_sites: tuple[CallSite, ...]
    ) -> None:
        """BDL-067 `.17`, part 2(a), stated as the fact it is.

        Every branch of `init` that writes a graph file takes a verdict, so the
        declaration above is empty because the source has nothing to declare —
        not because somebody deleted an entry. Both halves are asserted: a
        branch that stops taking its verdict fails the first, and an entry
        re-added without a branch to match fails the second.
        """
        assert [
            site.guard for site in writer_call_sites if not site.reaches_marker
        ] == []
        assert THE_DEFERRED_BRANCHES == ()


class TestTheDeferralChecksStillBite:
    """The two checks above, run over a declaration that is not empty.

    BDL-067 `.17`. `THE_DEFERRED_BRANCHES` is empty, so both cases in the class
    above assert over nothing. Deleting them would leave the next author to
    write the check again; keeping them silent would leave a carve-out unchecked
    on the day one is declared. So the checks are functions, and here they are
    given the two shapes they exist to reject — a deferral naming a branch that
    takes its verdict, and one whose branch tells the adopter nothing — plus the
    shape they must accept.

    The sites are the enumerator's own reading of the synthetic commands defined
    above, so what these cases judge is the same data the real ones judge.
    """

    #: A deferral for a branch that exists, takes no verdict, and says what to do.
    A_HONEST_DEFERRAL = DeferredBranch(
        guard=("rescan",),
        because="synthetic: the branch writes a file and hands the work back",
        tells_the_adopter="beadloom reindex",
    )

    def _sites(self, writing: frozenset[str]) -> tuple[CallSite, ...]:
        assert A_FOURTH_BRANCH_THAT_DEFERS_AND_SAYS_SO != A_COMMAND_LIKE_INIT, (
            "the anchor the mutation edits is gone, so these cases judge the "
            "unmutated command and the branch they name never existed"
        )
        return _call_sites_in(A_FOURTH_BRANCH_THAT_DEFERS_AND_SAYS_SO, writing)

    def test_a_deferral_matching_an_unjudged_branch_is_accepted(
        self, writing: frozenset[str]
    ) -> None:
        sites = self._sites(writing)

        assert _deferrals_naming_a_branch_that_is_gone(
            sites, (self.A_HONEST_DEFERRAL,)
        ) == set()

    def test_a_deferral_for_a_branch_that_takes_its_verdict_is_reported(
        self, writing: frozenset[str]
    ) -> None:
        """The stale carve-out: `non_interactive` is judged in every mutant."""
        sites = self._sites(writing)
        stale = DeferredBranch(
            guard=("non_interactive",), because="synthetic", tells_the_adopter="x"
        )

        assert _deferrals_naming_a_branch_that_is_gone(sites, (stale,)) == {
            ("non_interactive",)
        }

    def test_a_deferral_whose_branch_says_nothing_is_reported(
        self, writing: frozenset[str]
    ) -> None:
        """A silent skip under a better name is what the second check rejects."""
        sites = self._sites(writing)
        silent = DeferredBranch(
            guard=("rescan",),
            because="synthetic",
            tells_the_adopter="a sentence this branch does not contain",
        )

        assert _deferrals_that_tell_the_adopter_nothing(sites, (silent,)) != []

    def test_a_deferral_whose_branch_speaks_is_accepted(
        self, writing: frozenset[str]
    ) -> None:
        """Anti-vacuity: the check must not reject every deferral."""
        sites = self._sites(writing)

        assert _deferrals_that_tell_the_adopter_nothing(
            sites, (self.A_HONEST_DEFERRAL,)
        ) == []


class TestEveryBranchOfInitThatBootstrapsTakesAVerdict:
    """Read off `init`'s own source, so a branch added later is counted here."""

    def test_the_scan_finds_branches_to_judge(
        self, call_sites: tuple[CallSite, ...]
    ) -> None:
        """Anti-vacuity: an empty scan would pass every assertion below it."""
        assert call_sites, (
            f"no call reaching {THE_BOOTSTRAP} was found in `{THE_COMMAND}` — the "
            "enumeration below would assert nothing"
        )

    def test_no_branch_reaches_the_bootstrap_without_taking_a_verdict(
        self, call_sites: tuple[CallSite, ...]
    ) -> None:
        """The claim `.2` made about two branches, made about all of them.

        A fourth branch that writes a graph and returns without checking it
        against the rules it wrote fails here, whether or not anybody thought to
        add a case to `THE_BRANCHES`.
        """
        unguarded = [
            f"{site.callee} at line {site.lineno} under {site.guard or '<no flag>'}"
            for site in call_sites
            if not site.reaches_marker
        ]

        assert unguarded == [], (
            "a branch of `init` writes a bootstrap graph and never checks it "
            f"against the rules it wrote: {unguarded}"
        )


class TestTheParametrisedCasesCoverTheBranchesTheSourceHas:
    """The hand-maintained tuple, bound to the source it claims to enumerate.

    `THE_BRANCHES` drives every behavioural case in
    `tests/test_init_verdict_over_its_own_rules.py`. Nothing there fails when the
    tuple falls behind the command, because a case that is not written is a case
    that does not fail. These two assertions are what make it fail.
    """

    def test_every_branch_in_the_source_has_a_case(
        self, call_sites: tuple[CallSite, ...]
    ) -> None:
        declared = {branch.guard for branch in THE_BRANCHES}
        found = {site.guard for site in call_sites}

        assert found <= declared, (
            f"branches of `{THE_COMMAND}` with no case in THE_BRANCHES: "
            f"{sorted(found - declared)}"
        )

    def test_no_case_claims_a_branch_the_source_does_not_have(
        self, call_sites: tuple[CallSite, ...]
    ) -> None:
        """A case for a branch that was deleted tests nothing and says it does."""
        declared = {branch.guard for branch in THE_BRANCHES}
        found = {site.guard for site in call_sites}

        assert declared <= found, (
            f"THE_BRANCHES names branches `{THE_COMMAND}` does not have: "
            f"{sorted(declared - found)}"
        )
