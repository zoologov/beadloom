"""Self-checks of this repository's agent roles, hooks, tracker and commits (BDL-074 A3).

Moved out of ``tests/test_windows_dimension.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

import subprocess
import sys

from tests.support.repository_root import TESTS_ROOT as TESTS_DIR

#: The six rows BDL-061.36 item 3 was written about, by node id. Named
#: individually rather than counted: a count stays right while the rows are
#: replaced by different ones, and after beadloom-mr2l.64 withdrew the Windows
#: leg these six plus the ledger above them are the whole surviving deliverable
#: of BDL-061.39 — so what proves they RAN has to be as specific as they are.
#: (Five marks, six rows: one is parametrised over two targets.)
THE_SIX_CAPABILITY_GATED_ROWS = (
    "tests/test_guards_paths.py::TestTraversalCannotBypassAnExclusion::"
    "test_a_symlink_out_of_an_excluded_directory_is_guarded",
    "tests/test_guards_paths.py::TestSymlinksInBothDirections::"
    "test_a_link_into_the_excluded_tree_is_excluded",
    "tests/test_guards_paths.py::TestSymlinksInBothDirections::"
    "test_an_exclusion_stops_applying_when_its_directory_is_a_symlink",
    "tests/test_guards_paths.py::TestASymlinkLoopEndsInAVerdictAndNeverInATraceback::"
    "test_a_real_loop_comes_back_as_a_scope_whatever_this_platform_does[a]",
    "tests/test_guards_paths.py::TestASymlinkLoopEndsInAVerdictAndNeverInATraceback::"
    "test_a_real_loop_comes_back_as_a_scope_whatever_this_platform_does[a/x.py]",
    "tests/test_guards_paths.py::TestASymlinkLoopEndsInAVerdictAndNeverInATraceback::"
    "test_the_guard_reaches_a_verdict_through_a_real_loop",
)


class TestTheSymlinkCapabilityProbe:
    """The replacement for the six platform marks must itself be non-vacuous."""

    def test_the_six_rows_are_observed_to_run_rather_than_inferred_to(self) -> None:
        """The same guard again, and this time about the OUTCOME, not the wiring.

        The row above closes the one joint the review cut. This one does not
        care where the cut is: it runs the six by node id in a child pytest and
        reads what happened to them, so a constant condition, an edited mark, a
        module-level ``pytestmark``, a ``conftest`` that deselects them or a
        renamed row all redden it. That is the standard this epic converged on —
        a check that cannot fail is not a check — applied to the probe itself,
        which had until now been the one thing checking everything else.

        A machine that genuinely cannot create a symbolic link fails here rather
        than skipping six guard tests quietly elsewhere. That is deliberate and
        it is the same stance as
        ``test_this_machine_can_link_so_the_six_guard_rows_actually_run``: this
        project's own runners can link, so the honest report of an image that
        cannot is a red row that names the reason, not a green suite.
        """
        completed = subprocess.run(  # noqa: S603
            [
                sys.executable,
                "-m",
                "pytest",
                *THE_SIX_CAPABILITY_GATED_ROWS,
                "-p",
                "no:randomly",
                "-q",
                "--no-header",
                "-rs",
                "--tb=line",
            ],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            cwd=TESTS_DIR.parent,
            check=False,
        )
        report = completed.stdout + completed.stderr

        assert completed.returncode == 0, (
            "the six capability-gated guard rows did not all pass. A non-zero "
            "exit with no failure below usually means a node id no longer "
            f"exists — they are named, not counted, on purpose.\n{report}"
        )
        assert "skipped" not in report.lower(), (
            "at least one of the six was SKIPPED on a machine that can create "
            f"symbolic links, which is the defect BDL-061.39 removed.\n{report}"
        )
        assert f"{len(THE_SIX_CAPABILITY_GATED_ROWS)} passed" in report, report
