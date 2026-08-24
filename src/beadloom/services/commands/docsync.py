"""Doc-sync + ACTIVE/tracker reconcile commands.

Owns ``sync-check``, ``install-hooks``, ``active-sync``, and ``sync-update``.
"""
# beadloom:component=cli-commands

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    import sqlite3
    from types import ModuleType
    from typing import Any

    from beadloom.application.active_table import ReconcileResult

from beadloom.doc_sync.doc_shape import STATUS_INCOMPLETE
from beadloom.doc_sync.engine import STATUS_EXEMPT
from beadloom.services.commands._root import main


# beadloom:domain=doc-sync
@main.command("sync-check")
@click.option("--porcelain", is_flag=True, help="TAB-separated machine-readable output.")
@click.option("--json", "output_json", is_flag=True, help="Structured JSON output.")
@click.option("--report", "output_report", is_flag=True, help="Markdown report for CI posting.")
@click.option("--ref", "ref_filter", default=None, help="Filter by ref_id.")
@click.option(
    "--staged",
    is_flag=True,
    default=False,
    help="Judge only the pairs this commit stages, and say how many were left "
    "to the push gate. For a pre-commit hook in a shared working tree, where a "
    "whole-tree check fails one agent's commit on a neighbour's WIP (#118).",
)
@click.option(
    "--since",
    "since_ref",
    default=None,
    help="Baseline = code state at this git ref (e.g. the push's parent commit) "
    "instead of the stored sync_state. Reports pairs whose code drifted since "
    "the ref while the doc was not correspondingly updated.",
)
@click.option(
    "--record-surface",
    is_flag=True,
    default=False,
    help="Record the declared documentation surface (pair + declared-doc counts) "
    "to the committed `.beadloom/sync-surface.json`, so a later run can tell "
    "when the surface SHRANK. Deliberate act: no ordinary run rewrites it.",
)
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
def sync_check(
    *,
    porcelain: bool,
    output_json: bool,
    output_report: bool,
    ref_filter: str | None,
    staged: bool,
    since_ref: str | None,
    record_surface: bool,
    project: Path | None,
) -> None:
    """Check doc-code synchronization status.

    Exit codes: 0 = all ok, 1 = error, 2 = a pair is stale or MISSING.

    A pair reads ``ok`` only when it was compared against a baseline and found
    fresh. ``missing`` (the doc or code file is gone, or the graph declares a doc
    that is not on disk) fails the check; ``unverified`` (the index was rebuilt,
    so its baseline is the tree it was built from, and git could not supply one)
    is reported by name and never counted as fresh.
    """
    from beadloom.application.doc_shape import section_requirements
    from beadloom.doc_sync.commit_scope import scope_to_commit
    from beadloom.doc_sync.declared_docs import count_declared_docs
    from beadloom.doc_sync.doc_shape import (
        REASON_MISSING_SECTIONS,
        REASON_SECTION_NOT_IN_USE,
    )
    from beadloom.doc_sync.engine import (
        BLOCKING_STATUSES,
        STATUS_OK,
        STATUS_UNVERIFIED,
        _validate_git_ref,
        check_reference_drift,
        check_sync,
        check_sync_since,
        find_unchecked_doc_nodes,
    )
    from beadloom.doc_sync.git_baseline import staged_paths
    from beadloom.doc_sync.surface_ledger import compare_surface, read_ledger, write_ledger
    from beadloom.infrastructure.db import open_db
    from beadloom.infrastructure.doc_roots import resolve_docs_dir

    project_root = project or Path.cwd()
    db_path = project_root / ".beadloom" / "beadloom.db"

    if not db_path.exists():
        click.echo("Error: database not found. Run `beadloom reindex` first.", err=True)
        sys.exit(1)

    if since_ref is not None and (
        set(since_ref) == {"0"} or not _validate_git_ref(project_root, since_ref)
    ):
        click.echo(f"Error: Invalid git ref: '{since_ref}'", err=True)
        sys.exit(1)

    conn = open_db(db_path)
    if since_ref is not None:
        results = check_sync_since(conn, project_root=project_root, since=since_ref)
        # `--since` is a ref-relative symbol-pair view; reference surfaces have no
        # git-ref baseline, so they are not evaluated in that mode.
        references: list[dict[str, Any]] = []
        unchecked: list[dict[str, str]] = []
    else:
        results = check_sync(
            conn,
            project_root=project_root,
            section_requirements=section_requirements(project_root),
        )
        references = check_reference_drift(conn, project_root)
        # Nodes that declare a doc but contribute no pair. Naming them is what
        # stops a green verdict from reading as "checked" (BDL-UX #146);
        # advisory, so the exit code is unaffected.
        unchecked = find_unchecked_doc_nodes(conn)
    declared_docs = count_declared_docs(conn)
    conn.close()

    # The DECLARED surface is the whole surface, counted before any narrowing.
    # `--ref` and `--staged` both restrict what is REPORTED; neither says the
    # project declared less. Counted after the filter, `--ref sync-check` read
    # "declared surface SHRANK: 322 -> 6 pair(s)", and `--record-surface` would
    # have written that 6 into the committed ledger (BDL-061 S6).
    declared_pairs = len([r for r in results if r.get("code_path")])

    if ref_filter:
        results = [r for r in results if r["ref_id"] == ref_filter]
        unchecked = [u for u in unchecked if u["ref_id"] == ref_filter]

    # `--staged` moves the question from "is this tree clean" to "is this commit
    # clean", which is the only form of the question a shared working tree can
    # answer for one agent (BDL-UX #118). The pairs it leaves out are COUNTED and
    # printed: a check that narrows itself in silence is the false green this
    # epic exists to remove.
    commit_scope = None
    if staged:
        commit_scope = scope_to_commit(
            results, staged_paths(project_root), docs_dir=resolve_docs_dir(project_root)
        )
        results = list(commit_scope.pairs)

    # ``missing`` blocks exactly like ``stale``: the gate is not satisfied by
    # having less to check (BDL-UX #174).
    has_blocking = any(r["status"] in BLOCKING_STATUSES for r in results)
    unverified = [r for r in results if r["status"] == STATUS_UNVERIFIED]
    # Surface drift is advisory (warning) — it NEVER affects the exit code.
    drifted_refs = [r for r in references if r["status"] == "surface_drift"]

    pair_count = declared_pairs
    if record_surface:
        recorded_path = write_ledger(
            project_root,
            declared_pairs=pair_count,
            declared_docs=declared_docs,
            recorded_at=datetime.now(tz=timezone.utc).isoformat(),
        )
        click.echo(
            f"Recorded declared surface: {pair_count} pair(s), "
            f"{declared_docs} declared doc(s) -> {recorded_path}"
        )
    surface = compare_surface(
        read_ledger(project_root),
        declared_pairs=pair_count,
        declared_docs=declared_docs,
    )

    if output_json:
        ok_count = sum(1 for r in results if r["status"] == STATUS_OK)
        stale_count = sum(1 for r in results if r["status"] == "stale")
        summary: dict[str, Any] = {
            "total": len(results),
            "ok": ok_count,
            "stale": stale_count,
        }
        # Present only in commit-scoped mode: without `--staged` nothing was left
        # out, and a key reporting a narrowing that did not happen is a fact
        # rendered about a run that never made it.
        if commit_scope is not None:
            summary["not_checked_outside_commit"] = commit_scope.not_checked
            summary["commit_scope"] = (
                "narrowed" if commit_scope.narrowed else "not_narrowed"
            )
        data: dict[str, Any] = {
            "summary": summary,
            "pairs": [
                {
                    "status": r["status"],
                    "ref_id": r["ref_id"],
                    "doc_path": r["doc_path"],
                    "code_path": r["code_path"],
                    "reason": r.get("reason", "ok"),
                    # WHICH baseline produced this verdict — a green result must
                    # say what it was green against (BDL-UX #175). Only in the
                    # stored-baseline mode: `--since` is a ref-relative view
                    # whose JSON shape is a fixed contract.
                    **({} if since_ref is not None else {"baseline": r.get("baseline", "index")}),
                    **({"details": r["details"]} if r.get("details") else {}),
                }
                for r in results
            ],
        }
        # Reference-doc surface drift (BDL-057 Layer 2) is additive and only
        # applies to the stored-baseline mode — `--since` is a ref-relative
        # symbol-pair view with no reference baseline, so its JSON shape is left
        # untouched (the `pairs` array above is unchanged in both modes).
        if since_ref is None:
            # Both additions belong to the stored-baseline mode only: `--since`
            # is a ref-relative pair view whose JSON shape is a fixed contract.
            summary["missing"] = sum(1 for r in results if r["status"] == "missing")
            summary["unverified"] = len(unverified)
            # Every verdict has a key, so `ok + stale + missing + unverified +
            # exempt + incomplete` sums to `total`. It did not while `exempt` and
            # `incomplete` had none, and a consumer computing `total - ok` read
            # unexplained pairs (`beadloom-mr2l.76`). `unchecked` is deliberately
            # NOT in that sum: it counts NODES that contribute no pair at all,
            # which is a different population from the pairs above it.
            summary["exempt"] = sum(1 for r in results if r["status"] == STATUS_EXEMPT)
            summary["incomplete"] = sum(
                1 for r in results if r["status"] == STATUS_INCOMPLETE
            )
            summary["unchecked"] = len(unchecked)
            data["unchecked"] = unchecked
            summary["surface_drift"] = len(drifted_refs)
            summary["declared_docs"] = declared_docs
            data["declared_surface"] = {
                "recorded": surface.recorded,
                "shrank": surface.shrank,
                "message": surface.message,
            }
            data["references"] = [
                {
                    "status": r["status"],
                    "doc_path": r["doc_path"],
                    "watches": r["watches"],
                    "reason": r["reason"],
                    "severity": r["severity"],
                }
                for r in references
            ]
        click.echo(json.dumps(data, ensure_ascii=False, indent=2))
    elif output_report:
        click.echo(_build_sync_report(results))
    elif porcelain:
        # A record in the same five-column shape rather than a stray human line:
        # porcelain is what a hook parses, and a check that narrowed itself has
        # to say so THROUGH the contract its caller reads (BDL-UX #148).
        if commit_scope is not None:
            click.echo(f"scope\t\t\t\t{commit_scope.describe()}")
        for r in results:
            reason = r.get("reason", "ok")
            click.echo(
                f"{r['status']}\t{r['ref_id']}\t{r['doc_path']}\t{r['code_path']}\t{reason}"
            )
        for r in references:
            # ref_id/code_path columns are empty for a reference doc (no pairing).
            click.echo(f"{r['status']}\t\t{r['doc_path']}\t\t{r['reason']}")
        for u in unchecked:
            click.echo(f"unchecked\t{u['ref_id']}\t{u['doc_path']}\t\t{u['reason']}")
    else:
        if commit_scope is not None:
            click.echo(commit_scope.describe())
        if not results and not references and not unchecked:
            click.echo("No sync pairs found.")
        else:
            for r in results:
                marker = _STATUS_MARKER.get(str(r["status"]), "[ok]")
                reason = r.get("reason", "ok")
                details = r.get("details", "")

                if r["status"] == "missing":
                    click.echo(
                        f"  {marker} {r['ref_id']}: {r['doc_path']} "
                        f"({_MISSING_WHY[str(reason)]})"
                    )
                elif r["status"] == STATUS_EXEMPT:
                    click.echo(
                        f"  {marker} {r['ref_id']}: {r['doc_path']} <-> {r['code_path']} "
                        f"(not checked: {details or 'declared exempt from freshness'})"
                    )
                elif r["status"] == STATUS_UNVERIFIED:
                    click.echo(
                        f"  {marker} {r['ref_id']}: {r['doc_path']} <-> {r['code_path']} "
                        f"(not checked: no baseline — the index was rebuilt and git "
                        f"could not supply one)"
                    )
                elif reason == "untracked_files" and details:
                    click.echo(f"  {marker} {r['ref_id']}: {r['doc_path']} (untracked: {details})")
                elif reason == "missing_modules" and details:
                    click.echo(
                        f"  {marker} {r['ref_id']}: {r['doc_path']} (missing modules: {details})"
                    )
                elif reason == REASON_SECTION_NOT_IN_USE:
                    click.echo(
                        f"  {marker} required section(s) {details} — not carried "
                        f"by a majority of {r['ref_id']}, so no document is "
                        f"reported for them"
                    )
                elif reason == REASON_MISSING_SECTIONS:
                    click.echo(
                        f"  {marker} {r['ref_id']}: {r['doc_path']} "
                        f"(missing sections: {details})"
                    )
                elif r["status"] == "stale" and reason not in (
                    "ok",
                    "untracked_files",
                    "missing_modules",
                ):
                    click.echo(
                        f"  {marker} {r['ref_id']}: {r['doc_path']} "
                        f"<-> {r['code_path']} ({reason})"
                    )
                else:
                    click.echo(f"  {marker} {r['ref_id']}: {r['doc_path']} <-> {r['code_path']}")

            for r in references:
                marker = "[warn]" if r["status"] == "surface_drift" else "[ok]"
                if r["status"] == "surface_drift":
                    click.echo(
                        f"  {marker} {r['doc_path']} (surface drift: watches="
                        f"{r['watches']}; run `beadloom sync-update {r['doc_path']}`)"
                    )
                else:
                    click.echo(f"  {marker} {r['doc_path']} (watches={r['watches']})")

            for u in unchecked:
                click.echo(
                    f"  [warn] {u['ref_id']}: {u['doc_path']} "
                    f"(not checked: {_UNCHECKED_WHY[u['reason']].format(source=u['details'])})"
                )

            if surface.message:
                click.echo(f"  [warn] {surface.message}")

    if has_blocking:
        sys.exit(2)


