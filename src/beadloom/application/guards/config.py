# beadloom:domain=application
# beadloom:feature=flow-guards
"""Guard configuration — the ``guards:`` block of ``.beadloom/flow.yml`` (BDL-061 S1).

.. code-block:: yaml

    guards:
      bead-claimed:
        strictness: { default: warn, epic: block, chore: off }
        options: { }
        exclusions:
          - path: "scripts/**"
            reason: "operational scripts are not bead-scoped"
            until: "BDL-0xx introduces a scripts node"

Four rules are enforced here because each is a way a gate is switched off
without anyone saying so:

* an exclusion carries **both** ``reason`` and ``until`` — an unnamed, undated
  exclusion is permanent by accident;
* a guard name that is not registered is an error, not a no-op, so a typo
  cannot silently disable a gate;
* an unknown strictness value is an error rather than a fallback to something
  looser;
* a key this loader does not read is an error too, at either level
  (:data:`GUARD_BODY_KEYS`, :data:`EXCLUSION_KEYS`) — see
  :func:`_reject_unknown_keys` for what a dropped key costs.

An absent ``guards:`` block is not an error: every registered guard resolves to
its default spec (:data:`DEFAULT_STRICTNESS` = ``warn``, no exclusions), so a
project that upgrades Beadloom gains warnings that name what they did not check
— never a new red build.

There is deliberately no ``on:`` key. Which tool invocations count as an edit is
the harness adapter's vocabulary (Claude Code's ``Edit|Write|NotebookEdit``
matcher, say), and Beadloom had no consumer for an event list — the loader wrote
``GuardSpec.events`` and nothing read it, so the schema promised routing it did
not perform. It returns wired in S3, when composition and adapters are reworked.

The file is shared with the role configurator
(:mod:`beadloom.onboarding.flow_config`, which owns ``tools``/``architecture``/
``stack``). Each side parses only its own block; the path constant is imported
rather than rebuilt so there is one definition of where the file lives.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
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

#: The keys one guard's declaration block may carry — the ones the loader reads.
GUARD_BODY_KEYS: tuple[str, ...] = ("strictness", "exclusions", "options")

#: The keys one exclusion entry may carry, all three of them required.
EXCLUSION_KEYS: tuple[str, ...] = ("path", "reason", "until")


class GuardConfigError(ValueError):
    """A ``guards:`` block that is malformed or names something unknown.

    The message always names the offending guard/field and the allowed set, so
    the fix is mechanical.
    """


@lru_cache(maxsize=256)
def _glob_to_regex(pattern: str) -> re.Pattern[str]:
    """Compile a POSIX-ish glob where ``**`` crosses directories and ``*`` does not.

    ``fnmatch`` is not used: there ``*`` also matches ``/``, so ``src/*.py``
    would silently exclude the whole subtree. An exclusion that covers more than
    it says is exactly the failure this module exists to prevent.

    ``**/`` with a pattern after it is ``(?:.*/)?`` — zero or more WHOLE
    directory segments — and not a bare ``.*`` (F5): unanchored, ``**/app.py``
    also exempted ``src/myapp.py``, which is that same failure by one character.
    A trailing ``**/`` keeps the ``.*`` reading, because it names no file of its
    own and a pattern that quietly stops exempting anything is how an author
    discovers their exclusion moved.

    The tail anchor is ``\\Z`` and not ``$``: Python's ``$`` also matches
    *before* a trailing newline, so ``src/*.py`` covered ``'src/app.py\\n'`` —
    a second lock with the same hole as the one above it (BDL-061.28, m2). It
    was latent only because the resolver stripped the newline first, and that
    strip is gone.

    Cached because the liveness report matches every declared pattern against
    every file in the project; there are a handful of distinct patterns and
    thousands of paths.
    """
    out: list[str] = ["^"]
    i = 0
    while i < len(pattern):
        char = pattern[i]
        if char == "*":
            if pattern.startswith("**", i):
                i += 2
                if pattern.startswith("/", i) and i + 1 < len(pattern):
                    out.append("(?:.*/)?")
                    i += 1
                else:
                    out.append(".*")
                    if pattern.startswith("/", i):
                        i += 1
                continue
            out.append("[^/]*")
        elif char == "?":
            out.append("[^/]")
        else:
            out.append(re.escape(char))
        i += 1
    out.append(r"\Z")
    return re.compile("".join(out))


