# beadloom:domain=application
# beadloom:feature=site-generation
"""The GitHub Pages workflow that publishes a project's portal.

BDL-076 B2 (``beadloom-qki6``). ``beadloom docs site --pages-workflow`` writes
``.github/workflows/beadloom-portal.yml`` beside the portal. The workflow does in
CI what ``docs site`` did on the adopter's machine: it installs the beadloom that
wrote it, reindexes, regenerates the portal into the same directory, builds it
with the Node major the scaffold's ``package.json`` declares under
``engines.node``, and deploys it to Pages.

Three facts are the project's, and each comes from where the project declares it:

- the **base path**, from the ``site:`` block. The workflow compares it with the
  path GitHub Pages reports for the repository and fails before building when
  they differ, because a portal built for another base loads none of its assets;
- the **portal directory**, from ``--out``, which must lie inside the project;
- the **branch** it deploys from, which is not written at all: the build job runs
  only on the repository's default branch, read from the event at run time.

The workflow carries the scaffold's generated marker, so the rule is the
scaffold's rule (:func:`~beadloom.application.site.scaffold.place_marked`): a
workflow beadloom wrote and nobody edited is rewritten when its inputs change,
and any other file at that path is left as it is and reported.
"""

from __future__ import annotations

import json
import re
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from beadloom.application.site.scaffold import marker_line, place_marked, shipped_files

if TYPE_CHECKING:
    from importlib.abc import Traversable

#: Where the workflow is written, relative to the project root.
PAGES_WORKFLOW_PATH = Path(".github") / "workflows" / "beadloom-portal.yml"

#: The lowest major a range admits: `>=20`, `^20.1`, `~22`, `20.x`, `>= 22 <24`.
_LOWEST_MAJOR = re.compile(r"^\s*(?:>=|\^|~)?\s*v?(?P<major>\d+)(?:\.|\s|$)")

_NOTE = "written by `beadloom docs site --pages-workflow`; an edited copy is never written over"

_TEMPLATE = """\
# Publishes the portal `beadloom docs site` writes to GitHub Pages.
#
# Each run regenerates the portal from the project, with the beadloom that wrote
# this file, and deploys it only from the repository's default branch. Pages must
# be enabled with GitHub Actions as its source (Settings -> Pages -> Source).
#
# Run `beadloom docs site --pages-workflow` again after upgrading beadloom or
# changing the `site:` block of .beadloom/config.yml: it rewrites this file while
# the file is as beadloom wrote it.

name: Deploy the beadloom portal to GitHub Pages

on:
  push:
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

# The Pages actions below still ship Node 20 entry points; this runs them on
# Node 24, the runtime GitHub moves every action to.
env:
  FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true

jobs:
  build:
    if: github.ref_name == github.event.repository.default_branch
    runs-on: ubuntu-latest
    env:
      PORTAL_BASE: @BASE@
    steps:
      - uses: actions/checkout@v5

      - name: Configure Pages
        id: pages
        uses: actions/configure-pages@v5

      - name: Check the portal's base against the Pages address
        env:
          PAGES_BASE_PATH: ${{ steps.pages.outputs.base_path }}
        run: |
          served="${PAGES_BASE_PATH%/}/"
          if [ "$served" != "$PORTAL_BASE" ]; then
            where="GitHub Pages serves this repository under $served"
            built="the portal is built for $PORTAL_BASE"
            fix="set site.base to $served in .beadloom/config.yml"
            fix="$fix and run beadloom docs site --pages-workflow again"
            echo "::error::$where, and $built; $fix."
            exit 1
          fi

      - uses: actions/setup-python@v6
        with:
          python-version: "3.12"

      - name: Install beadloom
        run: @INSTALL@

      - name: Index the project
        run: beadloom reindex

      - name: Generate the portal
        run: @GENERATE@

      - uses: actions/setup-node@v5
        with:
          node-version: @NODE@

      - name: Install the portal's dependencies
        run: npm ci
        working-directory: @SITE_DIR@

      - name: Build the portal
        run: npm run docs:build
        working-directory: @SITE_DIR@

      - uses: actions/upload-pages-artifact@v3
        with:
          path: @DIST@

  deploy:
    needs: build
    runs-on: ubuntu-latest
    concurrency:
      group: pages
      cancel-in-progress: false
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
"""


class PagesWorkflowError(ValueError):
    """The workflow cannot be written for this project as it stands."""


