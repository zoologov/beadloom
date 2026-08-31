# BDL-067, closing BDL-UX #192.
#
# `beadloom init --yes --mode bootstrap` wrote a graph and, one step later,
# wrote the rules that graph fails. Measured on a TypeScript project with a
# single flat `src/index.ts`: rc 0, `Graph: 2 nodes, 0 edges`, then
# `lint --strict` rc 1 on `domain-needs-parent`.
#
# The hole is one branch of `bootstrap_project` — the fallback that runs when
# no source dir has code-bearing subdirectories. It writes one node per source
# dir at the preset's default kind (`domain` under MONOLITH) and no edge, and
# the root-attachment loop that would have rescued it iterates the clusters,
# which are empty on exactly that path.
#
# The scenarios below are stated over the bootstrap's output, not over the one
# branch, because a branch patch leaves the next branch free to forget the edge
# again. The fixture is a project that is not us: a rule that passed by
# recognising Beadloom's own tree would fail these.

@bead:beadloom-e8s4.1 @node:agent-prime
Feature: the bootstrap writes a graph that satisfies the rules it writes

  Scenario: A flat single-source-dir project bootstraps into a graph that passes its own rules
    Given a project whose only source file sits directly in its source directory
    When the project is bootstrapped
    And the bootstrapped graph is linted
    Then the lint reports no error-severity violation

  Scenario: Every domain the bootstrap writes carries a part_of edge
    Given a project whose only source file sits directly in its source directory
    When the project is bootstrapped
    Then every node written with kind domain has an outgoing part_of edge
    And each of those edges names the root node by the ref_id the bootstrap wrote

  Scenario: A parenthesised project name is still the name the edge points at
    Given a project whose name carries parentheses and whose source file sits directly in its source directory
    When the project is bootstrapped
    Then every node written with kind domain has an outgoing part_of edge
    And each of those edges names the root node by the ref_id the bootstrap wrote
    And every edge the bootstrap wrote points at a node the bootstrap wrote

  Scenario: A nested project keeps the parent its classifier chose
    Given a project whose source directory has code-bearing subdirectories
    When the project is bootstrapped
    Then no domain is attached to the root when its classifier already gave it a parent

  # BDL-067 `.2` — the other half, and the reason it is stated over `init` rather
  # than over the bootstrap: `.1` fixed the instance, so this scenario has to
  # CONSTRUCT a divergence instead of waiting for one. The step below writes the
  # real graph and the real rules and then takes the `part_of` edges back out, so
  # what `init` faces is exactly the shape #192 reported — on a bootstrap that is
  # no longer capable of producing it by itself.
  @bead:beadloom-e8s4.2
  Scenario: init does not report success over a graph that fails the rules it just wrote
    Given a project whose only source file sits directly in its source directory
    And a bootstrap that writes the graph and then forgets the edge its rules require
    When beadloom init is run on the project
    Then the command does not report success
    And the command names the rule the gate will name

  # BDL-067 `.6` — the third branch, and the one a human adopter meets first.
  # `.2` guarded `--yes` and `--bootstrap` and stopped there, because the tests
  # that covered them were parametrised over the two BINDINGS of
  # `bootstrap_project` and the wizard shares the `--yes` one. The Given below is
  # the same step the scenario above uses, unchanged, which is the whole point:
  # the sabotage could always reach this branch, and nothing ran it.
  @bead:beadloom-e8s4.6
  Scenario: the default wizard does not report success over such a graph either
    Given a project whose only source file sits directly in its source directory
    And a bootstrap that writes the graph and then forgets the edge its rules require
    When beadloom init is run with no flags and its prompts are answered
    Then the command does not report success
    And the command names the rule the gate will name

  # BDL-067 `.6`, the review's minor 4. Nothing here is wrong with the graph: the
  # rules file cannot be read at all, and the gate reports that through a finding
  # whose rule name is the gate step's own.
  @bead:beadloom-e8s4.6
  Scenario: a rules file that will not load is reported as what is wrong with the file
    Given a project whose only source file sits directly in its source directory
    And a bootstrap that leaves behind a rules file the loader will not read
    When beadloom init is run on the project
    Then the command does not report success
    And the command says what the loader could not read
    And the command does not offer the gate step's own name as a rule
