# beadloom:domain=onboarding
# beadloom:feature=flow-suppression
"""A declared suppression of a shipped core rule — append-only, named, dated.

Overlays are append-only: nothing in the project layer can delete core text.
That is deliberate. Silent override is a way to switch the gate off without
saying so, and a rule that vanished from a composed file leaves no trace that
anyone decided it should.

So a project that genuinely must stand down a core rule *declares* it in
``.beadloom/flow.yml``::

    overlays:
      suppress:
        - rule: "Anti-patterns / Shell"
          reason: "the team runs on Windows; the -f idiom does not apply"
          until: "BDL-0xx ships a windows stack overlay"

Both ``reason`` and ``until`` are mandatory — the same bar
``guards.<name>.exclusions`` holds (BDL-061 S1), for the same reason: an
unnamed, undated suppression is permanent by accident. ``until`` may answer
with a date or with an event; which it is, is decided by
:func:`~beadloom.graph.rules.exit_condition_deadline`, the one function both
surfaces use, because restating it here is how the two would come to mean
different things.

The suppression is then **reported twice**: appended to the composed artifact
as a visible notice (so the reader who is about to follow the core rule is told
it was stood down, by whom and until when), and surfaced by ``config-check``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from beadloom.graph.rules import exit_condition_deadline

#: Keys a suppression entry may carry; all three are required.
SUPPRESSION_KEYS: tuple[str, ...] = ("rule", "reason", "until")

_NOTICE_HEADING = "## Project rule suppressions (declared in `.beadloom/flow.yml`)"


class FlowSuppressionError(ValueError):
    """A suppression entry that is malformed or missing its reason / exit condition."""


@dataclass(frozen=True)
class FlowSuppression:
    """One declared suppression: which core rule, why, and what retires it."""

    rule: str
    reason: str
    until: str

    def expired(self, today: date | None = None) -> bool:
        """True when ``until`` names a day and that day is behind us.

        An event-shaped exit condition is never expired: unparseable is not a
        verdict either way. The deadline names the LAST day the suppression
        covers, so ``until`` equal to today still holds.
        """
        deadline = exit_condition_deadline(self.until)
        return deadline is not None and deadline < (today or date.today())

    def describe(self) -> str:
        """One-line rendering: which rule, why, and what retires it.

        It says nothing about *today*. This string is COMPOSED BYTES, and the
        composition must be a function of its inputs — which is the property
        :mod:`beadloom.onboarding.composer` asserts in its own docstring and
        the whole licence for ``config-check`` to compare against a composition
        rather than against stored bytes. Rendering the expiry verdict here made
        an untouched repository go from 0 findings to 9 errors overnight, under a
        reason that named three causes which had not occurred (BDL-061 `.57`).

        Expiry is not lost, it is MOVED: it is computed at check time by
        :func:`expired_suppressions` and reported as a finding, which is what
        CONTEXT promised in the first place — a suppression carries a named
        reason, an exit condition, and is itself reported.

        :class:`~beadloom.application.guards.config.GuardExclusion` keeps the
        verdict in its own ``describe()`` on purpose: that string is a runtime
        skip reason read by the person whose edit was just let through, not a
        byte anything is later diffed against.
        """
        return f"{self.rule}: {self.reason} (until {self.until})"


def build_suppression(entry: object) -> FlowSuppression:
    """Validate one ``overlays.suppress`` entry into a :class:`FlowSuppression`."""
    if not isinstance(entry, dict):
        msg = "flow.yml: overlays.suppress entries must be mappings"
        raise FlowSuppressionError(msg)
    unknown = sorted(str(k) for k in entry if k not in SUPPRESSION_KEYS)
    if unknown:
        msg = (
            f"flow.yml: overlays.suppress entry has unknown key(s) {unknown} — "
            f"allowed: {list(SUPPRESSION_KEYS)}"
        )
        raise FlowSuppressionError(msg)
    missing = [k for k in SUPPRESSION_KEYS if not str(entry.get(k) or "").strip()]
    if missing:
        msg = (
            f"flow.yml: overlays.suppress entry {entry!r} is missing {missing} — "
            "suppressing a shipped core rule must say WHICH rule, WHY it does "
            "not apply here, and UNTIL when (an unnamed, undated suppression "
            "disables the rule permanently by accident)"
        )
        raise FlowSuppressionError(msg)
    return FlowSuppression(
        rule=str(entry["rule"]).strip(),
        reason=str(entry["reason"]).strip(),
        until=str(entry["until"]).strip(),
    )


def build_suppressions(value: object) -> tuple[FlowSuppression, ...]:
    """Validate the whole ``overlays.suppress`` list (absent → empty)."""
    if value is None:
        return ()
    if not isinstance(value, list):
        msg = "flow.yml: overlays.suppress must be a list of mappings"
        raise FlowSuppressionError(msg)
    return tuple(build_suppression(entry) for entry in value)


def render_suppression_notice(suppressions: tuple[FlowSuppression, ...]) -> str:
    """The append-only notice added to every composed artifact.

    Empty when nothing is suppressed, so a project that suppresses nothing gets
    byte-identical output to before this feature existed.
    """
    if not suppressions:
        return ""
    lines = [
        "",
        "---",
        "",
        _NOTICE_HEADING,
        "",
        "The core rules below are stood down **in this project only**. The core "
        "text above is unchanged — a suppression is a declaration, never a "
        "deletion — and each one names its reason and its exit condition.",
        "",
    ]
    lines.extend(f"- {s.describe()}" for s in suppressions)
    lines.append("")
    return "\n".join(lines)


#: A Markdown ATX heading — the shape a *rule* takes in these documents. A
#: suppression names a rule by its heading path ("Anti-patterns / Shell"), so
#: headings are what a declaration is matched against; body prose is not, or
#: every entry would own something by coincidence.
_HEADING = re.compile(r"^#{1,6}[ \t]+(.+?)[ \t]*$", re.MULTILINE)

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def _normalise(text: str) -> str:
    """Lowercase, punctuation-free form, so ``Anti-patterns`` matches ``anti patterns``."""
    return _NON_ALNUM.sub(" ", text.lower()).strip()


def composed_headings(texts: tuple[str, ...]) -> tuple[str, ...]:
    """Every heading in the composed artifacts, normalised for matching.

    The corpus is the whole composition an adopter actually gets — CLAUDE.md,
    the slash commands and the role protocols — because a core rule may live in
    any of them and reporting "this suppresses nothing" from a partial corpus
    would be the false positive that teaches people to ignore the finding.
    """
    return tuple(
        _normalise(match.group(1))
        for text in texts
        for match in _HEADING.finditer(text)
    )


def suppresses_nothing(
    suppression: FlowSuppression, headings: tuple[str, ...]
) -> bool:
    """True when no heading in the composed corpus answers to this rule name.

    ``rule`` is read as a heading PATH: every ``/``-separated segment must be
    named by some heading. ``Anti-patterns / Shell`` is matched by
    ``### Anti-patterns (shell)``; ``Section 42 / Tap dance`` is matched by
    nothing, and a declaration that owns nothing is named rather than counted as
    checked (BDL-061 `.50`).
    """
    segments = [seg for seg in (_normalise(s) for s in suppression.rule.split("/")) if seg]
    if not segments:
        return True
    return not all(any(seg in heading for heading in headings) for seg in segments)


def expired_suppressions(
    suppressions: tuple[FlowSuppression, ...], *, today: date | None = None
) -> tuple[FlowSuppression, ...]:
    """Those whose exit condition named a day and that day is behind us.

    Computed HERE, at check time, and never rendered into the composed bytes —
    that separation is the whole of BDL-061 `.57`.
    """
    return tuple(s for s in suppressions if s.expired(today))
