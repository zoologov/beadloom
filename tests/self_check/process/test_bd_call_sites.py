"""Self-checks of this repository's agent roles, hooks, tracker and commits (BDL-074 A3).

Moved out of ``tests/test_bd_call_sites.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.services.bd_seam.assumptions import (
    ASSUMPTION_COMPLETE_POPULATION,
    ASSUMPTION_UNTRUNCATED_POPULATION,
    VERDICT_SECURED,
    VERDICT_UNSECURED,
)
from beadloom.services.bd_seam.invocations import (
    CHANNEL_HOOK,
    CHANNEL_PYTHON,
)
from beadloom.services.bd_seam.population import project_report

if TYPE_CHECKING:
    from pathlib import Path


def test_every_python_list_call_names_the_population_it_asked_for(
    self_check_snapshot: Path
) -> None:
    """BDL-UX #187 is ours to answer at every consumer, and today every one does.

    This is the assertion that fails when somebody adds `run_bd(["list", ...])`
    without a filter: bd would hand it 55 rows of 842 and nothing would say so.
    """
    report = project_report(self_check_snapshot)
    lists = [
        site
        for site in report.sites
        if site.channel == CHANNEL_PYTHON and site.subcommand == "list"
    ]
    assert lists, "the python channel found no `bd list` call at all"
    for site in lists:
        verdicts = {a.name: a.verdict for a in site.assumptions}
        assert verdicts == {
            ASSUMPTION_COMPLETE_POPULATION: VERDICT_SECURED,
            ASSUMPTION_UNTRUNCATED_POPULATION: VERDICT_SECURED,
        }, f"{site.source}:{site.line} `{site.text}` reads a filtered view as complete"


def test_no_python_call_site_of_ours_is_left_unsettled(self_check_snapshot: Path) -> None:
    """An unsettled python call site is a regression, not a backlog item.

    **There were three, and each was closed by the bead that owned it.** The
    first was BDL-UX #97 arriving through our own surface: `handle_complete_bead`
    closed with `--suggest-next` and returned `close.stdout.strip()` to the MCP
    client under the key `next`, so an agent finishing a bead was handed a list
    that can name still-blocked beads, and `beadloom-0mdo.52` made it confirm
    against `bd ready --limit 0`. The other two were BDL-UX #171 in the scaffold:
    `_bd_create_bead` scraped the allocated id out of `--silent` stdout instead
    of asking for it, and `handle_task_init` wired `dep add` from ids it had
    authored. `beadloom-0mdo.53` replaced both with ONE `bd create --graph` whose
    edges name plan-local keys, so the `dep add` site does not exist any more and
    the ids are read from bd's own JSON answer.

    Zero is now the assertion, which is the strongest form this can take: any
    site added later with a call form that does not settle its assumption
    reddens here, and no number has to be revised to keep it honest.
    """
    report = project_report(self_check_snapshot)
    unsettled = [
        site for site in report.sites if site.channel == CHANNEL_PYTHON and site.unsettled
    ]
    assert unsettled == [], (
        "a python call site's assumption is newly unsettled: "
        + "; ".join(f"{s.source}:{s.line} `{s.text}`" for s in unsettled)
    )


def test_the_most_relied_upon_assumption_in_this_flow_is_named_at_its_sites(
    self_check_snapshot: Path
) -> None:
    """`bd ready` is what this flow calls authoritative, and it caps at 100.

    `CLAUDE.md` tells every role to take work only from `bd ready` and to confirm
    `--suggest-next` against it. Measured on bd 1.0.4 over a rig grown past the
    cap: 100 rows of 120, announced on stderr. The report must name those sites,
    because an assumption relied on everywhere and checked nowhere is precisely
    what this epic converts.
    """
    report = project_report(self_check_snapshot)
    ready = [site for site in report.sites if site.subcommand == "ready"]
    assert len(ready) > 1
    assert all(
        any(
            a.name == ASSUMPTION_UNTRUNCATED_POPULATION and a.verdict == VERDICT_UNSECURED
            for a in site.assumptions
        )
        for site in ready
        if "--limit" not in site.flags and "-n" not in site.flags
    )
    assert any(site.source.endswith("CLAUDE.md") for site in ready)


def test_the_hook_channel_reaches_the_file_no_python_sweep_can_see(
    self_check_snapshot: Path
) -> None:
    """`beadloom-l2f2`'s subject: `.git/hooks/post-merge`, written by `bd init`.

    The RFC recorded it as "outside the repository entirely", untracked and named
    nowhere under `src/`. Reading the hooks where they RUN reaches it. Skipped
    rather than asserted away when the hooks are not installed, and the report
    names that absence itself.
    """
    hooks = self_check_snapshot / ".git" / "hooks"
    if not (hooks / "post-merge").is_file():
        pytest.skip("no post-merge hook is installed in this room")
    report = project_report(self_check_snapshot)
    assert any(site.channel == CHANNEL_HOOK for site in report.sites)


def test_the_derivation_names_what_it_did_not_reach(self_check_snapshot: Path) -> None:
    """A derivation that returned only what it found would hand over a clean list."""
    report = project_report(self_check_snapshot)
    assert report.unreached
    for region, why in report.unreached:
        assert region and why, "a region named with no reason is a region nobody can act on"
