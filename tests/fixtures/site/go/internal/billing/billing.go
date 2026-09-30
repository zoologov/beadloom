// Package billing charges for the berths a boat holds.
package billing

import "example.org/tidewater/internal/catalog"

// NightlyRateCents is what one berth costs for one night.
const NightlyRateCents = 4200

// Quote prices a stay of the given nights, if a berth is free.
func Quote(c *catalog.Catalog, nights int) (int, bool) {
	if len(c.Free()) == 0 {
		return 0, false
	}
	return nights * NightlyRateCents, true
}
