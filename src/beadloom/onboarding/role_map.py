# beadloom:domain=onboarding
# beadloom:feature=role-map
"""A role this flow composes, checked against the map its tool's reader opens.

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

**One map per declared tool, and the tool axis is stated** (BDL-068 `.84`).
The corpus comes from ``config.tools`` through :data:`_MAP_ARTIFACTS` -- the
composed ``CLAUDE.md`` for ``claude``, the Cursor orchestrator pointer
``role_adapters`` writes for ``cursor``. Until `.84` this module composed
Claude's map unconditionally and never read ``tools:``, so a project declaring
``cursor`` alone was judged against a document its flow does not declare, while
the one its agent does read -- ``.cursor/rules/beadloom-flow.md``, whose brace
expansion enumerates every composed role -- was asked nothing. That is BDL-UX
#252's own class, one axis over, inside the check written to close it.

A declared tool :data:`_MAP_ARTIFACTS` has no row for is reported in
:attr:`RoleMapReport.unreached` and judged against nothing. It is a stated
population rather than a finding, for the reason ``not_judged`` is one: the gap
belongs to Beadloom, which composes adapters for that tool and ships no map
artifact for it, and turning it into an adopter's drift would fail a project for
a hole in the release it installed.

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
    LayerFragment,
    compose,
    templates_dir,
)
from beadloom.onboarding.flow_config import resolve_flow_config
from beadloom.onboarding.role_adapters import cursor_rules_body, cursor_rules_relpath
from beadloom.onboarding.role_composer import ROLE_NAMES

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from beadloom.onboarding.flow_config import FlowConfig

__all__ = [
    "MapArtifact",
    "RoleMapFinding",
    "RoleMapReport",
    "RoleReference",
    "UnjudgedLine",
    "UnreachedTool",
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


@dataclass(frozen=True)
class MapArtifact:
    """One tool's role map: the document its adopter opens to learn what exists.

    ``name`` is the project-relative path that tool's reader holds, so a finding
    can name a file rather than an artifact kind. ``authored_in`` is the phrase a
    remediation puts after "name `<role>` in", because the two artifacts are
    repaired in two different places -- one is prose in a shipped core, the other
    is a template rendered over the derived role population.

    ``fragments`` is the body, in the pieces a finding takes its provenance from.
    It is the COMPOSITION this flow would write rather than whatever is on disk,
    which is the same corpus ``role_duties`` reads and for the same reason: a
    verdict about the file an adopter happens to hold is a verdict about their
    edit, and a verdict about the composition is a verdict about the release.
    """

    tool: str
    name: str
    authored_in: str
    fragments: tuple[LayerFragment, ...]


@dataclass(frozen=True)
class UnreachedTool:
    """A declared tool whose role map this release cannot name, hence did not read.

    Not a finding, and the distinction is the one this epic ships everywhere
    else: a population the check could not enter is stated beside the verdict,
    never converted into one. The gap is Beadloom's -- a tool it composes
    adapters for and ships no map artifact for -- so reporting it as the
    adopter's drift would fail a project for a hole in the release it installed.
    """

    tool: str
    why: str


def _claude_map(config: FlowConfig, project_root: Path) -> MapArtifact:
    """Claude's map: the composed ``CLAUDE.md``, core plus overlays plus project."""
    composition = compose(
        "claude", CLAUDE_ARTIFACT_NAME, config=config, project_root=project_root
    )
    return MapArtifact(
        tool="claude",
        name=str(Path(".claude") / f"{CLAUDE_ARTIFACT_NAME}.md"),
        authored_in=(
            f"the role map and the Agent Roles table of the shipped "
            f"`{CLAUDE_ARTIFACT_NAME}.md` core, so every adopter's composed copy "
            "carries it"
        ),
        fragments=composition.fragments,
    )


def _cursor_map(_config: FlowConfig, _project_root: Path) -> MapArtifact:
    """Cursor's map: the orchestrator pointer ``role_adapters`` writes.

    Four lines, one of which is a brace expansion over every composed role --
    which is exactly the construct this check reads as a designation, so the map
    a Cursor adopter holds is judged by the same derivation Claude's is. The
    pointer takes no overlay and no project layer, so its body does not depend on
    ``config``; the parameters are the registry's shape rather than this reader's
    need.
    """
    relpath = cursor_rules_relpath()
    return MapArtifact(
        tool="cursor",
        name=str(relpath),
        authored_in=(
            "the Cursor orchestrator pointer in `onboarding/role_adapters.py`, "
            "whose roster is rendered over the derived role population rather "
            "than typed into it -- a role missing from it means that rendering "
            "has stopped covering the population"
        ),
        fragments=(LayerFragment("generated", str(relpath), cursor_rules_body()),),
    )


