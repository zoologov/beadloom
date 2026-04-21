"""Catalog pricing (F3 dogfood fixture target of the forbidden import)."""


def price_of(plan_id: str) -> int:
    """Return a fixed illustrative price for a plan."""
    return 100 if plan_id else 0
