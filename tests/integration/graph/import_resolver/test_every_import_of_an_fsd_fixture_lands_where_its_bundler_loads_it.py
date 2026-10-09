"""Every import of the two FSD fixtures lands on the node owning the file its bundler loads.

BDL-080 S3T, the PRD's answer 2 and RFC D5: the viewer draws only what the import
resolver resolves, and Vue and React Native import differently. The adopter fixture's own
cases (``test_an_fsd_adopter_fixture_is_judged_by_the_rules_init_writes.py``) check a
listed import per form and that no import into the project stays unresolved. These check
every stored import against a reference reader written here, from each fixture's
configuration and its bundler's documented rules, and never from the product:

- Vite (``vue-fsd``): ``resolve.alias`` ``@`` and ``@shared``, tsconfig ``@/*`` and
  ``baseUrl: "."``, the default extensions (``.mjs .js .mts .ts .jsx .tsx .json``, so a
  ``.vue`` file is named in full), a ``.js`` specifier naming its ``.ts`` source, then a
  folder's ``index``;
- Metro (``rn-fsd``): Babel ``module-resolver`` ``@`` and ``@modules``, tsconfig ``~/*``,
  a platform suffix (``.ios .android .native .web``) before each plain extension, then a
  folder's ``index``.

A file is matched by its exact name, so the reader's answer does not depend on whether
the filesystem folds case. The owner of a file is the node whose source folder is its
longest prefix. ``require()`` is not read by the resolver (its SPEC's "Not handled"), and
neither fixture writes one, so the forms below are those of ESM.
"""

from __future__ import annotations

import posixpath
import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

import pytest

from tests.support.initialised_fixture import InitialisedFixture, initialise_fixture

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

pytest.importorskip("tree_sitter_typescript")


@dataclass(frozen=True)
class Bundler:
    """What a fixture's bundler reads a specifier through: its prefixes, then completion."""

    #: ``(prefix, folder)``: a specifier starting with the prefix names the folder's path.
    prefixes: tuple[tuple[str, str], ...]
    extensions: tuple[str, ...]
    platforms: tuple[str, ...] = ()


_BUNDLERS = {
    "vue-fsd": Bundler(
        prefixes=(("@/", "src/"), ("@shared/", "src/shared/"), ("src/", "src/")),
        extensions=(".mjs", ".js", ".mts", ".ts", ".jsx", ".tsx", ".json"),
    ),
    "rn-fsd": Bundler(
        prefixes=(("~/", ""), ("@modules/", "modules/"), ("@/", "src/")),
        extensions=(".tsx", ".ts", ".jsx", ".js", ".json", ".mjs", ".cjs"),
        platforms=(".ios", ".android", ".native", ".web"),
    ),
}

#: The forms a stored import is counted under. One import carries several: its importer,
#: its specifier, the statement and the file it lands on.
RELATIVE = "relative ./ ../"
TSCONFIG_PATHS = "tsconfig paths"
BUNDLER_ALIAS = "bundler alias"
BASE_URL = "tsconfig baseUrl"
FROM_VUE = '.vue <script setup lang="ts">'
FROM_TSX = "from a .tsx file"
FROM_JSX = "from a .jsx file"
FROM_JS = "from a .js file beside TypeScript"
RE_EXPORT = "re-export"
DYNAMIC = "dynamic import()"
FOLDER_INDEX = "a folder through its index"
PLATFORM = "a platform suffix"
VUE_FILE = "a .vue file by its name"
INTO_MJS_CJS = "into a .mjs/.cjs file"

#: The form a prefix is counted under, by fixture.
_PREFIX_FORMS = {
    "vue-fsd": {"@/": TSCONFIG_PATHS, "@shared/": BUNDLER_ALIAS, "src/": BASE_URL},
    "rn-fsd": {"~/": TSCONFIG_PATHS, "@modules/": BUNDLER_ALIAS, "@/": BUNDLER_ALIAS},
}

