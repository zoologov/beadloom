"""Step implementations for `an_aliased_or_platform_import_names_its_file.feature`.

BDL-080 S3a (`beadloom-cwzc`). Nothing is stubbed: the real `reindex` and
`incremental_reindex` run over projects on disk. The two fixtures are shaped like a Vue 3
+ TypeScript Feature-Sliced app and an Expo-like React Native app, and neither is this
repository nor any project of the owner's: their names and files are invented.

The shared When/Then steps, and the comparison with a fresh index, are in this folder's
`conftest.py`. The module is named `test_*` so default pytest collection picks the
scenarios up.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, parsers, scenarios, when

from beadloom.application.reindex import incremental_reindex

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    WriteProject = Callable[[Path, str, str, dict[str, str]], None]

pytest.importorskip("tree_sitter_typescript")

scenarios("../../../graph/import-resolver/an_aliased_or_platform_import_names_its_file.feature")


def _graph(service: str, nodes: dict[str, str]) -> str:
    """A root service and one component per source folder, each ``part_of`` the root."""
    lines = [
        "nodes:",
        f"  - ref_id: {service}",
        "    kind: service",
        f"    summary: The {service} app.",
        '    source: ""',
    ]
    for ref_id, source in nodes.items():
        lines += [
            f"  - ref_id: {ref_id}",
            "    kind: component",
            f"    summary: The {ref_id} slice.",
            f"    source: {source}/",
        ]
    lines.append("edges:")
    for ref_id in nodes:
        lines += [f"  - src: {ref_id}", f"    dst: {service}", "    kind: part_of"]
    return "\n".join(lines) + "\n"


def _tsconfig_app(target: str) -> str:
    """The app's tsconfig as `create-vue` writes it: comments, trailing commas, an extends."""
    return (
        "{\n"
        "  // the app: everything under src\n"
        '  "extends": "@vue/tsconfig/tsconfig.dom.json",\n'
        '  "include": ["src/**/*", "src/**/*.vue"],\n'
        '  "compilerOptions": {\n'
        "    /* one alias, as the template declares it */\n"
        '    "baseUrl": ".",\n'
        f'    "paths": {{ "@/*": ["{target}"], }},\n'
        "  },\n"
        "}\n"
    )


_STOREFRONT_NODES = {
    "app": "src/app",
    "header": "src/widgets/header",
    "cart": "src/features/cart",
    "config": "src/shared/config",
    "legacy-cart": "lib/features/cart",
}

_STOREFRONT: dict[str, str] = {
    "tsconfig.json": (
        '{ "files": [], "references": [{ "path": "./tsconfig.node.json" },'
        ' { "path": "./tsconfig.app.json" }] }\n'
    ),
    "tsconfig.node.json": '{ "include": ["vite.config.*"] }\n',
    "tsconfig.app.json": _tsconfig_app("./src/*"),
    "src/app/main.ts": (
        "import { createApp } from 'vue'\n"
        "import { tokens } from 'src/shared/config/tokens'\n"
        "createApp(tokens)\n"
    ),
    "src/widgets/header/ui/Header.vue": (
        "<template><header /></template>\n"
        '<script setup lang="ts">\n'
        "import { useCart } from '@/features/cart'\n"
        "</script>\n"
    ),
    "src/features/cart/index.ts": "export function useCart() { return 1 }\n",
    "src/shared/config/tokens.ts": "export const tokens = {}\n",
    "lib/features/cart/index.ts": "export function useCart() { return 0 }\n",
}

_STOREFRONT_CONFIG = "scan_paths:\n- src\n- lib\nlanguages:\n- .ts\n- .vue\n"

_TRAILMATE_NODES = {
    "screens": "app",
    "components": "components",
    "ui": "src/shared/ui",
    "lib": "src/shared/lib",
    "api": "src/shared/api",
    "env": "src/shared/config",
    "profile": "src/entities/profile",
    "auth": "src/features/auth",
    "legacy-api": "legacy/shared/api",
}

