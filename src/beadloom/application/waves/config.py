"""Read the ``waves:`` block of ``.beadloom/flow.yml`` — the declared overrides.

An override is a human outranking a computed decision, so it is held to the same
shape every other stand-down in this codebase is held to: it names the beads, the
direction, WHY, and what retires it. One with a missing field is a configuration
error rather than a lenient default, for the reason the guard exclusions already
state — an unnamed, undated stand-down is permanent by accident.

    waves:
      overrides:
      - beads: [proj-1, proj-2]
        decision: parallel
        reason: "the two touch one vocabulary module and nothing else"
        until: "2026-09-01"

An unknown key is rejected rather than ignored: a key nothing reads is dropped in
silence, and the override then runs on a default the project never declared.
"""

# beadloom:feature=wave-plan

from __future__ import annotations

from typing import TYPE_CHECKING

import yaml

from beadloom.application.waves.models import DECISIONS, WaveOverride

if TYPE_CHECKING:
    from pathlib import Path

#: The keys one override entry may carry. Every one of them is required.
OVERRIDE_KEYS: tuple[str, ...] = ("beads", "decision", "reason", "until")

#: The keys the ``waves:`` block itself may carry.
WAVES_KEYS: tuple[str, ...] = ("overrides",)

#: An override about fewer than two beads says nothing about concurrency.
_MIN_BEADS = 2


class WaveConfigError(ValueError):
    """A ``waves:`` block that cannot be used as declared."""


def _reject_unknown_keys(body: dict[str, object], *, where: str, allowed: tuple[str, ...]) -> None:
    unknown = sorted(str(key) for key in body if key not in allowed)
    if unknown:
        msg = (
            f"flow.yml: {where} has unknown key(s) {unknown} — "
            f"allowed: {list(allowed)}. A key nothing reads is dropped in "
            "silence, and the override then runs on a default the project "
            "never declared"
        )
        raise WaveConfigError(msg)


def _build_override(entry: object) -> WaveOverride:
    """Validate one override entry — every key required, decision from the pair."""
    if not isinstance(entry, dict):
        msg = "flow.yml: waves.overrides entries must be mappings"
        raise WaveConfigError(msg)
    _reject_unknown_keys(entry, where=f"waves override {entry!r}", allowed=OVERRIDE_KEYS)
    missing = [key for key in OVERRIDE_KEYS if not entry.get(key)]
    if missing:
        msg = (
            f"flow.yml: waves override {entry!r} is missing {missing} — an "
            "override must say which beads it moves, in WHICH direction, WHY, "
            "and UNTIL when (an unnamed, undated override outranks the graph "
            "permanently by accident)"
        )
        raise WaveConfigError(msg)
    raw_beads = entry["beads"]
    if not isinstance(raw_beads, list) or not all(isinstance(b, str) for b in raw_beads):
        msg = f"flow.yml: waves override {entry!r}: 'beads' must be a list of bead ids"
        raise WaveConfigError(msg)
    beads = tuple(str(bead).strip() for bead in raw_beads)
    if len({*beads}) < _MIN_BEADS:
        msg = (
            f"flow.yml: waves override {entry!r} names fewer than two distinct "
            "beads — an override about one bead states nothing about concurrency"
        )
        raise WaveConfigError(msg)
    decision = str(entry["decision"]).strip()
    if decision not in DECISIONS:
        msg = (
            f"flow.yml: waves override {entry!r}: unknown decision "
            f"{decision!r} — allowed: {list(DECISIONS)}"
        )
        raise WaveConfigError(msg)
    return WaveOverride(
        beads=beads,
        decision=decision,
        reason=str(entry["reason"]).strip(),
        until=str(entry["until"]).strip(),
    )


def load_overrides(project_root: Path) -> tuple[WaveOverride, ...]:
    """Every override declared in *project_root*'s ``flow.yml`` (possibly none).

    A project with no ``flow.yml``, or one with no ``waves:`` block, declares no
    override — which is a valid state and not a finding. A block that is present
    and malformed is an error: it was written to be read.
    """
    path = project_root / ".beadloom" / "flow.yml"
    if not path.exists():
        return ()
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        # All three reach the caller as one fact — *the declaration could not be
        # read* — and the caller already has the right response to it: exit 2,
        # "no wave shape could be decided". Catching only the YAML error would
        # let a flow.yml written in some other codec out as a bare traceback,
        # which is the narrow-handler shape this repository judges site by site.
        msg = f"flow.yml: could not be read as declared ({type(exc).__name__}: {exc})"
        raise WaveConfigError(msg) from exc
    if not isinstance(raw, dict):
        msg = "flow.yml: top level must be a mapping"
        raise WaveConfigError(msg)
    body = raw.get("waves")
    if body is None:
        return ()
    if not isinstance(body, dict):
        msg = "flow.yml: 'waves' must be a mapping"
        raise WaveConfigError(msg)
    _reject_unknown_keys(body, where="waves", allowed=WAVES_KEYS)
    entries = body.get("overrides") or []
    if not isinstance(entries, list):
        msg = "flow.yml: waves.overrides must be a list"
        raise WaveConfigError(msg)
    return tuple(_build_override(entry) for entry in entries)
