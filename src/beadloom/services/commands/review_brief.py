"""The ``review-brief`` command — hand a reviewer the change and the specification.

Presentation and wiring only. What is handed over and what is held back is
:mod:`beadloom.application.review_brief`; this module is where the bead and its
comments are read through the ``bd`` seam, where the change inventory is read out
of git, where the acceptance suite is read off disk, and where a brief becomes
lines on a stream and one exit code.

Codes (the contract a caller may rely on):

* ``0`` — a brief was assembled and rests on nothing unstated, or, under
  ``--release``, the author's account was released.
* ``1`` — a brief was assembled and carries findings: an undeclared scope, a ref
  the graph does not have, a change nobody could measure, a changed file owned by
  a node the bead never named, no scenario bound to the bead. Visible, never
  blocking — the brief is still usable.
* ``2`` — no brief could be assembled: no index, no answer from the tracker, a
  bead the tracker does not have.
* ``3`` — ``--release`` was refused because no verdict is recorded. Distinct from
  ``2`` on purpose: nothing failed, the account is simply still withheld, and a
  caller that could not tell those apart would retry the wrong one.

``--release`` shares that scale rather than having one of its own. It exits ``1``
when the account was released and the gate could not confirm that the verdict was
recorded by anyone other than the bead's own author — released, and a finding, on
the same rule that makes an unmeasured medium a finding instead of a silent pass.

**Every fact is printed in both shapes.** The human output and ``--json`` carry
the same counts and the same reachability statement, and neither depends on
whether stdout is a terminal — a surface whose shape depends on whether a human is watching will
be sampled by a program and silently given a different answer (BDL-UX #148).
Nothing here asks a caller to count lines.
"""

# beadloom:component=cli-commands

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import click

from beadloom.services.commands._root import main

if TYPE_CHECKING:
    from collections.abc import Sequence

    from beadloom.application.review_brief import (
        AuthorNote,
        Channel,
        Commit,
        ReleaseOutcome,
        ReviewBrief,
    )

#: Exit codes, named so the renderer and the docstring cannot drift apart.
_EXIT_CLEAN = 0
_EXIT_FINDINGS = 1
_EXIT_UNASSEMBLABLE = 2
_EXIT_WITHHELD = 3

#: The trunk assumed when ``flow.yml`` declares none. Read from the
#: ``working-branch`` guard's ``options.trunk`` first, because the trunk's name is
#: already configuration in this project and a second default for the same fact is
#: the two-sources-of-truth defect this epic has met three times.
_FALLBACK_TRUNK = "main"

#: How long git is given to answer before the change is reported as unmeasured.
_GIT_TIMEOUT_S = 30

#: The codec git's answer is read with, STATED rather than inherited from the
#: image. ``text=True`` decodes with the ambient locale, so the same repository
#: would yield a different path list on a container whose locale is not UTF-8.
_GIT_ENCODING = "utf-8"

#: ``surrogateescape`` rather than ``strict``, stated by which way each fails.
#: What this reads is PATHS, which git stores as bytes and which are not required
#: to be UTF-8. Under ``strict`` a single oddly-named file anywhere in the change
#: would raise, the whole inventory would come back unmeasured, and a reviewer
#: would be told nobody looked because of one filename. ``surrogateescape`` is
#: injective, so every path still decodes to a distinct string and no ownership
#: comparison can be given a wrong answer; the cost is that such a path reaches
#: the reader with ``\udcff``-style escapes in it, which is ugly and true.
_GIT_DECODE_ERRORS = "surrogateescape"


def _base_ref(project_root: Path) -> str:
    """The ref a change is measured against, from the declared trunk."""
    from beadloom.application.guards.config import GuardConfigError, load_guards_config

    try:
        config = load_guards_config(project_root)
    except GuardConfigError:
        # A flow.yml that will not parse is reported, loudly, by `beadloom ci`.
        # Here it means only that the trunk was not declared.
        return _FALLBACK_TRUNK
    return config.spec_for("working-branch").options.get("trunk", _FALLBACK_TRUNK)


