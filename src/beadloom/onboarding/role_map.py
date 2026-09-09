# beadloom:domain=onboarding
# beadloom:feature=role-map
"""A role this flow composes, checked against the document that enumerates roles.

**The class this closes** (BDL-UX #252): *a role that exists does not reach the
document that lists roles*. ``Explore`` shipped in BDL-068 S1 as a composed
role, was invoked by ``/coordinator`` and ``/task-init``, and was named zero
times in ``CLAUDE.md`` -- the file that calls itself the entry point, whose
section 0.0 draws the role map and whose section 4 is the Agent Roles table.
Both listed four roles while five were composed, so an agent reading the entry
point as that document instructs learned that the fifth did not exist.

**It is the third direction of the graph** :mod:`~beadloom.onboarding.role_duties`
checks two directions of. #228 was "a duty declared for a role does not reach
that role's core", and that module built the edge. This edge was never built
because nobody had added a role since the map was written: ``Explore`` is the
first new role in this flow's life and exposed the gap by being the first thing
that could.

**The population is derived, never listed.** The roles come from
:data:`~beadloom.onboarding.role_composer.ROLE_NAMES`, which
:func:`~beadloom.onboarding.role_composer.roles_in` derives from the shipped
CORE fragments over a shape -- a fragment is a role when its front matter names
its own file. ``templates/roles/core/`` also holds ``_landing``, ``_rooms``,
``_tracker`` and ``_writing`` and their localisations, and a directory listing
would read all eight as roles.

**A name is read as a role only inside a construct that designates one.** A bare
word search would read ``test`` in "Committing with failing tests" and ``review``
in "0 required reviews" as roles, which is the keyword-proximity class this
project has already filed three times (BDL-UX #190, #205, #209). Two kinds of
construct are read, and they carry different weight because they were written
with different intent:

* a **designation** -- ``subagent_type: <names>``, ``agents/<name>.md``,
  ``agents/{<names>}.md`` -- claims that each name inside it IS a role. Somebody
  wrote it on purpose, so a name it carries that no core fragment backs is an
  ``error``.
* an **inferred roster** -- a run of names joined by ``·``, or a run of
  backticked names joined by ``,`` or ``|`` -- is recognised as a roster only
  when it already names two of the composed roles. It is a guess about English
  punctuation, so it can only ever produce a ``warn``, and the names in it that
  are NOT composed roles are not reported at all. An adopter writing
  ``we deploy to `dev`, `test``` about environments must not have a release turn
  their green project red.

**What this does not judge, and says so on every run.**
:attr:`RoleMapReport.not_judged` names every line that mentions two or more
roles in a shape no construct reads -- the wave order ``dev -> test -> review ->
tech-writer``, a parenthesised list, a run of slash-prefixed names. Some of
those SHOULD be complete and some should not, and this derivation cannot tell
which. Listing them is what stops a clean verdict being read as a claim about
the whole document.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from beadloom.onboarding.composer import (
    CLAUDE_ARTIFACT_NAME,
    compose,
    templates_dir,
)
from beadloom.onboarding.flow_config import resolve_flow_config
from beadloom.onboarding.role_composer import ROLE_NAMES

if TYPE_CHECKING:
    from collections.abc import Iterator

    from beadloom.onboarding.composer import LayerFragment
    from beadloom.onboarding.flow_config import FlowConfig

__all__ = [
    "RoleMapFinding",
    "RoleMapReport",
    "RoleReference",
    "UnjudgedLine",
    "role_map_report",
]

#: A role name as every reader of this flow spells one: lowercase, hyphenated.
#: The population is derived; this only says what a candidate token looks like.
_NAME = r"[a-z][a-z0-9-]*"

#: ``subagent_type: dev``, ``subagent_type="dev"|"test"``, ``subagent_type: a|b``.
#: Only ``|`` joins the run: a comma would swallow ``, run_in_background=True``
#: and report ``run`` as a role the flow does not ship.
_SUBAGENT_RE = re.compile(
    rf"subagent_type\s*[:=]\s*(?P<list>[\"']?{_NAME}[\"']?"
    rf"(?:\s*\|\s*[\"']?{_NAME}[\"']?)*)"
)

#: ``.claude/agents/{dev,test,review}.md`` -- one brace expansion, many roles.
_AGENTS_BRACE_RE = re.compile(rf"agents/\{{(?P<list>{_NAME}(?:\s*,\s*{_NAME})*)\}}")

#: ``agents/dev.md`` -- the path to one role's protocol file. A placeholder such
#: as ``agents/<role>.md`` does not match, because ``<`` is not a name character.
_AGENTS_PATH_RE = re.compile(rf"agents/(?P<name>{_NAME})\.md")

#: ``dev · test · review · tech-writer`` -- the roster shape section 0.0's map
#: uses. Inferred, so it is only a roster when it already names two roles.
_DOT_ROSTER_RE = re.compile(rf"`?{_NAME}`?(?:\s*·\s*`?{_NAME}`?)+")

#: ```dev`, `test`, `review``` and ```dev` | `test``` -- the roster shape the
#: header line and the closing pointer use. Backticks are required: without them
#: ``Types: feat, fix, refactor, docs, test, chore`` reads as a roster.
_TICK_ROSTER_RE = re.compile(rf"`{_NAME}`(?:\s*[,|]\s*`{_NAME}`)+")

_NAME_RE = re.compile(_NAME)

#: The artifact this check reads. Named once because three findings quote it.
_MAP_ARTIFACT = f"{CLAUDE_ARTIFACT_NAME}.md"


@dataclass(frozen=True)
class RoleReference:
    """One construct in the map that names roles, and where to open it.

    ``designated`` separates the two kinds: a designation claims each name is a
    role, an inferred roster only guesses that a punctuated run is one.
    """

    names: tuple[str, ...]
    source: str
    text: str
    designated: bool


@dataclass(frozen=True)
class RoleMapFinding:
    """One incoherence between the roles composed and the roles enumerated.

    ``kind`` is one of ``unmapped`` (a composed role no construct in the map
    names), ``partial`` (a composed role omitted from a roster that names two
    other composed roles) and ``unbacked`` (a name a designation claims is a
    role that no CORE fragment ships). ``sites`` are the places a reader opens;
    ``severity`` is ``error`` for a designation and ``warn`` for an inferred
    roster, because the second is this derivation's guess about punctuation.
    """

    kind: str
    role: str
    sites: tuple[str, ...]
    severity: str
    why: str
    remediation: str


@dataclass(frozen=True)
class UnjudgedLine:
    """A line that mentions several roles in a shape no construct reads.

    Reported on every run, clean or not. Some of these should enumerate every
    role and some should not -- a wave order names four roles and `Explore` is
    not a wave -- and this derivation cannot tell them apart. Naming them is
    what keeps a clean verdict from reading as a claim about the whole document.
    """

    source: str
    roles: tuple[str, ...]
    text: str
    why: str


@dataclass(frozen=True)
class RoleMapReport:
    """What this flow composes, what its map enumerates, and what was not read."""

    roles: tuple[str, ...]
    references: tuple[RoleReference, ...]
    rosters: tuple[RoleReference, ...]
    findings: tuple[RoleMapFinding, ...]
    not_judged: tuple[UnjudgedLine, ...]
    inspected: tuple[str, ...]


def _fragment_label(source: str, project_root: Path) -> str:
    """The path a reader opens, relative to whichever root owns the fragment."""
    path = Path(source)
    if not path.is_absolute():
        return str(path)
    for root in (project_root, templates_dir().parent):
        try:
            return str(path.relative_to(root))
        except ValueError:
            continue
    return str(path)


def _names(text: str) -> tuple[str, ...]:
    """Every candidate role name in a construct's captured run, in order."""
    seen: list[str] = []
    for match in _NAME_RE.finditer(text):
        if match.group() not in seen:
            seen.append(match.group())
    return tuple(seen)


