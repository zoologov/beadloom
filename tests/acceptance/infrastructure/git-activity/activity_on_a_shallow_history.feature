# BDL-078 `beadloom-btkd.9`, from T's finding F1 (`beadloom-q63p`). The portal this
# repository publishes, and the one the Pages workflow `docs site --pages-workflow`
# writes for an adopter, were built from a clone one commit deep. Git shows the one
# commit of such a clone as adding every file, so every node read "1 commit in 30
# days", its changed lines were the size of its files, and only three levels were
# populated where the full history populates five. Nothing said the history was
# shallow.
#
# Activity is measured on the history a clone holds. A shallow clone whose first
# commit lies inside the 90-day window cannot say what changed in it, so no activity
# is recorded and the output names the history. A shallow clone that reaches back
# past the window holds every change the window needs, and is measured.

@bead:beadloom-btkd.9 @node:git-activity
Feature: activity is measured on the history a clone holds, and a shallow one is named

  Scenario: a clone one commit deep records no activity, and the reindex says why
    Given a project whose history reaches back 200 days
    And a clone of it 1 commit deep
    When the clone is reindexed from the command line
    Then no node of the clone records activity
    And the reindex says activity was not measured on "history: shallow (1 commit)"

  Scenario: the Gate names the shallow history on its reindex step
    Given a project whose history reaches back 200 days
    And a clone of it 1 commit deep
    When the Gate runs on the clone
    Then the Gate's reindex step warns that activity was not measured on "history: shallow (1 commit)"

  Scenario: a shallow clone that reaches back past the window is measured
    Given a project whose history reaches back 200 days
    And a clone of it 3 commits deep
    When the clone is reindexed from the command line
    Then every node of the clone records the activity the full history gives it
    And the reindex says activity was measured on "history: shallow (3 commits)"
