"""The derived `bd` call-site population (BDL-068 S5, `beadloom-0mdo.51`).

CONTEXT Q4: an External ``bd`` finding is answered by deriving our own call sites
and asserting what each assumes about the answer, never by a wrapper. The tests
below are therefore about the DERIVATION and about this repository's own
population, so a call site added later fails here rather than passing quietly.

**Every verdict is against bd 1.0.4**, and
:func:`test_the_recorded_release_is_the_one_installed` fails loudly when that
stops being true. That test is the point of the version pin: three premises this
slice inherited were re-measured and destroyed, and an External defect a later
``bd`` fixes must fail rather than guard nothing.

**A fourth withdrawal was made in this bead and was wrong**, which is why
:func:`test_a_defect_is_not_withdrawn_on_one_dependency_shape` exists. BDL-UX #97
was withdrawn on a measurement that was true and one-shaped — silent while the
target was blocked, speaking when it became ready, both directions of the
OUTCOME and one dependency shape. Over ten shapes ``--suggest-next`` lies in
four, and it is silent in exactly the shape that measurement used.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from typing import TYPE_CHECKING

import pytest

from beadloom.services.bd_seam.assumptions import (
    ASSUMPTION_ALLOCATED_ID,
    ASSUMPTION_COMPLETE_POPULATION,
    ASSUMPTION_EXCLUSIVE_HOLD,
    ASSUMPTION_INTENDED_ID,
    ASSUMPTION_LEGACY_ALIAS,
    ASSUMPTION_UNBLOCKED_IS_READY,
    ASSUMPTION_UNMEASURED_SUBCOMMAND,
    ASSUMPTION_UNTRUNCATED_POPULATION,
    BD_MEASURED_VERSION,
    VERDICT_HOLDS,
    VERDICT_SECURED,
    VERDICT_UNMEASURED,
    VERDICT_UNSECURED,
    call_sites,
    lock_invocations,
    report_of,
    subcommand_of,
)
from beadloom.services.bd_seam.client import _BD_DECODE_ERRORS, _BD_ENCODING
from beadloom.services.bd_seam.invocations import (
    CHANNEL_HOOK,
    CHANNEL_PYTHON,
    python_invocations,
    text_invocations,
)
from beadloom.services.bd_seam.population import UNREACHED, project_report
from tests.support.repository_root import REPO_ROOT as _PROJECT_ROOT

if TYPE_CHECKING:
    from pathlib import Path


def _judge(text: str) -> tuple[str, ...]:
    """The verdicts of the one site *text* carries, as ``name=verdict``."""
    sites = call_sites(text_invocations([("a.md", text)]))
    assert len(sites) == 1, f"{text!r} produced {len(sites)} sites, not one"
    return tuple(f"{a.name}={a.verdict}" for a in sites[0].assumptions)


# --------------------------------------------------------------------------
# The version the whole table is pinned to.
# --------------------------------------------------------------------------


def test_the_recorded_release_is_the_one_installed() -> None:
    """A verdict measured on one release must fail loudly on another.

    Not a pin on what may be installed — a statement that every ``holds`` in the
    table was taken on ONE ``bd`` and cannot be carried to a different one
    without re-measuring. BDL-UX #97 was annotated "1.0.4" by someone writing the
    note months after the observation, and that is exactly how a withdrawn defect
    would come back as a silent guard over nothing.
    """
    if shutil.which("bd") is None:
        pytest.skip("bd is not installed, so the room this table was measured in is absent")
    printed = subprocess.run(
        ["bd", "version"],  # noqa: S607
        capture_output=True,
        encoding=_BD_ENCODING,
        errors=_BD_DECODE_ERRORS,
        check=False,
        timeout=30,
    ).stdout
    found = re.search(r"\b(\d+\.\d+\.\d+)\b", printed)
    assert found is not None, f"`bd version` printed no version: {printed!r}"
    assert found.group(1) == BD_MEASURED_VERSION, (
        f"every verdict in `bd_seam/assumptions.py` was measured on bd "
        f"{BD_MEASURED_VERSION} and bd {found.group(1)} is installed. Re-measure "
        f"the table — in particular every `holds`, which is a claim about a "
        f"release and not about a call form: `bd close --suggest-next` (#97), "
        f"`bd import -i` (beadloom-l2f2), and both `bd list` default filters "
        f"(#187) — then move BD_MEASURED_VERSION."
    )


# --------------------------------------------------------------------------
# The grammar: over a shape, in both directions.
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "line",
    [
        "bd ready",
        "  bd ready --claim",
        "Run `bd ready` first",
        "$ bd ready",
        "3. bd ready",
        "git commit && bd ready",
        "if ! bd import -i f; then",
        'echo "Run \'bd import -i f\' manually"',
    ],
)
def test_a_command_position_invocation_is_found(line: str) -> None:
    assert text_invocations([("a.md", line)]), f"{line!r} carries an invocation"


@pytest.mark.parametrize(
    "line",
    [
        "the only release form bd verifies",
        "and reports success. bd checks the holder only when you pass",
        "flag the bead plus a bd comment with the unresolved refs",
        "Warning: bd command not found, skipping post-merge import",
        "the agentic flow requires bd installs are present",
    ],
)
def test_prose_about_bd_is_not_an_invocation(line: str) -> None:
    """Without the command-position anchor these five are reported as call sites.

    Measured over this repository's 65 instructing artifacts: the anchored sweep
    returns 266 invocations and no prose, and the unanchored one adds these.
    """
    assert not text_invocations([("a.md", line)]), f"{line!r} instructs nobody"


def test_a_trailing_comment_is_not_part_of_the_command() -> None:
    """The composed role cores carry exactly this line, seventeen times."""
    line = "bd merge-slot release --holder <bead-id>   # the only release form bd verifies"
    found = text_invocations([("a.md", line)])
    assert len(found) == 1
    assert found[0].text == "bd merge-slot release --holder <bead-id>"


def test_a_quote_anchored_invocation_ends_at_its_quote() -> None:
    """`.git/hooks/post-merge:53` is one instruction and then prose about it."""
    line = "    echo \"Run 'bd import -i $BEADS_DIR/issues.jsonl' manually to see the error\""
    found = text_invocations([("a.md", line)])
    assert [site.text for site in found] == ["bd import -i $BEADS_DIR/issues.jsonl"]


def test_a_redirection_is_not_an_argument() -> None:
    found = text_invocations([("a.md", 'if ! bd import -i "$F" >/dev/null 2>&1; then')])
    assert found[0].text == 'bd import -i "$F"'


@pytest.mark.parametrize(
    ("words", "expected"),
    [
        (("dep", "add"), "dep add"),
        (("dep", "tree"), "dep tree"),
        (("merge-slot", "acquire"), "merge-slot acquire"),
        (("show", "beadloom-x"), "show"),
        (("close",), "close"),
        (("quickstart",), "quickstart"),
    ],
)
def test_a_subcommand_is_the_longest_measured_form(
    words: tuple[str, ...], expected: str
) -> None:
    """Two ids after `dep add` must not be read as part of the name."""
    assert subcommand_of(words) == expected


# --------------------------------------------------------------------------
# The python channel.
# --------------------------------------------------------------------------


def test_a_module_level_constant_resolves() -> None:
    """`guard_probes` passes `CLAIMED_STATUS` and `UNLIMITED`; a literal-only
    reader would report this project's most careful call site as unresolved."""
    module = (
        'CLAIMED = "in_progress"\n'
        'UNLIMITED = "0"\n'
        "\n"
        "def probe():\n"
        '    return run_bd(["list", "--status", CLAIMED, "--json", "--limit", UNLIMITED])\n'
    )
    found = python_invocations([("p.py", module)])
    assert len(found) == 1
    assert found[0].unresolved_arguments == 0
    assert found[0].channel == CHANNEL_PYTHON
    assert found[0].flags == ("--status", "--json", "--limit")


