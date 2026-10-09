"""What an adopter expects ``init`` and the resolver to make of the two FSD fixtures.

BDL-080 S3d (``beadloom-chdx``), RFC D5/D6 and the PRD's answer 2: the viewer shows
only what the import resolver resolves, and Vue and React Native import differently, so
every import form the two frameworks use is listed here with the folder it names, read
from each fixture's code and never taken from the product. The findings the fixtures
plant on purpose and the Expo module's bridge are listed the same way.

Kept apart from :mod:`tests.support.adopter_portals`, which the slow tests import and
the ``site-adopters`` workflow's paths filter names: nothing here is read by a slow test.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

#: The import forms of the RFC's list, by the name a measurement reports them under.
RELATIVE = "relative ./ and ../"
DIRECTORY_INDEX = "a folder through its index"
VUE_SFC = 'inside <script setup lang="ts"> of a .vue file'
VUE_FILE = "a .vue file by its name"
TSX = "from a .tsx file"
JSX = "from a .jsx file"
JS_IN_TS = "JavaScript beside TypeScript (.js)"
MJS_CJS = ".mjs and .cjs"
TSCONFIG_PATHS = "tsconfig paths"
BUNDLER_ALIAS = "a bundler alias (Vite resolve.alias, Babel module-resolver)"
BASE_URL = "tsconfig baseUrl"
PLATFORM_SUFFIX = "a platform suffix (.ios .android .web)"
RE_EXPORT = "a re-export (export ... from)"
DYNAMIC_IMPORT = "a dynamic import()"

#: Every form, in the order a measurement reports them.
FORMS = (
    RELATIVE,
    DIRECTORY_INDEX,
    VUE_SFC,
    VUE_FILE,
    TSX,
    JSX,
    JS_IN_TS,
    MJS_CJS,
    TSCONFIG_PATHS,
    BUNDLER_ALIAS,
    BASE_URL,
    PLATFORM_SUFFIX,
    RE_EXPORT,
    DYNAMIC_IMPORT,
)


@dataclass(frozen=True)
class FormImport:
    """One import of the fixture's code that carries *form*: the file, its specifier and
    the folder of the node the specifier names, as the code's reader resolves it."""

    form: str
    importer: str
    specifier: str
    target: str


@dataclass(frozen=True)
class PlantedFinding:
    """A finding the fixture's code earns on purpose: the rule, its severity, the folders
    of the two nodes it names (``to`` is empty for a finding on one node) and the file it
    points at (empty when it names none)."""

    rule: str
    severity: str
    source: str
    to: str = ""
    file: str = ""


_V = "src"

VUE_FSD_FORMS = (
    FormImport(
        RELATIVE,
        f"{_V}/features/apply-coupon/ui/CouponField.vue",
        "../model/coupon",
        f"{_V}/features/apply-coupon",
    ),
    FormImport(
        RELATIVE,
        f"{_V}/entities/product/model/productStore.ts",
        "../api/productApi",
        f"{_V}/entities/product",
    ),
    FormImport(DIRECTORY_INDEX, f"{_V}/shared/api/http.ts", "../config", f"{_V}/shared/config"),
    FormImport(DIRECTORY_INDEX, f"{_V}/main.ts", "./app", f"{_V}/app"),
    FormImport(
        VUE_SFC,
        f"{_V}/pages/catalog/ui/CatalogPage.vue",
        "@/widgets/product-grid",
        f"{_V}/widgets/product-grid",
    ),
    FormImport(
        VUE_SFC,
        f"{_V}/widgets/site-header/ui/SiteHeader.vue",
        "@/entities/cart",
        f"{_V}/entities/cart",
    ),
    FormImport(
        VUE_FILE, f"{_V}/pages/catalog/index.ts", "./ui/CatalogPage.vue", f"{_V}/pages/catalog"
    ),
    FormImport(VUE_FILE, f"{_V}/shared/ui/index.ts", "./BaseButton.vue", f"{_V}/shared/ui"),
    FormImport(JS_IN_TS, f"{_V}/shared/lib/index.ts", "./slugify.js", f"{_V}/shared/lib"),
    FormImport(
        JS_IN_TS, f"{_V}/stores/wishlist.js", "@/entities/product", f"{_V}/entities/product"
    ),
    FormImport(MJS_CJS, f"{_V}/shared/config/index.ts", "./env.mjs", f"{_V}/shared/config"),
    FormImport(
        TSCONFIG_PATHS,
        f"{_V}/entities/cart/model/cartStore.ts",
        "@/shared/lib",
        f"{_V}/shared/lib",
    ),
    FormImport(
        TSCONFIG_PATHS,
        f"{_V}/features/apply-coupon/model/coupon.ts",
        "@/features/add-to-cart",
        f"{_V}/features/add-to-cart",
    ),
    FormImport(
        BUNDLER_ALIAS,
        f"{_V}/widgets/site-header/ui/SiteHeader.vue",
        "@shared/ui",
        f"{_V}/shared/ui",
    ),
    FormImport(
        BASE_URL,
        f"{_V}/features/add-to-cart/ui/AddToCartButton.vue",
        "src/shared/ui",
        f"{_V}/shared/ui",
    ),
    FormImport(
        RE_EXPORT,
        f"{_V}/features/add-to-cart/index.ts",
        "./model/useAddToCart",
        f"{_V}/features/add-to-cart",
    ),
    FormImport(
        RE_EXPORT, f"{_V}/entities/cart/index.ts", "./model/cartStore", f"{_V}/entities/cart"
    ),
    FormImport(
        DYNAMIC_IMPORT, f"{_V}/app/providers/router.ts", "@/pages/catalog", f"{_V}/pages/catalog"
    ),
    FormImport(
        DYNAMIC_IMPORT, f"{_V}/app/providers/router.ts", "@/pages/checkout", f"{_V}/pages/checkout"
    ),
)

