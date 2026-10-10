"""Expo Router's routes folder is found by the dependency that makes it one (BDL-080 S3e).

Expo Router reads the files under ``app/`` at the project root as the app's screens. What
makes the folder a routes folder is the router: ``expo-router`` among the ``dependencies``
of ``package.json``. A ``_layout`` file is optional to the router, so a routes folder
holding only ``index.tsx`` is still one, and an ``app/`` folder in a project that does not
depend on the router is ordinary code.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.onboarding.scanner.expo_router import expo_router_routes

if TYPE_CHECKING:
    from pathlib import Path

_DEPENDS_ON_THE_ROUTER = '{"dependencies": {"expo": "52.0.0", "expo-router": "4.0.9"}}'


def _write(root: Path, files: dict[str, str]) -> None:
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def test_the_routes_folder_of_a_project_that_depends_on_the_router(tmp_path: Path) -> None:
    _write(
        tmp_path,
        {"package.json": _DEPENDS_ON_THE_ROUTER, "app/index.tsx": "export default 1\n"},
    )

    assert expo_router_routes(tmp_path) == "app"


def test_a_layout_file_without_the_dependency_is_no_routes_folder(tmp_path: Path) -> None:
    _write(
        tmp_path,
        {
            "package.json": '{"dependencies": {"react": "18.3.1"}}',
            "app/_layout.tsx": "export default 1\n",
        },
    )

    assert expo_router_routes(tmp_path) is None


def test_the_router_as_a_dev_dependency_only_is_not_read(tmp_path: Path) -> None:
    _write(
        tmp_path,
        {
            "package.json": '{"devDependencies": {"expo-router": "4.0.9"}}',
            "app/index.tsx": "export default 1\n",
        },
    )

    assert expo_router_routes(tmp_path) is None


def test_the_dependency_without_an_app_folder_names_no_routes(tmp_path: Path) -> None:
    _write(tmp_path, {"package.json": _DEPENDS_ON_THE_ROUTER, "src/app/index.ts": "x\n"})

    assert expo_router_routes(tmp_path) is None


def test_a_package_json_that_is_not_json_names_no_routes(tmp_path: Path) -> None:
    _write(tmp_path, {"package.json": "{not json", "app/index.tsx": "export default 1\n"})

    assert expo_router_routes(tmp_path) is None


def test_a_project_with_no_package_json_names_no_routes(tmp_path: Path) -> None:
    _write(tmp_path, {"app/index.tsx": "export default 1\n"})

    assert expo_router_routes(tmp_path) is None
