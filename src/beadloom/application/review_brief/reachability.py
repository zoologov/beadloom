"""Derive what can reach the reviewer, channel by channel.

One responsibility: answer "what can this reviewer reach about this change", and
name a channel that could not be inspected instead of leaving it out.

**Every channel is DERIVED, and that is the whole of the design.** A hand-written
list of documents satisfies every test and goes stale the first time a role file
gains one, which is the shape this epic exists to remove:

* the documents a role prompt may name come from the composed prompts
  themselves — :data:`beadloom.onboarding.role_composer.ROLE_NAMES` (itself
  derived from the shipped CORE fragments) and every command fragment that
  ships, each composed for THIS project's ``flow.yml`` and including its project
  layer. A team that names its own document in ``.beadloom/flow/roles/review.md``
  moves this report by that act and by no other;
* the work item whose folder those documents live in comes from
  :func:`beadloom.application.declared_scope.work_item_of_branch`, whose folder
  population is the project's own planning corpus rather than this repository's
  convention;
* the commit range comes from the review's own base ref, which the brief already
  carries because the change inventory is measured over it.

**It raises detectability and closes nothing.** BDL-UX #219's finding is that the
review protocol itself sends the reviewer to the diff, and the commit bodies come
with it — the better the commit message, the more completely the withholding is
defeated. All three measured defeats (#204, #212, #219) were known only because a
reviewer declared one unprompted. What this buys is that a reviewer knows what to
declare.

git and the tracker arrive as data, the way ``changed_paths`` already does, so
the application layer never reaches up into ``services`` and the report can be
exercised without a repository.
"""

# beadloom:feature=review-brief

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from beadloom.application.declared_scope import work_item_of_branch
from beadloom.application.review_brief.models import (
    CHANNEL_BEAD_COMMENTS,
    CHANNEL_COMMIT_BODIES,
    CHANNEL_LAUNCH_PROMPT,
    CHANNEL_WORK_ITEM_DOCUMENTS,
    DEFEAT_NOTICE,
    RELEASE_CONDITION,
    WITHHELD_REASON,
    Channel,
    Reachability,
)
from beadloom.onboarding.composer import compose, templates_dir
from beadloom.onboarding.doc_templates import DEFAULT_DOC_CONFIG, doc_flow_config
from beadloom.onboarding.flow_config import FlowConfigError
from beadloom.onboarding.role_composer import ROLE_NAMES

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from pathlib import Path

    from beadloom.application.review_brief.models import AuthorNote, Commit
    from beadloom.onboarding.flow_config import FlowConfig

#: A document a prompt names, matched by SHAPE rather than by spelling: an
#: upper-case name ending in ``.md``. The shape is what the flow's own documents
#: share — ``PRD.md``, ``RFC.md``, ``CONTEXT.md``, ``PLAN.md``, ``BRIEF.md``,
#: ``ACTIVE.md`` — and what a team's own ``DECISIONS.md`` shares with them.
#: Nothing here lists the names, so a role fragment that gains one is read.
_DOCUMENT_RE = re.compile(r"\b([A-Z][A-Z0-9_-]{1,20}\.md)\b")

#: The suffix every shipped command fragment carries, and where they live. The
#: command population is read off the directory for the same reason
#: ``ROLE_NAMES`` is read off the role fragments: a fifth command added to the
#: package is a fifth prompt a coordinator composes.
_FRAGMENT_SUFFIX = ".md.txt"

#: What a launch prompt is, said in the report rather than left out. Nothing in
#: this process can observe one, so the duty to declare it is placed where the
#: observation is — which is the notice's own argument, reused rather than
#: written twice.
LAUNCH_PROMPT_REASON = f"nothing in this process can see one, so: {DEFEAT_NOTICE}"

#: Why bead comments are a channel at all: this command holds them, and says so.
BEAD_COMMENTS_REASON = (
    f"withheld by this command until {RELEASE_CONDITION}; {WITHHELD_REASON}"
)


def _command_names() -> tuple[str, ...]:
    """Every command fragment the package ships, in deterministic order."""
    core = templates_dir() / "agentic_flow" / "commands"
    return tuple(
        sorted(path.name[: -len(_FRAGMENT_SUFFIX)] for path in core.glob(f"*{_FRAGMENT_SUFFIX}"))
    )


def _composed_prompts(
    config: FlowConfig, project_root: Path | None
) -> tuple[tuple[str, str], ...]:
    """Each composed prompt as ``(label, text)``, project layer included.

    A prompt that will not compose contributes nothing and is not an error here:
    reporting a malformed ``flow.yml`` is ``config-check``'s job, and a second
    reporter of one fault is how two checks come to disagree about it.
    """
    prompts: list[tuple[str, str]] = []
    requests = [("roles", name) for name in ROLE_NAMES]
    requests += [("commands", name) for name in _command_names()]
    for kind, name in requests:
        try:
            composition = compose(kind, name, config=config, project_root=project_root)
        except FlowConfigError:
            continue
        for fragment in composition.fragments:
            label = f"{kind}/{name}"
            if fragment.layer == "project":
                label = f"{label} (project layer)"
            prompts.append((label, fragment.text))
    return tuple(prompts)


