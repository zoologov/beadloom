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

import base64
import html
import json
import re
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


#: A README that opens with a relative link, as most do. ``init`` takes the root
#: service's summary from this paragraph (BDL-076, ``beadloom-ujzb.11``).
_LINKED_README = "# Acme Orders\n\nSee [license](LICENSE).\n"

#: A document that links out of ``docs/``, to the README and to a module.
_LINKED_GUIDE = (
    "# Guide\n\nStart from [the readme](../README.md) and [the handler](../src/api/handler.js).\n"
)


def test_a_readme_that_opens_with_a_relative_link_builds(tmp_path: Path, npm: str) -> None:
    """The root service's page, built from a README's first paragraph, has no dead link.

    B1 measured the failure on this fixture: the summary ``See [license](LICENSE).``
    was written onto ``services/<root>.md`` as it was, VitePress reported the
    dead link ``./LICENSE`` and the build exited 1. The project declares no
    repository, so the link becomes its text.
    """
    root = tmp_path / "acme-orders"
    _write_project(root)
    (root / "README.md").write_text(_LINKED_README, encoding="utf-8")
    (root / "LICENSE").write_text("MIT\n", encoding="utf-8")
    (root / "docs").mkdir()
    (root / "docs" / "guide.md").write_text(_LINKED_GUIDE, encoding="utf-8")
    _beadloom("init", "--yes", "--project", str(root))
    _beadloom("reindex", "--project", str(root))
    _beadloom("docs", "site", "--project", str(root))

    site = root / "site"
    for command in ([npm, "ci", "--no-audit", "--no-fund"], [npm, "run", "docs:build"]):
        built = subprocess.run(command, cwd=site, capture_output=True, encoding="utf-8")  # noqa: S603
        assert built.returncode == 0, built.stdout + built.stderr

    # ``init`` names the root service after the project directory.
    service = site / ".vitepress" / "dist" / "services" / f"{root.name}.html"
    assert "See license." in service.read_text(encoding="utf-8")


#: A Helm value, as a chart's README and its docs write it (BDL-076, ``beadloom-ujzb.12``).
_HELM = "{{ .Values.image.tag }}"

#: A one-pixel PNG, the logo the README and the guide show.
_LOGO = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)

_HELM_README = (
    "# Acme Orders\n\n"
    f"Deploys the image {_HELM}; set `{_HELM}` in values.yaml.\n\n"
    '<p align="center"><img src="docs/logo.png" alt="Acme logo"></p>\n'
)

_HELM_GUIDE = (
    "# Guide\n\n"
    f"Pin {_HELM} before you upgrade, and keep `{_HELM}` in step.\n\n"
    '<img src="./logo.png" alt="Guide logo">\n\n'
    "Returns List<String> items.\n"
)


def test_project_text_with_a_helm_value_and_a_relative_image_builds_as_written(
    tmp_path: Path, npm: str
) -> None:
    """VitePress compiled the README and the guide as Vue templates and the build failed.

    Measured on this fixture before the fix: ``{{ .Values.image.tag }}`` in prose
    or inline code is not an expression Vue can parse, and ``List<String>`` is an
    element with no end tag. Now the build passes, the Helm value reads as written
    on the About page, the root service's page and the guide, and both images show:
    the README's reaches the copy of ``docs/logo.png`` the portal publishes.
    """
    root = tmp_path / "acme-orders"
    _write_project(root)
    (root / "README.md").write_text(_HELM_README, encoding="utf-8")
    (root / "docs").mkdir()
    (root / "docs" / "guide.md").write_text(_HELM_GUIDE, encoding="utf-8")
    (root / "docs" / "logo.png").write_bytes(_LOGO)
    _beadloom("init", "--yes", "--project", str(root))
    _beadloom("reindex", "--project", str(root))
    _beadloom("docs", "site", "--project", str(root))

    site = root / "site"
    for command in ([npm, "ci", "--no-audit", "--no-fund"], [npm, "run", "docs:build"]):
        built = subprocess.run(command, cwd=site, capture_output=True, encoding="utf-8")  # noqa: S603
        assert built.returncode == 0, built.stdout + built.stderr

    dist = site / ".vitepress" / "dist"
    about = (dist / "index.html").read_text(encoding="utf-8")
    guide = (dist / "docs" / "guide.html").read_text(encoding="utf-8")
    service = (dist / "services" / f"{root.name}.html").read_text(encoding="utf-8")
    for page in (about, guide, service):
        assert page.count(_HELM) >= 2, page
    assert "List&lt;String&gt; items" in guide
    # The root service's summary is the README's first paragraph, which holds no image.
    for page, alt in ((about, "Acme logo"), (guide, "Guide logo")):
        assert re.search(rf'<img src="(data:image/png|/assets/)[^"]*" alt="{alt}"', page), page


