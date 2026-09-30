package org.example.ledger.model;

/** One shipment to one buyer. */
public record Entry(String buyer, long tonnes, long priceCents) {

    /** What the shipment costs the buyer. */
    public long totalCents() {
        return tonnes * priceCents;
    }
}
