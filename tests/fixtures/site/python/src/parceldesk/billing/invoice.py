"""The price of a pickup, from its weight."""

from __future__ import annotations

from parceldesk.storage.rates import base_rate


def price_pickup(weight_kg: float) -> float:
    """The base rate plus a charge per kilogram, rounded to cents."""
    return round(base_rate() + 0.4 * weight_kg, 2)