_TRAILMATE: dict[str, str] = {
    "tsconfig.json": (
        '{ "extends": "expo/tsconfig.base",'
        ' "compilerOptions": { "strict": true, "paths": { "@/*": ["./*"] } } }\n'
    ),
    "app/index.tsx": (
        "import { ThemedText } from '@/components/ThemedText';\n"
        "export default function Home() { return ThemedText; }\n"
    ),
    "app/settings.tsx": (
        "import { useAuth } from '~/features/auth';\n"
        "export default function Settings() { return useAuth; }\n"
    ),
    "components/ThemedText.tsx": (
        "import { Text } from 'react-native';\nexport function ThemedText() { return Text; }\n"
    ),
    "src/shared/ui/Button/index.ts": "export { Button } from './Button';\n",
    "src/shared/ui/Button/Button.ios.tsx": "export function Button() { return 1; }\n",
    "src/shared/ui/Button/Button.android.tsx": "export function Button() { return 2; }\n",
    "src/shared/lib/haptics.native.ts": "export function haptic() { return 1; }\n",
    "src/shared/lib/haptics.web.ts": "export function haptic() { return 0; }\n",
    "src/shared/api/index.ts": "export const api = {};\n",
    "src/shared/api/client.ts": (
        "import { gone } from '@shared/missing';\nexport const client = gone;\n"
    ),
    "src/shared/config/env.mjs": (
        "import { haptic } from '@shared/lib/haptics';\nexport const API_URL = haptic();\n"
    ),
    "src/entities/profile/model/profile.ts": (
        "import { api } from '@shared/api';\nexport const profile = api;\n"
    ),
    "src/entities/profile/ui/ProfileCard.tsx": (
        "import { haptic } from '../../../shared/lib/haptics';\n"
        "export function ProfileCard() { return haptic(); }\n"
    ),
    "src/features/auth/index.ts": "export function useAuth() { return 1; }\n",
    "legacy/shared/api/index.ts": "export const api = 0;\n",
}


def _trailmate_config(shared: str) -> str:
    return (
        "scan_paths:\n- app\n- components\n- src\n- legacy\n"
        "languages:\n- .ts\n- .tsx\n- .js\n"
        "imports:\n"
        "  aliases:\n"
        f'    "@shared": {shared}\n'
        '    "~": src\n'
    )


@given(parsers.parse('a Vue app whose tsconfig.app.json maps "@/*" to "./src/*"'))
def _storefront(tmp_path: Path, state: dict[str, Any], write_project: WriteProject) -> None:
    root = tmp_path / "storefront"
    write_project(root, _graph("storefront", _STOREFRONT_NODES), _STOREFRONT_CONFIG, _STOREFRONT)
    state["root"] = root


@given("an Expo-like app whose Babel aliases are declared under imports.aliases")
def _trailmate(tmp_path: Path, state: dict[str, Any], write_project: WriteProject) -> None:
    root = tmp_path / "trailmate"
    write_project(
        root, _graph("trailmate", _TRAILMATE_NODES), _trailmate_config("src/shared"), _TRAILMATE
    )
    state["root"] = root


@when(
    parsers.parse(
        'tsconfig.app.json is rewritten to map "@/*" to "./lib/*" and the index is updated'
    )
)
def _tsconfig_rewritten(state: dict[str, Any]) -> None:
    (state["root"] / "tsconfig.app.json").write_text(_tsconfig_app("./lib/*"), encoding="utf-8")
    incremental_reindex(state["root"])


@when(parsers.parse('the "@shared" alias is pointed at "legacy/shared" and the index is updated'))
def _alias_repointed(state: dict[str, Any]) -> None:
    config = state["root"] / ".beadloom" / "config.yml"
    config.write_text(_trailmate_config("legacy/shared"), encoding="utf-8")
    incremental_reindex(state["root"])
