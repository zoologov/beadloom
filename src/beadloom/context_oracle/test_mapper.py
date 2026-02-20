"""Test mapper: detect test frameworks and map test files to source nodes."""

# beadloom:domain=context-oracle

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


@dataclass(frozen=True)
class TestMapping:
    """Mapping of test files to a source node."""

    framework: str  # pytest, jest, go_test, junit, xctest
    test_files: list[str]  # relative paths
    test_count: int  # number of test functions/methods
    coverage_estimate: str  # high | medium | low | none


# ---------------------------------------------------------------------------
# Test function counting patterns
# ---------------------------------------------------------------------------

_PYTEST_TEST_RE = re.compile(r"^\s*def\s+test_\w+", re.MULTILINE)
_JEST_TEST_RE = re.compile(r"(?:^|\s)(?:test|it)\s*\(", re.MULTILINE)
_GO_TEST_RE = re.compile(r"^\s*func\s+Test\w+\(", re.MULTILINE)
_JUNIT_TEST_RE = re.compile(r"@Test\b")
_XCTEST_TEST_RE = re.compile(r"^\s*func\s+test\w+\(", re.MULTILINE)

# Import patterns for Python test files
_IMPORT_FROM_RE = re.compile(r"^\s*from\s+([\w.]+)\s+import", re.MULTILINE)
_IMPORT_MODULE_RE = re.compile(r"^\s*import\s+([\w.]+)", re.MULTILINE)


# ---------------------------------------------------------------------------
# Framework detection
# ---------------------------------------------------------------------------


def _detect_frameworks(project_root: Path) -> list[str]:
    """Detect test frameworks present in the project.

    Returns a list of framework names found (may be multiple).
    """
    frameworks: list[str] = []

    # pytest: conftest.py at root, or test_*.py / *_test.py files
    if (project_root / "conftest.py").exists() or (
        ((project_root / "setup.cfg").exists() or (project_root / "pyproject.toml").exists())
        and _find_files_by_patterns(project_root, ["test_*.py", "*_test.py"])
    ):
        frameworks.append("pytest")

    # jest: jest.config.*, *.test.ts, *.spec.ts, __tests__/
    jest_patterns = [
        "*.test.ts",
        "*.spec.ts",
        "*.test.js",
        "*.spec.js",
    ]
    if (
        list(project_root.glob("jest.config.*"))
        or _find_files_by_patterns(project_root, jest_patterns)
        or _find_dirs_by_name(project_root, "__tests__")
    ):
        frameworks.append("jest")

    # go test: *_test.go files
    if _find_files_by_patterns(project_root, ["*_test.go"]):
        frameworks.append("go_test")

    # JUnit: src/test/ directory, or *Test.java / *Test.kt files
    if (project_root / "src" / "test").exists() or _find_files_by_patterns(
        project_root, ["*Test.java", "*Test.kt"]
    ):
        frameworks.append("junit")

    # XCTest: *Tests.swift files, or *Tests/ directories
    if _find_files_by_patterns(project_root, ["*Tests.swift"]) or _find_dirs_by_name(
        project_root, "Tests", suffix=True
    ):
        frameworks.append("xctest")

    return frameworks


def _find_files_by_patterns(root: Path, patterns: list[str]) -> list[Path]:
    """Find files matching any of the glob patterns recursively."""
    results: list[Path] = []
    for pattern in patterns:
        results.extend(root.rglob(pattern))
    return results


def _find_dirs_by_name(
    root: Path,
    name: str,
    *,
    suffix: bool = False,
) -> list[Path]:
    """Find directories by exact name or name ending."""
    results: list[Path] = []
    for item in root.rglob("*"):
        if item.is_dir() and (
            (suffix and item.name.endswith(name)) or (not suffix and item.name == name)
        ):
            results.append(item)
    return results


# ---------------------------------------------------------------------------
# Test file discovery per framework
# ---------------------------------------------------------------------------


def _find_pytest_test_files(project_root: Path) -> list[str]:
    """Find all pytest test files."""
    files: list[str] = []
    for pattern in ["test_*.py", "*_test.py"]:
        for f in project_root.rglob(pattern):
            if f.is_file() and "conftest" not in f.name:
                rel = str(f.relative_to(project_root))
                if rel not in files:
                    files.append(rel)
    return sorted(files)


