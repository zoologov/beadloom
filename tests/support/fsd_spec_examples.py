"""The specification's group and pages-first examples as trees on disk (BDL-082 S2a).

feature-sliced.design, ``/docs/reference/slices-segments`` (*Slice groups*): "Closely
related slices can be structurally grouped in a folder, but they should exercise the same
isolation rules as other slices — there should be no code sharing in that folder." The
group tree is the axes' probe ``p2-groups``: ``features/auth`` holds ``login`` and
``register``, ``register`` imports ``login`` (the sharing the passage forbids), and a page
imports both through their indexes.

``/docs/reference/layers`` (*Pages*): "There's no limit to how much code you can place in
a page slice as long as your team still finds it easy to navigate." The pages-first tree
is the probe ``p3-pagesfirst``: one page of 90 functions, and, when asked for, one feature
of 90 functions beside it.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

#: What ``init`` reads as a frontend, and the alias the imports below are written in.
PACKAGE = json.dumps({"name": "probe", "private": True, "dependencies": {"vue": "3.5.0"}})
TSCONFIG = json.dumps({"compilerOptions": {"baseUrl": ".", "paths": {"@/*": ["src/*"]}}})

#: The symbols one slice of the pages-first tree owns: past the 60 the other layers keep.
LARGE_SLICE_SYMBOLS = 90

GROUP: Mapping[str, str] = {
    "src/app/index.ts": "export const app = 1\n",
    "src/shared/lib/index.ts": "export const x = 1\n",
    "src/features/auth/login/index.ts": "export { form } from './ui/form'\n",
    "src/features/auth/login/ui/form.ts": "export function form() { return 1 }\n",
    "src/features/auth/register/index.ts": "export { form } from './ui/form'\n",
    "src/features/auth/register/ui/form.ts": (
        "import { form as login } from '@/features/auth/login'\n"
        "export function form() { return login() }\n"
    ),
    "src/pages/home/index.ts": "export { home } from './ui/home'\n",
    "src/pages/home/ui/home.ts": (
        "import { form } from '@/features/auth/login'\n"
        "import { form as register } from '@/features/auth/register'\n"
        "export function home() { return form() + register() }\n"
    ),
}

#: A group inside a group (BDL-082 S2 fix, review S2R minor 3): ``features/account`` holds
#: only the group ``settings``, whose slices ``profile`` and ``billing`` share code the way
#: :data:`GROUP`'s do. Until the fix ``init`` read the whole of ``features/account`` as one
#: slice, so ``billing`` importing ``profile`` was inside one node.
NESTED_GROUP: Mapping[str, str] = {
    "src/app/index.ts": "export const app = 1\n",
    "src/shared/lib/index.ts": "export const x = 1\n",
    "src/features/account/settings/profile/index.ts": "export { card } from './ui/card'\n",
    "src/features/account/settings/profile/ui/card.ts": "export function card() { return 1 }\n",
    "src/features/account/settings/billing/index.ts": "export { plan } from './ui/plan'\n",
    "src/features/account/settings/billing/ui/plan.ts": (
        "import { card } from '@/features/account/settings/profile'\n"
        "export function plan() { return card() }\n"
    ),
    "src/pages/home/index.ts": "export { home } from './ui/home'\n",
    "src/pages/home/ui/home.ts": (
        "import { plan } from '@/features/account/settings/billing'\n"
        "export function home() { return plan() }\n"
    ),
}

#: A slice not yet split into segments (BDL-082 S2 fix 2, re-review of S2R, Major A): code
#: files at the slice's top and a ``components`` folder, one component of which has its own
#: ``index``. ``db75ab46`` read ``checkout`` as a group and wrote one node, for ``Summary``,
#: leaving the other four files in no unit; a folder holding code at its top is a slice.
PRE_MIGRATION_SLICE: Mapping[str, str] = {
    "src/app/index.ts": "export const app = 1\n",
    "src/shared/lib/index.ts": "export const x = 1\n",
    "src/features/checkout/Checkout.vue": (
        "<script setup lang=\"ts\">\nimport { total } from './store'\n</script>\n"
    ),
    "src/features/checkout/store.ts": "export function total() { return 1 }\n",
    "src/features/checkout/store2.ts": "export function count() { return 2 }\n",
    "src/features/checkout/components/Total.vue": "<template><b>1</b></template>\n",
    "src/features/checkout/components/Summary/index.ts": "export const summary = 1\n",
    "src/features/checkout/components/Summary/Summary.vue": "<template><i>1</i></template>\n",
    "src/pages/home/index.ts": "export const home = 1\n",
}

#: The specification's group with one shared file at its top (BDL-082 S2 fix 4, the third
#: review pass's Major B). ``login`` and ``register`` hold ``ui/``, so by the owner's ruling
#: of 2026-10-13 ``auth`` stays a group and ``helpers.ts`` is code at a group's top.
GROUP_WITH_A_SHARED_FILE: Mapping[str, str] = {
    **GROUP,
    "src/features/auth/helpers.ts": "export const helper = 1\n",
}


def _functions(prefix: str, count: int) -> str:
    return "".join(f"export function {prefix}{i}() {{ return {i} }}\n" for i in range(count))


def _large_slice(folder: str, prefix: str) -> dict[str, str]:
    """A slice of :data:`LARGE_SLICE_SYMBOLS` functions over three segments and its index."""
    third = LARGE_SLICE_SYMBOLS // 3
    return {
        f"{folder}/index.ts": "export * from './ui/view'\n",
        f"{folder}/ui/view.ts": _functions(f"{prefix}View", third),
        f"{folder}/api/load.ts": _functions(f"{prefix}Load", third),
        f"{folder}/model/state.ts": _functions(f"{prefix}State", LARGE_SLICE_SYMBOLS - 2 * third),
    }


def pages_first(*, with_large_feature: bool = False) -> dict[str, str]:
    """The pages-first tree: a 90-function page, and a 90-function feature when asked."""
    files = {
        "src/app/index.ts": "export const app = 1\n",
        "src/shared/lib/index.ts": "export const x = 1\n",
        **_large_slice("src/pages/feed", "feed"),
    }
    if with_large_feature:
        files.update(_large_slice("src/features/compose", "compose"))
    return files


def write_example(root: Path, files: Mapping[str, str]) -> Path:
    """Write *files* under *root* beside the package and tsconfig a frontend has."""
    for rel, text in {"package.json": PACKAGE, "tsconfig.json": TSCONFIG, **files}.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root
