"""A project in which each staleness reason can be produced on demand.

BDL-069 S1 (`beadloom-h7b3`). A remediation is only as good as the reason it was
printed for, and whether re-attesting clears a reason is a fact about the real
pipeline — reindex, ``check_sync``, ``attest_ref`` — not about a table a test
fills in by hand. So every reason is produced here by doing what an adopter does
(edit a file, add a file, rebuild the index) and read back through the check.

The node owns ONE document paired with several code files, because a pair is a
document AND a code file: two files give two pairs over one document, and that
is exactly the population the rendering half of the bead is about.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING, Any

import yaml

from beadloom.application.reindex import reindex
from beadloom.doc_sync.engine import attest_ref, check_sync
from beadloom.infrastructure.db import open_db

if TYPE_CHECKING:
    from pathlib import Path

#: The node, its document as the index spells it (relative to ``docs/``), and the
#: code files the document is paired with.
REF_ID = "widgets"
DOC_PATH = "widgets.md"
MODULES = ("alpha", "beta")
SOURCE = "src/widgets/"


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)  # noqa: S603, S607


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def document_naming(*modules: str) -> str:
    """The document's text, naming exactly *modules*."""
    rows = "\n".join(f"- `{name}.py`" for name in modules)
    return f"# {REF_ID}\n\n## Modules\n\n{rows}\n"


def annotated_module(name: str, body: str = "pass") -> str:
    return f"# beadloom:domain={REF_ID}\ndef {name}():\n    {body}\n"


def build(root: Path, *, documents: tuple[str, ...] = (DOC_PATH,)) -> Path:
    """A committed repository, one node, *documents* each naming every module.

    The index is built from the committed tree, so every pair starts ``ok`` and
    its baseline is the one a fresh adopter has.
    """
    root.mkdir(parents=True, exist_ok=True)
    node = {
        "ref_id": REF_ID,
        "kind": "domain",
        "summary": REF_ID,
        "source": SOURCE,
        "docs": list(documents),
    }
    write(root, ".beadloom/_graph/graph.yml", yaml.dump({"nodes": [node]}))
    for document in documents:
        write(root, f"docs/{document}", document_naming(*MODULES))
    for name in MODULES:
        write(root, f"{SOURCE}{name}.py", annotated_module(name))
    write(root, ".gitignore", ".beadloom/beadloom.db\n")
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "Test")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "baseline")
    reindex(root)
    return root


def verdicts(root: Path) -> list[dict[str, Any]]:
    """Every row the freshness check returns, as the engine returns it."""
    conn = open_db(root / ".beadloom" / "beadloom.db")
    try:
        return check_sync(conn, project_root=root)
    finally:
        conn.close()


def stale(root: Path) -> list[dict[str, Any]]:
    return [row for row in verdicts(root) if row["status"] == "stale"]


def attest_stale(root: Path) -> None:
    """Re-attest every stale pair, the scope ``sync-update --yes`` claims."""
    rows = verdicts(root)
    scope = {(row["doc_path"], row["code_path"]) for row in rows if row["status"] == "stale"}
    conn = open_db(root / ".beadloom" / "beadloom.db")
    try:
        attest_ref(conn, REF_ID, root, scope=scope)
    finally:
        conn.close()


# --- The mutations, one per reason -------------------------------------------


def change_a_body(root: Path) -> None:
    """``hash_changed``: a code file's bytes move against an ATTESTED baseline.

    Against the baseline a fresh index builds, the same edit reads as
    ``hash_changed_since_head`` instead, because git is what sees it.
    """
    conn = open_db(root / ".beadloom" / "beadloom.db")
    try:
        attest_ref(conn, REF_ID, root, scope=None)
    finally:
        conn.close()
    write(root, f"{SOURCE}alpha.py", annotated_module("alpha", body="return 1"))
    reindex(root)


def change_a_body_on_a_rebuilt_index(root: Path) -> None:
    """``hash_changed_since_head``: the index is rebuilt over uncommitted code.

    A rebuilt index takes its baseline from the tree it was built from, so only
    git can see the drift — and it does, because the document did not move.
    """
    write(root, f"{SOURCE}alpha.py", annotated_module("alpha", body="return 1"))
    (root / ".beadloom" / "beadloom.db").unlink()
    reindex(root)


def add_an_annotated_module(root: Path) -> None:
    """``symbols_changed``: the node gains a file the document already names."""
    write(root, f"docs/{DOC_PATH}", document_naming(*MODULES, "gamma"))
    _git(root, "commit", "-q", "-am", "the document names gamma first")
    reindex(root)
    attest_stale(root)
    write(root, f"{SOURCE}gamma.py", annotated_module("gamma"))
    reindex(root)


def add_an_unannotated_module(root: Path) -> None:
    """``untracked_files``: a file under the source no pair and no annotation owns."""
    write(root, f"{SOURCE}gamma.py", "def gamma():\n    pass\n")
    reindex(root)


def unname_a_module(root: Path) -> None:
    """``missing_modules``: the document stops naming a module of its source."""
    write(root, f"docs/{DOC_PATH}", document_naming("alpha"))
    reindex(root)
