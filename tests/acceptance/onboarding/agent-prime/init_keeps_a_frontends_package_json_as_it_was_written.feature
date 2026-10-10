# BDL-080 S3f (`beadloom-af99.14`), the S3 review's minor 2 (`beadloom-jtki`). Measured on
# 4b42e86f: init wrote the `lint:fsd` script into a tab-indented package.json with a fixed
# two-space indent, so every line of the adopter's file changed (5 insertions, 4 deletions
# on the reviewer's probe), and wrote it with a plain write that a crash can cut short.
# npm keeps the indentation a package.json already has; so does init now.

@bead:beadloom-af99.14 @node:agent-prime
Feature: init adds its script to a frontend's package.json and changes nothing else

  Scenario Outline: the file keeps its own indentation
    Given a Feature-Sliced frontend whose package.json is indented with <indent>
    When beadloom init is run with --bootstrap
    Then package.json differs from what it was only by the "lint:fsd" script

    Examples:
      | indent   |
      | tabs     |
      | 4 spaces |
