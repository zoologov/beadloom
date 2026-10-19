"""The sections of the daily digest, built from the file history."""

from __future__ import annotations

from typing import TYPE_CHECKING

from digest.sections import Section

if TYPE_CHECKING:
    from file_history.entries import Entry


def uploads_section(entries: list[Entry]) -> Section:
    """The digest section that lists the day's uploads, one line per file."""
    return Section("Uploads", tuple(f"{entry.name}: {entry.rows}" for entry in entries))
