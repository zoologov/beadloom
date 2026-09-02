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
  # exited 1 — a success claim withdrawn one line later. The sentence that stood
  # here until `.17` went on to say that the `--bootstrap` branch takes its
  # verdict first and never makes the claim. It makes it, four check marks before
  # the error, and that false reason is why only the wizard withdrew anything for
  # two waves. The `--bootstrap` half is its own scenario below.
  @bead:beadloom-e8s4.9
  Scenario: the wizard withdraws its completion claim before reporting the failure
    Given a project whose only source file sits directly in its source directory
    And a bootstrap that writes the graph and then forgets the edge its rules require
    When beadloom init is run with no flags and its prompts are answered
    Then the command does not report success
    And the completion claim is withdrawn before the failure is reported
    And the claim withdrawn is the wizard's own completion line

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

  # BDL-067 `.15`, the review's major 2 on `.14`. Every scenario above pins one
  # mode, and `.14`'s defect lived in another: 112 tests across this epic's seven
  # files were green while `init --yes --mode both` reported success over a tree
  # its own `lint --strict` failed. The wizard, answering `both` on the same
  # project, reported the failure — two halves of one command disagreeing about
  # one tree. That disagreement is the assertion the review named, and it needs
  # no sabotage: a virgin project with a `docs/` directory produced it on its own.
  # Neither run is asserted to be right here. What is asserted is that they agree,
  # which is a claim that was false while every exit-code assertion in this file
  # was true.
  @bead:beadloom-e8s4.15
  Scenario: the wizard and the non-interactive run agree over the code and the docs together
    Given a project whose only source file sits directly in its source directory
    And a docs directory whose documents the classifier reads as domains
    When the project is initialised twice over, once with the mode flag and once through the wizard
    Then the two runs report the same verdict
    And each run leaves a graph that passes the rules on disk beside it

  # BDL-067 `.15`. The same agreement where the honest answer is red. Without it
  # the scenario above would be satisfied by two entry points that report success
  # unconditionally, which is the state `--yes --mode both` was in. The divergence
  # is applied to the import step because that is the writer whose output the two
  # entry points saw differently: `--yes` re-indexed before it ran, the wizard
  # after.
  @bead:beadloom-e8s4.15
  Scenario: the wizard and the non-interactive run agree over a graph the rules reject
    Given a project whose only source file sits directly in its source directory
    And a docs directory whose documents the classifier reads as domains
    And an import step that adds a domain the rules will not accept without a parent
    When the project is initialised twice over, once with the mode flag and once through the wizard
    Then the two runs report the same verdict
    And neither run reports success
    And each run names the rule the gate will name

  # BDL-067 `.17`, the review's major 1 on `.16`, and a release blocker. The
  # import step attaches what it writes to the graph's single root, and "single"
  # was counted over node ENTRIES rather than over ref_ids. `bootstrap_project`
  # writes the root service node under the project name and its top-level
  # attachment loop skips the cluster whose sanitized name equals that name, so a
  # repository named after one of its own source directories leaves two
  # unparented `service` entries under one ref_id. The import read that as two
  # candidates, attached nothing, and every run of `init --yes --mode both`
  # exited 1 on a rule the same command had just written. `core`, `api`, `web`
  # and `app` are ordinary repository names.
  @bead:beadloom-e8s4.17
  Scenario: a project named after one of its own source directories initialises green
    Given a project named after one of its own source directories
    And a docs directory whose documents the classifier reads as domains
    When beadloom init is run over the code and the docs together
    Then the command reports success
    And every domain in the graph on disk has an outgoing part_of edge
    And the graph on disk passes the rules on disk beside it

  # BDL-067 `.17`, the review's major 2 on `.16`. The report chose both halves of
  # its headline and the sentence under them from ONE boolean — whether this run
  # authored `rules.yml` — with no counterpart for the node. A run that
  # bootstrapped over an `imported.yml` an earlier run had left behind therefore
  # said "the graph this command just wrote" about nodes it had not written, and
  # sent the adopter to file a bug against a writer that had not run in this
  # command at all. The graph file here is put on disk BEFORE the command, so
  # nothing about the run can make it this run's.
  @bead:beadloom-e8s4.17
  Scenario: a graph file this run did not write is not reported as this run's own
    Given a project whose only source file sits directly in its source directory
    And a graph file an earlier run left behind holding a domain with no parent
    When beadloom init is run with the bootstrap flag
    Then the command does not report success
    And the command says the failing node was already there
    And the command does not blame Beadloom's bootstrap
    And the command does not ask for a bug report

  # BDL-067 `.17`, the review's major 3 on `.16`. Every branch announces a
  # scaffold before the verdict runs — the wizard its `Initialization complete!`,
  # `--bootstrap` its four check marks — and only the wizard withdrew it, under a
  # docstring asserting that `--bootstrap` took its verdict first and never made
  # the claim. It makes it. The scenario is stated over `--bootstrap` because
  # that is the branch the claim was false about.
  @bead:beadloom-e8s4.17
  Scenario: the bootstrap flag withdraws the scaffold it announced before reporting the failure
    Given a project whose only source file sits directly in its source directory
    And a bootstrap that writes the graph and then forgets the edge its rules require
    When beadloom init is run with the bootstrap flag
    Then the command does not report success
    And the command announced a scaffold before it withdrew the claim
    And the completion claim is withdrawn before the failure is reported

  # BDL-067 `.17`, the review's minor on `.16`. The report pre-empts the
  # adopter's next command, so what it promises has to survive whichever
  # rendering that command chooses: `beadloom ci` picks `rich` only on a TTY and
  # `github` otherwise, and the github renderer builds its own step line. The
  # promise is stated as the step's name and its summary, which every renderer
  # prints, rather than as one renderer's spelling of them.
  @bead:beadloom-e8s4.17
  Scenario: what the report promises about the gate is printed by every rendering of the gate
    Given a project whose only source file sits directly in its source directory
    And a bootstrap that writes the graph and then forgets the edge its rules require
    When beadloom init is run with the bootstrap flag
    Then the command does not report success
    And the command names the failing gate step and what it will say
    And every rendering the gate offers prints both of those
    And the command quotes no rendering's own step line

  # BDL-067 `.18`, the review's major 4 on `.16` (BDL-UX #216). `--yes --mode
  # both` generated the doc skeletons inside its bootstrap block and imported
  # afterwards, so it classified the documents it had written seconds earlier:
  # four documents where the wizard answering `both` classified one, three of
  # them Beadloom's own scaffolding, two of them arriving under a single ref_id
  # because the importer names a node after the file stem. The defect predates
  # this epic; `.14` changed its character by giving every imported node a
  # `part_of` edge to the root, so what used to be a visible orphan became
  # structurally valid and green. The scenario is therefore stated over what the
  # graph DESCRIBES, not over the verdict, which was already 0 on both sides.
  @bead:beadloom-e8s4.18
  Scenario: neither entry point imports the documents it generated in the same run
    Given a project whose source directory has code-bearing subdirectories
    And a docs directory whose documents the classifier reads as domains
    When the project is initialised twice over and both runs generate doc skeletons
    Then every imported node in either graph names a document the run did not write
    And the two runs leave the same imported graph

  # BDL-067 `.19`. `.17` gave the `--import` branch a verdict: it re-indexes the
  # graph file it just wrote and takes the Gate's reading over the tree, where
  # before it printed "then run `beadloom reindex`" and returned 0 whatever the
  # tree said. That is the one adopter-visible change `.17` made with no scenario
  # over it, and `--import` is the branch no enumeration in this epic reaches over
  # a failing tree: the branch enumerations run at `--mode bootstrap` and the mode
  # enumerations run through `--yes` and the wizard. The rules here are the
  # adopter's, so the run is red over a graph and a rule it did not write, which
  # is why it must not ask for a bug report while still refusing to report success.
  @bead:beadloom-e8s4.19
  Scenario: the import flag judges the tree it leaves without blaming Beadloom for it
    Given a project whose only source file sits directly in its source directory
    And a docs directory whose documents the classifier reads as domains
    And a graph file no writer rewrites, holding a root and a domain with no parent
    And a rules file the adopter wrote requiring every domain to have a parent
    When beadloom init is run with the import flag over that tree
    Then the command does not report success
    And the completion claim is withdrawn before the failure is reported
    And the command does not ask for a bug report

  # BDL-067 `.21`, the review's major 2 on `.20` — BDL-UX #192's sixth instance,
  # on the branch a human adopter meets first. `interactive_init` writes
  # `services.yml` and leaves the adopter's `rules.yml` in place BEFORE it asks
  # "Proceed with this graph?", so `cancel` never meant "nothing was written":
  # it meant the graph was on disk and the command said nothing about whether it
  # passes the rules beside it. Measured by the review: the wizard answering
  # cancel exited 0 while `lint --strict` on the same tree exited 1. The verdict
  # is now taken by any run that wrote a graph file, however it ends, and the
  # message says what is on disk instead of "Cancelled." over it.
  @bead:beadloom-e8s4.21
  Scenario: cancelling the graph review still judges the graph already written
    Given a project whose only source file sits directly in its source directory
    And a rules file the adopter wrote that the bootstrap graph fails
    When beadloom init is run with no flags and the graph review is answered with cancel
    Then the command does not report success
    And the command names the rule the adopter wrote
    And the command says where the graph it had already written is

  # BDL-067 `.21`, the review's major 1 on `.20` — BDL-UX #216 standing on the
  # third entry point. `docs/architecture.md` is a document about the WHOLE
  # graph, and `init --bootstrap` rendered it from the bootstrap's own nodes,
  # so on a tree carrying a graph file from an earlier run it documented part of
  # the tree and wrote no skeleton for the rest. The wizard, which passes no node
  # list, documented all of it. One declared mode, two entry points, two
  # different trees.
  @bead:beadloom-e8s4.21
  Scenario: every entry point documents the whole graph it found, not only its own part
    Given a project whose only source file sits directly in its source directory
    And a graph file no writer rewrites, holding a root and a domain with no parent
    When the bootstrap flag and the wizard are each run over that tree
    Then both runs document the domain the earlier run left
    And the two runs leave the same graph and the same documents

  # BDL-067 `.24`, the review of `.23`'s major 3 — the one defect in this epic
  # that this epic introduced. `.21` removed `generate_skeletons`' node-list
  # parameter, so `init --bootstrap` stopped passing its own nodes and started
  # reading the tree, through the one reader of `.beadloom/_graph/` that carried
  # no guard. An adopter with a hand-edited graph file that does not parse got a
  # raw `yaml.parser.ParserError` traceback instead of a scaffold. The scenario
  # is stated over the READERS and not over the one branch that reached them:
  # there were four readers of that directory with four skip policies, which is
  # the shape `.21` consolidated for the writers, standing on the readers.
  #
  # It says "in init's own modules" because that is the scope `.24` was given and
  # because the wider claim would be false: `reindex.read_declared_docs` walks
  # the same directory with no guard, so the command still ends in a traceback
  # one step later. That residue is measured and pinned in
  # `tests/test_graph_files_are_read_under_one_policy.py`.
  @bead:beadloom-e8s4.24
  Scenario: a hand-edited graph file that does not parse is skipped rather than raised on
    Given a project whose only source file sits directly in its source directory
    And a graph file in .beadloom/_graph/ that is not readable YAML
    When beadloom init is run with the bootstrap flag
    Then no reader in init's own modules raised on the file it could not parse
    And the scaffold is written from the graph files that do parse

  # BDL-067 `.24`, the review of `.23`'s major 4, decided by that review. The
  # corner that asks the adopter to file a bug report is the only one where
  # Beadloom is at fault, and it was chosen by whether this run wrote the FILE
  # the failing node sat in. `generate_skeletons` writes a README for every node
  # in the tree with no document and patches `docs:` back into that node's file,
  # so a node no writer in this run produced was blamed on this run whenever a
  # SIBLING node in the same file was annotated.
  @bead:beadloom-e8s4.24
  Scenario: a failing node an earlier run wrote is not blamed on this one
    Given a project whose only source file sits directly in its source directory
    And a graph file an earlier run left, holding a failing node and an undocumented one
    When beadloom init is run with the bootstrap flag
    Then this run annotates the undocumented node and leaves the failing one alone
    And the command does not report success
    And the command does not ask for a bug report
    And the command says the failing node was already there
