# BDL-076 K2, `beadloom-oo4m`.
#
# A0 (`beadloom-kcwz`) measured it on this repository's site: the theme node held
# 17 sync pairs, one per file, through its declared `source`. One
# `// beadloom:component=` annotation in one `.vue` file left ONE pair. The engine
# took the annotated files OR the source-owned files, never both, so the other 16
# files were held to no document. Nothing said so, because the coverage backstop
# listed only `*.py` files directly inside the source directory.
#
# The repair has two halves. A file that carries no annotation stays with the node
# that owns it by `source`, whatever its siblings carry. And the backstop reads the
# code files the index holds, in every language the reindex reads, so a file that
# still ends up paired with no document is named.

@bead:beadloom-oo4m @node:sync-check
Feature: A node with one annotated file keeps a sync pair for every file

  Scenario: every file of a JavaScript and Vue node keeps its pair when one file is annotated
    Given a Vue node of three files in three folders, only the JavaScript model annotated
    When the index is rebuilt and sync-check runs
    Then each of the three files is paired with the node's document

  Scenario: an edit to the unannotated Vue file is reported stale
    Given a Vue node of three files in three folders, only the JavaScript model annotated
    And its sync baseline is recorded
    When only the template of the unannotated Vue file is edited and the index is rebuilt
    Then sync-check reports the Vue file's pair stale and its siblings ok

  Scenario: a Vue file whose annotation names no node is named, not dropped
    Given a Vue node of three files in three folders, only the JavaScript model annotated
    And a fourth Vue file in the node whose annotation misspells the node
    When the index is rebuilt and sync-check runs
    Then sync-check names the misspelled Vue file as untracked under the node's document
