# beadloom:domain=onboarding
# beadloom:feature=flow-manifest
"""What the composer last wrote, so a later run can tell its output from a hand edit.

A composed artifact on disk can differ from the expected composition for two
opposite reasons, and they need opposite treatments:

* **the composition moved** — the shipped core was upgraded, or the project
  layer changed. The file should be recomposed.
* **a human edited the file** — the edit is the only copy of somebody's intent.
  It must be reported with somewhere to put it, and never rewritten.

Nothing in the file itself distinguishes the two. So every write records the
SHA-256 of exactly what was written in ``.beadloom/flow-manifest.json``; a later
run compares the file against that recorded digest. Matching means untouched
since we wrote it (safe to recompose); differing means somebody changed it.

A repo scaffolded before this manifest existed has no entry at all. That is a
third state and it is reported as such — ``unmanaged``, not ``hand-edited`` and
not ``clean`` — because guessing which of the two it is, is how a check comes to
print one word over several situations (BDL-061 S2b).
"""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from pathlib import Path

#: Manifest path relative to the project root — generated state, so it sits
#: beside ``flow.yml`` rather than inside the authored ``.beadloom/flow/`` tree.
FLOW_MANIFEST_RELPATH = Path(".beadloom") / "flow-manifest.json"

_SCHEMA_VERSION = 1


class ArtifactState(Enum):
    """How an on-disk composed artifact relates to its expected composition."""

    #: Byte-identical to the expected composition.
    CLEAN = "clean"
    #: Differs, but matches what we last wrote — the composition moved.
    STALE = "stale"
    #: Differs from both — somebody edited it by hand.
    HAND_EDITED = "hand_edited"
    #: No manifest entry: scaffolded before the manifest existed, or removed.
    UNMANAGED = "unmanaged"


def digest(text: str) -> str:
    """SHA-256 of ``text`` as UTF-8 — the recorded fingerprint of one write."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_manifest(project_root: Path) -> dict[str, str]:
    """Read the recorded ``{project-relative path: sha256}`` map (absent → empty)."""
    path = project_root / FLOW_MANIFEST_RELPATH
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        # An unreadable manifest means every artifact reads UNMANAGED, which is
        # reported rather than silently treated as clean.
        return {}
    written = data.get("written") if isinstance(data, dict) else None
    if not isinstance(written, dict):
        return {}
    return {str(k): str(v) for k, v in written.items()}


def record(project_root: Path, entries: dict[str, str]) -> None:
    """Merge ``{relpath: sha256}`` into the manifest and write it back.

    Merged rather than replaced because a single run writes only the artifacts
    it was asked for; dropping the rest would make them read ``unmanaged`` and
    manufacture the very ambiguity this module exists to remove.
    """
    if not entries:
        return
    path = project_root / FLOW_MANIFEST_RELPATH
    merged = load_manifest(project_root)
    merged.update(entries)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": _SCHEMA_VERSION, "written": dict(sorted(merged.items()))}
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def classify(
    *,
    on_disk: str | None,
    expected: str,
    recorded: str | None,
    alternates: tuple[str, ...] = (),
) -> ArtifactState:
    """Classify one artifact against its expected composition + recorded digest.

    ``alternates`` are other bodies Beadloom itself could have written — the
    shipped core without the project layer, for instance. A repo scaffolded
    before the manifest existed still matches one of them if nobody edited the
    file, so it reads ``stale`` (recomposable) rather than ``unmanaged``, and an
    adopter upgrading into this release keeps the strictness they had.
    """
    if on_disk is not None and on_disk == expected:
        return ArtifactState.CLEAN
    if on_disk is not None and on_disk in alternates:
        return ArtifactState.STALE
    if recorded is None:
        return ArtifactState.UNMANAGED
    if on_disk is not None and digest(on_disk) == recorded:
        return ArtifactState.STALE
    return ArtifactState.HAND_EDITED


def state_of(
    project_root: Path,
    relpath: str,
    *,
    expected: str,
    manifest: dict[str, str] | None = None,
    alternates: tuple[str, ...] = (),
) -> ArtifactState:
    """Classify the artifact at ``relpath`` (project-relative) against ``expected``."""
    entries = load_manifest(project_root) if manifest is None else manifest
    path = project_root / relpath
    on_disk: str | None
    try:
        on_disk = path.read_text(encoding="utf-8") if path.is_file() else None
    except OSError:
        on_disk = None
    return classify(
        on_disk=on_disk,
        expected=expected,
        recorded=entries.get(relpath),
        alternates=alternates,
    )
