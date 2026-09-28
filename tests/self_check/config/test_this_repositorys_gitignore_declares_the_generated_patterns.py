"""This repository's own ``.gitignore`` declares every pattern this version generates.

BDL-068 S6 (`beadloom-0mdo.40`). The drift the ignore-block check exists for was
found in this repository's own file: it carried the exact name
``.beadloom/guard-firings.jsonl`` while the generator had emitted the glob
``.beadloom/guard-firings*.jsonl`` since rotation shipped, and the rotated log
showed up as untracked churn. The product behaviour is judged over projects on
disk in ``tests/acceptance/features/ignore_block_drift.feature``. This module
holds the one claim about this repository.

Until BDL-074 F3 (`beadloom-2mj3.8`) the claim was the last scenario of that
feature. It asserts on this repository's tree, so it is a self-check, and it
moved here under its scenario's name. The ``config-check`` Gate leg reports the
same drift at ``warn`` and never blocks on it, which is why this is a test and
not a removed duplicate of that leg.

It reads the tracked ``.gitignore`` through ``REPO_ROOT``, like the other files in
this folder, and never the index, the tracker or the history. It carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

from beadloom.onboarding.ignore_block import undeclared_patterns
from tests.support.repository_root import REPO_ROOT


def test_this_repositorys_own_gitignore_declares_every_pattern_this_version_emits() -> None:
    path = REPO_ROOT / ".gitignore"
    # Asserted rather than skipped: a checkout without the file is one this claim
    # cannot be taken in, and the claim is the same in every room.
    assert path.is_file(), f"no .gitignore at the repository root {REPO_ROOT}"

    findings = undeclared_patterns(path.read_text(encoding="utf-8"))

    assert findings == [], [finding.pattern for finding in findings]