# The four verdicts, in the reader's terms. ``[missing]`` and ``[not verified]``
# exist because they used to print ``[ok]`` (BDL-UX #174/#175).
_STATUS_MARKER = {
    STATUS_INCOMPLETE: "[warn]",
    "ok": "[ok]",
    "stale": "[stale]",
    "missing": "[missing]",
    "unverified": "[not verified]",
    # Unverifiable, excused and clean are three states, and an exempt row read
    # `[ok]` — the word for a comparison that happened (`beadloom-mr2l.76`).
    STATUS_EXEMPT: "[exempt]",
}

# What a ``missing`` verdict means, by reason.
_MISSING_WHY = {
    "doc_missing": "the linked doc file is gone",
    "code_missing": "the paired code file is gone",
    "declared_doc_missing": "declared in the graph, not on disk",
}

# Why a node that declares a doc contributes no sync pair, in the reader's terms.
_UNCHECKED_WHY = {
    "no_indexed_code": "no indexed code under '{source}'",
    "files_owned_by_nested_nodes": "every file under '{source}' belongs to a nested node",
    "no_source": "the node declares no source path",
}


def _build_sync_report(results: list[dict[str, str]]) -> str:
    """Build a Markdown report from sync-check results."""
    ok_count = sum(1 for r in results if r["status"] == "ok")
    stale_count = sum(1 for r in results if r["status"] == "stale")
    stale_pairs = [r for r in results if r["status"] == "stale"]

    lines: list[str] = [
        "## Beadloom Doc Sync Report",
        "",
        "| Status | Count |",
        "|--------|-------|",
        f"| OK | {ok_count} |",
        f"| Stale | {stale_count} |",
    ]

    if stale_pairs:
        lines.extend(
            [
                "",
                "### Stale Documents",
                "",
                "| Node | Doc | Changed Code |",
                "|------|-----|-------------|",
            ]
        )
        for r in stale_pairs:
            lines.append(f"| {r['ref_id']} | `{r['doc_path']}` | `{r['code_path']}` |")
        lines.extend(
            [
                "",
                "> Run `beadloom sync-update <ref_id>` to review and update.",
            ]
        )
    else:
        lines.extend(["", "All documentation is up to date."])

    return "\n".join(lines)


