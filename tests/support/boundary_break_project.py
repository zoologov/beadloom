"""Two components with docs, a boundary rule between them, built in ``tmp_path``.

Moved out of ``test_s2_lying_checks.py`` when BDL-074 ``beadloom-2mj3.7`` split it by
node: the incremental reindex's import refresh and the ``sync-check`` and ``lint``
cases that stayed behind attack the same project, and a helper several test
modules share lives here rather than in either of them.
"""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

# The annotation deliberately sits INSIDE the module docstring — the shape the
# dogfood project hit in #146. It was invisible to the extractor (tree-sitter
# sees a string node, not a comment), so the symbol rows carried no annotation
# and every annotation-keyed reader silently saw nothing. SINCE BDL-061.50 the
# extractor READS this form, so these fixtures are genuinely annotated and #146's
# source-owned fallback is exercised instead by `gamma` in
# tests/test_s2_lying_checks.py (a node that declares docs and owns no file at
# all) and by the unannotated modules in
# tests/test_a_declaration_that_owns_nothing_is_reported.py.
ALPHA_CLEAN = (
    '"""Alpha service.\n\n# beadloom:component=alpha\n"""\n\n\ndef run() -> int:\n    return 1\n'
)
ALPHA_VIOLATING = (
    '"""Alpha service.\n\n# beadloom:component=alpha\n"""\n\n'
    "from app.beta import tokens\n\n\ndef run() -> int:\n    return tokens.verify()\n"
)
BETA = (
    '"""Beta tokens.\n\n# beadloom:component=beta\n"""\n\n\ndef verify() -> int:\n    return 2\n'
)

NODES_YML = """\
nodes:
  - ref_id: alpha
    kind: component
    summary: Alpha component
    source: src/app/alpha/
    docs:
      - components/alpha.md
  - ref_id: beta
    kind: component
    summary: Beta component
    source: src/app/beta/
    docs:
      - components/beta.md
"""


def services_yml(*, extra_nodes: str = "", edges: str = "edges: []\n") -> str:
    """Assemble a services.yml from the node block, optional extras, and edges."""
    return NODES_YML + extra_nodes + edges


RULES_YML = """\
version: 1
rules:
  - name: alpha-no-beta-import
    description: Alpha must not import beta
    severity: error
    forbid_import:
      from: 'src/app/alpha/*'
      to: 'app/beta*'
"""


def make_project(root: Path) -> Path:
    """Two component nodes, each with a doc, and a boundary rule between them."""
    project = root / "proj"
    (project / ".beadloom" / "_graph").mkdir(parents=True)
    (project / "docs" / "components").mkdir(parents=True)
    (project / ".beadloom" / "config.yml").write_text("scan_paths:\n  - src\ndocs_dir: docs\n")
    (project / ".beadloom" / "_graph" / "services.yml").write_text(services_yml())
    (project / ".beadloom" / "_graph" / "rules.yml").write_text(RULES_YML)
    (project / "docs" / "components" / "alpha.md").write_text(
        "# Alpha\n\nThe `service` module runs alpha.\n"
    )
    (project / "docs" / "components" / "beta.md").write_text(
        "# Beta\n\nThe `tokens` module verifies beta.\n"
    )
    (project / "src" / "app" / "alpha").mkdir(parents=True)
    (project / "src" / "app" / "beta").mkdir(parents=True)
    (project / "src" / "app" / "__init__.py").write_text("")
    (project / "src" / "app" / "alpha" / "__init__.py").write_text("")
    (project / "src" / "app" / "beta" / "__init__.py").write_text("")
    (project / "src" / "app" / "alpha" / "service.py").write_text(ALPHA_CLEAN)
    (project / "src" / "app" / "beta" / "tokens.py").write_text(BETA)
    return project


def index_db(project: Path) -> Path:
    return project / ".beadloom" / "beadloom.db"


def query(project: Path, sql: str, params: tuple[str, ...] = ()) -> list[tuple[object, ...]]:
    conn = sqlite3.connect(index_db(project))
    try:
        return [tuple(row) for row in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()
