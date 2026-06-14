# beadloom:domain=ai_agents
# beadloom:feature=ai-techwriter
"""Symbol-level scope narrowing (BDL-052 S4 / RFC Thread C, Decision 4).

The tech-writer's stale set is, by default, *file-level*: a single edit to a
god-file (e.g. ``cli.py``) drifts every doc that file is linked to. This module
narrows that to *symbol-level*: for each stale doc-code pair it computes the SET
of symbols that actually changed in the touched file (vs the ``--since``
baseline) ∩ the symbols the doc references; an **empty** intersection means the
doc did not depend on the change, so it is dropped from the agent run AND
``sync-update``-baselined deterministically (so ``sync-check`` still reaches 0
without an agent rewrite).

**Conservative by construction** — never under-refresh. Whenever per-symbol
attribution is unavailable or ambiguous for a pair (no ``--since`` baseline, a
non-symbol-attributable drift reason such as ``untracked_files`` /
``missing_modules``, a non-Python file, a change that maps to no symbol body, or
a missing file revision) the pair is KEPT in scope.

DDD: ``ai_agents`` stays a leaf consumer — this module reaches code only through
the :mod:`commands` subprocess seam (git / ``beadloom``) plus pure stdlib, never
importing another domain.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from beadloom.ai_agents.ai_techwriter.commands import (
    beadloom_sync_update,
    git_changed_line_numbers,
    git_file_at_ref,
    read_working_file,
)

if TYPE_CHECKING:
    from pathlib import Path

    from beadloom.ai_agents.ai_techwriter.models import DriftItem

#: Drift reasons whose attribution is a *code-symbol* change and therefore
#: eligible for symbol-level narrowing. Coverage reasons (untracked files,
#: missing module mentions) are structural, not symbol-level — keep those pairs.
_ATTRIBUTABLE_REASONS = frozenset({"hash_changed", "symbols_changed"})

#: Only Python is attributed here; other languages fall to the conservative
#: keep (the tree-sitter parser lives in another domain we must not import).
_PY_SUFFIX = ".py"

#: A top-level ``def`` / ``class`` (column-0) and its name.
_TOPLEVEL_DEF_RE = re.compile(r"^(?:async\s+)?(?:def|class)\s+([A-Za-z_]\w*)")


def python_symbol_ranges(content: str) -> dict[str, tuple[int, int]]:
    """Map each top-level Python symbol name to its 1-based ``(start, end)`` lines.

    A symbol's block runs from its ``def``/``class`` line up to (but not into)
    the next top-level statement — so a class range includes its nested methods.
    Pure and deterministic; indentation-based, no tree-sitter (kept in the
    ``ai_agents`` leaf). Decorators above a definition are not part of the body
    range here — a decorator-only edit is treated as ambiguous and kept.
    """
    lines = content.splitlines()
    starts: list[tuple[int, str]] = []
    for idx, line in enumerate(lines):
        match = _TOPLEVEL_DEF_RE.match(line)
        if match is not None:
            starts.append((idx + 1, match.group(1)))

    ranges: dict[str, tuple[int, int]] = {}
    total = len(lines)
    for pos, (start, name) in enumerate(starts):
        next_start = starts[pos + 1][0] if pos + 1 < len(starts) else total + 1
        end = _block_end(lines, start, next_start)
        ranges[name] = (start, end)
    return ranges


def _block_end(lines: list[str], start: int, next_start: int) -> int:
    """Last non-blank line of the block starting at 1-based *start*.

    Trailing blank lines between this symbol and the next top-level statement
    are excluded so an edit in the gap is not misattributed to this symbol.
    """
    end = next_start - 1
    while end > start and not lines[end - 1].strip():
        end -= 1
    return end


def changed_symbols(*, new_content: str | None, changed_lines: set[int]) -> set[str]:
    """Names of top-level symbols whose body overlaps a changed line.

    *new_content* is the working-tree content (the symbol ranges are keyed on
    its line numbers, matching ``git diff``'s new side). Returns ``set()`` when
    there is nothing to attribute (no content / no changed lines). A changed
    line that falls in no symbol body contributes nothing here — the caller
    detects that "change outside any symbol" case and keeps the pair.
    """
    if not new_content or not changed_lines:
        return set()
    ranges = python_symbol_ranges(new_content)
    hit: set[str] = set()
    for name, (start, end) in ranges.items():
        if any(start <= ln <= end for ln in changed_lines):
            hit.add(name)
    return hit


#: A symbol is *referenced* by a doc when its name appears as a whole word.
def doc_referenced_symbols(doc_text: str, universe: set[str]) -> set[str]:
    """Subset of *universe* whose names appear as whole words in *doc_text*."""
    referenced: set[str] = set()
    for name in universe:
        if re.search(rf"(?<!\w){re.escape(name)}(?!\w)", doc_text):
            referenced.add(name)
    return referenced


def narrow_by_changed_symbols(
    stale_items: list[DriftItem],
    project_root: Path,
    *,
    since: str | None,
) -> list[DriftItem]:
    """Narrow *stale_items* to those whose doc references a CHANGED symbol.

    For each stale pair, the changed-symbol set (∩ of "symbols changed in the
    touched file since *since*" and "symbols the doc references") decides:

    * non-empty ∩  -> the doc depends on the change      -> KEEP in scope;
    * empty ∩      -> the doc is unaffected               -> DROP + ``sync-update``
      the ref so ``sync-check`` still reaches 0 deterministically;
    * ambiguous    -> attribution impossible/unclear      -> KEEP (conservative).

    Returns the kept items in their original order. When *since* is ``None`` the
    whole list is returned unchanged (no baseline to diff against).
    """
    if since is None:
        return list(stale_items)

    kept: list[DriftItem] = []
    for item in stale_items:
        if _doc_depends_on_change(item, project_root, since=since):
            kept.append(item)
        else:
            beadloom_sync_update(project_root, item.ref_id)
    return kept


def _doc_depends_on_change(item: DriftItem, project_root: Path, *, since: str) -> bool:
    """True if *item*'s doc references a symbol that changed in its code files.

    Returns True (KEEP) whenever attribution is unavailable or ambiguous for any
    of the item's pairs — the conservative floor that prevents under-refresh.
    """
    if not _is_attributable(item):
        return True

    doc_text = read_working_file(project_root, item.doc_path) or ""
    for code_path in item.code_files:
        verdict = _pair_keeps(code_path, doc_text, project_root, since=since)
        if verdict:
            return True
    return False


def _is_attributable(item: DriftItem) -> bool:
    """Eligible for narrowing only when every drift reason is symbol-level."""
    if not item.reasons or not item.code_files:
        return True  # ambiguous -> keep
    return all(reason in _ATTRIBUTABLE_REASONS for reason in item.reasons)


def _pair_keeps(
    code_path: str, doc_text: str, project_root: Path, *, since: str
) -> bool:
    """Per (doc, code-file) verdict: True => keep (depends / ambiguous).

    Ambiguity (kept) covers: a non-Python file, a vanished revision, no
    detectable changed lines, or changed lines that map to no symbol body
    (e.g. a module-level / import edit).
    """
    if not code_path.endswith(_PY_SUFFIX):
        return True  # only Python is attributed here

    new_content = read_working_file(project_root, code_path)
    old_content = git_file_at_ref(project_root, code_path, since)
    if new_content is None or old_content is None:
        return True  # added/removed file revision -> ambiguous

    changed_lines = git_changed_line_numbers(project_root, code_path, since)
    if not changed_lines:
        return True  # no detectable hunks -> ambiguous

    changed = changed_symbols(new_content=new_content, changed_lines=changed_lines)
    if not changed:
        return True  # change outside any symbol body -> ambiguous

    referenced = doc_referenced_symbols(doc_text, changed)
    return bool(referenced)
