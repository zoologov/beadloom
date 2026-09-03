# beadloom:domain=onboarding
# beadloom:feature=role-duties
"""A duty declared for a role, checked against that role's composed core.

**The class this closes**, stated as narrowly as the evidence supports: *a duty
an agent is obliged to perform is written somewhere the performer does not
read*. It was measured four times across two epics before anyone named it. The
clean-room rule lives in the coordinator's prose and in the wave planner, and
occurs zero times in the role cores the roles actually receive; every agent said
the right words because the coordinator typed them into every launch prompt.

**Duties are DECLARED, never inferred.** A detector that read English role prose
looking for obligations would be the fourth instance of a class this project has
already filed three times: the docs-audit keyword-proximity classifier binds
"supports 11 languages" to a count of the languages the project is *written* in
(BDL-UX #205), reads a version cited as an example as a claim (#190) and
verifies nothing in a non-English document while counting it scanned (#209). So
a duty carries a marker, exactly the way a scenario carries ``@bead:`` and
``@node:``, and the binding is checked in **both** directions:

* ``<!-- beadloom:duty=<id> roles=<a,b> -->`` in any composed flow artifact —
  *this duty is owed by these roles*;
* ``<!-- beadloom:carries=<id> -->`` in a fragment that composes into a role —
  *this text is that duty*.

:func:`duty_report` composes every flow artifact for a project's ``flow.yml``
plus its project layer, collects both marker kinds with the fragment each came
from, and reports four findings: a duty declared for a role whose composed core
does not carry it, a duty carried by a role that no artifact declares, a
declaration naming a role no CORE fragment ships, and a ``duty=`` marker with no
``roles=`` list. The first two are the two directions ``scenario-coverage``
already checks one layer up; the third is its "scenario naming a dead node".

**The limit, stated here and in the report rather than discovered later.** A
duty carried only by a coordinator's launch prompt is unreachable by any
file-based check, because a prompt is not an artifact. This check covers
composed artifacts and nothing else, and :attr:`DutyReport.not_inspected` says
so on every run alongside the fragments this project's configuration does not
compose. That limit is the argument for moving a duty out of the prompt and into
a composed core, not a reason to leave it there.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from beadloom.onboarding.agentic_flow_setup import COMMAND_FILES
from beadloom.onboarding.composer import (
    CLAUDE_ARTIFACT_NAME,
    PROJECT_FLOW_DIRNAME,
    compose,
    templates_dir,
)
from beadloom.onboarding.flow_config import resolve_flow_config
from beadloom.onboarding.role_composer import ROLE_NAMES

if TYPE_CHECKING:
    from collections.abc import Iterator

    from beadloom.onboarding.composer import Composition, LayerFragment
    from beadloom.onboarding.flow_config import FlowConfig

__all__ = [
    "CARRIES_MARKER",
    "DUTY_MARKER",
    "DutyDeclaration",
    "DutyFinding",
    "DutyReport",
    "NotInspected",
    "duty_report",
]

#: The two marker spellings, named so a caller can render them in advice
#: without re-typing them (the fifth copy of a literal is what drifts).
DUTY_MARKER = "beadloom:duty"
CARRIES_MARKER = "beadloom:carries"

_MARKER_RE = re.compile(
    r"<!--\s*beadloom:(?P<verb>duty|carries)=(?P<duty>[A-Za-z0-9][\w.-]*)"
    r"(?P<rest>[^>]*?)-->"
)
_ROLES_RE = re.compile(r"\broles=(?P<roles>[A-Za-z0-9_,.-]+)")

#: The channel nothing on disk can reach. Constant because it is not a file: a
#: launch prompt exists only inside a running session, so no glob can find it
#: and no future release can make it inspectable.
_LAUNCH_PROMPT = "the coordinator's launch prompt"


@dataclass(frozen=True)
class DutyDeclaration:
    """A duty and the roles an artifact says owe it."""

    duty: str
    roles: tuple[str, ...]
    source: str


@dataclass(frozen=True)
class DutyFinding:
    """One incoherence between what is declared and what a role is told.

    ``kind`` is one of ``undelivered`` (declared for a role whose composed core
    does not carry it), ``undeclared`` (carried by a role and declared by
    nothing), ``unknown-role`` (declared for a role no CORE fragment ships) and
    ``malformed`` (a ``duty=`` marker naming no performer). ``source`` is the
    file a reader should open; ``why`` says what is wrong and ``remediation``
    the concrete move.
    """

    kind: str
    duty: str
    role: str | None
    source: str
    why: str
    remediation: str


@dataclass(frozen=True)
class NotInspected:
    """A place a duty could hide that this check cannot see.

    Reported on every run, clean or not. A check that lists only what it found
    hands the reader a clean list, and a clean list is trusted and stopped at.
    """

    source: str
    why: str


@dataclass(frozen=True)
class DutyReport:
    """What a project declares, what its roles carry, and what was not seen."""

    declarations: tuple[DutyDeclaration, ...]
    carried: tuple[tuple[str, str], ...]
    findings: tuple[DutyFinding, ...]
    inspected: tuple[str, ...]
    not_inspected: tuple[NotInspected, ...]


def _fragment_label(source: str, project_root: Path) -> str:
    """The path a reader opens, relative to whichever root owns the fragment."""
    path = Path(source)
    if not path.is_absolute():
        return str(path)
    for root, prefix in ((project_root, ""), (templates_dir().parent, "")):
        try:
            return prefix + str(path.relative_to(root))
        except ValueError:
            continue
    return str(path)


def _markers(fragment: LayerFragment) -> Iterator[re.Match[str]]:
    return _MARKER_RE.finditer(fragment.text)


def _compose_all(
    config: FlowConfig, project_root: Path
) -> list[tuple[str, Composition]]:
    """Every agent-addressed artifact this flow composes, with its label.

    Roles, slash commands and ``CLAUDE.md`` — the artifacts a suppression is
    matched against, for the same reason: they are the ones addressed to an
    agent. A document template carries no rules, so it owes no duties either.
    """
    artifacts = [
        *((f"roles/{role}", "roles", role) for role in ROLE_NAMES),
        *((f"commands/{name}", "commands", name) for name in COMMAND_FILES),
        (f"claude/{CLAUDE_ARTIFACT_NAME}", "claude", CLAUDE_ARTIFACT_NAME),
    ]
    return [
        (label, compose(kind, name, config=config, project_root=project_root))
        for label, kind, name in artifacts
    ]


def _declaration(
    match: re.Match[str], label: str
) -> tuple[DutyDeclaration | None, DutyFinding | None]:
    """Parse one ``duty=`` marker, or say why it declares nothing."""
    duty = match.group("duty")
    roles = _ROLES_RE.search(match.group("rest"))
    if roles is None:
        return None, DutyFinding(
            kind="malformed",
            duty=duty,
            role=None,
            source=label,
            why=(
                f"`{label}` carries `{DUTY_MARKER}={duty}` with no `roles=` list, "
                "so it names no performer and declares nothing"
            ),
            remediation=(
                f"write `<!-- {DUTY_MARKER}={duty} roles=dev,review -->` naming "
                "every role that owes the duty"
            ),
        )
    named = tuple(
        sorted({role for role in roles.group("roles").split(",") if role})
    )
    return DutyDeclaration(duty=duty, roles=named, source=label), None


def _scan(
    composed: list[tuple[str, Composition]], project_root: Path
) -> tuple[
    list[DutyDeclaration], dict[tuple[str, str], str], list[DutyFinding], set[Path]
]:
    """Read both marker kinds out of every composed fragment.

    Scanning per FRAGMENT rather than per composed text costs nothing and buys
    provenance: the composed body is the concatenation of its fragments, so the
    finding can name the file to open instead of the artifact it ended up in.

    Carriage is recorded for EVERY composed artifact, not only the role files.
    Delivery to a role is still judged against the role's own artifact, but a
    ``carries`` marker in a slash command is a duty text somebody wrote, and
    dropping it because its artifact is not a role would be this check
    committing the class it exists to report.
    """
    declarations: list[DutyDeclaration] = []
    carried: dict[tuple[str, str], str] = {}  # (artifact label, duty) -> fragment
    findings: list[DutyFinding] = []
    read: set[Path] = set()
    for label, composition in composed:
        for fragment in composition.fragments:
            read.add(_resolved(fragment.source, project_root))
            where = _fragment_label(fragment.source, project_root)
            for match in _markers(fragment):
                if match.group("verb") == "duty":
                    declared, malformed = _declaration(match, where)
                    if declared is not None:
                        declarations.append(declared)
                    if malformed is not None:
                        findings.append(malformed)
                else:
                    carried.setdefault((label, match.group("duty")), where)
    return declarations, carried, findings, read


def _resolved(source: str, project_root: Path) -> Path:
    """A fragment source as one comparable absolute path.

    Shipped fragments arrive absolute and project ones relative, and the two
    have to meet before a subtraction can mean anything.
    """
    path = Path(source)
    return path if path.is_absolute() else (project_root / path).resolve()


def _role_artifact(role: str) -> str:
    """The composed artifact a role's core becomes."""
    return f"roles/{role}"


