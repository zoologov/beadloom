# BDL-076 R2 finding 2 (`beadloom-fht7`), fixed by `beadloom-ujzb.19`. Slice 2 taught
# init to read a Maven/Gradle module and a Swift package, and took the TOP-LEVEL folder
# holding each one out of the directory clustering and the scan paths. In a monorepo
# that folder also holds the services written in other languages, so a Python service
# beside a Maven one, or a TypeScript app beside a Swift package, lost its node, was not
# scanned and had its imports dropped, and init said nothing about it. Before slice 2
# (92f0690d) both siblings were nodes.
#
# The projects are written here: every adopter fixture is single-stack, which is why
# none of them caught it.

@bead:beadloom-ujzb.19 @node:agent-prime
Feature: init reads every service of a monorepo, whichever stack the service beside it uses

  Scenario: a Python service beside a Maven service keeps its node and is scanned
    Given a monorepo with a Maven service "services/billing" and a Python service "services/notify"
    When beadloom init is run without prompts
    Then the code nodes init writes have exactly the sources "services/billing/", "services/billing/src/main/java/org/acme/billing/api/", "services/billing/src/main/java/org/acme/billing/core/", "services/notify/", "services/notify/notify/", "services/notify/sender/"
    And the scan paths init writes are exactly "services/billing/src/main/java", "services/notify"

  Scenario: reindex after init resolves the imports of both services
    Given a monorepo with a Maven service "services/billing" and a Python service "services/notify"
    When beadloom init is run without prompts
    And beadloom reindex is run
    Then the index holds exactly the depends_on edges "services-billing-api -> services-billing-core", "notify-notify -> notify-sender"

  Scenario: a TypeScript app beside a Swift package keeps its node and is scanned
    Given a monorepo with a Swift package "apps/ios" and a TypeScript app "apps/web"
    When beadloom init is run without prompts
    And beadloom reindex is run
    Then the code nodes init writes have exactly the sources "apps/ios/", "apps/ios/Sources/App/", "apps/ios/Sources/Core/", "apps/web/", "apps/web/src/"
    And the scan paths init writes are exactly "apps/ios/Sources/App", "apps/ios/Sources/Core", "apps/web"
    And the index holds exactly the depends_on edges "apps-ios-App -> apps-ios-Core"
    And the index holds the import "../util/f" of "apps/web/src/api/index.ts"
