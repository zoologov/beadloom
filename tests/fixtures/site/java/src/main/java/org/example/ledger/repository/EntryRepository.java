package org.example.ledger.repository;

import java.util.ArrayList;
import java.util.List;
import org.example.ledger.model.Entry;

/** Keeps entries in the order they were recorded. */
public class EntryRepository {
    private final List<Entry> entries = new ArrayList<>();

    public void save(Entry entry) {
        entries.add(entry);
    }

    public List<Entry> forBuyer(String buyer) {
        return entries.stream().filter(e -> e.buyer().equals(buyer)).toList();
    }
}
