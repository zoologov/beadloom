# beadloom:domain=onboarding
# beadloom:feature=doc-templates
"""The shape of a generated document: its template, its values, its sections.

Until BDL-061 S4b every doc skeleton was an f-string inside
:mod:`beadloom.onboarding.doc_generator`. Two consequences, and both are the
reason this module exists: an adopter had **nothing to adapt** — the shape of
their architecture documentation was a Python literal in our package — and
**nothing held the shape after generation**, so a document could lose the
sections it was born with and no check could tell.

The templates are package data under ``templates/docs/`` and compose through
:func:`beadloom.onboarding.composer.compose` — the same
``core → architecture → stack → project`` assembly S3 built for the role files.
Reusing it rather than inventing a second mechanism is what makes a project
layer (``.beadloom/flow/docs/<kind>.md``) work for documents on the day it
shipped for roles.

**Required sections are derived, never declared twice.** A section is required
because the composed template carries it as a literal ``## `` heading, so a
project fragment that appends ``## Runbook`` makes ``Runbook`` required by the
same act. A section that reaches the document through a placeholder (``## Public
API``, rendered only for a node that has public symbols) is conditional by
construction and cannot be required of a node that has none.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from beadloom.onboarding.composer import compose
from beadloom.onboarding.flow_config import (
    FlowConfig,
    FlowConfigError,
    load_flow_config_or_default,
)

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

#: The ``compose`` artifact kind these templates live under.
DOC_ARTIFACT_KIND = "docs"

#: ``{{name}}`` — deliberately NOT ``str.format``'s single brace: a generated
#: document carries Mermaid, JSON and shell fragments, and a lone ``{`` in any
#: of them would raise from the formatter or be silently eaten.
_PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-z_][a-z0-9_]*)\s*\}\}")

_HEADING_RE = re.compile(r"^## +(.+?)\s*$", re.MULTILINE)


class DocTemplateError(FlowConfigError):
    """A doc template that cannot be rendered: unknown kind or missing value.

    Subclasses :class:`FlowConfigError` so a caller that already handles a bad
    composition handles a bad render too — both mean "the shipped shape and the
    request disagree", and both are loud rather than a half-written file.
    """


@dataclass(frozen=True)
class DocKind:
    """One kind of generated document.

    Attributes
    ----------
    name:
        Template name under ``templates/docs/core/``.
    node_kind:
        Graph node kind this document is generated for, or ``None`` when the
        document describes the project rather than a node (the architecture
        overview and the ``.beadloom`` README). Only a document bound to a node
        kind can be checked for its sections — the others have no pair to check.
    """

    name: str
    node_kind: str | None = None


#: Every document ``beadloom docs generate`` writes, in generation order.
DOC_KINDS: tuple[DocKind, ...] = (
    DocKind("overview"),
    DocKind("domain", node_kind="domain"),
    DocKind("service", node_kind="service"),
    DocKind("feature", node_kind="feature"),
    DocKind("beadloom-readme"),
)

#: Graph node kind -> doc kind, for the checks that read a document back.
DOC_KIND_FOR_NODE_KIND: dict[str, str] = {
    kind.node_kind: kind.name for kind in DOC_KINDS if kind.node_kind is not None
}

_KNOWN_NAMES = frozenset(kind.name for kind in DOC_KINDS)


def doc_template(
    name: str,
    *,
    config: FlowConfig,
    project_root: Path | None = None,
) -> str:
    """The composed template text for doc kind *name*."""
    if name not in _KNOWN_NAMES:
        msg = (
            f"doc template: unknown kind {name!r} — "
            f"allowed: {sorted(_KNOWN_NAMES)}"
        )
        raise DocTemplateError(msg)
    return compose(
        DOC_ARTIFACT_KIND, name, config=config, project_root=project_root
    ).text


def render_doc(
    name: str,
    values: Mapping[str, str],
    *,
    config: FlowConfig,
    project_root: Path | None = None,
) -> str:
    """Render doc kind *name* by substituting ``{{placeholder}}`` from *values*.

    A placeholder with no value raises rather than substituting an empty
    string: a silently-empty substitution is how a document ships half-written,
    and the placeholder checks in :mod:`beadloom.doc_sync.doc_quality` exist
    because that has happened. A value the template does not use is allowed —
    an overlay is free to drop a fact it has no place for.
    """
    template = doc_template(name, config=config, project_root=project_root)
    missing: list[str] = []

    def _substitute(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in values:
            missing.append(key)
            return match.group(0)
        return values[key]

    rendered = _PLACEHOLDER_RE.sub(_substitute, template)
    if missing:
        msg = (
            f"doc template {name!r}: no value for "
            f"{', '.join(sorted(set(missing)))}"
        )
        raise DocTemplateError(msg)
    return rendered


def required_sections(
    name: str,
    *,
    config: FlowConfig,
    project_root: Path | None = None,
) -> tuple[str, ...]:
    """Section titles the composed template of *name* carries, in order."""
    template = doc_template(name, config=config, project_root=project_root)
    # Placeholders are erased first, for two reasons that point the same way: a
    # heading that arrives THROUGH a placeholder is conditional and must not be
    # required, and a heading the template writes right after one
    # (``{{symbols_section}}## Dependencies``) is unconditional and must be.
    skeleton = _PLACEHOLDER_RE.sub("", template)
    seen: list[str] = []
    for match in _HEADING_RE.finditer(skeleton):
        title = match.group(1)
        if title not in seen:
            seen.append(title)
    return tuple(seen)


def required_sections_by_node_kind(
    *,
    config: FlowConfig,
    project_root: Path | None = None,
) -> dict[str, tuple[str, ...]]:
    """Required sections keyed by GRAPH node kind, for the doc-shape check.

    This is the whole payload :mod:`beadloom.doc_sync.doc_shape` needs, which is
    why it is computed here and passed in: ``doc_sync`` is a peer domain and
    must not import ``onboarding`` to reach a template.
    """
    return {
        node_kind: required_sections(
            doc_kind, config=config, project_root=project_root
        )
        for node_kind, doc_kind in DOC_KIND_FOR_NODE_KIND.items()
    }


#: The selection a project that has not (yet) recorded one is composed from.
#: Beadloom's own defaults, and stated here rather than inlined at each call
#: site so a generator, a checker and a test cannot disagree about what an
#: unconfigured project's documents are supposed to look like.
DEFAULT_DOC_CONFIG = FlowConfig(
    tools=("claude",), architecture="ddd", stack=("python",)
)


def doc_flow_config(project_root: Path) -> FlowConfig:
    """The flow config the project's documents compose from.

    Falls back to :data:`DEFAULT_DOC_CONFIG` when the project records no
    ``.beadloom/flow.yml`` — generating documentation must not require the
    agentic flow to be scaffolded. A *malformed* config still raises; that is
    ``config-check``'s signal and silencing it here would hide it.
    """
    return load_flow_config_or_default(project_root, default=DEFAULT_DOC_CONFIG)
