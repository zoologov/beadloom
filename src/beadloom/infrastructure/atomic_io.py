"""Atomic file writes for the source-of-truth graph YAML.

# beadloom:domain=infrastructure
# beadloom:component=atomic-io

A crash mid-write must never corrupt a graph YAML (``.beadloom/_graph/*.yml``,
onboarding ``services.yml`` / ``imported.yml`` / ``rules.yml`` / ``config.yml``).
:func:`write_yaml_atomic` serializes the data, writes it to a temporary file in
the *same* directory, ``fsync``s it, then ``os.replace``s it onto the target —
which is atomic on POSIX. The reader therefore always sees either the complete
old file or the complete new file, never a half-written one. On any failure the
temp file is removed and the prior target is left untouched.

This is a domain-agnostic, dependency-free primitive: it lives in the lowest
(``infrastructure``) layer so every graph-YAML writer (``graph``, ``services``,
``onboarding``) routes through one commit point. Serialization options
(``sort_keys`` / ``default_flow_style`` / ``allow_unicode`` / ...) are passed
through verbatim to :func:`yaml.dump`, so the emitted bytes are identical to the
prior direct ``yaml.dump`` -> ``write_text`` path (behavior-preserving).
"""

from __future__ import annotations

import contextlib
import os
import tempfile
from pathlib import Path
from typing import Any

import yaml


def write_yaml_atomic(path: Path, data: Any, **dump_kwargs: Any) -> None:
    """Serialize ``data`` to YAML and write it to ``path`` atomically.

    The data is dumped with :func:`yaml.dump` using ``dump_kwargs`` verbatim,
    written to a temp file in the same directory as ``path``, flushed +
    ``fsync``ed, then committed with :func:`os.replace`. On any error the temp
    file is removed and ``path`` is left untouched.

    :param path: the target file (its parent directory must already exist).
    :param data: the Python object to serialize.
    :param dump_kwargs: passed straight to :func:`yaml.dump` (e.g.
        ``sort_keys=False``, ``default_flow_style=False``, ``allow_unicode=True``)
        so output bytes match the prior direct-dump call-site exactly.
    """
    text = yaml.dump(data, **dump_kwargs)

    # Temp file in the SAME directory as the target so the commit is a
    # same-filesystem atomic rename. delete=False: we own the rename/cleanup.
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())  # no Path equivalent for fsync
        # The rename is the single commit point — atomic on POSIX.
        tmp_path.replace(path)
    except BaseException:
        # Commit failed (or was interrupted) — remove the temp file and leave
        # the prior target intact. Re-raise the original error.
        with contextlib.suppress(FileNotFoundError):
            tmp_path.unlink()
        raise
