package catalog

import (
	"testing"

	"example.org/tidewater/internal/storage"
)

func TestFreeLeavesOutHeldBerths(t *testing.T) {
	c := New(storage.NewMemory())
	if got := len(c.Free()); got != 1 {
		t.Fatalf("free berths = %d, want 1", got)
	}
}
