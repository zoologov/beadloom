@bead:beadloom-rqma.1 @node:wave-plan
Feature: A wave plan is compared against the work already running under its work item

  # BDL-UX #283. `beadloom waves --parent <work-item>` takes its bead list from
  # `bd ready`, and a bead that is `in_progress` is not ready. So a bead running
  # under the same work item was never compared against the plan, and the plan
  # printed `0 serialisation(s)` — which a coordinator deciding whether to launch
  # reads as "nothing conflicts". Measured in BDL-069 on 2026-09-11: `--parent`
  # answered one clean wave for `beadloom-8lmj` while `beadloom-h7b3` was running,
  # and naming the pair explicitly serialised them over `cli-commands -> agent-prime`.
  #
  # Reproduced red on a bd 1.0.4 rig before the change: an epic holding one bead
  # in progress and one ready, both declaring `billing`, answered
  # `1 wave(s) for 1 bead(s), 0 serialisation(s)` under `--parent`, and
  # `shared_node: billing` when the two were named.

  Background:
    Given a project whose graph holds the nodes "billing" and "shipping"

  Scenario: A plan derived from a work item names a serialisation against a bead already running under it
    Given a work item "epic" holding a bead "running" in progress declaring "billing"
    And the work item "epic" holds a ready bead "new" declaring "billing"
    When the plan is derived from the work item "epic"
    Then "new" is serialised against the running bead "running" over "billing"
    And that serialisation is reported apart from the plan's own serialisations
    And the summary line states 1 serialisation against 1 running bead
    And the serialisation against running work is not a finding

  Scenario: A running bead that shares nothing with the plan is compared and says so
    Given a work item "epic" holding a bead "running" in progress declaring "shipping"
    And the work item "epic" holds a ready bead "new" declaring "billing"
    When the plan is derived from the work item "epic"
    Then the summary line states 0 serialisations against 1 running bead
    And the plan says no bead of it conflicts with the running work

  Scenario: An in-progress bead the tracker cannot show is counted as not compared
    Given a work item "epic" holding a bead "running" in progress declaring "billing"
    And the work item "epic" holds a ready bead "new" declaring "billing"
    And the tracker cannot show the bead "running"
    When the plan is derived from the work item "epic"
    Then the summary line states 1 running bead it did not compare against
    And the plan carries a finding naming "running" as not compared

  Scenario: A running bead named in the plan is planned rather than compared against
    Given a work item "epic" holding a bead "running" in progress declaring "billing"
    And the work item "epic" holds a ready bead "new" declaring "billing"
    When the plan is asked about the beads "running" and "new"
    Then "running" and "new" are serialised within the plan over "billing"
    And the summary line states 0 serialisations against 0 running beads

  Scenario: A plan that read no tracker census says running work was not compared
    Given a bead "new" declaring "billing" and a tracker that lists nothing
    When the plan is asked about the beads "new"
    Then the summary line says running work was not compared
