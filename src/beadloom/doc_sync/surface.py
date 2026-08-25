"""Layer 2 reference surface-drift signatures (BDL-057).

A reference / overview doc opts in with an in-doc annotation declaring a coarse
``watches:`` surface::

    <!-- beadloom:watches=cli,graph,flow.yml -->

For each declared surface this module computes a *coarse, deterministic*
signature — an identity set, not file content — so the aggregate hash only moves
on a structural change (a command/flag added, a node/edge added, the flow config
re-shaped), never on cosmetic edits. The aggregate hash is the SHA-256 of the
declared surfaces' signatures concatenated in declared order; ``sync-check``
compares it against the baseline stored in ``reference_state`` and, on drift,
emits a *warning* (never a hard failure) so a human re-reads the overview.

This is additive to the symbol-pair ``sync_state`` logic in :mod:`engine` — it
lives in its own table and never touches the reason-masking / fixpoint invariant.
"""

# beadloom:domain=doc-sync
# beadloom:feature=sync-check

from __future__ import annotations

import hashlib
import re
from typing import TYPE_CHECKING

import yaml

from beadloom.infrastructure.surface_registry import get_cli_group

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

# The coarse surfaces a reference doc may watch, in a fixed canonical tuple.
VALID_SURFACES: tuple[str, ...] = ("cli", "graph", "flow.yml")

# In-doc annotation: ``<!-- beadloom:watches=cli,graph,flow.yml -->``. The value
# is a comma list; surrounding whitespace per item is tolerated.
#
# The annotation OPENS the line, with at most three spaces of indentation —
# markdown's own boundary, since a fourth space starts a code block. Anchoring is
# what separates a document that MAKES this declaration from one that SHOWS it:
# the two are byte-identical as syntax, and only position tells them apart
# (BDL-061.86, and BDL-061.83 for the same shape in the wave declaration).
_WATCHES_RE = re.compile(r"^ {0,3}<!--\s*beadloom:watches\s*=\s*([^\->]+)")

#: A markdown fence, either delimiter. What is inside one is a SAMPLE: a document
#: that shows a reader how to declare a watch is not thereby declaring one.
_FENCE_RE = re.compile(r"^\s*(```|~~~)")


def parse_watches(text: str) -> list[str] | None:
    """Parse the ``<!-- beadloom:watches=... -->`` declaration from *text*.

    Returns the ordered, de-duplicated list of *known* watched surfaces in the
    order declared, or ``None`` when no declaration is present or it names no
    known surface. Unknown surface tokens are silently dropped
    (forward-compatible). The FIRST declaration decides; declared order is part of
    the contract, because the aggregate hash is order-sensitive.

    **A declaration opens a line, outside a fenced block.** Read over the whole
    text, this function enrolled four of this repository's documents in a check
    none of them had asked for — a changelog entry describing the feature, two
    SPECs mentioning it in a sentence, and the code-indexer SPEC's own fenced
    example, whose caption said it was not read. A false positive here is
    permanent: the operator's only remedies are to attest a declaration the
    document never made, or to leave a standing advisory warning that teaches
    everyone to ignore the ``surface_drift`` channel.

    What position cannot decide is an unfenced, unindented example written in
    prose. That shape is read as a declaration, and this is stated rather than
    hidden: a document showing markdown syntax fences it anyway, and inventing an
    escape marker for the remaining case would add a second syntax to get wrong.
    """
    fence: str | None = None
    for line in text.splitlines():
        fence_match = _FENCE_RE.match(line)
        if fence_match is not None:
            marker = fence_match.group(1)
            if fence is None:
                fence = marker
            elif marker == fence:
                fence = None
            continue
        if fence is not None:
            continue
        match = _WATCHES_RE.match(line)
        if match is None:
            continue
        return _known_surfaces(match.group(1))
    return None


def _known_surfaces(declared: str) -> list[str] | None:
    """The known surfaces named in a declaration's comma list, in declared order."""
    seen: set[str] = set()
    surfaces: list[str] = []
    for raw in declared.split(","):
        token = raw.strip()
        if token in VALID_SURFACES and token not in seen:
            seen.add(token)
            surfaces.append(token)
    return surfaces or None


_UNKNOWN_SURFACE = "<cli-surface-unavailable>"


