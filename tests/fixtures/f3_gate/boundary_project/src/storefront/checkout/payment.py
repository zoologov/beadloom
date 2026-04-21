"""Checkout payment flow (F3 dogfood fixture).

This module deliberately breaches the ``checkout-no-import-catalog`` boundary
rule by importing the catalog module directly. The gate MUST block it.
"""

from storefront.catalog import pricing


def total_due(plan_id: str) -> int:
    """Return the amount due for a plan (illustrative)."""
    return pricing.price_of(plan_id)
