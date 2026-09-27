"""'A file lies under a node's source' is one rule, and every reader of it calls it (BDL-069).

`beadloom-rqma.4`. The rule was written three times, in three domains, each body on
its own:

- `onboarding/doc_generator._symbols_for_node` matched by path component, since
  `beadloom-6rgr` repaired a string prefix there;
- `application/reindex/enrichment._extract_and_store_routes` matched by STRING
  PREFIX, so `src/ledger/` took the routes of `src/ledger_archive/`, and a node whose
  source is `''` took every route in the project;
- `infrastructure/git_activity._map_file_to_node` matched by path component, and
  always had.

The three now call `infrastructure.node_source.NodeSource`, and the cases below are
stated over the RULE and run against every site, rather than over the one site that
was wrong. Run against the three bodies before the change, the table found the two
correct ones disagreeing as well: `git_activity` held nothing for a source written
with surrounding whitespace, and `doc_generator` nothing for one with a leading `./`.

**Two shapes, because a fix for one breaks the other.** A prefix-sharing sibling is
the defect. A source that is ONE file is where the obvious repair goes wrong: a match
on `source + "/"` alone takes nothing for `src/ledger/core.py`, since no path starts
with `src/ledger/core.py/`.

`infrastructure.repository.source_covers` is NOT this rule and is not a site: it
answers which node OWNS a file, where a package facade covers its package. The
polish reader keeps a facade source to the facade, because the skeleton's disk
reader does, and `beadloom-6rgr` holds those two readers together.
"""

from __future__ import annotations

import ast
import inspect
import json
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest

from beadloom.application.reindex import enrichment
from beadloom.application.reindex.enrichment import _extract_and_store_routes
from beadloom.context_oracle.route_extractor import Route
from beadloom.infrastructure import git_activity
from beadloom.infrastructure.db import create_schema, open_db
from beadloom.infrastructure.git_activity import _map_file_to_node
from beadloom.infrastructure.node_source import NodeSource
from beadloom.onboarding import doc_generator
from beadloom.onboarding.doc_generator import _symbols_for_node

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

#: Every file the cases are asked about. `src/ledger_archive/`, `src/ledgerx/`,
#: `src/ledger.py` and `src/ledger_tools.py` all start with the characters
#: `src/ledger` and none is inside `src/ledger/`; `src/app.tsx` starts with the
#: characters `src/app.ts`, the prefix-sharing sibling of a single-file source.
FILES = (
    "src/ledger/__init__.py",
    "src/ledger/core.py",
    "src/ledger/postings/rules.py",
    "src/ledger_archive/core.py",
    "src/ledgerx/core.py",
    "src/ledger.py",
    "src/ledger_tools.py",
    "src/app.ts",
    "src/app.tsx",
)

THE_PACKAGE = ["src/ledger/__init__.py", "src/ledger/core.py", "src/ledger/postings/rules.py"]

#: (declared source, the files that lie under it). A declared source is typed by a
#: person into a graph file, so the spellings of one directory are cases of their own.
CASES = [
    pytest.param("src/ledger/", THE_PACKAGE, id="directory"),
    pytest.param("src/ledger", THE_PACKAGE, id="directory-without-trailing-slash"),
    pytest.param(" src/ledger/ ", THE_PACKAGE, id="surrounding-whitespace"),
    pytest.param("./src/ledger/", THE_PACKAGE, id="leading-dot-segment"),
    pytest.param("src/ledger/core.py", ["src/ledger/core.py"], id="single-file"),
    pytest.param("src/ledger.py", ["src/ledger.py"], id="single-file-beside-its-package"),
    pytest.param("src/app.ts", ["src/app.ts"], id="single-file-with-a-prefix-sharing-sibling"),
    pytest.param("src/ledger/__init__.py", ["src/ledger/__init__.py"], id="package-facade"),
    pytest.param("", [], id="empty"),
    pytest.param("/", [], id="a-lone-slash"),
    pytest.param(None, [], id="none"),
]


# ------------------------------------------------------------------
# The rule
# ------------------------------------------------------------------


@pytest.mark.parametrize(("source", "expected"), CASES)
def test_the_rule_holds_the_files_under_a_source_and_no_sibling(
    source: str | None, expected: list[str]
) -> None:
    under = NodeSource(source)

    assert [path for path in FILES if under.holds(path)] == expected


@pytest.mark.parametrize(
    ("source", "path"),
    [
        ("src/ledger/", "src/ledger"),
        ("src/ledger", "src/ledger"),
        (" ./src/ledger/ ", "src/ledger"),
        ("src/ledger/core.py", "src/ledger/core.py"),
        ("", ""),
        ("/", ""),
        (None, ""),
    ],
)
def test_the_rule_states_the_source_it_normalised(source: str | None, path: str) -> None:
    """`git_activity` ranks the nodes holding a file by this length, most specific first."""
    assert NodeSource(source).path == path


