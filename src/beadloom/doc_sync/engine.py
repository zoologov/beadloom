"""Sync engine: doc-code synchronization state management."""

# beadloom:domain=doc-sync
# beadloom:feature=sync-check

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from beadloom.doc_sync.declared_docs import find_missing_declared_docs
from beadloom.doc_sync.doc_shape import (
    REASON_MISSING_SECTIONS,
    REASON_SECTION_NOT_IN_USE,
    STATUS_INCOMPLETE,
    check_section_shape,
)
from beadloom.doc_sync.git_baseline import changed_paths
from beadloom.infrastructure.doc_roots import (
    SPACE_WORKING,
    DocSpaces,
    resolve_doc_spaces,
    resolve_docs_dir,
)
from beadloom.infrastructure.repository import covering_prefix, get_owned_code_files

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Collection, Mapping


def _compute_symbols_hash(
    conn: sqlite3.Connection, ref_id: str, *, file_path: str | None = None
) -> str:
    """SHA-256 of the sorted ``code_symbols`` for *ref_id*, optionally in one file.

    Without *file_path* this is the NODE's symbol surface. With it, the surface
    of that one file under this node — the granularity at which a doc-code pair
    actually makes its claim, and the fact BDL-UX #182 says the staleness
    verdict must be computed against.

    Returns an empty string when nothing matches. For the node form that means
    an unlinked node; for the file form it means this file contributes no
    annotated symbol to the node (it was paired through the node's declared
    ``source``, not through an annotation), and the caller must NOT read that as
    "unchanged".
    """
    sql = (
        "SELECT file_path, symbol_name, kind FROM code_symbols WHERE annotations LIKE ?"
    )
    params: tuple[str, ...] = (f'%"{ref_id}"%',)
    if file_path is not None:
        sql += " AND file_path = ?"
        params = (*params, file_path)
    rows = conn.execute(sql + " ORDER BY file_path, symbol_name", params).fetchall()
    if not rows:
        return ""
    data = "|".join(f"{r['file_path']}:{r['symbol_name']}:{r['kind']}" for r in rows)
    return hashlib.sha256(data.encode()).hexdigest()


@dataclass
class SyncPair:
    """A doc-code pair linked through a shared ref_id."""

    ref_id: str
    doc_path: str
    code_path: str
    doc_hash: str
    code_hash: str


def _annotated_files_by_ref(conn: sqlite3.Connection) -> dict[str, list[tuple[str, str]]]:
    """Map ``ref_id -> [(file_path, file_hash)]`` from code-symbol annotations.

    One pass over ``code_symbols``; the previous shape re-scanned the whole
    table once per linked doc.
    """
    by_ref: dict[str, list[tuple[str, str]]] = {}
    seen: set[tuple[str, str]] = set()
    for sym in conn.execute("SELECT file_path, file_hash, annotations FROM code_symbols"):
        annotations: dict[str, Any] = json.loads(sym["annotations"])
        file_path = str(sym["file_path"])
        for value in annotations.values():
            if not isinstance(value, str) or (value, file_path) in seen:
                continue
            seen.add((value, file_path))
            by_ref.setdefault(value, []).append((file_path, str(sym["file_hash"])))
    return by_ref


# beadloom:domain=doc-sync
def build_sync_state(conn: sqlite3.Connection) -> list[SyncPair]:
    """Build sync pairs for every node that has a linked doc AND indexed code.

    A node's code files are found first through symbol annotations
    (``# beadloom:<kind>=<ref>``) and, when those yield nothing, through the
    files the node's declared ``source`` OWNS. The fallback is the fix for
    BDL-UX #146: pairing keyed on annotations alone meant a node whose
    annotation sat somewhere tree-sitter does not read it as a comment — or
    which simply declared ``source:`` without annotating — contributed no pairs
    at all, and a freshness gate with no pairs reports "clean" for files it
    never opened.

    Nodes that still yield no pair are not silently dropped: see
    :func:`find_unchecked_doc_nodes`, which names them.
    """
    doc_rows = conn.execute(
        "SELECT ref_id, path, hash FROM docs WHERE ref_id IS NOT NULL"
    ).fetchall()
    if not doc_rows:
        return []

    annotated = _annotated_files_by_ref(conn)
    pairs: list[SyncPair] = []

    for doc_row in doc_rows:
        ref_id = str(doc_row["ref_id"])
        code_files = annotated.get(ref_id) or get_owned_code_files(conn, ref_id)
        pairs.extend(
            SyncPair(
                ref_id=ref_id,
                doc_path=str(doc_row["path"]),
                code_path=code_path,
                doc_hash=str(doc_row["hash"]),
                code_hash=code_hash,
            )
            for code_path, code_hash in code_files
        )

    return pairs


def find_unchecked_doc_nodes(conn: sqlite3.Connection) -> list[dict[str, str]]:
    """Nodes that declare a doc but contribute no sync pair.

    A freshness gate must never let "clean" stand for "nothing was looked at"
    (BDL-UX #146). Everything reachable is paired by :func:`build_sync_state`;
    what remains here is the honest residue — a doc whose node has no indexed
    code under it — and it is reported rather than dropped.

    Advisory only: this never changes an exit code, so a project that is green
    today does not turn red on upgrade.
    """
    paired = {str(row["ref_id"]) for row in conn.execute("SELECT DISTINCT ref_id FROM sync_state")}
    rows = conn.execute(
        "SELECT DISTINCT d.ref_id AS ref_id, d.path AS doc_path, n.source AS source "
        "FROM docs d JOIN nodes n ON n.ref_id = d.ref_id "
        "WHERE d.ref_id IS NOT NULL ORDER BY d.ref_id, d.path"
    ).fetchall()
    return [
        {
            "ref_id": str(row["ref_id"]),
            "doc_path": str(row["doc_path"]),
            **_unchecked_reason(conn, str(row["source"] or "")),
        }
        for row in rows
        if str(row["ref_id"]) not in paired
    ]


def _unchecked_reason(conn: sqlite3.Connection, source: str) -> dict[str, str]:
    """Say WHY a node contributes no pair, distinguishing the two causes.

    "No indexed code under X" would be false for a container whose every file
    belongs to a nested node — the reader would go looking for missing code
    that is in fact indexed, just owned elsewhere. The two cases get different
    words because they call for different action: index the code, or nothing.

    Both questions are asked of ``file_index``, not of ``code_symbols``, since
    BDL-061.50. Keyed on symbols, this branch answered ``no_indexed_code`` for
    ``graph-reads`` — a fully indexed 75-line re-export facade with no top-level
    ``def`` — and sent the reader hunting for missing code (review .7 MAJOR 3).
    It was the ONE place in this repository where the reason was exercised, and
    naming the residue accurately is the whole mechanism by which "clean means
    checked, and where it cannot, it says so" is worth anything.
    """
    if not source:
        return {"reason": "no_source", "details": ""}
    prefix = covering_prefix(source)
    if prefix.endswith("/"):
        indexed = conn.execute(
            "SELECT COUNT(*) FROM file_index WHERE kind = 'code' AND path LIKE ?",
            (f"{prefix}%",),
        ).fetchone()
    else:
        indexed = conn.execute(
            "SELECT COUNT(*) FROM file_index WHERE kind = 'code' AND path = ?",
            (source,),
        ).fetchone()
    if indexed is not None and int(indexed[0]) > 0:
        return {"reason": "files_owned_by_nested_nodes", "details": source}
    return {"reason": "no_indexed_code", "details": source}


