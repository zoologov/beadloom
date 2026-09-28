"""A test file that is not Python is counted by its language's test form (BDL-074 G2).

Review ``beadloom-b9ll`` M3: the retired mapper counted Go, JS/TS, JUnit and XCTest
test functions, and the reader that replaced it read Python only, so a Go test
beside its package counted as no test at all. The count is read by the file's
suffix, the imports of a non-Python file are not read, and a suffix the reader has
no form for counts zero rather than guessing.
"""

from __future__ import annotations

from beadloom.context_oracle.test_file_reader import read_test_file

GO_TEST = (
    "package billing\n\n"
    'import "testing"\n\n'
    "func TestTotal(t *testing.T) {}\n"
    "func TestRefund(t *testing.T) {}\n"
    "func helper() {}\n"
    "func BenchmarkTotal(b *testing.B) {}\n"
)

TS_TEST = (
    "import { total } from './cart';\n\n"
    "describe('cart', () => {\n"
    "  it('adds', () => { expect(total(1, 2)).toBe(3); });\n"
    "  test('empties', () => {});\n"
    "});\n"
)


class TestByLanguage:
    def test_go_counts_its_test_functions(self) -> None:
        contents = read_test_file(GO_TEST, suffix=".go")
        assert contents.test_count == 2
        assert contents.imports == ()

    def test_js_and_ts_count_their_it_and_test_calls(self) -> None:
        assert read_test_file(TS_TEST, suffix=".ts").test_count == 2
        assert read_test_file(TS_TEST, suffix=".jsx").test_count == 2

    def test_java_counts_its_annotated_tests(self) -> None:
        text = "class LedgerTest {\n  @Test\n  void posts() {}\n  @Test void voids() {}\n}\n"
        assert read_test_file(text, suffix=".java").test_count == 2

    def test_a_suffix_with_no_known_test_form_counts_zero(self) -> None:
        assert read_test_file("anything at all\n", suffix=".rb").test_count == 0

    def test_python_is_still_the_default(self) -> None:
        assert read_test_file("def test_a():\n    pass\n").test_count == 1
        assert read_test_file("def test_a():\n    pass\n", suffix=".py").test_count == 1