def cli_signature() -> str:
    """Coarse signature of the Click command + option tree.

    The identity set is every command's dotted path plus its option flag names,
    sorted — so adding/removing a command or a flag moves the signature, but
    reordering or re-wording help text does not. The actual SHA-256 digest of
    that canonical text is returned.
    """
    group = get_cli_group()
    if group is None:
        # Unknown surface: hashing "nothing" would silently re-baseline every
        # `watches=cli` doc against an empty CLI and report them all fresh.
        # A stable sentinel keeps the signature comparable and honest.
        return _digest(_UNKNOWN_SURFACE)

    entries = sorted(_walk_click(group, prefix=""))
    return _digest("\n".join(entries))


def _walk_click(group: object, *, prefix: str) -> list[str]:
    """Return ``"<path>::<sorted flags>"`` lines for *group* and its subtree."""
    import click

    if not isinstance(group, click.Group):
        return []

    lines: list[str] = []
    ctx = click.Context(group)
    for name in group.list_commands(ctx):
        cmd = group.get_command(ctx, name)
        if cmd is None:
            continue
        path = f"{prefix}{name}"
        flags = sorted(
            opt
            for param in cmd.params
            if isinstance(param, click.Option)
            for opt in param.opts
        )
        lines.append(f"{path}::{','.join(flags)}")
        if isinstance(cmd, click.Group):
            lines.extend(_walk_click(cmd, prefix=f"{path} "))
    return lines


def graph_signature(conn: sqlite3.Connection) -> str:
    """Coarse signature of the graph's node + edge identity set.

    Identity = sorted ``ref_id|kind`` for nodes and sorted
    ``src|dst|kind|contract_key`` for edges (not node summaries or extra) — so a
    cosmetic content edit does not fire, but a structural add/remove does.
    """
    node_rows = conn.execute("SELECT ref_id, kind FROM nodes").fetchall()
    nodes = sorted(f"{r['ref_id']}|{r['kind']}" for r in node_rows)

    edge_rows = conn.execute(
        "SELECT src_ref_id, dst_ref_id, kind, contract_key FROM edges"
    ).fetchall()
    edges = sorted(
        f"{r['src_ref_id']}|{r['dst_ref_id']}|{r['kind']}|{r['contract_key']}"
        for r in edge_rows
    )

    payload = "NODES\n" + "\n".join(nodes) + "\nEDGES\n" + "\n".join(edges)
    return _digest(payload)


def flow_signature(project_root: Path) -> str:
    """Coarse signature of ``.beadloom/flow.yml`` (canonical re-serialization).

    Returns ``""`` when the file is absent or empty/invalid YAML. Otherwise the
    parsed mapping is re-serialized with sorted keys, so comments, key order and
    whitespace do not move the signature — only the effective config does.
    """
    flow_path = project_root / ".beadloom" / "flow.yml"
    if not flow_path.is_file():
        return ""
    try:
        data = yaml.safe_load(flow_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return ""
    if data is None:
        return ""
    canonical = yaml.safe_dump(data, sort_keys=True, default_flow_style=False)
    return _digest(canonical)


def surface_signature(surface: str, conn: sqlite3.Connection, project_root: Path) -> str:
    """Dispatch to the per-surface signature for *surface*.

    Raises ``ValueError`` for an unknown surface (callers should pre-filter via
    :func:`parse_watches`, which only yields known surfaces).
    """
    if surface == "cli":
        return cli_signature()
    if surface == "graph":
        return graph_signature(conn)
    if surface == "flow.yml":
        return flow_signature(project_root)
    raise ValueError(f"unknown surface: {surface!r}")


def aggregate_hash(
    watches: list[str],
    conn: sqlite3.Connection,
    project_root: Path,
) -> str:
    """SHA-256 of the *watches* surfaces' signatures, concatenated in order.

    Order-sensitive by design: the declared order is part of the doc's contract,
    so ``[cli, graph]`` and ``[graph, cli]`` are distinct baselines.
    """
    parts = [surface_signature(s, conn, project_root) for s in watches]
    return _digest("|".join(parts))


def _digest(text: str) -> str:
    """SHA-256 hex digest of *text* (UTF-8)."""
    return hashlib.sha256(text.encode()).hexdigest()
