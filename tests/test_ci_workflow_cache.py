"""S5 (BDL-052) — assert the ai-techwriter CI job's cached-setup wiring.

The job's LOGIC / TRIGGER / loop-guard / AI_TW_PAT must stay unchanged; S5 only
ADDS caching. These structural checks parse ``.github/workflows/ci.yml`` and pin:

* ``setup-uv`` has its dependency cache enabled;
* the index DB is cached, keyed on a ``hashFiles`` of the graph + src + docs, so
  any of those changing rotates the key (stale → miss → reindex);
* the reindex step is gated on a cache MISS;
* the unchanged invariants survive: ``fetch-depth: 0``, the loop-guard, and the
  ``AI_TW_PAT`` checkout token.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml

_CI = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"


def _ai_techwriter_steps() -> list[dict[str, Any]]:
    data = cast("dict[str, Any]", yaml.safe_load(_CI.read_text(encoding="utf-8")))
    job = data["jobs"]["ai-techwriter"]
    return cast("list[dict[str, Any]]", job["steps"])


def _step(name_contains: str) -> dict[str, Any]:
    for step in _ai_techwriter_steps():
        haystack = f"{step.get('name', '')} {step.get('uses', '')}"
        if name_contains in haystack:
            return step
    msg = f"no ai-techwriter step matching {name_contains!r}"
    raise AssertionError(msg)


def test_setup_uv_cache_enabled() -> None:
    step = _step("astral-sh/setup-uv")
    assert step.get("with", {}).get("enable-cache") is True


def test_index_cache_keyed_on_graph_src_docs() -> None:
    step = _step("Cache the Beadloom index")
    assert step["uses"].startswith("actions/cache@")
    with_ = step["with"]
    assert with_["path"] == ".beadloom/beadloom.db"
    key = with_["key"]
    # The key is a hashFiles over exactly the three index inputs, so changing any
    # of graph/src/docs rotates the key -> a stale cache misses (full reindex).
    for glob in (".beadloom/_graph/**", "src/**", "docs/**"):
        assert glob in key
    assert "hashFiles(" in key


def test_reindex_runs_only_on_cache_miss() -> None:
    step = _step("Beadloom reindex")
    assert "index-cache.outputs.cache-hit != 'true'" in step["if"]


def test_unchanged_invariants_preserved() -> None:
    checkout = _step("actions/checkout")
    assert checkout["with"]["fetch-depth"] == 0
    assert "AI_TW_PAT" in checkout["with"]["token"]
    # The loop-guard step is still present and unchanged in intent.
    guard = _step("Loop-guard")
    assert "[skip ai-techwriter]" in guard["run"]
