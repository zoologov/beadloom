// Package storage keeps berths.
package storage

// Berth is one mooring place.
type Berth struct {
	Name string
	Held bool
}

// Store is anything that lists berths.
type Store interface {
	All() []Berth
}

// Memory is a Store held in memory.
type Memory struct {
	berths []Berth
}

// NewMemory returns a store with two berths, one held.
func NewMemory() *Memory {
	return &Memory{berths: []Berth{{Name: "north-1", Held: true}, {Name: "north-2"}}}
}

// All returns every berth.
func (m *Memory) All() []Berth {
	return m.berths
}