#: Which artifact enumerates roles, per tool. THE POPULATION IS ``config.tools``
#: and this is the lookup, not the other way round: a tool an adopter declares
#: and this table has no row for is reported as unreached, so the missing row
#: reaches the output instead of being answered with another tool's map. That is
#: the defect this replaced -- ``compose("claude", ...)`` ran unconditionally, so
#: a cursor-only project's verdict was about a document its agent never opens.
_MAP_ARTIFACTS: dict[str, Callable[[FlowConfig, Path], MapArtifact]] = {
    "claude": _claude_map,
    "cursor": _cursor_map,
}


def _unreached_tool(tool: str) -> UnreachedTool:
    return UnreachedTool(
        tool=tool,
        why=(
            f"`{tool}` is declared in this project's flow and this release names "
            "no artifact of it that enumerates roles, so the role map was NOT "
            f"checked for `{tool}`: a role missing from whatever document a "
            f"`{tool}` agent reads would not be reported here"
        ),
    )


@dataclass(frozen=True)
class RoleReference:
    """One construct in the map that names roles, and where to open it.

    ``designated`` separates the two kinds: a designation claims each name is a
    role, an inferred roster only guesses that a punctuated run is one. ``tool``
    names whose map it was read from, because one run reads one map per declared
    tool and a count that does not say which map it covers is the shape this
    check was fixed for.
    """

    names: tuple[str, ...]
    source: str
    tool: str
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

    ``tool`` and ``artifact`` say WHICH map the finding is about. A project
    declaring two tools holds two maps, and a role can be named in one of them
    and missing from the other -- so a finding that does not carry its artifact
    is a finding a reader cannot act on.
    """

    kind: str
    role: str
    tool: str
    artifact: str
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

    ``tool`` and ``artifact`` name the map the line is in, for the reason
    :class:`RoleMapFinding` carries them: with two maps read in one run, a bare
    ``source`` line number does not say which document a reader opens.
    """

    source: str
    tool: str
    artifact: str
    roles: tuple[str, ...]
    text: str
    why: str


@dataclass(frozen=True)
class RoleMapReport:
    """What this flow composes, what each tool's map enumerates, and what was not read.

    ``tools`` is the declared population and ``artifacts`` + ``unreached``
    partition it: every declared tool is either one map that was read or one
    reason it was not. ``references``, ``rosters``, ``findings`` and
    ``not_judged`` are flat across the artifacts and each element names its own,
    so a caller can render per tool without a second lookup.
    """

    roles: tuple[str, ...]
    tools: tuple[str, ...]
    artifacts: tuple[MapArtifact, ...]
    unreached: tuple[UnreachedTool, ...]
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
    artifact: MapArtifact, project_root: Path, roles: frozenset[str]
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
    for fragment in artifact.fragments:
        label = _fragment_label(fragment.source, project_root)
        for number, line in enumerate(fragment.text.splitlines(), start=1):
            source = f"{label}:{number}"
            found = [
                RoleReference(
                    names=names,
                    source=source,
                    tool=artifact.tool,
                    text=text,
                    designated=designated,
                )
                for designated, group in (
                    (True, _designations(line)),
                    (False, _inferred_rosters(line, roles)),
                )
                for names, text in group
            ]
            references.extend(found)
            entry = _unjudged(line, source, artifact, roles, found)
            if entry is not None:
                unjudged.append(entry)
    return references, unjudged


def _mentioned(line: str, roles: frozenset[str]) -> tuple[str, ...]:
    """Composed role names occurring on a line as whole words, in role order."""
    return tuple(
        role for role in sorted(roles) if re.search(rf"(?<![\w-]){re.escape(role)}(?![\w-])", line)
    )


def _unjudged(
    line: str,
    source: str,
    artifact: MapArtifact,
    roles: frozenset[str],
    found: list[RoleReference],
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
        tool=artifact.tool,
        artifact=artifact.name,
        roles=mentioned,
        text=line.strip(),
        why=(
            f"the line names {len(mentioned)} roles ({', '.join(mentioned)}) and "
            "no construct this derivation reads accounts for them, so whether it "
            "is a roster that must be complete or an ordering that must not be "
            "was not decided here"
        ),
    )


def _unmapped(
    role: str, artifact: MapArtifact, omitting: list[RoleReference]
) -> RoleMapFinding:
    sites = tuple(reference.source for reference in omitting)
    where = f" — including the {len(sites)} roster(s) above" if sites else ""
    return RoleMapFinding(
        kind="unmapped",
        role=role,
        tool=artifact.tool,
        artifact=artifact.name,
        sites=sites,
        severity="error",
        why=(
            f"`{role}` is a role this flow composes and `{artifact.name}` — the "
            f"map a `{artifact.tool}` reader opens — names it nowhere{where}: an "
            "agent reading it, as that document instructs, learns that the role "
            "does not exist"
        ),
        remediation=f"name `{role}` in {artifact.authored_in}",
    )


