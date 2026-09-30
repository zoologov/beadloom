// Package catalog lists the berths that are free.
package catalog

import "example.org/tidewater/internal/storage"

// Catalog reads berths from a store.
type Catalog struct {
	store storage.Store
}

// New builds a catalogue over a store.
func New(s storage.Store) *Catalog {
	return &Catalog{store: s}
}

// Free returns the names of the berths nobody holds.
func (c *Catalog) Free() []string {
	var free []string
	for _, b := range c.store.All() {
		if !b.Held {
			free = append(free, b.Name)
		}
	}
	return free
}
