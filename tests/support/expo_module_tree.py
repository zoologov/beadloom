"""A synthetic Expo app with two local Expo modules (BDL-080 S3b, RFC D5 (e)).

The app is shaped as a React Native project in the Feature-Sliced layout: Expo Router's
``app/`` at the root, the FSD layers under ``src/``, and two local Expo modules under
``modules/``, each a folder holding ``expo-module.config.json`` beside its TypeScript:

- ``haptic-pulse`` is linked on both platforms and declares them with the keys Expo has
  written since SDK 50: ``apple.modules`` for the Swift class in ``ios/`` and
  ``android.modules`` for the Kotlin class in ``android/``, which Gradle builds as a
  library (``android/build.gradle``, ``src/main/java``);
- ``screen-lock`` is linked on iOS only and uses the earlier key ``ios.modules``.

No import joins a module's TypeScript to its native code: ``requireNativeModule`` names
the module by a string, and the native side registers under that string. The config is
the only place the bridge is written down.

Synthetic names only (CONTEXT: no owner project name in a committed artifact).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

#: The module folder each module lives in, by name.
HAPTIC_PULSE = "modules/haptic-pulse"
SCREEN_LOCK = "modules/screen-lock"

EXPO_APP_TREE: dict[str, str] = {
    "package.json": (
        "{\n"
        '  "name": "pathfinder-app",\n'
        '  "main": "expo-router/entry",\n'
        '  "dependencies": {"expo": "52.0.0", "react-native": "0.76.0"}\n'
        "}\n"
    ),
    "tsconfig.json": (
        '{"extends": "expo/tsconfig.base", "compilerOptions": {"paths": {"@/*": ["./*"]}}}\n'
    ),
    "app/_layout.tsx": (
        "import { Pulse } from '@/src/features/pulse'\n"
        "export default function Layout() { return Pulse }\n"
    ),
    "src/app/providers/index.ts": "export const providers = []\n",
    "src/pages/home/index.ts": (
        "import { Pulse } from '@/src/features/pulse'\nexport const Home = Pulse\n"
    ),
    "src/features/pulse/index.ts": "export { Pulse } from './ui/Pulse'\n",
    "src/features/pulse/ui/Pulse.tsx": (
        "import HapticPulse from '@/modules/haptic-pulse'\n"
        "import { lockScreen } from '@/modules/screen-lock'\n"
        "export const Pulse = [HapticPulse, lockScreen]\n"
    ),
    "src/entities/user/index.ts": "export const user = 1\n",
    "src/shared/lib/index.ts": "export const noop = () => {}\n",
    f"{HAPTIC_PULSE}/expo-module.config.json": (
        "{\n"
        '  "platforms": ["apple", "android", "web"],\n'
        '  "apple": {"modules": ["HapticPulseModule"]},\n'
        '  "android": {"modules": ["expo.modules.hapticpulse.HapticPulseModule"]}\n'
        "}\n"
    ),
    f"{HAPTIC_PULSE}/index.ts": "export { default } from './src/HapticPulseModule'\n",
    f"{HAPTIC_PULSE}/src/HapticPulseModule.ts": (
        "import { requireNativeModule } from 'expo'\n"
        "export default requireNativeModule('HapticPulse')\n"
    ),
    f"{HAPTIC_PULSE}/src/HapticPulseModule.web.ts": "export default { pulse() {} }\n",
    f"{HAPTIC_PULSE}/ios/HapticPulse.podspec": (
        "Pod::Spec.new do |s|\n  s.name = 'HapticPulse'\nend\n"
    ),
    f"{HAPTIC_PULSE}/ios/HapticPulseModule.swift": (
        "import ExpoModulesCore\n\n"
        "public class HapticPulseModule: Module {\n"
        "  public func definition() -> ModuleDefinition {\n"
        '    Name("HapticPulse")\n'
        "  }\n"
        "}\n"
    ),
    f"{HAPTIC_PULSE}/android/build.gradle": "apply plugin: 'com.android.library'\n",
    f"{HAPTIC_PULSE}/android/src/main/java/expo/modules/hapticpulse/HapticPulseModule.kt": (
        "package expo.modules.hapticpulse\n\n"
        "import expo.modules.kotlin.modules.Module\n"
        "import expo.modules.kotlin.modules.ModuleDefinition\n\n"
        "class HapticPulseModule : Module() {\n"
        '  override fun definition() = ModuleDefinition { Name("HapticPulse") }\n'
        "}\n"
    ),
    f"{SCREEN_LOCK}/expo-module.config.json": (
        '{"platforms": ["ios"], "ios": {"modules": ["ScreenLockModule"]}}\n'
    ),
    f"{SCREEN_LOCK}/index.ts": (
        "import { requireNativeModule } from 'expo-modules-core'\n"
        "const native = requireNativeModule('ScreenLock')\n"
        "export function lockScreen() { return native.lock() }\n"
    ),
    f"{SCREEN_LOCK}/ios/ScreenLockModule.swift": (
        "import ExpoModulesCore\n\n"
        "public class ScreenLockModule: Module {\n"
        '  public func definition() -> ModuleDefinition { Name("ScreenLock") }\n'
        "}\n"
    ),
}


def write_tree(root: Path, tree: dict[str, str]) -> Path:
    """Write *tree*, project-relative path to text, under *root* and return *root*."""
    for rel_path, text in tree.items():
        path = root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


def write_expo_app(root: Path) -> Path:
    """Write :data:`EXPO_APP_TREE` under *root* and return *root*."""
    return write_tree(root, EXPO_APP_TREE)
