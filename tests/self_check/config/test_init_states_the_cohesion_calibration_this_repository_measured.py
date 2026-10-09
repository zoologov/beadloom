"""``init``'s FSD cohesion limits and the measurement they cite agree with this repository.

BDL-080 S2d (``beadloom-af99.10``), from the S2 review (``beadloom-cp4u``, nitpick 4).
``init`` writes the per-layer cohesion signal for a Feature-Sliced frontend and cites
the measurement it was calibrated on: Beadloom's own portal, whose largest widget's
owned symbols decided the widget limit. That measurement is written down twice, in
``rules_gen.py`` (shipped to adopters) and in this repository's ``rules.yml`` (beside
the rules it calibrated), and the two said 66 and 65. One measurement has one number.

What this checks is agreement, not truth: whether 65 is still the largest widget is a
measurement on the index, and ``rules.yml`` carries the date and commit it was taken at.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from beadloom.onboarding.scanner import rules_gen
from beadloom.onboarding.scanner.rules_gen import FSD_COHESION_LIMITS

_ROOT = Path(__file__).resolve().parents[3]
_RULES = _ROOT / ".beadloom" / "_graph" / "rules.yml"


def _prose(text: str) -> str:
    """The text with comment markers dropped and whitespace folded, so a wrap is a space."""
    lines = (line.strip().removeprefix("#").strip() for line in text.splitlines())
    return " ".join(line for line in lines if line)


def _numbers(pattern: str, text: str) -> set[int]:
    return {int(found) for found in re.findall(pattern, _prose(text))}


def test_init_and_this_repository_cite_one_largest_widget() -> None:
    shipped = _numbers(r"largest widget owns (\d+)", Path(rules_gen.__file__).read_text("utf-8"))
    measured = _numbers(
        r"widgets own at most (\d+) \(site-graph-viewer", _RULES.read_text("utf-8")
    )

    assert len(shipped) == 1, shipped
    assert len(measured) == 1, measured
    assert shipped == measured


def test_init_writes_the_limits_this_repository_holds_its_own_site_to() -> None:
    rules = yaml.safe_load(_RULES.read_text("utf-8"))["rules"]
    held = {
        rule["name"].removeprefix("site-fsd-cohesion-"): rule["check"]["max_symbols"]
        for rule in rules
        if rule["name"].startswith("site-fsd-cohesion-")
    }

    assert held == FSD_COHESION_LIMITS
