"""Where S5's six instruments state one fact, they state it once — and it is still true.

BDL-068 S5 answered eight External ``bd`` findings by deriving this project's own call
sites and asserting what each assumes about the answer. Six beads did that in five waves
on a moving tree: ``beadloom-0mdo.39`` (the landing lock), ``.51`` (the derived
population), ``.52`` (an answer's population), ``.53`` (a bead's id and the cost of a
DAG), ``.54`` (the hook's staging and a decorated id) and ``beadloom-l2f2`` (the
post-merge hook's alias). Each bead's own suite covers its own instrument, red-first.
What no bead's suite could cover is the JOIN, and this file is only that.

**Every assertion here is a BOUNDARY GUARD written after the behaviour**, per the house
standard the dev beads of this slice declared. One was red on the tree when written and
says so in its own docstring; every other one was verified red by a one-sided edit to a
pair that agrees today, which is the only thing a seam test can be worth. Two of them
build an isolated ``bd init`` rig and take about fifteen seconds between them, which is
the price of re-taking a measurement instead of quoting it.

**Every bd measurement below was re-taken against bd 1.0.4 (``ce242a879``)** in isolated
``bd init`` rigs, streams separated, every exit code read from ``$?`` without a pipe. The
slice's distinctive fact is that its premises kept falling — six were re-measured, three
were false and withdrawn, one was falsely withdrawn and restored — so an assertion that
repeats a log entry's wording rather than a measurement is the exact failure this file
exists to catch.

The five joins, with the question each answers.

* **Is the measurement still true of the bd on PATH, or only of a string?**
  :data:`~beadloom.services.bd_seam.assumptions.BD_MEASURED_VERSION` is compared against
  the installed ``bd`` by ``tests/test_bd_call_sites.py``, and that is a comparison of
  NAMES. Nothing compared the table's content — the flags it calls securing, the flag it
  relies on being absent, the two caps it quotes — against the tool. A bd that renamed
  ``--all`` would leave every ``secured`` verdict in place and the instruction it ships
  wrong.
* **Does one rig measurement have one number?** ``.51`` measured the ``bd ready`` cap on
  a rig of 135 and ``.52`` re-measured it on a rig of 120. Thirteen statements of it in
  this tree say 120, including the shared role fragment five composed roles carry to an
  adopter, and one says 135 — the sentence ``beadloom bd-calls`` prints at every
  unsecured site.
* **Can the population lose a call site?** ``.53``'s first draft put its argv behind a
  helper and its own creation site left the report entirely — not unsecured, ABSENT. It
  guarded that with a test naming ONE call site, which is the hand-written list this
  slice's own bead description forbids. The derived form is below.
* **Is anything downstream reading an unmeasured subcommand as a clean one?** ``bd
  swarm`` and ``bd gate`` are the two commands ``/coordinator`` orchestrates every wave
  with and the two ``.51`` deliberately did not guess at.
* **Does an assumption with no site enforce anything?** ``.53`` shipped ``echoed-titles``
  with zero sites, declared as reddening the day one appears. Both halves of that claim
  are measured here, and one of them is qualified.
"""

from __future__ import annotations