def prompts_naming_documents(
    project_root: Path | None = None, *, config: FlowConfig | None = None
) -> dict[str, tuple[str, ...]]:
    """Which composed prompts name which document, ``{document: (prompt, ...)}``.

    ``config`` defaults to the project's own ``flow.yml`` when a root is given
    and to the shipped default otherwise — the same fallback
    :func:`beadloom.application.work_item_routing.task_init_routing` makes, so a
    project that never scaffolded the flow is still read against the shipped
    prompts rather than against nothing.
    """
    if config is None:
        config = (
            doc_flow_config(project_root) if project_root is not None else DEFAULT_DOC_CONFIG
        )
    naming: dict[str, list[str]] = {}
    for label, text in _composed_prompts(config, project_root):
        for document in sorted(set(_DOCUMENT_RE.findall(text))):
            labels = naming.setdefault(document, [])
            if label not in labels:
                labels.append(label)
    return {document: tuple(labels) for document, labels in sorted(naming.items())}


def bead_comments_channel(notes: Sequence[AuthorNote]) -> Channel:
    """The author's comments, counted and attributed, never quoted.

    The items are each comment's author and date. That is what a reviewer needs
    to know an account exists and how much of it there is; the text is the thing
    being withheld, so it is not here and is not in the count's explanation.
    """
    items = tuple(
        f"{note.author or 'unattributed'} {note.created}".strip() for note in notes
    )
    return Channel(
        name=CHANNEL_BEAD_COMMENTS,
        inspected=True,
        items=items,
        reason=BEAD_COMMENTS_REASON,
    )


def _document_item(path: Path, project_root: Path, naming: dict[str, tuple[str, ...]]) -> str:
    """One document of the work item, with the prompts that send a reader to it."""
    relative = path.relative_to(project_root).as_posix()
    prompts = naming.get(path.name, ())
    attribution = ", ".join(prompts) if prompts else "no composed prompt"
    return f"{relative} — named by {attribution}"


def work_item_documents_channel(
    project_root: Path | None, *, branch: str | None, config: FlowConfig | None = None
) -> Channel:
    """The documents of the work item this branch names, and who names them.

    Four different ways this cannot be answered, each reported as itself rather
    than as an empty folder: no project root, no branch, a branch naming no work
    item in the project's planning corpus, and a work item folder that is gone.
    """
    if project_root is None:
        return Channel(
            name=CHANNEL_WORK_ITEM_DOCUMENTS,
            inspected=False,
            reason="no project root was given, so no work item's folder could be read",
        )
    if not branch:
        return Channel(
            name=CHANNEL_WORK_ITEM_DOCUMENTS,
            inspected=False,
            reason="no branch is checked out, so nothing names the work item to read",
        )
    folder = work_item_of_branch(project_root, branch)
    if folder is None or not folder.is_dir():
        return Channel(
            name=CHANNEL_WORK_ITEM_DOCUMENTS,
            inspected=False,
            reason=(
                f"the branch {branch!r} names no work item among the project's "
                "planning documents, so no folder could be read"
            ),
        )
    naming = prompts_naming_documents(project_root, config=config)
    items = tuple(
        _document_item(document, project_root, naming)
        for document in sorted(folder.glob("*.md"))
    )
    return Channel(
        name=CHANNEL_WORK_ITEM_DOCUMENTS,
        inspected=True,
        items=items,
        reason=(
            f"the folder {folder.relative_to(project_root).as_posix()}, against the "
            f"{len(naming)} document name(s) this project's composed prompts mention"
        ),
    )


def commit_bodies_channel(commits: Iterable[Commit] | None, *, since: str) -> Channel:
    """The commits of the reviewed range, and how much prose each body carries.

    ``None`` means git gave no answer and is reported as such. The range is the
    review's OWN base, so the statement names the window it was taken over — a
    count whose window is unstated is the defect this whole report replaces.
    """
    window = since or "the base ref"
    if commits is None:
        return Channel(
            name=CHANNEL_COMMIT_BODIES,
            inspected=False,
            reason=f"git gave no answer for the range since {window}",
        )
    listed = tuple(commits)
    items = tuple(
        f"{commit.sha} {commit.subject} — {commit.body_lines} body line(s)"
        for commit in listed
    )
    with_a_body = sum(1 for commit in listed if commit.body_lines > 0)
    return Channel(
        name=CHANNEL_COMMIT_BODIES,
        inspected=True,
        items=items,
        reason=(
            f"read over the range since {window}; {with_a_body} of {len(listed)} "
            "carry a body, and your protocol sends you to this diff"
        ),
    )


def launch_prompt_channel() -> Channel:
    """The channel this command cannot inspect, named rather than omitted."""
    return Channel(
        name=CHANNEL_LAUNCH_PROMPT, inspected=False, reason=LAUNCH_PROMPT_REASON
    )


def reachability_of(
    *,
    notes: Sequence[AuthorNote],
    project_root: Path | None,
    branch: str | None,
    commits: Iterable[Commit] | None,
    since: str,
    config: FlowConfig | None = None,
) -> Reachability:
    """The whole statement, in the order a reviewer reads it.

    Bead comments first, because that is the channel this command acts on;
    the launch prompt last, because it is the one nothing here can measure and a
    reader who stops early should have read every answer before the absence.
    """
    return Reachability(
        channels=(
            bead_comments_channel(notes),
            work_item_documents_channel(project_root, branch=branch, config=config),
            commit_bodies_channel(commits, since=since),
            launch_prompt_channel(),
        )
    )