def _find_jest_test_files(project_root: Path) -> list[str]:
    """Find all jest test files."""
    files: list[str] = []
    jest_patterns = [
        "*.test.ts",
        "*.spec.ts",
        "*.test.js",
        "*.spec.js",
        "*.test.tsx",
        "*.spec.tsx",
    ]
    for pattern in jest_patterns:
        for f in project_root.rglob(pattern):
            if f.is_file():
                rel = str(f.relative_to(project_root))
                if rel not in files:
                    files.append(rel)
    # Also check __tests__/ directories
    for tests_dir in _find_dirs_by_name(project_root, "__tests__"):
        for f in tests_dir.rglob("*"):
            if f.is_file() and f.suffix in (".ts", ".tsx", ".js", ".jsx"):
                rel = str(f.relative_to(project_root))
                if rel not in files:
                    files.append(rel)
    return sorted(files)


def _find_go_test_files(project_root: Path) -> list[str]:
    """Find all Go test files."""
    files: list[str] = []
    for f in project_root.rglob("*_test.go"):
        if f.is_file():
            files.append(str(f.relative_to(project_root)))
    return sorted(files)


def _find_junit_test_files(project_root: Path) -> list[str]:
    """Find all JUnit test files."""
    files: list[str] = []
    # Standard Maven/Gradle test directory
    test_dir = project_root / "src" / "test"
    if test_dir.exists():
        for f in test_dir.rglob("*"):
            if f.is_file() and f.suffix in (".java", ".kt"):
                files.append(str(f.relative_to(project_root)))
    # Also look for *Test.java / *Test.kt anywhere
    for pattern in ["*Test.java", "*Test.kt"]:
        for f in project_root.rglob(pattern):
            if f.is_file():
                rel = str(f.relative_to(project_root))
                if rel not in files:
                    files.append(rel)
    return sorted(files)


def _find_xctest_test_files(project_root: Path) -> list[str]:
    """Find all XCTest test files."""
    files: list[str] = []
    for f in project_root.rglob("*Tests.swift"):
        if f.is_file():
            files.append(str(f.relative_to(project_root)))
    # Also check *Tests/ directories
    for tests_dir in _find_dirs_by_name(project_root, "Tests", suffix=True):
        for f in tests_dir.rglob("*.swift"):
            if f.is_file():
                rel = str(f.relative_to(project_root))
                if rel not in files:
                    files.append(rel)
    return sorted(files)


def _get_test_files_for_framework(
    project_root: Path,
    framework: str,
) -> list[str]:
    """Get test files for a specific framework."""
    finders: dict[str, Callable[[Path], list[str]]] = {
        "pytest": _find_pytest_test_files,
        "jest": _find_jest_test_files,
        "go_test": _find_go_test_files,
        "junit": _find_junit_test_files,
        "xctest": _find_xctest_test_files,
    }
    finder = finders.get(framework)
    if finder is None:
        return []
    return finder(project_root)


# ---------------------------------------------------------------------------
# Test function counting
# ---------------------------------------------------------------------------