def _designations(line: str) -> Iterator[tuple[tuple[str, ...], str]]:
    """Every construct on one line that claims its names are roles."""
    for match in _SUBAGENT_RE.finditer(line):
        yield _names(match.group("list")), match.group()
    for match in _AGENTS_BRACE_RE.finditer(line):
        yield _names(match.group("list")), match.group()
    for match in _AGENTS_PATH_RE.finditer(line):
        yield (match.group("name"),), match.group()


def _inferred_rosters(line: str, roles: frozenset[str]) -> Iterator[tuple[tuple[str, ...], str]]:
    """Punctuated runs that name two composed roles, hence read as rosters.

    The two-role threshold is what makes the shape safe to infer: a run of
    backticked words is ordinary markdown, and only one that already enumerates
    part of this flow's role population is plausibly enumerating all of it.
    """
    for pattern in (_DOT_ROSTER_RE, _TICK_ROSTER_RE):
        for match in pattern.finditer(line):
            names = _names(match.group())
            if len(roles.intersection(names)) >= 2:
                yield names, match.group()


def _references(
    fragments: tuple[LayerFragment, ...], project_root: Path, roles: frozenset[str]
) -> tuple[list[RoleReference], list[UnjudgedLine]]:
    """Read both construct kinds out of every fragment, and what neither read.

    Scanning per FRAGMENT rather than over the composed body costs nothing and
    buys provenance: the composed text is the concatenation of its fragments, so
    a finding can name the file and line to open instead of the artifact the
    text ended up in. That is the same reason :mod:`role_duties` scans per
    fragment.
    """
    references: list[RoleReference] = []
    unjudged: list[UnjudgedLine] = []
    for fragment in fragments:
        label = _fragment_label(fragment.source, project_root)
        for number, line in enumerate(fragment.text.splitlines(), start=1):
            source = f"{label}:{number}"
            found = [
                RoleReference(names=names, source=source, text=text, designated=designated)
                for designated, group in (
                    (True, _designations(line)),
                    (False, _inferred_rosters(line, roles)),
                )
                for names, text in group
            ]
            references.extend(found)
            entry = _unjudged(line, source, roles, found)
            if entry is not None:
                unjudged.append(entry)
    return references, unjudged