def _performer(artifact: str) -> str:
    """The performer an artifact addresses, as a reader would name it."""
    kind, _, name = artifact.partition("/")
    return name if kind == "roles" else artifact


def _undelivered(
    declaration: DutyDeclaration, role: str, carried: dict[tuple[str, str], str]
) -> DutyFinding | None:
    if (_role_artifact(role), declaration.duty) in carried:
        return None
    return DutyFinding(
        kind="undelivered",
        duty=declaration.duty,
        role=role,
        source=declaration.source,
        why=(
            f"`{declaration.source}` declares the `{declaration.duty}` duty for "
            f"`{role}`, and `{role}`'s composed core carries no "
            f"`{CARRIES_MARKER}={declaration.duty}` marker — the role is obliged "
            "to do something it is never told"
        ),
        remediation=(
            f"add the duty's text and `<!-- {CARRIES_MARKER}="
            f"{declaration.duty} -->` to the core fragment for `{role}` (or to a "
            "shared core fragment when every role owes it), then regenerate the "
            "adapters with `beadloom config-check --fix`"
        ),
    )


def _unknown_role(declaration: DutyDeclaration, role: str) -> DutyFinding:
    return DutyFinding(
        kind="unknown-role",
        duty=declaration.duty,
        role=role,
        source=declaration.source,
        why=(
            f"`{declaration.source}` declares the `{declaration.duty}` duty for "
            f"`{role}`, and no CORE fragment ships a role by that name — the "
            f"roles this flow ships are: {', '.join(ROLE_NAMES)}"
        ),
        remediation=(
            f"correct the `roles=` list, or ship `roles/core/{role}.md.txt` whose "
            "front matter names itself so the role exists in every reader"
        ),
    )


