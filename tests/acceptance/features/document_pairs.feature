# BDL-069 S4, beadloom-19m6. This repository ships two READMEs and nothing held
# them against each other. On 2026-09-10 the Russian file carried a paragraph --
# "there is one honest answer here: I did not check this" -- that stood alone in
# Russian and was buried inside the neighbouring paragraph in English, plus an
# opener the English side did not have at all. The only number that differed
# between the two files was a line count, 362 against 360, which nothing reads
# and which cannot be told apart from a translator wrapping differently. The
# drift was found by a person reading the two files side by side.
#
# The comparison is by SHAPE and never by text. The files are in two languages,
# so a text comparison is a check that has to be switched off -- and a check
# somebody switches off is the class this epic is about. What IS comparable is
# the sequence of blocks each file is built from: heading, paragraph, code, list
# and table, with the row counts of the lists and the tables.
#
# The pair is DECLARED in `.beadloom/config.yml`, modelled on `issue_log:`. An
# adopter's translated README is their business, and a project that declares no
# pair is not judged by this check at all.

@bead:beadloom-19m6 @node:document-pairs
Feature: a declared document pair is compared by shape

  Scenario: A declared document pair whose block sequences differ is reported with the population compared
    Given a declared pair whose follower is missing a paragraph the source has
    When the document pairs are compared
    Then the missing paragraph is reported against the heading it stands under
    And the comparison reports how many blocks it compared

  Scenario: The paragraph the English README lost on 2026-09-10 is found by the comparison
    Given the README pair as it stood on 2026-09-10
    When the document pairs are compared
    Then a block present in the Russian file and absent in the English one is reported

  Scenario: A declared pair whose files correspond block for block is reported clean
    Given a declared pair whose two files carry the same blocks in the same order
    When the document pairs are compared
    Then no finding is reported
    And the comparison reports how many blocks it compared

  Scenario: A list that gained a row in one language and not the other is reported
    Given a declared pair whose follower's list carries one row fewer
    When the document pairs are compared
    Then the row count difference is reported against both files

  Scenario: A project that declares no document pair is not judged
    Given a project that declares no document pair
    When the document pairs are compared
    Then the comparison reports that no pair is declared
    And no finding is reported