#: The codec the installed git hooks are written in. UTF-8 is the hook's own
#: contract — the templates below carry an em dash, git executes the file as
#: bytes, and every reader of it (an editor, a diff, the shell's error message)
#: assumes UTF-8. Left to ``locale.getpreferredencoding(False)`` it was the
#: image's decision instead, which is a wrong answer in both directions
#: (BDL-061.42: 30 of the 108 measured ASCII-leg failures came from this one
#: call site).
_HOOK_ENCODING = "utf-8"

#: The header both pre-commit templates open with, and the whole of the #118
#: repair in one place. The hook judges THE COMMIT: it reads what git says this
#: commit stages, and it states the tree it therefore did not judge. Serialising
#: *who* commits does not help — the merge slot orders the commits and leaves the
#: tree exactly as shared as it was — so the boundary has to be what each check
#: is asked about.
_HOOK_COMMIT_SCOPE = """\
# This hook judges THE COMMIT, not the working tree. In a tree shared by several
# agents -- the mode a multi-agent flow prescribes, not an exotic one -- a
# whole-tree check fails one agent's commit on a neighbour's half-written file,
# in a module the committer never opened (BDL-UX #118). The pre-push Beadloom
# Gate judges the whole tree, so nothing stops being enforced; what moves is WHEN
# a file is judged.
#
# Stated rather than assumed: the content read below is the WORKING-TREE content
# of the staged paths, not the staged blobs, so a partially staged file is judged
# including the part this commit leaves behind.

staged_py=$(git diff --cached --name-only --diff-filter=ACMR | grep -E '^(src|tests)/.*[.]py$')
outside=$(git diff --name-only | wc -l | tr -d ' ')
"""

