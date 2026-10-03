// Package api answers HTTP requests for berths.
package api

import (
	"encoding/json"
	"net/http"
	"strconv"

	"example.org/tidewater/internal/billing"
	"example.org/tidewater/internal/catalog"
)

// Handler serves the catalogue and quotes.
type Handler struct {
	catalog *catalog.Catalog
}

// NewHandler wraps a catalogue in an HTTP handler.
func NewHandler(c *catalog.Catalog) *Handler {
	return &Handler{catalog: c}
}

func (h *Handler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	if nights, err := strconv.Atoi(r.URL.Query().Get("nights")); err == nil {
		cents, ok := billing.Quote(h.catalog, nights)
		_ = json.NewEncoder(w).Encode(map[string]any{"cents": cents, "available": ok})
		return
	}
	_ = json.NewEncoder(w).Encode(h.catalog.Free())
}
