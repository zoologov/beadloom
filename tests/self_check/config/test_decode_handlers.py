"""Self-checks of this repository's manifest, CI workflows and configuration (BDL-074 A3).

Moved out of ``tests/test_decode_handlers.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tests.test_decode_handlers import (
    _SRC_ROOT,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]


_PYPROJECT = _REPO_ROOT / "pyproject.toml"


#: ruff ships in the same ``dev`` extra as pytest, so a process that can run
#: this module can run ruff. Asserting that beats skipping on it: a skip here
#: would be inert on every leg that has the tool and silent on every leg that
#: does not, which is the "skip that can never fail" this epic keeps removing.
_RUFF = Path(sys.executable).parent / "ruff"


def _run_ruff(*args: str) -> subprocess.CompletedProcess[str]:
    """ruff, driven with THIS project's configuration and nothing implicit."""
    assert _RUFF.exists(), (
        f"ruff is not installed beside {sys.executable}. It comes from the same "
        "`dev` extra as pytest, so this suite cannot be running without it — "
        "install with `uv sync --extra dev` rather than skipping the check."
    )
    return subprocess.run(  # noqa: S603 — fixed argv, no shell
        [str(_RUFF), "check", "--config", str(_PYPROJECT), "--no-cache", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def _plw1514_findings(*paths: Path) -> list[dict[str, object]]:
    """Every ``unspecified-encoding`` ruff reports for *paths*, as data."""
    completed = _run_ruff("--output-format", "json", *(str(p) for p in paths))
    reported = json.loads(completed.stdout or "[]")
    return [item for item in reported if item["code"] == "PLW1514"]


class TestTheEncodingRuleIsSelectedAndBites:
    """Half one, and the false green it would otherwise be.

    ``PLW1514`` is a **preview** rule in ruff 0.16.3. Selecting it without
    enabling preview is not an error and not a failure: ruff prints ``warning:
    Selection `PLW1514` has no effect because preview is not enabled`` on
    stderr and exits **0** (measured with ``--isolated``). A configuration line
    that reads as a gate while checking nothing is precisely the class BDL-UX
    #172/#173 are about, so the check here is not "the code appears in
    ``select``" but "ruff, run with this project's own configuration, reports a
    planted site".

    One honest caveat about that measurement on *this* tree: dropping ``preview``
    happens to redden ``ruff check`` anyway, because the ``RUF002`` ``noqa`` in
    ``tests/test_decoding_symmetry.py`` that preview mode requires would then go
    unused and ``RUF100`` fires. That coupling is an accident of one comment and
    would vanish with it, so the guarantee rests on the planted site below and
    not on it.
    """

    @pytest.fixture(autouse=True)
    def _planting_ground(self, tmp_path: Path) -> None:
        self._tmp = tmp_path
        self._planted = 0

    def _plant(self, source: str) -> Path:
        """Write *source* to a fresh module and hand back its path."""
        self._planted += 1
        path = self._tmp / f"planted_{self._planted}.py"
        path.write_text(source, encoding="utf-8")
        return path

    def test_a_read_without_an_encoding_is_reported(self) -> None:
        """The planted module is the whole proof: two calls, two findings."""
        planted = self._plant(
            "from pathlib import Path\n"
            "\n"
            "\n"
            "def read(p: Path) -> str:\n"
            "    first = p.read_text()\n"
            "    with p.open() as handle:\n"
            "        second = handle.read()\n"
            "    return first + second\n"
        )

        reported = _plw1514_findings(planted)

        assert [item["location"]["row"] for item in reported] == [5, 6], (
            "ruff run with this project's configuration did not report text I/O "
            "without an explicit `encoding=`. Either PLW1514 left "
            "[tool.ruff.lint] select, or preview was turned off underneath it — "
            "in which case `ruff check` still exits 0 and the gate is off.\n"
            f"reported: {reported}"
        )

    def test_a_stated_encoding_is_not_reported(self) -> None:
        """The other direction, so the rule is not simply refusing everything."""
        planted = self._plant(
            "from pathlib import Path\n"
            "\n"
            "\n"
            "def read(p: Path) -> str:\n"
            '    return p.read_text(encoding="utf-8")\n'
        )

        assert _plw1514_findings(planted) == []

    def test_the_package_and_the_suite_are_clean_under_it(self) -> None:
        """Enabling the rule cost no code change, and this is what says so.

        ``.42`` swept about forty call sites before this rule was ever run, so
        the population it guards was already at zero. That is why half one is
        one configuration line: it locks a state that was reached by hand, and
        the next ``read_text()`` without an encoding fails the lint job of every
        leg of every pull request.
        """
        reported = _plw1514_findings(_REPO_ROOT / "src", _REPO_ROOT / "tests")

        rendered = "\n".join(
            f"  {item['filename']}:{item['location']['row']} {item['message']}"
            for item in reported
        )
        assert not reported, f"text I/O with no stated codec:\n{rendered}"

    def test_the_reach_of_the_rule_is_the_one_that_was_measured(self) -> None:
        """``PLW1514`` needs to KNOW the receiver is a ``Path``, and often cannot.

        Found by sabotage, not by reading the documentation: planting
        ``path.read_text()`` in ``graph/linter.py`` behind an *unannotated*
        parameter left ``ruff check src/ tests/`` at exit 0, and only the
        BDL-061.42 AST sweep reddened. Annotating the same parameter ``path:
        Path`` made ruff report it. ``open()`` has no receiver to infer and is
        reported either way.

        THE CONSEQUENCE IS WHY TWO INSTRUMENTS EXIST. Over ``src/`` the reach is
        broad because ``mypy --strict`` makes annotations mandatory there. Over
        ``tests/`` — which nothing type-checks — it is partial, and the
        receiver-agnostic AST sweep is what actually covers the package. Anyone
        tempted to delete that sweep as redundant should redden this row first.

        If a later ruff widens the rule and this row fails, that is the good
        outcome and the answer is to re-scope the sweep deliberately, not to
        weaken the row.
        """
        unannotated = self._plant(
            "from pathlib import Path\n"
            "\n"
            "\n"
            "def read(p):\n"
            "    return p.read_text()\n"
        )
        annotated = self._plant(
            "from pathlib import Path\n"
            "\n"
            "\n"
            "def read(p: Path) -> str:\n"
            "    return p.read_text()\n"
        )

        assert _plw1514_findings(unannotated) == [], (
            "ruff now reports a read_text() on an inferred-nothing receiver. The "
            "AST sweep's unique reach just shrank — re-scope it on purpose."
        )
        assert len(_plw1514_findings(annotated)) == 1

    def test_the_selection_is_not_inert(self) -> None:
        """The exact warning ruff prints when the rule is selected but asleep.

        Kept beside the planted-site test rather than instead of it: this one
        names the knob that went missing, and the planted site proves the rule
        actually runs. Either alone would have let the other's failure through.
        """
        completed = _run_ruff(str(_SRC_ROOT))

        assert "has no effect because preview is not enabled" not in completed.stderr, (
            "ruff says a selected rule is inert. `[tool.ruff.lint] preview` and "
            "`explicit-preview-rules` travel WITH the PLW1514 selection; "
            "removing either leaves a green lint that checks nothing.\n"
            f"{completed.stderr}"
        )
