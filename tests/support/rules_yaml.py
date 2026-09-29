"""A one-file ``rules.yml`` for the loader's unit tests, and the pattern a refusal must match.

The loader's tests write a small rules file under ``tmp_path`` and read it with
``load_rules``; a refused block is pinned by its whole message, because that
message is the only thing an adopter reads when their ``rules.yml`` is wrong.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def write_rules_file(root: Path, body: str) -> Path:
    """Write ``rules.yml`` under *root*: a version header, then *body* as its ``rules:`` list."""
    path = root / "rules.yml"
    path.write_text(f"version: 1\nrules:\n{body}", encoding="utf-8")
    return path


def exactly(message: str) -> str:
    """A ``pytest.raises`` pattern matching *message* and nothing longer or shorter."""
    return f"^{re.escape(message)}$"