def _undeclared(role: str, duty: str, source: str) -> DutyFinding:
    return DutyFinding(
        kind="undeclared",
        duty=duty,
        role=role,
        source=source,
        why=(
            f"`{source}` carries the `{duty}` duty into `{role}`'s composed core "
            "and no composed artifact declares it — nothing states which roles "
            "owe it, so nothing can check that the others were told"
        ),
        remediation=(
            f"declare it with `<!-- {DUTY_MARKER}={duty} roles=... -->` in the "
            "artifact that owns the rule (the coordinator command, or "
            f"CLAUDE.md), or drop the `{CARRIES_MARKER}` marker"
        ),
    )


def _judge(
    declarations: list[DutyDeclaration], carried: dict[tuple[str, str], str]
) -> list[DutyFinding]:
    """Both directions, over merged declarations so one duty yields one verdict."""
    findings: list[DutyFinding] = []
    for declaration in declarations:
        for role in declaration.roles:
            if role not in ROLE_NAMES:
                findings.append(_unknown_role(declaration, role))
                continue
            undelivered = _undelivered(declaration, role, carried)
            if undelivered is not None:
                findings.append(undelivered)
    declared = {declaration.duty for declaration in declarations}
    findings.extend(
        _undeclared(_performer(artifact), duty, source)
        for (artifact, duty), source in carried.items()
        if duty not in declared
    )
    return findings


