"""A project that is not this repository builds its portal from ``docs site`` alone.

BDL-076 B1 (``beadloom-dfwt``), the bead's done-when. A small JavaScript project
with its own layers is initialised with ``beadloom init``, declares its identity
under ``site:``, and gets its portal from ``beadloom docs site``: no file is
copied from this repository. ``npm ci`` installs the locked dependencies the
scaffold ships, and ``vitepress build`` renders the portal. The built pages
carry the project's title, base path and repository link, and none of this
repository's.

Marked ``slow``: it installs the portal's npm dependencies and runs a production
build, about a minute on a warm npm cache. It runs when ``BEADLOOM_RUN_SLOW=1``
and Node 20 or later is on ``PATH``; otherwise it is skipped with the reason.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.slow

#: The oldest Node the scaffold's ``engines.node`` accepts.
_NODE_MAJOR = 20

_TITLE = "Acme Orders"
_BASE = "/orders/"
_REPO = "https://gitlab.com/acme/orders"

#: The project's own layers, a vocabulary this repository does not ship.
_LAYERS = ("interface", "core", "persistence")

_MODULES = {
    "src/api/handler.js": (
        'import { save } from "../store/db.js";\n'
        "export function handle(order) {\n  return save(order);\n}\n"
    ),
    "src/core/pricing.js": "export function price(order) {\n  return order.qty * 2;\n}\n",
    "src/store/db.js": (
        'import { price } from "../core/pricing.js";\n'
        "export function save(order) {\n  return price(order);\n}\n"
    ),
}

#: This repository's identity, as the portal used to carry it.
_OUR_IDENTITY = ("zoologov", "/beadloom/", "<title>Beadloom")


def _node_major(node: str) -> int:
    version = subprocess.run(  # noqa: S603 - the node on PATH, asked its version
        [node, "--version"], check=True, capture_output=True, encoding="utf-8"
    ).stdout.strip()
    return int(version.lstrip("v").split(".")[0])


@pytest.fixture()
def npm() -> str:
    npm_bin, node_bin = shutil.which("npm"), shutil.which("node")
    if npm_bin is None or node_bin is None:
        pytest.skip("npm and node are not on PATH, so no portal can be built in this room")
    if _node_major(node_bin) < _NODE_MAJOR:
        pytest.skip(f"node on PATH is older than the {_NODE_MAJOR} the scaffold declares")
    return npm_bin


def _beadloom(*args: str) -> str:
    result = CliRunner().invoke(main, list(args), catch_exceptions=False)
    assert result.exit_code == 0, result.output
    return result.output


def _layer_rule() -> str:
    lines = [
        "- name: project-layers",
        "  description: The orders service's layers import downward",
        "  severity: error",
        "  layers:",
    ]
    for name in _LAYERS:
        lines += [f"  - name: {name}", f"    tag: tier-{name}"]
    lines += ["  enforce: top-down", "  allow_skip: true", "  edge_kind: depends_on"]
    return "\n".join(lines) + "\n"


def _write_project(root: Path) -> None:
    (root / "package.json").parent.mkdir(parents=True)
    (root / "package.json").write_text(
        '{ "name": "acme-orders", "version": "0.1.0", "type": "module" }\n', encoding="utf-8"
    )
    (root / "README.md").write_text("# Acme Orders\n\nTakes orders.\n", encoding="utf-8")
    for rel, body in _MODULES.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(body, encoding="utf-8")


def _declare(root: Path) -> None:
    config = root / ".beadloom" / "config.yml"
    config.write_text(
        config.read_text(encoding="utf-8")
        + f"site:\n  title: {_TITLE}\n  base: {_BASE}\n  repo_url: {_REPO}\n",
        encoding="utf-8",
    )
    rules = root / ".beadloom" / "_graph" / "rules.yml"
    text = rules.read_text(encoding="utf-8")
    rules.write_text(text.replace("rules:\n", "rules:\n" + _layer_rule(), 1), encoding="utf-8")


def test_an_adopter_builds_its_portal_from_docs_site(tmp_path: Path, npm: str) -> None:
    root = tmp_path / "acme-orders"
    _write_project(root)
    _beadloom("init", "--yes", "--project", str(root))
    _declare(root)
    _beadloom("reindex", "--project", str(root))
    _beadloom("docs", "site", "--project", str(root))

    site = root / "site"
    for command in ([npm, "ci", "--no-audit", "--no-fund"], [npm, "run", "docs:build"]):
        subprocess.run(command, cwd=site, check=True, capture_output=True)  # noqa: S603

    dist = site / ".vitepress" / "dist"
    index = (dist / "index.html").read_text(encoding="utf-8")
    assert f"<title>{_TITLE}</title>" in index
    assert f'src="{_BASE}assets/' in index or f'href="{_BASE}assets/' in index
    assert _REPO in index
    built = [path for path in dist.rglob("*.html")]
    leaks = [
        (path.name, token)
        for path in built
        for token in _OUR_IDENTITY
        if token in path.read_text(encoding="utf-8")
    ]
    assert leaks == []

    data = json.loads((dist / "architecture.data.json").read_text(encoding="utf-8"))
    assert [layer["name"] for layer in data["layers"]] == list(_LAYERS)