def test_a_runtime_argument_is_counted_and_does_not_hide_its_subcommand() -> None:
    module = 'def close(bead):\n    return run_bd(["close", bead, "--suggest-next"])\n'
    found = python_invocations([("p.py", module)])
    assert (found[0].words, found[0].unresolved_arguments) == (("close",), 1)


def test_a_module_that_cannot_be_parsed_is_skipped_rather_than_guessed_at() -> None:
    assert python_invocations([("broken.py", "def (:\n")]) == ()


# --------------------------------------------------------------------------
# The four verdicts, each in both directions.
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        # BDL-UX #187: two default filters, and bd announces one of them.
        (
            "bd list --json",
            (
                f"{ASSUMPTION_COMPLETE_POPULATION}={VERDICT_UNSECURED}",
                f"{ASSUMPTION_UNTRUNCATED_POPULATION}={VERDICT_UNSECURED}",
            ),
        ),
        (
            "bd list --status open --json",
            (
                f"{ASSUMPTION_COMPLETE_POPULATION}={VERDICT_SECURED}",
                f"{ASSUMPTION_UNTRUNCATED_POPULATION}={VERDICT_UNSECURED}",
            ),
        ),
        (
            "bd list --all --json",
            (
                f"{ASSUMPTION_COMPLETE_POPULATION}={VERDICT_SECURED}",
                f"{ASSUMPTION_UNTRUNCATED_POPULATION}={VERDICT_SECURED}",
            ),
        ),
        (
            "bd list --json --limit 0",
            (
                f"{ASSUMPTION_COMPLETE_POPULATION}={VERDICT_UNSECURED}",
                f"{ASSUMPTION_UNTRUNCATED_POPULATION}={VERDICT_SECURED}",
            ),
        ),
        # The cap `bd ready` carries is a different number and no entry records it.
        ("bd ready", (f"{ASSUMPTION_UNTRUNCATED_POPULATION}={VERDICT_UNSECURED}",)),
        ("bd ready --limit 0", (f"{ASSUMPTION_UNTRUNCATED_POPULATION}={VERDICT_SECURED}",)),
        # BDL-UX #171: the remedy exists upstream.
        ("bd create 'a' --type task", (f"{ASSUMPTION_ALLOCATED_ID}={VERDICT_UNSECURED}",)),
        ("bd create 'a' --json", (f"{ASSUMPTION_ALLOCATED_ID}={VERDICT_SECURED}",)),
        # BDL-UX #171's third item: nothing at the call site can settle it.
        ("bd dep add a b", (f"{ASSUMPTION_INTENDED_ID}={VERDICT_UNSECURED}",)),
        # BDL-UX #97 STANDS: it names beads that are still blocked, and no flag
        # settles it. Withdrawn once in this bead on one dependency shape; see
        # `test_a_defect_is_not_withdrawn_on_one_dependency_shape` below.
        (
            "bd close x --suggest-next",
            (f"{ASSUMPTION_UNBLOCKED_IS_READY}={VERDICT_UNSECURED}",),
        ),
        # beadloom-l2f2, withdrawn: the alias exists.
        ("bd import -i f", (f"{ASSUMPTION_LEGACY_ALIAS}={VERDICT_HOLDS}",)),
        ("bd import f", ()),
        # BDL-UX #194 / #237, withdrawn: the primitive is sound, the form was not.
        (
            "bd merge-slot acquire --holder <bead-id>",
            (f"{ASSUMPTION_EXCLUSIVE_HOLD}={VERDICT_SECURED}",),
        ),
        ("bd merge-slot acquire", (f"{ASSUMPTION_EXCLUSIVE_HOLD}={VERDICT_UNSECURED}",)),
        ("bd merge-slot release", (f"{ASSUMPTION_EXCLUSIVE_HOLD}={VERDICT_UNSECURED}",)),
        (
            "bd merge-slot acquire --holder x --wait",
            (f"{ASSUMPTION_EXCLUSIVE_HOLD}={VERDICT_UNSECURED}",),
        ),
        # An unjudged site must never read as a clean one.
        ("bd quickstart", (f"{ASSUMPTION_UNMEASURED_SUBCOMMAND}={VERDICT_UNMEASURED}",)),
        ("bd merge-slot rescind", (f"{ASSUMPTION_EXCLUSIVE_HOLD}={VERDICT_UNMEASURED}",)),
        # Measured to carry no assumption this table knows how to break, which is
        # a different fact from a subcommand nobody looked at.
        ("bd show beadloom-x --json", ()),
        ("bd export -o .beads/issues.jsonl", ()),
    ],
)
def test_a_call_form_earns_the_verdict_its_flags_earn(
    line: str, expected: tuple[str, ...]
) -> None:
    assert _judge(line) == expected


