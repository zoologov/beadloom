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

  # BDL-067 `.7`. The carve-out, written down as a decision instead of living
  # only in a condition. `init` skips the verdict on exactly one bootstrap path:
  # the wizard's `edit` answer, which has just handed `services.yml` to the user
  # and told them to re-index, so nothing has settled to be judged. The scenario
  # above is the other half — same fixture, same sabotage, the `yes` answer — and
  # neither half states the claim alone: one says the wizard is judged, this one
  # says which single answer is not.
  @bead:beadloom-e8s4.7
  Scenario: the wizard's edit answer hands the graph back instead of judging it
    Given a project whose only source file sits directly in its source directory
    And a bootstrap that writes the graph and then forgets the edge its rules require
    When beadloom init is run with no flags and the graph review is answered with edit
    Then the command reports success
    And the command tells the user to re-index after editing

  # BDL-067 `.9`, the review's major 1 on `.8`. `bootstrap_project` writes
  # `rules.yml` only when the file is not already there, so on a re-init — or
  # over rules an earlier Beadloom or a hand edit left behind — the rule that
  # fails is the adopter's own, and `init` told them it was ours and asked them
  # to report it. Nothing below is patched: the bootstrap and the linter are the
  # real ones, and the fixture is a rules file that was on disk first.
  @bead:beadloom-e8s4.9
  Scenario: a rule the command did not write is not reported as a Beadloom defect
    Given a project whose only source file sits directly in its source directory
    And a rules file the adopter wrote that the bootstrap graph fails
    When beadloom init is run with the bootstrap flag
    Then the command does not report success
    And the command names the rule the adopter wrote
    And the command does not blame Beadloom's bootstrap
    And the command does not ask for a bug report
    And the command says the rules file was already there

  # BDL-067 `.9`, the review's minor 2. `interactive_init` prints its own tail
  # before returning, so the wizard announced `Initialization complete!` and then
  # exited 1 — a success claim withdrawn one line later. The `--bootstrap` branch
  # takes its verdict before its `Next steps` and never makes the claim.
  @bead:beadloom-e8s4.9
  Scenario: the wizard withdraws its completion claim before reporting the failure
    Given a project whose only source file sits directly in its source directory
    And a bootstrap that writes the graph and then forgets the edge its rules require
    When beadloom init is run with no flags and its prompts are answered
    Then the command does not report success
    And the completion claim is withdrawn before the failure is reported

  # BDL-067 `.12`, the review's major 1 on `.11`. The withdrawal is one string
  # shared by the two shapes of red the wizard can reach, and it was written for
  # one of them. Over a `rules.yml` the loader will not read, no rule is
  # evaluated at all, so a headline saying the graph does not pass its rules is
  # denied by the two lines printed under it — and its colon promises a list of
  # failing rules where a parse error follows. The unloadable file is covered
  # above only on the `--bootstrap` branch, which prints no withdrawal, so this
  # contradiction could not appear there.
  @bead:beadloom-e8s4.12
  Scenario: the wizard withdraws its completion claim without naming rules that never ran
    Given a project whose only source file sits directly in its source directory
    And a bootstrap that leaves behind a rules file the loader will not read
    When beadloom init is run with no flags and its prompts are answered
    Then the command does not report success
    And the completion claim is withdrawn before the failure is reported
    And the withdrawal does not say a rule failed
    And the command says what the loader could not read

  # BDL-067 `.14`, the review's major 1 on `.13`. `.1` stated the domain-parent
  # post-condition over `bootstrap_project`'s output, and `import_docs` is a
  # SECOND writer of `domain` nodes that never received it: every document it
  # cannot classify becomes a domain with no `part_of` edge, in `imported.yml`,
  # in the same run that writes `domain-needs-parent` at error severity.
  # Measured on this fixture before the fix: `init --yes --mode both` rc 0,
  # `lint --strict` rc 1 on three nodes.
  @bead:beadloom-e8s4.14
  Scenario: importing documents alongside the code leaves a graph that passes its own rules
    Given a project whose only source file sits directly in its source directory
    And a docs directory whose documents the classifier reads as domains
    When beadloom init is run over the code and the docs together
    Then the command reports success
    And every domain in the graph on disk has an outgoing part_of edge
    And the graph on disk passes the rules on disk beside it

  # BDL-067 `.14`, the second half of the same finding. The verdict read an index
  # written BEFORE the import step wrote `imported.yml`, because the reindex sat
  # inside the bootstrap block, so `init` judged a graph it had not finished
  # writing. The divergence is ADDED to the import step rather than taken out of
  # it, so the instrument does not depend on what `import_docs` writes: a
  # sabotage that removed edges would be a no-op on the defect it is meant to
  # expose, and would go green for the wrong reason.
  @bead:beadloom-e8s4.14
  Scenario: the verdict sees the graph file the import step wrote after the reindex
    Given a project whose only source file sits directly in its source directory
    And a docs directory whose documents the classifier reads as domains
    And an import step that adds a domain the rules will not accept without a parent
    When beadloom init is run over the code and the docs together
    Then the command does not report success
    And the command names the rule the gate will name

  # BDL-067 `.14`. The reviewer's second reproduction, and the one that needs no
  # bootstrap at all: over a project that is already initialised, `init --import`
  # writes `imported.yml` against rules that are already on disk. It takes no
  # verdict, so nothing here asserts an exit code — the claim is that the file it
  # leaves behind does not fail those rules.
  @bead:beadloom-e8s4.14
  Scenario: importing into a graph that already exists attaches the imported nodes to its root
    Given a project whose only source file sits directly in its source directory
    And a docs directory whose documents the classifier reads as domains
    And the project has already been initialised from its code
    When beadloom init is run with the import flag
    Then every domain in the graph on disk has an outgoing part_of edge
    And the graph on disk passes the rules on disk beside it
