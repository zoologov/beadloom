"""Self-checks of this repository's manifest, CI workflows and configuration (BDL-074 A3).

Moved out of ``tests/test_ci_windows_dimension.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

from tests.support.ci_workflows import GH_CI, windows_jobs

#: The commit that holds the leg, its anti-vacuity probe and the sixteen rows
#: that exercised the probe. Named so a future re-add restores the lock with the
#: leg rather than reinventing a weaker one.
LEG_COMMIT = "98bcb0d"


def test_the_pipeline_runs_no_windows_leg() -> None:
    """The owner declined the platform dimension; the workflow says the same thing.

    If this fails because a Windows leg was re-added, the leg needs its
    anti-vacuity probe back with it — a Windows runner that cannot create a
    symbolic link capability-skips the six guard rows the leg is bought for and
    reports green on the rest. Restore both from ``98bcb0d`` and re-price the
    ~16-28 runner-minutes per PR, rather than adding the job alone.
    """
    assert windows_jobs(GH_CI) == [], (
        f"ci.yml runs a Windows leg again; it was withdrawn in "
        f"beadloom-mr2l.64 for cost. Restore the probe from {LEG_COMMIT} with "
        "it, or the leg can go green while covering nothing it was bought for."
    )


def test_the_workflow_states_why_there_is_no_platform_dimension() -> None:
    """An absence with a reason is a decision; an absence without one is a gap.

    The next person to ask "why does this pipeline vary the locale but not the
    platform?" reads ci.yml, not a closed bead, so the price and the bead id are
    in the file next to the dimension that WAS kept.
    """
    text = GH_CI.read_text(encoding="utf-8")

    assert "beadloom-mr2l.64" in text, (
        "ci.yml does not say why the platform dimension is absent; the locale "
        "dimension next to it carries its own price, and this one costs more"
    )
    assert "16-28" in text, "the withdrawal drops the measured cost that justified it"
