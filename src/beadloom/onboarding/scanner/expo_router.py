"""Expo Router's routes folder, found for ``init`` (BDL-080 S3e).

Expo Router reads the files under ``app/`` at the project root as the app's screens:
``_layout.tsx`` wraps the folder it sits in, ``index.tsx`` is the folder's screen and
``trail/[id].tsx`` a screen with a parameter. FSD's guidance for an Expo app keeps that
folder at the root, beside the layers in ``src/``, and reads it as the top layer; so the
folder is one unit of the ``app`` layer, never a folder of slices (see
:mod:`beadloom.onboarding.scanner.fsd_layout`).

**Found by the dependency, not by a file.** The folder is a routes folder when
``package.json`` names ``expo-router`` among its ``dependencies``, because the router is
what reads it: without the package an ``app/`` folder is ordinary code. A file test such as
``app/_layout.tsx`` would miss real routes folders, since the router makes the root layout
optional, and would read a name other tools are free to use. ``devDependencies`` are not
read: the router runs in the shipped app, so a project that installs it declares it as a
runtime dependency.

Not read: the ``root`` option of the ``expo-router`` config plugin, which moves the folder,
and ``src/app/`` as Expo Router's alternative location, which in an FSD project is the
``app`` layer itself.
"""

# beadloom:domain=onboarding
# beadloom:feature=agent-prime

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.onboarding.scanner.project_facts import _package_json_dependencies

if TYPE_CHECKING:
    from pathlib import Path

#: The package whose presence makes ``app/`` a routes folder.
EXPO_ROUTER_PACKAGE = "expo-router"

#: The folder Expo Router reads its routes from, relative to the project root.
EXPO_ROUTER_ROUTES = "app"


def expo_router_routes(project_root: Path) -> str | None:
    """The project-relative routes folder of *project_root*, or ``None`` when it has none.

    ``app`` when ``package.json`` depends on ``expo-router`` and ``app/`` is a folder at
    the root; ``None`` otherwise, a ``package.json`` that is missing or no JSON included.
    """
    if EXPO_ROUTER_PACKAGE not in _package_json_dependencies(project_root):
        return None
    return EXPO_ROUTER_ROUTES if (project_root / EXPO_ROUTER_ROUTES).is_dir() else None
