# beadloom:domain=infrastructure
# beadloom:component=doc-roots
"""Where each documentation space lives, and which space a document belongs to.

Three spaces, named after what the document IS rather than after a status
(BDL-061 S5):

* **TO-BE** — PRD, RFC, BRIEF, CONTEXT, PLAN. What the system is to become.
* **AS-IS** — SPEC, DOC, README. What it is. The space ``sync-check`` holds
  against the code, which is exactly what "as-is" means.
* **WORKING** — ACTIVE. Ephemeral progress state, neither intent nor reality.

Deliberately *not* TODO/DONE. Nothing here changes status: a PRD does not become
"done", it stays the record of what was intended while a **different** artifact —
the AS-IS document — is updated to describe the new reality. The claim worth
checking is therefore a relation between two artifacts, and a flag on one
document could not express it.

This module is the config reader half, a peer of :mod:`beadloom.infrastructure.
scan_paths`: it answers *where* and *which*, and nothing about freshness. The
relation itself lives in :mod:`beadloom.application.doc_spaces`, because it joins
the graph, the tracker and this vocabulary — three readers no single domain owns.

Roots are configurable from the start. A hardcoded ``docs/`` would make every
check built on this true on Beadloom's own layout and unknown everywhere else,
which is the defect class :mod:`tests.adopter_project` exists to catch.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

#: Intent: what the system is to become.
SPACE_TO_BE = "to_be"

#: Reality: what the system is, held against the code by ``sync-check``.
SPACE_AS_IS = "as_is"

#: Ephemeral progress state — neither intent nor reality.
SPACE_WORKING = "working"

#: Every space, in the order a report reads best: intent, reality, work.
SPACES: tuple[str, ...] = (SPACE_TO_BE, SPACE_AS_IS, SPACE_WORKING)

#: ``.beadloom/config.yml`` key holding a project's own spaces.
CONFIG_KEY = "doc_roots"

#: Where each space lives when a project declares nothing. ``to_be`` points at
#: the flow's scaffold (``/task-init`` writes there and ``active-sync`` already
#: reads it); ``as_is`` at the documentation tree ``sync-check`` pairs with code.
#: ``working`` declares no root of its own because ACTIVE.md lives INSIDE the
#: TO-BE tree — its space follows from its kind, which is why kind wins below.
DEFAULT_ROOTS: Mapping[str, tuple[str, ...]] = {
    SPACE_TO_BE: (
        ".claude/development/docs/features/*/*.md",
        ".claude/development/*.md",
    ),
    SPACE_AS_IS: ("docs/**/*.md", "*.md"),
    SPACE_WORKING: (),
}

#: Document kinds each space claims, when a project declares nothing. Keyed by
#: the file stem the shipped flow writes, upper-cased so ``prd.md`` and ``PRD.md``
#: answer the same — a project whose convention is lower case is not a project
#: with a different vocabulary.
DEFAULT_KINDS: Mapping[str, tuple[str, ...]] = {
    SPACE_TO_BE: ("PRD", "RFC", "BRIEF", "CONTEXT", "PLAN"),
    SPACE_AS_IS: ("SPEC", "DOC", "README"),
    SPACE_WORKING: ("ACTIVE",),
}

#: The reason the shipped WORKING exemption is declared with. Stated here rather
#: than left blank, because an exemption whose reason is empty is a config error
#: below and a shipped default must not be one.
DEFAULT_WORKING_REASON = (
    "ACTIVE.md records progress within a bead, not what the code is; holding it "
    "against the code would compare a document to something it never described"
)


def document_kind(path: str) -> str:
    """The kind of document a path names — ``PRD.md`` is a ``PRD``.

    The stem, because that is how the shipped flow names a document and it needs
    no configuration to derive. A project whose documents are ``prd.md`` gets
    ``prd`` as a kind of its own, which is honest: nothing here was told the two
    are the same thing. Space membership upper-cases before comparing, so the
    two do land in the same space.
    """
    name = path.replace("\\", "/").rsplit("/", 1)[-1]
    stem, _, _ = name.rpartition(".")
    return (stem or name).strip()


@dataclass(frozen=True)
class WorkingExemption:
    """The WORKING space's freshness exemption, as declared.

    A **declaration**, never an inference from a missing pair. Absence is not
    evidence: if the exemption were derived from "no sync pair mentions this
    document", deleting the pair would silently widen it, which is the equation
    BDL-UX #174 and this epic's `.57` both turn on.

    ``reason`` is mandatory and ``until`` is deliberately absent. ``until`` is an
    exit condition for a debt, and a document's being ephemeral is not a debt: an
    ACTIVE.md does not become a description of the code on a calendar date, so a
    mandatory date would be one nobody could choose honestly.
    """

    exempt_from_freshness: bool
    reason: str
    declared: bool = False
    """Whether the PROJECT declared this, rather than inheriting the default.

    The liveness finding ("this exemption excused nothing") applies to a
    declaration and not to a shipped default: a project that simply has no
    ephemeral documents has not switched a gate off, and reporting it would make
    the finding fire on every clean adopter. What stays visible either way is the
    COUNT of documents excused, which is what a shrinking denominator would show.
    """


@dataclass(frozen=True)
class DocSpaces:
    """A project's three documentation spaces, resolved from configuration."""

    roots: Mapping[str, tuple[str, ...]]
    kinds: Mapping[str, tuple[str, ...]]
    working: WorkingExemption
    config_errors: tuple[str, ...] = ()

    def space_of_kind(self, kind: str) -> str | None:
        """The space claiming *kind*, or ``None`` when no space claims it."""
        wanted = kind.strip().upper()
        for space in SPACES:
            if any(k.upper() == wanted for k in self.kinds.get(space, ())):
                return space
        return None

    def space_of(self, rel_path: str) -> str | None:
        """The space a project-relative document path belongs to.

        **Kind wins over root**, and the ordering is load-bearing rather than
        arbitrary: ``ACTIVE.md`` lives inside the TO-BE tree, so a root-first
        answer would classify every WORKING document as intent and the exemption
        would apply to nothing. A path in no root and of no known kind returns
        ``None`` — unclassified, which is reported rather than defaulted.
        """
        by_kind = self.space_of_kind(document_kind(rel_path))
        if by_kind is not None:
            return by_kind
        posix = rel_path.replace("\\", "/")
        for space in SPACES:
            if any(path_matches(posix, p) for p in self.roots.get(space, ())):
                return space
        return None

    def documents_in(self, project_root: Path, space: str) -> list[Path]:
        """Files under *space*'s roots whose kind does not move them elsewhere.

        Deterministically ordered and de-duplicated, because two globs may name
        one file and a report that counts it twice is wrong about its own
        population.
        """
        found: set[Path] = set()
        for pattern in self.roots.get(space, ()):
            found.update(p for p in project_root.glob(pattern) if p.is_file())
        kept = []
        for path in sorted(found):
            rel = _relative(path, project_root)
            if self.space_of(rel) == space:
                kept.append(path)
        return kept

    def working_documents(self, project_root: Path) -> list[Path]:
        """Every WORKING-kind document found anywhere under the declared roots.

        WORKING declares no root of its own, so its population is drawn from the
        other spaces' trees and filtered by kind. A search that looked only under
        ``roots[working]`` would find nothing and read exactly like a project
        with no ephemeral documents at all.
        """
        found: set[Path] = set()
        for space in SPACES:
            for pattern in self.roots.get(space, ()):
                found.update(p for p in project_root.glob(pattern) if p.is_file())
        return sorted(
            p
            for p in found
            if self.space_of(_relative(p, project_root)) == SPACE_WORKING
        )