import ast
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from beadloom.services.bd_seam import population as bd_population
from beadloom.services.bd_seam.answers import COVERAGE_UNCHECKED, coverage_of
from beadloom.services.bd_seam.assumptions import (
    ASSUMPTION_ALLOCATED_ID,
    ASSUMPTION_ECHOED_TITLES,
    ASSUMPTION_INTENDED_ID,
    ASSUMPTION_UNMEASURED_SUBCOMMAND,
    ASSUMPTIONS,
    BD_MEASURED_VERSION,
    VERDICT_SECURED,
    VERDICT_UNMEASURED,
    VERDICT_UNSECURED,
    call_sites,
    population_flags,
)
from beadloom.services.bd_seam.invocations import (
    CHANNEL_PYTHON,
    SEAM_FUNCTION,
    python_invocations,
    text_invocations,
)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _bd_help(*words: str) -> str:
    """``bd <words> --help`` as text, or an empty string when bd is not installed.

    Read from both streams deliberately: bd 1.0.4 prints help on stdout for a valid
    subcommand and on stderr beside an error, and this reader wants the flag list either
    way. Nothing here reads an exit code, so the merge cannot destroy one.
    """
    binary = shutil.which("bd")
    if binary is None:  # pragma: no cover - exercised only on a machine without bd
        return ""
    done = subprocess.run(  # noqa: S603
        [binary, *words, "--help"],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    return done.stdout + done.stderr


def _installed_bd_version() -> str | None:
    """The version of the ``bd`` on PATH, or ``None`` when there is none."""
    binary = shutil.which("bd")
    if binary is None:  # pragma: no cover - exercised only on a machine without bd
        return None
    done = subprocess.run(  # noqa: S603
        [binary, "version"], capture_output=True, text=True, check=False, timeout=30
    )
    found = re.search(r"(\d+\.\d+\.\d+)", done.stdout + done.stderr)
    return found.group(1) if found else None


def _requires_the_measured_bd() -> None:
    """Skip when the installed bd is not the one the table was measured against.

    A guard against re-measuring is NOT the point: ``test_the_recorded_release_is_the_one
    _installed`` already fails loudly on a different release, and that failure is what
    tells a reader the table needs re-measuring. These tests would then be asserting a
    table nobody has re-taken, so they step aside and let the one loud failure speak.
    """
    installed = _installed_bd_version()
    if installed is None:
        pytest.skip("no `bd` on PATH in this room")
    if installed != BD_MEASURED_VERSION:
        pytest.skip(
            f"the table was measured on bd {BD_MEASURED_VERSION} and bd {installed} is "
            "installed; test_the_recorded_release_is_the_one_installed is the failure "
            "that reports it"
        )


def _instructing_texts() -> tuple[tuple[str, str], ...]:
    """Every artifact the derived population reads, as ``(label, text)``.

    Taken from the population's own collectors rather than from a list of paths, so an
    artifact added to the flow is swept here by being added there.
    """
    return (
        *bd_population.flow_artifacts(_PROJECT_ROOT),
        *bd_population.shipped_templates(),
        *bd_population.package_python(),
    )


# --------------------------------------------------------------------------
# JOIN 1 — the measurement, checked against the tool rather than against a version string.
# --------------------------------------------------------------------------


def test_every_flag_the_table_calls_securing_exists_on_the_bd_installed() -> None:
    """A ``secured`` verdict is a claim that a flag bd HAS makes the assumption true.

    The verdict vocabulary rests entirely on this: ``bd list --all`` is ``secured``
    because ``--all`` lifts both default filters, and an artifact instructing that form
    is judged clean. If a later bd renames or drops one of those flags, every verdict
    stays ``secured``, every shipped instruction keeps naming a flag that no longer
    exists, and the only thing that reddens is a version string. Derived from the rule
    table, so a rule added later is covered without editing this test.

    Re-measured on bd 1.0.4: ``--all``, ``-s``/``--status`` and ``-n``/``--limit`` on
    ``bd list``; ``-n``/``--limit`` on ``bd ready``; ``--graph`` and the global ``--json``
    on ``bd create``; ``--file`` on ``bd dep add``; ``-i`` on ``bd import``.
    """
    # Arrange
    _requires_the_measured_bd()
    from beadloom.services.bd_seam.assumptions import _MEASURED

    claimed = {
        subcommand: sorted(
            {flag for rule in rules for flag in (*rule.securing_flags, *rule.applies_when)}
        )
        for subcommand, rules in _MEASURED.items()
    }
    claimed = {sub: flags for sub, flags in claimed.items() if flags}
    assert claimed, "the rule table names no securing flag at all"

    # Act
    missing = [
        f"bd {subcommand} has no {flag}"
        for subcommand, flags in claimed.items()
        for flag in flags
        if flag not in _bd_help(*subcommand.split())
    ]

    # Assert
    assert missing == [], (
        "a rule secures a call site on a flag the installed bd does not have, so the "
        "remedy this project instructs would fail: " + "; ".join(missing)
    )


def test_the_absence_the_intended_id_rule_rests_on_is_still_an_absence() -> None:
    """``intended-id`` is ``unsecured`` and not ``holds`` because no flag can settle it.

    The whole verdict turns on ``bd dep add`` having no ``--expect-title``: with one, the
    rule would gain a securing flag and every wiring site this project instructs would be
    judged against it instead of against the artifact naming ``bd dep tree``. An absence
    is a measurement and needs re-checking exactly as a presence does — measured on bd
    1.0.4, where the flag is rejected with ``unknown flag: --expect-title`` at exit 1.
    """
    # Arrange
    _requires_the_measured_bd()

    # Act
    help_text = _bd_help("dep", "add")

    # Assert
    assert "--expect-title" not in help_text, (
        "`bd dep add` now has --expect-title, so `intended-id` can be settled at the "
        "line and its rule must gain the flag rather than keep pointing at `dep tree`"
    )


@pytest.mark.parametrize(
    ("subcommand", "cap"),
    [("list", 50), ("ready", 100)],
)
def test_the_cap_each_rule_quotes_is_the_default_bd_declares(subcommand: str, cap: int) -> None:
    """The two truncation numbers this flow repeats are bd's own documented defaults.

    ``untruncated-population`` exists because both answers are narrower than the question
    and announce it on stderr only. The numbers reached this tree through a rig, and a
    rig is a measurement somebody took once — bd states both in its own ``--help``, so
    the claim can be re-checked without one. Re-measured in a 120-bead rig on bd 1.0.4:
    ``bd ready`` returned 100 rows and printed ``Showing 100 of 120 ready issues.`` on
    stderr, ``bd list`` returned 50 with its own notice on stderr, and both answers were
    complete under ``--limit 0``.
    """
    # Arrange
    _requires_the_measured_bd()

    # Act
    limit_line = [
        line for line in _bd_help(subcommand).splitlines() if "--limit" in line and "int" in line
    ]

    # Assert
    assert limit_line, f"bd {subcommand} no longer documents a --limit at all"
    assert f"default {cap}" in limit_line[0] or f"(default {cap})" in limit_line[0], (
        f"the table says `bd {subcommand}` caps at {cap} and bd now documents "
        f"{limit_line[0].strip()!r}"
    )


def test_every_subcommand_the_table_judges_is_one_the_installed_bd_still_has() -> None:
    """A rule keyed on a subcommand bd dropped would judge a population of zero forever.

    This is the same class as an assumption with no site, one level up: the table would
    keep its entry, ``bd-calls`` would keep printing a vocabulary that names it, and the
    verdict would be about a command nobody can run. Derived from the table's own keys.
    """
    # Arrange
    _requires_the_measured_bd()
    from beadloom.services.bd_seam.assumptions import _MEASURED

    # Act
    unknown = [
        subcommand
        for subcommand in _MEASURED
        if "unknown command" in _bd_help(*subcommand.split()).lower()
    ]

    # Assert
    assert unknown == [], f"the table judges subcommands bd no longer has: {unknown}"


def test_both_answers_this_flow_relies_on_are_still_narrower_than_the_question(
    tmp_path: Path,
) -> None:
    """BDL-UX #187 and the ``bd ready`` cap, re-taken rather than quoted.

    These two are the slice's central surviving premises and the reason fifteen shipped
    instructions changed: ``bd list`` omits every closed bead and says so on NEITHER
    stream, and both answers cap silently on stdout. Everything downstream rests on it —
    ``complete-population``, ``untruncated-population``, ``coverage_of``'s notice grammar
    and the ``_tracker`` fragment five composed roles carry. All of it was measured once,
    by hand, in a rig nobody kept, and quoted from there onwards. This test keeps the rig.

    Re-measured on bd 1.0.4 (``ce242a879``) in an isolated 120-bead rig, ready read
    before five beads were closed and the list read after,
    streams separated: ``bd list --limit 0`` returned 115 rows with both streams silent
    about the 5 it dropped, ``--all --limit 0`` returned 120, the default returned 50
    with its notice on stderr, and ``bd ready`` returned 100 of 120 with ``Showing 100 of
    120 ready issues.`` on stderr and nothing on stdout.
    """
    # Arrange
    _requires_the_measured_bd()
    binary = shutil.which("bd")
    assert binary is not None

    def run(*words: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(  # noqa: S603
            [binary, *words], cwd=tmp_path, capture_output=True, text=True, check=False, timeout=60
        )

    def rows(*words: str) -> tuple[int, str]:
        done = run(*words)
        assert done.returncode == 0, done.stderr
        answer = json.loads(done.stdout)
        return len(answer if isinstance(answer, list) else answer["issues"]), done.stderr

    assert run("init", "--prefix", "cap").returncode == 0
    plan = tmp_path / "plan.json"
    plan.write_text(
        json.dumps(
            {
                "nodes": [
                    {"key": f"n{i:03d}", "title": f"node {i}", "type": "task", "priority": 2}
                    for i in range(120)
                ],
                "edges": [],
            }
        ),
        encoding="utf-8",
    )
    created = run("create", "--graph", str(plan), "--json")
    assert created.returncode == 0, created.stderr
    ids = list(json.loads(created.stdout)["ids"].values())
    assert len(ids) == 120

    # Act
    ready_default, ready_stderr = rows("ready", "--json")
    ready_all, _ = rows("ready", "--json", "--limit", "0")
    capped, capped_stderr = rows("list", "--json")
    for bead in ids[:5]:
        assert run("close", bead).returncode == 0
    open_only, open_stderr = rows("list", "--json", "--limit", "0")
    everything, _ = rows("list", "--all", "--json", "--limit", "0")

    # Assert
    assert (open_only, everything) == (115, 120), (
        "`bd list` no longer omits closed beads by default, so `complete-population` "
        "guards nothing and every instruction naming `--all` explains a filter that is gone"
    )
    assert open_stderr.strip() == "", (
        "`bd list` now announces its status filter, so the sentence saying it is silent "
        "on both streams is stale in five shipped role files"
    )
    assert capped == 50, "`bd list` no longer caps at 50, so the number the table quotes is wrong"
    assert "50" in capped_stderr, "the cap notice left stderr, where every consumer reads it"
    assert (ready_default, ready_all) == (100, 120), (
        "`bd ready` no longer caps at 100, so the assumption this flow relies on most "
        "has changed and `--limit 0` may no longer be the remedy"
    )
    assert "100 of 120" in ready_stderr, (
        "the notice this project quotes verbatim in thirteen places is no longer what bd "
        f"prints: {ready_stderr.strip()!r}"
    )


def test_the_landing_locks_two_flags_are_flags_the_installed_bd_has() -> None:
    """The lock's judgement is a second table, and it was outside the check above.

    ``exclusive-hold`` is not judged from ``_MEASURED``: the merge-slot forms are read in
    ``application/waves/landing.py`` so the tree holds one judgement of the primitive.
    That is the right structure and it puts two more flag claims outside the rule table's
    reach. ``--holder`` is what makes a hold name a bead and a release owner-checked, and
    ``--wait`` is the flag every defective call form of ours used; a bd that dropped
    either would leave eighteen instructions naming it and every verdict ``secured``.
    """
    # Arrange
    _requires_the_measured_bd()
    from beadloom.application.waves.landing import (
        HOLDER_FLAG,
        LOCK_COMMAND,
        WAIT_FLAG,
    )

    command = LOCK_COMMAND.split()[1:]

    # Act
    acquire = _bd_help(*command, "acquire")
    release = _bd_help(*command, "release")

    # Assert
    assert HOLDER_FLAG in acquire, f"`bd merge-slot acquire` no longer takes {HOLDER_FLAG}"
    assert WAIT_FLAG in acquire, f"`bd merge-slot acquire` no longer takes {WAIT_FLAG}"
    assert HOLDER_FLAG in release, (
        f"`bd merge-slot release` no longer takes {HOLDER_FLAG}, which is the only "
        "release form bd verifies and the one this flow instructs"
    )


def test_the_slot_still_grants_what_the_shipped_instruction_says_it_grants(
    tmp_path: Path,
) -> None:
    """Four claims carried to every adopter, re-taken against the tool rather than quoted.

    ``beadloom-0mdo.39`` measured these in an isolated rig, wrote them into
    ``templates/roles/core/_landing.md.txt``, and the composer now carries them into five
    role files an adopter is handed. Nothing re-took them: BDL-UX #194 and #237 both
    declared this primitive broken on a reading of printed output, and the correction
    that followed is prose in a shipped template with no measurement behind it in the
    suite. Slow by construction — one ``bd init`` and one slot, about four seconds — and
    that is the price of the instruction being checked rather than asserted.

    Re-measured on bd 1.0.4 (``ce242a879``), every exit code read from the return code of
    a captured subprocess and never through a pipe:

    * ``acquire --holder beadA`` on a free slot exits 0;
    * ``acquire --holder beadB`` on a held slot exits 1 — the exclusion the flow relies on;
    * ``acquire --holder beadB --wait`` returns in 354 ms at exit 1 and prints ``added to
      waiters queue (position 1)``, so it queues rather than blocks;
    * ``release --holder beadB`` against beadA's hold exits 1 with ``slot held by beadA,
      not beadB``, and a bare ``release`` exits 0 and frees it.
    """
    # Arrange
    _requires_the_measured_bd()
    binary = shutil.which("bd")
    assert binary is not None

    def run(*words: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(  # noqa: S603
            [binary, *words],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )

    assert run("init", "--prefix", "lck").returncode == 0
    assert run("merge-slot", "create").returncode == 0

    # Act
    first = run("merge-slot", "acquire", "--holder", "beadA")
    second = run("merge-slot", "acquire", "--holder", "beadB")
    waiting = run("merge-slot", "acquire", "--holder", "beadB", "--wait")
    wrong_holder = run("merge-slot", "release", "--holder", "beadB")
    anonymous = run("merge-slot", "release")

    # Assert
    assert first.returncode == 0, "the slot no longer grants a hold to the form we instruct"
    assert second.returncode != 0, (
        "a second acquire succeeded on a held slot, so the primitive this flow relies on "
        "for landing order no longer excludes anyone"
    )
    assert waiting.returncode != 0, "`--wait` now grants the slot rather than queueing"
    assert "wait" not in waiting.stdout.lower() or "queue" in waiting.stdout.lower(), (
        "`--wait` returned without saying it only queued, so the instruction telling "
        "agents to write their own bounded loop may no longer be the right one"
    )
    assert wrong_holder.returncode != 0, (
        "`release --holder <not-the-holder>` succeeded, so the one release form bd "
        "verifies stopped verifying"
    )
    assert anonymous.returncode == 0, (
        "a bare `release` no longer frees whoever holds the slot, so the defect the "
        "shipped instruction warns about may be fixed upstream and the warning stale"
    )


# --------------------------------------------------------------------------
# JOIN 2 — one rig measurement, stated once.
# --------------------------------------------------------------------------


def test_the_ready_cap_measurement_is_stated_with_one_rig_size_across_the_tree() -> None:
    """Two beads measured one cap on two rigs and the tree kept both numbers.

    RED WHEN WRITTEN. ``beadloom-0mdo.51`` measured ``bd ready`` returning 100 of 135;
    ``beadloom-0mdo.52`` re-measured it as 100 of 120 on a rig built with ``bd create
    --graph`` and updated the module docstring, ``answers.py``, the shared ``_tracker``
    role fragment, five composed role files, five vendored template snapshots and two
    tests. The one statement it did not own kept 135: the ``untruncated-population``
    detail, which is the sentence ``beadloom bd-calls`` prints at every unsecured ``bd
    ready`` site. An agent reading its role core is told one number and the report it is
    pointed at prints another, about one measurement.

    Re-measured for this test on bd 1.0.4 in an isolated 120-bead rig: 100 rows returned,
    ``Showing 100 of 120 ready issues.`` on stderr, stdout silent about it, and 120 rows
    under ``--limit 0``. The rig size is a property of the rig, so neither number is
    false — what cannot be true is both, in one tree, about one sentence.
    """
    # Arrange
    cap_sentence = re.compile(r"100 of (\d+)")

    # Act
    stated: dict[str, set[str]] = {}
    for label, text in _instructing_texts():
        for size in cap_sentence.findall(text):
            stated.setdefault(size, set()).add(label)

    # Assert
    assert stated, "no artifact states the `bd ready` cap measurement at all"
    assert len(stated) == 1, "one measurement is stated with more than one rig size: " + "; ".join(
        f"100 of {size} in {sorted(labels)[0]}"
        + (f" and {len(labels) - 1} more" if len(labels) > 1 else "")
        for size, labels in sorted(stated.items())
    )


def test_every_sentence_pinning_a_measurement_to_a_bd_release_names_the_measured_one() -> None:
    """The release is pinned in one constant and RESTATED in prose the constant cannot reach.

    ``BD_MEASURED_VERSION`` is compared against the installed bd, so a bd upgrade reddens
    one test. It cannot see the sentences that say "measured on bd 1.0.4" in the seam's
    module docstrings, in the wave plan's landing module and in the shared role fragments
    five composed roles carry to an adopter. Bumping the constant without moving those
    turns thirty measured statements into claims about a release nobody took them on.

    Limited by construction to the ``bd <version>`` shape, which is how every one of them
    is written today; a sentence pinning a release some other way is outside this guard
    and is named here rather than implied.
    """
    # Arrange
    pinned = re.compile(r"\bbd (\d+\.\d+\.\d+)")

    # Act
    stated: dict[str, list[str]] = {}
    for label, text in _instructing_texts():
        for version in pinned.findall(text):
            stated.setdefault(version, []).append(label)

    # Assert
    assert stated, "no artifact pins a measurement to a bd release at all"
    assert set(stated) == {BD_MEASURED_VERSION}, (
        f"the table is measured on bd {BD_MEASURED_VERSION} and prose in this tree "
        f"pins a measurement to another release: "
        + "; ".join(
            f"bd {version} in {sorted(set(labels))[0]}"
            for version, labels in sorted(stated.items())
            if version != BD_MEASURED_VERSION
        )
    )


# --------------------------------------------------------------------------
# JOIN 3 — the population cannot quietly lose a call site.
# --------------------------------------------------------------------------


def _seam_calls_in_the_package() -> list[tuple[str, int]]:
    """Every ``run_bd(...)`` call in the installed package, as ``(label, line)``.

    Read from the package root the population itself resolves, and by the same AST the
    reader uses, so this counts CALLS where the reader counts calls-it-could-read. The
    difference between the two is the whole subject of the test below.
    """
    found: list[tuple[str, int]] = []
    for label, text in bd_population.package_python():
        for node in ast.walk(ast.parse(text)):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
            if name == SEAM_FUNCTION:
                found.append((label, node.lineno))
    return found


def test_every_call_to_the_seam_in_this_package_is_visible_to_the_derivation() -> None:
    """A call site the reader cannot follow leaves NO trace, which reads as clean.

    ``beadloom-0mdo.53`` built this exact defect by tidying: its first version put the
    scaffold's argv behind a ``graph_argv()`` helper, and because the reader resolves a
    list literal handed to ``run_bd`` and cannot follow a function call, the creation
    site vanished from the report rather than appearing in it unsecured. The guard that
    bead left behind names ONE call site by module, function and test, which is the
    hand-written list this slice's own description forbids and which covers nothing about
    the twelve other call sites or the thirteenth somebody adds.

    This is the derived form: the calls this package makes, counted against the calls the
    population reports. It is one-sided on purpose — a site the reader DID read but the
    population dropped for another reason would show here too, and that is also a defect.
    """
    # Arrange
    calls = _seam_calls_in_the_package()
    assert calls, "no `run_bd` call was found at all, so this test proves nothing"

    # Act
    seen = {
        (site.source, site.line)
        for site in bd_population.project_report(_PROJECT_ROOT).sites
        if site.channel == CHANNEL_PYTHON
    }

    # Assert
    invisible = [f"{label}:{line}" for label, line in calls if (label, line) not in seen]
    assert invisible == [], (
        "a `run_bd` call is absent from the derived population rather than unsecured in "
        "it, so the report reads clean about a site nothing judged. Spell the argv as a "
        "list literal at the call: " + "; ".join(invisible)
    )


@pytest.mark.parametrize(
    ("argv_expression", "why"),
    [
        ("graph_argv()", "a helper returning the argv — `beadloom-0mdo.53`'s own draft"),
        ('["list"] + extra', "a list built by concatenation"),
        ("*argv", "an unpacked sequence"),
        ("argv_from_config", "a name bound to something the module reader cannot resolve"),
    ],
)
def test_an_argv_the_reader_cannot_follow_leaves_no_trace_in_the_population(
    argv_expression: str, why: str
) -> None:
    """The reader drops the CALL silently, where it counts an unresolved ARGUMENT.

    This is the honest statement of a gap rather than a complaint about one. The module
    says "what it cannot resolve, it says", and that holds at two of three levels: an
    argument decided at runtime is counted in ``unresolved_arguments`` and its subcommand
    still reported, and a module that will not parse is skipped where the caller can see
    the gap between paths handed over and labels returned. A ``run_bd`` call whose argv
    is not a list literal is at neither level: it is dropped with no counter, inside a
    module that parsed.

    The day this test reddens is the day that gap was closed, and closing it is the
    remedy — the assertion is on the behaviour as measured, not on the behaviour wanted.
    """
    # Arrange
    source = f"from x import run_bd\nrun_bd({argv_expression})\n"
    control = python_invocations([("m.py", 'from x import run_bd\nrun_bd(["ready"])\n')])
    assert len(control) == 1, "the reader found nothing at all, so an empty answer says nothing"

    # Act
    invocations = python_invocations([("m.py", source)])

    # Assert
    assert invocations == (), (
        f"{why} is now readable, so the population no longer loses it and "
        "test_every_call_to_the_seam_in_this_package_is_visible_to_the_derivation "
        "gained a level it can see"
    )


# --------------------------------------------------------------------------
# JOIN 4 — an unmeasured subcommand, all the way down.
# --------------------------------------------------------------------------


def test_the_two_command_families_the_coordinator_runs_are_still_unjudged() -> None:
    """``bd swarm`` and ``bd gate`` are unmeasured, and nothing has quietly claimed them.

    They are the two commands ``/coordinator`` orchestrates every wave with and the two
    ``beadloom-0mdo.51`` deliberately did not guess at, because measuring two command
    families properly is its own bead and guessing is the false confidence this epic
    removes. Three beads landed on the table afterwards and each could have converted one
    into a claim by adding a key with an empty tuple — which is how the table records "a
    subcommand measured to carry no assumption", one keystroke from "a subcommand nobody
    looked at".

    Measured today: 26 ``swarm`` sites and 22 ``gate`` sites, every one in the
    instruction channel, every one carrying ``unmeasured-subcommand`` and nothing else.
    """
    # Arrange
    report = bd_population.project_report(_PROJECT_ROOT)

    # Act
    orchestration = [site for site in report.sites if site.subcommand in ("swarm", "gate")]

    # Assert
    assert {site.subcommand for site in orchestration} == {"swarm", "gate"}, (
        "this project no longer instructs both command families, so the gap this test "
        "keeps open may have been closed by deletion rather than by measurement"
    )
    claimed = [
        f"{site.source}:{site.line} `{site.text}` -> "
        + ",".join(f"{a.name}={a.verdict}" for a in site.assumptions)
        for site in orchestration
        if [a.name for a in site.assumptions] != [ASSUMPTION_UNMEASURED_SUBCOMMAND]
        or [a.verdict for a in site.assumptions] != [VERDICT_UNMEASURED]
    ]
    assert claimed == [], (
        "an unmeasured subcommand now carries a verdict, so a site nobody measured reads "
        "as judged: " + "; ".join(claimed)
    )


def test_a_subcommand_with_no_population_question_is_not_the_same_as_one_nobody_measured() -> None:
    """The one place the two facts could be conflated, asserted in both layers.

    ``population_flags`` answers ``None`` for BOTH — for ``show``, which is in the table
    and carries no population question, and for ``swarm``, which is outside it. At run
    time ``coverage_of`` turns both into ``unchecked``, and that conflation is stated in
    the module's own docstring. What must NOT collapse is the derivation-time
    distinction, which is the only place a reader can tell an unjudged site from a clean
    one: a ``show`` site reports no assumption and a ``swarm`` site reports
    ``unmeasured-subcommand``.
    """
    # Arrange / Act
    measured_without_a_question = call_sites(text_invocations([("a.md", "`bd show proj-1`")]))
    never_measured = call_sites(text_invocations([("a.md", "`bd swarm status`")]))

    # Assert
    assert population_flags("show") is None
    assert population_flags("swarm") is None
    assert coverage_of(("show", "proj-1", "--json"), "").coverage == COVERAGE_UNCHECKED
    assert coverage_of(("swarm", "status"), "").coverage == COVERAGE_UNCHECKED
    assert measured_without_a_question[0].assumptions == ()
    assert [a.name for a in never_measured[0].assumptions] == [ASSUMPTION_UNMEASURED_SUBCOMMAND]
    assert never_measured[0].unsettled, "an unjudged site must never read as a settled one"


# --------------------------------------------------------------------------
# JOIN 5 — an assumption with no site, and what it actually enforces.
# --------------------------------------------------------------------------


def test_no_instruction_of_ours_leaves_a_creation_or_wiring_assumption_unsettled() -> None:
    """The zero ``beadloom-0mdo.53`` asserted covers the channel that cannot hold a site.

    ``.53`` removed both of this project's Python ``create``/``dep add`` call sites — the
    scaffold makes ONE ``bd create --graph`` call now — and then asserted zero unsettled
    sites over the PYTHON channel. Every remaining place this project can get bead
    creation or wiring wrong is therefore an INSTRUCTION site, and no test covered them:
    measured by injecting ``bd create --parent proj-1 "some child"`` into
    ``.claude/commands/task-init.md``, where ``beadloom bd-calls`` judged it
    ``allocated-id=unsecured`` and the 132 tests of the four S5 suites passed.

    This is that gate. It reddens on an artifact of ours telling an agent to create a
    bead without asking bd for the id it allocated, or to wire an edge nothing verifies.
    """
    # Arrange
    report = bd_population.project_report(_PROJECT_ROOT)
    owned = {ASSUMPTION_ALLOCATED_ID, ASSUMPTION_INTENDED_ID, ASSUMPTION_ECHOED_TITLES}

    # Act
    unsettled = [
        f"{site.source}:{site.line} `{site.text}` -> "
        + ",".join(f"{a.name}={a.verdict}" for a in site.unsettled if a.name in owned)
        for site in report.sites
        if any(a.name in owned for a in site.unsettled)
    ]

    # Assert
    assert unsettled == [], (
        "an artifact of ours instructs a bead creation or a wiring whose assumption "
        "nothing settles: " + "; ".join(unsettled)
    )
    judged = [site for site in report.sites if any(a.name in owned for a in site.assumptions)]
    assert judged, "no create or dep-add site was judged at all, so the zero above is vacuous"


def test_the_bulk_wiring_form_is_reported_and_the_verification_is_what_settles_it() -> None:
    """``echoed-titles`` has zero sites, can fail, and cannot fail where it matters most.

    ``.53`` shipped it as "zero sites today, reddening the day an artifact of ours
    instructs the bulk form". Both halves measured here, because the first is true and
    the second is qualified. It DOES fire: an artifact instructing ``bd dep add --file``
    and nothing else is ``unsecured``, so this is the honest form of an empty rule and
    not a check that cannot fail. And it is SECURED by the artifact naming ``bd dep
    tree`` anywhere in it, which is a defensible design — bulk-wire fast, then verify
    from the tracker — with one consequence nobody wrote down: ``task-init.md`` is the
    only artifact of ours that would ever bulk-wire, and it already names ``bd dep tree``
    at line 151. Injecting the bulk form there produced ``echoed-titles=secured``.

    Re-measured on bd 1.0.4: ``bd dep add A B`` prints ``✓ Added dependency: rigq-6h6
    (alpha the first) depends on rigq-kxv (beta the second) (blocks)`` and ``bd dep add
    --file`` prints ``✓ Added 2 dependencies`` with no title at all, both at exit 0.
    """
    # Arrange
    bulk = "`bd dep add --file edges.ndjson`"
    verified = f"{bulk}\n\nThen confirm the edges with `bd dep tree proj-1`.\n"

    # Act
    alone = call_sites(text_invocations([("a.md", bulk)]))[0]
    beside_its_check = call_sites(text_invocations([("b.md", verified)]))[0]

    # Assert
    assert ASSUMPTION_ECHOED_TITLES in ASSUMPTIONS, "the vocabulary lost the rule entirely"
    assert (ASSUMPTION_ECHOED_TITLES, VERDICT_UNSECURED) in {
        (a.name, a.verdict) for a in alone.assumptions
    }, "the bulk form on its own no longer reddens, so the rule guards nothing"
    assert (ASSUMPTION_ECHOED_TITLES, VERDICT_SECURED) in {
        (a.name, a.verdict) for a in beside_its_check.assumptions
    }, "naming `bd dep tree` no longer settles the bulk form"


def test_an_assumption_with_no_site_is_selectable_and_an_invented_one_is_refused() -> None:
    """An empty population and a name the report does not judge must not read alike.

    ``beadloom bd-calls --assumption echoed-titles`` selects nothing today. A reader has
    to be able to tell that from a typo, or the way to make any finding disappear is to
    misspell it. Measured with the streams separated and the exit code read from ``$?``:
    the empty selection is rc 0 with ``0 site(s) selected`` on stdout, and an invented
    name is rc 2 with a message on stderr that lists every assumption the derivation
    judges.
    """
    # Arrange
    from click.testing import CliRunner

    from beadloom.services.cli import main

    runner = CliRunner()

    # Act
    empty = runner.invoke(main, ["bd-calls", "--assumption", ASSUMPTION_ECHOED_TITLES])
    invented = runner.invoke(main, ["bd-calls", "--assumption", "no-such-assumption"])

    # Assert
    assert empty.exit_code == 0
    assert "0 site(s) selected" in empty.output
    assert invented.exit_code == 2
    assert ASSUMPTION_ECHOED_TITLES in invented.output, (
        "the refusal must name the vocabulary, or a reader cannot tell a typo from a "
        "rule that was removed"
    )