def _changed_since(project_root: Path, ref: str) -> frozenset[str] | None:
    """Paths that differ from *ref*, or ``None`` when the question had no answer.

    ``None`` covers every way the question can fail — no repository, no git, a ref
    that does not resolve — and callers must read it as *nobody looked*, never as
    *nothing changed*. The two reaching a reviewer as the same brief is the silent
    false-green this command exists to remove.

    Three questions are asked, not one: what the branch committed since *ref*,
    what the working tree holds on top of it, and what exists on disk that git
    does not track yet. The third is not decoration — ``git diff`` never lists an
    untracked path, so a brief built from diffs alone showed a reviewer every file
    the change TOUCHED and none of the files it ADDED, which is the half of a
    change most worth reading. Ignored files stay out (``--exclude-standard``):
    git does not track them, so git has no opinion about them, and inventing one
    would put an index and a build directory in front of a reviewer as work.
    """
    questions = (
        ["diff", "--name-only", f"{ref}...HEAD"],
        ["diff", "--name-only", "HEAD"],
        ["ls-files", "--others", "--exclude-standard"],
    )
    paths: set[str] = set()
    for args in questions:
        try:
            proc = subprocess.run(  # noqa: S603
                ["git", *args],  # noqa: S607
                cwd=project_root,
                capture_output=True,
                encoding=_GIT_ENCODING,
                errors=_GIT_DECODE_ERRORS,
                check=False,
                timeout=_GIT_TIMEOUT_S,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        if proc.returncode != 0:
            return None
        paths.update(line.strip() for line in proc.stdout.splitlines() if line.strip())
    return frozenset(paths)


#: Field and record separators for ``git log``. Bytes no commit message can
#: contain, so a subject holding a newline or a pipe cannot shift a field — the
#: same reason ``git status --porcelain -z`` is read with NULs elsewhere.
_LOG_FIELD_SEP = "\x1f"
_LOG_RECORD_SEP = "\x1e"


def _commits_since(project_root: Path, ref: str) -> tuple[Commit, ...] | None:
    """The commits of the reviewed range, or ``None`` when git had no answer.

    ``ref..HEAD`` — what THIS branch added — rather than the symmetric
    difference, so a commit that landed on the trunk after the branch left is not
    reported as something the reviewer can read about this change.

    Only the subject and the body's LINE COUNT come back. The bodies are the
    channel being reported, not the report's content: this project writes long,
    specific commit messages, which is exactly why BDL-UX #219 found them
    defeating the withholding, and a report that quoted them would be the leak.
    """
    fmt = f"%H{_LOG_FIELD_SEP}%s{_LOG_FIELD_SEP}%b{_LOG_RECORD_SEP}"
    try:
        proc = subprocess.run(  # noqa: S603
            ["git", "log", f"--format={fmt}", f"{ref}..HEAD"],  # noqa: S607
            cwd=project_root,
            capture_output=True,
            encoding=_GIT_ENCODING,
            errors=_GIT_DECODE_ERRORS,
            check=False,
            timeout=_GIT_TIMEOUT_S,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    from beadloom.application import review_brief as vocabulary

    found: list[Commit] = []
    for record in proc.stdout.split(_LOG_RECORD_SEP):
        fields = record.strip("\n").split(_LOG_FIELD_SEP)
        if len(fields) != 3 or not fields[0].strip():
            continue
        sha, subject, body = fields
        found.append(
            vocabulary.Commit(
                sha=sha.strip()[:8],
                subject=subject.strip(),
                body_lines=len([line for line in body.splitlines() if line.strip()]),
            )
        )
    return tuple(found)


def _bead_fields(bead_id: str, project_root: Path) -> dict[str, Any]:
    """The tracker's record for *bead_id*, read once through the ``bd`` seam.

    One call, because three different questions are asked of the same record —
    what the bead was asked to do, what it says it occupies, and who is working
    on it — and asking the tracker three times is how three answers come to
    disagree about one bead.
    """
    from beadloom.services.bd_seam import run_bd

    result = run_bd(["show", bead_id, "--json"], cwd=str(project_root))
    if not result.ok or not result.stdout.strip():
        msg = f"the tracker has no bead {bead_id!r} ({result.stderr.strip()})"
        raise LookupError(msg)
    parsed = json.loads(result.stdout)
    record = parsed[0] if isinstance(parsed, list) and parsed else parsed
    if not isinstance(record, dict):
        msg = f"the tracker's answer for {bead_id!r} was not a bead record"
        raise LookupError(msg)
    return record


def _bead_record(bead_id: str, fields: dict[str, Any]) -> tuple[Any, str]:
    """The bead as data, and the ASSIGNMENT string.

    Two strings come back because they answer different questions. The
    declaration carries everything the bead says about itself so the ``refs:``
    token is found wherever the author wrote it — this epic's own beads put it in
    ``notes`` as often as in the description — and it is composed by
    :func:`compose_declaration`, the one composer all three callers of the parser
    share. The assignment is the title and the description alone, because
    ``notes`` is also where a dev appends progress.
    """
    from beadloom.application.waves import BeadRecord, compose_declaration

    title = str(fields.get("title", ""))
    description = str(fields.get("description", ""))
    assignment = f"{title}\n\n{description}".strip()
    return (
        BeadRecord(
            bead_id=bead_id, declaration=compose_declaration(fields), title=title
        ),
        assignment,
    )


def _bead_author(fields: dict[str, Any]) -> str:
    """The party whose account is being withheld — the tracker's assignee.

    Empty when the tracker names none, and the release reports that rather than
    reading it as an independent verdict: an unknown identity is not a different
    one.
    """
    return str(fields.get("assignee", "") or "")


def _author_notes(bead_id: str, project_root: Path) -> tuple[AuthorNote, ...]:
    """Every comment on the bead, as data the brief will only ever count.

    A tracker that cannot answer is an error rather than an empty list: "the
    author wrote nothing" and "nobody asked" are different facts, and reporting
    the second as the first would print ``0 withheld`` over an account that exists.
    """
    from beadloom.application.review_brief import AuthorNote
    from beadloom.services.bd_seam import run_bd

    result = run_bd(["comments", bead_id, "--json"], cwd=str(project_root))
    if not result.ok:
        msg = f"the tracker would not list comments for {bead_id!r} ({result.stderr.strip()})"
        raise LookupError(msg)
    if not result.stdout.strip():
        return ()
    parsed = json.loads(result.stdout)
    if not isinstance(parsed, list):
        msg = f"the tracker's comment list for {bead_id!r} was not a list"
        raise LookupError(msg)
    return tuple(
        AuthorNote(
            text=str(item.get("text", "")),
            author=str(item.get("author", "")),
            created=str(item.get("created_at", "")),
        )
        for item in parsed
        if isinstance(item, dict)
    )


def _suite_scenarios(project_root: Path) -> tuple[Any, ...]:
    """Every scenario in the acceptance suite, under the project's declared glob.

    The glob is read from the ``scenario_coverage`` rule so an adopter's layout is
    honoured; a rules file that will not parse falls back to the shipped default,
    because reporting that parse failure is ``beadloom lint``'s job and doing it
    twice, differently, is how two checks come to disagree.
    """
    from beadloom.graph.rules.loader import load_rules
    from beadloom.graph.rules.types import ScenarioCoverageRule
    from beadloom.graph.scenarios import DEFAULT_FEATURE_GLOB, load_suite

    glob = DEFAULT_FEATURE_GLOB
    rules_path = project_root / ".beadloom" / "_graph" / "rules.yml"
    if rules_path.exists():
        try:
            for rule in load_rules(rules_path):
                if isinstance(rule, ScenarioCoverageRule):
                    glob = rule.features
                    break
        except (ValueError, OSError):
            glob = DEFAULT_FEATURE_GLOB
    return load_suite(project_root, glob).scenarios


def _brief_as_dict(brief: ReviewBrief) -> dict[str, Any]:
    """The whole brief as data — the same facts the human shape prints."""
    return {
        "bead": brief.bead_id,
        "title": brief.title,
        "assignment": brief.assignment,
        "refs": list(brief.refs),
        "unknown_refs": list(brief.unknown_refs),
        "docs": [{"ref": d.ref, "path": d.path, "kind": d.kind} for d in brief.docs],
        "base_ref": brief.measured_since,
        "change_measured": brief.change_measured,
        "changed": [
            {"path": c.path, "owner": c.owner, "in_scope": c.in_scope}
            for c in brief.changed
        ],
        "scenarios": [
            {"name": s.name, "path": s.path, "line": s.line} for s in brief.scenarios
        ],
        "reachability": [
            {
                "channel": channel.name,
                "inspected": channel.inspected,
                "carries": channel.carries,
                "reason": channel.reason,
                "items": list(channel.items),
            }
            for channel in brief.reachability.channels
        ],
        "findings": list(brief.findings),
        "exit_code": _EXIT_FINDINGS if brief.findings else _EXIT_CLEAN,
    }


def _render_specification(brief: ReviewBrief) -> None:
    click.echo("")
    click.echo("THE ASSIGNMENT (the bead's description; the author's account is withheld)")
    for line in brief.assignment.splitlines() or [""]:
        click.echo(f"  {line}")
    click.echo("")
    click.echo(f"DECLARED SCOPE: {', '.join(brief.refs) if brief.refs else 'none declared'}")
    click.echo("")
    click.echo(
        f"SPECIFICATION — {len(brief.docs)} document(s), "
        f"{len(brief.scenarios)} bound scenario(s)"
    )
    for doc in brief.docs:
        click.echo(f"  {doc.path} ({doc.kind}) — {doc.ref}")
    for scenario in brief.scenarios:
        click.echo(f"  {scenario.path}:{scenario.line} — {scenario.name}")


def _render_change(brief: ReviewBrief) -> None:
    base_ref = brief.measured_since
    click.echo("")
    if not brief.change_measured:
        click.echo(
            f"CHANGE since {base_ref}: UNMEASURED — git gave no answer, so this is "
            "'nobody looked', not 'nothing changed'."
        )
        return
    click.echo(f"CHANGE since {base_ref} — {len(brief.changed)} file(s)")
    for changed in brief.changed:
        owner = changed.owner or "unowned"
        known = changed.in_scope or changed.owner is None
        outside = "" if known else "  — OUTSIDE the declared scope"
        click.echo(f"  [{owner}] {changed.path}{outside}")
    click.echo(f"  read it: git diff {base_ref}...HEAD -- <path>")


#: The heading of the reachability block, and the claim it is careful NOT to
#: make. This report raises detectability; it closes nothing. The review protocol
#: itself sends a reviewer to the diff, and the commit bodies come with it.
_REACHABLE_HEADING = (
    "REACHABLE — what can reach you about this change, per channel. This command "
    "withholds one of them and closes none of the others; declaring what actually "
    "reached you is still yours to do."
)


def _render_channel(channel: Channel) -> None:
    """One channel's statement, then what it carries, indented under it."""
    click.echo(f"  {channel.statement()}")
    for item in channel.items:
        click.echo(f"    {item}")


def _render_reachability(brief: ReviewBrief) -> None:
    click.echo("")
    click.echo(_REACHABLE_HEADING)
    for channel in brief.reachability.channels:
        _render_channel(channel)


def _render_brief(brief: ReviewBrief) -> None:
    """Print the change, the specification, and what was held back."""
    click.echo(f"Review brief for {brief.bead_id} — {brief.title}")
    click.echo(
        f"{len(brief.changed)} changed file(s), {len(brief.docs)} document(s), "
        f"{len(brief.scenarios)} bound scenario(s), {len(brief.findings)} finding(s)."
    )
    _render_specification(brief)
    _render_change(brief)
    _render_reachability(brief)
    if brief.findings:
        click.echo("")
        for finding in brief.findings:
            click.echo(f"FINDING: {finding}", err=True)


def _render_release(
    outcome: ReleaseOutcome, notes: Sequence[AuthorNote], *, bead: str
) -> None:
    """The release half, in the vocabulary the brief half already speaks.

    The refusal names the CHANNEL and the BEAD, because it reports a count of
    things it does not show and that is exactly the count whose population has to
    be stated. The release below it names neither: it prints the comments
    themselves, so its population is on the screen under it.
    """
    if outcome.refused_reason is not None:
        click.echo(
            f"WITHHELD — bead comments on {bead}: {len(notes)} item(s) stay "
            f"withheld: {outcome.refused_reason}",
            err=True,
        )
        return
    click.echo(
        f"RELEASED — {len(outcome.released)} author comment(s), on the verdict "
        f"{outcome.verdict_marker!r} already recorded."
    )
    if outcome.independence_note is not None:
        # Before the account, not after it: a reviewer reads top-down, and a
        # caveat printed under the thing it qualifies arrives too late to qualify
        # anything.
        click.echo(f"FINDING: {outcome.independence_note}", err=True)
    for note in outcome.released:
        click.echo("")
        click.echo(f"--- {note.author} {note.created}".rstrip())
        click.echo(note.text)


def _release_as_dict(outcome: ReleaseOutcome, notes: Sequence[AuthorNote]) -> dict[str, Any]:
    return {
        "withheld_count": len(notes),
        "verdict_marker": outcome.verdict_marker,
        "verdict_author": outcome.verdict_author,
        "independence_note": outcome.independence_note,
        "refused_reason": outcome.refused_reason,
        "released": [
            {"author": n.author, "created": n.created, "text": n.text}
            for n in outcome.released
        ],
        "exit_code": _release_exit_code(outcome),
    }


def _release_exit_code(outcome: ReleaseOutcome) -> int:
    """The one place the release's exit code is decided, for both output shapes.

    Three answers, not two. A refused release is exit 3; a release resting on a
    verdict whose independence the tracker could not confirm is exit 1, released
    and reported; anything else is 0.
    """
    if outcome.refused_reason is not None:
        return _EXIT_WITHHELD
    return _EXIT_FINDINGS if outcome.independence_note is not None else _EXIT_CLEAN


def _run_release(bead: str, project_root: Path, *, output_json: bool) -> int:
    """The AFTER half: the author's account, once a verdict is on the record."""
    from beadloom.application.review_brief import release_notes

    notes = _author_notes(bead, project_root)
    outcome = release_notes(notes, bead_author=_bead_author(_bead_fields(bead, project_root)))
    if output_json:
        click.echo(json.dumps(_release_as_dict(outcome, notes), indent=2))
    else:
        _render_release(outcome, notes, bead=bead)
    return _release_exit_code(outcome)


def _run_brief(
    bead: str, project_root: Path, *, since: str | None, output_json: bool
) -> int:
    """The BEFORE half: the change and the specification, and a count."""
    from beadloom.application.review_brief import assemble_brief
    from beadloom.doc_sync.git_baseline import current_branch
    from beadloom.infrastructure.db import open_db

    db_path = project_root / ".beadloom" / "beadloom.db"
    if not db_path.exists():
        click.echo("Error: database not found. Run `beadloom reindex` first.", err=True)
        return _EXIT_UNASSEMBLABLE

    record, assignment = _bead_record(bead, _bead_fields(bead, project_root))
    notes = _author_notes(bead, project_root)
    base_ref = since or _base_ref(project_root)
    conn = open_db(db_path)
    try:
        brief = assemble_brief(
            conn,
            record,
            assignment=assignment,
            changed_paths=_changed_since(project_root, base_ref),
            measured_since=base_ref,
            notes=notes,
            scenarios=_suite_scenarios(project_root),
            project_root=project_root,
            branch=current_branch(project_root),
            commits=_commits_since(project_root, base_ref),
        )
    finally:
        conn.close()

    if output_json:
        click.echo(json.dumps(_brief_as_dict(brief), indent=2))
    else:
        _render_brief(brief)
    return _EXIT_FINDINGS if brief.findings else _EXIT_CLEAN


# beadloom:domain=application
@main.command("review-brief")
@click.argument("bead")
@click.option("--since", default=None, help="Base ref the change is measured against.")
@click.option(
    "--release",
    "release",
    is_flag=True,
    help="Print the author's account, once a verdict is recorded.",
)
@click.option("--json", "output_json", is_flag=True, help="Structured JSON output.")
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
def review_brief(
    *, bead: str, since: str | None, release: bool, output_json: bool, project: Path | None
) -> None:
    """Assemble a reviewer's input: the change and the specification, not the author's account.

    A review that reads what the author said it did is not an independent check.
    The bead's description is the assignment and is handed over; its comments are
    the author's report and are counted, not printed, until a verdict is recorded
    — then `--release` prints them, so a deliberate deferral or a measurement is
    not re-derived and the reviewer's own judgement was formed first.
    """
    from beadloom.services.bd_seam import BdUnavailableError

    project_root = project or Path.cwd()
    try:
        code = (
            _run_release(bead, project_root, output_json=output_json)
            if release
            else _run_brief(bead, project_root, since=since, output_json=output_json)
        )
    except (LookupError, BdUnavailableError, json.JSONDecodeError) as exc:
        click.echo(f"Error: no review brief could be assembled — {exc}", err=True)
        sys.exit(_EXIT_UNASSEMBLABLE)
    sys.exit(code)
