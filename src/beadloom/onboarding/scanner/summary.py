"""Framework-aware cluster summaries (detection + context-rich assembly)."""

# beadloom:domain=onboarding
# beadloom:feature=agent-prime

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.onboarding.scanner.readme import _extract_first_paragraph

if TYPE_CHECKING:
    from pathlib import Path


def _detect_framework_summary(
    dir_path: Path,
    name: str,
    kind: str,
    file_count: int,
) -> str:
    """Detect framework patterns and return a descriptive summary.

    Checks for known framework markers in the directory and returns
    a framework-aware summary instead of the generic "Kind: name (N files)".
    Summaries are kept under 120 characters.

    Detection order: most specific to least specific to avoid false positives.
    """

    def _safe_read(path: Path) -> str:
        """Read file text, returning empty string on errors."""
        try:
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return ""

    # --- Highly specific: unique config/marker files ---

    # NestJS: nest-cli.json or *.module.ts pattern
    if (dir_path / "nest-cli.json").exists() or list(dir_path.glob("*.module.ts")):
        return f"NestJS module: {name} ({file_count} files)"

    # Angular: angular.json or *.component.ts pattern
    if (dir_path / "angular.json").exists() or list(dir_path.glob("*.component.ts")):
        return f"Angular app: {name} ({file_count} files)"

    # Next.js: next.config.js / next.config.mjs / next.config.ts
    if (
        (dir_path / "next.config.js").exists()
        or (dir_path / "next.config.mjs").exists()
        or (dir_path / "next.config.ts").exists()
    ):
        return f"Next.js app: {name} ({file_count} files)"

    # Expo / React Native: app.json with "expo" key or react-native in package.json
    app_json = dir_path / "app.json"
    if app_json.exists():
        app_json_text = _safe_read(app_json)
        if '"expo"' in app_json_text:
            return f"Expo app: {name} ({file_count} files)"

    pkg_json = dir_path / "package.json"
    if pkg_json.exists():
        pkg_text = _safe_read(pkg_json)
        if '"react-native"' in pkg_text:
            return f"React Native app: {name} ({file_count} files)"

    # Django app: contains apps.py
    if (dir_path / "apps.py").exists():
        return f"Django app: {name} ({file_count} files)"

    # Spring Boot: pom.xml or build.gradle with spring-boot
    pom_xml = dir_path / "pom.xml"
    if pom_xml.exists():
        pom_text = _safe_read(pom_xml)
        if "spring-boot" in pom_text:
            return f"Spring Boot service: {name} ({file_count} files)"

    build_gradle = dir_path / "build.gradle"
    if build_gradle.exists():
        gradle_text = _safe_read(build_gradle)
        if "spring-boot" in gradle_text or "springframework.boot" in gradle_text:
            return f"Spring Boot service: {name} ({file_count} files)"

    # Actix: Cargo.toml with actix-web
    cargo_toml = dir_path / "Cargo.toml"
    if cargo_toml.exists():
        cargo_text = _safe_read(cargo_toml)
        if "actix-web" in cargo_text:
            return f"Actix service: {name} ({file_count} files)"

    # FastAPI: main.py or app.py with FastAPI imports, or manifest with fastapi
    for entry_file in ("main.py", "app.py"):
        entry = dir_path / entry_file
        if entry.exists():
            entry_text = _safe_read(entry)
            if "FastAPI" in entry_text or "fastapi" in entry_text:
                return f"FastAPI service: {name} ({file_count} files)"

    req_txt = dir_path / "requirements.txt"
    if req_txt.exists():
        req_text = _safe_read(req_txt)
        if "fastapi" in req_text.lower():
            return f"FastAPI service: {name} ({file_count} files)"

    pyproject = dir_path / "pyproject.toml"
    if pyproject.exists():
        pyproject_text = _safe_read(pyproject)
        if "fastapi" in pyproject_text.lower():
            return f"FastAPI service: {name} ({file_count} files)"

    # Flask: app.py with Flask pattern, or requirements.txt with flask
    flask_app = dir_path / "app.py"
    if flask_app.exists():
        flask_text = _safe_read(flask_app)
        if "Flask" in flask_text or "flask" in flask_text:
            return f"Flask app: {name} ({file_count} files)"

    if req_txt.exists():
        req_text = _safe_read(req_txt)
        if "flask" in req_text.lower():
            return f"Flask app: {name} ({file_count} files)"

    # Express: package.json with express dependency
    if pkg_json.exists():
        pkg_text = _safe_read(pkg_json)
        if '"express"' in pkg_text:
            return f"Express service: {name} ({file_count} files)"

    # Vue: *.vue files or vue.config.js
    if (dir_path / "vue.config.js").exists() or list(dir_path.glob("*.vue")):
        return f"Vue app: {name} ({file_count} files)"

    # Gin: Go files with gin-gonic/gin import
    go_files = list(dir_path.glob("*.go"))
    if go_files:
        for go_file in go_files:
            go_text = _safe_read(go_file)
            if "github.com/gin-gonic/gin" in go_text:
                return f"Gin service: {name} ({file_count} files)"

    # SwiftUI: .swift files with import SwiftUI
    swift_files = list(dir_path.glob("*.swift"))
    if swift_files:
        for sf in swift_files:
            sf_text = _safe_read(sf)
            if "import SwiftUI" in sf_text:
                return f"SwiftUI app: {name} ({file_count} files)"

    # Jetpack Compose: .kt files with import androidx.compose
    kt_files = list(dir_path.glob("*.kt"))
    if kt_files:
        for kf in kt_files:
            kf_text = _safe_read(kf)
            if "import androidx.compose" in kf_text:
                return f"Jetpack Compose app: {name} ({file_count} files)"

    # UIKit: .swift or .m files with import UIKit
    uikit_files = list(dir_path.glob("*.swift")) + list(dir_path.glob("*.m"))
    if uikit_files:
        for uf in uikit_files:
            uf_text = _safe_read(uf)
            if "import UIKit" in uf_text:
                return f"UIKit app: {name} ({file_count} files)"

    # React component: contains index.tsx or index.jsx
    if (dir_path / "index.tsx").exists() or (dir_path / "index.jsx").exists():
        return f"React component: {name} ({file_count} files)"

    # Python package: contains __init__.py + (setup.py or pyproject.toml)
    if (dir_path / "__init__.py").exists() and (
        (dir_path / "setup.py").exists() or (dir_path / "pyproject.toml").exists()
    ):
        return f"Python package: {name} ({file_count} files)"

    # Containerized service: contains Dockerfile
    if (dir_path / "Dockerfile").exists():
        return f"Containerized service: {name} ({file_count} files)"

    # Default: use kind label
    kind_label = kind.capitalize()
    return f"{kind_label}: {name} ({file_count} files)"


