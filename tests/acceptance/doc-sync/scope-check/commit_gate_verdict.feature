# BDL-068 S4, `beadloom-0mdo.32` — the residue of `beadloom-mr2l.81`. S1 shipped
# `scope-check` and the pre-commit hook already called it, but it called it as
# `beadloom scope-check --porcelain 2>/dev/null` and printed only when the answer
# came back non-empty. Measured on this repository at `8b40417`: a run that found
# nothing outside and a run that could attribute no work item are BOTH the empty
# string on the stream the hook reads, because the reason goes to stderr. So the
# hook printed the same nothing for both, and a commit nobody could attribute
# read as clean — the false green this epic exists to remove.
#
# Measured over the eleven commits of `features/BDL-068` before this bead: 52
# paths, 11 a node owns, 41 no node owns, 0 findings. Four paths in five were
# never compared at all, and the gate said nothing about that either.

@bead:beadloom-0mdo.32 @node:scope-check
Feature: the commit gate states what it compared, and an unattributable commit is unjudged

  Scenario: A run that could attribute no work item says so where the gate reads
    Given a branch that names no work item
    When the commit gate reads the porcelain verdict
    Then the verdict says the run checked nothing, with the reason
    And the run reports no finding

  Scenario: A run that compared paths states the population it compared over
    Given a work item whose declared axes reach one bounded context
    When the commit gate reads the porcelain verdict
    Then the verdict states how many staged paths a node owns
    And the verdict states how many staged paths no node owns

  Scenario: The verdict is a line the gate can tell apart from a finding
    Given a work item whose declared axes reach one bounded context
    When the commit gate reads the porcelain verdict
    Then the verdict line starts with a marker no reported path can begin with