def test_a_defect_is_not_withdrawn_on_one_dependency_shape() -> None:
    """BDL-UX #97 stands, and this test is the record of why it was withdrawn.

    The withdrawal came from a rig where one target had two blockers and one was
    closed: `--suggest-next` printed nothing while the target was blocked and
    named it exactly when it became ready. Both directions of the OUTCOME, and
    one dependency shape.

    Closing `beadloom-0mdo.51` minutes later named `beadloom-0mdo.55` and
    `beadloom-0mdo.13`, which `bd dep tree` shows blocked by four and six open
    beads and which `bd ready` correctly excludes. Re-measured over ten shapes,
    varying the number of already-closed blockers, the number remaining, and
    whether the target was created before or after them, `--suggest-next` names a
    still-blocked bead in four of the ten — and is silent in EVERY shape where
    exactly one blocker had been closed, which is the cell the first measurement
    picked.

    So `unblocked-is-ready` is `unsecured` and not `holds`, and the sentence a
    reader gets says the entry stands. `bd ready` was correct in all ten shapes,
    which is what `CLAUDE.md` already tells every role — instruction that this
    measurement now supports rather than contradicts.
    """
    sites = call_sites(text_invocations([("a.md", "bd close x --suggest-next")]))
    verdicts = {a.name: a for a in sites[0].assumptions}
    assumption = verdicts[ASSUMPTION_UNBLOCKED_IS_READY]
    assert assumption.verdict == VERDICT_UNSECURED
    assert "bd ready" in assumption.detail, "the remedy must reach the reader"
    assert BD_MEASURED_VERSION in assumption.detail