#: Every form each fixture carries, as measured on 8dbe844c: a form leaving a fixture is
#: a fixture that no longer measures it, and fails here rather than passing on nothing.
CARRIED = {
    "vue-fsd": (
        RELATIVE,
        TSCONFIG_PATHS,
        BUNDLER_ALIAS,
        BASE_URL,
        FROM_VUE,
        FROM_JS,
        RE_EXPORT,
        DYNAMIC,
        FOLDER_INDEX,
        VUE_FILE,
        INTO_MJS_CJS,
    ),
    "rn-fsd": (
        RELATIVE,
        TSCONFIG_PATHS,
        BUNDLER_ALIAS,
        FROM_TSX,
        FROM_JSX,
        FROM_JS,
        RE_EXPORT,
        FOLDER_INDEX,
        PLATFORM,
        INTO_MJS_CJS,
    ),
}

_IMPORTER_FORMS = {".vue": FROM_VUE, ".tsx": FROM_TSX, ".jsx": FROM_JSX, ".js": FROM_JS}

#: An ESM specifier: ``from '...'``, ``import '...'`` and ``import('...')``.
_SPECIFIER = re.compile(r"""(?:\bfrom\s*|\bimport\s*\(\s*|\bimport\s+)['"]([^'"]+)['"]""")


@dataclass(frozen=True)
class Landing:
    """One stored import, the forms it carries, and where it landed against where it loads."""

    where: str
    forms: frozenset[str]
    stored: str | None
    expected: str | None

    @property
    def lands_right(self) -> bool:
        return self.stored is not None and self.stored == self.expected


class _Reader:
    """The reference reader of one fixture's imports, over its copy on disk."""

    def __init__(self, fixture: InitialisedFixture) -> None:
        self.root = fixture.root
        self.bundler = _BUNDLERS[fixture.stack]
        self.prefix_forms = _PREFIX_FORMS[fixture.stack]
        self.sources = {ref: src for ref, src in fixture.sources().items() if src}

    def kind(self, rel_path: str) -> str | None:
        """``file`` or ``dir`` when *rel_path* exists under its exact name, else None."""
        current = self.root
        for part in PurePosixPath(rel_path).parts:
            try:
                names = {child.name for child in current.iterdir()}
            except OSError:
                return None
            if part not in names:
                return None
            current = current / part
        return "dir" if current.is_dir() else "file"

    def _completed(self, base: str) -> tuple[str | None, frozenset[str]]:
        """The file *base* loads, and the completion forms it took to get there."""
        if self.kind(base) == "file":
            return base, frozenset()
        if base.endswith(".js"):
            for extension in (".ts", ".tsx"):
                if self.kind(base.removesuffix(".js") + extension) == "file":
                    return base.removesuffix(".js") + extension, frozenset()
        for stem, forms in ((base, frozenset()), (f"{base}/index", frozenset({FOLDER_INDEX}))):
            if stem != base and self.kind(base) != "dir":
                continue
            for extension in self.bundler.extensions:
                for platform in self.bundler.platforms:
                    if self.kind(stem + platform + extension) == "file":
                        return stem + platform + extension, forms | {PLATFORM}
                if self.kind(stem + extension) == "file":
                    return stem + extension, forms
        return None, frozenset()

    def owner(self, rel_path: str) -> str | None:
        """The node whose source folder is the longest prefix of *rel_path*."""
        owners = [
            (len(source), ref)
            for ref, source in self.sources.items()
            if rel_path == source or rel_path.startswith(f"{source}/")
        ]
        return max(owners)[1] if owners else None

    def landing(self, importer: str, line: int, specifier: str, stored: str | None) -> Landing:
        """Where the import of *specifier* from *importer* loads; None for a package."""
        forms = set()
        if specifier.startswith(("./", "../")):
            forms.add(RELATIVE)
            base = posixpath.normpath(str(PurePosixPath(importer).parent / specifier))
        else:
            prefix = next(p for p, _ in self.bundler.prefixes if specifier.startswith(p))
            folder = dict(self.bundler.prefixes)[prefix]
            forms.add(self.prefix_forms[prefix])
            base = folder + specifier.removeprefix(prefix)
        forms.update(form for suffix, form in _IMPORTER_FORMS.items() if importer.endswith(suffix))
        statement = self._statement(importer, line, specifier)
        if re.match(r"export\b", statement):
            forms.add(RE_EXPORT)
        if re.search(r"\bimport\s*\(", statement):
            forms.add(DYNAMIC)
        target, completion = self._completed(base.rstrip("/"))
        forms.update(completion)
        if target is not None and target.endswith(".vue"):
            forms.add(VUE_FILE)
        if target is not None and target.endswith((".mjs", ".cjs")):
            forms.add(INTO_MJS_CJS)
        expected = self.owner(target) if target is not None else None
        return Landing(f"{importer}:{line} {specifier}", frozenset(forms), stored, expected)

    def names_the_project(self, specifier: str) -> bool:
        return specifier.startswith(("./", "../")) or any(
            specifier.startswith(prefix) for prefix, _ in self.bundler.prefixes
        )

    def _statement(self, importer: str, line: int, specifier: str) -> str:
        """The statement the specifier stands in, from its first line on."""
        lines = (self.root / importer).read_text(encoding="utf-8").splitlines()
        statement = lines[line - 1].strip()
        follow = line
        while f"'{specifier}'" not in statement and f'"{specifier}"' not in statement:
            if follow >= len(lines):
                break
            statement = f"{statement} {lines[follow].strip()}"
            follow += 1
        return statement


