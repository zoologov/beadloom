package org.example.ledger.web;

import org.example.ledger.service.LedgerService;

/** Turns a request line into a ledger call. */
public class LedgerController {
    private final LedgerService ledger;

    public LedgerController(LedgerService ledger) {
        this.ledger = ledger;
    }

    public String balance(String buyer) {
        return buyer + ": " + ledger.balanceCents(buyer);
    }
}