def _relative(path: Path, project_root: Path) -> str:
    """*path* as a project-relative POSIX string, or its absolute spelling."""
    try:
        return path.relative_to(project_root).as_posix()
    except ValueError:
        return path.as_posix()


@lru_cache(maxsize=256)
def _pattern_regex(pattern: str) -> re.Pattern[str]:
    """*pattern* as a regex with the same reach ``Path.glob`` gives it.

    ``fnmatch`` is deliberately not used: it lets ``*`` cross a path separator,
    so the root glob ``*.md`` would classify ``vendor/lib/notes.md`` as a
    top-level document. Classification has to agree with the glob that FOUND the
    file — a document a root finds and the classifier then puts in no space (or
    the reverse) is the check disagreeing with itself, and the disagreement is
    invisible in every count it produces.

    ``**/`` matches zero or more segments, ``*`` and ``?`` stop at a separator.
    """
    out = ["(?s:"]
    i = 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:[^/]+/)*")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    out.append(r")\Z")
    return re.compile("".join(out))


def path_matches(posix: str, pattern: str) -> bool:
    """Whether a project-relative POSIX path is matched by a root glob."""
    return _pattern_regex(pattern).match(posix) is not None


#: Returned when configuration is absent or unreadable — the shipped defaults.
def default_doc_spaces() -> DocSpaces:
    """The shipped spaces, for a project that configures nothing."""
    return DocSpaces(
        roots=dict(DEFAULT_ROOTS),
        kinds=dict(DEFAULT_KINDS),
        working=WorkingExemption(
            exempt_from_freshness=True, reason=DEFAULT_WORKING_REASON, declared=False
        ),
    )


