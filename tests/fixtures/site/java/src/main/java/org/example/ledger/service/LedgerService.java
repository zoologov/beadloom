package org.example.ledger.service;

import org.example.ledger.model.Entry;
import org.example.ledger.repository.EntryRepository;

/** Records shipments and answers a buyer's balance. */
public class LedgerService {
    private final EntryRepository repository;

    public LedgerService(EntryRepository repository) {
        this.repository = repository;
    }

    public void record(String buyer, long tonnes, long priceCents) {
        repository.save(new Entry(buyer, tonnes, priceCents));
    }

    public long balanceCents(String buyer) {
        return repository.forBuyer(buyer).stream().mapToLong(Entry::totalCents).sum();
    }
}