#: The one rule by which **both** sides of every hash comparison in this module
#: are decoded: the working tree and the content at a git ref.
#:
#: The codec is stated because the alternative is ``text=True``, which consults
#: ``locale.getpreferredencoding(False)`` -- the image speaking, not the tool --
#: while the working-tree side has always read UTF-8. A comparison whose two
#: sides are decoded by different rules reports a difference that is an artefact
#: of the environment: MEASURED on this repo with ``docs/architecture.md``
#: unchanged at HEAD, an ambient latin-1 made ``sync-check --since`` report drift
#: in a file nobody touched, and an ambient ascii raised an uncaught
#: ``UnicodeDecodeError`` out of a command that runs inside ``beadloom ci``.
#:
#: ``surrogateescape`` rather than ``strict`` because the Gate must have an
#: answer for every file: bytes that are not UTF-8 round-trip to exactly
#: themselves, so the digest stays the digest of the file's own bytes and one
#: latin-1 source file cannot crash ``sync-check``. ``replace`` is rejected here
#: for the usual reason -- it is not injective, so two different files could
#: hash equal, which is a comparison handed a wrong answer.
_TEXT_CODEC = "utf-8"
_TEXT_ERRORS = "surrogateescape"


def _file_hash(path: Path) -> str | None:
    """Compute SHA-256 hash of a file, or None if file doesn't exist."""
    if not path.is_file():
        return None
    return _hash_text(path.read_text(encoding=_TEXT_CODEC, errors=_TEXT_ERRORS))


#: The four verdicts a pair can carry, and the distinction the whole of BDL-UX
#: #174/#175 turns on: ``ok`` and ``stale`` are outcomes of a comparison that
#: HAPPENED, while ``missing`` (the file is gone) and ``unverified`` (there was
#: nothing to compare against) are states in which the checker cannot know.
#: *Unverifiable is not clean*, and the two must not print the same word.
STATUS_OK = "ok"
STATUS_STALE = "stale"
STATUS_MISSING = "missing"
STATUS_UNVERIFIED = "unverified"

#: A pair whose document is in the WORKING space and is exempt from freshness by
#: DECLARATION (BDL-061 S5). Not ``ok`` — nothing was verified — and deliberately
#: absent from :data:`BLOCKING_STATUSES`: an ACTIVE.md records progress within a
#: bead rather than what the code is, so holding it against the code would
#: compare a document to something it never described. The exemption is read from
#: ``doc_roots`` and never inferred from a missing pair, because an absence is
#: evidence of nothing and deleting a pair must not make a check quieter.
STATUS_EXEMPT = "exempt"

#: Why an exempt pair was not checked — one reason token, so a caller reads
#: the same field it reads for every other outcome.
REASON_WORKING_SPACE = "working_space"

#: This pair's OWN code file changed its symbol surface. The document describes
#: something that moved, the writer can see what moved, and revising the document
#: is an act with evidence behind it.
REASON_SYMBOLS_CHANGED = "symbols_changed"

#: A DIFFERENT code file of the same node changed its symbol surface; this pair's
#: own file did not. The pair is ``unverified`` rather than ``stale`` because the
#: comparison it can make came out equal, and the one it cannot make — whether
#: the shared document still describes the node — is not a fact about this file.
#:
#: The distinction is the whole of BDL-UX #182. While the follower printed
#: ``stale/symbols_changed``, the only action available for it was re-attestation
#: without evidence (#163), because nothing about its file had changed to revise
#: the document against. Measured on this repository: one new package made 72
#: pairs stale and 10 of them named a modified file.
REASON_SIBLING_SYMBOLS_CHANGED = "sibling_symbols_changed"


def _exempt_reason(doc_path: str, spaces: DocSpaces) -> str | None:
    """The declared reason *doc_path* is exempt from freshness, or ``None``.

    A skip always says why (this epic's S1 discipline), so the declaration's
    own reason travels with the row. An exemption declared without one is a
    config error reported by ``docs spaces``; it still applies here, because
    making the remedy for a missing sentence a wave of stale documents would
    teach a reader to delete the declaration instead of writing the sentence.
    """
    if not spaces.working.exempt_from_freshness:
        return None
    # ONE spelling. A `sync_state` row names its document relative to the docs
    # directory and every root glob is written relative to the project, so
    # asking with the row's own spelling asked a different question from the one
    # the spaces report asks about the same file (`beadloom-mr2l.75`).
    if spaces.space_of(spaces.project_path(doc_path)) != SPACE_WORKING:
        return None
    return spaces.working.reason or "declared exempt without a stated reason"

#: Which baseline produced a verdict. Reported on every pair so a green result
#: says what it was green against, instead of printing a count that means
#: nothing (BDL-UX #175).
BASELINE_INDEX = "index"
BASELINE_GIT = "git:HEAD"
BASELINE_NONE = "none"

#: Statuses that must fail a gate: the tree does not meet the bar (``stale``) or
#: the thing to check is gone (``missing``). ``unverified`` is deliberately NOT
#: here — it is reported by name and never counted as fresh, but a project that
#: cannot supply a baseline is not thereby broken.
BLOCKING_STATUSES = frozenset({STATUS_STALE, STATUS_MISSING})

#: Re-exported so a caller that already imports the status vocabulary from the
#: engine finds the structural one beside the five content ones, rather than
#: having to know which module each verdict was born in.
_SHAPE_VOCABULARY = (
    STATUS_INCOMPLETE,
    REASON_MISSING_SECTIONS,
    REASON_SECTION_NOT_IN_USE,
)

#: Where a pair's stored baseline came from, written by the reindex that built
#: it. ``index_build`` is a baseline copied from the tree at build time and
#: therefore worth nothing on its own; ``carried`` came from an earlier index
#: generation; ``attested`` followed an observed doc edit or an explicit
#: ``sync-update``. The vocabulary lives in the domain that interprets it.
BASELINE_SOURCE_INDEX_BUILD = "index_build"
BASELINE_SOURCE_CARRIED = "carried"
BASELINE_SOURCE_ATTESTED = "attested"

#: Sentinel: the git baseline has not been consulted yet. Distinct from ``None``,
#: which is git's own answer ("I cannot tell you"), so an unavailable git is
#: asked once per run rather than once per pair.
_UNREAD: Any = object()


def _files_whose_symbols_moved(conn: sqlite3.Connection, ref_id: str) -> tuple[str, ...]:
    """The node's own code files whose symbol surface differs from its baseline.

    A follower pair is told which file to look at instead of being handed
    ``sync-update`` for a document nobody has grounds to re-attest. Two
    populations count as moved: a paired file whose file-level hash no longer
    matches, and a file the node has gained since the baseline — the arrival is
    exactly what moved the node hash, so leaving it unnamed would report an
    effect with no cause.
    """
    baselined: dict[str, str] = {
        str(row["code_path"]): str(row["file_symbols_hash"] or "")
        for row in conn.execute(
            "SELECT code_path, file_symbols_hash FROM sync_state WHERE ref_id = ?",
            (ref_id,),
        )
    }
    moved = {
        code_path
        for code_path, stored in baselined.items()
        if stored and _compute_symbols_hash(conn, ref_id, file_path=code_path) != stored
    }
    moved |= {
        str(row["file_path"])
        for row in conn.execute(
            "SELECT DISTINCT file_path FROM code_symbols WHERE annotations LIKE ?",
            (f'%"{ref_id}"%',),
        )
        if str(row["file_path"]) not in baselined
    }
    return tuple(sorted(moved))


