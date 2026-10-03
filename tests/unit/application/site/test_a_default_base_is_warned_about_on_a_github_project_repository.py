"""A base that cannot match the project's GitHub Pages path is named before CI does.

BDL-076 ``beadloom-ujzb.13``. GitHub serves a project repository's Pages site
under ``/<repo>/`` and a user or organisation repository (``<owner>.github.io``)
at ``/``. ``docs site`` reads the ``origin`` remote only to say, on stderr, that
the default base ``/`` will load none of the portal's assets under ``/<repo>/``.
"""

from __future__ import annotations

import pytest

from beadloom.application.site.pages_base import base_warning, project_pages_base


class TestTheProjectPagesPathOfARemote:
    @pytest.mark.parametrize(
        ("remote", "path"),
        [
            ("git@github.com:acme/orders.git", "/orders/"),
            ("https://github.com/acme/orders", "/orders/"),
            ("https://github.com/acme/orders.git", "/orders/"),
            ("ssh://git@github.com/acme/orders.git", "/orders/"),
            ("https://user:secret@github.com/acme/orders.git", "/orders/"),
            ("https://GitHub.com/Acme/Orders.git\n", "/Orders/"),
        ],
    )
    def test_a_github_project_repository_is_served_under_its_name(
        self, remote: str, path: str
    ) -> None:
        assert project_pages_base(remote) == path

    @pytest.mark.parametrize(
        "remote",
        [
            "",
            "https://github.com/acme/acme.github.io",
            "git@github.com:Acme/ACME.GitHub.io.git",
            "git@gitlab.com:acme/orders.git",
            "https://github.example.com/acme/orders.git",
            "https://codeberg.org/acme/orders",
            "https://github.com/acme",
            "https://github.com/acme/orders/extra",
            "/srv/git/orders.git",
            "file:///srv/git/orders.git",
            "git@[::1]:acme/orders.git",
        ],
    )
    def test_anything_else_names_no_project_pages_path(self, remote: str) -> None:
        assert project_pages_base(remote) is None


class TestTheWarning:
    def test_the_default_base_on_a_project_repository_is_warned_about_with_the_fix(
        self,
    ) -> None:
        warning = base_warning("/", "git@github.com:acme/orders.git")
        assert warning is not None
        assert "site.base: /orders/" in warning
        assert ".beadloom/config.yml" in warning

    def test_the_warning_carries_nothing_of_the_remote_but_the_repository_name(
        self,
    ) -> None:
        warning = base_warning("/", "https://user:secret@github.com/acme/orders.git")
        assert warning is not None
        assert "secret" not in warning
        assert "user:" not in warning
        assert "acme" not in warning

    @pytest.mark.parametrize("base", ["/orders/", "/portal/"])
    def test_a_declared_base_is_not_second_guessed(self, base: str) -> None:
        assert base_warning(base, "git@github.com:acme/orders.git") is None

    @pytest.mark.parametrize(
        "remote", ["", "https://github.com/acme/acme.github.io", "git@gitlab.com:acme/orders"]
    )
    def test_no_project_pages_path_no_warning(self, remote: str) -> None:
        assert base_warning("/", remote) is None
