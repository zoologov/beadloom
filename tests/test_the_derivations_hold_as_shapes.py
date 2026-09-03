"""The derivations hold as SHAPES, and an unresolved answer never reads as an empty one.

BDL-068 `.7`, and it is an audit rather than a quota. `.1` through `.6` each
measured their own premise and five of the six found it false or half-false, so
the first act here was a census of what is already pinned. Most of it is: `.2`
pins the effect-rule exclusion, `.3` pins the gap that exclusion exists for, `.5`
pins three attacks on the role population's shape rule, `.6` pins five on the
derivation-target shape and names the axis in three. None of that is repeated
here. What is here is what the census found MISSING, and every case ran red
before it ran green.

**Three findings, three classes.**

:class:`TestEveryDiskWriteVerbIsExercisedByACase` closes the gap `.1` measured
and `.3` handed over by name. Narrowing ``PUTS_BYTES_ON_DISK`` from
``{write_text, write_bytes, open}`` to ``{write_text}`` survived the whole suite,
and the measured reason is that on this tree the wide set names exactly one body
and it writes with ``write_text``: ``write_bytes`` and ``open`` are exercised by
nothing. Three synthetic bodies, one per verb, make each of them load-bearing.
Beside them is the shape that ACTUALLY holds and was nowhere stated — the commit
point puts its bytes down through ``fdopen``, ``write`` and ``replace``, which
the set spells none of — so widening the vocabulary is a failure that names the
re-measurement it owes rather than a silent re-answer of every ``impact`` target.

:class:`TestTheSameAnswerSaysUnresolvedAndEmptyInTwoDifferentWays` is the
direction of the unresolved report. `.2` pinned it on the ANSWER (``resolved`` is
not ``sites``); nothing pinned it on the two RENDERINGS, which is where a reader
meets it, and the one acceptance assertion that reached the human text could not
fail. A seedless target and a target nothing calls both carry an empty
population, in the same answer, and the two sections must not read alike.

:class:`TestTheLaunchIsFoundInEverySpellingOfIt` and
:class:`TestARoutingRowWhoseFlowCellIsUnreadableIsDroppedSilently` are the two
halves `.5` handed over: the launch form is attacked with four spellings and two
near-misses, and the routing table's own silent omission is recorded as a GAP.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

import beadloom
from beadloom.application.impact import ImpactAnswer, impact_of
from beadloom.application.impact.render import answer_to_dict, render_impact
from beadloom.application.source_derivation import (
    PUTS_BYTES_ON_DISK,
    SERIALISES_YAML,
    bodies_calling,
    functions_that_serialise_yaml_to_disk,
    functions_to_their_calls,
    sweep_modules,
)
from beadloom.application.work_item_routing import read_routing
from beadloom.infrastructure.atomic_io import write_yaml_atomic

#: The commit point every graph YAML routes through, read off the product's own
#: function object so a rename fails at import rather than at a string compare.
THE_COMMIT_POINT = write_yaml_atomic.__name__

#: How the commit point actually puts its bytes on disk, read off its own body.
#: MEASURED on this tree: its callees are Path, dump, fdopen, fileno, flush,
#: fsync, mkstemp, replace, str, suppress, unlink, write. These three are the
#: ones that do the writing, and `PUTS_BYTES_ON_DISK` spells none of them.
THE_VERBS_THE_COMMIT_POINT_WRITES_THROUGH = frozenset({"fdopen", "write", "replace"})

#: A body that serialises YAML and puts the bytes down itself, one spelling per
#: verb in `PUTS_BYTES_ON_DISK`. MEASURED at `803ef06`: over the real package the
#: wide set names ONE body and it writes with `write_text`, so `write_bytes` and
#: `open` are pinned by nothing until these exist.
_A_WRITER_SPELLED_EACH_WAY = {
    "write_text": (
        "import yaml\n"
        "from pathlib import Path\n\n\n"
        "def dump_it(path, payload):\n"
        "    Path(path).write_text(yaml.safe_dump(payload))\n"
    ),
    "write_bytes": (
        "import yaml\n"
        "from pathlib import Path\n\n\n"
        "def dump_it(path, payload):\n"
        "    Path(path).write_bytes(yaml.safe_dump(payload).encode())\n"
    ),
    "open": (
        "import yaml\n\n\n"
        "def dump_it(path, payload):\n"
        "    with open(path, 'w') as stream:\n"
        "        stream.write(yaml.safe_dump(payload))\n"
    ),
}

#: One half of the conjunction, so the shape is not satisfied by a body that only
#: writes. The other half — serialising without writing — is `write_yaml_atomic`
#: itself, which is why this shape walks past it.
_A_BODY_THAT_WRITES_AND_SERIALISES_NOTHING = (
    "from pathlib import Path\n\n\n"
    "def copy_it(source, target):\n"
    "    Path(target).write_text(Path(source).read_text())\n"
)

#: A target that reaches a sink, and a module that reaches nothing and is reached
#: by nothing. Both are needed in ONE answer for the rendering case: the seedless
#: module's co-writer axis is unresolved and its caller axis is resolved-and-empty.
_THE_SINK = (
    "import os\n"
    "import tempfile\n"
    "from pathlib import Path\n\n"
    "import yaml\n\n\n"
    "def commit_yaml(path, payload):\n"
    "    handle, temporary = tempfile.mkstemp()\n"
    '    with os.fdopen(handle, "w") as stream:\n'
    "        stream.write(yaml.safe_dump(payload))\n"
    "    Path(temporary).replace(path)\n"
)

_THE_MODULE_NOBODY_CALLS = "def note(what):\n    return what\n"

#: A `/task-init` whose routing table and explore step are both well formed, with
#: the launch spelling left open so each case supplies its own.
_A_TASK_INIT = """\
## Step 0.5 — Derive the axes