#: R2's findings F1, F3 and F4 (BDL-076, ``beadloom-ujzb.21``), each of which failed
#: ``vitepress build`` or left a live Vue binding: a link whose text is code, and
#: text the hand-written reader read differently from VitePress's markdown-it.
_ADVERSARIAL_README = (
    "# Acme Orders\n\n"
    "See [`LICENSE`](LICENSE), [`the guide`][g] and ![`logo`](docs/missing.png).\n\n"
    "[g]: docs/missing.md\n"
)
_ADVERSARIAL_DOC = """---
title: Adversarial {{ .Values.a }}
---

# Adversarial

Intro.

    ```
    image: {{ .Values.b }}
    ```

A paragraph line
    ```
still {{ .Values.c }} prose

- item

      ```yaml
      tag: {{ .Values.d }}
      ```

- item:

      helm install {{ .Values.e }}

* a

  para

        {{ .Values.f }}

> Note:
>
>     helm install {{ .Values.g }}

- item
  ```
  code {{ .Values.h }}
- next item {{ .Values.i }}

Use `a`{{ .Values.j }}`c` here.

| a | b |
|---|---|
| `x|{{ .Values.k }}` | <T> |

*a {{ .Values.l* }}

<details>
<summary>Map<String, Integer> config</summary>

Body.

</details>

<div>
Map<K,V> and {{ .Values.m }}
</div>

<div @click="go">clicked</div>

Text.

<!-- todo: finish

More {{ .Values.n }}.
"""
#: How each case must read on the built page, as text a reader sees.
_AS_WRITTEN = (
    "image: {{ .Values.b }}",
    "still {{ .Values.c }} prose",
    "tag: {{ .Values.d }}",
    "helm install {{ .Values.e }}",
    "{{ .Values.f }}",
    "helm install {{ .Values.g }}",
    "code {{ .Values.h }}",
    "next item {{ .Values.i }}",
    "a{{ .Values.j }}c",
    "{{ .Values.k }}",
    "a {{ .Values.l }}",  # the asterisks are an emphasis around "a {{ .Values.l"
    "Map<String, Integer> config",
    "Map<K,V> and {{ .Values.m }}",
    "clicked",
    "<!-- todo: finish",
    "More {{ .Values.n }}.",
)


def _shown_text(page: str) -> str:
    """The text a reader sees on *page*: the body's markup removed, entities decoded."""
    body = page.split("<body", 1)[1]
    body = re.sub(r"<script\b.*?</script>", "", body, flags=re.DOTALL)
    return html.unescape(re.sub(r"<[^>]+>", "", body))


def test_project_text_markdown_it_reads_differently_builds_and_reads_as_written(
    tmp_path: Path, npm: str
) -> None:
    """Every R2 case in one README and one document: the build passes, the text reads as written.

    On the code before ``beadloom-ujzb.21`` the README failed with a dead link
    (``./LICENSE``) and the document with "Error parsing JavaScript expression"
    and "Element is missing end tag".
    """
    root = tmp_path / "acme-orders"
    _write_project(root)
    (root / "README.md").write_text(_ADVERSARIAL_README, encoding="utf-8")
    (root / "LICENSE").write_text("MIT\n", encoding="utf-8")
    (root / "docs").mkdir()
    (root / "docs" / "adversarial.md").write_text(_ADVERSARIAL_DOC, encoding="utf-8")
    _beadloom("init", "--yes", "--project", str(root))
    _beadloom("reindex", "--project", str(root))
    _beadloom("docs", "site", "--project", str(root))

    site = root / "site"
    for command in ([npm, "ci", "--no-audit", "--no-fund"], [npm, "run", "docs:build"]):
        built = subprocess.run(command, cwd=site, capture_output=True, encoding="utf-8")  # noqa: S603
        assert built.returncode == 0, built.stdout + built.stderr

    dist = site / ".vitepress" / "dist"
    about = _shown_text((dist / "index.html").read_text(encoding="utf-8"))
    assert "See LICENSE, the guide and logo." in about, about
    page = (dist / "docs" / "adversarial.html").read_text(encoding="utf-8")
    shown = _shown_text(page)
    missing = [text for text in _AS_WRITTEN if text not in shown]
    assert missing == [], shown
    # The front matter stayed front matter: it titles the page and is not shown.
    assert "<title>Adversarial {{ .Values.a }}" in page
    assert "title: Adversarial" not in shown
    assert "@click" not in page
