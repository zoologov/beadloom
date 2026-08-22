# beadloom:domain=application
# beadloom:feature=flow-guards
"""Locating the project a guard answers about, and writes its record to (BDL-061.29).

The shipped hook adapter is ``exec beadloom guard "$1" --hook claude-code`` — no
``--project`` — so the root was ``Path.cwd()``, i.e. wherever the harness
happened to have chdir'd. Measured from ``<root>/src/beadloom`` in a project
whose ``flow.yml`` declares ``block``: the declared strictness was gone (block →
the shipped default ``warn``, exit 1, non-blocking), every declared exclusion
was gone with it, and the firing was written to a **new** ``src/beadloom/
.beadloom/`` that ``--liveness`` at the real root never reads. The report showed
the guard as never having fired *after a real evaluation had happened*, so a
record in the wrong place was indistinguishable from no record — and the next
invocation from that directory would find the manufactured marker and treat the
subdirectory as the project, which makes the failure self-entrenching rather
than one-shot.

**The decision: walk up from the working directory to the nearest ancestor that
contains ``.beadloom/``.** The alternative — refuse to run outside a project
root, which is consistent with ``.27``'s narrow-the-input philosophy — was
rejected on what each failure costs. Refusing turns an agent that merely changed
directory into an agent that cannot edit anything, for a reason it cannot fix
from inside the harness; and it does not even remove the "cannot locate the
project" path, it only makes it the common case. Walking up is also not the kind
of guess ``.27`` removed: that was about repairing a *model-supplied string*,
where every normalisation is a bet on what the harness will write. A directory
tree is not model-supplied, ``.beadloom/`` is unambiguous evidence rather than
an inference, and there is exactly one nearest ancestor carrying it.

**The marker is ``.beadloom/``** and not ``.git/``: it is the directory the
guard's own configuration (``flow.yml``) and its own record live in, so the
directory that answers "where does this firing belong" is the same one that
answers "which flow.yml governs this edit". ``.git/`` nests (submodules,
worktrees) and would name a root Beadloom knows nothing about.

**An explicit ``--project`` is honoured verbatim** — no walking up. The caller
has stated where the project is, and searching past that statement would make an
explicit argument mean something other than what it says. It must name an
existing directory; anything else is "the project could not be located", which
is the same refusal as the discovery failure and not a separate spelling of it.

What is deliberately NOT done: manufacturing a root. A guard that cannot find a
project answers ``error`` (which blocks) and writes nothing — it does not create
``.beadloom/`` where it stands. A silent ``skip`` at exit 0 was the shape of this
defect, and creating the directory was its self-entrenching half.

The residual, named rather than implied: a **nested** ``.beadloom/`` — a fixture
project checked into a tree, say — makes the inner directory the root for every
invocation beneath it. That is what a nested project *is*, and the verdict names
the root it used, so the reading is at least visible.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

#: The directory whose presence marks a project root.
PROJECT_MARKER = Path(".beadloom")

#: Refusal when no ancestor of the working directory carries the marker.
NO_PROJECT_FOUND = (
    "no Beadloom project was found at {start} or in any directory above it "
    "(looked for {marker}/), so there is no flow.yml to read and no firing "
    "record to write"
)

#: Refusal when ``--project`` names something that is not a directory.
DECLARED_PROJECT_MISSING = (
    "the project directory named by --project does not exist: {declared}"
)

#: Refusal when the working directory itself cannot be read.
UNREADABLE_START = "the working directory could not be read ({detail})"


@dataclass(frozen=True)
class ProjectLocation:
    """Where the project is — or why the guard could not tell.

    ``root`` is ``None`` exactly when ``refusal`` is non-empty; the two are kept
    on one object so a caller cannot handle the success and forget the failure.
    """

    root: Path | None = None
    declared: bool = False
    refusal: str = ""


def locate_project_root(
    *, declared: Path | None = None, start: Path | None = None
) -> ProjectLocation:
    """Locate the project root, from *declared* if given, else by walking up from *start*.

    Never raises for an ordinary "it is not there": that is a
    :class:`ProjectLocation` carrying a refusal, because the caller has to turn
    it into a verdict either way.
    """
    if declared is not None:
        if declared.is_dir():
            return ProjectLocation(root=declared, declared=True)
        return ProjectLocation(
            refusal=DECLARED_PROJECT_MISSING.format(declared=declared)
        )
    try:
        origin = (start or Path.cwd()).resolve()
    except OSError as exc:
        return ProjectLocation(refusal=UNREADABLE_START.format(detail=exc))
    for candidate in (origin, *origin.parents):
        if (candidate / PROJECT_MARKER).is_dir():
            return ProjectLocation(root=candidate)
    return ProjectLocation(
        refusal=NO_PROJECT_FOUND.format(start=origin, marker=PROJECT_MARKER.as_posix())
    )