def _count_tests_in_file(file_path: Path, framework: str) -> int:
    """Count the number of test functions/methods in a file."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0

    patterns: dict[str, re.Pattern[str]] = {
        "pytest": _PYTEST_TEST_RE,
        "jest": _JEST_TEST_RE,
        "go_test": _GO_TEST_RE,
        "junit": _JUNIT_TEST_RE,
        "xctest": _XCTEST_TEST_RE,
    }
    pattern = patterns.get(framework)
    if pattern is None:
        return 0

    return len(pattern.findall(content))


# ---------------------------------------------------------------------------
# Mapping logic: test files -> source nodes
# ---------------------------------------------------------------------------


def _extract_module_name_from_test_file(
    test_file: str,
    framework: str,
) -> list[str]:
    """Extract potential module names from a test file path.

    Strategies:
    - Naming convention: test_auth.py -> "auth", auth.test.ts -> "auth"
    - Directory proximity: tests/auth/test_login.py -> "auth"
    """
    from pathlib import PurePosixPath

    parts = PurePosixPath(test_file).parts
    candidates: list[str] = []

    if framework == "pytest":
        # test_auth.py -> "auth"
        filename = PurePosixPath(test_file).stem
        if filename.startswith("test_"):
            base = filename[5:]  # strip "test_"
            # Remove trailing suffixes like _service, _handler
            candidates.append(base.split("_")[0])
            candidates.append(base)
        elif filename.endswith("_test"):
            base = filename[:-5]  # strip "_test"
            candidates.append(base.split("_")[0])
            candidates.append(base)

        # Directory proximity: tests/auth/test_login.py -> "auth"
        for part in parts:
            if part not in ("tests", "test", ".", "..") and not part.startswith("test_"):
                candidates.append(part)

    elif framework == "jest":
        # auth.test.ts -> "auth"
        filename = PurePosixPath(test_file).name
        jest_suffixes = (
            ".test.ts",
            ".spec.ts",
            ".test.js",
            ".spec.js",
            ".test.tsx",
            ".spec.tsx",
        )
        for sfx in jest_suffixes:
            if filename.endswith(sfx):
                base = filename[: -len(sfx)]
                candidates.append(base.split(".")[0])
                candidates.append(base)
                break

        # __tests__/ directory + parent: src/auth/__tests__/auth.test.ts -> "auth"
        for i, part in enumerate(parts):
            if part == "__tests__" and i > 0:
                candidates.append(parts[i - 1])
            elif part not in ("__tests__", "src", ".", ".."):
                candidates.append(part)

    elif framework == "go_test":
        # auth_test.go in src/auth/ -> "auth"
        for part in parts:
            if not part.endswith("_test.go") and part not in ("src", ".", ".."):
                candidates.append(part)

    elif framework == "junit":
        # AuthTest.java -> "auth"
        filename = PurePosixPath(test_file).stem
        if filename.endswith("Test"):
            base = filename[:-4].lower()
            candidates.append(base)
        # Directory names from path
        for part in parts:
            if part not in ("src", "test", "java", "kotlin", ".", ".."):
                candidates.append(part.lower())

    elif framework == "xctest":
        # AuthTests.swift -> "auth"
        filename = PurePosixPath(test_file).stem
        if filename.endswith("Tests"):
            base = filename[:-5].lower()
            candidates.append(base)
        # *Tests/ directory
        for part in parts:
            if part.endswith("Tests"):
                candidates.append(part[:-5].lower())
            elif part not in (".", ".."):
                candidates.append(part.lower())

    return candidates


def _extract_imports_from_python_test(
    file_path: Path,
) -> list[str]:
    """Extract module names from Python import statements in a test file."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    modules: list[str] = []

    # from auth.service import AuthService -> "auth"
    for match in _IMPORT_FROM_RE.finditer(content):
        module_path = match.group(1)
        top_module = module_path.split(".")[0]
        modules.append(top_module)

    # import billing -> "billing"
    for match in _IMPORT_MODULE_RE.finditer(content):
        module_path = match.group(1)
        top_module = module_path.split(".")[0]
        modules.append(top_module)

    return modules


def _map_test_file_to_nodes(
    test_file: str,
    framework: str,
    source_dirs: dict[str, str],
    project_root: Path,
) -> list[str]:
    """Map a single test file to source node ref_ids.

    Uses three strategies in priority order:
    1. Import analysis (for Python/pytest)
    2. Naming convention
    3. Directory proximity
    """
    matched_nodes: list[str] = []
    source_keys_lower = {k.lower(): k for k in source_dirs}

    # Strategy 1: Import analysis (pytest only)
    if framework == "pytest":
        abs_path = project_root / test_file
        imports = _extract_imports_from_python_test(abs_path)
        for imp in imports:
            imp_lower = imp.lower()
            if imp_lower in source_keys_lower:
                ref_id = source_keys_lower[imp_lower]
                if ref_id not in matched_nodes:
                    matched_nodes.append(ref_id)

    # Strategy 2 & 3: Naming convention + directory proximity
    candidates = _extract_module_name_from_test_file(test_file, framework)
    for candidate in candidates:
        candidate_lower = candidate.lower()
        if candidate_lower in source_keys_lower:
            ref_id = source_keys_lower[candidate_lower]
            if ref_id not in matched_nodes:
                matched_nodes.append(ref_id)

    return matched_nodes


# ---------------------------------------------------------------------------
# Coverage estimate
# ---------------------------------------------------------------------------


