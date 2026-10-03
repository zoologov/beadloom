"""Bookings kept in memory, in the order they were made."""

from __future__ import annotations


class BookingStore:
    """An append-only list of bookings."""

    def __init__(self) -> None:
        self._rows: list[tuple[str, float]] = []

    def add(self, sender: str, amount: float) -> int:
        """Keep a booking and return its number."""
        self._rows.append((sender, amount))
        return len(self._rows)