_HOOK_TEMPLATE_WARN = """\
#!/bin/sh
# pre-commit hook managed by beadloom
""" + _HOOK_COMMIT_SCOPE + """
# --- Lint check (ruff), over the staged files only ---
if command -v uv >/dev/null 2>&1 && [ -n "$staged_py" ]; then
  echo "Running ruff check on the staged Python file(s)..."
  echo "$staged_py" | xargs uv run ruff check 2>/dev/null
  if [ $? -ne 0 ]; then
    echo "Warning: ruff lint violations in this commit"
  fi
fi

# --- Type check (mypy), over the staged files only ---
if command -v uv >/dev/null 2>&1 && [ -n "$staged_py" ]; then
  echo "Running mypy on the staged Python file(s)..."
  echo "$staged_py" | xargs uv run mypy 2>/dev/null
  if [ $? -ne 0 ]; then
    echo "Warning: mypy type errors in this commit"
  fi
fi

# --- Doc sync check, over the pairs this commit stages ---
stale=$(beadloom sync-check --staged --porcelain 2>/dev/null)
exit_code=$?

if [ $exit_code -eq 2 ]; then
  echo "Warning: stale documentation in this commit"
  echo "$stale"
  echo ""
  echo "Run: beadloom sync-update <ref_id> to update docs"
fi

if [ $exit_code -eq 1 ]; then
  echo "Warning: beadloom sync-check failed (index may be stale)"
fi

# --- What this commit did NOT judge ---
echo "$outside modified file(s) outside this commit were not judged here;"
echo "the pre-push Gate (beadloom ci) judges the whole tree."

# --- ACTIVE / tracker coherence ---
# Guarded no-op: only runs when BOTH `bd` and `beadloom` are installed. In any
# repo without `bd` (or without ACTIVE tables) this block does nothing and never
# blocks the commit. Auto-fixes the bead-status tables + tracked issues.jsonl
# and restages them so the commit is coherent by construction. `--stage` stages
# EXACTLY the reconciled ACTIVE.md(s) + the exported jsonl -- never an unrelated
# concurrently-edited doc in the same subtree.
if command -v bd >/dev/null 2>&1 && command -v beadloom >/dev/null 2>&1; then
  beadloom active-sync --stage >/dev/null 2>&1
fi
"""

_HOOK_TEMPLATE_BLOCK = """\
#!/bin/sh
# pre-commit hook managed by beadloom
failed=0
""" + _HOOK_COMMIT_SCOPE + """
# --- Lint check (ruff), over the staged files only ---
if command -v uv >/dev/null 2>&1 && [ -n "$staged_py" ]; then
  echo "Running ruff check on the staged Python file(s)..."
  echo "$staged_py" | xargs uv run ruff check 2>/dev/null
  if [ $? -ne 0 ]; then
    echo "Error: ruff lint violations in this commit — commit blocked"
    echo "Run: echo \"$staged_py\" | xargs uv run ruff check --fix"
    failed=1
  fi
fi

# --- Type check (mypy), over the staged files only ---
if command -v uv >/dev/null 2>&1 && [ -n "$staged_py" ]; then
  echo "Running mypy on the staged Python file(s)..."
  echo "$staged_py" | xargs uv run mypy 2>/dev/null
  if [ $? -ne 0 ]; then
    echo "Error: mypy type errors in this commit — commit blocked"
    failed=1
  fi
fi

# --- Doc sync check, over the pairs this commit stages ---
stale=$(beadloom sync-check --staged --porcelain 2>/dev/null)
exit_code=$?

if [ $exit_code -eq 2 ]; then
  echo "Error: stale documentation in this commit — commit blocked"
  echo "$stale"
  echo ""
  echo "Run: beadloom sync-update <ref_id> to update docs"
  failed=1
fi

if [ $exit_code -eq 1 ]; then
  echo "Warning: beadloom sync-check failed (index may be stale)"
fi

# --- What this commit did NOT judge ---
echo "$outside modified file(s) outside this commit were not judged here;"
echo "the pre-push Gate (beadloom ci) judges the whole tree."

# --- ACTIVE / tracker coherence ---
# Guarded no-op: only runs when BOTH `bd` and `beadloom` are installed. In any
# repo without `bd` (or without ACTIVE tables) this block does nothing and never
# blocks the commit. Auto-fixes the bead-status tables + tracked issues.jsonl
# and restages them so the commit is coherent by construction. `--stage` stages
# EXACTLY the reconciled ACTIVE.md(s) + the exported jsonl -- never an unrelated
# concurrently-edited doc in the same subtree.
if command -v bd >/dev/null 2>&1 && command -v beadloom >/dev/null 2>&1; then
  beadloom active-sync --stage >/dev/null 2>&1
fi

if [ $failed -ne 0 ]; then
  exit 1
fi
"""


