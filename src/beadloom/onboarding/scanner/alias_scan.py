"""The import aliases a project's bundler declares, read by ``init`` from the text of its config.

BDL-080 S3a (``beadloom-cwzc``), RFC D5 (b). A React Native project aliases its folders
with Babel's ``module-resolver`` (``alias: {'@shared': './src/shared'}`` in
``babel.config.js``), a Vite project with ``resolve.alias`` in ``vite.config.ts``. Both
files are programs, and nothing here runs them: the scan reads their text, finds each
``alias:`` block and takes from it what a reader can take without evaluating anything.

**What is read.** In an ``alias: { ... }`` object, each entry whose key is a quoted string
or a bare name; in an ``alias: [ ... ]`` array, each ``{ find, replacement }`` entry whose
``find`` is a string. The folder is built from the string literals of the value, in order
(``path.resolve(__dirname, 'src', 'shared')`` is ``src/shared``;
``fileURLToPath(new URL('./src', import.meta.url))`` is ``src``); the ``${...}`` parts of a
template literal are dropped, and a leading ``/`` (Vite's project root) and ``./`` are too.
Comments are not read, and a comment marker inside a string is text.

**What is named and not written:** a regular-expression alias, a value with no string
literal (``process.env.X``), and a folder that is not in the project. **Which files:**
``babel.config.{js,cjs,mjs,json}``, ``.babelrc`` and ``vite.config.*`` at the project
root, in that order; an alias two of them declare is taken from the first.

``init`` writes the usable aliases under ``imports.aliases:`` and prints
:meth:`AliasScan.sentence`, which says they came from a text scan, so the user confirms
them rather than trusting them.
"""

# beadloom:domain=onboarding
# beadloom:feature=agent-prime

from __future__ import annotations

import posixpath
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

#: The Babel configs read, in order; then every ``vite.config.*``.
_BABEL_CONFIGS = (
    "babel.config.js",
    "babel.config.cjs",
    "babel.config.mjs",
    "babel.config.json",
    ".babelrc",
)
_VITE_GLOB = "vite.config.*"

_ALIAS_BLOCK = re.compile(r"""(?<![\w$])["']?alias["']?\s*:\s*([\[{])""")
_BARE_KEY = re.compile(r"[A-Za-z_$#@~][\w$@~#/-]*")
_FIND = re.compile(r"""(?<![\w$])find\s*:\s*""")
_REPLACEMENT = re.compile(r"""(?<![\w$])replacement\s*:\s*""")
_QUOTES = "'\"`"
_OPENERS = "([{"
_CLOSERS = ")]}"
_REGEX_MARKS = frozenset("^$()+?|[]\\")
_TEMPLATE_PART = re.compile(r"\$\{[^}]*\}")

_REGULAR_EXPRESSION = "a regular expression"
_NO_LITERAL = "a value built with no string literal"
_ROOT = "."


@dataclass(frozen=True)
class AliasScan:
    """What the scan read, the aliases it can write, and the ones it names and does not."""

    aliases: tuple[tuple[str, str], ...] = ()
    read_from: tuple[str, ...] = ()
    skipped: tuple[tuple[str, str], ...] = ()

    def sentence(self) -> str:
        """What ``init`` says about the scan; ``""`` when no file was read."""
        if not self.read_from:
            return ""
        files = ", ".join(self.read_from)
        if self.aliases:
            found = ", ".join(f"{alias} -> {folder}" for alias, folder in self.aliases)
            said = (
                f"Import aliases: {len(self.aliases)} read from {files} by a text scan, "
                f"not by running it ({found}); written under imports.aliases: in "
                ".beadloom/config.yml - confirm them"
            )
        else:
            said = f"Import aliases: none read from {files} by a text scan"
        if self.skipped:
            named = "; ".join(f"{alias} ({why})" for alias, why in self.skipped)
            said += f"; not written: {named}"
        return said


def _string_end(text: str, start: int) -> int:
    """The index just past the string literal opening at *start*."""
    quote = text[start]
    index = start + 1
    while index < len(text):
        if text[index] == "\\":
            index += 2
            continue
        if text[index] == quote:
            return index + 1
        index += 1
    return len(text)


def _without_comments(text: str) -> str:
    """*text* with every ``//`` and ``/* */`` comment blanked; strings are kept whole."""
    out: list[str] = []
    index = 0
    while index < len(text):
        char = text[index]
        if char in _QUOTES:
            end = _string_end(text, index)
            out.append(text[index:end])
            index = end
        elif text.startswith("//", index):
            end = text.find("\n", index)
            index = len(text) if end < 0 else end
        elif text.startswith("/*", index):
            end = text.find("*/", index + 2)
            index = len(text) if end < 0 else end + 2
        else:
            out.append(char)
            index += 1
    return "".join(out)


def _closing(text: str, opening: int) -> int:
    """The index of the bracket closing the one at *opening*; strings are skipped."""
    depth = 0
    index = opening
    while index < len(text):
        char = text[index]
        if char in _QUOTES:
            index = _string_end(text, index)
            continue
        if char in _OPENERS:
            depth += 1
        elif char in _CLOSERS:
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return len(text)


