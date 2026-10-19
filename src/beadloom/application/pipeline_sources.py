# beadloom:domain=application
# beadloom:component=verdict-room
"""Which pipeline files a room census reads: every one present, or the ones the project names.

BDL-083 S2F1 (``beadloom-ba9w.22``), RFC D6 as amended on 2026-10-19. S2a read
``.github/workflows`` first and set ``.gitlab-ci.yml`` aside whenever both were in the tree,
which was a choice of forge the census made on the project's behalf and was right only for a
project whose GitLab file is a mirror. The choice is now the project's, declared in
``.beadloom/config.yml``::

    rooms:
      pipelines: [github]      # github and/or gitlab

**Unset, every pipeline file the tree holds is read**, each room carrying its source. Set,
the named ones only: a present file the key leaves out is set aside with the key named, and a
name with no file in the tree is a named line, never an error -- a declaration that outlives
its file is a fact for the room block, not a reason to fail a census.

**An unusable value is named, not obeyed or dropped in silence.** A name outside the
vocabulary is refused and the usable names are kept; a value that is not a list is refused and
the census reads as if the key were unset, which the refusal says.

One reader for the room census and the gate's coverage report, so the key governs both
(:mod:`beadloom.application.rooms`, :mod:`beadloom.application.gate_coverage`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from beadloom.application.gitlab_pipeline import GITLAB_CI_FILE
from beadloom.doc_sync.declarations import describe_value, mapping_of, read_declaration

#: Where a project declares its GitHub pipeline. Public because two derivations read one
#: declaration: the room census and the verifications a gate run did not perform.
WORKFLOW_DIR = Path(".github") / "workflows"

#: The key of ``.beadloom/config.yml`` this module reads, and the field under it.
ROOMS_KEY = "rooms"
PIPELINES_FIELD = "pipelines"
DECLARING_KEY = f"{ROOMS_KEY}.{PIPELINES_FIELD}"

#: The names ``rooms.pipelines`` accepts. A vocabulary of the pipelines this census reads.
GITHUB = "github"
GITLAB = "gitlab"
PIPELINE_NAMES: tuple[str, ...] = (GITHUB, GITLAB)

_CONFIG_RELATIVE = ".beadloom/config.yml"


@dataclass(frozen=True)
class PipelineNote:
    """A pipeline file the census did not read, or a declaration it could not use, and why."""

    source: str
    why: str


@dataclass(frozen=True)
class PipelineSources:
    """The pipeline files a census reads its legs from, and what it was told about the rest.

    ``set_aside`` names a present file the declaration leaves out, ``missing`` a name the
    declaration gives with no file in the tree, and ``refused`` a value it could not use.
    """

    workflows: tuple[Path, ...] = ()
    gitlab: Path | None = None
    set_aside: tuple[PipelineNote, ...] = ()
    missing: tuple[PipelineNote, ...] = ()
    refused: tuple[PipelineNote, ...] = ()

    @property
    def declared(self) -> bool:
        """Whether the census reads at least one pipeline file."""
        return bool(self.workflows) or self.gitlab is not None

    @property
    def notes(self) -> tuple[PipelineNote, ...]:
        """Every line the room block carries about the pipeline files, in a stable order."""
        return self.refused + self.missing + self.set_aside


def pipeline_sources(project_root: Path) -> PipelineSources:
    """The pipeline files *project_root*'s legs are read from, chosen once for every reader."""
    workflows = tuple(
        sorted(p for p in (project_root / WORKFLOW_DIR).glob("*.y*ml") if p.is_file())
    )
    gitlab_path = project_root / GITLAB_CI_FILE
    gitlab = gitlab_path if gitlab_path.is_file() else None
    named, refused = declared_pipelines(project_root)
    if named is None:
        return PipelineSources(workflows=workflows, gitlab=gitlab, refused=refused)
    set_aside: list[PipelineNote] = []
    missing: list[PipelineNote] = []
    present = {GITHUB: bool(workflows), GITLAB: gitlab is not None}
    for name in PIPELINE_NAMES:
        if name in named and not present[name]:
            missing.append(_missing(name))
        elif name not in named and present[name]:
            set_aside.append(_set_aside(name, named))
    return PipelineSources(
        workflows=workflows if GITHUB in named else (),
        gitlab=gitlab if GITLAB in named else None,
        set_aside=tuple(set_aside),
        missing=tuple(missing),
        refused=refused,
    )


def declared_pipelines(
    project_root: Path,
) -> tuple[frozenset[str] | None, tuple[PipelineNote, ...]]:
    """The pipelines ``rooms.pipelines`` names, ``None`` when it names none, and every refusal.

    ``None`` means "read every file present": the key is unset, or its value is unusable. An
    empty set is a declaration that names no pipeline, and reads none.
    """
    declaration = read_declaration(project_root, ROOMS_KEY)
    if not declaration.present:
        return None, tuple(_refused(r.where, r.why) for r in declaration.refusals)
    block, refusals = mapping_of(declaration, f"the key `{PIPELINES_FIELD}:`")
    if block is None:
        return None, tuple(_refused(r.where, r.why) for r in refusals)
    notes = [
        _refused(
            f"{ROOMS_KEY}.{key}",
            f"`{key}:` is not a key of `{ROOMS_KEY}:`; the block reads `{PIPELINES_FIELD}:`",
        )
        for key in map(str, block)
        if key != PIPELINES_FIELD
    ]
    if PIPELINES_FIELD not in block:
        return None, tuple(notes)
    value = block[PIPELINES_FIELD]
    if not isinstance(value, list):
        notes.append(
            _refused(
                DECLARING_KEY,
                f"`{PIPELINES_FIELD}:` is {describe_value(value)}, not a list of "
                f"{_vocabulary()}, so every pipeline file present is read",
            )
        )
        return None, tuple(notes)
    named: set[str] = set()
    for index, entry in enumerate(value):
        name = entry.strip().lower() if isinstance(entry, str) else None
        if name in PIPELINE_NAMES:
            named.add(name)
            continue
        shown = f"`{entry}`" if isinstance(entry, str) else describe_value(entry)
        notes.append(
            _refused(
                f"{DECLARING_KEY}[{index}]",
                f"the entry is {shown}, not one of {_vocabulary()}, so it names no "
                "pipeline this census reads",
            )
        )
    return frozenset(named), tuple(notes)


def _vocabulary() -> str:
    return " or ".join(f"`{name}`" for name in PIPELINE_NAMES)


def _location(name: str) -> str:
    """The file or folder a pipeline name stands for, as a room's source spells it."""
    return WORKFLOW_DIR.as_posix() if name == GITHUB else GITLAB_CI_FILE


def _missing(name: str) -> PipelineNote:
    held = f"`{WORKFLOW_DIR.as_posix()}/*.yml`" if name == GITHUB else f"`{GITLAB_CI_FILE}`"
    return PipelineNote(
        source=_location(name),
        why=(
            f"`{DECLARING_KEY}` names `{name}`, and the tree holds no {held}, so no leg is "
            "read from it"
        ),
    )


def _set_aside(name: str, named: frozenset[str]) -> PipelineNote:
    declared = ", ".join(f"`{n}`" for n in PIPELINE_NAMES if n in named) or "no pipeline"
    return PipelineNote(
        source=_location(name),
        why=(
            f"not read: `{DECLARING_KEY}` names {declared}, so the jobs declared here are "
            "not among the legs reported"
        ),
    )


def _refused(where: str, why: str) -> PipelineNote:
    return PipelineNote(source=_CONFIG_RELATIVE, why=f"{where}: {why}")
