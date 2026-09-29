"""Adopter projects whose tests are not `tests/**/test_*.py` (BDL-074 G2, G2b).

Review ``beadloom-b9ll`` M3 reproduced the regression on a two-package Go module
and named two Python layouts beside it: tests kept in ``test/`` and tests kept
beside the code. Each builder writes one of them under a directory the caller
owns and returns its root; the reindex, ``ctx`` and the debt report are then run
against it by the test that asked. The Go module is the reviewer's, file for file
(``goproj`` in the review's scratchpad), less the files ``beadloom init`` wrote.

The Maven, Gradle-Kotlin and SwiftPM projects (``beadloom-2mj3.13``) are each laid
out by their ecosystem's standard directory layout, with the tests in the test
source tree the build tool runs and named by its convention, and two tests per
file.

``beadloom-2mj3.15`` adds one project for each remaining convention the retired
mapper read (``git show db5c3f28:src/beadloom/context_oracle/test_mapper.py``): a
Python test named ``*_test.py``, a JS/TS project whose test sits at a path the
caller names (``*.test.*``, ``*.spec.*`` or a ``__tests__/`` folder), a JVM test in
the build tool's test tree under a name no pattern matches, and a SwiftPM test
target per module holding a file no pattern matches.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

_GO_TEST = (
    "package {package}\n\n"
    'import "testing"\n\n'
    'func TestTotal(t *testing.T) {{ if Total(1, 2) != 3 {{ t.Fatal("bad") }} }}\n'
)
_GO_CODE = "package {package}\n\nfunc Total(a, b int) int {{ return a + b }}\n"

_PY_CODE = "def total(a: int, b: int) -> int:\n    return a + b\n"
_PY_TEST = (
    "from shop.{package}.{package} import total\n\n\n"
    "def test_total() -> None:\n    assert total(1, 2) == 3\n\n\n"
    "def test_zero() -> None:\n    assert total(0, 0) == 0\n"
)

#: The two packages every project here holds, each with a node of its own.
PACKAGES = ("billing", "orders")


def write(root: Path, relative: str, text: str) -> None:
    """Write *text* at *relative* under *root*, creating its folders."""
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _graph(root: Path, sources: dict[str, str]) -> None:
    nodes: list[dict[str, object]] = [
        {"ref_id": "shop", "kind": "service", "summary": "Root: shop", "source": ""}
    ]
    edges: list[dict[str, str]] = []
    for ref_id, source in sources.items():
        nodes.append({"ref_id": ref_id, "kind": "domain", "summary": ref_id, "source": source})
        edges.append({"src": ref_id, "dst": "shop", "kind": "part_of"})
    graph = {"nodes": nodes, "edges": edges}
    write(root, ".beadloom/_graph/services.yml", yaml.safe_dump(graph, sort_keys=False))


def _config(root: Path, *, language: str, scan_path: str, tests: object = None) -> None:
    config: dict[str, object] = {"languages": [language], "scan_paths": [scan_path]}
    if tests is not None:
        config["tests"] = tests
    write(root, ".beadloom/config.yml", yaml.safe_dump(config, sort_keys=False))


def go_module(root: Path) -> Path:
    """The reviewer's Go module: two packages, each with one test beside its code."""
    write(root, "go.mod", "module example.com/shop\n\ngo 1.22\n")
    for package in PACKAGES:
        write(root, f"internal/{package}/{package}.go", _GO_CODE.format(package=package))
        write(root, f"internal/{package}/{package}_test.go", _GO_TEST.format(package=package))
    _config(root, language=".go", scan_path="internal")
    _graph(root, {package: f"internal/{package}/" for package in PACKAGES})
    return root


def _python_code(root: Path) -> None:
    write(root, "pyproject.toml", '[project]\nname = "shop"\nversion = "0.1.0"\n')
    write(root, "src/shop/__init__.py", "")
    for package in PACKAGES:
        write(root, f"src/shop/{package}/__init__.py", "")
        write(root, f"src/shop/{package}/{package}.py", _PY_CODE)
    _graph(root, {package: f"src/shop/{package}/" for package in PACKAGES})


