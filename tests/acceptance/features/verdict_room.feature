# The room a verdict was taken in, and the rooms it did not enter (BDL-068 S3.2).
# One Feature per file.

@bead:beadloom-0mdo.23 @node:ci-gate
Feature: a verdict names the room it was taken in

  BDL-067 reported "green on the tree" nine times. All nine were measured on
  macOS; the CI legs are Ubuntu, and the tenth measurement was red on six of
  them. The same suite skips fifteen tests on Linux that it does not skip on
  macOS, and a type check run against one interpreter locally met four in CI.

  Naming the room does not make a verdict stronger. It makes it answerable: a
  reader can see which rooms the run entered and which it did not, instead of
  reading a claim about one room as a claim about the product.

  The rooms are DERIVED -- the supported interpreters from the packaging
  metadata, the legs from the CI workflows -- so a leg added later is covered
  by the same act rather than by somebody remembering to edit a list.

  Scenario: the rooms come from where the project declares them
    Given a project whose packaging declares support for Python 3.10 and 3.11
    And a workflow job running on "ubuntu-latest" over both versions
    When the rooms are reported
    Then both declared legs are reported
    And a version added to the workflow is reported without the tool being changed

  Scenario: a run names the declared rooms it did not enter
    Given a project whose packaging declares support for Python 3.10 and 3.11
    And a workflow job running on "ubuntu-latest" over both versions
    When the rooms are reported
    Then at least one declared leg is reported as not entered
    And every leg not entered names the dimension that differs
    And every leg reported as entered matches this run in every dimension it declares

  Scenario: a leg the report cannot describe is named rather than dropped
    Given a workflow job running on a runner label the report has no platform for
    When the rooms are reported
    Then that job is reported as unresolved
    And it is not reported as a room this run entered

  Scenario: the gate verdict carries the room it was taken in
    Given a project the gate can run over
    When the gate verdict is rendered
    Then the verdict names the room it was taken in
    And the verdict names how many declared rooms it did not enter

  Scenario: naming the room does not change the verdict
    Given a project the gate can run over
    When the gate verdict is rendered
    Then the verdict names the room it was taken in
    And the verdict states the same result it states without its room
    And naming the room adds no finding

  @bead:beadloom-0mdo.24
  Scenario: a verdict with no run to report still names the room it was taken in
    Given a project declaring a mutation target that no run covered
    When the mutation verdict is rendered
    Then the verdict names the room it was taken in
    And the verdict reports the target as measured by no run
