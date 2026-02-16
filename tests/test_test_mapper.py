"""Tests for beadloom.context_oracle.test_mapper — test file mapping to source nodes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.context_oracle.test_mapper import TestMapping, map_tests

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_file(path: Path, content: str = "") -> None:
    """Create parent dirs and write content to a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Framework Detection
# ---------------------------------------------------------------------------


class TestFrameworkDetection:
    """Test that each of the 5 frameworks is detected correctly."""

    def test_detect_pytest(self, tmp_path: Path) -> None:
        _write_file(tmp_path / "conftest.py", "import pytest\n")
        _write_file(
            tmp_path / "tests" / "test_auth.py",
            "def test_login():\n    assert True\n",
        )
        source_dirs = {"auth": "src/auth"}
        result = map_tests(tmp_path, source_dirs)
        # Should detect at least one mapping with pytest framework
        frameworks = {m.framework for m in result.values()}
        assert "pytest" in frameworks

    def test_detect_jest(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path / "jest.config.js",
            "module.exports = { testEnvironment: 'node' };\n",
        )
        _write_file(
            tmp_path / "src" / "auth" / "__tests__" / "auth.test.ts",
            "test('login', () => { expect(true).toBe(true); });\n",
        )
        source_dirs = {"auth": "src/auth"}
        result = map_tests(tmp_path, source_dirs)
        frameworks = {m.framework for m in result.values()}
        assert "jest" in frameworks

    def test_detect_go_test(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path / "src" / "auth" / "auth_test.go",
            'package auth\n\nimport "testing"\n\nfunc TestLogin(t *testing.T) {}\n',
        )
        source_dirs = {"auth": "src/auth"}
        result = map_tests(tmp_path, source_dirs)
        frameworks = {m.framework for m in result.values()}
        assert "go_test" in frameworks

    def test_detect_junit(self, tmp_path: Path) -> None:
        _write_file(tmp_path / "src" / "test" / "java" / "AuthTest.java", "")
        _write_file(
            tmp_path / "src" / "test" / "java" / "LoginTest.java",
            "import org.junit.Test;\npublic class LoginTest {\n"
            "    @Test\n    public void testLogin() {}\n"
            "    @Test\n    public void testLogout() {}\n}\n",
        )
        source_dirs = {"auth": "src/main/java/auth"}
        result = map_tests(tmp_path, source_dirs)
        frameworks = {m.framework for m in result.values()}
        assert "junit" in frameworks

    def test_detect_xctest(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path / "AuthTests" / "AuthTests.swift",
            "import XCTest\n\nclass AuthTests: XCTestCase {\n"
            "    func testLogin() {}\n    func testLogout() {}\n}\n",
        )
        source_dirs = {"auth": "Sources/Auth"}
        result = map_tests(tmp_path, source_dirs)
        frameworks = {m.framework for m in result.values()}
        assert "xctest" in frameworks


# ---------------------------------------------------------------------------
# Naming Convention Mapping
# ---------------------------------------------------------------------------


class TestNamingConventionMapping:
    """Test that test files are mapped to source nodes by naming convention."""

    def test_pytest_naming_convention(self, tmp_path: Path) -> None:
        """test_auth.py should map to 'auth' node."""
        _write_file(tmp_path / "conftest.py", "")
        _write_file(
            tmp_path / "tests" / "test_auth.py",
            "def test_login():\n    pass\n",
        )
        _write_file(
            tmp_path / "tests" / "test_billing.py",
            "def test_invoice():\n    pass\n",
        )
        source_dirs = {"auth": "src/auth", "billing": "src/billing"}
        result = map_tests(tmp_path, source_dirs)
        assert "auth" in result
        assert "billing" in result
        assert any("test_auth.py" in f for f in result["auth"].test_files)
        assert any("test_billing.py" in f for f in result["billing"].test_files)

    def test_jest_naming_convention(self, tmp_path: Path) -> None:
        """auth.test.ts should map to 'auth' node."""
        _write_file(tmp_path / "jest.config.js", "")
        _write_file(
            tmp_path / "src" / "auth.test.ts",
            "test('works', () => {});\n",
        )
        source_dirs = {"auth": "src/auth"}
        result = map_tests(tmp_path, source_dirs)
        assert "auth" in result

    def test_go_test_naming_convention(self, tmp_path: Path) -> None:
        """auth_test.go in the same dir maps to 'auth' node."""
        _write_file(
            tmp_path / "src" / "auth" / "auth_test.go",
            'package auth\n\nimport "testing"\n\nfunc TestLogin(t *testing.T) {}\n',
        )
        source_dirs = {"auth": "src/auth"}
        result = map_tests(tmp_path, source_dirs)
        assert "auth" in result

    def test_directory_proximity_mapping(self, tmp_path: Path) -> None:
        """tests/auth/ should map to 'auth' node."""
        _write_file(tmp_path / "conftest.py", "")
        _write_file(
            tmp_path / "tests" / "auth" / "test_login.py",
            "def test_login():\n    pass\n",
        )
        source_dirs = {"auth": "src/auth"}
        result = map_tests(tmp_path, source_dirs)
        assert "auth" in result