def _partial(
    role: str, artifact: MapArtifact, omitting: list[RoleReference]
) -> RoleMapFinding:
    designated = [reference for reference in omitting if reference.designated]
    return RoleMapFinding(
        kind="partial",
        role=role,
        tool=artifact.tool,
        artifact=artifact.name,
        sites=tuple(reference.source for reference in omitting),
        severity="error" if designated else "warn",
        why=(
            f"`{role}` is a role this flow composes and {len(omitting)} roster(s) "
            f"in `{artifact.name}` enumerate other roles without it — a reader who "
            "stops at one of them has a list that is wrong rather than short"
        ),
        remediation=(
            f"add `{role}` to each roster named above, or, when the run is an "
            "ordering rather than an enumeration, write it in a shape this "
            "derivation does not read as a roster"
        ),
    )


def _unbacked(name: str, artifact: MapArtifact, sites: list[str]) -> RoleMapFinding:
    return RoleMapFinding(
        kind="unbacked",
        role=name,
        tool=artifact.tool,
        artifact=artifact.name,
        sites=tuple(sites),
        severity="error",
        why=(
            f"`{artifact.name}` — the map a `{artifact.tool}` reader opens — "
            f"designates `{name}` as a role and no CORE fragment ships one by "
            "that name, so an agent told to launch it has nothing to read"
        ),
        remediation=(
            f"correct the name, or ship `roles/core/{name}.md.txt` whose front "
            "matter names itself so the role exists in every reader"
        ),
    )


def _judge(
    roles: tuple[str, ...], artifact: MapArtifact, references: list[RoleReference]
) -> list[RoleMapFinding]:
    """Both directions, one finding per role, each naming every site to open.

    Judged per ARTIFACT rather than over every reference in the run: two tools
    hold two maps, each owes the whole role population on its own, and a role
    named in one of them is not thereby named in the other.
    """
    population = frozenset(roles)
    rosters = _rosters(references, population)
    findings: list[RoleMapFinding] = []
    for role in roles:
        omitting = [roster for roster in rosters if role not in roster.names]
        if not any(role in reference.names for reference in references):
            findings.append(_unmapped(role, artifact, omitting))
        elif omitting:
            findings.append(_partial(role, artifact, omitting))
    findings.extend(_unbacked_findings(artifact, references, population))
    return findings


def _rosters(references: list[RoleReference], population: frozenset[str]) -> list[RoleReference]:
    """References enumerating two or more composed roles, hence owing all of them."""
    return [
        reference for reference in references if len(population.intersection(reference.names)) >= 2
    ]


def _unbacked_findings(
    artifact: MapArtifact, references: list[RoleReference], population: frozenset[str]
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
    return [_unbacked(name, artifact, where) for name, where in sorted(sites.items())]


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

    ONE MAP PER DECLARED TOOL. The corpus is derived from ``config.tools``
    through :data:`_MAP_ARTIFACTS`, and a declared tool with no row there is
    reported in ``unreached`` rather than answered with another tool's map
    (BDL-068 `.84`).
    """
    resolved = config if config is not None else resolve_flow_config(project_root)
    population = roles if roles is not None else ROLE_NAMES
    artifacts: list[MapArtifact] = []
    unreached: list[UnreachedTool] = []
    references: list[RoleReference] = []
    not_judged: list[UnjudgedLine] = []
    findings: list[RoleMapFinding] = []
    inspected: list[str] = []
    for tool in resolved.tools:
        reader = _MAP_ARTIFACTS.get(tool)
        if reader is None:
            unreached.append(_unreached_tool(tool))
            continue
        artifact = reader(resolved, project_root)
        artifacts.append(artifact)
        found, unread = _references(artifact, project_root, frozenset(population))
        references.extend(found)
        not_judged.extend(unread)
        findings.extend(_judge(population, artifact, found))
        inspected.extend(
            _fragment_label(fragment.source, project_root) for fragment in artifact.fragments
        )
    return RoleMapReport(
        roles=population,
        tools=resolved.tools,
        artifacts=tuple(artifacts),
        unreached=tuple(unreached),
        references=tuple(references),
        rosters=tuple(_rosters(references, frozenset(population))),
        findings=tuple(sorted(findings, key=lambda f: (f.tool, f.kind, f.role, f.sites))),
        not_judged=tuple(not_judged),
        inspected=tuple(inspected),
    )