def python_with_a_test_root(root: Path, *, mirrored: bool) -> Path:
    """A Python project whose tests live in `test/`, declared as its test root.

    *mirrored* lays them out as ``test/unit/<package>/test_<package>.py``; otherwise
    they sit flat in ``test/``, which binds them to nothing.
    """
    _python_code(root)
    for package in PACKAGES:
        folder = f"test/unit/{package}/" if mirrored else "test/"
        write(root, f"{folder}test_{package}.py", _PY_TEST.format(package=package))
    _config(root, language=".py", scan_path="src", tests={"roots": ["test"]})
    return root


def python_beside_the_code(root: Path) -> Path:
    """A Python project whose tests sit beside the modules they test."""
    _python_code(root)
    for package in PACKAGES:
        write(root, f"src/shop/{package}/test_{package}.py", _PY_TEST.format(package=package))
    _config(root, language=".py", scan_path="src")
    return root


_JAVA_CODE = (
    "package com.example.shop.{package};\n\n"
    "public class {cls} {{\n    public int total(int a, int b) {{ return a + b; }}\n}}\n"
)
_JAVA_TEST = (
    "package com.example.shop.{package};\n\n"
    "import org.junit.jupiter.api.Test;\n\n"
    "class {test_class} {{\n"
    "    @Test\n    void adds() {{ assert new {cls}().total(1, 2) == 3; }}\n\n"
    "    @Test\n    void addsZero() {{ assert new {cls}().total(0, 0) == 0; }}\n"
    "}}\n"
)
_KOTLIN_CODE = (
    "package com.example.shop.{package}\n\n"
    "class {cls} {{\n    fun total(a: Int, b: Int) = a + b\n}}\n"
)
_KOTLIN_TEST = (
    "package com.example.shop.{package}\n\n"
    "import kotlin.test.Test\nimport kotlin.test.assertEquals\n\n"
    "class {test_class} {{\n"
    "    @Test\n    fun adds() = assertEquals(3, {cls}().total(1, 2))\n\n"
    "    @Test\n    fun addsZero() = assertEquals(0, {cls}().total(0, 0))\n"
    "}}\n"
)
_SWIFT_CODE = "public func total{cls}(_ a: Int, _ b: Int) -> Int {{ a + b }}\n"
_SWIFT_TEST = (
    "import XCTest\n@testable import Shop\n\n"
    "final class {cls}Tests: XCTestCase {{\n"
    "    func testAdds() {{ XCTAssertEqual(total{cls}(1, 2), 3) }}\n"
    "    func testAddsZero() {{ XCTAssertEqual(total{cls}(0, 0), 0) }}\n"
    "}}\n"
)


def _jvm_project(
    root: Path,
    *,
    language: str,
    suffix: str,
    code: str,
    test: str,
    test_class: str = "{cls}Test",
) -> Path:
    for package in PACKAGES:
        cls = package.title()
        folder = f"com/example/shop/{package}"
        write(
            root,
            f"src/main/{language}/{folder}/{cls}{suffix}",
            code.format(package=package, cls=cls),
        )
        write(
            root,
            f"src/test/{language}/{folder}/{test_class.format(cls=cls)}{suffix}",
            test.format(package=package, cls=cls, test_class=test_class.format(cls=cls)),
        )
    _config(root, language=suffix, scan_path="src")
    _graph(root, {p: f"src/main/{language}/com/example/shop/{p}/" for p in PACKAGES})
    return root


def maven_project(root: Path) -> Path:
    """A Maven project: `src/main/java` and `src/test/java`, `*Test.java` classes."""
    write(root, "pom.xml", "<project><artifactId>shop</artifactId></project>\n")
    return _jvm_project(root, language="java", suffix=".java", code=_JAVA_CODE, test=_JAVA_TEST)


def gradle_kotlin_project(root: Path) -> Path:
    """A Gradle Kotlin project: `src/main/kotlin` and `src/test/kotlin`, `*Test.kt` classes."""
    write(root, "build.gradle.kts", 'plugins { kotlin("jvm") version "2.0.0" }\n')
    return _jvm_project(
        root, language="kotlin", suffix=".kt", code=_KOTLIN_CODE, test=_KOTLIN_TEST
    )


