"""The portal's identity comes from the project's ``site:`` block, never from this repository.

BDL-076 B1 (``beadloom-dfwt``). Explore built a TypeScript project's portal by
copying this repository's scaffold, and the result carried Beadloom's title, the
``/beadloom/`` base and a link to Beadloom's repository. The title, description,
base path and repository link now come from ``.beadloom/config.yml``'s ``site:``
block, with defaults that name nothing but the project's own directory.

Owner ruling (CONTEXT, 2026-09-30): a project's name comes from configuration and
never from the git remote, and nothing from the remote is published except each
node's ``source_url``. So the repository link has no default: a project that
declares none gets none.

A key the block does not know is refused by name. ``bsae: /shop/`` is a one-letter
typo whose cost is a portal deployed under the wrong path, and a reader of the
refusal has to see which key was not read.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

import pytest

from beadloom.application.site.site_config import (
    SiteConfig,
    SiteConfigError,
    read_site_config,
    render_site_module,
    site_config_of,
)

if TYPE_CHECKING:
    from pathlib import Path


def _project(tmp_path: Path, config: str | None, name: str = "acme-orders") -> Path:
    root = tmp_path / name
    (root / ".beadloom").mkdir(parents=True)
    if config is not None:
        (root / ".beadloom" / "config.yml").write_text(config, encoding="utf-8")
    return root


def _module_value(module: str) -> dict[str, object]:
    match = re.search(r"export const site = (\{.*\});", module)
    assert match is not None, module
    value = json.loads(match.group(1))
    assert isinstance(value, dict)
    return value


def test_a_project_without_a_site_block_gets_its_directory_name_and_the_root_base(
    tmp_path: Path,
) -> None:
    root = _project(tmp_path, "scan_paths: [src]\n")
    config, refusals = read_site_config(root)
    assert refusals == ()
    assert config.title == "acme-orders"
    assert config.base == "/"
    assert config.repo_url == ""
    assert "acme-orders" in config.description


def test_a_project_without_a_config_file_gets_the_same_defaults(tmp_path: Path) -> None:
    root = _project(tmp_path, None, name="ledger")
    config, refusals = read_site_config(root)
    assert refusals == ()
    assert (config.title, config.base, config.repo_url) == ("ledger", "/", "")


def test_a_declared_site_block_is_the_portal_identity(tmp_path: Path) -> None:
    root = _project(
        tmp_path,
        "site:\n"
        "  title: Acme Orders\n"
        "  description: Orders, payments and stock\n"
        "  base: /orders/\n"
        "  repo_url: https://gitlab.com/acme/orders\n",
    )
    config, refusals = read_site_config(root)
    assert refusals == ()
    assert config == SiteConfig(
        title="Acme Orders",
        description="Orders, payments and stock",
        base="/orders/",
        repo_url="https://gitlab.com/acme/orders",
    )


def test_an_unknown_key_is_refused_by_name_with_the_keys_the_block_reads(
    tmp_path: Path,
) -> None:
    root = _project(tmp_path, "site:\n  title: Shop\n  bsae: /shop/\n")
    _, refusals = read_site_config(root)
    assert len(refusals) == 1
    refusal = refusals[0]
    assert refusal.where == "site.bsae"
    assert "`bsae:`" in refusal.why
    for known in ("title", "description", "base", "repo_url"):
        assert f"`{known}:`" in refusal.why


@pytest.mark.parametrize(
    ("block", "where"),
    [
        ("site:\n  base: shop\n", "site.base"),
        ("site:\n  base: /shop\n", "site.base"),
        ("site:\n  title: 42\n", "site.title"),
        ("site:\n  title: ''\n", "site.title"),
        ("site:\n  description: [a, b]\n", "site.description"),
        ("site:\n  repo_url: gitlab.com/acme/orders\n", "site.repo_url"),
        ("site:\n  repo_url: ftp://example.com/acme\n", "site.repo_url"),
        ("site:\n  repo_url: https://user:token@example.com/acme\n", "site.repo_url"),
        ("site:\n  repo_url: https://example.com/acme?private_token=x\n", "site.repo_url"),
        ("site: /shop/\n", "site"),
    ],
    ids=[
        "base-without-slashes",
        "base-without-trailing-slash",
        "title-a-number",
        "title-empty",
        "description-a-list",
        "repo-url-without-scheme",
        "repo-url-not-web",
        "repo-url-with-a-credential",
        "repo-url-with-a-query",
        "block-not-a-mapping",
    ],
)
def test_a_value_the_portal_cannot_use_is_refused_where_it_was_written(
    tmp_path: Path, block: str, where: str
) -> None:
    root = _project(tmp_path, block)
    _, refusals = read_site_config(root)
    assert [refusal.where for refusal in refusals] == [where]
    assert all(refusal.remediation for refusal in refusals)


def test_an_empty_site_block_declares_nothing(tmp_path: Path) -> None:
    root = _project(tmp_path, "site:\n")
    config, refusals = read_site_config(root)
    assert refusals == ()
    assert config.base == "/"


def test_an_unreadable_config_is_refused_rather_than_read_as_defaults(tmp_path: Path) -> None:
    root = _project(tmp_path, "site: [unclosed\n")
    _, refusals = read_site_config(root)
    assert len(refusals) == 1
    assert "config.yml" in refusals[0].why


def test_the_generator_refuses_a_block_it_cannot_use(tmp_path: Path) -> None:
    root = _project(tmp_path, "site:\n  bsae: /shop/\n")
    with pytest.raises(SiteConfigError) as caught:
        site_config_of(root)
    assert [refusal.where for refusal in caught.value.refusals] == ["site.bsae"]
    assert "site.bsae" in str(caught.value)


def test_the_generated_module_carries_the_identity_and_nothing_else(tmp_path: Path) -> None:
    config = SiteConfig(
        title='Acme "Orders"',
        description="Orders",
        base="/orders/",
        repo_url="https://gitlab.com/acme/orders",
    )
    value = _module_value(render_site_module(config, tmp_path))
    assert value == {
        "title": 'Acme "Orders"',
        "description": "Orders",
        "base": "/orders/",
        "repoUrl": "https://gitlab.com/acme/orders",
        "repoIcon": "gitlab",
        "logo": "",
        "logoMonochrome": False,
        "favicons": [
            {"href": "/brand/beadloom-favicon.svg", "type": "image/svg+xml"},
            {"href": "/brand/beadloom-favicon.png", "type": "image/png", "sizes": "32x32"},
            {
                "href": "/brand/beadloom-favicon-dark.png",
                "type": "image/png",
                "sizes": "32x32",
                "media": "(prefers-color-scheme: dark)",
            },
        ],
        "poweredBy": True,
    }


@pytest.mark.parametrize(
    ("url", "icon"),
    [
        ("https://github.com/acme/orders", "github"),
        ("https://gitlab.com/acme/orders", "gitlab"),
        ("https://bitbucket.org/acme/orders", "bitbucket"),
        # Codeberg's own mark, by the owner's ruling of 2026-10-09 (BDL-080 S4d);
        # it was Gitea's, the software Codeberg runs, before.
        ("https://codeberg.org/acme/orders", "codeberg"),
        ("https://dev.azure.com/acme/orders/_git/orders", "azuredevops"),
        ("https://git.acme.example/orders", "git"),
        ("", ""),
    ],
    ids=["github", "gitlab", "bitbucket", "codeberg", "azure", "self-hosted", "none"],
)
def test_the_repository_icon_follows_the_forge_the_link_points_at(
    url: str, icon: str, tmp_path: Path
) -> None:
    config = SiteConfig(title="t", description="d", base="/", repo_url=url)
    assert _module_value(render_site_module(config, tmp_path))["repoIcon"] == icon
