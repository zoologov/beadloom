# beadloom:domain=application
# beadloom:feature=flow-guards
"""Guard configuration — the ``guards:`` block of ``.beadloom/flow.yml`` (BDL-061 S1).

.. code-block:: yaml

    guards:
      bead-claimed:
        on: [edit]
        strictness: { default: warn, epic: block, chore: off }
        options: { }
        exclusions:
          - path: "scripts/**"
            reason: "operational scripts are not bead-scoped"
            until: "BDL-0xx introduces a scripts node"

Three rules are enforced here because each is a way a gate is switched off
without anyone saying so:

* an exclusion carries **both** ``reason`` and ``until`` — an unnamed, undated
  exclusion is permanent by accident;
* a guard name that is not registered is an error, not a no-op, so a typo
  cannot silently disable a gate;
* an unknown strictness value is an error rather than a fallback to something
  looser.

An absent ``guards:`` block is not an error: every registered guard resolves to
its default spec (:data:`DEFAULT_STRICTNESS` = ``warn``, no exclusions), so a
project that upgrades Beadloom gains warnings that name what they did not check
— never a new red build.

The file is shared with the role configurator
(:mod:`beadloom.onboarding.flow_config`, which owns ``tools``/``architecture``/
``stack``). Each side parses only its own block; the path constant is imported
rather than rebuilt so there is one definition of where the file lives.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import yaml

from beadloom.application.guards.checks import BUILTIN_GUARDS
from beadloom.onboarding.flow_config import FLOW_CONFIG_RELPATH

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

#: Strictness applied when neither the work kind nor ``default`` is configured.
DEFAULT_STRICTNESS = "warn"

#: The strictness values a guard may be configured with.
STRICTNESS_VALUES: tuple[str, ...] = ("off", "warn", "block")

#: Key under which a work kind's fallback strictness is declared.
DEFAULT_KEY = "default"


class GuardConfigError(ValueError):
    """A ``guards:`` block that is malformed or names something unknown.

    The message always names the offending guard/field and the allowed set, so
    the fix is mechanical.
    """


def _glob_to_regex(pattern: str) -> re.Pattern[str]:
    """Compile a POSIX-ish glob where ``**`` crosses directories and ``*`` does not.

    ``fnmatch`` is not used: there ``*`` also matches ``/``, so ``src/*.py``
    would silently exclude the whole subtree. An exclusion that covers more than
    it says is exactly the failure this module exists to prevent.
    """
    out: list[str] = ["^"]
    i = 0
    while i < len(pattern):
        char = pattern[i]
        if char == "*":
            if pattern.startswith("**", i):
                out.append(".*")
                i += 2
                if pattern.startswith("/", i):
                    i += 1
                continue
            out.append("[^/]*")
        elif char == "?":
            out.append("[^/]")
        else:
            out.append(re.escape(char))
        i += 1
    out.append("$")
    return re.compile("".join(out))


@dataclass(frozen=True)
class GuardExclusion:
    """One declared exclusion: a path pattern, why it exists, and when it ends."""

    path: str
    reason: str
    until: str

    def matches(self, relative_path: str) -> bool:
        """True when this exclusion covers *relative_path* (project-relative POSIX)."""
        return bool(_glob_to_regex(self.path).match(relative_path))

    def describe(self) -> str:
        """One-line rendering used as the ``skip`` reason."""
        return f"excluded by {self.path!r}: {self.reason} (until {self.until})"


@dataclass(frozen=True)
class GuardSpec:
    """The effective configuration of one guard."""

    name: str
    events: tuple[str, ...] = ("edit",)
    strictness: Mapping[str, str] = field(default_factory=dict)
    exclusions: tuple[GuardExclusion, ...] = ()
    options: Mapping[str, str] = field(default_factory=dict)
    declared: bool = False

    def strictness_for(self, work_kind: str | None) -> str:
        """Strictness for *work_kind*, falling back to ``default`` then ``warn``."""
        if work_kind and work_kind in self.strictness:
            return self.strictness[work_kind]
        return self.strictness.get(DEFAULT_KEY, DEFAULT_STRICTNESS)

    def exclusion_for(self, relative_path: str | None) -> GuardExclusion | None:
        """The first exclusion covering *relative_path*, if any.

        A caller with no path gets ``None``: an unknown target must not inherit
        someone else's exclusion.
        """
        if relative_path is None:
            return None
        for exclusion in self.exclusions:
            if exclusion.matches(relative_path):
                return exclusion
        return None

    def excluded_everywhere(self) -> bool:
        """True when this guard can never fire as configured.

        Either every configured strictness is ``off``, or an exclusion pattern
        covers every path. Reported by ``beadloom guard --liveness``.
        """
        values = set(self.strictness.values()) or {DEFAULT_STRICTNESS}
        if values == {"off"}:
            return True
        return any(exclusion.path in ("**", "*", "**/*") for exclusion in self.exclusions)


@dataclass(frozen=True)
class GuardsConfig:
    """Every guard's effective spec for one project."""

    specs: Mapping[str, GuardSpec] = field(default_factory=dict)

    def spec_for(self, name: str) -> GuardSpec:
        """The declared spec for *name*, or the shipped default spec."""
        if name in self.specs:
            return self.specs[name]
        return _default_spec(name)

    def declared_names(self) -> tuple[str, ...]:
        """Guard names explicitly declared in ``flow.yml``, sorted."""
        return tuple(sorted(self.specs))


def _default_spec(name: str) -> GuardSpec:
    """The spec a registered-but-undeclared guard runs under (warn, no exclusions)."""
    guard = BUILTIN_GUARDS.get(name)
    events = guard.default_events if guard else ("edit",)
    return GuardSpec(name=name, events=events, declared=False)


