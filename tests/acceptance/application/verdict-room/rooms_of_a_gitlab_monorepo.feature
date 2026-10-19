# BDL-083 S2a (`beadloom-3618`), RFC D6, BDL-UX #332. Measured on 9.0.0 over the monorepo
# fixture: a Python backend under `backend/` with its own `pyproject.toml`, a GitLab pipeline
# in `.gitlab-ci.yml`, and no packaging at the root. `rooms` read the root `pyproject.toml` and
# `.github/workflows` and nothing else, so it declared 0 rooms, and `ci` printed
# `0 of 0 declared room(s)` and named no leg of the pipeline the project runs.

@bead:beadloom-3618 @node:verdict-room
Feature: the rooms of a monorepo on GitLab come from its pipeline and the project under its scan paths

  Background:
    Given the monorepo fixture checked out

  Scenario: a GitLab job is a declared room that names its source
    When the rooms are reported as JSON
    Then a declared room comes from ".gitlab-ci.yml: backend-tests"
    And that room declares the python "3.12"

  Scenario: the packaging is read from the project found under the scan paths
    When the rooms are reported as JSON
    Then the interpreter floor is ">=3.12"
    And no unresolved entry names a packaging file at the root

  Scenario: the gate holds its run against the GitLab legs
    When the gate runs in the github format
    Then the room notice counts "0 of 2 declared room(s)"

  Scenario: a pipeline the census cannot read is a named skip
    Given the checkout's pipeline replaced by a Jenkinsfile
    When the gate runs in the rich format
    Then the room block says "rooms: not derived — no readable pipeline"
    And the rooms JSON carries a not-derived reason that names "Jenkinsfile"

  Scenario: the gate's coverage reads the GitLab pipeline
    When the gate runs in the json format
    Then the verifications not run name "uv run pytest tests" from ".gitlab-ci.yml: backend-tests"
