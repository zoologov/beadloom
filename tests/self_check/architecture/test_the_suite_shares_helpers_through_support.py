"""BDL-074 B1 — the suite's own layout: shared helpers in one place, one root.

Two shapes stop a test file from moving to another folder, and B2 and B3 move
several hundred of them:

* **It imports another test module.** The definitions it borrowed travel with
  the neighbour, not with it, and a test module imported for its helpers is
  collected twice over the same helper. What two modules share lives in
  ``tests/support/``.
* **It counts its own parents to find the repository root.** ``parents[3]``
  is the root only at the depth the file was written at; one folder deeper it
  is ``tests/``, and nothing fails until a read comes back empty.
  :mod:`tests.support.repository_root` finds the root one way from any depth.

Both are held here over every Python file under ``tests/``, so a file added
tomorrow is judged the way today's are. What is exempt is declared below with
its reason and the bead that removes it.
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

from tests.support.repository_root import REPO_ROOT, TESTS_ROOT

if TYPE_CHECKING:
    from pathlib import Path

#: The one module allowed to locate the repository from its own file.
_THE_ROOT_HELPER = "tests/support/repository_root.py"

#: The package every shared helper lives in.
_SUPPORT = "tests.support"

#: Trees under ``tests/`` that are data rather than suite: projects the tests
#: copy and run the product over.
_DATA_DIRS = frozenset({"fixtures", "__pycache__"})

#: Paths (by prefix) still allowed to count their own parents, with reason and
#: exit. Empty since ``beadloom-vr0b`` landed and its five mutation self-checks
#: moved onto the helper; an entry added here needs both, and fails when unused.
PARENT_COUNTING_EXEMPT: dict[str, str] = {}

#: Test modules (by path prefix) another module may import, with reason and exit.
IMPORTABLE_TEST_MODULES: dict[str, str] = {
    "tests/self_check/config/test_mutation_weekly_announcement.py": (
        "the announcement's own tests are the SUBJECT of "
        "test_the_weekly_announcement_tests_would_notice.py, which runs them "
        "against a broken copy of the workflow and requires them to go red: the "
        "import is the test, not a borrowed helper. Exit: the day that check runs "
        "them in a child pytest by path instead of importing them"
    ),
    "tests/release/verify_the_release.py": (
        "the release harness is a script a maintainer runs by path, stdlib-only so any "
        "Python 3.10+ runs it without the dev environment, which rules out tests/support "
        "(its __init__ imports pytest). Its unit test, "
        "tests/self_check/process/test_the_release_harness_reports_what_ran.py, imports it "
        "because the harness is the SUBJECT of that test, not a borrowed helper. Exit: the "
        "harness moves into a package the suite may import"
    ),
}


def _exempt(path: str, table: dict[str, str]) -> bool:
    return any(path.startswith(prefix) for prefix in table)


def _suite_files() -> list[Path]:
    """Every Python file of the suite, data trees excluded."""
    return sorted(
        path
        for path in TESTS_ROOT.rglob("*.py")
        if not _DATA_DIRS.intersection(path.relative_to(TESTS_ROOT).parts)
    )


def _relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _module_of(path: Path, root: Path) -> list[str]:
    parts = list(path.relative_to(root).with_suffix("").parts)
    return parts[:-1] if parts[-1] == "__init__" else parts


def _file_of(module: str, root: Path = REPO_ROOT) -> Path | None:
    base = root.joinpath(*module.split("."))
    for candidate in (base.with_suffix(".py"), base / "__init__.py"):
        if candidate.is_file():
            return candidate
    return None


def suite_imports(path: Path, root: Path = REPO_ROOT) -> list[tuple[int, str]]:
    """Each suite module *path* imports, as ``(line, module)``; relative forms resolved."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    package = _module_of(path, root)
    if path.name != "__init__.py":
        package = package[:-1]
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(
                (node.lineno, alias.name)
                for alias in node.names
                if alias.name.startswith("tests.")
            )
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                anchor = package[: len(package) - node.level + 1]
                module = ".".join([*anchor, *([node.module] if node.module else [])])
            else:
                module = node.module or ""
            if module != "tests" and not module.startswith("tests."):
                continue
            # ``from tests import x`` imports the MODULE x when there is one.
            submodules = [
                f"{module}.{alias.name}"
                for alias in node.names
                if _file_of(f"{module}.{alias.name}", root)
            ]
            found.extend((node.lineno, name) for name in submodules or [module])
    return found


def parent_counts(source: str) -> list[int]:
    """The lines where *source* walks up from a file's own location.

    Two spellings: ``.parent`` or ``.parents`` on a path built from this
    module's ``__file__``, and ``.parents`` on another module's ``__file__``
    (``Path(beadloom.__file__).resolve().parents[2]``) — the root reached by
    counting from the package instead. One ``.parent`` of another module's file
    is that module's directory, not the root, and is not counted.
    """
    lines: set[int] = set()
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Attribute) or node.attr not in {"parent", "parents"}:
            continue
        origin = _file_origin(node.value)
        if origin == "own" or (origin == "other" and node.attr == "parents"):
            lines.add(node.lineno)
    return sorted(lines)


