"""A case Playwright never started is told from a case that skipped and named a shape.

``beadloom-btkd.22``. The shipped suite times the viewer in a project of its own
that depends on every other case (``e2e/playwright.config.js``): when one of those
fails, Playwright starts none of the timing cases and reports each as skipped,
with no result and no reason. On PR #94 the python fixture's run failed one case,
and its ten timing cases were then read as skips that named no shape, a second
failure that was the first one counted again.

The report says which is which: a case that ran carries a result, a case never
started carries none. These tests read a report of that form, recorded from a
run where one case of the ``chromium`` project failed.
"""

from __future__ import annotations

from typing import Any

from tests.support.portal_browser_suite import BrowserRun

#: The skip the shape helper writes, as a case that ran reports it.
_SHAPE_SKIP = {
    "type": "skip",
    "description": "this portal's graph lacks what the case needs: no declared layer",
}


def _spec(file: str, title: str, project: str, status: str, results: list[Any]) -> dict[str, Any]:
    """A spec of a Playwright JSON report holding one case."""
    annotations = [a for result in results for a in result.get("annotations", [])]
    return {
        "file": file,
        "title": title,
        "tags": [],
        "tests": [
            {
                "projectName": project,
                "status": status,
                "annotations": annotations,
                "results": results,
            }
        ],
    }


def _report(*specs: dict[str, Any]) -> dict[str, Any]:
    return {"suites": [{"title": "e2e", "specs": list(specs), "suites": []}]}


def test_a_case_with_no_result_was_never_started() -> None:
    run = BrowserRun(
        1,
        "",
        _report(
            _spec(
                "layout.spec.js",
                "the toolbar answers",
                "chromium",
                "unexpected",
                [{"status": "failed"}],
            ),
            _spec("performance.spec.js", "a frame takes no longer", "performance", "skipped", []),
        ),
    )

    assert [(case.title, case.ran) for case in run.cases()] == [
        ("the toolbar answers", True),
        ("a frame takes no longer", False),
    ]


def test_a_case_that_skipped_by_naming_a_shape_ran() -> None:
    run = BrowserRun(
        0,
        "",
        _report(
            _spec(
                "layers.spec.js",
                "a layer's band",
                "chromium",
                "skipped",
                [{"status": "skipped", "annotations": [_SHAPE_SKIP]}],
            )
        ),
    )

    (case,) = run.cases()

    assert (case.status, case.ran, case.skip_reason) == (
        "skipped",
        True,
        _SHAPE_SKIP["description"],
    )