# Pre-push hook: the AUTHORITATIVE blocking Beadloom Gate. Runs the full
# `beadloom ci` Gate (incremental reindex -> lint -> coverage-lint -> sync-check
# -> doctor) and exits non-zero to BLOCK the push on red. Guarded + fail-safe:
# in any repo without `beadloom` on PATH the hook is a safe no-op (never blocks).
# Idempotent (re-running install-hooks overwrites cleanly). `--no-verify` is the
# documented escape hatch. The pre-commit hook stays the lighter warn check; the
# full Gate lives here so it isn't duplicated on every commit.
_HOOK_TEMPLATE_PRE_PUSH = """\
#!/bin/sh
# pre-push hook managed by beadloom -- the blocking Beadloom Gate.

# Fail-safe: outside a Beadloom flow repo (no `beadloom` on PATH) this hook is a
# safe no-op so it never blocks a push in a repo that does not use Beadloom.
if ! command -v beadloom >/dev/null 2>&1; then
  exit 0
fi

echo "Running Beadloom Gate (beadloom ci)..."
beadloom ci
if [ $? -ne 0 ]; then
  echo ""
  echo "Beadloom Gate failed (docs stale / lint / coverage / doctor)."
  echo "Run the tech-writer (or /coordinator) to refresh docs, then re-push."
  echo "To override (discouraged): git push --no-verify"
  exit 1
fi
"""


# beadloom:domain=doc-sync
@main.command("install-hooks")
@click.option(
    "--mode",
    type=click.Choice(["warn", "block"]),
    default="warn",
    help="Hook mode: warn (default) or block commits on stale docs.",
)
@click.option("--remove", is_flag=True, help="Remove the selected hook(s).")
@click.option(
    "--pre-commit",
    "pre_commit",
    is_flag=True,
    help="Operate on the pre-commit hook only (default: both pre-commit + pre-push).",
)
@click.option(
    "--pre-push",
    "pre_push",
    is_flag=True,
    help="Operate on the pre-push Gate hook only (default: both pre-commit + pre-push).",
)
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
def install_hooks(
    *,
    mode: str,
    remove: bool,
    pre_commit: bool,
    pre_push: bool,
    project: Path | None,
) -> None:
    """Install or remove beadloom git hooks.

    By default installs BOTH the pre-commit hook (lighter warn/block check) and
    the pre-push hook (the authoritative blocking Beadloom Gate). Use
    ``--pre-commit`` / ``--pre-push`` to select one. ``--remove`` removes the
    selected hook(s).
    """
    import stat

    project_root = project or Path.cwd()
    hooks_dir = project_root / ".git" / "hooks"

    if not hooks_dir.exists():
        click.echo("Error: .git/hooks not found. Is this a git repository?", err=True)
        sys.exit(1)

    # No selector -> operate on both hooks.
    do_pre_commit = pre_commit or not (pre_commit or pre_push)
    do_pre_push = pre_push or not (pre_commit or pre_push)

    if remove:
        _remove_hooks(hooks_dir, pre_commit=do_pre_commit, pre_push=do_pre_push)
        return

    if do_pre_commit:
        template = _HOOK_TEMPLATE_BLOCK if mode == "block" else _HOOK_TEMPLATE_WARN
        _write_hook(hooks_dir / "pre-commit", template, stat)
        click.echo(f"Installed pre-commit hook (mode: {mode}).")
    if do_pre_push:
        _write_hook(hooks_dir / "pre-push", _HOOK_TEMPLATE_PRE_PUSH, stat)
        click.echo("Installed pre-push hook (Beadloom Gate, blocking).")


def _write_hook(hook_path: Path, template: str, stat_mod: ModuleType) -> None:
    """Write an executable git hook (idempotent overwrite), always as UTF-8.

    The encoding is stated rather than inherited: the templates above contain an
    em dash, and ``write_text()`` without ``encoding=`` uses
    ``locale.getpreferredencoding(False)``. Measured under the locale CI leg
    (BDL-061.42): on an ASCII image the write RAISES and ``install-hooks`` aborts
    having written nothing; on an ISO-8859-1 image nothing raises and the byte
    lands mangled inside an executable script the adopter then keeps. A hook is a
    file we generate for other programs to read, not prose in the operator's
    locale, so UTF-8 is its contract.
    """
    hook_path.write_text(template, encoding=_HOOK_ENCODING)
    hook_path.chmod(
        hook_path.stat().st_mode | stat_mod.S_IXUSR | stat_mod.S_IXGRP | stat_mod.S_IXOTH
    )


def _remove_hooks(hooks_dir: Path, *, pre_commit: bool, pre_push: bool) -> None:
    """Remove the selected git hook(s); report what was removed."""
    targets: list[str] = []
    if pre_commit:
        targets.append("pre-commit")
    if pre_push:
        targets.append("pre-push")
    removed_any = False
    for name in targets:
        path = hooks_dir / name
        if path.exists():
            path.unlink()
            click.echo(f"Removed {name} hook.")
            removed_any = True
    if not removed_any:
        click.echo("No matching hook to remove.")