@dataclass(frozen=True)
class Read:
    """A fixture after ``init``, with every stored import into the project read again."""

    fixture: InitialisedFixture
    landings: tuple[Landing, ...]


@pytest.fixture(scope="module")
def read(tmp_path_factory: pytest.TempPathFactory) -> Callable[[str], Read]:
    """The FSD fixture of *stack* given ``init``, its imports read by the reader, once."""
    done: dict[str, Read] = {}

    def read_of(stack: str) -> Read:
        if stack not in done:
            fixture = initialise_fixture(stack, tmp_path_factory.mktemp(f"forms-{stack}"))
            reader = _Reader(fixture)
            rows = fixture.query(
                "SELECT file_path, line_number, import_path, resolved_ref_id FROM code_imports"
            )
            landings = tuple(
                reader.landing(path, line, specifier, ref)
                for path, line, specifier, ref in rows
                if reader.names_the_project(specifier)
            )
            done[stack] = Read(fixture, landings)
        return done[stack]

    return read_of


_CASES = [(stack, form) for stack, forms in CARRIED.items() for form in forms]


@pytest.mark.parametrize(("stack", "form"), _CASES)
def test_every_import_of_a_form_lands_on_the_node_owning_the_file_its_bundler_loads(
    read: Callable[[str], Read], stack: str, form: str
) -> None:
    landings = [landing for landing in read(stack).landings if form in landing.forms]

    wrong = [
        f"{landing.where}: stored {landing.stored}, loads into {landing.expected}"
        for landing in landings
        if not landing.lands_right
    ]

    assert landings, f"{stack} no longer carries the form {form!r}"
    assert wrong == []


@pytest.mark.parametrize("stack", list(CARRIED))
def test_every_esm_specifier_the_indexed_code_writes_is_stored(
    read: Callable[[str], Read], stack: str
) -> None:
    fixture = read(stack).fixture
    indexed = [path for (path,) in fixture.query("SELECT path FROM file_index")]
    stored = {
        (path, spec)
        for path, spec in fixture.query("SELECT file_path, import_path FROM code_imports")
    }

    written = {
        (path, match.group(1))
        for path in indexed
        if _is_script(fixture.root / path)
        for match in _SPECIFIER.finditer((fixture.root / path).read_text(encoding="utf-8"))
    }

    assert written
    assert sorted(written - stored) == []


def _is_script(path: Path) -> bool:
    return path.suffix in {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".vue"}