@dataclass(frozen=True)
class PagesWorkflowReport:
    """What one run did with the workflow, and what the workflow it wanted holds.

    ``reason`` and ``remediation`` are set only when the file there was kept.
    """

    path: str
    outcome: Literal["written", "updated", "unchanged", "kept"]
    base: str
    node_major: str
    site_dir: str
    reason: str = ""
    remediation: str = ""


def node_major_of(engines_node: str) -> str:
    """The lowest Node major *engines_node* admits: the one the workflow sets up.

    Raises :class:`PagesWorkflowError` for a range with no lowest major, such
    as ``*`` or ``<22``: a workflow would then pick a Node nobody declared.
    """
    found = _LOWEST_MAJOR.match(engines_node)
    if found is None:
        raise PagesWorkflowError(
            f"the portal's package.json declares engines.node as `{engines_node}`, "
            "which names no lowest Node major for the workflow to set up"
        )
    return found["major"]


def site_dir_of(project_root: Path, out_dir: Path) -> str:
    """*out_dir* as the workflow names it: a path inside the project, relative to its root.

    Raises :class:`PagesWorkflowError` when *out_dir* is not inside the project,
    because a workflow runs in a checkout of the project and nowhere else.
    """
    root = project_root.resolve()
    out = out_dir.resolve()
    if out == root or not out.is_relative_to(root):
        raise PagesWorkflowError(
            f"--pages-workflow needs the portal inside the project, and --out is {out_dir}; "
            f"name a directory inside the project, such as {root / 'site'}"
        )
    return out.relative_to(root).as_posix()


def render_pages_workflow(*, base: str, site_dir: str, node_major: str, version: str) -> str:
    """The workflow's body, without its marker line.

    Every value reaches the YAML as a JSON string, which YAML reads as a
    double-quoted scalar, so a path holding `#` or `: ` cannot change the file's
    structure; the ones a shell also reads are quoted for the shell first.
    """
    install = f'python -m pip install "beadloom[languages]=={version}"'
    values = {
        "@BASE@": json.dumps(base),
        "@INSTALL@": json.dumps(install),
        "@GENERATE@": json.dumps(f"beadloom docs site --out {shlex.quote(site_dir)}"),
        "@NODE@": json.dumps(node_major),
        "@SITE_DIR@": json.dumps(site_dir),
        "@DIST@": json.dumps(f"{site_dir}/.vitepress/dist"),
    }
    body = _TEMPLATE
    for placeholder, value in values.items():
        body = body.replace(placeholder, value)
    return body


def _node_major_of_scaffold(source: Traversable | Path | None) -> str:
    package = json.loads(shipped_files(source)["package.json"])
    engines = package.get("engines", {}) if isinstance(package, dict) else {}
    declared = engines.get("node") if isinstance(engines, dict) else None
    if not isinstance(declared, str):
        raise PagesWorkflowError("the portal's package.json declares no engines.node")
    return node_major_of(declared)


def write_pages_workflow(
    project_root: Path,
    *,
    out_dir: Path,
    base: str,
    version: str,
    source: Traversable | Path | None = None,
) -> PagesWorkflowReport:
    """Write the Pages workflow for the portal at *out_dir*, unless a file there is not ours.

    Args:
        project_root: The project; the workflow is written under its ``.github/``.
        out_dir: The portal directory ``docs site`` writes, inside the project.
        base: The base path the portal is built for, from the ``site:`` block.
        version: The installed beadloom version, which the workflow installs.
        source: Replaces the installed package's scaffold, for a test.
    """
    site_dir = site_dir_of(project_root, out_dir)
    node_major = _node_major_of_scaffold(source)
    body = render_pages_workflow(
        base=base, site_dir=site_dir, node_major=node_major, version=version
    )
    expected = f"# {marker_line(body, version, _NOTE)}\n{body}"
    rel = PAGES_WORKFLOW_PATH.as_posix()
    placed = place_marked(project_root / PAGES_WORKFLOW_PATH, expected)
    remediation = ""
    if placed.outcome == "kept":
        remediation = (
            f"beadloom leaves {rel} as it is; to take the generated workflow, delete it "
            "and run `beadloom docs site --pages-workflow` again"
        )
    return PagesWorkflowReport(
        path=rel,
        outcome=placed.outcome,
        base=base,
        node_major=node_major,
        site_dir=site_dir,
        reason=placed.reason,
        remediation=remediation,
    )