# beadloom:component=active-table
def _bd_statuses_from_list(beads: list[dict[str, object]]) -> dict[str, str]:
    """Build ``{bead_id -> status_token}`` from a ``bd list --json`` payload.

    Each bead's own ``status`` is taken verbatim, except that an ``open`` bead
    with at least one *open blocker* is reported as ``"blocked"`` so the ACTIVE
    table reflects readiness. A blocker is a ``dependencies`` entry of type
    ``blocks`` whose target bead is not ``closed`` (parent-child links never
    block). Malformed entries are skipped defensively (best-effort, never raises).
    """
    statuses: dict[str, str] = {}
    blockers: dict[str, list[str]] = {}
    for bead in beads:
        bead_id = bead.get("id")
        status = bead.get("status")
        if not isinstance(bead_id, str) or not isinstance(status, str):
            continue
        statuses[bead_id] = status
        deps = bead.get("dependencies")
        targets: list[str] = []
        if isinstance(deps, list):
            for dep in deps:
                if not isinstance(dep, dict) or dep.get("type") != "blocks":
                    continue
                target = dep.get("depends_on_id")
                if isinstance(target, str):
                    targets.append(target)
        blockers[bead_id] = targets

    for bead_id, status in list(statuses.items()):
        if status != "open":
            continue
        if any(statuses.get(t) not in (None, "closed") for t in blockers.get(bead_id, [])):
            statuses[bead_id] = "blocked"
    return statuses


# beadloom:component=active-table
def _query_bd_statuses(project_root: Path) -> dict[str, str] | None:
    """Return bead-id -> status from ``bd list --json``, or None if bd unavailable.

    Funnels through :func:`bd_seam.run_bd` (mockable). Returns ``None`` when ``bd``
    is not installed (``BdUnavailableError``) or the call/JSON fails — the caller
    treats ``None`` as "skip, no-op" so a non-flow repo is never affected.
    """
    from beadloom.services.bd_seam import BdUnavailableError, run_bd

    try:
        result = run_bd(["list", "--json"], cwd=str(project_root))
    except BdUnavailableError:
        return None
    if not result.ok:
        return None
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, list):
        return None
    beads = [b for b in payload if isinstance(b, dict)]
    return _bd_statuses_from_list(beads)


# beadloom:component=active-table
def _jsonl_is_tracked(project_root: Path) -> bool:
    """True when ``.beads/issues.jsonl`` exists AND is git-tracked in *project_root*."""
    import subprocess

    jsonl = project_root / ".beads" / "issues.jsonl"
    if not jsonl.is_file():
        return False
    try:
        # Fixed argv, no shell; queries the index for the tracked path.
        # NOT decoded: only the exit status is read below, so `text=True` bought
        # nothing and cost a codec — under an ASCII image git's own message about
        # a non-ASCII path made this raise where a boolean was expected. Bytes are
        # the honest type for an answer nobody reads (BDL-061.42).
        completed = subprocess.run(
            ["git", "ls-files", "--error-unmatch", ".beads/issues.jsonl"],  # noqa: S607
            cwd=project_root,
            capture_output=True,
            check=False,
        )
    except OSError:
        return False
    return completed.returncode == 0


# beadloom:component=active-table
def _export_jsonl(project_root: Path) -> bool:
    """Best-effort ``bd export -o .beads/issues.jsonl`` when the jsonl is tracked.

    Keeps the tracked tracker artifact honest across branch/squash-merge (the
    bd-close jsonl-drift fix). Skips silently if ``bd`` is unavailable or the
    jsonl isn't tracked — never raises. Returns ``True`` when ``bd export`` was
    actually run (so a caller may stage the exact jsonl path), else ``False``.
    """
    from beadloom.services.bd_seam import BdUnavailableError, run_bd

    if not _jsonl_is_tracked(project_root):
        return False
    try:
        run_bd(["export", "-o", ".beads/issues.jsonl"], cwd=str(project_root))
    except BdUnavailableError:
        return False
    return True


# beadloom:component=active-table
def _stage_reconciled(
    project_root: Path,
    changed_files: list[Path],
    *,
    exported_jsonl: bool,
) -> None:
    """``git add`` EXACTLY the reconciled ACTIVE.md paths (+ the exported jsonl).

    Replaces the old broad ``git add -u .claude/development/docs/features`` in the
    hook, which over-staged any concurrently-edited sibling doc in that subtree.
    Best-effort and guarded: no paths → no-op; no git / failure → silently skip
    (never raises, never stages anything beyond the supplied paths).
    """
    import subprocess

    paths = [str(p) for p in changed_files]
    if exported_jsonl:
        paths.append(".beads/issues.jsonl")
    if not paths:
        return
    try:
        # Fixed argv (no shell); `--` guards the explicit, reconciled paths only.
        subprocess.run(  # noqa: S603
            ["git", "add", "--", *paths],  # noqa: S607
            cwd=project_root,
            capture_output=True,
            check=False,
        )
    except OSError:
        return


