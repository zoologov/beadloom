# BDL-068 S2. `review-brief` counted what IT withheld and printed `0 withheld`.
# That sentence is true of bead comments and false about the question its reader
# is asking, which is "what can this reviewer reach".
#
# Three measured defeats of the same mechanism, each found only because a
# reviewer declared it unprompted:
#   #212 the author's account reached the reviewer through ACTIVE.md, which the
#        launch prompt names because the playbook says a role subagent gets
#        CONTEXT.md and ACTIVE.md;
#   #219 through the commit bodies of the reviewed range — not reachable by
#        prompt discipline at all, because the review protocol itself directs the
#        reviewer to read the diff, and the better the commit message the more
#        completely the withholding is defeated;
#   #204 the command cannot see the coordinator's prompt, so its count is about
#        its own scope and is read as being about the reviewer's knowledge.
#
# The report states what is REACHABLE per channel. It raises detectability and
# closes nothing: a reviewer that knows what it can reach can declare a leak,
# which is how all three of these were ever known.

@bead:beadloom-0mdo.18 @node:review-brief
Feature: the brief states what can reach the reviewer, per channel, and names a channel it cannot inspect

  Scenario: The bead comments this command withholds are stated as a channel, with their count
    Given a bead "alpha" declaring the node scope "billing"
    And the author recorded 3 comments on "alpha"
    When the reviewer's brief is assembled
    Then the "bead comments" channel was inspected and carries 3 item(s)
    And the "bead comments" channel says this command withholds them

  Scenario: A document a composed role prompt names is reported as reachable, with the prompt that names it
    Given a work item "ALPHA-1" carrying the documents "CONTEXT.md, ACTIVE.md"
    And the review runs on the branch "features/ALPHA-1"
    When the reviewer's brief is assembled
    Then the "the work item's documents" channel was inspected and carries 2 item(s)
    And the "the work item's documents" channel names "ACTIVE.md" and the prompt that names it

  Scenario: A document named only by the project's own role fragment moves the report
    Given a work item "ALPHA-1" carrying the documents "CONTEXT.md, DECISIONS.md"
    And the project's own "review" role fragment names "DECISIONS.md"
    And the review runs on the branch "features/ALPHA-1"
    When the reviewer's brief is assembled
    Then the "the work item's documents" channel names "DECISIONS.md" and the prompt that names it

  Scenario: The commit bodies of the reviewed range are stated with the range they were read over
    Given the reviewed range since "main" holds a commit whose body carries 4 line(s)
    When the reviewer's brief is assembled
    Then the "the commit bodies of the reviewed range" channel was inspected and carries 1 item(s)
    And the "the commit bodies of the reviewed range" channel names the range it was read over

  Scenario: A channel nobody could inspect is named rather than omitted
    Given git gave no answer for the reviewed range
    When the reviewer's brief is assembled
    Then the "the commit bodies of the reviewed range" channel was not inspected
    And the "the commit bodies of the reviewed range" channel gives its reason

  Scenario: An inspected channel that found nothing does not read like one nobody could inspect
    Given the reviewed range since "main" holds no commits
    And the review runs on the branch "features/NOTHING-HERE"
    When the reviewer's brief is assembled
    Then the "the commit bodies of the reviewed range" channel was inspected and carries 0 item(s)
    And the "the work item's documents" channel was not inspected
    And the two channels state themselves differently

  Scenario: The launch prompt is named as a channel this command cannot inspect
    Given a bead "alpha" declaring the node scope "billing"
    When the reviewer's brief is assembled
    Then the "the launch prompt" channel was not inspected
    And the "the launch prompt" channel says only the reviewer can see it

  # BDL-068.19-1, filed as a strict xfail by the test bead and reproduced by the
  # S2 review: the config the prompts compose from was read OUTSIDE the guard the
  # composition already had, so a `flow.yml` that will not parse raised out of the
  # derivation and `review-brief` produced no brief at all. A report about what a
  # reviewer can reach is worth nothing if a broken configuration file removes it.
  @bead:beadloom-0mdo.28
  Scenario: A project flow file that will not parse costs one channel and not the brief
    Given a work item "ALPHA-1" carrying the documents "CONTEXT.md, ACTIVE.md"
    And the review runs on the branch "features/ALPHA-1"
    And the project's own flow file will not parse
    And the reviewed range since "main" holds no commits
    When the reviewer's brief is assembled
    Then the "the work item's documents" channel was not inspected
    And the "the work item's documents" channel gives its reason
    And the "the commit bodies of the reviewed range" channel was inspected and carries 0 item(s)

  # The count is scoped to ONE bead, and under this project's wave structure that
  # bead is a review bead, which by construction carries no author account: the
  # account of the change sits on the beads that made it. On the S2 review's own
  # run `0 item(s)` stood beside 31,544 characters on two sibling beads.
  @bead:beadloom-0mdo.28
  Scenario: The bead comments channel names the one bead it counted and says the others are not counted
    Given a bead "alpha" declaring the node scope "billing"
    And the author recorded 3 comments on "alpha"
    When the reviewer's brief is assembled
    Then the "bead comments" channel names the bead it counted
    And the "bead comments" channel says no other bead's comments are counted
