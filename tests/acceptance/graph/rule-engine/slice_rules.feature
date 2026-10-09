# BDL-080 S3c (`beadloom-5t8d`), RFC D4. Feature-Sliced Design enters a slice through the
# `index` at its top and gives a slice its shape: the segments `ui model lib api config`.
# `forbid_import` cannot say "past the index" — its globs see import paths, and
# `@/features/auth` and `@/features/auth/model/session` differ only by what an alias table
# makes of them — so `slice_public_api` reads the imports the reindex resolved.
#
# The graph is written by hand here, so the rules are judged without `init`'s preset.

@bead:beadloom-5t8d @node:rule-engine
Feature: a slice is entered through its index and holds only its segments

  Scenario: an import past another slice's index is reported, one through it is not
    Given the synthetic FSD frontend with a hand-written graph of its slices
    And the rules declare slice_public_api over the four sliced layers
    When the project is linted
    Then "slice_public_api" reports "src/widgets/header/ui/Header.ts" reaching into "features-auth"
    And "slice_public_api" reports nothing from "src/pages/home/ui/HomePage.vue"

  Scenario: a folder that is no segment is reported against its slice
    Given the synthetic FSD frontend with a hand-written graph of its slices
    And the rules declare slice_shape over the four sliced layers
    When the project is linted
    Then "slice_shape" reports the folder "helpers/" of "features-cart"
    And "slice_shape" reports nothing about "features-auth"

  Scenario: a slice rule whose tags no node carries says it checks nothing
    Given the synthetic FSD frontend with a hand-written graph of its slices
    And the rules declare slice_public_api over the tag "fsd-nowhere"
    When the project is linted
    Then the rule is reported as checking nothing because no node carries "fsd-nowhere"