# beadloom:component=active-table
@main.command("active-sync")
@click.option("--epic", "epic", default=None, help="Reconcile only this epic's ACTIVE.md.")
@click.option(
    "--check",
    "check_only",
    is_flag=True,
    help="Report drift without writing; exit 1 if any drift, 0 if clean.",
)
@click.option("--json", "output_json", is_flag=True, help="Machine-readable JSON output.")
@click.option(
    "--no-export",
    "no_export",
    is_flag=True,
    help="Skip the `bd export` jsonl sync (fix mode only).",
)
@click.option(
    "--stage",
    "stage",
    is_flag=True,
    help="git add EXACTLY the reconciled ACTIVE.md(s) + the exported jsonl "
    "(fix mode only); never stages unrelated files. Best-effort (no git → skip).",
)
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
def active_sync(
    *,
    epic: str | None,
    check_only: bool,
    output_json: bool,
    no_export: bool,
    stage: bool,
    project: Path | None,
) -> None:
    """Reconcile ACTIVE.md bead-status tables from ``bd`` (the source of truth).

    For each epic's ACTIVE.md, rewrites the bead-status table's Status cells to
    match ``bd`` (rich coordinator notes are preserved when the state agrees).
    Default = fix mode (writes + syncs the tracked ``.beads/issues.jsonl`` via
    ``bd export``); ``--check`` reports drift without writing (exit 1 on drift).

    No-op contract: if ``bd`` is unavailable OR there is no ACTIVE file with a
    bead-status table, this exits 0 and writes nothing (a non-flow repo is never
    affected). With ``--stage`` (fix mode), ``git add`` is run on EXACTLY the
    reconciled ACTIVE.md paths + the exported jsonl — nothing else (so a
    concurrently-edited sibling doc is never collaterally staged).
    """
    from beadloom.application.active_table import reconcile_active_tables

    project_root = project or Path.cwd()

    if not _has_active_table(project_root, epic):
        click.echo("active-sync: no ACTIVE.md bead tables — nothing to reconcile (skipped).")
        return

    bd_statuses = _query_bd_statuses(project_root)
    if bd_statuses is None:
        click.echo("active-sync: bd unavailable — skipped.")
        return

    if check_only:
        _active_sync_check(project_root, bd_statuses, epic=epic, output_json=output_json)
        return

    result = reconcile_active_tables(project_root, bd_statuses, epic=epic)
    exported = False if no_export else _export_jsonl(project_root)
    if stage:
        _stage_reconciled(project_root, result.changed_files, exported_jsonl=exported)
    _emit_active_sync(result, output_json=output_json, check=False)


# beadloom:component=active-table
def _has_active_table(project_root: Path, epic: str | None) -> bool:
    """True when at least one in-scope ACTIVE.md contains a bead-status table."""
    from beadloom.application.active_table import (
        _discover_active_files,
        _find_status_column,
    )

    for path in _discover_active_files(project_root, epic):
        try:
            lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        except OSError:
            continue
        if _find_status_column(lines) is not None:
            return True
    return False


# beadloom:component=active-table
def _active_sync_check(
    project_root: Path,
    bd_statuses: dict[str, str],
    *,
    epic: str | None,
    output_json: bool,
) -> None:
    """``--check`` mode: detect drift on a throwaway copy, never write; exit 1 on drift."""
    import shutil
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        sandbox = Path(tmp) / "proj"
        src = project_root / ".claude" / "development" / "docs" / "features"
        if src.is_dir():
            shutil.copytree(src, sandbox / ".claude" / "development" / "docs" / "features")
        from beadloom.application.active_table import reconcile_active_tables

        result = reconcile_active_tables(sandbox, bd_statuses, epic=epic)
    drift = bool(result.drifted_rows)
    _emit_active_sync(result, output_json=output_json, check=True)
    if drift:
        sys.exit(1)


# beadloom:component=active-table
def _emit_active_sync(
    result: ReconcileResult,
    *,
    output_json: bool,
    check: bool,
) -> None:
    """Print the reconcile outcome (JSON or human-readable)."""
    if output_json:
        payload = {
            "changed_files": [str(p) for p in result.changed_files],
            "drifted_rows": [
                {"path": str(p), "bead_id": bid, "old": old, "new": new}
                for (p, bid, old, new) in result.drifted_rows
            ],
        }
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    if not result.drifted_rows:
        click.echo("active-sync: ACTIVE tables already coherent.")
        return
    verb = "would update" if check else "updated"
    click.echo(f"active-sync: {verb} {len(result.drifted_rows)} row(s):")
    for path, bead_id, old, new in result.drifted_rows:
        click.echo(f"  {path}: {bead_id}  {old!r} -> {new!r}")


# beadloom:domain=doc-sync
def _mark_synced_noninteractive(
    conn: sqlite3.Connection,
    project_root: Path,
    *,
    ref_id: str | None,
    all_refs: bool,
) -> None:
    """Re-baseline freshness for a ref (or every stale ref) without prompting.

    Wraps ``mark_synced_by_ref``: recomputes hashes + symbols_hash and records
    ``status='ok'``. Prints a concise, deterministic summary and exits 0.
    """
    from beadloom.doc_sync.engine import (
        check_sync,
        mark_reference_synced,
        mark_synced_by_ref,
    )

    if all_refs:
        results = check_sync(conn, project_root=project_root)
        stale_refs = sorted({r["ref_id"] for r in results if r["status"] == "stale"})
        total = 0
        for ref in stale_refs:
            rows = mark_synced_by_ref(conn, ref, project_root)
            total += rows
            click.echo(f"Re-baselined {ref}: {rows} pair(s).")
        # Also clear any reference-doc surface drift (BDL-057 Layer 2; advisory).
        ref_docs = mark_reference_synced(conn, None, project_root, all_docs=True)
        if not stale_refs and not ref_docs:
            click.echo("No stale refs to re-baseline.")
            return
        if stale_refs:
            click.echo(f"Marked {len(stale_refs)} ref(s) synced ({total} pair(s) total).")
        if ref_docs:
            click.echo(f"Re-baselined {ref_docs} reference doc(s).")
        return

    assert ref_id is not None  # guaranteed by the command-level validation
    # A reference doc (watches annotation) is addressed by its doc_path; try that
    # first so `sync-update docs/architecture.md --yes` clears surface drift.
    ref_docs = mark_reference_synced(conn, ref_id, project_root)
    if ref_docs:
        click.echo(f"Re-baselined reference doc {ref_id}.")
        return

    rows = mark_synced_by_ref(conn, ref_id, project_root)
    if rows == 0:
        click.echo(f"No sync pairs found for {ref_id}; nothing to re-baseline.")
        return
    click.echo(f"Re-baselined {ref_id}: {rows} pair(s).")