def _estimate_coverage(test_file_count: int, framework_detected: bool) -> str:
    """Estimate test coverage level based on test file count.

    Parameters
    ----------
    test_file_count:
        Number of test files mapped to this module.
    framework_detected:
        Whether any test framework was detected in the project.

    Returns
    -------
    str
        One of: 'high', 'medium', 'low', 'none'.
    """
    if test_file_count > 3:
        return "high"
    if 1 <= test_file_count <= 3:
        return "medium"
    if framework_detected:
        return "low"
    return "none"


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def map_tests(
    project_root: Path,
    source_dirs: dict[str, str],
) -> dict[str, TestMapping]:
    """Map test files to source nodes.

    Parameters
    ----------
    project_root:
        Root of the project to scan.
    source_dirs:
        Mapping of ref_id -> source_path (relative) for source modules.

    Returns
    -------
    dict[str, TestMapping]
        Mapping of ref_id -> TestMapping for each source node.
    """
    if not source_dirs:
        return {}

    # Step 1: Detect frameworks
    frameworks = _detect_frameworks(project_root)
    framework_detected = len(frameworks) > 0

    # Step 2: Collect all test files per framework
    framework_files: dict[str, list[str]] = {}
    for fw in frameworks:
        framework_files[fw] = _get_test_files_for_framework(project_root, fw)

    # Step 3: Map test files to source nodes
    # node_ref_id -> {framework -> [test_file, ...]}
    node_tests: dict[str, dict[str, list[str]]] = {ref_id: {} for ref_id in source_dirs}

    for fw, test_files in framework_files.items():
        for test_file in test_files:
            matched_nodes = _map_test_file_to_nodes(
                test_file,
                fw,
                source_dirs,
                project_root,
            )
            for ref_id in matched_nodes:
                if fw not in node_tests[ref_id]:
                    node_tests[ref_id][fw] = []
                if test_file not in node_tests[ref_id][fw]:
                    node_tests[ref_id][fw].append(test_file)

    # Step 4: Build TestMapping for each source node
    result: dict[str, TestMapping] = {}

    for ref_id in source_dirs:
        fw_tests = node_tests[ref_id]

        if fw_tests:
            # Pick the framework with the most test files
            best_fw = max(fw_tests, key=lambda f: len(fw_tests[f]))
            all_test_files = fw_tests[best_fw]

            # Count test functions across all mapped test files
            total_test_count = 0
            for test_file in all_test_files:
                abs_path = project_root / test_file
                total_test_count += _count_tests_in_file(abs_path, best_fw)

            coverage = _estimate_coverage(len(all_test_files), framework_detected)

            result[ref_id] = TestMapping(
                framework=best_fw,
                test_files=sorted(all_test_files),
                test_count=total_test_count,
                coverage_estimate=coverage,
            )
        else:
            # No test files mapped to this node
            # Use the first detected framework or "none"
            fw = frameworks[0] if frameworks else "none"
            coverage = _estimate_coverage(0, framework_detected)

            result[ref_id] = TestMapping(
                framework=fw,
                test_files=[],
                test_count=0,
                coverage_estimate=coverage,
            )

    return result


# ---------------------------------------------------------------------------
# Parent aggregation: roll up child test counts to domain-level parents
# ---------------------------------------------------------------------------


def aggregate_parent_tests(
    mappings: dict[str, TestMapping],
    parent_children: dict[str, list[str]],
) -> dict[str, TestMapping]:
    """Aggregate child test counts up to parent nodes.

    For each parent in *parent_children* that has **no direct test files**,
    sums ``test_count`` and collects ``test_files`` from its children.

    Parameters
    ----------
    mappings:
        Existing per-node TestMapping dict (from :func:`map_tests`).
    parent_children:
        Mapping of parent ref_id -> list of child ref_ids.
        Typically built from ``part_of`` edges in the graph.

    Returns
    -------
    dict[str, TestMapping]
        Updated mappings with parent nodes having aggregated values.
    """
    if not mappings:
        return {}

    result = dict(mappings)

    for parent_id, children in parent_children.items():
        if parent_id not in result:
            continue
        parent_mapping = result[parent_id]
        # Only aggregate if parent has no direct test files
        if parent_mapping.test_files:
            continue

        total_count = 0
        all_files: list[str] = []
        for child_id in children:
            child_mapping = result.get(child_id)
            if child_mapping is None:
                continue
            total_count += child_mapping.test_count
            for f in child_mapping.test_files:
                if f not in all_files:
                    all_files.append(f)

        if total_count > 0 or all_files:
            coverage = _estimate_coverage(len(all_files), True)
            result[parent_id] = TestMapping(
                framework=parent_mapping.framework,
                test_files=sorted(all_files),
                test_count=total_count,
                coverage_estimate=coverage,
            )

    return result
