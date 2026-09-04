# beadloom:domain=onboarding
# beadloom:feature=flow-composer
"""``compose(core, architecture, stack, project)`` — one assembly for every flow artifact.

BDL-052 S3 composed *roles* from three shipped layers. BDL-061 S3 generalises
that in two directions at once:

* **every** flow artifact composes — the role files, the slash commands, and
  ``CLAUDE.md`` itself, which until now was a byte-snapshot of Beadloom's own
  live file (BDL-UX #177);
* a fourth, **project** layer is appended from ``.beadloom/flow/<kind>/``, so an
  adopter has a supported place for their own standing practices instead of
  hand-editing a drift-guarded file (BDL-UX #139, #152).

Layer order is fixed and deterministic — ``core``, the one ``architecture``
overlay, each ``stack`` overlay sorted, then the project fragment — so the same
inputs always yield the same bytes. That determinism is what lets
``config-check`` verify the **composition result** rather than file bytes: a
project extension is *part of* the expected output, while a change to the
shipped core still differs from it and is reported.

Overlays are append-only. Nothing in this module can remove core text; the only
way to disable a core rule is a declared suppression (see
:mod:`beadloom.onboarding.flow_suppression`), which is appended as a visible
notice rather than applied as a deletion.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from beadloom.onboarding.flow_config import (
    DEFAULT_LANGUAGE,
    FlowConfigError,
)
from beadloom.onboarding.flow_suppression import render_suppression_notice

if TYPE_CHECKING:
    from beadloom.onboarding.flow_config import FlowConfig

#: Project-relative root of the project layer (Q1 — flow *configuration* in
#: Beadloom's schema, which dies with the tool, unlike documentation).
PROJECT_FLOW_DIRNAME = Path(".beadloom") / "flow"


def templates_dir() -> Path:
    """Package directory holding every shipped template layer."""
    return Path(__file__).resolve().parent / "templates"


@dataclass(frozen=True)
class ArtifactKind:
    """Where the four layers of one artifact kind live.

    ``core_dir`` holds the shipped CORE fragment; ``overlay_root`` holds the
    ``architecture/<name>/`` and ``stack/<name>/`` subdirectories. The two are
    separate because the role templates already ship as
    ``roles/{core,architecture,stack}/`` while the commands and ``CLAUDE.md``
    keep their vendored location as the core and gain overlay roots beside it —
    a move would have churned the whole scaffold for no signal.
    """

    name: str
    core_dir: Path
    overlay_root: Path
    #: Whether a declared flow suppression is appended to this artifact. A
    #: suppression stands down a rule addressed to an AGENT; a generated
    #: document has no rules to stand down, so appending the notice would
    #: publish flow configuration as documentation (BDL-061 S4b).
    carries_suppressions: bool = True
    #: CORE fragments every artifact of this kind carries in addition to its own,
    #: composed straight after it. One text, one file, four consumers — the
    #: alternative is a copy per role, which drifts the moment one is edited
    #: (BDL-061 S4: the writing standard used to live inside `tech-writer`, so the
    #: three roles that produce the TO-BE documents were held to no standard).
    shared: tuple[str, ...] = ()


def _artifact_kinds() -> dict[str, ArtifactKind]:
    root = templates_dir()
    return {
        "roles": ArtifactKind(
            "roles",
            root / "roles" / "core",
            root / "roles",
            shared=SHARED_ROLE_FRAGMENTS,
        ),
        "commands": ArtifactKind(
            "commands", root / "agentic_flow" / "commands", root / "commands"
        ),
        "claude": ArtifactKind("claude", root / "agentic_flow", root / "claude"),
        "docs": ArtifactKind(
            "docs",
            root / "docs" / "core",
            root / "docs",
            carries_suppressions=False,
        ),
    }


#: CORE fragments shared by every role. Named here, next to the composition that
#: reads them, because a LAYER is not a role: it has no front matter, is never
#: written as an adapter, and ``compose_role`` refuses it.
#:
#: ``_writing`` holds the standard every role that writes a document is held to;
#: ``_rooms`` holds the one every role that reports a MEASUREMENT is held to;
#: ``_landing`` holds what the merge slot grants and what it does not, for every
#: role that lands a commit in a tree it shares. All three are shared for the
#: same reason: five copies of one rule drift the moment one of them is edited.
SHARED_ROLE_FRAGMENTS: tuple[str, ...] = ("_writing", "_rooms", "_landing")

#: The artifact kinds ``compose`` understands.
ARTIFACT_KINDS: tuple[str, ...] = ("roles", "commands", "claude", "docs")

#: Fragment name of the composed ``CLAUDE.md`` (its core is the vendored asset).
CLAUDE_ARTIFACT_NAME = "CLAUDE"

#: Provenance stamp carried by the shipped ``CLAUDE.md`` core. Its presence is
#: what tells ``config-check`` the body is Beadloom's to verify: a project whose
#: ``CLAUDE.md`` was written by hand and never scaffolded is not ours to police,
#: the same boundary ``_is_beadloom_adapter`` draws for IDE adapter files.
COMPOSED_MARKER = "<!-- beadloom:composed"


@dataclass(frozen=True)
class LayerFragment:
    """One layer's contribution to a composition.

    ``layer`` is the stable label a report shows (``core``,
    ``architecture:ddd``, ``stack:python``, ``project``); ``source`` is the path
    it was read from, so a reader can go and look.
    """

    layer: str
    source: str
    text: str


@dataclass(frozen=True)
class Composition:
    """The result of composing one artifact from its four layers.

    ``notes`` carries the honest skips — a requested localisation with no
    shipped fragment, for instance. A layer that contributed nothing is simply
    absent from ``fragments``; a layer that could not do what was asked says so
    in ``notes`` rather than passing silently (S1's ``skip`` discipline).
    """

    kind: str
    name: str
    fragments: tuple[LayerFragment, ...]
    notes: tuple[str, ...] = ()
    suppression_notice: str = ""

    @property
    def text(self) -> str:
        """The composed artifact body."""
        return "".join(f.text for f in self.fragments) + self.suppression_notice


def _read_layer(
    directory: Path,
    name: str,
    *,
    language: str,
    layer: str,
    notes: list[str],
) -> LayerFragment | None:
    """Read one layer fragment, preferring a ``<name>.<lang>.md.txt`` localisation.

    A missing fragment is legitimate (the overlay does not refine this
    artifact) and contributes nothing. A missing *localisation* is different:
    the composition falls back to the default language and records WHY in
    ``notes``, so a Russian-speaking team is never silently handed English
    without being told (BDL-UX #136).
    """
    localized = directory / f"{name}.{language}.md.txt"
    default = directory / f"{name}.md.txt"
    if language != DEFAULT_LANGUAGE and localized.is_file():
        return LayerFragment(layer, str(localized), localized.read_text(encoding="utf-8"))
    if not default.is_file():
        return None
    if language != DEFAULT_LANGUAGE:
        notes.append(
            f"{layer}: no {language!r} fragment for {name!r} — "
            f"{DEFAULT_LANGUAGE!r} used; supply one at "
            f"{PROJECT_FLOW_DIRNAME}/<kind>/{name}.md to localise it"
        )
    return LayerFragment(layer, str(default), default.read_text(encoding="utf-8"))


def project_fragment_path(kind: str, name: str, project_root: Path) -> Path:
    """Absolute path of the project layer's fragment for ``kind``/``name``."""
    return project_root / PROJECT_FLOW_DIRNAME / kind / f"{name}.md"


def _project_layer(kind: str, name: str, project_root: Path | None) -> LayerFragment | None:
    if project_root is None:
        return None
    path = project_fragment_path(kind, name, project_root)
    if not path.is_file():
        return None
    return LayerFragment(
        "project",
        str(path.relative_to(project_root)),
        path.read_text(encoding="utf-8"),
    )


def compose(
    kind: str,
    name: str,
    *,
    config: FlowConfig,
    project_root: Path | None = None,
) -> Composition:
    """Compose one flow artifact from CORE + architecture + stack + project.

    Raises :class:`FlowConfigError` for an unknown ``kind`` or a missing CORE
    fragment — a bad compose request is loud rather than a silently-empty file.
    ``project_root`` is optional so a composition can be computed for a config
    alone (the drift baseline for a repo that has no project layer).
    """
    kinds = _artifact_kinds()
    if kind not in kinds:
        msg = f"compose: unknown artifact kind {kind!r} — allowed: {list(ARTIFACT_KINDS)}"
        raise FlowConfigError(msg)
    spec = kinds[kind]
    language = config.language
    notes: list[str] = []

    core = _read_layer(
        spec.core_dir, name, language=language, layer="core", notes=notes
    )
    if core is None:
        msg = (
            f"compose: missing CORE fragment for {kind}/{name!r} at "
            f"{spec.core_dir / f'{name}.md.txt'}"
        )
        raise FlowConfigError(msg)

    fragments = [core]
    for shared_name in spec.shared:
        shared = _read_layer(
            spec.core_dir,
            shared_name,
            language=language,
            layer=f"core:{shared_name}",
            notes=notes,
        )
        if shared is not None:
            fragments.append(shared)
    arch = _read_layer(
        spec.overlay_root / "architecture" / config.architecture,
        name,
        language=language,
        layer=f"architecture:{config.architecture}",
        notes=notes,
    )
    if arch is not None:
        fragments.append(arch)
    for stack_name in sorted(config.stack):
        overlay = _read_layer(
            spec.overlay_root / "stack" / stack_name,
            name,
            language=language,
            layer=f"stack:{stack_name}",
            notes=notes,
        )
        if overlay is not None:
            fragments.append(overlay)
    project = _project_layer(kind, name, project_root)
    if project is not None:
        fragments.append(project)

    return Composition(
        kind=kind,
        name=name,
        fragments=tuple(fragments),
        notes=tuple(notes),
        suppression_notice=(
            render_suppression_notice(config.suppressions)
            if spec.carries_suppressions
            else ""
        ),
    )