def _as_str_map(value: object, *, guard: str, key: str) -> dict[str, str]:
    """Coerce a YAML mapping of scalars into ``str -> str`` (or raise)."""
    if value is None:
        return {}
    if not isinstance(value, dict):
        msg = f"flow.yml: guards.{guard}.{key} must be a mapping"
        raise GuardConfigError(msg)
    out: dict[str, str] = {}
    for raw_key, raw_val in value.items():
        # YAML turns a bare `off` into False; the user wrote a strictness word.
        # Restricted to real booleans on purpose: a lookup keyed by the value
        # crashed on an unhashable one (a list read as exit 1 — the *warn* code —
        # so a malformed file was indistinguishable from a warning), and it also
        # coerced the integers 0/1, silently switching a guard `off`.
        text: object = raw_val
        if isinstance(raw_val, bool):
            text = "on" if raw_val else "off"
        if not isinstance(raw_key, str) or not isinstance(text, str):
            msg = f"flow.yml: guards.{guard}.{key} must map strings to strings"
            raise GuardConfigError(msg)
        out[raw_key] = text
    return out


def _build_strictness(value: object, *, guard: str) -> dict[str, str]:
    """Validate the per-work-kind strictness mapping."""
    strictness = _as_str_map(value, guard=guard, key="strictness")
    unknown = sorted({v for v in strictness.values() if v not in STRICTNESS_VALUES})
    if unknown:
        msg = (
            f"flow.yml: guards.{guard}.strictness has unknown value(s) {unknown} — "
            f"allowed: {list(STRICTNESS_VALUES)}"
        )
        raise GuardConfigError(msg)
    return strictness


def _build_exclusion(entry: object, *, guard: str) -> GuardExclusion:
    """Validate one exclusion entry — ``path`` + ``reason`` + ``until`` all required."""
    if not isinstance(entry, dict):
        msg = f"flow.yml: guards.{guard}.exclusions entries must be mappings"
        raise GuardConfigError(msg)
    missing = [
        field_name
        for field_name in ("path", "reason", "until")
        if not str(entry.get(field_name) or "").strip()
    ]
    if missing:
        msg = (
            f"flow.yml: guards.{guard} exclusion {entry!r} is missing {missing} — "
            "every exclusion must say which paths it covers, WHY it exists, and "
            "UNTIL when (an unnamed, undated exclusion disables the guard "
            "permanently by accident)"
        )
        raise GuardConfigError(msg)
    return GuardExclusion(
        path=str(entry["path"]).strip(),
        reason=str(entry["reason"]).strip(),
        until=str(entry["until"]).strip(),
    )


def _build_events(value: object, *, guard: str) -> tuple[str, ...]:
    """Validate the ``on:`` event list, defaulting to the guard's own events."""
    if value is None:
        return _default_spec(guard).events
    if isinstance(value, str):
        return (value,)
    if isinstance(value, list) and all(isinstance(v, str) for v in value):
        return tuple(value)
    msg = f"flow.yml: guards.{guard}.on must be a string or a list of strings"
    raise GuardConfigError(msg)


def _build_spec(name: str, body: object) -> GuardSpec:
    """Validate one guard's declaration block."""
    if body is None:
        body = {}
    if not isinstance(body, dict):
        msg = f"flow.yml: guards.{name} must be a mapping"
        raise GuardConfigError(msg)
    raw_exclusions = body.get("exclusions") or []
    if not isinstance(raw_exclusions, list):
        msg = f"flow.yml: guards.{name}.exclusions must be a list"
        raise GuardConfigError(msg)
    return GuardSpec(
        name=name,
        events=_build_events(body.get("on"), guard=name),
        strictness=_build_strictness(body.get("strictness"), guard=name),
        exclusions=tuple(_build_exclusion(e, guard=name) for e in raw_exclusions),
        options=_as_str_map(body.get("options"), guard=name, key="options"),
        declared=True,
    )


def build_guards_config(data: object) -> GuardsConfig:
    """Validate a parsed ``flow.yml`` mapping into a :class:`GuardsConfig`."""
    if data is None:
        return GuardsConfig()
    if not isinstance(data, dict):
        msg = "flow.yml: top-level content must be a mapping"
        raise GuardConfigError(msg)
    raw = data.get("guards")
    if raw is None:
        return GuardsConfig()
    if not isinstance(raw, dict):
        msg = "flow.yml: 'guards' must be a mapping of guard name -> settings"
        raise GuardConfigError(msg)
    unknown = sorted(name for name in raw if name not in BUILTIN_GUARDS)
    if unknown:
        msg = (
            f"flow.yml: unknown guard(s) {unknown} — allowed: {sorted(BUILTIN_GUARDS)}. "
            "A guard name with no implementation is a silently dead gate, so it is "
            "rejected rather than ignored"
        )
        raise GuardConfigError(msg)
    return GuardsConfig(
        specs={name: _build_spec(name, body) for name, body in raw.items()}
    )


def load_guards_config(project_root: Path) -> GuardsConfig:
    """Load the ``guards:`` block of ``<project_root>/.beadloom/flow.yml``.

    An absent file yields the shipped defaults (every guard ``warn``); a present
    but malformed one raises :class:`GuardConfigError`.
    """
    path = project_root / FLOW_CONFIG_RELPATH
    if not path.is_file():
        return GuardsConfig()
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        msg = f"flow.yml: invalid YAML — {exc}"
        raise GuardConfigError(msg) from exc
    return build_guards_config(data)
