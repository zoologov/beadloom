# BDL-076 B5. Measured by B3 (`beadloom-hmqn`) on the Go adopter fixture: `reindex`
# recorded every Go import with no node, because nothing stripped the module path
# `go.mod` declares, so a Go project got no `depends_on` edge from its code and a
# deny rule — which judges resolved imports — never fired on a Go project.
#
# The fixtures are Go projects this repository cannot be mistaken for: it holds no
# Go and no `go.mod`, so a fix that recognised our own tree would pass nothing here.
# The entry point of the first one is named after its module, which is the layout
# that drew every internal import onto the entry point in `init`.

@bead:beadloom-ujzb.14 @node:import-resolver
Feature: a Go import becomes an edge to the node that owns the package its module path names

  Scenario: the edges of a Go service are exactly the imports between its packages
    Given a Go service whose entry point is named after its module
    When the project is indexed
    Then the depends_on edges are exactly "harbour -> berths", "harbour -> ledger", "ledger -> berths"

  Scenario: an import of the standard library or of a module the project does not hold names no node
    Given a Go service whose entry point is named after its module
    When the project is indexed
    Then the import "net/http" of "cmd/harbour/main.go" is recorded with no node
    And the import "github.com/acme/harbour/internal/berths" of "internal/ledger/ledger.go" is recorded with no node

  Scenario: a module of a Go workspace reaches a package of another module the workspace uses
    Given a Go workspace whose orders module imports a package of its money module
    When the project is indexed
    Then the import "example.org/money/fx" of "services/orders/orders.go" resolves to "money"
    And the depends_on edges are exactly "orders -> money"

  Scenario: a deny rule between two Go packages reports the import that crosses it
    Given a Go service whose entry point is named after its module
    And a warn rule that denies the entry point any import of the berths package
    When the project is linted
    Then the rule reports "cmd/harbour/main.go" importing "berths"
