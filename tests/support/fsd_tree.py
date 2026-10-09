"""A synthetic Feature-Sliced Design frontend, with three planted violations (BDL-080 S3c).

The tree ``init``'s FSD preset is measured on: six layers under ``src/`` with slices and
segments, an ``index.ts`` per slice, ``app`` and ``shared`` holding segments, two legacy
folders beside the layers (``components``, ``hooks``), a tsconfig ``@/*`` path, a Vite
alias ``@features`` no tsconfig carries, and a ``.vue`` single-file component.

Planted, each to be found by the rule that names it:

- **a deep import** past a slice's public API: ``widgets/header/ui/Header.ts`` imports
  ``@/features/auth/model/session`` (``slice_public_api``);
- **a cross-import inside a layer**: ``features/cart/model/cart.ts`` imports
  ``@features/auth`` (the ``layers`` rule, through the Vite alias);
- **a folder that is no segment**: ``features/cart/helpers/`` (``slice_shape``).

Synthetic names only (CONTEXT: no owner project name in a committed artifact).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

FSD_TREE: dict[str, str] = {
    "package.json": (
        "{\n"
        '  "name": "orchard-web",\n'
        '  "private": true,\n'
        '  "scripts": {"dev": "vite"},\n'
        '  "dependencies": {"vue": "3.5.0"},\n'
        '  "devDependencies": {"vite": "6.0.0", "typescript": "5.6.0"}\n'
        "}\n"
    ),
    "tsconfig.json": (
        "{\n"
        "  // the app's paths\n"
        '  "compilerOptions": {"baseUrl": ".", "paths": {"@/*": ["src/*"]}},\n'
        "}\n"
    ),
    "vite.config.ts": (
        "import { defineConfig } from 'vite'\n"
        "export default defineConfig({\n"
        "  resolve: { alias: { '@features': './src/features' } },\n"
        "})\n"
    ),
    "src/main.ts": (
        "import { createApp } from 'vue'\nimport { mountApp } from './app'\nmountApp(createApp)\n"
    ),
    "src/app/index.ts": (
        "export { router } from './providers/router'\n"
        "export function mountApp(f: unknown) { return f }\n"
    ),
    "src/app/providers/router.ts": (
        "import { HomePage } from '@/pages/home'\n"
        "import { ProfilePage } from '@/pages/profile'\n"
        "export const router = [HomePage, ProfilePage]\n"
    ),
    "src/app/styles/theme.ts": ("export const theme = { dark: false }\n"),
    "src/pages/home/index.ts": ("export { default as HomePage } from './ui/HomePage.vue'\n"),
    "src/pages/home/ui/HomePage.vue": (
        '<script setup lang="ts">\n'
        "import { Header } from '@/widgets/header'\n"
        "import { LoginForm } from '@/features/auth'\n"
        "</script>\n"
        "<template><Header /><LoginForm /></template>\n"
    ),
    "src/pages/profile/index.ts": ("export { ProfilePage } from './ui/ProfilePage'\n"),
    "src/pages/profile/ui/ProfilePage.ts": (
        "import { userName } from '@/entities/user'\n"
        "export function ProfilePage() { return userName() }\n"
    ),
    "src/widgets/header/index.ts": ("export { Header } from './ui/Header'\n"),
    # PLANTED: a deep import past features/auth's index (public API sidestep).
    "src/widgets/header/ui/Header.ts": (
        "import { currentSession } from '@/features/auth/model/session'\n"
        "import { userName } from '@/entities/user'\n"
        "export function Header() { return [currentSession(), userName()] }\n"
    ),
    "src/features/auth/index.ts": (
        "export { LoginForm } from './ui/LoginForm'\n"
        "export { currentSession } from './model/session'\n"
    ),
    "src/features/auth/ui/LoginForm.ts": (
        "import { currentSession } from '../model/session'\n"
        "import { Button } from '@/shared/ui'\n"
        "export function LoginForm() { return [Button(), currentSession()] }\n"
    ),
    "src/features/auth/model/session.ts": (
        "import { userName } from '@/entities/user'\n"
        "import { client } from '@/shared/api'\n"
        "export function currentSession() { return [userName(), client] }\n"
    ),
    "src/features/cart/index.ts": ("export { addToCart } from './model/cart'\n"),
    # PLANTED: a cross-import inside the features layer, through the Vite alias.
    "src/features/cart/model/cart.ts": (
        "import { currentSession } from '@features/auth'\n"
        "import { formatPrice } from '../helpers/format'\n"
        "import { productTitle } from '@/entities/product'\n"
        "export function addToCart() {\n"
        "  return [currentSession(), formatPrice(1), productTitle()]\n"
        "}\n"
    ),
    # PLANTED: `helpers/` is not one of FSD's standard segments.
    "src/features/cart/helpers/format.ts": (
        "export function formatPrice(n: number) { return `${n}` }\n"
    ),
    "src/entities/user/index.ts": ("export { userName } from './model/user'\n"),
    "src/entities/user/model/user.ts": (
        "import { capitalise } from '@/shared/lib'\n"
        "export function userName() { return capitalise('ann') }\n"
    ),
    "src/entities/product/index.ts": ("export { productTitle } from './model/product'\n"),
    "src/entities/product/model/product.ts": (
        "import { capitalise } from '@/shared/lib'\n"
        "export function productTitle() { return capitalise('pear') }\n"
    ),
    "src/shared/api/index.ts": ("export const client = { get: (u: string) => u }\n"),
    "src/shared/lib/index.ts": (
        "export function capitalise(s: string) { return s.toUpperCase() }\n"
    ),
    "src/shared/ui/index.ts": ("export { Button } from './button'\n"),
    "src/shared/ui/button.ts": (
        "import { capitalise } from '../lib'\n"
        "export function Button() { return capitalise('ok') }\n"
    ),
    # Legacy folders beside the layers, from before the project moved to FSD.
    "src/components/LegacyButton.ts": (
        "import { Button } from '@/shared/ui'\n"
        "export function LegacyButton() { return Button() }\n"
    ),
    "src/hooks/useCart.ts": (
        "import { addToCart } from '@/features/cart'\n"
        "export function useCart() { return addToCart() }\n"
    ),
}


#: The planted violations, as ``(rule, importer or slice)``.
PLANTED = (
    ("fsd-public-api", "src/widgets/header/ui/Header.ts"),
    ("fsd-layers", "features-cart -> features-auth"),
    ("fsd-slice-shape", "features-cart"),
)


def write_fsd_tree(root: Path) -> Path:
    """Write :data:`FSD_TREE` under *root* and return *root*."""
    for rel_path, text in FSD_TREE.items():
        path = root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root