def _uninspected(
    read: set[Path], project_root: Path, config: FlowConfig
) -> list[NotInspected]:
    """Every place a duty marker could sit that no composition read.

    Derived by subtraction rather than listed: a fragment carrying a marker that
    is not among the fragments the compositions read is one this configuration
    does not compose — another architecture's overlay, an unconfigured stack, a
    project fragment for a role that does not exist. The launch prompt is added
    as a constant because it is the one channel that is not a file at all.
    """
    entries = [
        NotInspected(
            source=_LAUNCH_PROMPT,
            why=(
                "a prompt is not an artifact, so a duty carried only there is "
                "unreachable by any file-based check; moving it into a composed "
                "core is what makes it checkable"
            ),
        )
    ]
    stack = ", ".join(config.stack) or "none"
    for path in sorted(_marked_files(project_root)):
        if path in read:
            continue
        entries.append(
            NotInspected(
                source=_fragment_label(str(path), project_root),
                why=(
                    "it carries a duty marker and no artifact this flow composes "
                    f"reads it (architecture {config.architecture}, stack "
                    f"{stack}), so the duties in it reach no role"
                ),
            )
        )
    return entries


def _is_vendored_snapshot(path: Path) -> bool:
    """Whether *path* is the byte-identical copy of a composed role file.

    ``templates/agentic_flow/agents/*.md.txt`` is a SNAPSHOT of the live
    ``.claude/agents/*.md``, held byte-identical by the vendoring drift guard and
    dropped verbatim into an adopter's roles directory by the plain scaffold
    path. It therefore carries every marker its composed role carries, and
    subtraction listed all five of them the moment a role core first declared a
    duty — under a reason that says the duties in it reach no role, which is
    false twice over: the marker is inspected in its composed form, and the file
    reaches an adopter's roles directory. Excluding output is not the list this
    derivation avoids; it is the derivation declining to report its own input
    back to itself.
    """
    return path.parent == templates_dir() / "agentic_flow" / "agents"


def _marked_files(project_root: Path) -> Iterator[Path]:
    """Fragment files carrying any duty marker, shipped and project alike."""
    candidates = [
        *(
            path
            for path in templates_dir().rglob("*.md.txt")
            if not _is_vendored_snapshot(path)
        ),
        *(project_root / PROJECT_FLOW_DIRNAME).rglob("*.md"),
    ]
    for path in candidates:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            # Unreadable is not "carries nothing"; it is reported by the caller
            # that owns file health, not silently counted as clean here.
            continue
        if _MARKER_RE.search(text):
            yield path.resolve()


def duty_report(
    project_root: Path, config: FlowConfig | None = None
) -> DutyReport:
    """Check every declared duty against the composed core of each role it names.

    ``config`` defaults to the project's resolved ``flow.yml``. Raises
    :class:`~beadloom.onboarding.flow_config.FlowConfigError` when that file
    cannot be resolved — a report computed against a guessed configuration would
    be a verdict about a flow the project does not run.
    """
    resolved = config if config is not None else resolve_flow_config(project_root)
    composed = _compose_all(resolved, project_root)
    declarations, carried, findings, read = _scan(composed, project_root)
    findings.extend(_judge(declarations, carried))
    return DutyReport(
        declarations=tuple(declarations),
        carried=tuple(sorted(carried)),
        findings=tuple(
            sorted(findings, key=lambda f: (f.kind, f.duty, f.role or "", f.source))
        ),
        inspected=tuple(label for label, _ in composed),
        not_inspected=tuple(_uninspected(read, project_root, resolved)),
    )
