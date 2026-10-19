# BDL-083 S2b, RFC D6, BDL-UX #333 and #311. Measured on the first outside adopter's
# monorepo, anonymised as the monorepo fixture: `clean-room` built no environment for the
# Python project under `backend/`, because it read the legs of `.github/workflows` only, and
# its "Measure in the room" hint printed this repository's own layout — `<room>/src`,
# `<room>/tests` and `import beadloom` — none of which the room holds. Where it did build an
# environment it installed with `uv pip install -e`, which resolves afresh and ignores
# `uv.lock`: gherkin-official 42 against the lock's 29 failed one self-check test in every
# room of BDL-083 S1 and S2, and in no CI leg.
#
# So the room finds the Python project that owns the carried files, builds that project's
# environment from its own `uv.lock` with `uv sync --frozen`, derives the hint from that
# project, and names what its missing `.git` costs a suite.

@bead:beadloom-cptm @node:wave-plan
Feature: a clean room measures the Python project that owns the carried files

  Scenario: The room builds the owning project's environment from that project's lock
    Given the monorepo fixture checked out
    When bead "beadloom-x.1" builds its clean room carrying "backend/src/digest/sections.py"
    Then the room is built for the Python project "backend"
    And the room's environment was installed from "backend/uv.lock"
    And the room's environment holds the version of "pytest" that "backend/uv.lock" pins

  Scenario: The hint measures the project the room was built for, and runs as printed
    Given the monorepo fixture checked out
    When bead "beadloom-x.1" builds its clean room carrying "backend/src/digest/sections.py"
    Then every line of the hint names the interpreter under "backend/.venv" in the room
    And the hint names no path the room does not hold
    And the hint's suite line passes when it is run as printed

  Scenario: A project without a lock is resolved afresh, and the room says so
    Given the monorepo fixture checked out
    And the checkout's "backend/uv.lock" deleted and committed
    When bead "beadloom-x.1" builds its clean room carrying "backend/src/digest/sections.py"
    Then the room's environment says it was resolved outside a lock

  Scenario: The room names what its missing .git costs a suite
    Given the monorepo fixture checked out
    When bead "beadloom-x.1" builds its clean room carrying "backend/src/digest/sections.py"
    Then the room's limits say a test that reads git fails there for that reason
