"""A two-component project with one live import boundary, built and indexed in ``tmp_path``.

Moved out of ``test_s2_false_green_residue.py`` when BDL-074 E1 split it by node:
the lint, ``sync-check``, the Gate, ``doctor`` and ``docs audit`` cases all attack the
same project from outside, and a helper several test modules share lives here.
Defaults give a clean project with one live ``forbid_import`` rule; each test
overrides only the axis it is about.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.application.reindex import reindex

if TYPE_CHECKING:
    from pathlib import Path


# The clean alpha still imports SOMETHING: `evaluate_import_boundary_rules` is
# deliberately silent when the index holds no imports at all (that is lint's
# "0 files scanned" header), so an import-free fixture would make every
# liveness assertion below vacuous.
ALPHA_CLEAN = (
    "# beadloom:component=alpha\n'''Alpha.'''\n\n"
    "import os\n\n\ndef run() -> int:\n    return len(os.sep)\n"
)


ALPHA_CROSSING = (
    "# beadloom:component=alpha\n'''Alpha.'''\n\n"
    "import os\n\nfrom app.beta import tokens\n\n\n"
    "def run() -> int:\n    return tokens.verify() + len(os.sep)\n"
)


_BETA = (
    "# beadloom:component=beta\n'''Beta.'''\n\n"
    "from app.beta import util\n\n\ndef verify() -> int:\n    return util.two()\n"
)


#: Beta imports its own sibling so that the live rule's `to:` glob matches
#: SOMETHING in the index. Without it the rule is inert and BDL-061.43's
#: liveness finding fires on the fixture itself, drowning every assertion below.
_BETA_UTIL = "# beadloom:component=beta\n'''Beta util.'''\n\n\ndef two() -> int:\n    return 2\n"


#: The doc must NAME the module it documents: an unmentioned module is a
#: `missing_modules` staleness reason, which would make every Gate assertion
#: below red for a reason that has nothing to do with what is under test.
ALPHA_DOC = "# Alpha\n\nThe `service` module runs alpha.\n"


_NODES = """\
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
edges: []
"""


#: The live boundary rule the fixture is built around: alpha must not import beta.
LIVE_RULE = """\
  - name: alpha-no-beta-import
    description: Alpha must not import beta
    severity: error
    forbid_import:
      from: 'src/app/alpha/*'
      to: 'app/beta*'
"""


def rules_yml(*rule_blocks: str) -> str:
    """Assemble a ``rules.yml`` from rule blocks, live rule first."""
    return "version: 1\nrules:\n" + "".join(rule_blocks)


def make_project(
    root: Path,
    *,
    rules: str | None = None,
    alpha_source: str = ALPHA_CLEAN,
) -> Path:
    """Build a minimal indexable project and return its root.

    Defaults give a clean project with one live ``forbid_import`` rule; each
    test overrides only the axis it is about.
    """
    project = root / "proj"
    (project / ".beadloom" / "_graph").mkdir(parents=True)
    (project / "docs" / "components").mkdir(parents=True)
    (project / ".beadloom" / "config.yml").write_text(
        "scan_paths:\n  - src\ndocs_dir: docs\n", encoding="utf-8"
    )
    (project / ".beadloom" / "_graph" / "services.yml").write_text(_NODES, encoding="utf-8")
    (project / ".beadloom" / "_graph" / "rules.yml").write_text(
        rules if rules is not None else rules_yml(LIVE_RULE), encoding="utf-8"
    )
    (project / "docs" / "components" / "alpha.md").write_text(ALPHA_DOC, encoding="utf-8")
    (project / "docs" / "components" / "beta.md").write_text(
        "# Beta\n\nThe `tokens` and `util` modules verify beta.\n", encoding="utf-8"
    )
    for pkg in ("alpha", "beta"):
        (project / "src" / "app" / pkg).mkdir(parents=True)
        (project / "src" / "app" / pkg / "__init__.py").write_text("", encoding="utf-8")
    (project / "src" / "app" / "__init__.py").write_text("", encoding="utf-8")
    (project / "src" / "app" / "alpha" / "service.py").write_text(alpha_source, encoding="utf-8")
    (project / "src" / "app" / "beta" / "tokens.py").write_text(_BETA, encoding="utf-8")
    (project / "src" / "app" / "beta" / "util.py").write_text(_BETA_UTIL, encoding="utf-8")
    return project


def indexed_project(root: Path, **kwargs: str) -> Path:
    """Build the project and index it once."""
    project = make_project(root, **kwargs)
    reindex(project)
    return project
