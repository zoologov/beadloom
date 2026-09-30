# beadloom:domain=application
# beadloom:feature=site-generation
"""Dashboard AI tech-writer activity — honest run-record store rollup (G9).

Reads the append-only run-record store the CI harness emits and produces the
per-run + cumulative docs-refreshed / token spend series (token counts are
FACTS from the model API; the $ figure is a clearly-labeled estimate).
Absent/empty/corrupt store degrades to "no data", never an error.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

# The append-only run-record store the CI harness emits (one record per run):
# ``{ts, platform, docs_refreshed[], input_tokens, output_tokens, model, gate,
# pr_url}``. We read it independently (the harness lives in ``tools/`` and is
# not importable from the ``application`` layer) — absent/empty/corrupt all
# degrade to "no data" (never an error).
_AI_RUNS_FILENAME = "ai_techwriter_runs.json"

# Blended $/1M-token rate used ONLY to turn the FACT (token counts from the
# model API) into a clearly-labeled ESTIMATE. Tiered/changing pricing makes any
# dollar figure approximate, so the dashboard never presents this as a hard
# cost — see ``cost_estimate.is_estimate`` / ``cost_estimate.label``.
_USD_PER_1M_TOKENS = 0.40


@dataclass(frozen=True)
class _AiRun:
    """One normalized run-record (typed, so cumulative math stays type-safe)."""

    ts: str
    platform: str
    gate: str
    docs_refreshed: int
    input_tokens: int
    output_tokens: int


def _coerce_int(value: object) -> int:
    """Coerce a JSON-loaded value to a non-negative int (0 on anything else)."""
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return max(0, int(value))
    return 0


def _read_ai_runs(project_root: Path) -> list[dict[str, object]]:
    """Read the run-record store; absent/empty/corrupt -> ``[]`` (no data)."""
    store = project_root / ".beadloom" / _AI_RUNS_FILENAME
    if not store.is_file():
        return []
    try:
        payload = json.loads(store.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        logger.warning("Could not read AI tech-writer run store %s", store)
        return []
    if not isinstance(payload, list):
        return []
    return [r for r in payload if isinstance(r, dict)]


def _ai_run_row(raw: dict[str, object]) -> _AiRun | None:
    """Normalize one stored record; skip rows without a usable ``ts``."""
    ts = raw.get("ts")
    if not isinstance(ts, str) or not ts:
        return None
    refreshed = raw.get("docs_refreshed")
    docs_count = len(refreshed) if isinstance(refreshed, list) else 0
    return _AiRun(
        ts=ts,
        platform=str(raw.get("platform", "")),
        gate=str(raw.get("gate", "")),
        docs_refreshed=docs_count,
        input_tokens=_coerce_int(raw.get("input_tokens")),
        output_tokens=_coerce_int(raw.get("output_tokens")),
    )


def _ai_cost_estimate(input_tokens: int, output_tokens: int) -> dict[str, object]:
    """A clearly-labeled $ ESTIMATE (tokens are fact; $ is approximate)."""
    total = input_tokens + output_tokens
    usd = round(total / 1_000_000 * _USD_PER_1M_TOKENS, 4)
    return {
        "usd": usd,
        "rate_usd_per_1m": _USD_PER_1M_TOKENS,
        "is_estimate": True,
        "label": f"est. @ ${_USD_PER_1M_TOKENS}/1M tokens",
    }


def _ai_techwriter(project_root: Path) -> dict[str, object]:
    """Honest AI tech-writer activity from the run-record store (G9).

    Returns per-run + cumulative docs-refreshed and input/output token spend
    (sorted by ts; ONLY real recorded runs — no interpolation, sparse-at-first
    is correct, mirroring ``trends``). Token counts are FACTS from the record;
    the $ figure is a clearly-labeled estimate. Absent/empty/corrupt store ->
    an empty (but present) section.
    """
    rows = [row for raw in _read_ai_runs(project_root) if (row := _ai_run_row(raw))]
    rows.sort(key=lambda r: r.ts)

    cum_docs = cum_in = cum_out = 0
    runs: list[dict[str, object]] = []
    for row in rows:
        cum_docs += row.docs_refreshed
        cum_in += row.input_tokens
        cum_out += row.output_tokens
        runs.append(
            {
                "ts": row.ts,
                "platform": row.platform,
                "gate": row.gate,
                "docs_refreshed": row.docs_refreshed,
                "input_tokens": row.input_tokens,
                "output_tokens": row.output_tokens,
                "cumulative_docs": cum_docs,
                "cumulative_input_tokens": cum_in,
                "cumulative_output_tokens": cum_out,
            }
        )

    return {
        "runs": runs,
        "totals": {
            "runs": len(runs),
            "docs_refreshed": cum_docs,
            "input_tokens": cum_in,
            "output_tokens": cum_out,
        },
        "cost_estimate": _ai_cost_estimate(cum_in, cum_out),
    }
