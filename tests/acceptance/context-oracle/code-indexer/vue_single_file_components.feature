# BDL-076 J3, `beadloom-tmxa`.
#
# A0 (`beadloom-kcwz`) measured that `.vue` is a code extension with no parser:
# all ten components of this repository's theme and a two-file fixture gave 0
# symbols, so `ctx` showed none of a component's functions and `sync-check` saw a
# component only as a whole-file hash. The owner folded the fix into BDL-076 on
# 2026-09-30: the script blocks are parsed with the existing JS/TS grammar, and
# every symbol is reported at its line in the `.vue` file.

@bead:beadloom-tmxa @node:code-indexer
Feature: The script blocks of a Vue single-file component are read as code

  Scenario: each component shows itself and its script's symbols at their lines in the file
    Given a Vue app with a script setup component, a plain script component and one with both
    When the index is rebuilt and the context of the components node is read
    Then the context shows every component and its script symbols at their lines

  Scenario: an exported constant of a JavaScript module is a symbol
    Given a Vue app with a script setup component, a plain script component and one with both
    When the index is rebuilt and the context of the composables node is read
    Then the context shows the exported constants, the let binding and the default export

  Scenario: a new function in a component's script is reported as a symbol change
    Given a Vue app with a script setup component, a plain script component and one with both
    And its sync baseline is recorded
    When a function is added to the Counter script and the index is rebuilt
    Then sync-check says the other components are unverified because Counter.vue's symbols moved

  Scenario: an edit to a component's style alone moves no symbol
    Given a Vue app with a script setup component, a plain script component and one with both
    And its sync baseline is recorded
    When only the style of Counter is edited and the index is rebuilt
    Then sync-check reports Counter.vue stale by its hash and the other components ok
