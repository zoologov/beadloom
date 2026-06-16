"""Application entry-point discovery across source directories."""

# beadloom:domain=onboarding
# beadloom:feature=agent-prime

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from beadloom.onboarding.scanner.constants import _RECURSIVE_SKIP

if TYPE_CHECKING:
    from pathlib import Path

# Entry-point detection patterns (compiled once).
_EP_IF_NAME_RE = re.compile(
    r"""if\s+__name__\s*==\s*['"]__main__['"]""",
)
_EP_CLICK_RE = re.compile(r"@click\.(command|group)")
_EP_TYPER_RE = re.compile(r"typer\.Typer\(\)")
_EP_ARGPARSE_RE = re.compile(r"argparse\.ArgumentParser")
_EP_GO_MAIN_RE = re.compile(r"func\s+main\(\)")
_EP_RUST_MAIN_RE = re.compile(r"fn\s+main\(\)")
_EP_JAVA_MAIN_RE = re.compile(r"public\s+static\s+void\s+main")
_EP_KOTLIN_MAIN_RE = re.compile(r"fun\s+main\(")
_EP_SWIFT_MAIN_RE = re.compile(r"@main")
_EP_SERVER_RE = re.compile(r"(uvicorn\.run|app\.run\(|\.listen\()")

# Max files per extension to avoid slow scans.
_EP_MAX_FILES_PER_EXT = 50
# Max total entry points to return.
_EP_MAX_RESULTS = 20

# Extensions eligible for entry-point scanning.
_EP_EXTENSIONS: dict[str, str] = {
    ".py": "python",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".kt": "kotlin",
    ".swift": "swift",
    ".js": "javascript",
    ".ts": "typescript",
}


def _discover_entry_points(
    project_root: Path,
    source_dirs: list[str],
) -> list[dict[str, str]]:
    """Discover application entry points across source directories.

    Detects:
    - __main__.py files (Python CLI entry)
    - if __name__ == "__main__" blocks (Python scripts)
    - Click/Typer/argparse CLI definitions
    - main() in Go/Rust/Java/Kotlin files
    - @main in Swift
    - Server bootstrap patterns (uvicorn, gunicorn, express.listen, etc.)

    Returns list of dicts with: file_path (relative), kind (cli|script|server|app),
    description.
    """
    results: list[dict[str, str]] = []
    seen_paths: set[str] = set()

    def _add(rel: str, kind: str, desc: str) -> None:
        if rel not in seen_paths and len(results) < _EP_MAX_RESULTS:
            seen_paths.add(rel)
            results.append({"file_path": rel, "kind": kind, "description": desc})

    # Collect files per extension, capped.
    files_by_ext: dict[str, list[Path]] = {}
    for sd_name in source_dirs:
        sd = project_root / sd_name
        if not sd.is_dir():
            continue
        for f in sd.rglob("*"):
            if not f.is_file():
                continue
            if any(part in _RECURSIVE_SKIP for part in f.relative_to(project_root).parts):
                continue
            ext = f.suffix
            if ext not in _EP_EXTENSIONS:
                continue
            bucket = files_by_ext.setdefault(ext, [])
            if len(bucket) < _EP_MAX_FILES_PER_EXT:
                bucket.append(f)

    # 1. Python __main__.py detection (file existence).
    for py_file in files_by_ext.get(".py", []):
        if py_file.name == "__main__.py":
            rel = str(py_file.relative_to(project_root))
            _add(rel, "cli", "Python CLI entry (__main__.py)")

    # 2-5. Python content patterns.
    for py_file in files_by_ext.get(".py", []):
        if len(results) >= _EP_MAX_RESULTS:
            break
        rel = str(py_file.relative_to(project_root))
        if rel in seen_paths:
            continue
        try:
            text = py_file.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeDecodeError):
            continue

        # Click CLI.
        if _EP_CLICK_RE.search(text):
            _add(rel, "cli", "Click CLI definition")
            continue
        # Typer CLI.
        if _EP_TYPER_RE.search(text):
            _add(rel, "cli", "Typer CLI definition")
            continue
        # argparse CLI.
        if _EP_ARGPARSE_RE.search(text):
            _add(rel, "cli", "argparse CLI definition")
            continue
        # Server bootstrap.
        if _EP_SERVER_RE.search(text):
            _add(rel, "server", "Server bootstrap (Python)")
            continue
        # if __name__ == "__main__".
        if _EP_IF_NAME_RE.search(text):
            _add(rel, "script", 'Python script (if __name__ == "__main__")')
            continue

    # 6. Go main.
    for go_file in files_by_ext.get(".go", []):
        if len(results) >= _EP_MAX_RESULTS:
            break
        try:
            text = go_file.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeDecodeError):
            continue
        if _EP_GO_MAIN_RE.search(text):
            rel = str(go_file.relative_to(project_root))
            _add(rel, "app", "Go application entry (func main)")

    # 7. Rust main.
    for rs_file in files_by_ext.get(".rs", []):
        if len(results) >= _EP_MAX_RESULTS:
            break
        if rs_file.name != "main.rs":
            continue
        try:
            text = rs_file.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeDecodeError):
            continue
        if _EP_RUST_MAIN_RE.search(text):
            rel = str(rs_file.relative_to(project_root))
            _add(rel, "app", "Rust application entry (fn main)")

    # 8. Java main.
    for java_file in files_by_ext.get(".java", []):
        if len(results) >= _EP_MAX_RESULTS:
            break
        try:
            text = java_file.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeDecodeError):
            continue
        if _EP_JAVA_MAIN_RE.search(text):
            rel = str(java_file.relative_to(project_root))
            _add(rel, "app", "Java application entry (public static void main)")

    # 9. Kotlin main.
    for kt_file in files_by_ext.get(".kt", []):
        if len(results) >= _EP_MAX_RESULTS:
            break
        try:
            text = kt_file.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeDecodeError):
            continue
        if _EP_KOTLIN_MAIN_RE.search(text):
            rel = str(kt_file.relative_to(project_root))
            _add(rel, "app", "Kotlin application entry (fun main)")

    # 10. Swift @main.
    for swift_file in files_by_ext.get(".swift", []):
        if len(results) >= _EP_MAX_RESULTS:
            break
        try:
            text = swift_file.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeDecodeError):
            continue
        if _EP_SWIFT_MAIN_RE.search(text):
            rel = str(swift_file.relative_to(project_root))
            _add(rel, "app", "Swift application entry (@main)")

    # 11. Server bootstrap in JS/TS.
    for ext in (".js", ".ts"):
        for js_file in files_by_ext.get(ext, []):
            if len(results) >= _EP_MAX_RESULTS:
                break
            try:
                text = js_file.read_text(encoding="utf-8", errors="replace")
            except (OSError, UnicodeDecodeError):
                continue
            if _EP_SERVER_RE.search(text):
                rel = str(js_file.relative_to(project_root))
                _add(rel, "server", "Server bootstrap (JS/TS)")

    return results