{launch}

## Step 1 — Decide the type

| Type | Flow | Docs created |
|---|---|---|
| epic | Full: PRD, RFC, CONTEXT, PLAN, ACTIVE | PRD, RFC, CONTEXT, PLAN, ACTIVE |
| bug | Simplified: BRIEF, ACTIVE | BRIEF, ACTIVE |
{extra_row}"""

#: Four ways one command can state the same launch. `.5` derived the step from
#: the launch rather than from its heading text precisely so a rename of the
#: heading cannot hide it; these are the spellings that must all still be found.
_FOUR_SPELLINGS_OF_THE_LAUNCH = {
    "an-agent-call": 'Agent(subagent_type="explore", run_in_background=True)',
    "a-bare-mention-in-prose": "launch the role (subagent_type: explore) before deciding",
    "an-assignment-in-single-quotes": "subagent_type = 'explore'",
    "a-colon-with-loose-spacing": "subagent_type :   explore",
}

#: Two near-misses, one per way of getting the role wrong. A longer name that
#: merely starts with the role's is the one a prefix match would accept.
_TWO_LAUNCHES_OF_SOMETHING_ELSE = {
    "a-longer-role-name": 'Agent(subagent_type="explorer")',
    "no-launch-at-all": "run the Explore role by hand before deciding",
}


def _a_package_holding(tmp_path: Path, **modules: str) -> Path:
    """A source tree under *tmp_path* holding one module per keyword."""
    package = tmp_path / "src" / "tree"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    for name, body in modules.items():
        (package / f"{name}.py").write_text(body, encoding="utf-8")
    return package


class TestEveryDiskWriteVerbIsExercisedByACase:
    """`PUTS_BYTES_ON_DISK` holds three verbs, and all three now decide something.

    The gap, in the words `.1` measured it in: narrowing the set to
    ``{write_text}`` survived the whole suite. The cause is in the corpus rather
    than in the shape — over the real package the set names ONE body, which
    writes with ``write_text``, so the other two verbs were carried by nothing.
    """

    @pytest.mark.parametrize("verb", sorted(_A_WRITER_SPELLED_EACH_WAY))
    def test_a_body_that_writes_with_this_verb_is_named(self, tmp_path: Path, verb: str) -> None:
        """One case per verb, so removing any one of the three goes red."""
        package = _a_package_holding(tmp_path, writer=_A_WRITER_SPELLED_EACH_WAY[verb])

        assert set(functions_that_serialise_yaml_to_disk(package)) == {"dump_it"}

    def test_a_body_that_writes_without_serialising_is_not_named(self, tmp_path: Path) -> None:
        """The conjunction, from the side the widening threatens.

        A shape stated over the write verbs alone would name most of a codebase,
        which is the second reason `.2` refused to seed on them: `open` reads as
        well as writes.
        """
        package = _a_package_holding(tmp_path, copier=_A_BODY_THAT_WRITES_AND_SERIALISES_NOTHING)

        assert functions_that_serialise_yaml_to_disk(package) == {}

    def test_the_commit_point_writes_through_verbs_the_shape_does_not_spell(
        self,
    ) -> None:
        """The shape that actually holds, so a widening is a failure and not a silence.

        `.3` recorded the CONSEQUENCE — 268 names reach a body in that set and the
        commit point is not one of them. This is the cause, stated positively: the
        commit point's own body names `fdopen`, `write` and `replace`, and the set
        spells `write_text`, `write_bytes` and `open`. Every `beadloom impact`
        answer depends on which vocabulary the seed rule is stated over, so a
        widening must arrive as a red test that names the re-measurement it owes.
        """
        package = Path(inspect.getfile(beadloom)).parent
        own_calls = functions_to_their_calls(package)[THE_COMMIT_POINT]

        assert own_calls >= THE_VERBS_THE_COMMIT_POINT_WRITES_THROUGH
        assert not (PUTS_BYTES_ON_DISK & THE_VERBS_THE_COMMIT_POINT_WRITES_THROUGH), (
            "the disk-write vocabulary now spells one of the verbs "
            f"{THE_COMMIT_POINT} commits through. That re-answers every `beadloom "
            "impact` target at once: re-run BDL-068 `.2`'s two acceptance targets "
            "at af26750d before accepting the new set, and delete the gap class in "
            "tests/test_the_seed_decides_what_impact_reports.py rather than "
            "repairing it."
        )

    def test_the_widened_vocabulary_does_name_the_commit_point(self) -> None:
        """The exclusion is a live choice: widened, the shape reaches the sink.

        Without this the previous case could pass over a set that names nothing at
        all, and an exclusion that excludes nothing is not a decision.
        """
        package = Path(inspect.getfile(beadloom)).parent
        sweep = sweep_modules(package)
        widened = PUTS_BYTES_ON_DISK | THE_VERBS_THE_COMMIT_POINT_WRITES_THROUGH

        named = {body.name for body in bodies_calling(sweep, widened, and_also=SERIALISES_YAML)}
        narrow = {
            body.name
            for body in bodies_calling(sweep, PUTS_BYTES_ON_DISK, and_also=SERIALISES_YAML)
        }

        assert THE_COMMIT_POINT in named
        assert THE_COMMIT_POINT not in narrow


class TestTheSameAnswerSaysUnresolvedAndEmptyInTwoDifferentWays:
    """A derivation that found nothing and one that could not look must not read alike.

    `.2` pinned this on the answer's fields. The two RENDERINGS are where a reader
    meets it, and nothing reached them: the only assertion over the human text was
    that the word "unresolved" appears in it, which every answer satisfies through
    the `## unresolved (N)` heading it always prints.

    One answer carries both populations, which is why this is a shape and not two
    fixtures: for a module that reaches no sink and that nothing calls, the
    co-writer axis is UNRESOLVED and the caller axis is RESOLVED AND EMPTY.
    """

    @pytest.fixture()
    def an_answer_holding_both_populations(self, tmp_path: Path) -> ImpactAnswer:
        _a_package_holding(tmp_path, sink=_THE_SINK, lonely=_THE_MODULE_NOBODY_CALLS)
        return impact_of("src/tree/lonely.py", project_root=tmp_path)

    def test_the_two_populations_are_equally_empty(
        self, an_answer_holding_both_populations: ImpactAnswer
    ) -> None:
        """Anti-vacuity: the emptiness is what the two have in common.

        If the caller axis found somebody, the case below would be distinguishing
        a full population from an empty one, which any rendering does.
        """
        answer = an_answer_holding_both_populations

        assert answer.co_writers.sites == ()
        assert answer.callers.sites == ()

    def test_the_text_reads_the_two_differently(
        self, an_answer_holding_both_populations: ImpactAnswer
    ) -> None:
        rendered = render_impact(an_answer_holding_both_populations)

        assert f"- unresolved: {an_answer_holding_both_populations.co_writers.reason}" in (
            rendered
        )
        assert "- none found." in rendered

    def test_a_seedless_target_states_the_absence_rather_than_printing_no_seeds(
        self, an_answer_holding_both_populations: ImpactAnswer
    ) -> None:
        """The seed section of a seedless answer is a sentence, not a blank."""
        rendered = render_impact(an_answer_holding_both_populations)

        assert "none. Every axis below the seed is unresolved, not empty." in rendered

    def test_the_json_keeps_them_apart_where_the_site_list_cannot(
        self, an_answer_holding_both_populations: ImpactAnswer
    ) -> None:
        """`sites` is `[]` on both sides, so `resolved` and `reason` carry the whole
        difference — a consumer reading only the list sees one fact where there are
        two."""
        payload = answer_to_dict(an_answer_holding_both_populations)

        assert payload["co_writers"]["sites"] == payload["callers"]["sites"] == []
        assert payload["co_writers"]["resolved"] is False
        assert payload["co_writers"]["reason"]
        assert payload["callers"]["resolved"] is True
        assert payload["callers"]["reason"] == ""

    def test_the_missing_seed_is_a_kind_in_the_rendered_population(
        self, an_answer_holding_both_populations: ImpactAnswer
    ) -> None:
        """The absence travels in the population, not only in the axis that lost it."""
        payload = answer_to_dict(an_answer_holding_both_populations)

        assert "no-seed" in {gap["kind"] for gap in payload["unresolved"]}


class TestTheLaunchIsFoundInEverySpellingOfIt:
    """The explore step is found by its LAUNCH, attacked with four spellings.

    `.5` chose the launch over the heading text because a heading can be renamed
    and a step that launches nothing does nothing. It shipped one spelling. These
    are the four a command could reasonably state, and the two that name something
    else — `explorer` is the one a prefix match would accept.
    """

    @pytest.mark.parametrize("spelling", sorted(_FOUR_SPELLINGS_OF_THE_LAUNCH))
    def test_the_step_is_found_however_the_launch_is_written(self, spelling: str) -> None:
        routing = read_routing(
            _A_TASK_INIT.format(launch=_FOUR_SPELLINGS_OF_THE_LAUNCH[spelling], extra_row="")
        )

        assert routing.explore_line == 1
        assert routing.explore_step == "Step 0.5 — Derive the axes"
        assert routing.notes == ()

    @pytest.mark.parametrize("spelling", sorted(_TWO_LAUNCHES_OF_SOMETHING_ELSE))
    def test_a_launch_of_another_role_is_not_the_step(self, spelling: str) -> None:
        routing = read_routing(
            _A_TASK_INIT.format(launch=_TWO_LAUNCHES_OF_SOMETHING_ELSE[spelling], extra_row="")
        )

        assert routing.explore_line is None
        assert routing.notes, "a command that launches nothing must say so"

    def test_the_step_is_not_found_by_the_heading_it_happens_to_sit_under(self) -> None:
        """The heading is reported, never matched — renaming it changes nothing."""
        renamed = _A_TASK_INIT.format(
            launch=_FOUR_SPELLINGS_OF_THE_LAUNCH["an-agent-call"], extra_row=""
        ).replace("Step 0.5 — Derive the axes", "Whatever this step is called now")

        routing = read_routing(renamed)

        assert routing.explore_line == 1
        assert routing.explore_step == "Whatever this step is called now"


class TestARoutingRowWhoseFlowCellIsUnreadableIsDroppedSilently:
    """A GAP this bead measured and did not repair, recorded so it is not re-found.

    The direction the bead's third clause states — a derivation that resolved
    everything and one that silently omitted what it could not parse must not read
    the same — holds in `impact` and does NOT hold here. `_routes_in` skips a row
    whose `Flow` cell spells neither `simplified` nor `full`, and `Routing.notes`,
    which exists for exactly this class of honesty, is left empty. The consequence
    reaches a check: the dropped type's document kinds are missing from
    `simplified_kinds`, so every work item of that type falls out of
    `check_work_item_types`' population and the report reads as a clean run over a
    smaller corpus.

    NOT repaired here, and the reason is a measurement rather than caution: the
    obvious repair — a note for every unreadable cell — fires on the table's own
    `|---|---|` alignment row, which `.5` already has a mutant for. Repairing it
    means re-measuring `.5`'s sixteen mutants, which is a dev bead's work.

    When this class goes red the gap has closed: DELETE it rather than repair it.
    """

    #: A type whose flow cell names a third route nobody derives.
    A_ROW_WHOSE_FLOW_CELL_NAMES_NEITHER = "| spike | Lightweight: NOTE | NOTE |\n"

    def test_the_row_is_dropped_from_the_routes(self) -> None:
        routing = read_routing(
            _A_TASK_INIT.format(
                launch=_FOUR_SPELLINGS_OF_THE_LAUNCH["an-agent-call"],
                extra_row=self.A_ROW_WHOSE_FLOW_CELL_NAMES_NEITHER,
            )
        )

        assert [route.type for route in routing.routes] == ["epic", "bug"]
        assert routing.flow_of("spike") is None

    def test_nothing_in_the_routing_says_a_row_was_dropped(self) -> None:
        """The gap itself. `notes` is the field that would say it, and it is empty."""
        routing = read_routing(
            _A_TASK_INIT.format(
                launch=_FOUR_SPELLINGS_OF_THE_LAUNCH["an-agent-call"],
                extra_row=self.A_ROW_WHOSE_FLOW_CELL_NAMES_NEITHER,
            )
        )

        assert routing.notes == (), (
            "the routing now reports the row it could not read — the gap this "
            "class records has closed, so delete the class rather than repair it"
        )

    def test_the_dropped_row_takes_its_document_kinds_with_it(self) -> None:
        """Why it matters: the kinds decide which work items are judged at all."""
        with_the_row = read_routing(
            _A_TASK_INIT.format(
                launch=_FOUR_SPELLINGS_OF_THE_LAUNCH["an-agent-call"],
                extra_row=self.A_ROW_WHOSE_FLOW_CELL_NAMES_NEITHER,
            )
        )
        readable = read_routing(
            _A_TASK_INIT.format(
                launch=_FOUR_SPELLINGS_OF_THE_LAUNCH["an-agent-call"],
                extra_row="| spike | Simplified: NOTE | NOTE |\n",
            )
        )

        assert "NOTE" not in with_the_row.simplified_kinds
        assert "NOTE" in readable.simplified_kinds
