"""``site.forges``: the forge that serves each self-hosted host, read and refused by name.

BDL-076 B4 (``beadloom-ujzb.8``). The block maps a host to a forge kind, or to a
URL template for a forge no kind describes::

    site:
      repo_url: https://git.acme.example/platform/shop
      forges:
        git.acme.example: gitlab
        code.acme.example:
          source: "{url}/browse/{path}?at={ref}"
          raw: "{url}/raw/{path}?at={ref}"

A value the generator cannot use is refused where it was written, like every
other key of the block, and reaches ``docs site``, ``config-check`` and the Gate.
A project that writes no ``forges:`` reads exactly as before.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

import pytest

from beadloom.application.site.forge_routes import KNOWN_FORGES
from beadloom.application.site.site_config import (
    SiteConfig,
    SiteConfigError,
    read_site_config,
    render_site_module,
    site_config_of,
)

if TYPE_CHECKING:
    from pathlib import Path


def _project(tmp_path: Path, config: str) -> Path:
    root = tmp_path / "shop"
    (root / ".beadloom").mkdir(parents=True)
    (root / ".beadloom" / "config.yml").write_text(config, encoding="utf-8")
    return root


def test_a_host_declared_as_a_kind_is_that_forge(tmp_path: Path) -> None:
    root = _project(tmp_path, "site:\n  forges:\n    Git.Acme.Example: gitlab\n")

    config, refusals = read_site_config(root)

    assert refusals == ()
    assert dict(config.forges) == {"git.acme.example": KNOWN_FORGES["gitlab"]}


def test_a_host_declared_by_template_is_read(tmp_path: Path) -> None:
    root = _project(
        tmp_path,
        "site:\n  forges:\n    code.acme.example:\n"
        "      source: '{url}/browse/{path}?at={ref}'\n"
        "      raw: '{url}/raw/{path}?at={ref}'\n",
    )

    config, refusals = read_site_config(root)

    assert refusals == ()
    forge = config.forges["code.acme.example"]
    assert forge.tree == forge.blob == "{url}/browse/{path}?at={ref}"
    assert forge.raw == "{url}/raw/{path}?at={ref}"


def test_a_project_without_the_setting_declares_no_forge(tmp_path: Path) -> None:
    root = _project(tmp_path, "site:\n  title: Shop\n")

    config, refusals = read_site_config(root)

    assert refusals == ()
    assert dict(config.forges) == {}


@pytest.mark.parametrize(
    ("block", "where", "said"),
    [
        ("forges: gitlab\n", "site.forges", "not a mapping"),
        (
            "forges:\n    git.acme.example: gitlab-ce\n",
            "site.forges[git.acme.example]",
            "gitlab-ce",
        ),
        (
            "forges:\n    git.acme.example:\n      source: '{url}/-/tree/{branch}/{path}'\n",
            "site.forges[git.acme.example]",
            "{branch}",
        ),
        (
            "forges:\n    git.acme.example:\n      source: '{url}/-/tree/{ref}'\n",
            "site.forges[git.acme.example]",
            "{path}",
        ),
        (
            "forges:\n    'https://git.acme.example': gitlab\n",
            "site.forges[https://git.acme.example]",
            "host name",
        ),
        (
            "forges:\n    'git.acme.example:8443': gitlab\n",
            "site.forges[git.acme.example:8443]",
            "host name",
        ),
        (
            "forges:\n    'git.acme.example/gitlab': gitlab\n",
            "site.forges[git.acme.example/gitlab]",
            "host name",
        ),
        ("forges:\n    42: gitlab\n", "site.forges[42]", "host name"),
    ],
    ids=[
        "not-a-mapping",
        "unknown-kind",
        "unknown-placeholder",
        "no-path",
        "host-with-scheme",
        "host-with-port",
        "host-with-path",
        "host-a-number",
    ],
)
def test_a_forge_setting_the_generator_cannot_use_is_refused_where_it_was_written(
    tmp_path: Path, block: str, where: str, said: str
) -> None:
    root = _project(tmp_path, "site:\n  " + block)

    _, refusals = read_site_config(root)

    assert [refusal.where for refusal in refusals] == [where]
    assert said in refusals[0].why
    assert refusals[0].remediation


def test_every_unusable_host_is_refused_and_the_usable_ones_are_kept(tmp_path: Path) -> None:
    root = _project(
        tmp_path,
        "site:\n  forges:\n    a.example: gitlab\n    b.example: gitlab-ce\n"
        "    c.example: forgejo\n",
    )

    config, refusals = read_site_config(root)

    assert [refusal.where for refusal in refusals] == [
        "site.forges[b.example]",
        "site.forges[c.example]",
    ]
    assert list(config.forges) == ["a.example"]


def test_the_generator_refuses_an_unknown_kind_before_it_writes(tmp_path: Path) -> None:
    root = _project(tmp_path, "site:\n  forges:\n    git.acme.example: gitlab-ce\n")

    with pytest.raises(SiteConfigError) as caught:
        site_config_of(root)

    assert "site.forges[git.acme.example]" in str(caught.value)


def test_the_unknown_key_refusal_names_forges_among_the_keys(tmp_path: Path) -> None:
    root = _project(tmp_path, "site:\n  forge: gitlab\n")

    _, refusals = read_site_config(root)

    assert "`forges:`" in refusals[0].why


def _icon(config: SiteConfig) -> object:
    match = re.search(r"export const site = (\{.*\});", render_site_module(config))
    assert match is not None
    return json.loads(match.group(1))["repoIcon"]


def test_the_repository_icon_follows_the_declared_kind() -> None:
    url = "https://git.acme.example/platform/shop"
    declared = SiteConfig(
        title="t",
        description="d",
        base="/",
        repo_url=url,
        forges={"git.acme.example": KNOWN_FORGES["gitlab"]},
    )
    undeclared = SiteConfig(title="t", description="d", base="/", repo_url=url)

    assert _icon(declared) == "gitlab"
    assert _icon(undeclared) == "git"