def test_the_landing_lock_is_judged_once_and_not_twice(tmp_path: Path) -> None:
    """`application/waves/landing.py` carries no grammar of its own any more.

    `beadloom-0mdo.39` derived merge-slot sites with a regex of its own. This bead
    generalised that grammar to every subcommand and homed it at the seam, so the
    application layer imports no ``re`` at all and receives parsed invocations.
    Two derivations of one kind is the defect the epic is removing.
    """
    landing = (_PROJECT_ROOT / "src/beadloom/application/waves/landing.py").read_text(
        encoding="utf-8"
    )
    assert "import re" not in landing
    assert "re.compile" not in landing
    invocations = text_invocations([("a.md", "bd merge-slot acquire --holder x")])
    assert len(lock_invocations(invocations)) == 1


# --------------------------------------------------------------------------
# The population's reports. This repository's own population — the part that
# fails on a call site added later — is a self-check since BDL-074 A3:
# tests/self_check/process/test_bd_call_sites.py.
# --------------------------------------------------------------------------


def test_an_empty_population_still_states_the_release_it_was_judged_against() -> None:
    empty = report_of(())
    assert empty.sites == ()
    assert empty.measured_against == BD_MEASURED_VERSION


def test_the_declared_unreached_regions_each_carry_a_reason() -> None:
    assert len(UNREACHED) >= 4
    assert all(len(why) > 40 for _, why in UNREACHED)


def test_the_hook_channel_reads_the_hooks_a_project_has_installed(tmp_path: Path) -> None:
    """A hook runs from disk, so the derivation reads it there, and skips a sample.

    Its self-check twin reads the hooks installed in this checkout, which the
    self-check snapshot does not carry (a clone copies no hooks), so it skips
    wherever the suite runs isolated. This holds the channel on a project whose
    one hook the test writes (BDL-074 A3).
    """
    hooks = tmp_path / ".git" / "hooks"
    hooks.mkdir(parents=True)
    (hooks / "post-merge").write_text("#!/bin/sh\nbd sync --import-only\n", encoding="utf-8")
    (hooks / "pre-commit.sample").write_text("#!/bin/sh\nbd ready\n", encoding="utf-8")

    report = project_report(tmp_path)

    hooked = [site for site in report.sites if site.channel == CHANNEL_HOOK]
    assert [(site.source, site.line, site.subcommand) for site in hooked] == [
        (".git/hooks/post-merge", 2, "sync")
    ]