#: Paths a pattern is probed against to decide whether it is a catch-all.
#:
#: Synthetic on purpose: "is this pattern a catch-all" is a question about the
#: PATTERN, and an answer computed from whichever files happen to exist today
#: would change under an unrelated commit. The set spans the shapes a glob can
#: distinguish — top level vs nested vs deeply nested, dotted vs extensionless,
#: dotfile vs ordinary — so a pattern matching all of them cannot single out a
#: subset of a real tree either.
CATCH_ALL_PROBE_PATHS: tuple[str, ...] = (
    "README.md",
    "Makefile",
    ".gitignore",
    "src/app.py",
    "src/a/b/c/deep.txt",
    "docs/domains/graph/README.md",
)


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

        Either every configured strictness is ``off``, or nothing escapes the
        exclusions. Reported by ``beadloom guard --liveness``.

        The second half is asked of the exclusion **list**, not of one pattern at
        a time: ``*`` and ``*/**`` are each narrow, and together they exempt every
        path there is (F4). It is asked of the matcher rather than of the
        spelling, because comparing the literal string to a list of known
        catch-alls was wrong in both directions (review .3, M1) — it missed
        ``**/**`` and called ``*`` a catch-all though ``*`` does not cross
        directories.

        What this does NOT claim: that no file in *this* project escapes the
        exclusions. ``src/**`` in a project whose code is entirely under ``src/``
        leaves the guard dead and is not reported here, because the answer is
        computed from the patterns alone and an answer computed from today's
        files would flip under an unrelated commit. The project-dependent half —
        does anything that actually exists escape them — is answered by the
        liveness report, which has the tree to look at.
        """
        values = set(self.strictness.values()) or {DEFAULT_STRICTNESS}
        if values == {"off"}:
            return True
        return all(
            any(exclusion.matches(path) for exclusion in self.exclusions)
            for path in CATCH_ALL_PROBE_PATHS
        )


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
    return GuardSpec(name=name, declared=False)


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


def _reject_unknown_keys(
    body: Mapping[object, object], *, where: str, allowed: tuple[str, ...]
) -> None:
    """Refuse a key nobody reads, naming it and the set that would have been read.

    The fourth rule of this module, and the one that was missing (BDL-061.34). A
    key the loader does not read is dropped in silence, and the guard then runs
    on a default the project never declared — which is the same failure as an
    unregistered guard name and an unknown strictness value, both already
    errors here. It is not symmetric: ``exclude:`` for ``exclusions:`` costs
    zero exclusions and the guard OVER-guards, while ``option:`` for
    ``options:`` costs ``working-branch`` its declared ``trunk``. Measured
    through the real binary on a project whose trunk is ``develop``: an edit
    made directly on ``develop`` answered ``PASS ... (trunk is 'main')`` at exit
    ``0``.

    Reported as an error rather than a warning because the one mitigation — the
    verdict names the trunk it compared against — travels on the stream and the
    exit code a hook harness discards, so in the case that matters nobody reads
    it. Nothing green goes red: a ``guards:`` block that only uses keys the
    loader reads is unaffected, and the feature is unreleased, so no published
    project has one at all.
    """
    unknown = sorted(str(key) for key in body if key not in allowed)
    if unknown:
        msg = (
            f"flow.yml: {where} has unknown key(s) {unknown} — "
            f"allowed: {list(allowed)}. A key nothing reads is dropped in "
            "silence, and the guard then runs on a default the project never "
            "declared"
        )
        raise GuardConfigError(msg)


def _build_exclusion(entry: object, *, guard: str) -> GuardExclusion:
    """Validate one exclusion entry — ``path`` + ``reason`` + ``until`` all required."""
    if not isinstance(entry, dict):
        msg = f"flow.yml: guards.{guard}.exclusions entries must be mappings"
        raise GuardConfigError(msg)
    _reject_unknown_keys(
        entry, where=f"guards.{guard} exclusion {entry!r}", allowed=EXCLUSION_KEYS
    )
    missing = [
        field_name
        for field_name in EXCLUSION_KEYS
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


def _build_spec(name: str, body: object) -> GuardSpec:
    """Validate one guard's declaration block."""
    if body is None:
        body = {}
    if not isinstance(body, dict):
        msg = f"flow.yml: guards.{name} must be a mapping"
        raise GuardConfigError(msg)
    _reject_unknown_keys(body, where=f"guards.{name}", allowed=GUARD_BODY_KEYS)
    raw_exclusions = body.get("exclusions") or []
    if not isinstance(raw_exclusions, list):
        msg = f"flow.yml: guards.{name}.exclusions must be a list"
        raise GuardConfigError(msg)
    return GuardSpec(
        name=name,
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