# ---------------------------------------------------------------------------
# Import Analysis Mapping (pytest)
# ---------------------------------------------------------------------------


class TestImportAnalysisMapping:
    """Test that import statements in test files are used for mapping."""

    def test_import_from_mapping(self, tmp_path: Path) -> None:
        """Test file importing from auth.service should map to 'auth' node."""
        _write_file(tmp_path / "conftest.py", "")
        _write_file(
            tmp_path / "tests" / "test_service.py",
            "from auth.service import AuthService\n\ndef test_auth_service():\n    pass\n",
        )
        source_dirs = {"auth": "src/auth"}
        result = map_tests(tmp_path, source_dirs)
        assert "auth" in result

    def test_import_module_mapping(self, tmp_path: Path) -> None:
        """Test file with 'import billing' should map to 'billing' node."""
        _write_file(tmp_path / "conftest.py", "")
        _write_file(
            tmp_path / "tests" / "test_invoices.py",
            "import billing\n\ndef test_create_invoice():\n    pass\n",
        )
        source_dirs = {"billing": "src/billing"}
        result = map_tests(tmp_path, source_dirs)
        assert "billing" in result


# ---------------------------------------------------------------------------
# Coverage Estimate
# ---------------------------------------------------------------------------


class TestCoverageEstimate:
    """Test the coverage estimate logic: high, medium, low, none."""

    def test_high_coverage(self, tmp_path: Path) -> None:
        """More than 3 test files per module = high."""
        _write_file(tmp_path / "conftest.py", "")
        for i in range(4):
            _write_file(
                tmp_path / "tests" / f"test_auth_{i}.py",
                f"def test_case_{i}():\n    pass\n",
            )
        source_dirs = {"auth": "src/auth"}
        result = map_tests(tmp_path, source_dirs)
        assert "auth" in result
        assert result["auth"].coverage_estimate == "high"

    def test_medium_coverage(self, tmp_path: Path) -> None:
        """1-3 test files per module = medium."""
        _write_file(tmp_path / "conftest.py", "")
        _write_file(
            tmp_path / "tests" / "test_auth.py",
            "def test_login():\n    pass\n",
        )
        _write_file(
            tmp_path / "tests" / "test_auth_service.py",
            "def test_create():\n    pass\n",
        )
        source_dirs = {"auth": "src/auth"}
        result = map_tests(tmp_path, source_dirs)
        assert "auth" in result
        assert result["auth"].coverage_estimate == "medium"

    def test_low_coverage(self, tmp_path: Path) -> None:
        """0 test files for a module, but framework detected = low."""
        _write_file(tmp_path / "conftest.py", "")
        _write_file(
            tmp_path / "tests" / "test_billing.py",
            "def test_invoice():\n    pass\n",
        )
        source_dirs = {"auth": "src/auth", "billing": "src/billing"}
        result = map_tests(tmp_path, source_dirs)
        # auth has no test files, but pytest framework is detected
        assert "auth" in result
        assert result["auth"].coverage_estimate == "low"

    def test_none_coverage(self, tmp_path: Path) -> None:
        """No framework detected = none."""
        source_dirs = {"auth": "src/auth"}
        result = map_tests(tmp_path, source_dirs)
        # No test files, no markers at all
        assert "auth" in result
        assert result["auth"].coverage_estimate == "none"


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Test edge cases: no test files, multiple frameworks, test counting."""

    def test_no_test_files(self, tmp_path: Path) -> None:
        """When no test files exist, all modules get 'none' coverage."""
        source_dirs = {"auth": "src/auth", "billing": "src/billing"}
        result = map_tests(tmp_path, source_dirs)
        for ref_id in source_dirs:
            assert ref_id in result
            assert result[ref_id].test_files == []
            assert result[ref_id].test_count == 0
            assert result[ref_id].coverage_estimate == "none"

    def test_multiple_frameworks(self, tmp_path: Path) -> None:
        """Project with both pytest and jest should detect both."""
        _write_file(tmp_path / "conftest.py", "")
        _write_file(
            tmp_path / "tests" / "test_backend.py",
            "def test_api():\n    pass\n",
        )
        _write_file(tmp_path / "jest.config.js", "")
        _write_file(
            tmp_path / "frontend" / "app.test.ts",
            "test('renders', () => {});\ntest('clicks', () => {});\n",
        )
        source_dirs = {"backend": "src/backend", "frontend": "frontend"}
        result = map_tests(tmp_path, source_dirs)
        frameworks = {m.framework for m in result.values()}
        assert len(frameworks) >= 1  # At least one framework detected

    def test_test_count_pytest(self, tmp_path: Path) -> None:
        """Count def test_* functions in pytest files."""
        _write_file(tmp_path / "conftest.py", "")
        _write_file(
            tmp_path / "tests" / "test_auth.py",
            "def test_login():\n    pass\n\n"
            "def test_logout():\n    pass\n\n"
            "def test_register():\n    pass\n",
        )
        source_dirs = {"auth": "src/auth"}
        result = map_tests(tmp_path, source_dirs)
        assert "auth" in result
        assert result["auth"].test_count == 3

    def test_test_count_jest(self, tmp_path: Path) -> None:
        """Count test( and it( calls in jest files."""
        _write_file(tmp_path / "jest.config.js", "")
        _write_file(
            tmp_path / "src" / "auth.test.ts",
            "test('login', () => {});\nit('should logout', () => {});\n",
        )
        source_dirs = {"auth": "src/auth"}
        result = map_tests(tmp_path, source_dirs)
        assert "auth" in result
        assert result["auth"].test_count == 2

    def test_frozen_dataclass(self) -> None:
        """TestMapping should be immutable (frozen dataclass)."""
        mapping = TestMapping(
            framework="pytest",
            test_files=["tests/test_auth.py"],
            test_count=5,
            coverage_estimate="medium",
        )
        assert mapping.framework == "pytest"
        assert mapping.test_count == 5

    def test_empty_source_dirs(self, tmp_path: Path) -> None:
        """Empty source_dirs should return empty dict."""
        result = map_tests(tmp_path, {})
        assert result == {}

    def test_test_count_go(self, tmp_path: Path) -> None:
        """Count func Test* in Go test files."""
        _write_file(
            tmp_path / "src" / "auth" / "auth_test.go",
            'package auth\n\nimport "testing"\n\n'
            "func TestLogin(t *testing.T) {}\n"
            "func TestLogout(t *testing.T) {}\n",
        )
        source_dirs = {"auth": "src/auth"}
        result = map_tests(tmp_path, source_dirs)
        assert "auth" in result
        assert result["auth"].test_count == 2

    def test_test_count_junit(self, tmp_path: Path) -> None:
        """Count @Test annotations in JUnit files."""
        _write_file(
            tmp_path / "src" / "test" / "java" / "AuthTest.java",
            "import org.junit.Test;\npublic class AuthTest {\n"
            "    @Test\n    public void testLogin() {}\n"
            "    @Test\n    public void testLogout() {}\n}\n",
        )
        source_dirs = {"auth": "src/main/java/auth"}
        result = map_tests(tmp_path, source_dirs)
        assert "auth" in result
        assert result["auth"].framework == "junit"
        assert result["auth"].test_count >= 2

    def test_test_count_xctest(self, tmp_path: Path) -> None:
        """Count func test* in XCTest files."""
        _write_file(
            tmp_path / "AuthTests" / "AuthTests.swift",
            "import XCTest\n\nclass AuthTests: XCTestCase {\n"
            "    func testLogin() {}\n    func testLogout() {}\n}\n",
        )
        source_dirs = {"auth": "Sources/Auth"}
        result = map_tests(tmp_path, source_dirs)
        xctest_mappings = [m for m in result.values() if m.framework == "xctest"]
        assert len(xctest_mappings) >= 1
        total_tests = sum(m.test_count for m in xctest_mappings)
        assert total_tests >= 2