@main.command("sync-update")
@click.argument("ref_id", required=False)
@click.option("--check", "check_only", is_flag=True, help="Only show status, don't open editor.")
@click.option(
    "--yes",
    "-y",
    "assume_yes",
    is_flag=True,
    help="Non-interactive: re-baseline freshness without an editor or prompt.",
)
@click.option(
    "--all",
    "all_refs",
    is_flag=True,
    help="With --yes: re-baseline every currently-stale ref (for the fixpoint loop).",
)
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
def sync_update(
    ref_id: str | None,
    *,
    check_only: bool,
    assume_yes: bool,
    all_refs: bool,
    project: Path | None,
) -> None:
    """Show sync status and update docs for a ref_id.

    Use --check to only display status without opening an editor.

    Use --yes (-y) for a non-interactive re-baseline (no editor/prompt): records
    that the doc(s) match the code now. Add --all to re-baseline every stale ref
    in one call (useful for an automated fixpoint loop).

    For automated doc updates, use your AI agent (Claude Code, Cursor, etc.)
    with Beadloom's MCP tools (update_node, mark_synced).
    """
    from beadloom.doc_sync.engine import check_sync
    from beadloom.infrastructure.db import open_db

    if all_refs and not assume_yes:
        raise click.UsageError("--all requires --yes (non-interactive only).")
    if all_refs and ref_id is not None:
        raise click.UsageError("--all and an explicit REF_ID are mutually exclusive.")
    if not all_refs and ref_id is None:
        raise click.UsageError("Provide a REF_ID (or use --all with --yes).")

    project_root = project or Path.cwd()
    db_path = project_root / ".beadloom" / "beadloom.db"

    if not db_path.exists():
        click.echo("Error: database not found. Run `beadloom reindex` first.", err=True)
        sys.exit(1)

    conn = open_db(db_path)

    if assume_yes:
        _mark_synced_noninteractive(conn, project_root, ref_id=ref_id, all_refs=all_refs)
        conn.close()
        return

    results = check_sync(conn, project_root=project_root)
    filtered = [r for r in results if r["ref_id"] == ref_id]

    if not filtered:
        # No symbol pair matched. The id may instead be a reference doc
        # (BDL-057 Layer 2) addressed by its doc_path.
        #
        # `--check` is answered FIRST. This branch used to re-baseline before
        # the `check_only` guard below could be reached, so the flag whose whole
        # contract is "tell me, do not change anything" cleared the very drift it
        # was asked to describe, and the next `sync-check` read clean for a
        # reason nobody recorded (BDL-UX #189 — #147's defect in another
        # command, and #163 reached by accident rather than by choice).
        from beadloom.doc_sync.engine import (
            describe_reference_doc,
            mark_reference_synced,
        )

        if check_only:
            report = describe_reference_doc(conn, ref_id, project_root)
            conn.close()
            if report is None:
                click.echo(f"No sync pairs found for {ref_id}.")
                return
            marker = "[surface drift]" if report["status"] != "ok" else "[ok]"
            click.echo(
                f"  {marker} {report['doc_path']} watches "
                f"{', '.join(report['watches'])}"
            )
            return

        ref_docs = mark_reference_synced(conn, ref_id, project_root)
        if ref_docs:
            click.echo(f"Re-baselined reference doc {ref_id}.")
        else:
            click.echo(f"No sync pairs found for {ref_id}.")
        conn.close()
        return

    stale = [r for r in filtered if r["status"] == "stale"]

    if check_only:
        for r in filtered:
            marker = "[stale]" if r["status"] == "stale" else "[ok]"
            click.echo(f"  {marker} {r['doc_path']} <-> {r['code_path']}")
        conn.close()
        return

    if not stale:
        click.echo(f"All docs for {ref_id} are up to date.")
        conn.close()
        return

    # Interactive mode: open editor for each stale doc.
    from beadloom.doc_sync.engine import mark_synced

    # Group stale pairs by doc_path (one doc may have multiple code files).
    doc_stale: dict[str, list[dict[str, str]]] = {}
    for r in stale:
        doc_stale.setdefault(r["doc_path"], []).append(r)

    for doc_path, pairs in doc_stale.items():
        click.echo(f"\n  Doc: {doc_path}")
        for r in pairs:
            click.echo(f"    Code changed: {r['code_path']}")

        doc_full_path = project_root / "docs" / doc_path
        if not doc_full_path.exists():
            click.echo(f"    Warning: {doc_full_path} does not exist, skipping.")
            continue

        if not click.confirm(f"\n  Open {doc_path} in editor?", default=True):
            continue

        # Open in $EDITOR.
        click.edit(filename=str(doc_full_path))

        # Mark all pairs for this doc as synced.
        for r in pairs:
            mark_synced(conn, r["doc_path"], r["code_path"], project_root)
        click.echo(f"  Synced: {doc_path}")

    conn.close()
