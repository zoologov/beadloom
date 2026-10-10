"""``init``'s text scan of ``babel.config.js`` and ``vite.config.*`` for import aliases.

BDL-080 S3a (``beadloom-cwzc``), RFC D5 (b). The aliases a bundler applies live in a
program the resolver does not run. ``init`` reads them by a tolerant text scan — string
keys, the string literals of a value — writes what it found under ``imports.aliases:``
and says so, so the user confirms rather than trusts. What it cannot read (a regular
expression, a value built with no literal, a folder that is not there) it names.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.onboarding.scanner.alias_scan import scan_bundler_aliases

if TYPE_CHECKING:
    from pathlib import Path

_BABEL = """\
module.exports = function (api) {
  api.cache(true);
  return {
    presets: ['babel-preset-expo'],
    plugins: [
      [
        'module-resolver',
        {
          root: ['./'],
          // alias: { '@old': './old' },
          alias: {
            '@app': './src/app',
            "@shared": "./src/shared",
            '~': './src',
            '^@icons/(.+)': './assets/icons/\\\\1',
            gone: './src/gone',
          },
        },
      ],
    ],
  };
};
"""

_VITE = """\
import { fileURLToPath, URL } from 'node:url'
import path from 'node:path'
import { defineConfig } from 'vite'

export default defineConfig({
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
      '@shared': path.resolve(__dirname, 'src', 'shared'),
      '#root': `${__dirname}/`,
      '@env': process.env.ENV_DIR,
    },
  },
})
"""

_VITE_ARRAY = """\
export default {
  resolve: {
    alias: [
      { find: '@', replacement: '/src' },
      { find: /^~(.*)$/, replacement: '$1' },
    ],
  },
}
"""


def _project(tmp_path: Path, files: dict[str, str], folders: tuple[str, ...]) -> Path:
    for folder in folders:
        (tmp_path / folder).mkdir(parents=True, exist_ok=True)
    for rel_path, text in files.items():
        (tmp_path / rel_path).write_text(text, encoding="utf-8")
    return tmp_path


def test_a_project_with_neither_file_reads_nothing_and_says_nothing(tmp_path: Path) -> None:
    scan = scan_bundler_aliases(tmp_path)
    assert scan.aliases == ()
    assert scan.read_from == ()
    assert scan.sentence() == ""


def test_babel_module_resolver_aliases_are_read_and_unusable_ones_named(
    tmp_path: Path,
) -> None:
    root = _project(tmp_path, {"babel.config.js": _BABEL}, ("src/app", "src/shared", "old"))
    scan = scan_bundler_aliases(root)
    assert scan.read_from == ("babel.config.js",)
    assert scan.aliases == (("@app", "src/app"), ("@shared", "src/shared"), ("~", "src"))
    assert dict(scan.skipped) == {
        "^@icons/(.+)": "a regular expression",
        "gone": "`src/gone` names nothing in the project",
    }


def test_vite_aliases_are_read_from_the_literals_of_their_values(tmp_path: Path) -> None:
    root = _project(tmp_path, {"vite.config.ts": _VITE}, ("src/shared",))
    scan = scan_bundler_aliases(root)
    assert scan.read_from == ("vite.config.ts",)
    assert scan.aliases == (("@", "src"), ("@shared", "src/shared"), ("#root", "."))
    assert dict(scan.skipped) == {"@env": "a value built with no string literal"}


def test_vite_array_form_is_read_by_find_and_replacement(tmp_path: Path) -> None:
    root = _project(tmp_path, {"vite.config.mjs": _VITE_ARRAY}, ("src",))
    scan = scan_bundler_aliases(root)
    assert scan.aliases == (("@", "src"),)
    assert [why for _, why in scan.skipped] == ["a regular expression"]


def test_an_alias_both_files_declare_is_taken_from_the_first_read(tmp_path: Path) -> None:
    root = _project(
        tmp_path,
        {"babel.config.js": _BABEL, "vite.config.ts": _VITE},
        ("src/app", "src/shared"),
    )
    scan = scan_bundler_aliases(root)
    assert scan.read_from == ("babel.config.js", "vite.config.ts")
    assert [alias for alias, _ in scan.aliases] == ["@app", "@shared", "~", "@", "#root"]


def test_the_sentence_names_the_files_the_aliases_and_that_nothing_was_run(
    tmp_path: Path,
) -> None:
    root = _project(tmp_path, {"babel.config.js": _BABEL}, ("src/app", "src/shared"))
    sentence = scan_bundler_aliases(root).sentence()
    assert "babel.config.js" in sentence
    assert "@app -> src/app" in sentence
    assert "text scan" in sentence
    assert "imports.aliases" in sentence
    assert "not written: ^@icons/(.+) (a regular expression)" in sentence