def swift_package(root: Path) -> Path:
    """A Swift package: `Sources/Shop/<Package>/`, and `Tests/ShopTests/<Package>Tests.swift`."""
    write(root, "Package.swift", "// swift-tools-version:5.9\nimport PackageDescription\n")
    for package in PACKAGES:
        cls = package.title()
        write(root, f"Sources/Shop/{cls}/{cls}.swift", _SWIFT_CODE.format(cls=cls))
        write(root, f"Tests/ShopTests/{cls}Tests.swift", _SWIFT_TEST.format(cls=cls))
    _config(root, language=".swift", scan_path="Sources")
    _graph(root, {p: f"Sources/Shop/{p.title()}/" for p in PACKAGES})
    return root


def python_suffix_named(root: Path) -> Path:
    """A Python project whose tests sit beside the code, named ``<module>_test.py``."""
    _python_code(root)
    for package in PACKAGES:
        write(root, f"src/shop/{package}/{package}_test.py", _PY_TEST.format(package=package))
    _config(root, language=".py", scan_path="src")
    return root


_TS_CODE = "export function total(a: number, b: number): number {{ return a + b; }}\n"
_JS_TEST = (
    "import {{ total }} from '{module}';\n\n"
    "test('adds', () => {{ expect(total(1, 2)).toBe(3); }});\n"
    "it('adds zero', () => {{ expect(total(0, 0)).toBe(0); }});\n"
)


def jest_project(root: Path, test_path: str) -> Path:
    """A TypeScript project, `src/<package>/<package>.ts`, tested at *test_path*.

    *test_path* names each package's test file, with ``{p}`` for the package:
    ``src/{p}/{p}.test.ts`` beside the code, or ``src/{p}/__tests__/{p}.ts`` in a
    Jest ``__tests__/`` folder.
    """
    write(root, "package.json", '{"name": "shop", "devDependencies": {"jest": "29"}}\n')
    for package in PACKAGES:
        write(root, f"src/{package}/{package}.ts", _TS_CODE.format())
        write(root, test_path.format(p=package), _JS_TEST.format(module=f"./{package}"))
    _config(root, language=".ts", scan_path="src")
    _graph(root, {package: f"src/{package}/" for package in PACKAGES})
    return root


def jvm_test_tree_project(root: Path, *, kotlin: bool, test_class: str) -> Path:
    """A Maven or Gradle-Kotlin project whose test class is named *test_class*.

    *test_class* is a template over ``{cls}`` (``{cls}Spec``, ``{cls}Should``): a
    name no default pattern matches, in the test tree the build tool runs.
    """
    if kotlin:
        write(root, "build.gradle.kts", 'plugins { kotlin("jvm") version "2.0.0" }\n')
        return _jvm_project(
            root,
            language="kotlin",
            suffix=".kt",
            code=_KOTLIN_CODE,
            test=_KOTLIN_TEST,
            test_class=test_class,
        )
    write(root, "pom.xml", "<project><artifactId>shop</artifactId></project>\n")
    return _jvm_project(
        root,
        language="java",
        suffix=".java",
        code=_JAVA_CODE,
        test=_JAVA_TEST,
        test_class=test_class,
    )


def swift_package_by_target(root: Path, *, test_file: str) -> Path:
    """A Swift package with a target per module and a test target per target.

    `Sources/<Package>/<Package>.swift` is tested by `Tests/<Package>Tests/<test_file>`,
    where *test_file* is a template over ``{cls}`` (``{cls}Checks.swift``).
    """
    write(root, "Package.swift", "// swift-tools-version:5.9\nimport PackageDescription\n")
    for package in PACKAGES:
        cls = package.title()
        write(root, f"Sources/{cls}/{cls}.swift", _SWIFT_CODE.format(cls=cls))
        write(
            root,
            f"Tests/{cls}Tests/{test_file.format(cls=cls)}",
            _SWIFT_TEST.format(cls=cls).replace(
                "@testable import Shop", f"@testable import {cls}"
            ),
        )
    _config(root, language=".swift", scan_path="Sources")
    _graph(root, {p: f"Sources/{p.title()}/" for p in PACKAGES})
    return root


