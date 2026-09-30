package org.example.ledger.service;

import static org.junit.jupiter.api.Assertions.assertEquals;

import org.example.ledger.repository.EntryRepository;
import org.junit.jupiter.api.Test;

class LedgerServiceTest {

    @Test
    void balanceSumsEveryShipmentOfTheBuyer() {
        LedgerService ledger = new LedgerService(new EntryRepository());
        ledger.record("granite-yard", 2, 150);
        ledger.record("granite-yard", 1, 100);
        assertEquals(400, ledger.balanceCents("granite-yard"));
    }
}
