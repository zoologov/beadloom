"""The product code the slow tests' beadloom steps run, traced in a fresh interpreter.

BDL-076, the re-review's finding m6 (``beadloom-ujzb.22``), fixed by ``beadloom-ujzb.24``.
The ``site-adopters`` workflow runs only on a pull request that changes what it tests,
through a ``paths:`` filter, and the self-check held that filter to the files the slow
tests READ - the tests, their conftests and the support modules they import - while
the product code they RUN was a hand list. It missed ``application/reindex``, the
``init`` command and every module those reach, so a pull request changing how
``init`` or ``reindex`` reads an adopter's project started no run.

**How the set is derived.** :func:`~tests.support.adopter_portals.adopt` - the beadloom
half of the build every slow test makes (``init``, ``reindex``, ``docs site``) - is run
on every adopter fixture with a profile hook installed, and every file under
``src/beadloom`` whose code is ENTERED while it runs is recorded: a function called,
and the body of a module imported for the first time during the run. A module the
command line imports before any step, and nothing in it is called, is not counted:
it is code every command loads, not code these steps run.

**Why a fresh interpreter.** A module imported earlier in the same process - by
another test - is not imported again, so its body would go unrecorded depending on
the order the suite ran in. Run as ``python -m tests.support.slow_test_trace <dir>``;
it prints one repository-relative path per line and exits 1 when a step failed,
because a trace of a run that stopped early is not the run the slow tests make.

**What it cannot see.** Code entered only in a thread the hook was not installed for,
and the npm half of the build, which runs no Python.
"""

from __future__ import annotations

import sys
import threading
from pathlib import Path
from typing import TYPE_CHECKING

from tests.support.adopter_portals import FIXTURES_BY_STACK, adopt
from tests.support.repository_root import REPO_ROOT

if TYPE_CHECKING:
    from types import FrameType

#: The package whose files are traced.
PRODUCT = REPO_ROOT / "src" / "beadloom"


def trace(workdir: Path) -> tuple[frozenset[str], list[str]]:
    """Every product file entered while the fixtures are adopted under *workdir*, and failures."""
    product = str(PRODUCT.resolve())
    entered: set[str] = set()

    def hook(frame: FrameType, event: str, _arg: object) -> None:
        if event == "call" and frame.f_code.co_filename.startswith(product):
            entered.add(frame.f_code.co_filename)

    failures: list[str] = []
    sys.setprofile(hook)
    threading.setprofile(hook)
    try:
        for fixture in FIXTURES_BY_STACK.values():
            failed = adopt(fixture, workdir).failed_step()
            if failed is not None:
                failures.append(f"{fixture.stack}: {failed}")
    finally:
        sys.setprofile(None)
        threading.setprofile(None)
    files = frozenset(Path(path).resolve().relative_to(REPO_ROOT).as_posix() for path in entered)
    return files, failures


def main(argv: list[str]) -> int:
    """Print the traced files, one per line; exit 1 naming the failed steps when any failed."""
    (workdir,) = argv
    files, failures = trace(Path(workdir))
    if failures:
        sys.stderr.write("\n".join(failures) + "\n")
        return 1
    sys.stdout.write("".join(f"{path}\n" for path in sorted(files)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
