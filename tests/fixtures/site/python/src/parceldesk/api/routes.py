"""Takes a pickup request and answers with its booking."""

from __future__ import annotations

from parceldesk.billing.invoice import price_pickup
from parceldesk.storage.bookings import BookingStore

#: The bookings of this process, when the caller keeps none of its own.
DEFAULT_STORE = BookingStore()


def book_pickup(
    sender: str, weight_kg: float, store: BookingStore = DEFAULT_STORE
) -> dict[str, object]:
    """Price a pickup, keep it, and return what the caller sees."""
    amount = price_pickup(weight_kg)
    booking_id = store.add(sender, amount)
    return {"id": booking_id, "sender": sender, "amount": amount}
