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

#: The order roots are consulted in when two of them name one file. WORKING
#: first, and that is the whole rule: its shipped root list is empty, so the only
#: way a document lands there by root is a project DECLARING it, while the AS-IS
#: default is the catch-all ``docs/**/*.md`` that claims everything under the
#: documentation tree. If the catch-all won, a declaration a project wrote in the
#: file we tell it to edit would be silently inert — which is the defect
#: `beadloom-mr2l.75` closes one layer up, where a declaration never reached the
#: reader that would object to it. A declaration wins, and the win is visible:
#: a document excused this way that the graph ALSO declares as a node's
#: documentation is reported as `working_declaration_contradicted`.
_ROOT_PRECEDENCE: tuple[str, ...] = (SPACE_WORKING, SPACE_TO_BE, SPACE_AS_IS)

#: ``.beadloom/config.yml`` key holding a project's own spaces.
CONFIG_KEY = "doc_roots"

#: ``.beadloom/config.yml`` key naming the directory ``sync-check`` pairs with
#: code. A ``sync_state`` row spells its document RELATIVE TO that directory, so
#: this key is what turns the indexer's spelling into the project-relative one
#: every root glob is written in.
DOCS_DIR_KEY = "docs_dir"

#: Where documentation lives when a project declares nothing.
DEFAULT_DOCS_DIR = "docs"

#: The documents an epic declares its related nodes in, most specific first.
#: Configuration rather than a constant, because every root around them is:
#: an adopter whose planning document is named otherwise would lose 100% of its
#: epics and read a plausible "0 of 0" (`beadloom-mr2l.73`). Declared under
#: ``doc_roots.to_be.intent_documents``, beside the kinds they are drawn from.
DEFAULT_INTENT_DOCUMENTS: tuple[str, ...] = ("CONTEXT.md", "BRIEF.md")

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
    docs_dir: str = DEFAULT_DOCS_DIR
    """Where documentation lives, project-relative — see :meth:`project_path`."""
    intent_documents: tuple[str, ...] = DEFAULT_INTENT_DOCUMENTS
    """File names an epic declares its related nodes in, most specific first."""

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
        for space in _ROOT_PRECEDENCE:
            if any(path_matches(posix, p) for p in self.roots.get(space, ())):
                return space
        return None

    def project_path(self, doc_path: str) -> str:
        """A ``sync_state`` document path in the ONE project-relative spelling.

        ``index_docs`` writes a document's path relative to the docs directory
        while every root glob is written relative to the project, so the two
        readers of one declaration held two strings for one file:
        ``guides/ci.md`` reached freshness and ``docs/guides/ci.md`` reached the
        report that exists to object. Kind hid it — a stem carries no prefix, so
        every shipped case agreed — and roots did not. Every caller holding a
        docs-dir-relative path passes it through here before asking.
        """
        posix = doc_path.replace("\\", "/").lstrip("/")
        prefix = self.docs_dir.strip("/")
        return f"{prefix}/{posix}" if prefix else posix

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
def default_doc_spaces(docs_dir: str = DEFAULT_DOCS_DIR) -> DocSpaces:
    """The shipped spaces, for a project that configures nothing."""
    return DocSpaces(
        roots=dict(DEFAULT_ROOTS),
        kinds=dict(DEFAULT_KINDS),
        working=WorkingExemption(
            exempt_from_freshness=True, reason=DEFAULT_WORKING_REASON, declared=False
        ),
        docs_dir=docs_dir,
        intent_documents=DEFAULT_INTENT_DOCUMENTS,
    )


def _read_config(project_root: Path) -> tuple[dict[str, object] | None, str | None]:
    """``.beadloom/config.yml`` as a mapping, and what was wrong with reading it.

    One parse for both facts this module answers — where the spaces are, and
    where the documentation directory is. Two parses are two chances to
    disagree, which is the defect class this module was just repaired for.
    """
    import yaml

    config_path = project_root / ".beadloom" / "config.yml"
    if not config_path.is_file():
        return None, None
    try:
        data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        return None, f"config.yml is unreadable: {exc}"
    return (data if isinstance(data, dict) else {}), None


def _docs_dir_from(data: Mapping[str, object] | None) -> str:
    """The documentation directory a config mapping declares, or the default."""
    value = data.get(DOCS_DIR_KEY) if data is not None else None
    if isinstance(value, str) and value.strip():
        return value.strip().replace("\\", "/").strip("/")
    return DEFAULT_DOCS_DIR


def resolve_docs_dir(project_root: Path) -> str:
    """The project-relative documentation directory, read from configuration.

    The single reader of ``docs_dir``. Three lived in the tree before this — the
    reindexer's, the reference-document scan's, and a hardcoded ``docs`` inside
    ``check_sync`` — so a project keeping its documentation elsewhere had one
    reader looking in a directory the others had left.
    """
    data, _ = _read_config(project_root)
    return _docs_dir_from(data)


def resolve_doc_spaces(project_root: Path) -> DocSpaces:
    """Read ``doc_roots`` from ``.beadloom/config.yml``, falling back to defaults.

    Configuration errors are **carried, not raised**. A malformed block would
    otherwise turn one bad line into a crashing gate that names the wrong file;
    every error here is reported by name in the spaces report instead.
    """
    data, error = _read_config(project_root)
    docs_dir = _docs_dir_from(data)
    if error is not None:
        return _with_errors(docs_dir, f"{CONFIG_KEY}: {error}")
    if data is None:
        return default_doc_spaces(docs_dir)
    block = data.get(CONFIG_KEY)
    if block is None:
        return default_doc_spaces(docs_dir)
    if not isinstance(block, dict):
        return _with_errors(
            docs_dir,
            f"{CONFIG_KEY}: expected a mapping of space -> settings, "
            f"got {type(block).__name__}",
        )
    return _from_block(block, docs_dir)


def _with_errors(docs_dir: str, *errors: str) -> DocSpaces:
    """The shipped spaces, carrying the configuration errors that were found."""
    base = default_doc_spaces(docs_dir)
    return DocSpaces(
        roots=base.roots,
        kinds=base.kinds,
        working=base.working,
        config_errors=tuple(errors),
        docs_dir=docs_dir,
        intent_documents=base.intent_documents,
    )


def _from_block(block: dict[str, object], docs_dir: str = DEFAULT_DOCS_DIR) -> DocSpaces:
    """Build the spaces from a ``doc_roots`` mapping, collecting every error."""
    roots: dict[str, tuple[str, ...]] = dict(DEFAULT_ROOTS)
    kinds: dict[str, tuple[str, ...]] = dict(DEFAULT_KINDS)
    intent_documents: tuple[str, ...] = DEFAULT_INTENT_DOCUMENTS
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
        if space == SPACE_TO_BE:
            declared_documents = _string_list(settings.get("intent_documents"))
            if declared_documents is not None:
                intent_documents = declared_documents
    unknown = sorted(set(block) - set(SPACES))
    errors.extend(
        f"{CONFIG_KEY}.{name}: not a documentation space — "
        f"expected one of {', '.join(SPACES)}"
        for name in unknown
    )
    working, working_errors = _working_from(block.get(SPACE_WORKING))
    errors.extend(working_errors)
    return DocSpaces(
        roots=roots,
        kinds=kinds,
        working=working,
        config_errors=tuple(errors),
        docs_dir=docs_dir,
        intent_documents=intent_documents,
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