def _symbol_drift_verdict(
    conn: sqlite3.Connection,
    ref_id: str,
    code_path: str,
    stored_file_symbols: str,
    moved: tuple[str, ...],
) -> tuple[str, str, str]:
    """Verdict for a pair whose NODE's symbol surface moved: did it move here?

    A row with no file-level baseline (an index written before BDL-061 S6, or a
    file paired through the node's declared ``source`` rather than through an
    annotation) keeps the node-level answer. Reading a missing fact as
    "unchanged" would make an un-rebuilt index quieter than a rebuilt one, which
    is the one failure worse than the noise this replaces.
    """
    if not stored_file_symbols:
        return STATUS_STALE, REASON_SYMBOLS_CHANGED, ""
    if _compute_symbols_hash(conn, ref_id, file_path=code_path) != stored_file_symbols:
        return STATUS_STALE, REASON_SYMBOLS_CHANGED, ""
    others = ", ".join(Path(f).name for f in moved if f != code_path)
    return STATUS_UNVERIFIED, REASON_SIBLING_SYMBOLS_CHANGED, others


def _missing_side(current_doc_hash: str | None, current_code_hash: str | None) -> str | None:
    """Which side of the pair no longer exists on disk, if either.

    A pair whose file is gone used to be skipped by both hash comparisons and
    fall through as ``ok`` — "the gate is defeated by deleting documentation"
    (BDL-UX #174), from the other side.
    """
    if current_doc_hash is None:
        return "doc_missing"
    if current_code_hash is None:
        return "code_missing"
    return None


def _corroborate_with_git(
    doc_path: str, code_path: str, changed: frozenset[str] | None, docs_dir: str
) -> tuple[str, str, str]:
    """Verdict for a pair whose only baseline is the tree the index was built from.

    Such a pair compares equal to its baseline by construction, so the stored
    answer is worthless and git is asked instead: code that differs from ``HEAD``
    while its doc does not is drift the rebuild absorbed. When git cannot answer
    the pair is ``unverified`` — reported, never green by default.
    """
    if changed is None:
        return STATUS_UNVERIFIED, "no_baseline", BASELINE_NONE
    doc_changed = str(Path(docs_dir) / doc_path) in changed
    if code_path in changed and not doc_changed:
        return STATUS_STALE, "hash_changed_since_head", BASELINE_GIT
    return STATUS_OK, "ok", BASELINE_GIT