def _mentioned(line: str, roles: frozenset[str]) -> tuple[str, ...]:
    """Composed role names occurring on a line as whole words, in role order."""
    return tuple(
        role for role in sorted(roles) if re.search(rf"(?<![\w-]){re.escape(role)}(?![\w-])", line)
    )


def _unjudged(
    line: str, source: str, roles: frozenset[str], found: list[RoleReference]
) -> UnjudgedLine | None:
    """A line naming two or more roles that no construct on it accounts for."""
    mentioned = _mentioned(line, roles)
    if len(mentioned) < 2:
        return None
    read = {name for reference in found for name in reference.names}
    if set(mentioned) <= read:
        return None
    return UnjudgedLine(
        source=source,
        roles=mentioned,
        text=line.strip(),
        why=(
            f"the line names {len(mentioned)} roles ({', '.join(mentioned)}) and "
            "no construct this derivation reads accounts for them, so whether it "
            "is a roster that must be complete or an ordering that must not be "
            "was not decided here"
        ),
    )


def _unmapped(role: str, omitting: list[RoleReference]) -> RoleMapFinding:
    sites = tuple(reference.source for reference in omitting)
    where = f" — including the {len(sites)} roster(s) above" if sites else ""
    return RoleMapFinding(
        kind="unmapped",
        role=role,
        sites=sites,
        severity="error",
        why=(
            f"`{role}` is a role this flow composes and the composed "
            f"`{_MAP_ARTIFACT}` names it nowhere{where} — an agent reading the "
            "entry point, as that document instructs, learns that the role does "
            "not exist"
        ),
        remediation=(
            f"name `{role}` in the role map and the Agent Roles table of the "
            f"shipped `{_MAP_ARTIFACT}` core, so every adopter's composed copy "
            "carries it"
        ),
    )


