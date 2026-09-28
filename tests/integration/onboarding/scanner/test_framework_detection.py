"""Tests for _detect_framework_summary() in beadloom.onboarding.scanner."""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.onboarding.scanner import _detect_framework_summary

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Existing 4 framework detections (regression tests)
# ---------------------------------------------------------------------------


class TestExistingFrameworks:
    """Verify the original 4 framework detections still work."""

    def test_django_app(self, tmp_path: Path) -> None:
        (tmp_path / "apps.py").write_text("class MyConfig(AppConfig): pass\n")
        result = _detect_framework_summary(tmp_path, "auth", "domain", 10)
        assert result == "Django app: auth (10 files)"

    def test_react_component_tsx(self, tmp_path: Path) -> None:
        (tmp_path / "index.tsx").write_text("export default function App() {}\n")
        result = _detect_framework_summary(tmp_path, "header", "feature", 3)
        assert result == "React component: header (3 files)"

    def test_react_component_jsx(self, tmp_path: Path) -> None:
        (tmp_path / "index.jsx").write_text("export default function App() {}\n")
        result = _detect_framework_summary(tmp_path, "sidebar", "feature", 5)
        assert result == "React component: sidebar (5 files)"

    def test_python_package(self, tmp_path: Path) -> None:
        (tmp_path / "__init__.py").write_text("")
        (tmp_path / "setup.py").write_text("from setuptools import setup\n")
        result = _detect_framework_summary(tmp_path, "mylib", "service", 20)
        assert result == "Python package: mylib (20 files)"

    def test_python_package_pyproject(self, tmp_path: Path) -> None:
        (tmp_path / "__init__.py").write_text("")
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "mylib"\n')
        result = _detect_framework_summary(tmp_path, "mylib", "service", 12)
        assert result == "Python package: mylib (12 files)"

    def test_containerized_service(self, tmp_path: Path) -> None:
        (tmp_path / "Dockerfile").write_text("FROM python:3.11\n")
        result = _detect_framework_summary(tmp_path, "api", "service", 8)
        assert result == "Containerized service: api (8 files)"


# ---------------------------------------------------------------------------
# New framework detections
# ---------------------------------------------------------------------------