_HAPTICS = "modules/trail-haptics"

RN_FSD_FORMS = (
    FormImport(
        RELATIVE,
        f"{_V}/features/start-hike/ui/StartHikeButton.tsx",
        "../model/hike",
        f"{_V}/features/start-hike",
    ),
    FormImport(
        RELATIVE, f"{_V}/entities/trail/model/trail.test.ts", "./trail", f"{_V}/entities/trail"
    ),
    FormImport(DIRECTORY_INDEX, f"{_V}/shared/api/client.tsx", "../config", f"{_V}/shared/config"),
    FormImport(
        DIRECTORY_INDEX,
        f"{_V}/features/start-hike/ui/StartHikeButton.tsx",
        "@modules/trail-haptics",
        _HAPTICS,
    ),
    FormImport(
        TSX,
        f"{_V}/widgets/trail-list/ui/TrailList.tsx",
        "@/entities/trail",
        f"{_V}/entities/trail",
    ),
    FormImport(TSX, "app/trail/[id].tsx", "@/pages/trail", f"{_V}/pages/trail"),
    FormImport(JSX, f"{_V}/entities/trail/ui/TrailCard.jsx", "@/shared/ui", f"{_V}/shared/ui"),
    FormImport(JSX, f"{_V}/entities/trail/index.ts", "./ui/TrailCard", f"{_V}/entities/trail"),
    FormImport(
        JS_IN_TS, f"{_V}/screens/LegacyMapScreen.js", "@/entities/trail", f"{_V}/entities/trail"
    ),
    FormImport(JS_IN_TS, f"{_V}/shared/config/index.js", "./env.mjs", f"{_V}/shared/config"),
    FormImport(MJS_CJS, f"{_V}/shared/config/index.js", "./env.mjs", f"{_V}/shared/config"),
    FormImport(MJS_CJS, f"{_V}/shared/lib/index.ts", "./units.cjs", f"{_V}/shared/lib"),
    FormImport(
        TSCONFIG_PATHS,
        f"{_V}/pages/trail/ui/TrailScreen.tsx",
        "~/src/features/start-hike",
        f"{_V}/features/start-hike",
    ),
    FormImport(
        BUNDLER_ALIAS,
        f"{_V}/pages/home/ui/HomeScreen.tsx",
        "@/widgets/trail-list",
        f"{_V}/widgets/trail-list",
    ),
    FormImport(
        BUNDLER_ALIAS,
        f"{_V}/features/start-hike/ui/StartHikeButton.tsx",
        "@modules/trail-haptics",
        _HAPTICS,
    ),
    FormImport(PLATFORM_SUFFIX, f"{_V}/shared/ui/index.ts", "./button/Button", f"{_V}/shared/ui"),
    FormImport(RE_EXPORT, "app/index.tsx", "@/pages/home", f"{_V}/pages/home"),
    FormImport(RE_EXPORT, f"{_HAPTICS}/index.ts", "./src/TrailHapticsModule", _HAPTICS),
)

#: Each FSD fixture's import forms, by stack. Vue has no ``.tsx``/``.jsx``, no platform
#: suffix; React Native has no ``.vue``, no ``baseUrl`` and no dynamic ``import()``.
IMPORT_FORMS: Mapping[str, tuple[FormImport, ...]] = {
    "vue-fsd": VUE_FSD_FORMS,
    "rn-fsd": RN_FSD_FORMS,
}

#: The specifier prefixes that name the project rather than a package, per fixture: the
#: relative ones, the tsconfig paths, the bundler aliases and the ``baseUrl`` folder.
PROJECT_PREFIXES: Mapping[str, tuple[str, ...]] = {
    "vue-fsd": ("./", "../", "@/", "@shared/", "src/"),
    "rn-fsd": ("./", "../", "@/", "@modules/", "~/"),
}

#: The findings each fixture earns on purpose, beside the layer rule's population note.
PLANTED: Mapping[str, frozenset[PlantedFinding]] = {
    "vue-fsd": frozenset(
        {
            # A cross-import inside the features layer.
            PlantedFinding(
                "fsd-layers", "error", f"{_V}/features/apply-coupon", f"{_V}/features/add-to-cart"
            ),
            # A deep import past entities/product's index.
            PlantedFinding(
                "fsd-public-api",
                "error",
                f"{_V}/widgets/product-grid",
                f"{_V}/entities/product",
                f"{_V}/widgets/product-grid/ui/ProductGrid.vue",
            ),
        }
    ),
    "rn-fsd": frozenset(
        {
            # `hooks/` is not one of FSD's standard segments.
            PlantedFinding("fsd-slice-shape", "warn", f"{_V}/features/start-hike"),
        }
    ),
}

#: The Expo module's bridge: its TypeScript to its Swift and its Kotlin side, which no
#: import carries (``requireNativeModule`` names the module by a string).
EXPO_BRIDGES: Mapping[str, frozenset[tuple[str, str]]] = {
    "rn-fsd": frozenset({(_HAPTICS, f"{_HAPTICS}/ios"), (_HAPTICS, f"{_HAPTICS}/android")}),
}

#: Expo Router's routes folder: one module to its adopter, holding the routes' files.
EXPO_ROUTER_ROUTES = "app"
EXPO_ROUTER_FILES = ("app/_layout.tsx", "app/index.tsx", "app/trail/[id].tsx")
