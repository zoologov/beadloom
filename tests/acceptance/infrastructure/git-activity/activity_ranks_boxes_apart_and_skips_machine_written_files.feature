# BDL-078 `beadloom-btkd.1`. The owner, after F-activity (`beadloom-lw56`): a box rolls up
# its parts, so in one population with the leaves it outranks them -- 7 of this
# repository's 10 hot nodes were boxes. And a lock file counts as work: package-lock.json
# was 3,912 of vitepress-site's 17,714 changed lines in 30 days. A box is ranked among
# boxes and a leaf among leaves; a file a machine wrote is not change.

@bead:beadloom-btkd.1 @node:git-activity
Feature: activity ranks a box among boxes and does not count what a machine wrote

  Scenario: a leaf is not pushed down by the boxes that hold it
    Given a repository whose history reaches main only through squash merges
    When its activity is analysed
    Then among the boxes "app" is hot and "core" is cool
    And among the leaves "parser" is hot, "api" warm and "ui" cool

  Scenario: a lock file a package manager rewrote is not change
    Given a repository where one commit adds 5 lines to "web/app.js" and 4000 to "web/package-lock.json"
    When its activity is analysed
    Then the node "web" has 5 lines changed in 30 days

  Scenario: a file git marks generated is not change
    Given a repository whose ".gitattributes" marks "gen/*" linguist-generated
    And one commit adds 700 lines to "gen/client.py" only
    When its activity is analysed
    Then the node "gen" has no change in 90 days

  Scenario: a file pattern the project declares is not change
    Given a project whose config excludes "*.pb.go" from activity
    And one commit adds 900 lines to "src/proto/api.pb.go" and 4 to "src/proto/api.go"
    When the project is reindexed
    Then the stored activity of "proto" has 4 lines changed in 30 days
