# BDL-062 bead `.3`. Measured on `main`@`cdc16de`: `_collect_mcp_tool_count` takes no
# `project_root` and `_collect_cli_command_count` counts the running Click group, so in
# EVERY adopter repository `docs audit` declared two facts about Beadloom as facts about
# their documentation — and counted them in the denominator of "N of 9 verified".
#
# The second half is the denominator's shape. A fact that could not be computed was
# "silently omitted" (the collector's own docstring), so the audit's ignorance left no
# trace: measured in-process on this repository, an unregistered CLI surface turned
# "3 of 9 declared fact(s) verified" into "3 of 8" and nothing said which fact left.
#
# After this bead the audit reports three populations: verified, not applicable to this
# project (with the reason), and declared but unverified (named, never counted as fine).

@bead:beadloom-viaj.3 @node:docs-audit
Feature: the audit reports facts about the project it audits, and names what it did not check

  Scenario: A project that is not Beadloom is told no facts about Beadloom
    Given a Python project that is not Beadloom
    When the audit collects that project's facts
    Then no declared fact carries a value read from Beadloom's own source
    And the MCP tool count is reported not applicable, and the reason names the project

  Scenario: Beadloom's own repository still reports the surfaces it provides
    Given the project under audit is Beadloom's own repository
    When the audit collects that project's facts
    Then the MCP tool count equals the length of the tool catalogue
    And the CLI command count equals the number of commands the CLI registers

  Scenario: A fact the audit could not compute is named with its reason, not dropped
    Given a Python project that is not Beadloom
    When the audit collects that project's facts
    Then every fact the audit declined to declare carries a reason

  Scenario: A declared fact nothing states is named beside the count of verified ones
    Given a Python project that is not Beadloom
    When the audit runs over that project's documents
    Then the report states how many of the declared facts were verified
    And it names version among the facts declared but unverified
    And the three populations share no fact between them
