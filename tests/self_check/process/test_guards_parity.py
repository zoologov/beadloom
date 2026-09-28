"""Self-checks of this repository's agent roles, hooks, tracker and commits (BDL-074 A3).

Moved out of ``tests/integration/application/guards/test_guards_parity.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

import hashlib
import time
from pathlib import Path

from beadloom.application.guards.evaluation import evaluate_guard
from tests.support.guard_parity import (
    attribute,
    differing,
    report_attribution,
)


class TestGuardsAreReadOnly:
    def test_the_live_repo_index_is_byte_identical_after_a_real_evaluation(
        self, self_check_snapshot: Path
    ) -> None:
        """This repository's real index and real bd/git probes — not a stub's contract.

        **Measured on the self-check snapshot since BDL-074 A3**, not on the
        checkout the suite runs in: the snapshot is this repository's working
        tree with its own index and its git history, so the evaluation below
        runs the real guards against real data, and no test of the suite reads
        the live ``.beadloom/beadloom.db`` any more (``beadloom-qq6m``). What
        that gives up, stated: ``bd`` answers from the snapshot's copy of the
        tracker export, not from the tracker this checkout runs, and a
        concurrent ``beadloom lint`` in the checkout can no longer confound the
        comparison — the attribution below stays because a self-check earlier
        in the same session may still write the snapshot's index.

        ``lint`` mutates the index today (#147, standing rule 3); a guard must
        not, which is why the read-only claim is measured here rather than
        assumed from the absence of a visible write.

        **This test reads four files the REPOSITORY owns, not four files it
        owns**, which is the whole difficulty and was for a while mistaken for
        flakiness (BDL-062.10, m4). A byte change in ``beadloom.db`` means
        "somebody wrote the index", and the guard is only one of the candidates:
        a concurrent ``beadloom lint`` is another, and writing the index is that
        command's documented behaviour. Measured on this repository with a plain
        ``beadloom lint --project .`` looping alongside: **4 failures in 4
        consecutive runs**, ``beadloom.db`` differing in all four and
        ``.beads/issues.jsonl`` in one — none of them a guard, all of them
        reported as one. A red that a session cannot act on is worse than no
        check, because it teaches the reader to discount the next one.

        The confound is removed by ATTRIBUTION rather than by dropping the
        files or loosening the comparison, and there are two instruments for it
        because there are two kinds of writer.

        BY FILE, first, because it is cheap and certain. A guard's only tracker
        call is ``bd list``, a read, so ``.beads/issues.jsonl`` is outside every
        guard's reach and a change there is another process's whatever the clock
        says. The path is still compared, the change is still detected and the
        file is still named — it is charged to the writer that can write it. It
        is NOT removed from the comparison: a guard that gained a tracker write
        must turn this red, and the claim that it has not gained one is itself
        checked, by :class:`TestTheTrackerExportIsOutsideTheGuardsReach`, against
        the argv the evaluation actually issues.

        BY TIMING, second, for the files the guard could have written. A control
        window of at least the measurement window's duration runs with no
        evaluation in it; if the repository moves then too, another writer is
        active and this test honestly cannot attribute the change, so it skips
        and names the files. If the repository is still, the evaluation is the
        only candidate left and the assertion fails exactly as it always did.

        The order is the fix for BDL-UX #233, which read as flakiness and was
        not. The control window can only see a writer that is STILL WRITING when
        it opens — true of a concurrent ``beadloom lint``, false of a ``bd``
        export, which is one burst the tracker DEFERS to a moment no session
        command marks: measured here, a write leaves the export unmoved when
        sampled straight afterwards and rewritten by the next sample.
        Both observed failures named ``.beads/issues.jsonl`` and neither named
        ``beadloom.db``: the burst landed in the measurement window, missed the
        control window entirely, and the failure was reported as the guard's. A
        wave makes that likelier rather than rarer, since both agents run ``bd
        comments add`` — so the check was least reliable exactly where the flow
        is most parallel, which is how a check teaches its reader to discount it.
        The same reader-facing symptom reaches this file from two other causes:
        BDL-UX #168 (a random test order no seed reproduces) and #207 (the
        pre-commit hook re-staging the same file).

        The snapshots the assertions use are the ones taken at the END of the
        measurement window, not fresh reads taken after the control window. The
        earlier version re-read the tree at the assertion, so a write landing
        during the control sleep failed a claim about a window it was never in —
        the same defect one layer down.

        The ``-wal`` check is stated RELATIVE to what was there before, and the
        reason is measured rather than defensive (BDL-061.36): the file belongs
        to the repository, not to this test, and any earlier test in the session
        that opened the live index can own it. Traced with a teardown hook over
        ``pytest -k guard``, the ``-wal`` appears after
        ``test_bead15_s3b_coverage.py::TestErrorLevelRegressionGuard::
        test_new_uncovered_module_fails_lint_strict_at_error`` — a ``lint`` run
        against the real repo, i.e. the very command standing rule 3 is about —
        and outlives that test, so an absolute ``not exists()`` here fails on
        another command's connection while saying "a guard wrote to the index".
        What this test can honestly claim is that the evaluation below added
        none, which is what it now asserts.
        """
        from beadloom.services.guard_probes import build_probes

        root = self_check_snapshot
        db = root / ".beadloom" / "beadloom.db"
        assert db.is_file(), "the self-check snapshot carries an index of its own"
        tracked = [
            db,
            Path(f"{db}-wal"),
            Path(f"{db}-shm"),
            root / ".beads" / "issues.jsonl",
        ]

        def digest() -> dict[str, str]:
            return {
                path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                for path in tracked
                if path.is_file()
            }

        before = digest()
        wal = Path(f"{db}-wal")
        wal_before = wal.exists()
        started = time.monotonic()
        for name in ("bead-claimed", "working-branch"):
            verdict = evaluate_guard(
                name,
                project_root=root,
                context={"path": "src/beadloom/application/guards/evaluation.py"},
                probes=build_probes(root),
            )
            assert verdict.why
        window_s = time.monotonic() - started
        after = digest()
        wal_after = wal.exists()

        report_attribution(
            attribute(differing(before, after), snapshot=digest, window_s=window_s),
            window_s=window_s,
        )
        assert wal_after == wal_before, (
            "the evaluation left a write-ahead log the index did not have"
            if wal_after
            else "the evaluation checkpointed another connection's log"
        )