def check_sync(
    conn: sqlite3.Connection,
    project_root: Path | None = None,
    *,
    section_requirements: Mapping[str, tuple[str, ...]] | None = None,
) -> list[dict[str, Any]]:
    """Check sync_state entries against actual file hashes on disk.

    Reads files directly from disk to detect changes since last sync,
    independent of whether reindex has been run.  Also runs source
    coverage and doc coverage checks to catch untracked files and
    missing module mentions.

    Parameters
    ----------
    conn:
        Open SQLite connection.
    project_root:
        Project root directory. If None, inferred from DB path.
    section_requirements:
        Required document sections keyed by GRAPH node kind, from
        :func:`beadloom.onboarding.doc_templates.required_sections_by_node_kind`.
        ``None`` means structure is NOT checked — the reason is passed in rather
        than read here because the templates live in the ``onboarding`` peer
        domain, which this one must not import.

    Returns list of dicts with doc_path, code_path, ref_id, status,
    reason, and optional details.
    """
    # An empty sync_state is NOT a clean project: phases 2 and 3 below check
    # doc coverage against files on disk and need no pairs to do it. Returning
    # early here meant a project where nothing paired skipped every check and
    # printed a green "No sync pairs found" (BDL-UX #146).
    sync_rows = conn.execute("SELECT * FROM sync_state").fetchall()

    # Infer project root from database path if not provided.
    if project_root is None:
        db_path = conn.execute("PRAGMA database_list").fetchone()[2]
        project_root = Path(db_path).parent.parent  # .beadloom/beadloom.db → project

    results: list[dict[str, Any]] = []
    # Read at most once per run, and only if some pair actually needs it.
    git_changed: frozenset[str] | None = _UNREAD
    spaces = resolve_doc_spaces(project_root)
    # Which of a node's files moved their symbols, computed at most once per
    # node: every pair of that node asks the same question about the same set.
    moved_by_ref: dict[str, tuple[str, ...]] = {}

    for row in sync_rows:
        doc_path = row["doc_path"]
        code_path = row["code_path"]
        ref_id = row["ref_id"]
        stored_code_hash = row["code_hash_at_sync"]
        stored_doc_hash = row["doc_hash_at_sync"]
        doc_hash_at_last_edit: str = (
            row["doc_hash_at_last_edit"]
            if "doc_hash_at_last_edit" in row.keys()  # noqa: SIM118 - sqlite3.Row `in` checks values, not keys
            else ""
        )
        baseline_source: str = (
            row["baseline_source"]
            if "baseline_source" in row.keys()  # noqa: SIM118 - sqlite3.Row `in` checks values, not keys
            else ""
        )

        exempt_reason = _exempt_reason(doc_path, spaces)

        # Hash actual files on disk, under the documentation directory the
        # project declared — the same one the classification above asked about.
        current_doc_hash = _file_hash(project_root / spaces.docs_dir / doc_path)
        current_code_hash = _file_hash(project_root / code_path)

        # A file that is gone is reported before any exemption is applied. The
        # exemption says a WORKING document was never a description of the code,
        # which is a statement about freshness and none at all about existence;
        # excusing an absent file would make deleting it quieter than leaving it
        # (BDL-UX #174) through the one verdict that never blocks.
        gone = _missing_side(current_doc_hash, current_code_hash)
        if gone is None and exempt_reason is not None:
            results.append(
                {
                    "doc_path": doc_path,
                    "code_path": code_path,
                    "ref_id": ref_id,
                    "status": STATUS_EXEMPT,
                    "reason": REASON_WORKING_SPACE,
                    "baseline": BASELINE_NONE,
                    "details": exempt_reason,
                }
            )
            continue

        if gone is not None:
            conn.execute(
                "UPDATE sync_state SET status = ? WHERE doc_path = ? AND code_path = ?",
                (STATUS_MISSING, doc_path, code_path),
            )
            results.append(
                {
                    "doc_path": doc_path,
                    "code_path": code_path,
                    "ref_id": ref_id,
                    "status": STATUS_MISSING,
                    "reason": gone,
                    "baseline": BASELINE_NONE,
                }
            )
            continue

        status = "ok"
        reason = "ok"
        details = ""
        baseline = BASELINE_INDEX

        # --- Two-phase sync detection ---
        # When doc_hash_at_last_edit is set, use it to detect code drift
        # that survives reindex (which resets code_hash_at_sync).
        doc_edited = (
            bool(current_doc_hash)
            and bool(doc_hash_at_last_edit)
            and current_doc_hash != doc_hash_at_last_edit
        )

        if current_code_hash and current_code_hash != stored_code_hash:
            status = "stale"
            reason = "hash_changed"
        if current_doc_hash and current_doc_hash != stored_doc_hash:
            status = "stale"
            reason = "hash_changed"

        # Update doc_hash_at_last_edit when doc changes.
        if doc_edited and current_doc_hash:
            # Doc was edited: record new doc hash and reset code
            # baseline so future checks measure drift from here. An OBSERVED doc
            # edit is evidence, so this baseline stops being the tree's own echo
            # and becomes attested (BDL-UX #175).
            conn.execute(
                "UPDATE sync_state SET baseline_source = ? "
                "WHERE doc_path = ? AND code_path = ?",
                (BASELINE_SOURCE_ATTESTED, doc_path, code_path),
            )
            baseline_source = BASELINE_SOURCE_ATTESTED
            conn.execute(
                "UPDATE sync_state "
                "SET doc_hash_at_last_edit = ?, "
                "code_hash_at_sync = ? "
                "WHERE doc_path = ? AND code_path = ?",
                (
                    current_doc_hash,
                    current_code_hash or stored_code_hash,
                    doc_path,
                    code_path,
                ),
            )
        elif not doc_hash_at_last_edit and current_doc_hash:
            # Legacy/first run: initialize doc_hash_at_last_edit.
            conn.execute(
                "UPDATE sync_state "
                "SET doc_hash_at_last_edit = ? "
                "WHERE doc_path = ? AND code_path = ?",
                (current_doc_hash, doc_path, code_path),
            )

        # Symbol-level drift detection, at the granularity of the file that moved.
        # The node hash answers "did this document's subject move at all"; the
        # file hash answers "did it move HERE". Only the second one can make THIS
        # pair stale (BDL-UX #182).
        stored_symbols_hash = row["symbols_hash"] if "symbols_hash" in row.keys() else ""  # noqa: SIM118 - sqlite3.Row `in` checks values, not keys
        stored_file_symbols: str = (
            row["file_symbols_hash"] or ""
            if "file_symbols_hash" in row.keys()  # noqa: SIM118 - sqlite3.Row `in` checks values, not keys
            else ""
        )
        if stored_symbols_hash and status == STATUS_OK:
            current_symbols_hash = _compute_symbols_hash(conn, ref_id)
            if current_symbols_hash != stored_symbols_hash:
                if ref_id not in moved_by_ref:
                    moved_by_ref[ref_id] = _files_whose_symbols_moved(conn, ref_id)
                status, reason, details = _symbol_drift_verdict(
                    conn, ref_id, code_path, stored_file_symbols, moved_by_ref[ref_id]
                )

        # A baseline the index invented from the tree it was just built from
        # cannot make a pair fresh: ask git, or say it was not checked.
        if status == "ok" and baseline_source == BASELINE_SOURCE_INDEX_BUILD:
            if git_changed is _UNREAD:
                git_changed = changed_paths(project_root)
            status, reason, baseline = _corroborate_with_git(
                doc_path, code_path, git_changed, spaces.docs_dir
            )

        # Update status in DB.
        conn.execute(
            "UPDATE sync_state SET status = ? WHERE doc_path = ? AND code_path = ?",
            (status, doc_path, code_path),
        )

        results.append(
            {
                "doc_path": doc_path,
                "code_path": code_path,
                "ref_id": ref_id,
                "status": status,
                "reason": reason,
                "baseline": baseline,
                **({"details": details} if details else {}),
            }
        )

    conn.commit()

    # --- Phase 2: Source coverage checks ---
    source_gaps = check_source_coverage(conn, project_root)

    # Build a lookup of ref_ids already in results and their indices.
    ref_id_indices: dict[str, list[int]] = {}
    for i, r in enumerate(results):
        ref_id_indices.setdefault(r["ref_id"], []).append(i)

    for gap in source_gaps:
        gap_ref_id: str = gap["ref_id"]
        gap_doc_path: str = gap["doc_path"]
        untracked: list[str] = gap["untracked_files"]
        details = ", ".join(Path(f).name for f in untracked)

        if gap_ref_id in ref_id_indices:
            # Update existing results: if any are "ok", change to "stale"
            for idx in ref_id_indices[gap_ref_id]:
                # ``unverified`` is included: a pair nothing could be compared
                # against is still allowed to be found stale by a check that
                # does not need a baseline.
                if results[idx]["status"] in (STATUS_OK, STATUS_UNVERIFIED):
                    results[idx]["status"] = "stale"
                    results[idx]["reason"] = "untracked_files"
                    results[idx]["details"] = details
                    # Update DB status
                    conn.execute(
                        "UPDATE sync_state SET status = 'stale' "
                        "WHERE doc_path = ? AND code_path = ?",
                        (results[idx]["doc_path"], results[idx]["code_path"]),
                    )
        else:
            # Add new result for ref_id not yet in sync_state
            results.append(
                {
                    "doc_path": gap_doc_path,
                    "code_path": "",
                    "ref_id": gap_ref_id,
                    "status": "stale",
                    "reason": "untracked_files",
                    "details": details,
                    "baseline": BASELINE_INDEX,
                }
            )

    # --- Phase 3: Doc coverage checks ---
    doc_gaps = check_doc_coverage(conn, project_root)
    # Rebuild index since source coverage may have added entries.
    ref_id_indices = {}
    for i, r in enumerate(results):
        ref_id_indices.setdefault(r["ref_id"], []).append(i)

    for gap in doc_gaps:
        gap_ref_id = gap["ref_id"]
        gap_doc_path = gap["doc_path"]
        missing: list[str] = gap["missing_modules"]
        details = ", ".join(missing)

        if gap_ref_id in ref_id_indices:
            for idx in ref_id_indices[gap_ref_id]:
                # ``unverified`` is included: a pair nothing could be compared
                # against is still allowed to be found stale by a check that
                # does not need a baseline.
                if results[idx]["status"] in (STATUS_OK, STATUS_UNVERIFIED):
                    results[idx]["status"] = "stale"
                    results[idx]["reason"] = "missing_modules"
                    results[idx]["details"] = details
                    conn.execute(
                        "UPDATE sync_state SET status = 'stale' "
                        "WHERE doc_path = ? AND code_path = ?",
                        (results[idx]["doc_path"], results[idx]["code_path"]),
                    )
        else:
            results.append(
                {
                    "doc_path": gap_doc_path,
                    "code_path": "",
                    "ref_id": gap_ref_id,
                    "status": "stale",
                    "reason": "missing_modules",
                    "details": details,
                    "baseline": BASELINE_INDEX,
                }
            )

    # --- Phase 4: the DECLARED surface, which deleting a file cannot shrink ---
    # A doc the graph declares and the tree does not hold is a failure, not an
    # absence: without this phase the pair simply stopped existing at the next
    # reindex and every count still read fresh (BDL-UX #174).
    results.extend(
        {
            "doc_path": missing["doc_path"],
            "code_path": "",
            "ref_id": missing["ref_id"],
            "status": STATUS_MISSING,
            "reason": "declared_doc_missing",
            "details": missing["doc_path"],
            "baseline": BASELINE_NONE,
        }
        for missing in find_missing_declared_docs(conn, project_root)
    )

    # --- Phase 5: the document's SHAPE, which no content hash can see --------
    # Read-only and never written to ``sync_state``: ``incomplete`` is a warn
    # about structure, and recording it would make the status column mean two
    # different things (BDL-061 S4b).
    if section_requirements is not None:
        results.extend(
            check_section_shape(conn, project_root, section_requirements)
        )

    conn.commit()
    return results


def _validate_git_ref(project_root: Path, ref: str) -> bool:
    """Check a git ref resolves, mirroring ``graph.diff._validate_git_ref``.

    Uses ``git rev-parse --verify <ref>``. An all-zero SHA (force-push /
    first-push sentinel) never resolves, so it is rejected here too.
    """
    try:
        result = subprocess.run(  # noqa: S603
            ["git", "rev-parse", "--verify", ref],  # noqa: S607
            cwd=project_root,
            capture_output=True,
            check=False,
        )
    except OSError:
        # As wide as this call can raise: with no text mode, nothing is decoded,
        # so ``OSError`` (git missing, not executable, bad cwd) is the whole set
        # -- ``check=False`` rules out ``CalledProcessError`` and no ``timeout``
        # is passed. A ref that cannot be verified does not resolve; the CLI
        # turns that into "Invalid git ref" at exit 1 rather than a traceback.
        return False
    return result.returncode == 0