class TestFastAPI:
    def test_fastapi_main_py(self, tmp_path: Path) -> None:
        (tmp_path / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n")
        result = _detect_framework_summary(tmp_path, "api", "service", 15)
        assert result == "FastAPI service: api (15 files)"

    def test_fastapi_app_py(self, tmp_path: Path) -> None:
        (tmp_path / "app.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n")
        result = _detect_framework_summary(tmp_path, "backend", "service", 10)
        assert result == "FastAPI service: backend (10 files)"

    def test_fastapi_requirements(self, tmp_path: Path) -> None:
        (tmp_path / "requirements.txt").write_text("fastapi==0.100.0\nuvicorn\n")
        result = _detect_framework_summary(tmp_path, "api", "service", 5)
        assert result == "FastAPI service: api (5 files)"

    def test_fastapi_pyproject(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text('[project]\ndependencies = ["fastapi>=0.100"]\n')
        result = _detect_framework_summary(tmp_path, "svc", "service", 7)
        assert result == "FastAPI service: svc (7 files)"


class TestFlask:
    def test_flask_app_py(self, tmp_path: Path) -> None:
        (tmp_path / "app.py").write_text("from flask import Flask\napp = Flask(__name__)\n")
        result = _detect_framework_summary(tmp_path, "web", "service", 12)
        assert result == "Flask app: web (12 files)"

    def test_flask_requirements(self, tmp_path: Path) -> None:
        (tmp_path / "requirements.txt").write_text("flask==3.0\ngunicorn\n")
        result = _detect_framework_summary(tmp_path, "web", "service", 6)
        assert result == "Flask app: web (6 files)"


class TestExpress:
    def test_express_package_json(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(
            '{"name": "api", "dependencies": {"express": "^4.18.0"}}\n'
        )
        result = _detect_framework_summary(tmp_path, "api", "service", 20)
        assert result == "Express service: api (20 files)"


class TestNestJS:
    def test_nestjs_cli_json(self, tmp_path: Path) -> None:
        (tmp_path / "nest-cli.json").write_text('{"language": "ts"}\n')
        result = _detect_framework_summary(tmp_path, "backend", "service", 30)
        assert result == "NestJS module: backend (30 files)"

    def test_nestjs_module_ts(self, tmp_path: Path) -> None:
        (tmp_path / "app.module.ts").write_text("import { Module } from '@nestjs/common';\n")
        result = _detect_framework_summary(tmp_path, "app", "service", 25)
        assert result == "NestJS module: app (25 files)"


class TestNextJS:
    def test_nextjs_config_js(self, tmp_path: Path) -> None:
        (tmp_path / "next.config.js").write_text("module.exports = {}\n")
        result = _detect_framework_summary(tmp_path, "frontend", "service", 40)
        assert result == "Next.js app: frontend (40 files)"

    def test_nextjs_config_mjs(self, tmp_path: Path) -> None:
        (tmp_path / "next.config.mjs").write_text("export default {}\n")
        result = _detect_framework_summary(tmp_path, "web", "service", 35)
        assert result == "Next.js app: web (35 files)"

    def test_nextjs_config_ts(self, tmp_path: Path) -> None:
        (tmp_path / "next.config.ts").write_text("export default {}\n")
        result = _detect_framework_summary(tmp_path, "site", "service", 22)
        assert result == "Next.js app: site (22 files)"


class TestVue:
    def test_vue_files(self, tmp_path: Path) -> None:
        (tmp_path / "App.vue").write_text("<template><div>Hello</div></template>\n")
        result = _detect_framework_summary(tmp_path, "frontend", "feature", 18)
        assert result == "Vue app: frontend (18 files)"

    def test_vue_config_js(self, tmp_path: Path) -> None:
        (tmp_path / "vue.config.js").write_text("module.exports = {}\n")
        result = _detect_framework_summary(tmp_path, "client", "service", 25)
        assert result == "Vue app: client (25 files)"


class TestSpringBoot:
    def test_spring_boot_pom(self, tmp_path: Path) -> None:
        (tmp_path / "pom.xml").write_text(
            "<project><parent>"
            "<groupId>org.springframework.boot</groupId>"
            "<artifactId>spring-boot-starter-parent</artifactId>"
            "</parent></project>\n"
        )
        result = _detect_framework_summary(tmp_path, "orders", "service", 50)
        assert result == "Spring Boot service: orders (50 files)"

    def test_spring_boot_gradle(self, tmp_path: Path) -> None:
        (tmp_path / "build.gradle").write_text(
            "plugins {\n  id 'org.springframework.boot' version '3.1.0'\n}\n"
        )
        result = _detect_framework_summary(tmp_path, "users", "service", 30)
        assert result == "Spring Boot service: users (30 files)"


class TestGin:
    def test_gin_go_file(self, tmp_path: Path) -> None:
        (tmp_path / "main.go").write_text(
            'package main\n\nimport "github.com/gin-gonic/gin"\n\nfunc main() {}\n'
        )
        result = _detect_framework_summary(tmp_path, "api", "service", 15)
        assert result == "Gin service: api (15 files)"


class TestActix:
    def test_actix_cargo_toml(self, tmp_path: Path) -> None:
        (tmp_path / "Cargo.toml").write_text(
            '[package]\nname = "api"\n\n[dependencies]\nactix-web = "4"\n'
        )
        result = _detect_framework_summary(tmp_path, "api", "service", 10)
        assert result == "Actix service: api (10 files)"


class TestExpoReactNative:
    def test_expo_app_json(self, tmp_path: Path) -> None:
        (tmp_path / "app.json").write_text('{"expo": {"name": "myapp"}}\n')
        result = _detect_framework_summary(tmp_path, "mobile", "service", 30)
        assert result == "Expo app: mobile (30 files)"

    def test_react_native_package_json(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(
            '{"name": "app", "dependencies": {"react-native": "0.72.0"}}\n'
        )
        result = _detect_framework_summary(tmp_path, "mobile", "service", 25)
        assert result == "React Native app: mobile (25 files)"


class TestSwiftUI:
    def test_swiftui_import(self, tmp_path: Path) -> None:
        (tmp_path / "ContentView.swift").write_text(
            "import SwiftUI\n\nstruct ContentView: View {\n"
            '    var body: some View { Text("Hello") }\n}\n'
        )
        result = _detect_framework_summary(tmp_path, "app", "feature", 8)
        assert result == "SwiftUI app: app (8 files)"


class TestJetpackCompose:
    def test_compose_import(self, tmp_path: Path) -> None:
        (tmp_path / "MainActivity.kt").write_text(
            'import androidx.compose.material3.Text\n\nfun Greeting() { Text("Hello") }\n'
        )
        result = _detect_framework_summary(tmp_path, "ui", "feature", 12)
        assert result == "Jetpack Compose app: ui (12 files)"


class TestUIKit:
    def test_uikit_swift(self, tmp_path: Path) -> None:
        (tmp_path / "ViewController.swift").write_text(
            "import UIKit\n\nclass ViewController: UIViewController {}\n"
        )
        result = _detect_framework_summary(tmp_path, "screens", "feature", 6)
        assert result == "UIKit app: screens (6 files)"

    def test_uikit_objc(self, tmp_path: Path) -> None:
        (tmp_path / "AppDelegate.m").write_text(
            "#import <UIKit/UIKit.h>\nimport UIKit\n@implementation AppDelegate\n@end\n"
        )
        result = _detect_framework_summary(tmp_path, "legacy", "feature", 4)
        assert result == "UIKit app: legacy (4 files)"


class TestAngular:
    def test_angular_json(self, tmp_path: Path) -> None:
        (tmp_path / "angular.json").write_text('{"version": 1}\n')
        result = _detect_framework_summary(tmp_path, "dashboard", "service", 50)
        assert result == "Angular app: dashboard (50 files)"

    def test_angular_component_ts(self, tmp_path: Path) -> None:
        (tmp_path / "app.component.ts").write_text("import { Component } from '@angular/core';\n")
        result = _detect_framework_summary(tmp_path, "admin", "service", 15)
        assert result == "Angular app: admin (15 files)"


# ---------------------------------------------------------------------------
# Fallback (no framework match)
# ---------------------------------------------------------------------------


class TestFallback:
    def test_kind_based_fallback(self, tmp_path: Path) -> None:
        """When no framework is detected, use kind-based summary."""
        result = _detect_framework_summary(tmp_path, "utils", "domain", 5)
        assert result == "Domain: utils (5 files)"

    def test_kind_capitalization(self, tmp_path: Path) -> None:
        result = _detect_framework_summary(tmp_path, "core", "service", 10)
        assert result == "Service: core (10 files)"

    def test_feature_kind_fallback(self, tmp_path: Path) -> None:
        result = _detect_framework_summary(tmp_path, "search", "feature", 3)
        assert result == "Feature: search (3 files)"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_summary_under_120_chars(self, tmp_path: Path) -> None:
        """All summaries must be under 120 characters."""
        long_name = "a" * 80
        result = _detect_framework_summary(tmp_path, long_name, "domain", 999)
        assert len(result) < 120

    def test_empty_directory(self, tmp_path: Path) -> None:
        """Empty directory falls back to kind-based summary."""
        result = _detect_framework_summary(tmp_path, "empty", "domain", 0)
        assert result == "Domain: empty (0 files)"

    def test_unreadable_file_handled(self, tmp_path: Path) -> None:
        """Files with encoding issues are handled gracefully."""
        # Create a binary file that will fail UTF-8 decode
        (tmp_path / "main.py").write_bytes(b"\xff\xfe" + b"\x00" * 100)
        # Should not raise — falls through to fallback
        result = _detect_framework_summary(tmp_path, "svc", "service", 5)
        assert isinstance(result, str)
        assert "svc" in result

    def test_priority_nestjs_over_angular(self, tmp_path: Path) -> None:
        """NestJS should take priority over Angular when both match."""
        (tmp_path / "nest-cli.json").write_text("{}")
        (tmp_path / "angular.json").write_text("{}")
        result = _detect_framework_summary(tmp_path, "api", "service", 10)
        assert result.startswith("NestJS")

    def test_priority_fastapi_over_flask(self, tmp_path: Path) -> None:
        """FastAPI in app.py should take priority over Flask."""
        (tmp_path / "app.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n")
        result = _detect_framework_summary(tmp_path, "api", "service", 10)
        assert result.startswith("FastAPI")

    def test_priority_expo_over_react_native(self, tmp_path: Path) -> None:
        """Expo detection should take priority when app.json has expo key."""
        (tmp_path / "app.json").write_text('{"expo": {"name": "myapp"}}')
        (tmp_path / "package.json").write_text('{"dependencies": {"react-native": "0.72"}}')
        result = _detect_framework_summary(tmp_path, "app", "service", 20)
        assert result.startswith("Expo")

    def test_priority_swiftui_over_uikit(self, tmp_path: Path) -> None:
        """SwiftUI detection should take priority over UIKit."""
        (tmp_path / "ContentView.swift").write_text("import SwiftUI\n")
        (tmp_path / "Legacy.swift").write_text("import UIKit\n")
        result = _detect_framework_summary(tmp_path, "app", "feature", 5)
        assert result.startswith("SwiftUI")
