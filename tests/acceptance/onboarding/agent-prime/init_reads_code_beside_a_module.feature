# BDL-076, the re-review's finding m3 (`beadloom-ujzb.22`), fixed by `beadloom-ujzb.24`.
# After R2 finding 2 the JVM and Swift layouts claim a module's or a package's own
# folder, and init dropped that whole folder from its scan paths. Code in the module's
# folder but outside its source roots - Python deployment scripts in `backend/scripts`
# beside `backend/src/main/kotlin` - was then in no scan path, and a code file lying
# directly in a folder beside a module (`services/run.py`) was in none either. Neither
# was read by reindex, and init said nothing about either.
#
# A module owns its `src` folder; everything else in its folder is scanned. A scan path
# is a folder, so a file lying directly beside a module cannot be one without scanning
# the module's test tree too: init names that file instead of dropping it in silence.

@bead:beadloom-ujzb.24 @node:agent-prime
Feature: init scans the code beside a module and names what it cannot scan

  Scenario: Python scripts in a Gradle module's folder, outside its source roots, are scanned
    Given a Gradle project whose module "backend" holds Python scripts in "backend/scripts"
    When beadloom init is run without prompts
    And beadloom reindex is run
    Then the scan paths init writes are exactly "backend/scripts", "backend/src/main/kotlin", "web"
    And the index holds the symbols of "backend/scripts/deploy/helm.py"
    And init says it also scanned "backend/scripts" beside a module

  Scenario: a file lying directly in a folder beside a Maven service is named as not read
    Given a monorepo with a Maven service "services/billing" and a file "services/run.py" beside it
    When beadloom init is run without prompts
    Then the scan paths init writes are exactly "services/billing/src/main/java", "services/notify"
    And init names "services/run.py" as not read