def _file_content_at_ref(project_root: Path, rel_path: str, ref: str) -> str | None:
    """Return *rel_path* content at *ref* via ``git show``, or None if absent.

    Non-destructive: reads from the object store, never touches the working
    tree or any beadloom DB.

    Decoded by :data:`_TEXT_CODEC` / :data:`_TEXT_ERRORS` -- the same rule the
    working-tree side uses -- so the two sides of the comparison in
    :func:`check_sync_since` cannot disagree about what the bytes say. Text mode
    is kept (rather than hashing raw bytes) because it also applies universal
    newline translation on both sides, so a CRLF checkout does not read as drift.

    ``None`` means *absent at that ref* and nothing else. An unreachable ``git``
    is deliberately not caught into ``None``: that would report drift in a file
    nobody touched, which is the defect this call site exists to have fixed. The
    CLI validates the ref through :func:`_validate_git_ref` first, so the
    reachable case is answered there.
    """
    result = subprocess.run(  # noqa: S603
        ["git", "show", f"{ref}:{rel_path}"],  # noqa: S607
        cwd=project_root,
        capture_output=True,
        encoding=_TEXT_CODEC,
        errors=_TEXT_ERRORS,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def _hash_text(text: str) -> str:
    """SHA-256 of *text*, and the single definition of "the digest of a file".

    :func:`_file_hash` routes through here so the working-tree side and the
    at-ref side cannot drift apart: same codec, same error handler, one place.
    """
    return hashlib.sha256(text.encode(_TEXT_CODEC, _TEXT_ERRORS)).hexdigest()


def check_sync_since(
    conn: sqlite3.Connection,
    *,
    project_root: Path,
    since: str,
) -> list[dict[str, Any]]:
    """Report doc-code pairs that drifted **relative to a git ref baseline**.

    Unlike :func:`check_sync` (which compares against the stored ``sync_state``
    baseline), this compares the *current* working tree against the code state
    captured at ``since``. A fresh CI checkout re-baselines ``sync_state`` to
    the just-pushed code, masking per-push drift; the ref baseline is immune to
    that because it reads the parent commit straight from git history.

    A tracked pair is **stale-since-ref** iff:

    * its code file changed between ``since`` and the working tree, **and**
    * its linked doc was *not* correspondingly updated since ``since``.

    If the doc *also* changed since ``since`` the dev already touched it, so the
    pair is reported ``ok`` (we never re-flag a doc the dev just updated).

    Pure and deterministic (no wall-clock); reads git + disk only, mutates
    neither ``sync_state`` nor the working tree. The result list mirrors
    :func:`check_sync`'s shape so the JSON/porcelain renderers are shared.
    """
    sync_rows = conn.execute(
        "SELECT doc_path, code_path, ref_id FROM sync_state"
    ).fetchall()
    docs_dir = resolve_docs_dir(project_root)

    results: list[dict[str, Any]] = []
    for row in sync_rows:
        doc_path = row["doc_path"]
        code_path = row["code_path"]
        ref_id = row["ref_id"]
        if not code_path:
            continue

        code_at_ref = _file_content_at_ref(project_root, code_path, since)
        current_code_hash = _file_hash(project_root / code_path)
        ref_code_hash = _hash_text(code_at_ref) if code_at_ref is not None else None
        code_drifted = ref_code_hash != current_code_hash

        doc_rel = str(Path(docs_dir) / doc_path)
        doc_at_ref = _file_content_at_ref(project_root, doc_rel, since)
        current_doc_hash = _file_hash(project_root / docs_dir / doc_path)
        ref_doc_hash = _hash_text(doc_at_ref) if doc_at_ref is not None else None
        doc_changed = ref_doc_hash != current_doc_hash

        stale = code_drifted and not doc_changed
        results.append(
            {
                "doc_path": doc_path,
                "code_path": code_path,
                "ref_id": ref_id,
                "status": "stale" if stale else "ok",
                "reason": "hash_changed" if stale else "ok",
            }
        )

    return results


def mark_synced(
    conn: sqlite3.Connection,
    doc_path: str,
    code_path: str,
    project_root: Path,
) -> None:
    """Recompute hashes for a doc-code pair and mark as synced.

    Also updates ``symbols_hash`` to the current value so that future
    :func:`check_sync` calls use this as the new baseline for symbol drift
    detection, and records the baseline as ATTESTED: somebody looked and said
    the doc is current, which is the one thing a rebuilt index cannot fabricate
    (BDL-UX #175).
    """
    doc_hash = _file_hash(project_root / resolve_docs_dir(project_root) / doc_path)
    code_hash = _file_hash(project_root / code_path)

    # Look up ref_id for this pair to recompute symbols_hash.
    row = conn.execute(
        "SELECT ref_id FROM sync_state WHERE doc_path = ? AND code_path = ?",
        (doc_path, code_path),
    ).fetchone()
    symbols_hash = _compute_symbols_hash(conn, row["ref_id"]) if row else ""
    # The pair's OWN file surface, so a later check can tell "this file moved"
    # from "a sibling moved" (BDL-UX #182). Written by every attestation; a row
    # that carries only the node hash is one this repair has not reached yet.
    file_symbols_hash = (
        _compute_symbols_hash(conn, row["ref_id"], file_path=code_path) if row else ""
    )

    now = datetime.now(tz=timezone.utc).isoformat()
    conn.execute(
        "UPDATE sync_state SET doc_hash_at_sync = ?, code_hash_at_sync = ?, "
        "symbols_hash = ?, file_symbols_hash = ?, synced_at = ?, status = 'ok', "
        "doc_hash_at_last_edit = ?, baseline_source = ? "
        "WHERE doc_path = ? AND code_path = ?",
        (
            doc_hash,
            code_hash,
            symbols_hash,
            file_symbols_hash,
            now,
            doc_hash,
            BASELINE_SOURCE_ATTESTED,
            doc_path,
            code_path,
        ),
    )
    conn.commit()


@dataclass(frozen=True)
class Attestation:
    """What one re-baseline CLAIMED, and which pairs it deliberately did not.

    Two populations because the run has grounds for one and not the other, and
    a summary that reported only the first would hide the size of the second —
    which is the whole of BDL-UX #163.
    """

    #: ``(doc_path, code_path)`` pairs recorded as read: ``baseline_source``
    #: becomes ``attested`` and ``synced_at`` moves.
    attested: tuple[tuple[str, str], ...]
    #: Pairs whose node-level ``symbols_hash`` was carried forward and about
    #: which nothing was claimed.
    carried: tuple[tuple[str, str], ...]


def pairs_of_ref(conn: sqlite3.Connection, ref_id: str) -> list[tuple[str, str]]:
    """Every ``(doc_path, code_path)`` pair the ref owns, in stable order."""
    return [
        (str(row["doc_path"]), str(row["code_path"]))
        for row in conn.execute(
            "SELECT doc_path, code_path FROM sync_state WHERE ref_id = ? "
            "ORDER BY doc_path, code_path",
            (ref_id,),
        )
    ]


def attest_ref(
    conn: sqlite3.Connection,
    ref_id: str,
    project_root: Path,
    *,
    scope: Collection[tuple[str, str]] | None = None,
) -> Attestation:
    """Re-baseline *ref_id*, claiming only the pairs in *scope*.

    **A fact and a claim were one UPDATE, and this splits them.** The node-level
    ``symbols_hash`` is a fact about the index — what the node's symbol surface
    was when this ran — and it is carried forward for EVERY pair the ref owns,
    so the ``unverified``/``sibling_symbols_changed`` verdict bead ``.78``
    created clears once the file that caused it has been re-baselined. Leaving
    it behind would leave a verdict that names no mover (its cause is now
    re-baselined) standing on every later run, and a signal that cannot be
    cleared by reading is a signal people clear with ``--all-pairs``.

    The attestation is a claim about a DOCUMENT somebody read: ``doc_hash_at_sync``,
    ``code_hash_at_sync``, ``file_symbols_hash``, ``synced_at`` and
    ``baseline_source = attested``. It is written only for the pairs in *scope*.
    An un-attested pair keeps whatever baseline it had, which is not cosmetic:
    :func:`check_sync` corroborates an ``index_build`` baseline against git
    instead of trusting it, and a bulk re-attestation used to switch that harder
    check off for documents nobody had opened.

    *scope* ``None`` means every pair — the deliberate whole-ref attestation,
    reached from the CLI by ``sync-update <ref> --yes --all-pairs``.
    """
    pairs = pairs_of_ref(conn, ref_id)
    if not pairs:
        return Attestation(attested=(), carried=())

    claimed = set(pairs) if scope is None else {p for p in pairs if p in set(scope)}
    symbols_hash = _compute_symbols_hash(conn, ref_id)
    now = datetime.now(tz=timezone.utc).isoformat()
    docs_dir = resolve_docs_dir(project_root)

    for doc_path, code_path in pairs:
        if (doc_path, code_path) not in claimed:
            conn.execute(
                "UPDATE sync_state SET symbols_hash = ? "
                "WHERE doc_path = ? AND code_path = ?",
                (symbols_hash, doc_path, code_path),
            )
            continue
        doc_hash = _file_hash(project_root / docs_dir / doc_path)
        code_hash = _file_hash(project_root / code_path)
        # One node hash for the ref, but each pair gets ITS OWN file hash — the
        # whole point of the distinction is lost if every row stores the same
        # number under a different name.
        file_symbols_hash = _compute_symbols_hash(conn, ref_id, file_path=code_path)
        conn.execute(
            "UPDATE sync_state SET doc_hash_at_sync = ?, code_hash_at_sync = ?, "
            "symbols_hash = ?, file_symbols_hash = ?, synced_at = ?, status = 'ok', "
            "doc_hash_at_last_edit = ?, baseline_source = ? "
            "WHERE doc_path = ? AND code_path = ?",
            (
                doc_hash,
                code_hash,
                symbols_hash,
                file_symbols_hash,
                now,
                doc_hash,
                BASELINE_SOURCE_ATTESTED,
                doc_path,
                code_path,
            ),
        )

    conn.commit()
    return Attestation(
        attested=tuple(p for p in pairs if p in claimed),
        carried=tuple(p for p in pairs if p not in claimed),
    )


def mark_synced_by_ref(
    conn: sqlite3.Connection,
    ref_id: str,
    project_root: Path,
) -> int:
    """Mark all doc-code pairs for *ref_id* as synced; return the rows updated.

    The whole-ref attestation, kept as its own name because that is what every
    caller outside the ``sync-update`` command means. Scoped attestation is
    :func:`attest_ref`.
    """
    return len(attest_ref(conn, ref_id, project_root, scope=None).attested)


# ---------------------------------------------------------------------------
# BDL-057 Layer 2 — reference doc surface-drift (advisory / warning)
#
# Reference / overview docs opt in with an in-doc annotation
# ``<!-- beadloom:watches=cli,graph,flow.yml -->``. Their coarse aggregate hash
# is baselined on reindex (:func:`build_reference_state`), re-checked on
# sync-check (:func:`check_reference_drift`, severity *warning*), and re-baselined
# on sync-update (:func:`mark_reference_synced`). This lives in the separate
# ``reference_state`` table and never touches the symbol-pair ``sync_state``
# logic or its reason-masking / fixpoint invariant.
# ---------------------------------------------------------------------------


def _resolve_reference_docs_dir(project_root: Path) -> Path:
    """The docs directory as an absolute path, from the one reader of the key.

    It mirrored the application-layer resolver here once, and a mirror is two
    readers of one fact: `beadloom-mr2l.75` collapsed them into
    :func:`beadloom.infrastructure.doc_roots.resolve_docs_dir`.
    """
    return project_root / resolve_docs_dir(project_root)


def _discover_reference_docs(project_root: Path) -> list[tuple[str, list[str]]]:
    """Find markdown docs declaring a ``watches:`` annotation.

    Scans the top-level ``*.md`` files (e.g. ``README.md``, ``README.ru.md``)
    and every ``*.md`` under the docs directory. Returns a sorted list of
    ``(project-root-relative doc_path, watched surfaces)`` for docs whose
    annotation names at least one known surface.
    """
    from beadloom.doc_sync.surface import parse_watches

    candidates: list[Path] = sorted(project_root.glob("*.md"))
    docs_dir = _resolve_reference_docs_dir(project_root)
    if docs_dir.is_dir():
        candidates += sorted(docs_dir.rglob("*.md"))

    found: list[tuple[str, list[str]]] = []
    for path in candidates:
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        watches = parse_watches(text)
        if watches:
            rel = str(path.relative_to(project_root))
            found.append((rel, watches))
    return found


def build_reference_state(conn: sqlite3.Connection, project_root: Path) -> int:
    """Baseline the aggregate hash of every ``watches``-annotated reference doc.

    Discovers reference docs and records a ``reference_state`` row for each.

    The stored ``aggregate_hash`` baseline is **preserved across reindex** for
    docs already tracked with the *same* ``watches`` set — otherwise a routine
    reindex after a surface change would silently re-baseline and never warn (the
    same fixpoint concern as the symbol-pair ``sync_state``). A fresh baseline at
    the current hash is computed only for newly-discovered docs, or when the
    declared ``watches`` set itself changed (the old baseline no longer applies).
    Docs whose annotation was removed are dropped. Idempotent. Returns the number
    of reference docs recorded.
    """
    from beadloom.doc_sync.surface import aggregate_hash

    discovered = _discover_reference_docs(project_root)
    keep = {doc_path for doc_path, _ in discovered}

    prior: dict[str, tuple[str, str]] = {
        row["doc_path"]: (row["watches"], row["aggregate_hash"])
        for row in conn.execute(
            "SELECT doc_path, watches, aggregate_hash FROM reference_state"
        ).fetchall()
    }

    # Forget docs that no longer declare a watches annotation.
    for doc_path in prior:
        if doc_path not in keep:
            conn.execute(
                "DELETE FROM reference_state WHERE doc_path = ?", (doc_path,)
            )

    for doc_path, watches in discovered:
        watches_csv = ",".join(watches)
        prior_entry = prior.get(doc_path)
        if prior_entry is not None and prior_entry[0] == watches_csv:
            # Already tracked with the same surfaces — keep the existing baseline
            # so a later sync-check still sees drift accrued since it was set.
            continue
        agg = aggregate_hash(watches, conn, project_root)
        conn.execute(
            "INSERT INTO reference_state (doc_path, watches, aggregate_hash, status) "
            "VALUES (?, ?, ?, 'ok') "
            "ON CONFLICT(doc_path) DO UPDATE SET "
            "watches = excluded.watches, aggregate_hash = excluded.aggregate_hash, "
            "status = 'ok'",
            (doc_path, watches_csv, agg),
        )
    conn.commit()
    return len(discovered)


def check_reference_drift(
    conn: sqlite3.Connection,
    project_root: Path,
) -> list[dict[str, Any]]:
    """Recompute each reference doc's aggregate hash and report drift (warning).

    For every ``reference_state`` row, compares the stored baseline against the
    current aggregate hash of its watched surfaces. A mismatch yields
    ``status='surface_drift'`` with ``reason='surface_drift'`` and
    ``severity='warning'`` (never a hard failure); a match yields ``'ok'``. The
    new status is persisted. Returns one result dict per reference doc.
    """
    from beadloom.doc_sync.surface import aggregate_hash

    rows = conn.execute(
        "SELECT doc_path, watches, aggregate_hash FROM reference_state ORDER BY doc_path"
    ).fetchall()
    if not rows:
        return []

    results: list[dict[str, Any]] = []
    for row in rows:
        doc_path = row["doc_path"]
        watches = [s for s in row["watches"].split(",") if s]
        baseline = row["aggregate_hash"]

        current = aggregate_hash(watches, conn, project_root)
        drifted = current != baseline
        status = "surface_drift" if drifted else "ok"

        conn.execute(
            "UPDATE reference_state SET status = ? WHERE doc_path = ?",
            (status, doc_path),
        )
        results.append(
            {
                "doc_path": doc_path,
                "watches": row["watches"],
                "status": status,
                "reason": "surface_drift" if drifted else "ok",
                "severity": "warning",
            }
        )

    conn.commit()
    return results


def describe_reference_doc(
    conn: sqlite3.Connection,
    doc_path: str | None,
    project_root: Path,
) -> dict[str, Any] | None:
    """Read-only report on one reference doc: its watches and its drift status.

    The counterpart :func:`mark_reference_synced` needs so that ``sync-update
    <doc> --check`` can answer without writing. ``--check`` used to reach the
    re-baselining branch before its own guard, so the flag whose contract is
    "tell me, do not change anything" cleared the drift it was asked to describe
    and the next ``sync-check`` read clean for a reason nobody recorded
    (BDL-UX #189, the same defect as #147).

    Returns ``None`` when *doc_path* is not a tracked reference doc — the caller
    distinguishes "not this kind of thing" from "this thing, and here it is".
    Nothing here executes an ``UPDATE``, and the connection is not committed.
    """
    from beadloom.doc_sync.surface import aggregate_hash

    row = conn.execute(
        "SELECT doc_path, watches, aggregate_hash FROM reference_state "
        "WHERE doc_path = ?",
        (doc_path,),
    ).fetchone()
    if row is None:
        return None
    watches = [s for s in row["watches"].split(",") if s]
    current = aggregate_hash(watches, conn, project_root)
    drifted = current != row["aggregate_hash"]
    return {
        "doc_path": row["doc_path"],
        "watches": watches,
        "status": "surface_drift" if drifted else "ok",
        "baseline_hash": row["aggregate_hash"],
        "current_hash": current,
    }


def mark_reference_synced(
    conn: sqlite3.Connection,
    doc_path: str | None,
    project_root: Path,
    *,
    all_docs: bool = False,
) -> int:
    """Re-baseline a reference doc's aggregate hash, clearing surface drift.

    Recomputes the current aggregate hash for *doc_path* (or every reference doc
    when *all_docs* is set) and stores it with ``status='ok'``. Returns the
    number of rows re-baselined (0 when the doc is not a tracked reference doc).
    """
    from beadloom.doc_sync.surface import aggregate_hash

    if all_docs:
        rows = conn.execute("SELECT doc_path, watches FROM reference_state").fetchall()
    else:
        rows = conn.execute(
            "SELECT doc_path, watches FROM reference_state WHERE doc_path = ?",
            (doc_path,),
        ).fetchall()

    count = 0
    for row in rows:
        watches = [s for s in row["watches"].split(",") if s]
        agg = aggregate_hash(watches, conn, project_root)
        conn.execute(
            "UPDATE reference_state SET aggregate_hash = ?, status = 'ok' "
            "WHERE doc_path = ?",
            (agg, row["doc_path"]),
        )
        count += 1

    conn.commit()
    return count


# Excluded filenames — boilerplate, not doc-worthy
_COVERAGE_EXCLUDE = frozenset({"__init__.py", "conftest.py", "__main__.py"})

# File-level beadloom annotation in a source comment, e.g.
#   # beadloom:domain=core   or   # beadloom:feature=docs-audit
# Captures the ref_id value regardless of the key (domain/feature/...).
_FILE_ANNOTATION_RE = re.compile(
    r"beadloom:(?:domain|feature|service|entity)=([\w.\-]+)"
)

# Doc-side binding marker, e.g. <!-- beadloom:track=src/app/constants.py -->
_TRACK_MARKER_RE = re.compile(r"beadloom:track=([^\s>]+)")


def _file_annotation_ref_ids(path: Path) -> set[str]:
    """Return ref_ids declared by file-level beadloom annotations in *path*.

    Scans the head of the file for ``# beadloom:domain=X`` /
    ``# beadloom:feature=X`` style comments.  These declare node ownership
    even when the file contains no extractable top-level symbol (e.g. a pure
    constants module), so the file is still considered *tracked* (#89).
    """
    if not path.is_file():
        return set()
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return set()
    return set(_FILE_ANNOTATION_RE.findall(content))


def _tracked_paths_from_doc(doc_file: Path, project_root: Path) -> set[str]:
    """Return code paths bound to a doc via ``beadloom:track`` markers (#90).

    Parses ``<!-- beadloom:track=<path> -->`` comments in *doc_file* and
    normalizes each path relative to *project_root* so it can be compared
    against the on-disk file set.
    """
    if not doc_file.is_file():
        return set()
    try:
        content = doc_file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return set()

    tracked: set[str] = set()
    for raw in _TRACK_MARKER_RE.findall(content):
        candidate = Path(raw)
        if candidate.is_absolute():
            try:
                tracked.add(str(candidate.relative_to(project_root)))
            except ValueError:
                continue
        else:
            tracked.add(str(candidate))
    return tracked


def _doc_paths_by_ref_id(conn: sqlite3.Connection) -> dict[str, str]:
    """Prefetch one ``doc_path`` per ref_id, sync_state taking precedence.

    Replaces the per-node ``sync_state``-then-``docs`` lookup with two
    set-based scans. Mirrors the old ``LIMIT 1`` behavior: a ref_id present in
    ``sync_state`` resolves to its sync_state ``doc_path``; otherwise it falls
    back to the ``docs`` table. Within each source, the *first* row by rowid
    wins — the same row SQLite returned for the old unordered ``LIMIT 1``.
    """
    doc_paths: dict[str, str] = {}
    # docs first, so sync_state can overwrite (sync_state has precedence).
    for row in conn.execute(
        "SELECT ref_id, path AS doc_path FROM docs "
        "WHERE ref_id IS NOT NULL ORDER BY id DESC"
    ):
        doc_paths[row["ref_id"]] = row["doc_path"]
    for row in conn.execute(
        "SELECT ref_id, doc_path FROM sync_state ORDER BY id DESC"
    ):
        doc_paths[row["ref_id"]] = row["doc_path"]
    return doc_paths


def _children_by_parent(conn: sqlite3.Connection) -> dict[str, list[str]]:
    """Prefetch ``part_of`` child ref_ids grouped by their parent ref_id."""
    children: dict[str, list[str]] = {}
    for row in conn.execute(
        "SELECT src_ref_id, dst_ref_id FROM edges WHERE kind = 'part_of'"
    ):
        children.setdefault(row["dst_ref_id"], []).append(row["src_ref_id"])
    return children


def _sync_paths_by_ref_id(conn: sqlite3.Connection) -> dict[str, set[str]]:
    """Prefetch tracked ``code_path`` sets from ``sync_state`` per ref_id."""
    sync_paths: dict[str, set[str]] = {}
    for row in conn.execute("SELECT ref_id, code_path FROM sync_state"):
        sync_paths.setdefault(row["ref_id"], set()).add(row["code_path"])
    return sync_paths


def _symbol_paths_by_ref_id(conn: sqlite3.Connection) -> dict[str, set[str]]:
    """Prefetch ``code_symbols`` file_paths grouped by their annotated ref_id.

    Uses ``json_each`` to fan out the ``annotations`` JSON object and match on
    its keys/values — an indexable, parse-driven lookup that is byte-identical
    to the old per-ref_id ``annotations LIKE '%"ref_id"%'`` substring scan
    (the quoted form only ever matched a JSON key or value), but runs as a
    single set-based query instead of one ``LIKE`` per ref_id.
    """
    symbol_paths: dict[str, set[str]] = {}
    for row in conn.execute(
        "SELECT cs.file_path AS file_path, je.value AS ref_value, je.key AS ref_key "
        "FROM code_symbols cs, json_each(cs.annotations) je"
    ):
        for rid in (row["ref_value"], row["ref_key"]):
            if rid is not None:
                symbol_paths.setdefault(rid, set()).add(row["file_path"])
    return symbol_paths


def check_source_coverage(
    conn: sqlite3.Connection,
    project_root: Path,
) -> list[dict[str, Any]]:
    """Check if all source files in a node's directory are tracked in sync_state.

    For each node with a ``source`` field ending in ``/`` (a directory),
    compares actual Python files on disk against code_paths tracked in
    sync_state for that ref_id.

    Returns list of dicts with ``ref_id``, ``doc_path``, ``untracked_files``
    for nodes that have gaps.
    """
    docs_dir = resolve_docs_dir(project_root)
    # 1. Query nodes with directory-based source (ending in /)
    node_rows = conn.execute(
        "SELECT ref_id, source FROM nodes WHERE source IS NOT NULL AND source LIKE '%/'"
    ).fetchall()

    if not node_rows:
        return []

    # Set-based prefetch of all per-node lookups (#123): replaces the former
    # ~5N per-node queries (doc lookup, sync_state, edges, child sync_state,
    # per-ref_id symbol LIKE) with a small fixed number of scans.
    doc_paths = _doc_paths_by_ref_id(conn)
    children_by_parent = _children_by_parent(conn)
    sync_paths_by_ref = _sync_paths_by_ref_id(conn)
    symbol_paths_by_ref = _symbol_paths_by_ref_id(conn)

    results: list[dict[str, Any]] = []

    for node in node_rows:
        ref_id: str = node["ref_id"]
        source: str = node["source"]

        # 2. Resolve directory on disk
        source_dir = project_root / source
        if not source_dir.is_dir():
            continue

        # 3. Find doc_path for this ref_id (sync_state precedence, then docs)
        doc_path = doc_paths.get(ref_id)
        if doc_path is None:
            # No linked doc — skip, nothing to mark stale
            continue

        # 4. List *.py files on disk (non-recursive), excluding boilerplate
        disk_files: set[str] = set()
        for py_file in source_dir.glob("*.py"):
            if py_file.name in _COVERAGE_EXCLUDE:
                continue
            relative = str(py_file.relative_to(project_root))
            disk_files.add(relative)

        if not disk_files:
            continue

        # 5. Collect tracked code_paths from sync_state for this ref_id and
        #    its part_of children.
        child_ref_ids = children_by_parent.get(ref_id, [])
        all_ref_ids = [ref_id, *child_ref_ids]

        tracked: set[str] = set()
        for rid in all_ref_ids:
            tracked |= sync_paths_by_ref.get(rid, set())
            # 6. Also include files from code_symbols annotated with this
            #    ref_id OR any child ref_id.
            tracked |= symbol_paths_by_ref.get(rid, set())

        # 6b. (#90) Honor explicit `beadloom:track=path` markers in the doc.
        owned_ref_ids = set(all_ref_ids)
        tracked |= _tracked_paths_from_doc(
            project_root / docs_dir / doc_path, project_root
        )

        # 6c. (#89) Honor file-level `# beadloom:domain/feature=` annotations.
        #     Symbol-less files (e.g. pure constants modules) produce no
        #     code_symbols rows, so the annotation is the only ownership
        #     signal — count the file as tracked when it declares this node.
        for disk_file in disk_files:
            if disk_file in tracked:
                continue
            if _file_annotation_ref_ids(project_root / disk_file) & owned_ref_ids:
                tracked.add(disk_file)

        # 7. Find untracked files
        untracked = sorted(disk_files - tracked)

        # 8. Report if gaps exist
        if untracked:
            results.append(
                {
                    "ref_id": ref_id,
                    "doc_path": doc_path,
                    "untracked_files": untracked,
                }
            )

    return results


def check_doc_coverage(
    conn: sqlite3.Connection,
    project_root: Path,
) -> list[dict[str, Any]]:
    """Check if documentation mentions module names from the node's source directory.

    For each node with a directory-based ``source``, lists Python file stems
    (without .py) and checks if the linked doc content contains each name.

    Returns list of dicts with ``ref_id``, ``doc_path``, ``missing_modules``
    for nodes where the doc is missing module mentions.
    """
    docs_dir = resolve_docs_dir(project_root)
    # 1. Query nodes with directory-based source (ending in /)
    node_rows = conn.execute(
        "SELECT ref_id, source FROM nodes WHERE source IS NOT NULL AND source LIKE '%/'"
    ).fetchall()

    if not node_rows:
        return []

    results: list[dict[str, Any]] = []

    for node in node_rows:
        ref_id: str = node["ref_id"]
        source: str = node["source"]

        # 2. Resolve source dir on disk
        source_dir = project_root / source
        if not source_dir.is_dir():
            continue

        # 3. Get the doc path from docs table for this ref_id
        doc_row = conn.execute(
            "SELECT path FROM docs WHERE ref_id = ? LIMIT 1",
            (ref_id,),
        ).fetchone()

        if doc_row is None:
            continue

        doc_path: str = doc_row["path"]

        # 4. Read the doc file content from disk
        doc_file = project_root / docs_dir / doc_path
        if not doc_file.is_file():
            continue

        doc_content = doc_file.read_text(encoding="utf-8")

        # 5. List *.py files on disk (non-recursive), excluding boilerplate
        missing_modules: list[str] = []
        for py_file in sorted(source_dir.glob("*.py")):
            if py_file.name in _COVERAGE_EXCLUDE:
                continue

            # 6. Get stem and check if it appears as a word in doc content
            stem = py_file.stem
            pattern = re.compile(rf"\b{re.escape(stem)}\b", re.IGNORECASE)
            if not pattern.search(doc_content):
                missing_modules.append(stem)

        # 7-8. If any missing, add to results
        if missing_modules:
            results.append(
                {
                    "ref_id": ref_id,
                    "doc_path": doc_path,
                    "missing_modules": missing_modules,
                }
            )

    return results