def _jest(test_path: str) -> Callable[[Path], Path]:
    return lambda root: jest_project(root, test_path)


#: Every convention the retired mapper read, each as a project whose tests follow it:
#: (convention, project builder, test path per package over {p} and {c}, framework,
#: tests per file). The last three are main's figures for billing and orders,
#: measured by running main's ``map_tests`` on the project (db5c3f28, 2026-09-28);
#: the root node ``shop`` held the union of both, as main's parent aggregation gave it.
CONVENTIONS_MAIN_READ: list[tuple[str, Callable[[Path], Path], str, str, int]] = [
    (
        "pytest test_*.py beside the code",
        python_beside_the_code,
        "src/shop/{p}/test_{p}.py",
        "pytest",
        2,
    ),
    (
        "pytest test_*.py mirrored under a declared root",
        lambda root: python_with_a_test_root(root, mirrored=True),
        "test/unit/{p}/test_{p}.py",
        "pytest",
        2,
    ),
    (
        "pytest *_test.py beside the code",
        python_suffix_named,
        "src/shop/{p}/{p}_test.py",
        "pytest",
        2,
    ),
    ("go *_test.go beside the package", go_module, "internal/{p}/{p}_test.go", "go_test", 1),
    ("jest *.test.ts", _jest("src/{p}/{p}.test.ts"), "src/{p}/{p}.test.ts", "jest", 2),
    ("jest *.spec.ts", _jest("src/{p}/{p}.spec.ts"), "src/{p}/{p}.spec.ts", "jest", 2),
    ("jest *.test.js", _jest("src/{p}/{p}.test.js"), "src/{p}/{p}.test.js", "jest", 2),
    ("jest *.spec.js", _jest("src/{p}/{p}.spec.js"), "src/{p}/{p}.spec.js", "jest", 2),
    (
        "jest __tests__/*.ts",
        _jest("src/{p}/__tests__/{p}.ts"),
        "src/{p}/__tests__/{p}.ts",
        "jest",
        2,
    ),
    (
        "jest __tests__/*.tsx",
        _jest("src/{p}/__tests__/{p}.tsx"),
        "src/{p}/__tests__/{p}.tsx",
        "jest",
        2,
    ),
    (
        "jest __tests__/*.js",
        _jest("src/{p}/__tests__/{p}.js"),
        "src/{p}/__tests__/{p}.js",
        "jest",
        2,
    ),
    (
        "jest __tests__/*.jsx",
        _jest("src/{p}/__tests__/{p}.jsx"),
        "src/{p}/__tests__/{p}.jsx",
        "jest",
        2,
    ),
    (
        "jest __tests__/ nested folder",
        _jest("src/{p}/__tests__/helpers/{p}.ts"),
        "src/{p}/__tests__/helpers/{p}.ts",
        "jest",
        2,
    ),
    (
        "junit *Test.java in src/test/java",
        maven_project,
        "src/test/java/com/example/shop/{p}/{c}Test.java",
        "junit",
        2,
    ),
    (
        "junit *Test.kt in src/test/kotlin",
        gradle_kotlin_project,
        "src/test/kotlin/com/example/shop/{p}/{c}Test.kt",
        "junit",
        2,
    ),
    (
        "junit any .java in src/test",
        lambda root: jvm_test_tree_project(root, kotlin=False, test_class="{cls}Should"),
        "src/test/java/com/example/shop/{p}/{c}Should.java",
        "junit",
        2,
    ),
    (
        "junit any .kt in src/test",
        lambda root: jvm_test_tree_project(root, kotlin=True, test_class="{cls}Spec"),
        "src/test/kotlin/com/example/shop/{p}/{c}Spec.kt",
        "junit",
        2,
    ),
    (
        "xctest *Tests.swift in Tests/",
        swift_package,
        "Tests/ShopTests/{c}Tests.swift",
        "xctest",
        2,
    ),
    (
        "xctest any .swift in a *Tests/ folder",
        lambda root: swift_package_by_target(root, test_file="{cls}Checks.swift"),
        "Tests/{c}Tests/{c}Checks.swift",
        "xctest",
        2,
    ),
]


