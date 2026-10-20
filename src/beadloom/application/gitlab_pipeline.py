# beadloom:domain=application
# beadloom:component=verdict-room
"""A GitLab pipeline read into the jobs it declares: each job's image and its commands.

BDL-083 S2a (RFC D6, BDL-UX #332). The room census and the gate's coverage report read a
project's legs out of ``.github/workflows`` and nothing else, so a GitLab project declared no
leg at all and ``ci`` printed ``0 of 0 declared room(s)``. This module is the GitLab half of
"where a project declares its legs"; the rooms are made from it by
:mod:`beadloom.application.rooms`, and the verifications by
:mod:`beadloom.application.gate_coverage`, so one file has one reader.

**What it does not follow, it names.** ``include:`` pulls jobs from other files, ``extends:``
merges a template into a job, and ``parallel: matrix`` multiplies a job into several. None is
expanded here; each becomes a note beside what was read, because a pipeline read in part and
reported as read in full is the clean list this project refuses to hand back.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

#: Where GitLab reads a project's pipeline from, relative to the project root.
GITLAB_CI_FILE = ".gitlab-ci.yml"

#: Top-level keys that configure the pipeline rather than naming a job (GitLab's
#: "global keywords"). Every other mapping whose name does not start with a dot is a job.
_GLOBAL_KEYWORDS = frozenset(
    {
        "stages",
        "variables",
        "workflow",
        "default",
        "include",
        "image",
        "services",
        "before_script",
        "after_script",
        "cache",
        "types",
        "spec",
    }
)

#: The script sections of a job, in the order a runner executes them.
_SCRIPT_KEYS = ("before_script", "script", "after_script")

#: The sections a job inherits from ``default:`` (or the top level) when it declares none.
_INHERITED_KEYS = ("image", "before_script", "after_script")

#: ``python:3.12-slim``, ``docker.io/library/python:3.10.14`` -- the official image's tag
#: names the interpreter. A tag naming no minor version names none.
_PYTHON_IMAGE_RE = re.compile(r"^(?:[^\s$]*/)?python:(\d+\.\d+)(?:[.\-][^\s]*)?$")


@dataclass(frozen=True)
class GitlabJob:
    """One job of a GitLab pipeline: its name, its image, and the commands it runs.

    ``image`` is ``None`` when neither the job nor the pipeline's default names one, which is
    a runner whose platform the file does not declare. ``notes`` names what the reader saw on
    this job and did not follow.
    """

    name: str
    image: str | None
    commands: tuple[str, ...]
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class GitlabPipeline:
    """The jobs a ``.gitlab-ci.yml`` declares, and what the file pulls in from elsewhere."""

    jobs: tuple[GitlabJob, ...]
    notes: tuple[str, ...] = ()


def load_gitlab_pipeline(path: Path) -> tuple[GitlabPipeline | None, str | None]:
    """The pipeline *path* declares, or the reason it could not be read.

    The failure sentences are the GitHub reader's
    (:func:`beadloom.application.rooms.load_jobs`), so "this pipeline could not be parsed"
    reads the same whichever host's file it was.
    """
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        return None, f"the pipeline could not be parsed ({type(exc).__name__})"
    if not isinstance(document, dict):
        return None, "the pipeline is not a mapping, so it declares no jobs"
    defaults = _defaults_of(document)
    jobs = tuple(
        _job(str(name), body, defaults) for name, body in document.items() if _is_job(name, body)
    )
    notes: tuple[str, ...] = ()
    if "include" in document:
        notes = (
            "the pipeline carries `include:`, which this report does not follow, so the "
            "jobs it pulls in from other files are not among the legs reported here",
        )
    return GitlabPipeline(jobs=jobs, notes=notes), None


def python_of_image(image: str) -> str | None:
    """The ``X.Y`` interpreter an official ``python`` image's tag names, or ``None``.

    Only the official image is read: a tag naming no minor version, an image of another
    name, or one spelled through a variable names no interpreter this report can state.
    """
    match = _PYTHON_IMAGE_RE.match(image.strip())
    return match.group(1) if match else None


def _is_job(name: object, body: object) -> bool:
    """A top-level mapping that is neither a global keyword nor a hidden template."""
    if not isinstance(name, str) or not isinstance(body, dict):
        return False
    return name not in _GLOBAL_KEYWORDS and not name.startswith(".")


def _defaults_of(document: Mapping[str, Any]) -> dict[str, Any]:
    """What a job inherits: ``default:``'s sections, else the top-level ones."""
    default = document.get("default")
    declared = default if isinstance(default, dict) else {}
    return {
        key: declared[key] if key in declared else document.get(key)
        for key in _INHERITED_KEYS
        if key in declared or key in document
    }


def _job(name: str, body: Mapping[str, Any], defaults: Mapping[str, Any]) -> GitlabJob:
    """One job, its inherited sections filled in, and what was not followed named."""
    merged = {**defaults, **body}
    return GitlabJob(
        name=name,
        image=_image_name(merged.get("image")),
        commands=tuple(command for key in _SCRIPT_KEYS for command in _lines(merged.get(key))),
        notes=_job_notes(body),
    )


def _image_name(value: object) -> str | None:
    """``image: python:3.12`` or ``image: {name: python:3.12}``, as the name alone."""
    if isinstance(value, dict):
        value = value.get("name")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _lines(value: object) -> list[str]:
    """A script section as its command lines: one string, or a list of them."""
    if isinstance(value, str):
        return [line for line in value.splitlines() if line.strip()]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str) and item.strip()]
    return []


def _job_notes(body: Mapping[str, Any]) -> tuple[str, ...]:
    """What this job declares that the reader does not expand."""
    notes: list[str] = []
    if "extends" in body:
        notes.append(
            "the job carries `extends:`, which this report does not merge, so an image or "
            "a script it takes from the template is not read"
        )
    parallel = body.get("parallel")
    if isinstance(parallel, dict) and "matrix" in parallel:
        notes.append(
            "the job carries `parallel: matrix`, which this report does not expand, so the "
            "real set of legs is wider than the one room reported here"
        )
    return tuple(notes)
