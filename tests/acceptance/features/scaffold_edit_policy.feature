# What `beadloom setup-agentic-flow` does to an edit somebody made by hand
# (BDL-068 S6, BDL-UX #191). One Feature per file.

@bead:beadloom-0mdo.67 @node:agentic-flow-setup
Feature: the scaffold answers a hand edit the same way in every artifact it writes

  The command writes three kinds of artifact into a repository it does not own:
  the role adapters under .claude/agents/, the slash commands under
  .claude/commands/, and .claude/CLAUDE.md. Until this bead it answered a hand
  edit two ways. Measured on a scratch project scaffolded by the shipped
  command, with the same two lines appended to one file of each kind and one
  re-run with no flags: .claude/agents/dev.md was recomposed over, the other two
  were left alone and reported with somewhere to move the edit.

  Nothing said which was intended, and an adopter cannot predict which of their
  edits survive. That is the defect, and it would still be the defect if the
  answer had turned out to be "the scaffold overwrites".

  The answer is that it does not, and it is not a new answer. The --force flag
  is already documented as "Overwrite hand-edited scaffolded flow files (default:
  preserve them)", and `config-check` already prints "It will NOT be rewritten"
  over the very adapter this command was recomposing — under a remediation that
  says to re-run this command. Following that remediation literally destroyed
  the edit it was printed to protect.

  The flow manifest is what makes this a rule rather than a guess: it records the
  SHA-256 of every body Beadloom writes, so "we wrote this" and "somebody changed
  it" are told apart by evidence. Everything Beadloom can prove it wrote is still
  recomposed, so an upgrade still lands.

  Scenario: a hand-edited role adapter survives a re-run of the scaffold
    Given a project that has been scaffolded once
    And "dev" has been edited by hand
    When the scaffold is re-run with no flags
    Then the hand edit in "dev" is still on disk

  Scenario: the scaffold names the adapter it left alone and where the edit belongs
    Given a project that has been scaffolded once
    And "dev" has been edited by hand
    When the scaffold is re-run with no flags
    Then the output names ".claude/agents/dev.md" as left alone
    And the output names ".beadloom/flow/roles/dev.md" as where the edit belongs
    And the output does not claim to have written ".claude/agents/dev.md"

  Scenario: all three artifact kinds answer one hand edit the same way
    Given a project that has been scaffolded once
    And one file of every artifact kind has been edited by hand
    When the scaffold is re-run with no flags
    Then every hand edit is still on disk

  Scenario: an adapter Beadloom last wrote is still recomposed
    Given a project that has been scaffolded once
    And "dev" has been edited by hand
    When the scaffold is re-run with no flags
    Then "review" was recomposed
    And the output names ".claude/agents/review.md" as written

  Scenario: --force is the one door that adopts the composed body
    Given a project that has been scaffolded once
    And "dev" has been edited by hand
    When the scaffold is re-run with --force
    Then the hand edit in "dev" is gone
    And nothing is reported as left alone

  Scenario: the check's own remediation can be followed without losing the edit
    Given a project that has been scaffolded once
    And "dev" has been edited by hand
    When the agent-config check runs
    And the scaffold is re-run with no flags
    Then the file the check said would not be rewritten was not rewritten

  Scenario: the scaffold and --fix decline the same files for the same reasons
    Given a project that has been scaffolded once
    And one file of every artifact kind has been edited by hand
    When the scaffold is re-run with no flags
    Then every adapter --fix declines is one the scaffold left alone

  Scenario: a preserved CLAUDE.md is not reported as written
    Given a project that has been scaffolded once
    And "CLAUDE.md" has been edited by hand
    When the scaffold is re-run with no flags
    Then the output does not claim to have written ".claude/CLAUDE.md"
    And the output names no path under ".claude/commands/" for CLAUDE.md