def _items(text: str) -> list[str]:
    """*text* split at its top-level commas; strings and brackets are kept whole."""
    items: list[str] = []
    depth, start, index = 0, 0, 0
    while index < len(text):
        char = text[index]
        if char in _QUOTES:
            index = _string_end(text, index)
            continue
        if char in _OPENERS:
            depth += 1
        elif char in _CLOSERS:
            depth -= 1
        elif char == "," and depth == 0:
            items.append(text[start:index])
            start = index + 1
        index += 1
    items.append(text[start:])
    return [item.strip() for item in items if item.strip()]


def _literals(text: str) -> list[str]:
    """The contents of every string literal in *text*, in order; ``${...}`` dropped."""
    found: list[str] = []
    index = 0
    while index < len(text):
        if text[index] in _QUOTES:
            end = _string_end(text, index)
            found.append(_TEMPLATE_PART.sub("", text[index + 1 : end - 1]))
            index = end
        else:
            index += 1
    return found


def _folder(value: str) -> str | None:
    """The project-relative folder *value*'s literals spell, or ``None`` when it has none."""
    parts = [part.strip("/") for part in _literals(value) if part.strip()]
    if not _literals(value):
        return None
    joined = "/".join(part for part in parts if part not in ("", _ROOT))
    normal = posixpath.normpath(joined) if joined else _ROOT
    return _ROOT if normal in ("", _ROOT) else normal


def _key(text: str) -> tuple[str | None, str]:
    """An object entry's key and the text after its colon; ``None`` for a computed key."""
    if text[:1] in _QUOTES:
        end = _string_end(text, 0)
        key, rest = text[1 : end - 1], text[end:]
    else:
        match = _BARE_KEY.match(text)
        if match is None:
            return None, ""
        key, rest = match.group(0), text[match.end() :]
    rest = rest.lstrip()
    return (key, rest[1:]) if rest.startswith(":") else (None, "")


def _object_entries(block: str) -> list[tuple[str, str | None]]:
    """``(alias, value text)`` of each entry of an ``alias: { ... }`` object."""
    found: list[tuple[str, str | None]] = []
    for item in _items(block):
        key, value = _key(item)
        if key is not None:
            found.append((key, value))
    return found


def _array_entries(block: str) -> list[tuple[str, str | None]]:
    """``(find, replacement text)`` of each ``{ find, replacement }`` entry of an array."""
    found: list[tuple[str, str | None]] = []
    for item in _items(block):
        find = _FIND.search(item)
        if find is None:
            continue
        rest = item[find.end() :]
        if rest[:1] == "/":
            found.append((rest.split(",")[0].strip(), None))
            continue
        if rest[:1] not in _QUOTES:
            continue
        alias = rest[1 : _string_end(rest, 0) - 1]
        replacement = _REPLACEMENT.search(item)
        found.append((alias, item[replacement.end() :] if replacement else ""))
    return found


def _declared(text: str) -> list[tuple[str, str | None]]:
    """Every ``(alias, value text)`` the ``alias:`` blocks of *text* hold; ``None``: a regex."""
    code = _without_comments(text)
    found: list[tuple[str, str | None]] = []
    for match in _ALIAS_BLOCK.finditer(code):
        opening = match.start(1)
        block = code[opening + 1 : _closing(code, opening)]
        found.extend(_object_entries(block) if code[opening] == "{" else _array_entries(block))
    return found


def _judged(project_root: Path, alias: str, value: str | None) -> tuple[str | None, str]:
    """The folder *alias* is written with, or why it is named and not written."""
    if value is None or set(alias) & _REGEX_MARKS:
        return None, _REGULAR_EXPRESSION
    folder = _folder(value)
    if folder is None:
        return None, _NO_LITERAL
    if folder.startswith("..") or not (project_root / folder).exists():
        return None, f"`{folder}` names nothing in the project"
    return folder, ""


def _config_files(project_root: Path) -> list[Path]:
    babel = [project_root / name for name in _BABEL_CONFIGS]
    vite = sorted(project_root.glob(_VITE_GLOB))
    return [path for path in (*babel, *vite) if path.is_file()]


def scan_bundler_aliases(project_root: Path) -> AliasScan:
    """The aliases ``babel.config.*`` and ``vite.config.*`` at *project_root* declare."""
    read_from: list[str] = []
    aliases: dict[str, str] = {}
    skipped: dict[str, str] = {}
    for path in _config_files(project_root):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        read_from.append(path.name)
        for declared, value in _declared(text):
            alias = declared.rstrip("/") if value is not None else declared
            if alias in aliases or alias in skipped:
                continue
            folder, why = _judged(project_root, alias, value)
            if folder is None:
                skipped[alias] = why
            else:
                aliases[alias] = folder
    return AliasScan(tuple(aliases.items()), tuple(read_from), tuple(skipped.items()))
