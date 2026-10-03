# BDL-076 B5. Measured by B3 (`beadloom-hmqn`) on the Go adopter fixture: `init`'s
# quick import scan split `example.org/tidewater/internal/catalog` into segments
# and took the first one naming a cluster. On the standard Go layout the entry
# point lives in `cmd/<module-name>/`, so `tidewater` named it, and every internal
# import landed on the entry point: three edges the code does not have, and three
# of the seven it does have were missing.
#
# The fixture is written here, not taken from this repository, which holds no Go.

@bead:beadloom-ujzb.14 @node:agent-prime
Feature: init draws a Go project's package imports, not edges onto the entry point named after its module

  Scenario: init on the standard Go layout writes an edge for each import between packages
    Given a Go repository whose entry point directory is named after its module
    When beadloom init is run without prompts
    Then the graph init writes has exactly the depends_on edges "harbour-service -> berths", "harbour-service -> ledger", "ledger -> berths"
    And no depends_on edge init writes points at "harbour-service"