def _partial(role: str, omitting: list[RoleReference]) -> RoleMapFinding:
    designated = [reference for reference in omitting if reference.designated]
    return RoleMapFinding(
        kind="partial",
        role=role,
        sites=tuple(reference.source for reference in omitting),
        severity="error" if designated else "warn",
        why=(
            f"`{role}` is a role this flow composes and {len(omitting)} roster(s) "
            f"in the composed `{_MAP_ARTIFACT}` enumerate other roles without it "
            "— a reader who stops at one of them has a list that is wrong rather "
            "than short"
        ),
        remediation=(
            f"add `{role}` to each roster named above, or, when the run is an "
            "ordering rather than an enumeration, write it in a shape this "
            "derivation does not read as a roster"
        ),
    )


def _unbacked(name: str, sites: list[str]) -> RoleMapFinding:
    return RoleMapFinding(
        kind="unbacked",
        role=name,
        sites=tuple(sites),
        severity="error",
        why=(
            f"the composed `{_MAP_ARTIFACT}` designates `{name}` as a role and no "
            "CORE fragment ships one by that name, so an agent told to launch it "
            "has nothing to read"
        ),
        remediation=(
            f"correct the name, or ship `roles/core/{name}.md.txt` whose front "
            "matter names itself so the role exists in every reader"
        ),
    )


def _judge(roles: tuple[str, ...], references: list[RoleReference]) -> list[RoleMapFinding]:
    """Both directions, one finding per role, each naming every site to open."""
    population = frozenset(roles)
    rosters = _rosters(references, population)
    findings: list[RoleMapFinding] = []
    for role in roles:
        omitting = [roster for roster in rosters if role not in roster.names]
        if not any(role in reference.names for reference in references):
            findings.append(_unmapped(role, omitting))
        elif omitting:
            findings.append(_partial(role, omitting))
    findings.extend(_unbacked_findings(references, population))
    return findings


def _rosters(references: list[RoleReference], population: frozenset[str]) -> list[RoleReference]:
    """References enumerating two or more composed roles, hence owing all of them."""
    return [
        reference for reference in references if len(population.intersection(reference.names)) >= 2
    ]


def _unbacked_findings(
    references: list[RoleReference], population: frozenset[str]
) -> list[RoleMapFinding]:
    """Names a DESIGNATION claims are roles and no core fragment ships.

    Inferred rosters are excluded on purpose: a punctuated run's other tokens
    are ordinary words, and reporting them would turn ``we deploy to `dev`,
    `staging``` into a release-introduced error in an adopter's own prose.
    """
    sites: dict[str, list[str]] = {}
    for reference in references:
        if not reference.designated:
            continue
        for name in reference.names:
            if name not in population:
                sites.setdefault(name, []).append(reference.source)
    return [_unbacked(name, where) for name, where in sorted(sites.items())]


def role_map_report(
    project_root: Path,
    config: FlowConfig | None = None,
    *,
    roles: tuple[str, ...] | None = None,
) -> RoleMapReport:
    """Check every composed role against the map that enumerates roles.

    ``config`` defaults to the project's resolved ``flow.yml``. Raises
    :class:`~beadloom.onboarding.flow_config.FlowConfigError` when that file
    cannot be resolved, for the reason :func:`role_duties.duty_report` does: a
    report computed against a guessed configuration is a verdict about a flow
    the project does not run.

    ``roles`` defaults to the population ``role-composer`` derives from the
    shipped CORE fragments, which is the only value production passes. A caller
    varies it to ask the question of a population other than the running flow's
    — which is how this check is demonstrated red on a sixth role without
    writing a sixth fragment into a templates directory every concurrent run in
    the same working tree also reads.
    """
    resolved = config if config is not None else resolve_flow_config(project_root)
    population = roles if roles is not None else ROLE_NAMES
    composition = compose(
        "claude", CLAUDE_ARTIFACT_NAME, config=resolved, project_root=project_root
    )
    references, not_judged = _references(
        composition.fragments, project_root, frozenset(population)
    )
    findings = _judge(population, references)
    return RoleMapReport(
        roles=population,
        references=tuple(references),
        rosters=tuple(_rosters(references, frozenset(population))),
        findings=tuple(sorted(findings, key=lambda f: (f.kind, f.role, f.sites))),
        not_judged=tuple(not_judged),
        inspected=tuple(
            _fragment_label(fragment.source, project_root) for fragment in composition.fragments
        ),
    )