# The conventions the retired mapper could reach only by a guess at a node's name
# (``beadloom-2mj3.15``): each is a place outside every root, test tree and node
# source, where it matched a file name, a folder name or an import against the
# node ids. The binding does not guess (owner ruling, 2026-09-28).


def python_flat_under(root: Path, folder: str) -> Path:
    """A Python project whose tests sit flat in *folder*, named after each package."""
    _python_code(root)
    for package in PACKAGES:
        write(root, f"{folder}/test_{package}.py", _PY_TEST.format(package=package))
    _config(root, language=".py", scan_path="src")
    return root


def python_tests_by_node_folder(root: Path) -> Path:
    """A Python project whose tests sit in `tests/<package>/`, with no kind folder."""
    _python_code(root)
    for package in PACKAGES:
        write(root, f"tests/{package}/test_flows.py", _PY_TEST.format(package=package))
    _config(root, language=".py", scan_path="src")
    return root


def python_tests_named_by_what_they_import(root: Path) -> Path:
    """A Python project whose flat `tests/test_<x>_flows.py` names its package only by import."""
    _python_code(root)
    for package in PACKAGES:
        write(
            root,
            f"tests/test_{package}_flows.py",
            f"import {package}\n\n\ndef test_a() -> None:\n    assert {package}\n",
        )
    _config(root, language=".py", scan_path="src")
    return root


def jest_top_level_tests_folder(root: Path) -> Path:
    """A TypeScript project whose tests sit in a `__tests__/` folder at the project root."""
    write(root, "package.json", '{"name": "shop", "devDependencies": {"jest": "29"}}\n')
    for package in PACKAGES:
        write(root, f"src/{package}/{package}.ts", _TS_CODE.format())
        write(
            root,
            f"__tests__/{package}.test.ts",
            _JS_TEST.format(module=f"../src/{package}/{package}"),
        )
    _config(root, language=".ts", scan_path="src")
    _graph(root, {package: f"src/{package}/" for package in PACKAGES})
    return root


def xcode_project(root: Path, *, mirrors: dict[str, str] | None = None) -> Path:
    """An Xcode project: code in `Shop/<Package>/`, tests in the `ShopTests/` sibling.

    *mirrors*, when given, is declared as ``tests.mirrors``.
    """
    for package in PACKAGES:
        cls = package.title()
        write(root, f"Shop/{cls}/{cls}.swift", _SWIFT_CODE.format(cls=cls))
        write(root, f"ShopTests/{cls}Tests.swift", _SWIFT_TEST.format(cls=cls))
    tests = None if mirrors is None else {"mirrors": mirrors}
    _config(root, language=".swift", scan_path="Shop", tests=tests)
    _graph(root, {p: f"Shop/{p.title()}/" for p in PACKAGES})
    return root


def declare_tests(root: Path, ref_id: str, prefixes: list[str]) -> None:
    """Give node *ref_id* a `tests:` list of *prefixes* in the project's graph."""
    graph_path = root / ".beadloom/_graph/services.yml"
    graph = yaml.safe_load(graph_path.read_text(encoding="utf-8"))
    for node in graph["nodes"]:
        if node["ref_id"] == ref_id:
            node["tests"] = prefixes
    graph_path.write_text(yaml.safe_dump(graph, sort_keys=False), encoding="utf-8")


def declare_config(root: Path, tests: dict[str, object]) -> None:
    """Add a `tests:` block to the project's `.beadloom/config.yml`."""
    config_path = root / ".beadloom/config.yml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["tests"] = tests
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")


def jest_flat_spec(root: Path, folder: str = "spec") -> Path:
    """A TypeScript project whose Jasmine-style tests sit flat in *folder*: `spec/<p>.spec.ts`."""
    write(root, "package.json", '{"name": "shop", "devDependencies": {"jest": "29"}}\n')
    for package in PACKAGES:
        write(root, f"src/{package}/{package}.ts", _TS_CODE.format())
        write(
            root,
            f"{folder}/{package}.spec.ts",
            _JS_TEST.format(module=f"../src/{package}/{package}"),
        )
    _config(root, language=".ts", scan_path="src")
    _graph(root, {package: f"src/{package}/" for package in PACKAGES})
    return root
