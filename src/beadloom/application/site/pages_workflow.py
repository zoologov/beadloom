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
- the **branch** it deploys from: the default branch the project's own git
  records for its remote (``origin/HEAD``), read when the file is written and
  named in the push trigger, so a push to another branch starts no run. When git
  records none, no branch is named - a branch the project did not choose is
  never guessed - and every push starts a run the build job skips. Either way
  the build job runs only when the ref is a BRANCH and is the repository's
  default at run time, so a tag named like it, a stale trigger after a rename or
  a manual run on another branch deploys nothing.

Hardened after R2 (BDL-076 ``beadloom-ujzb.20``, finding F10): the workflow
grants nothing by default; ``build``, which runs third-party install scripts,
only reads; ``deploy`` alone writes Pages and mints the OIDC token. Every action
is pinned by the full commit of a release, named in a comment. A value holding
an Actions expression (``${{``) is refused, because quoting keeps the YAML's
structure and Actions still evaluates the expression.

The workflow carries the scaffold's generated marker, so the rule is the
scaffold's rule (:func:`~beadloom.application.site.scaffold.place_marked`): a
workflow beadloom wrote and nobody edited is rewritten when its inputs change,
and any other file at that path is left as it is and reported.
"""

from __future__ import annotations

import json
import logging
import re
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from beadloom.application.site.scaffold import marker_line, place_marked, shipped_files

if TYPE_CHECKING:
    from importlib.abc import Traversable

#: Where the workflow is written, relative to the project root.
PAGES_WORKFLOW_PATH = Path(".github") / "workflows" / "beadloom-portal.yml"

logger = logging.getLogger(__name__)

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
  push:@BRANCHES@
  workflow_dispatch:

# Nothing by default: each job declares what it needs.
permissions: {}

# The Pages actions below still ship Node 20 entry points; this runs them on
# Node 24, the runtime GitHub moves every action to.
env:
  FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true

jobs:
  build:
    # A branch, and the default one: a tag of the same name is no branch.
    if: github.ref_type == 'branch' && github.ref_name == github.event.repository.default_branch
    runs-on: ubuntu-latest
    # Reads the repository and the Pages site; runs install scripts, so writes nothing.
    permissions:
      contents: read
      pages: read
    env:
      PORTAL_BASE: @BASE@
    steps:
      - uses: actions/checkout@@CHECKOUT@

      - name: Configure Pages
        id: pages
        uses: actions/configure-pages@@CONFIGURE_PAGES@

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

      - uses: actions/setup-python@@SETUP_PYTHON@
        with:
          python-version: "3.12"

      - name: Install beadloom
        run: @INSTALL@

      - name: Index the project
        run: beadloom reindex

      - name: Generate the portal
        run: @GENERATE@

      - uses: actions/setup-node@@SETUP_NODE@
        with:
          node-version: @NODE@

      - name: Install the portal's dependencies
        run: npm ci
        working-directory: @SITE_DIR@

      - name: Build the portal
        run: npm run docs:build
        working-directory: @SITE_DIR@

      - uses: actions/upload-pages-artifact@@UPLOAD_PAGES_ARTIFACT@
        with:
          path: @DIST@

  deploy:
    needs: build
    runs-on: ubuntu-latest
    # The only job that publishes: Pages write, and the OIDC token deploy-pages presents.
    permissions:
      pages: write
      id-token: write
    concurrency:
      group: pages
      cancel-in-progress: false
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@@DEPLOY_PAGES@
"""

#: Each action the workflow uses, pinned by the full commit of a release; the
#: release is written beside it. Majors are the ones this repository's own
#: workflows run. Each commit was read with ``git ls-remote`` from the action's
#: repository on 2026-10-01, and the tags are lightweight, so each names the
#: commit itself.
_PINS = {
    "@CHECKOUT@": ("fbc6f3992d24b796d5a048ff273f7fcc4a7b6c09", "v5.1.0"),
    "@CONFIGURE_PAGES@": ("983d7736d9b0ae728b81ab479565c72886d7745b", "v5.0.0"),
    "@SETUP_PYTHON@": ("ece7cb06caefa5fff74198d8649806c4678c61a1", "v6.3.0"),
    "@SETUP_NODE@": ("a0853c24544627f65ddf259abe73b1d18a591444", "v5.0.0"),
    "@UPLOAD_PAGES_ARTIFACT@": ("56afc609e74202658d3ffba0e8f6dda462b719fa", "v3.0.1"),
    "@DEPLOY_PAGES@": ("d6db90164ac5ed86f2b6aed7e0febac5b3c0c03e", "v4.0.5"),
}

#: What Actions evaluates wherever it stands in a workflow, quoted or not.
_EXPRESSION = "${{"

#: The prefix ``git symbolic-ref --short`` gives a branch of the ``origin`` remote.
_ORIGIN_PREFIX = "origin/"


class PagesWorkflowError(ValueError):
    """The workflow cannot be written for this project as it stands."""


@dataclass(frozen=True)
class PagesWorkflowReport:
    """What one run did with the workflow, and what the workflow it wanted holds.

    ``branch`` is the branch the push trigger names, ``""`` when git recorded
    no default branch. ``reason`` and ``remediation`` are set only when the file
    there was kept.
    """

    path: str
    outcome: Literal["written", "updated", "unchanged", "kept"]
    base: str
    node_major: str
    site_dir: str
    branch: str = ""
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
    site_dir = out.relative_to(root).as_posix()
    _refuse_expression(site_dir, "--out")
    return site_dir


def default_branch_of(project_root: Path) -> str:
    """The default branch git records for the project's ``origin`` remote, or ``""``.

    Read from ``origin/HEAD``, which a clone sets and ``git remote set-head
    origin --auto`` refreshes. ``""`` outside git, without the ref, or when it
    names no branch of ``origin``: the workflow then names no branch rather than
    one the project did not choose.
    """
    try:
        result = subprocess.run(
            ["git", "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"],  # noqa: S607 - the git on PATH, as every git read here
            cwd=project_root,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError as exc:
        logger.debug("git is not available to read the default branch: %s", exc)
        return ""
    name = result.stdout.strip() if result.returncode == 0 else ""
    return name.removeprefix(_ORIGIN_PREFIX) if name.startswith(_ORIGIN_PREFIX) else ""


def _refuse_expression(value: str, named: str) -> None:
    """Raise :class:`PagesWorkflowError` when *value* holds an Actions expression."""
    if _EXPRESSION in value:
        raise PagesWorkflowError(
            f"{named} holds `{_EXPRESSION}`, which GitHub Actions would evaluate as an "
            "expression in the workflow; write it without that sequence"
        )


def render_pages_workflow(
    *, base: str, site_dir: str, node_major: str, version: str, branch: str = ""
) -> str:
    """The workflow's body, without its marker line.

    Every value reaches the YAML as a JSON string, which YAML reads as a
    double-quoted scalar, so a path holding `#` or `: ` cannot change the file's
    structure; the ones a shell also reads are quoted for the shell first. A
    value holding ``${{`` is refused, because Actions evaluates it however it is
    quoted. *branch* is the one the push trigger names; ``""`` names none.
    """
    for value, named in (
        (base, "site.base"),
        (site_dir, "--out"),
        (branch, "the default branch"),
        (node_major, "engines.node"),
        (version, "the beadloom version"),
    ):
        _refuse_expression(value, named)
    install = f'python -m pip install "beadloom[languages]=={version}"'
    values = {
        "@BRANCHES@": f"\n    branches: [{json.dumps(branch)}]" if branch else "",
        "@BASE@": json.dumps(base),
        "@INSTALL@": json.dumps(install),
        "@GENERATE@": json.dumps(f"beadloom docs site --out {shlex.quote(site_dir)}"),
        "@NODE@": json.dumps(node_major),
        "@SITE_DIR@": json.dumps(site_dir),
        "@DIST@": json.dumps(f"{site_dir}/.vitepress/dist"),
    }
    values.update({key: f"{sha} # {release}" for key, (sha, release) in _PINS.items()})
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
    branch: str | None = None,
) -> PagesWorkflowReport:
    """Write the Pages workflow for the portal at *out_dir*, unless a file there is not ours.

    Args:
        project_root: The project; the workflow is written under its ``.github/``.
        out_dir: The portal directory ``docs site`` writes, inside the project.
        base: The base path the portal is built for, from the ``site:`` block.
        version: The installed beadloom version, which the workflow installs.
        source: Replaces the installed package's scaffold, for a test.
        branch: The branch the push trigger names; read with
            :func:`default_branch_of` when not given.
    """
    site_dir = site_dir_of(project_root, out_dir)
    node_major = _node_major_of_scaffold(source)
    named = default_branch_of(project_root) if branch is None else branch
    body = render_pages_workflow(
        base=base, site_dir=site_dir, node_major=node_major, version=version, branch=named
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
        branch=named,
        reason=placed.reason,
        remediation=remediation,
    )