def resolve_doc_spaces(project_root: Path) -> DocSpaces:
    """Read ``doc_roots`` from ``.beadloom/config.yml``, falling back to defaults.

    Configuration errors are **carried, not raised**. A malformed block would
    otherwise turn one bad line into a crashing gate that names the wrong file;
    every error here is reported by name in the spaces report instead.
    """
    import yaml

    config_path = project_root / ".beadloom" / "config.yml"
    if not config_path.is_file():
        return default_doc_spaces()
    try:
        data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        return _with_errors(f"{CONFIG_KEY}: config.yml is unreadable: {exc}")
    block = data.get(CONFIG_KEY) if isinstance(data, dict) else None
    if block is None:
        return default_doc_spaces()
    if not isinstance(block, dict):
        return _with_errors(
            f"{CONFIG_KEY}: expected a mapping of space -> settings, "
            f"got {type(block).__name__}"
        )
    return _from_block(block)


def _with_errors(*errors: str) -> DocSpaces:
    """The shipped spaces, carrying the configuration errors that were found."""
    base = default_doc_spaces()
    return DocSpaces(
        roots=base.roots,
        kinds=base.kinds,
        working=base.working,
        config_errors=tuple(errors),
    )


def _from_block(block: dict[str, object]) -> DocSpaces:
    """Build the spaces from a ``doc_roots`` mapping, collecting every error."""
    roots: dict[str, tuple[str, ...]] = dict(DEFAULT_ROOTS)
    kinds: dict[str, tuple[str, ...]] = dict(DEFAULT_KINDS)
    errors: list[str] = []
    for space in SPACES:
        settings = block.get(space)
        if settings is None:
            continue
        if not isinstance(settings, dict):
            errors.append(
                f"{CONFIG_KEY}.{space}: expected a mapping with `roots` and "
                f"`kinds`, got {type(settings).__name__}"
            )
            continue
        declared_roots = _string_list(settings.get("roots"))
        if declared_roots is not None:
            roots[space] = declared_roots
        declared_kinds = _string_list(settings.get("kinds"))
        if declared_kinds is not None:
            kinds[space] = declared_kinds
    unknown = sorted(set(block) - set(SPACES))
    errors.extend(
        f"{CONFIG_KEY}.{name}: not a documentation space — "
        f"expected one of {', '.join(SPACES)}"
        for name in unknown
    )
    working, working_errors = _working_from(block.get(SPACE_WORKING))
    errors.extend(working_errors)
    return DocSpaces(
        roots=roots, kinds=kinds, working=working, config_errors=tuple(errors)
    )


def _working_from(settings: object) -> tuple[WorkingExemption, list[str]]:
    """The WORKING exemption a project declared, and what was wrong with it.

    An exemption declared without a reason is a **config error**, the shape every
    other exclusion in this codebase carries: an unnamed exclusion is how a gate
    is quietly switched off. The exemption still applies while the error stands,
    because refusing to apply it would make the remedy for a missing reason a
    wave of stale documents.
    """
    default = default_doc_spaces().working
    if not isinstance(settings, dict):
        return default, []
    if "exempt_from_freshness" not in settings:
        return default, []
    exempt = settings.get("exempt_from_freshness")
    if not isinstance(exempt, bool):
        return default, [
            f"{CONFIG_KEY}.{SPACE_WORKING}.exempt_from_freshness: expected true "
            f"or false, got {type(exempt).__name__}"
        ]
    reason = settings.get("reason")
    if exempt and not (isinstance(reason, str) and reason.strip()):
        return WorkingExemption(
            exempt_from_freshness=True, reason="", declared=True
        ), [
            f"{CONFIG_KEY}.{SPACE_WORKING}.reason: an exemption without a stated "
            f"reason is how a gate is switched off without saying so"
        ]
    return (
        WorkingExemption(
            exempt_from_freshness=exempt,
            reason=reason.strip() if isinstance(reason, str) else "",
            declared=True,
        ),
        [],
    )


def _string_list(value: object) -> tuple[str, ...] | None:
    """*value* as a tuple of strings, or ``None`` when it is not a list of them.

    An empty list is a DECLARATION that the space has none, and is kept as such;
    ``None`` means the project said nothing and the default applies.
    """
    if isinstance(value, str):
        return (value,)
    if isinstance(value, list) and all(isinstance(v, str) for v in value):
        return tuple(value)
    return None
