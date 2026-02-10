"""Tests for beadloom.presets — architecture preset definitions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.presets import (
    MICROSERVICES,
    MONOLITH,
    MONOREPO,
    PRESETS,
    detect_preset,
)

if TYPE_CHECKING:
    from pathlib import Path


class TestPresetClassifyDir:
    """Preset.classify_dir returns correct (kind, confidence)."""

    def test_monolith_models_entity(self) -> None:
        kind, conf = MONOLITH.classify_dir("models")
        assert kind == "entity"
        assert conf == "high"

    def test_monolith_api_feature(self) -> None:
        kind, conf = MONOLITH.classify_dir("api")
        assert kind == "feature"
        assert conf == "high"

    def test_monolith_services_service(self) -> None:
        kind, conf = MONOLITH.classify_dir("services")
        assert kind == "service"
        assert conf == "high"

    def test_monolith_utils_service(self) -> None:
        kind, conf = MONOLITH.classify_dir("utils")
        assert kind == "service"
        assert conf == "medium"

    def test_monolith_unknown_domain(self) -> None:
        kind, conf = MONOLITH.classify_dir("billing")
        assert kind == "domain"
        assert conf == "medium"

    def test_microservices_shared_domain(self) -> None:
        kind, conf = MICROSERVICES.classify_dir("shared")
        assert kind == "domain"
        assert conf == "high"

    def test_microservices_unknown_service(self) -> None:
        kind, conf = MICROSERVICES.classify_dir("auth-service")
        assert kind == "service"
        assert conf == "medium"

    def test_monorepo_lib_domain(self) -> None:
        kind, conf = MONOREPO.classify_dir("lib")
        assert kind == "domain"
        assert conf == "high"

    def test_entity_patterns(self) -> None:
        for name in ("models", "entities", "schemas", "database"):
            kind, _ = MONOLITH.classify_dir(name)
            assert kind == "entity", f"{name} should be entity"

    def test_feature_patterns(self) -> None:
        for name in ("api", "routes", "controllers", "handlers", "views"):
            kind, _ = MONOLITH.classify_dir(name)
            assert kind == "feature", f"{name} should be feature"


class TestDetectPreset:
    """detect_preset auto-detects architecture from directory structure."""

    def test_detect_monolith_default(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        preset = detect_preset(tmp_path)
        assert preset.name == "monolith"

    def test_detect_microservices_from_services(self, tmp_path: Path) -> None:
        (tmp_path / "services").mkdir()
        preset = detect_preset(tmp_path)
        assert preset.name == "microservices"

    def test_detect_microservices_from_cmd(self, tmp_path: Path) -> None:
        (tmp_path / "cmd").mkdir()
        preset = detect_preset(tmp_path)
        assert preset.name == "microservices"

    def test_detect_monorepo_from_packages(self, tmp_path: Path) -> None:
        (tmp_path / "packages").mkdir()
        preset = detect_preset(tmp_path)
        assert preset.name == "monorepo"

    def test_detect_monorepo_from_apps(self, tmp_path: Path) -> None:
        (tmp_path / "apps").mkdir()
        preset = detect_preset(tmp_path)
        assert preset.name == "monorepo"

    def test_empty_project_monolith(self, tmp_path: Path) -> None:
        preset = detect_preset(tmp_path)
        assert preset.name == "monolith"


class TestPresetsRegistry:
    """PRESETS dict contains all three presets."""

    def test_all_presets_registered(self) -> None:
        assert set(PRESETS.keys()) == {"monolith", "microservices", "monorepo"}

    def test_preset_names_match_keys(self) -> None:
        for key, preset in PRESETS.items():
            assert preset.name == key

    def test_presets_are_frozen(self) -> None:
        for preset in PRESETS.values():
            assert preset.__dataclass_params__.frozen  # type: ignore[attr-defined]
