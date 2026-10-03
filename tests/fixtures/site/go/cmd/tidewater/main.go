// Command tidewater serves the berth catalogue.
package main

import (
	"log"
	"net/http"

	"example.org/tidewater/internal/api"
	"example.org/tidewater/internal/catalog"
	"example.org/tidewater/internal/storage"
)

func main() {
	store := storage.NewMemory()
	handler := api.NewHandler(catalog.New(store))
	log.Fatal(http.ListenAndServe(":8080", handler))
}
