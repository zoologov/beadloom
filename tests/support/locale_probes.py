"""The locales this repository's workflows declare, and the codec a child really gets.

The codec is asked of a second process started under the locale's name, so a
test that compares it with the product's own answer compares two measurements.
"""

from __future__ import annotations

import os
import subprocess
import sys

import yaml

from tests.support.repository_root import REPO_ROOT


def declared_locales() -> list[str]:
    """The locale names this repository's own workflows publish."""
    found: list[str] = []
    for path in sorted((REPO_ROOT / ".github" / "workflows").glob("*.yml")):
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        for job in (document or {}).get("jobs", {}).values():
            matrix = (job or {}).get("strategy", {}).get("matrix", {})
            found.extend(str(v) for v in matrix.get("locale", []))
    return found


def codec_of_a_child(name: str) -> str:
    """What a process started under *name* is really in, asked of the stdlib.

    A second child rather than the census's own answer: the assertion is that
    the two agree, and reading one of them from the thing under test would make
    it agree with itself.
    """
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "import codecs, locale; print(codecs.lookup(locale.getpreferredencoding(False)).name)",
        ],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=True,
        env={
            **os.environ,
            "LC_ALL": name,
            "PYTHONUTF8": "0",
            "PYTHONCOERCECLOCALE": "0",
        },
    )
    return completed.stdout.strip()