@pytest.mark.parametrize("source", ["", "/", None])
def test_a_source_that_declares_nothing_holds_no_path_not_even_an_absolute_one(
    source: str | None,
) -> None:
    """Nothing is below an empty source, including a path that starts with `/`.

    Every site passes a project-relative path today, and `Route.file_path` is absolute,
    so a fourth site handing the extractor's path straight in is one edit away.
    """
    under = NodeSource(source)

    assert not under.holds("/project/src/ledger/core.py")
    assert not under.holds("")


# ------------------------------------------------------------------
# Every site, over the same cases
# ------------------------------------------------------------------


def _polish_symbols(source: str | None, _tmp_path: Path) -> list[str]:
    """`docs polish`: the index rows `_symbols_for_node` gives a node."""
    index = {path: [{"symbol_name": path, "file_path": path}] for path in FILES}
    rows = _symbols_for_node({"ref_id": "ledger", "source": source}, index)
    return sorted({str(row["symbol_name"]) for row in rows})


def _git_activity(source: str | None, _tmp_path: Path) -> list[str]:
    """`reindex`'s activity: the files `_map_file_to_node` gives the one node declared.

    `_store_git_activity` never passes a node without a source, so `None` reaches this
    site as the empty string it would have been filtered out as.
    """
    return [path for path in FILES if _map_file_to_node(path, {"ledger": source or ""})]


def _reindex_routes(source: str | None, tmp_path: Path) -> list[str]:
    """`reindex`'s routes: the files of the routes `_extract_and_store_routes` stores.

    Every file serves one route, so a wrong attribution names the file it came from.
    The extractor is replaced because what is under test is the attribution, and
    `.ts` files would otherwise need a grammar the attribution never reads.
    """
    for relative in FILES:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")

    def one_route_per_file(file_path: Path, _language: str) -> list[Route]:
        return [Route("GET", f"/{file_path.name}", "handler", str(file_path), 1, "fastapi")]

    conn = open_db(tmp_path / "beadloom.db")
    try:
        create_schema(conn)
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, source) VALUES (?, ?, ?)",
            ("ledger", "domain", source),
        )
        with patch("beadloom.context_oracle.route_extractor.extract_routes", one_route_per_file):
            _extract_and_store_routes(tmp_path, conn)
        (extra,) = conn.execute("SELECT extra FROM nodes WHERE ref_id = 'ledger'").fetchone()
    finally:
        conn.close()
    stored = json.loads(extra or "{}").get("routes", [])
    return sorted(str(route["file"]) for route in stored)


SITES: dict[str, Callable[[str | None, Path], list[str]]] = {
    "doc-generator": _polish_symbols,
    "git-activity": _git_activity,
    "reindex-routes": _reindex_routes,
}


@pytest.mark.parametrize("site", sorted(SITES))
@pytest.mark.parametrize(("source", "expected"), CASES)
def test_every_site_gives_a_node_the_files_under_its_source_and_no_sibling(
    site: str, source: str | None, expected: list[str], tmp_path: Path
) -> None:
    assert SITES[site](source, tmp_path) == sorted(expected)


def test_the_route_site_reaches_every_file_so_an_empty_answer_bites(tmp_path: Path) -> None:
    """Anti-vacuity for the route site: a directory source above every file takes all."""
    assert _reindex_routes("src", tmp_path) == sorted(FILES)


def test_a_node_that_declares_an_empty_source_is_given_no_route(tmp_path: Path) -> None:
    """The root a bootstrap declares has `source: ''`, and `''` prefixes every string.

    Measured on the foreign repository before the fix: the root node `rig` was given
    `GET /replay` from `src/ledger_archive/api.py`, beside `ledger` and `ledger_archive`.
    The same node's polish symbols were already `[]`, so one payload disagreed with
    itself about what the root holds.
    """
    assert _reindex_routes("", tmp_path) == []


# ------------------------------------------------------------------
# A route the reindex attributed earlier does not outlive the attribution
# ------------------------------------------------------------------

_FASTAPI_ROUTE = (
    'from fastapi import FastAPI\n\napp = FastAPI()\n\n\n@app.get("/replay")\n'
    "def replay() -> None:\n    pass\n"
)
_NO_ROUTE = "def replay() -> None:\n    pass\n"