# Maximum files to scan for symbols per cluster (performance guard).
_SUMMARY_MAX_SYMBOL_FILES = 20


def _build_contextual_summary(
    dir_path: Path,
    name: str,
    kind: str,
    files: list[str],
    project_root: Path,
    entry_points: list[dict[str, str]] | None = None,
) -> str:
    """Build a context-rich summary for a cluster node.

    Combines:
    - Framework detection (via ``_detect_framework_summary``)
    - Key symbol counts (classes, functions) from source files
    - README excerpt from the directory
    - Entry point information

    Returns a summary string under 120 characters.

    Example: ``"FastAPI service: auth — JWT auth, 3 classes, 5 functions"``
    """
    file_count = len(files)

    # 1. Get framework-aware base summary (e.g. "FastAPI service: auth (5 files)").
    base = _detect_framework_summary(dir_path, name, kind, file_count)

    # Extract the prefix (everything before the parenthesized file count).
    # e.g. "FastAPI service: auth" from "FastAPI service: auth (5 files)"
    paren_idx = base.rfind(" (")
    prefix = base[:paren_idx] if paren_idx > 0 else base

    # 2. Count symbols from code files using tree-sitter.
    class_count = 0
    function_count = 0
    if files:
        try:
            from beadloom.context_oracle.code_indexer import extract_symbols
        except ImportError:
            extract_symbols = None  # type: ignore[assignment]

        if extract_symbols is not None:
            for rel_path in files[:_SUMMARY_MAX_SYMBOL_FILES]:
                abs_path = project_root / rel_path
                if not abs_path.is_file():
                    continue
                try:
                    symbols = extract_symbols(abs_path)
                except Exception:  # noqa: S112
                    continue
                for sym in symbols:
                    if sym["kind"] == "class":
                        class_count += 1
                    elif sym["kind"] == "function":
                        function_count += 1

    # 3. Read per-directory README excerpt.
    readme_excerpt = ""
    for readme_name in ("README.md", "readme.md", "README.rst"):
        readme_path = dir_path / readme_name
        if readme_path.is_file():
            try:
                readme_text = readme_path.read_text(encoding="utf-8")
                readme_excerpt = _extract_first_paragraph(readme_text)
            except (OSError, UnicodeDecodeError):
                pass
            break

    # 4. Check for entry points relevant to this cluster.
    ep_labels: list[str] = []
    if entry_points:
        for ep in entry_points:
            ep_file = ep.get("file_path", "")
            # Check if the entry point file belongs to this cluster.
            for f in files:
                if ep_file == f:
                    ep_kind = ep.get("kind", "")
                    if ep_kind == "cli":
                        ep_labels.append("CLI entry")
                    elif ep_kind == "server":
                        ep_labels.append("server entry")
                    elif ep_kind == "app":
                        ep_labels.append("app entry")
                    break

    # 5. Assemble detail fragments.
    details: list[str] = []

    # README excerpt (truncated to fit).
    if readme_excerpt:
        # Truncate to ~50 chars to leave room for other details.
        if len(readme_excerpt) > 50:
            readme_excerpt = readme_excerpt[:47] + "..."
        details.append(readme_excerpt)

    # Entry point labels.
    if ep_labels:
        details.extend(ep_labels[:2])  # At most 2 entry point labels.

    # Symbol counts.
    sym_parts: list[str] = []
    if class_count:
        sym_parts.append(f"{class_count} class{'es' if class_count != 1 else ''}")
    if function_count:
        sym_parts.append(f"{function_count} fn{'s' if function_count != 1 else ''}")
    if sym_parts:
        details.append(", ".join(sym_parts))

    # 6. Build final summary.
    if details:
        detail_str = ", ".join(details)
        summary = f"{prefix} — {detail_str}"
    else:
        # No extra details — use the base summary as-is.
        summary = base

    # Enforce 120-char limit.
    if len(summary) > 120:
        summary = summary[:117] + "..."

    return summary
