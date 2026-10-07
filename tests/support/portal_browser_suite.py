"""The browser suite the scaffold ships, as this repository's tests run and read it.

BDL-076 (``beadloom-ujzb.17``). The Playwright suite ships in the scaffold, so an
adopter runs it on their own portal with ``npm run test:e2e``. A case whose shape
the served graph lacks (no declared layer, an empty landscape, no page under
``other/``, ...) skips through ``e2e/support/shape.js`` and names that shape; under
the switch that file defines, a missing shape fails the case instead.

:func:`shape_constant` reads the switch and the skip wording from that file, so a
test here cannot drift from the suite. :func:`run_shipped_suite` runs the suite the
way the adopter does, adding only a JSON report beside the console one, and
:class:`BrowserRun` reads each case's outcome, tags and skip reason from that report.

``beadloom-m6k7.7``: the cases tagged :func:`adopter_sized_tag` run on a made-up
graph of an adopter's size that takes nothing from the portal but its declared
layer ranks (``e2e/support/adopterGraph.js``). On two portals that declare as many
layers they do the same work, so a run may leave them out, through the switch that
file names, where another portal of that layer count has run them.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from tests.support.repository_root import REPO_ROOT

if TYPE_CHECKING:
    from pathlib import Path

#: The suite as it ships, in the scaffold.
SHIPPED_E2E = REPO_ROOT / "src" / "beadloom" / "site_scaffold" / "e2e"

#: The one file through which a shipped case may skip.
SHAPE_HELPER = SHIPPED_E2E / "support" / "shape.js"

#: The module that makes the adopter-sized graph and names the tag of its cases.
ADOPTER_GRAPH = SHIPPED_E2E / "support" / "adopterGraph.js"


def _exported_string(module: Path, name: str) -> str:
    """The string constant *name* that the suite's *module* exports."""
    text = module.read_text(encoding="utf-8")
    match = re.search(rf'export const {re.escape(name)} = "([^"]+)";', text)
    if match is None:
        raise LookupError(f"{module.name} exports no string constant {name}")
    return match.group(1)


def shape_constant(name: str) -> str:
    """The string constant *name* that :data:`SHAPE_HELPER` exports."""
    return _exported_string(SHAPE_HELPER, name)


def adopter_sized_tag() -> str:
    """The tag of the cases on the adopter-sized graph, as :data:`ADOPTER_GRAPH` names it."""
    return _exported_string(ADOPTER_GRAPH, "ADOPTER_SIZED")


@dataclass(frozen=True)
class BrowserCase:
    """One case of a run: its spec file, its title, its outcome, why it skipped and its tags.

    ``ran`` is whether Playwright started the case. One it never started, as a
    case of a project whose dependency failed, is reported as skipped with no
    result and no reason (``beadloom-btkd.22``).
    """

    file: str
    title: str
    status: str
    skip_reason: str | None
    tags: tuple[str, ...] = ()
    ran: bool = True


@dataclass(frozen=True)
class BrowserRun:
    """A run of the shipped suite: its exit code, its console output and its JSON report."""

    returncode: int
    output: str
    report: dict[str, Any]

    def cases(self) -> list[BrowserCase]:
        """Every case the report holds, in the report's order."""
        found: list[BrowserCase] = []

        def walk(suite: dict[str, Any]) -> None:
            for child in suite.get("suites", []):
                walk(child)
            for spec in suite.get("specs", []):
                for case in spec.get("tests", []):
                    skips = [a for a in case.get("annotations", []) if a.get("type") == "skip"]
                    reason = skips[0].get("description") if skips else None
                    tags = tuple(f"@{tag}" for tag in spec.get("tags", []))
                    ran = bool(case.get("results"))
                    found.append(
                        BrowserCase(spec["file"], spec["title"], case["status"], reason, tags, ran)
                    )

        for suite in self.report.get("suites", []):
            walk(suite)
        return found

    def failures(self) -> str:
        """The failed cases of the console output, from the first one on, or its tail."""
        first = self.output.find("  1) ")
        return self.output[first : first + 12000] if first >= 0 else self.output[-8000:]


def run_shipped_suite(
    npm: str, site: Path, port: str, report: Path, *, adopter_sized: bool = True
) -> BrowserRun:
    """``npm run test:e2e`` in the portal at *site*, served on *port*, reported to *report*.

    ``CI=1`` as on a build server: a fresh server on the port, never one left
    running by somebody else. The skip switch is removed from the environment,
    because a portal an adopter builds may lack a shape and is still correct.
    With *adopter_sized* false the cases on the adopter-sized graph are left out,
    through the switch :data:`ADOPTER_GRAPH` names; otherwise that switch is
    removed, so a run takes them unless it is asked not to.
    """
    environment = {
        **os.environ,
        "CI": "1",
        "BEADLOOM_E2E_PORT": port,
        "PLAYWRIGHT_JSON_OUTPUT_FILE": str(report),
    }
    environment.pop(shape_constant("NO_SKIP"), None)
    leave_out = _exported_string(ADOPTER_GRAPH, "NO_ADOPTER_SIZED")
    environment.pop(leave_out, None)
    if not adopter_sized:
        environment[leave_out] = "1"
    done = subprocess.run(  # noqa: S603 - the portal's own browser suite, as its adopter runs it
        [npm, "run", "test:e2e", "--", "--reporter=line,json"],
        cwd=site,
        env=environment,
        capture_output=True,
        encoding="utf-8",
        check=False,
    )
    loaded: dict[str, Any] = (
        json.loads(report.read_text(encoding="utf-8")) if report.is_file() else {}
    )
    return BrowserRun(done.returncode, done.stdout + done.stderr, loaded)