def _project_serving_one_route(root: Path) -> None:
    graph_dir = root / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)
    (graph_dir / "services.yml").write_text(
        "nodes:\n"
        "  - ref_id: ledger\n    kind: domain\n    summary: Ledger\n    source: src/ledger/\n"
        "  - ref_id: ledger_archive\n    kind: domain\n    summary: Archive\n"
        "    source: src/ledger_archive/\n",
        encoding="utf-8",
    )
    for relative, text in {
        "src/ledger/core.py": "def record() -> None:\n    pass\n",
        "src/ledger_archive/api.py": _FASTAPI_ROUTE,
    }.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def _routes_by_node(root: Path) -> dict[str, list[str]]:
    conn = open_db(root / ".beadloom" / "beadloom.db")
    try:
        rows = conn.execute("SELECT ref_id, extra FROM nodes ORDER BY ref_id").fetchall()
    finally:
        conn.close()
    return {
        str(row["ref_id"]): [str(r["path"]) for r in json.loads(row["extra"] or "{}")["routes"]]
        for row in rows
        if "routes" in json.loads(row["extra"] or "{}")
    }


def test_a_route_the_old_rule_attributed_is_withdrawn_by_the_next_incremental_reindex(
    tmp_path: Path,
) -> None:
    """An index written before the fix is corrected by an ordinary reindex, not only `--full`.

    Measured on the foreign repository: with the rule fixed, an incremental reindex
    after a code change still left `ledger` and the root holding `GET /replay`. The
    route store only ever WROTE a node that had routes, so a route attributed wrongly
    once stayed attributed until a full rebuild dropped the table.
    """
    from beadloom.application.reindex import incremental_reindex, reindex

    _project_serving_one_route(tmp_path)
    reindex(tmp_path)
    conn = open_db(tmp_path / ".beadloom" / "beadloom.db")
    try:
        # What the string prefix stored: the sibling's route on `ledger`.
        (extra,) = conn.execute("SELECT extra FROM nodes WHERE ref_id = 'ledger'").fetchone()
        leaked = json.loads(extra or "{}")
        leaked["routes"] = [
            {"method": "GET", "path": "/replay", "file": "src/ledger_archive/api.py"}
        ]
        conn.execute("UPDATE nodes SET extra = ? WHERE ref_id = 'ledger'", (json.dumps(leaked),))
        conn.commit()
    finally:
        conn.close()
    (tmp_path / "src/ledger/core.py").write_text(
        "def record() -> None:\n    pass\n\n\ndef amend() -> None:\n    pass\n", encoding="utf-8"
    )

    incremental_reindex(tmp_path)

    assert _routes_by_node(tmp_path) == {"ledger_archive": ["/replay"]}


def test_a_route_removed_from_the_code_is_withdrawn_when_no_route_is_left(
    tmp_path: Path,
) -> None:
    """The last route leaving the project took an early return that cleared nothing."""
    from beadloom.application.reindex import incremental_reindex, reindex

    _project_serving_one_route(tmp_path)
    reindex(tmp_path)
    # Anti-vacuity: the route was stored, so there is something to withdraw.
    assert _routes_by_node(tmp_path) == {"ledger_archive": ["/replay"]}
    (tmp_path / "src/ledger_archive/api.py").write_text(_NO_ROUTE, encoding="utf-8")

    incremental_reindex(tmp_path)

    assert _routes_by_node(tmp_path) == {}


def test_git_activity_gives_a_file_to_the_most_specific_node_holding_it() -> None:
    """The ranking stays `git_activity`'s own; only 'holds' is the shared rule."""
    nodes = {
        "ledger": "src/ledger/",
        "ledger_archive": "src/ledger_archive",
        "recording": "src/ledger/core.py",
        "root": "",
    }

    assert {path: _map_file_to_node(path, nodes) for path in FILES} == {
        "src/ledger/__init__.py": "ledger",
        "src/ledger/core.py": "recording",
        "src/ledger/postings/rules.py": "ledger",
        "src/ledger_archive/core.py": "ledger_archive",
        "src/ledgerx/core.py": None,
        "src/ledger.py": None,
        "src/ledger_tools.py": None,
        "src/app.ts": None,
        "src/app.tsx": None,
    }


# ------------------------------------------------------------------
# No site keeps a copy
# ------------------------------------------------------------------

#: Each site, as (module, function). A site named here that stops calling the rule,
#: or starts comparing path strings itself, fails the case below.
SITE_FUNCTIONS: list[tuple[Any, str]] = [
    (doc_generator, "_symbols_for_node"),
    (enrichment, "_extract_and_store_routes"),
    (git_activity, "_map_file_to_node"),
]


@pytest.mark.parametrize(
    ("module", "function"),
    SITE_FUNCTIONS,
    ids=[f"{module.__name__}.{function}" for module, function in SITE_FUNCTIONS],
)
def test_each_site_calls_the_rule_and_compares_no_path_itself(module: Any, function: str) -> None:
    tree = ast.parse(inspect.getsource(getattr(module, function)))
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    string_prefix_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "startswith"
    ]

    assert "NodeSource" in names, f"{function} does not call the rule"
    assert string_prefix_calls == [], f"{function} still compares a path by itself"