def _file_origin(node: ast.expr) -> str | None:
    """``"own"`` for this module's ``__file__``, ``"other"`` for ``x.__file__``, else ``None``."""
    while True:
        if isinstance(node, ast.Name):
            return "own" if node.id == "__file__" else None
        if isinstance(node, ast.Attribute):
            if node.attr == "__file__":
                return "other"
            node = node.value
        elif isinstance(node, ast.Subscript):
            node = node.value
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                node = node.func.value
            elif node.args:
                node = node.args[0]
            else:
                return None
        else:
            return None


class TestNoTestModuleImportsAnother:
    def test_every_import_of_a_suite_module_is_an_import_of_support(self) -> None:
        offenders = sorted(
            f"{_relative(path)}:{line} imports {module}"
            for path in _suite_files()
            for line, module in suite_imports(path)
            if not (module == _SUPPORT or module.startswith(f"{_SUPPORT}."))
            and _file_of(module) != path  # a module reading its own members
            and not _exempt(_relative(_file_of(module) or path), IMPORTABLE_TEST_MODULES)
        )

        assert offenders == [], (
            "a module of the suite imports a module outside tests/support/. Move "
            "what it borrows into tests/support/ under a name that says what it "
            f"is for: {offenders}"
        )

    def test_every_declared_exemption_is_still_imported(self) -> None:
        imported = {
            _relative(target)
            for path in _suite_files()
            for _, module in suite_imports(path)
            if (target := _file_of(module)) is not None
        }
        unused = [
            prefix
            for prefix in IMPORTABLE_TEST_MODULES
            if not any(path.startswith(prefix) for path in imported)
        ]

        assert unused == [], f"an exemption no import uses any more; remove it: {unused}"


class TestNoTestCountsItsParents:
    def test_no_file_of_the_suite_finds_the_root_from_its_own_depth(self) -> None:
        carrying = {
            _relative(path)
            for path in _suite_files()
            if _relative(path) != _THE_ROOT_HELPER
            and parent_counts(path.read_text(encoding="utf-8"))
        }
        undeclared = sorted(path for path in carrying if not _exempt(path, PARENT_COUNTING_EXEMPT))
        unused = [
            prefix
            for prefix in PARENT_COUNTING_EXEMPT
            if not any(path.startswith(prefix) for path in carrying)
        ]

        assert undeclared == [], (
            "a file of the suite walks up from its own location. Use REPO_ROOT or "
            f"TESTS_ROOT from tests.support.repository_root: {undeclared}"
        )
        assert unused == [], f"an exemption no file needs any more; remove it: {unused}"


class TestTheDetectorsBite:
    """Each shape, written fresh, is caught; the helper's own shape is not."""

    def test_counting_this_files_parents_is_caught(self) -> None:
        assert parent_counts(
            "from pathlib import Path\nR = Path(__file__).resolve().parents[3]\n"
        ) == [2]
        assert parent_counts("from pathlib import Path\nR = Path(__file__).parent.parent\n") == [2]
        assert parent_counts("from pathlib import Path\nT = Path(__file__).parent / 'x'\n") == [2]

    def test_counting_the_packages_parents_is_caught(self) -> None:
        source = (
            "import beadloom\nfrom pathlib import Path\n"
            "R = Path(beadloom.__file__).resolve().parents[2]\n"
        )
        assert parent_counts(source) == [3]

    def test_the_packages_own_directory_is_not_the_root_and_is_not_caught(self) -> None:
        source = (
            "import beadloom\nfrom pathlib import Path\n"
            "P = Path(beadloom.__file__).resolve().parent\n"
        )
        assert parent_counts(source) == []

    def test_a_path_that_is_not_built_from_a_file_is_not_caught(self) -> None:
        assert parent_counts("def f(p):\n    return p.parent.parent\n") == []

    def test_every_import_form_of_a_suite_module_is_seen(self, tmp_path: Path) -> None:
        steps = tmp_path / "tests" / "acceptance" / "steps"
        steps.mkdir(parents=True)
        for package in (tmp_path / "tests", tmp_path / "tests" / "acceptance", steps):
            (package / "__init__.py").write_text("", encoding="utf-8")
        (steps / "shared_steps.py").write_text("", encoding="utf-8")
        (tmp_path / "tests" / "test_neighbour.py").write_text("", encoding="utf-8")
        importer = steps / "test_x_steps.py"
        importer.write_text(
            "from .shared_steps import build\n"
            "from tests import test_neighbour\n"
            "import tests.test_neighbour\n"
            "from tests.test_neighbour import helper\n"
            "from beadloom import tests_elsewhere\n",
            encoding="utf-8",
        )

        assert suite_imports(importer, tmp_path) == [
            (1, "tests.acceptance.steps.shared_steps"),
            (2, "tests.test_neighbour"),
            (3, "tests.test_neighbour"),
            (4, "tests.test_neighbour"),
        ]
