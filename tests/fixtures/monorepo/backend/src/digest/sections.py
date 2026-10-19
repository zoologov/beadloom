"""A digest section: a titled group of metric lines."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Section:
    """A titled group of metric lines, in the order they are reported."""

    title: str
    lines: tuple[str, ...]

    def render(self) -> str:
        """The section as text: its title, then one line per metric."""
        return "\n".join((self.title, *self.lines))
