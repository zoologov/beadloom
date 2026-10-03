"""A generated module that exists and fails to load stops the portal; only a missing one is empty.

BDL-076 ``beadloom-ujzb.20`` (R2 finding F11). The shipped ``.vitepress/config.mjs``
and ``e2e/playwright.config.js`` read the two modules ``docs site`` generates -
``site.generated.mjs`` (title, base, repository link) and ``config.generated.mjs``
(nav, sidebar) - inside ``catch { return {}; }``. That was meant for the moment
before the first generation, and it swallowed everything: a module that exists
and does not load built a portal with no title, base ``/`` and no nav, and the
browser tests aimed at ``/``, with no message.

Both now read through one shipped reader, ``.vitepress/generated.mjs``, which
returns an empty module only when the FILE is missing, and says so; a syntax
error, a throw, or a missing import inside an existing module reaches the build.
The reader is exercised here through Node over a written portal; the two
configs' use of it is read from the written files, and the slow adopter suite
builds a portal through the real ``config.mjs``.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from typing import TYPE_CHECKING

import pytest

from beadloom.application.site.scaffold import write_scaffold

if TYPE_CHECKING:
    from pathlib import Path

_VERSION = "7.0.0"
_READER = ".vitepress/generated.mjs"
_CONSUMERS = (".vitepress/config.mjs", "e2e/playwright.config.js")

#: Calls the shipped reader on one module next to it and prints what it returned.
_PROBE = """\
import { importGenerated } from "./generated.mjs";
const module = await importGenerated(new URL("./probe.generated.mjs", import.meta.url));
console.log(JSON.stringify({ ...module }));
"""

_NODE = shutil.which("node")
needs_node = pytest.mark.skipif(_NODE is None, reason="node is not on PATH")


@pytest.fixture()
def site(tmp_path: Path) -> Path:
    project = tmp_path / "shop"
    (project / ".beadloom").mkdir(parents=True)
    write_scaffold(project / "site", project_root=project, version=_VERSION)
    (project / "site" / ".vitepress" / "probe.mjs").write_text(_PROBE, encoding="utf-8")
    return project / "site"


def _probe(site: Path, module: str | None) -> subprocess.CompletedProcess[str]:
    if module is not None:
        target = site / ".vitepress" / "probe.generated.mjs"
        target.write_text(module, encoding="utf-8")
    assert _NODE is not None
    return subprocess.run(  # noqa: S603 - the node on PATH, over a file this test wrote
        [_NODE, str(site / ".vitepress" / "probe.mjs")],
        capture_output=True,
        encoding="utf-8",
        check=False,
    )


@needs_node
def test_a_module_that_loads_is_read(site: Path) -> None:
    result = _probe(site, 'export const site = { base: "/orders/" };\n')
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"site": {"base": "/orders/"}}


@needs_node
def test_a_missing_module_is_read_as_empty_and_said(site: Path) -> None:
    result = _probe(site, None)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {}
    assert "probe.generated.mjs" in result.stderr
    assert "beadloom docs site" in result.stderr


@needs_node
@pytest.mark.parametrize(
    ("module", "error"),
    [
        ("export const site = {\n", "SyntaxError"),
        ('throw new Error("the generator wrote half a file");\n', "half a file"),
        ('import "./not-there.mjs";\nexport const site = {};\n', "not-there.mjs"),
    ],
    ids=["syntax-error", "throws", "missing-import"],
)
def test_a_module_that_exists_and_fails_to_load_stops_the_reader(
    site: Path, module: str, error: str
) -> None:
    result = _probe(site, module)
    assert result.returncode != 0, result.stdout
    assert error in result.stderr
    assert result.stdout == ""


@pytest.mark.parametrize("consumer", _CONSUMERS)
def test_each_config_reads_the_generated_modules_through_the_reader(
    site: Path, consumer: str
) -> None:
    text = (site / consumer).read_text(encoding="utf-8")
    assert "importGenerated(" in text
    assert re.search(r"catch\s*(\(\s*\w*\s*\))?\s*\{\s*return", text) is None, consumer
