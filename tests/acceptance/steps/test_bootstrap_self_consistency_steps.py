"""Step implementations for `features/bootstrap_self_consistency.feature`.

BDL-067, closing BDL-UX #192. The `.1` steps run the real `bootstrap_project`
and the real linter over real directories; nothing there is stubbed, because a
stub would agree with whatever the bootstrap currently writes and that is the
thing under test.

The one `.2` step that does patch — `a bootstrap that writes the graph and then
forgets the edge its rules require` — patches for the opposite reason. `.1` made
a self-contradicting graph impossible to obtain honestly, so the divergence
`init` is asked to notice has to be CONSTRUCTED. It is constructed at the graph
only: the real bootstrap runs, the real `generate_rules` writes
`domain-needs-parent`, and the `part_of` edges are then taken back out of
`services.yml`. Nothing about `init`'s verdict is faked.

**FAKES PROVE FAKES.** Every fixture here is a project that is not Beadloom —
`orders-web`, `orders (web)`, `supply-chain/src/platform/orders`. None of those
names exists in this repository, so a fix that worked by recognising our own
tree would fail these.

The fixtures are built here rather than imported from `tests.adopter_project`,
which holds the same TypeScript shape. `tests/test_bead14_s4_binding.py` copies
`tests/acceptance/` out of the repository and runs it standalone to prove a
broken step binding reddens the suite, and in that copy the `tests` package is
not importable — an import of it turns that sabotage into a collection failure,
which proves nothing about the binding.

The module is named `test_*` so default pytest collection picks the scenarios up.
"""

from __future__ import annotations

import json
import shutil
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.application.reindex import incremental_reindex
from beadloom.graph.linter import lint
from beadloom.onboarding.scanner import bootstrap_project
from beadloom.onboarding.scanner.doc_classify import import_docs
from beadloom.services.cli import main
from beadloom.services.commands.setup import WITHDRAWN_COMPLETION_CLAIM

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../features/bootstrap_self_consistency.feature")

#: A project name that survives `_sanitize_ref_id` only by losing characters.
#: The root's ref_id is written unsanitised, so an edge that recomputes the
#: name from the project instead of reading the node points at nothing.
PARENTHESISED_NAME = "orders (web)"

#: The rule `generate_rules` writes for any graph holding a domain, and the rule
#: BDL-UX #192's reporter read out of `lint --strict` after a green `init`. The
#: scenario asserts this exact string: "the command failed" is not the fact the
#: adopter needs, the name they will meet again in the Gate's output is.
THE_RULE = "domain-needs-parent"

#: A `rules.yml` the loader refuses, and the part of its complaint an adopter
#: needs to read. `bootstrap_project` never rewrites a rules file that is already
#: there, so a hand edit that will not parse is a file `init` can meet.
UNLOADABLE_RULES = "rules:\n  - name: hand-edited\n    require:\n      match: {}\n"
THE_LOADER_COMPLAINT = "missing required 'version' field"

#: The gate step's own name, which its `LintError` finding carries in `rule`.
#: Printed as though it were a rule, it names a rule no rules file contains.
THE_STEP_NAME = "lint"

#: A rules file the ADOPTER wrote — valid, loadable, and failed by any graph the
#: bootstrap writes. `generate_rules` dropped `service-needs-parent` for exactly
#: the reason it fails here: the root service node has no parent by definition.
THE_ADOPTERS_RULE = "service-needs-parent"
THE_ADOPTERS_RULES_FILE = """\
version: 1
rules:
  - name: service-needs-parent
    description: Every service must have a part_of edge
    require:
      for:
        kind: service
      has_edge_to: {}
      edge_kind: part_of
"""

#: The sentence that is true only when the bootstrap authored `rules.yml`, and
#: the request that follows it.
THE_BLAME = "defect in Beadloom's bootstrap"
THE_BUG_REPORT_REQUEST = "please report it"

#: What the adopter is told instead, and the file they have to open.
THE_FILE_WAS_ALREADY_THERE = "did not write"
THE_RULES_PATH = ".beadloom/_graph/rules.yml"

#: The wizard's success claim, and the first word of the report that follows it.
THE_COMPLETION_CLAIM = "Initialization complete!"
THE_FAILURE_REPORT = "Error:"


@pytest.fixture()
def world() -> dict[str, Any]:
    return {}


def _flat_project(root: Path) -> Path:
    """One source file directly under `src/` — no code-bearing subdirectory.

    The shape BDL-UX #192 was reported against, and the same shape
    `tests.adopter_project.typescript_project` builds: a Node manifest whose
    name the root node takes, and a single flat `src/index.ts`.
    """
    project = root / "orders-web"
    (project / "src").mkdir(parents=True)
    (project / "package.json").write_text(
        json.dumps({"name": "orders-web", "version": "0.4.1"}, indent=2) + "\n",
        encoding="utf-8",
    )
    (project / "src" / "index.ts").write_text("export const orders = [];\n", encoding="utf-8")
    return project


def _parenthesised_project(root: Path) -> Path:
    """The same flat shape under a name `_sanitize_ref_id` would rewrite.

    No manifest, so `_detect_project_name` falls back to the directory name and
    the root node's ref_id keeps its parentheses.
    """
    project = root / PARENTHESISED_NAME
    (project / "src").mkdir(parents=True)
    (project / "src" / "index.ts").write_text("export const orders = [];\n", encoding="utf-8")
    return project


def _nested_project(root: Path) -> Path:
    """A source dir with a code-bearing subdirectory whose child is a domain.

    `platform` and `orders` match no preset pattern, so both classify at the
    MONOLITH default kind `domain`. `orders` therefore has a classified parent
    and must keep it.
    """
    project = root / "supply-chain"
    orders = project / "src" / "platform" / "orders"
    orders.mkdir(parents=True)
    boot = project / "src" / "platform" / "boot.ts"
    boot.write_text("export const b = 1;\n", encoding="utf-8")
    (orders / "orders.ts").write_text("export const o = 1;\n", encoding="utf-8")
    return project


@given("a project whose only source file sits directly in its source directory")
def _given_flat(world: dict[str, Any], tmp_path: Path) -> None:
    world["project"] = _flat_project(tmp_path)


@given(
    "a project whose name carries parentheses and whose source file sits "
    "directly in its source directory"
)
def _given_parenthesised(world: dict[str, Any], tmp_path: Path) -> None:
    world["project"] = _parenthesised_project(tmp_path)


@given("a project whose source directory has code-bearing subdirectories")
def _given_nested(world: dict[str, Any], tmp_path: Path) -> None:
    world["project"] = _nested_project(tmp_path)


@when("the project is bootstrapped")
def _when_bootstrapped(world: dict[str, Any]) -> None:
    world["result"] = bootstrap_project(world["project"])


@when("the bootstrapped graph is linted")
def _when_linted(world: dict[str, Any]) -> None:
    world["lint"] = lint(world["project"], reindex=incremental_reindex)


@then("the lint reports no error-severity violation")
def _then_no_errors(world: dict[str, Any]) -> None:
    result = world["lint"]
    assert not result.has_errors, [
        (v.rule_name, v.from_ref_id, v.message) for v in result.violations
    ]


@then(parsers.parse("every node written with kind {kind} has an outgoing part_of edge"))
def _then_every_node_of_kind_is_parented(world: dict[str, Any], kind: str) -> None:
    nodes = world["result"]["nodes"]
    parented = {e["src"] for e in world["result"]["edges"] if e["kind"] == "part_of"}
    orphans = [n["ref_id"] for n in nodes if n["kind"] == kind and n["ref_id"] not in parented]
    assert not orphans, f"{kind} nodes with no part_of edge: {orphans}"
    # Guard: a graph with no node of this kind would pass the assertion above
    # without exercising anything.
    assert any(n["kind"] == kind for n in nodes), f"fixture produced no {kind} node"


@then("each of those edges names the root node by the ref_id the bootstrap wrote")
def _then_dst_is_the_written_root(world: dict[str, Any]) -> None:
    nodes = world["result"]["nodes"]
    root_ref_id = next(n["ref_id"] for n in nodes if n["kind"] == "service")
    domains = {n["ref_id"] for n in nodes if n["kind"] == "domain"}
    dsts = {
        e["dst"]
        for e in world["result"]["edges"]
        if e["kind"] == "part_of" and e["src"] in domains
    }
    assert dsts == {root_ref_id}, f"expected part_of -> {root_ref_id!r}, got {sorted(dsts)}"


@then("every edge the bootstrap wrote points at a node the bootstrap wrote")
def _then_edges_resolve(world: dict[str, Any]) -> None:
    ref_ids = {n["ref_id"] for n in world["result"]["nodes"]}
    dangling = [e for e in world["result"]["edges"] if e["dst"] not in ref_ids]
    assert not dangling, f"edges pointing at no node: {dangling}"


@then("no domain is attached to the root when its classifier already gave it a parent")
def _then_classified_parent_is_kept(world: dict[str, Any]) -> None:
    nodes = world["result"]["nodes"]
    root_ref_id = next(n["ref_id"] for n in nodes if n["kind"] == "service")
    part_of = [e for e in world["result"]["edges"] if e["kind"] == "part_of"]
    nested = [e for e in part_of if e["dst"] != root_ref_id]
    assert nested, f"fixture produced no classified parent: {part_of}"
    for edge in nested:
        siblings = [e for e in part_of if e["src"] == edge["src"]]
        assert len(siblings) == 1, f"{edge['src']} was attached twice: {siblings}"


@given("a bootstrap that writes the graph and then forgets the edge its rules require")
def _given_a_forgetful_bootstrap(monkeypatch: pytest.MonkeyPatch) -> None:
    """Re-create #192's shape on a bootstrap that can no longer produce it.

    Only the graph half is sabotaged: the real `generate_rules` still writes
    `domain-needs-parent`, and the real `bootstrap_project` still runs. The
    `part_of` edges are taken back out of `services.yml` afterwards, which is
    what makes this a test of `init`'s verdict rather than a second test of `.1`.

    BOTH bindings are patched, since BDL-067 `.17`. `init --yes` and the wizard
    reach `bootstrap_project` through the name `init_flow` binds at import time;
    `init --bootstrap` imports it from the package inside the command body. Only
    the first was patched here, so this step silently did nothing on the
    `--bootstrap` branch and any scenario written over that branch would have run
    an unsabotaged bootstrap and passed for the wrong reason. Confusing the two
    bindings for the two branches is what let the wizard ship unguarded through
    four green waves (BDL-067 `.6`), and it was still in this fixture.
    """
    real = bootstrap_project

    def forgetful(project_root: Path, **kwargs: Any) -> dict[str, Any]:
        result = real(project_root, **kwargs)
        services = project_root / ".beadloom" / "_graph" / "services.yml"
        data = yaml.safe_load(services.read_text(encoding="utf-8"))
        # `bootstrap_project` writes no `edges:` key when there are none, so the
        # sabotaged file keeps the shape the bug was reported against.
        data.pop("edges", None)
        services.write_text(
            yaml.safe_dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        result["edges"] = []
        result["edges_generated"] = 0
        return result

    for binding in (
        "beadloom.onboarding.scanner.init_flow.bootstrap_project",
        "beadloom.onboarding.bootstrap_project",
    ):
        monkeypatch.setattr(binding, forgetful)


@when("beadloom init is run on the project")
def _when_init_is_run(world: dict[str, Any]) -> None:
    world["init"] = CliRunner().invoke(
        main,
        ["init", "--yes", "--mode", "bootstrap", "--project", str(world["project"])],
    )


@then("the command does not report success")
def _then_init_failed(world: dict[str, Any]) -> None:
    result = world["init"]
    assert result.exit_code != 0, result.output


@then("the command names the rule the gate will name")
def _then_init_names_the_rule(world: dict[str, Any]) -> None:
    result = world["init"]
    assert THE_RULE in result.output, result.output


@given("a bootstrap that leaves behind a rules file the loader will not read")
def _given_an_unreadable_rules_file(monkeypatch: pytest.MonkeyPatch) -> None:
    """The graph is untouched; what fails is reading the rules at all.

    That is the gate's `LintError` branch, where the finding's `rule` is the step
    name and the loader's complaint is in `why` — the shape `init` used to render
    as a rule name, telling the adopter a rule called `lint` had failed.
    """
    real = bootstrap_project

    def with_broken_rules(project_root: Path, **kwargs: Any) -> dict[str, Any]:
        result = real(project_root, **kwargs)
        rules = project_root / ".beadloom" / "_graph" / "rules.yml"
        rules.write_text(UNLOADABLE_RULES, encoding="utf-8")
        return result

    monkeypatch.setattr(
        "beadloom.onboarding.scanner.init_flow.bootstrap_project", with_broken_rules
    )


@when("beadloom init is run with no flags and its prompts are answered")
def _when_the_wizard_is_run(world: dict[str, Any]) -> None:
    """Plain `beadloom init`: choose the bootstrap mode, accept the graph.

    The doc-skeleton prompt is declined, which keeps the scenario about the
    verdict and off the skeleton writer.
    """
    with (
        patch("rich.prompt.Prompt.ask", side_effect=["bootstrap", "yes"]),
        patch("rich.prompt.Confirm.ask", return_value=False),
    ):
        world["init"] = CliRunner().invoke(
            main, ["init", "--project", str(world["project"])]
        )


@then("the command says what the loader could not read")
def _then_init_names_the_loader_complaint(world: dict[str, Any]) -> None:
    result = world["init"]
    assert THE_LOADER_COMPLAINT in result.output, result.output


@then("the command does not offer the gate step's own name as a rule")
def _then_init_does_not_name_the_step(world: dict[str, Any]) -> None:
    result = world["init"]
    named = [line for line in result.output.splitlines() if line == f"  {THE_STEP_NAME}"]
    assert not named, result.output


@when("beadloom init is run with no flags and the graph review is answered with edit")
def _when_the_wizard_is_asked_to_edit(world: dict[str, Any]) -> None:
    """Plain `beadloom init`, choosing to edit the graph by hand.

    The same wizard and the same sabotage as the scenario above. Only the answer
    to the graph review differs, which is what makes the pair a claim about the
    answer rather than about the branch.
    """
    with (
        patch("rich.prompt.Prompt.ask", side_effect=["bootstrap", "edit"]),
        patch("rich.prompt.Confirm.ask", return_value=False),
    ):
        world["init"] = CliRunner().invoke(
            main, ["init", "--project", str(world["project"])]
        )


@then("the command reports success")
def _then_init_succeeded(world: dict[str, Any]) -> None:
    result = world["init"]
    assert result.exit_code == 0, result.output


@then("the command tells the user to re-index after editing")
def _then_init_asks_for_a_reindex(world: dict[str, Any]) -> None:
    """Also the guard against a vacuous green.

    A zero from a wizard that fell over before the review prompt would satisfy
    the assertion above while saying nothing about the carve-out. The re-index
    instruction is printed only on the `edit` answer, so it is the evidence that
    the branch under test is the branch that ran.
    """
    result = world["init"]
    assert "beadloom reindex" in result.output, result.output


@given("a rules file the adopter wrote that the bootstrap graph fails")
def _given_the_adopters_own_rules(world: dict[str, Any]) -> None:
    """Put a valid rules file on disk before `init` runs, and patch nothing.

    `bootstrap_project` writes `rules.yml` only when the file is not already
    there, so this one file is the entire fixture: the real bootstrap runs, the
    real linter runs, and the rule that fails is one the command did not write.
    `generate_rules` dropped `service-needs-parent` for exactly the reason it
    fails here — the root service node has no parent by definition — so a project
    carrying a hand-written rule of that name is a project whose red is its own.
    """
    graph_dir = world["project"] / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True, exist_ok=True)
    (graph_dir / "rules.yml").write_text(THE_ADOPTERS_RULES_FILE, encoding="utf-8")


@when("beadloom init is run with the bootstrap flag")
def _when_init_bootstrap_is_run(world: dict[str, Any]) -> None:
    """`init --bootstrap`, which keeps a `.beadloom/` that is already there.

    `--yes` cannot reach this case and is not asked to: `non_interactive_init`
    returns `skipped` over an existing `.beadloom/` and deletes the whole
    directory under `--force`, so the rules file that branch meets is always the
    one it just wrote.
    """
    world["init"] = CliRunner().invoke(
        main, ["init", "--bootstrap", "--project", str(world["project"])]
    )


@then("the command names the rule the adopter wrote")
def _then_init_names_the_adopters_rule(world: dict[str, Any]) -> None:
    result = world["init"]
    assert THE_ADOPTERS_RULE in result.output, result.output


@then("the command does not blame Beadloom's bootstrap")
def _then_init_does_not_blame_us(world: dict[str, Any]) -> None:
    result = world["init"]
    # Anti-vacuity: a command that printed nothing satisfies a negative claim.
    assert result.exit_code != 0, result.output
    assert THE_BLAME not in result.output, result.output


@then("the command does not ask for a bug report")
def _then_init_does_not_ask_for_a_report(world: dict[str, Any]) -> None:
    """The cost of the defect: a tracker filled with adopters' own rules."""
    result = world["init"]
    assert result.exit_code != 0, result.output
    assert THE_BUG_REPORT_REQUEST not in result.output, result.output


@then("the command says the rules file was already there")
def _then_init_says_the_file_predates_it(world: dict[str, Any]) -> None:
    """Withholding the blame is half an answer; the adopter needs the reason."""
    result = world["init"]
    assert THE_FILE_WAS_ALREADY_THERE in result.output, result.output
    assert THE_RULES_PATH in result.output, result.output


@then("the completion claim is withdrawn before the failure is reported")
def _then_the_claim_is_withdrawn(world: dict[str, Any]) -> None:
    """Every branch claims something, so every branch has to take it back.

    Written without naming any one branch's wording, since BDL-067 `.17`. It
    used to assert the wizard's `Initialization complete!`, which made it a step
    only the wizard could satisfy — the same shape as the code it covers, where
    the withdrawal was passed in by the one caller that remembered. What every
    branch shares is that it printed something above the withdrawal, and that is
    what the anti-vacuity assertion is stated over. The wizard's own string keeps
    its own step below.
    """
    output = world["init"].output
    withdrawn = output.find(WITHDRAWN_COMPLETION_CLAIM)
    reported = output.index(THE_FAILURE_REPORT)
    assert withdrawn != -1, output
    # Anti-vacuity: with nothing announced there is nothing to withdraw, and the
    # ordering below would be a statement about lines that never appeared.
    assert [line for line in output[:withdrawn].splitlines() if line.strip()], output
    assert withdrawn < reported, output


@then("the claim withdrawn is the wizard's own completion line")
def _then_the_wizards_claim_is_the_one_withdrawn(world: dict[str, Any]) -> None:
    """`Initialization complete!` is the string BDL-067 `.9` was reported against.

    Kept as its own step after the one above widened to every branch: a wizard
    that stopped printing it before a red verdict is still a change somebody has
    to notice.
    """
    output = world["init"].output
    claimed = output.index(THE_COMPLETION_CLAIM)
    withdrawn = output.find(WITHDRAWN_COMPLETION_CLAIM)
    reported = output.index(THE_FAILURE_REPORT)
    assert withdrawn != -1, output
    assert claimed < withdrawn < reported, output


@then("the withdrawal does not say a rule failed")
def _then_the_withdrawal_names_no_rule(world: dict[str, Any]) -> None:
    """On this branch the rules file never loaded, so no rule was evaluated.

    Read off the line the adopter sees rather than off the constant, so that a
    second withdrawal string added later is judged by the same claim. The
    trailing colon is part of the same defect: it promises the list of failing
    rules that `_report_rules_the_graph_fails` prints and this branch does not.
    """
    output = world["init"].output
    withdrawn = output.find(WITHDRAWN_COMPLETION_CLAIM)
    # Anti-vacuity: an output with no withdrawal satisfies any claim about it.
    assert withdrawn != -1, output
    the_line = output[withdrawn:].splitlines()[0]
    assert "rule" not in the_line.lower(), the_line
    assert not the_line.rstrip().endswith(":"), the_line


# ---------------------------------------------------------------------------
# BDL-067 `.14` — the second writer of `domain` nodes, and the stale index
# ---------------------------------------------------------------------------

#: Documents whose text matches none of `classify_doc`'s three patterns, so each
#: one falls through to the `other` branch and is written as a `domain` node.
#: Deliberately free of the words that would classify them otherwise — no
#: "decision", no "feature"/"requirement"/"spec", no "architecture"/"deployment"
#: — because the defect lives on exactly that fallthrough.
UNCLASSIFIABLE_DOCS = {
    "payments.md": "# Payments\n\nHow money moves through the shop.\n",
    "billing.md": "# Billing\n\nWho is charged, and when.\n",
}

#: The orphan the import sabotage adds to `imported.yml`. It is ADDED rather
#: than carved out of what `import_docs` writes, so the instrument says the same
#: thing before and after the post-condition lands.
THE_ADDED_ORPHAN = "ledger"


def _write_unclassifiable_docs(project: Path) -> None:
    docs = project / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    for name, text in UNCLASSIFIABLE_DOCS.items():
        (docs / name).write_text(text, encoding="utf-8")


def _graph_on_disk(project: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Every node and edge in `.beadloom/_graph/`, whichever file wrote it.

    Read off the files rather than off any writer's return value: the finding
    this covers is that one writer's post-condition said nothing about the
    other's output, and a fixture that asked `bootstrap_project` what it wrote
    would repeat that mistake.
    """
    graph_dir = project / ".beadloom" / "_graph"
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    for yml in sorted(graph_dir.glob("*.yml")):
        if yml.name == "rules.yml":
            continue
        data = yaml.safe_load(yml.read_text(encoding="utf-8")) or {}
        nodes.extend(data.get("nodes") or [])
        edges.extend(data.get("edges") or [])
    return nodes, edges


@given("a docs directory whose documents the classifier reads as domains")
def _given_unclassifiable_docs(world: dict[str, Any]) -> None:
    _write_unclassifiable_docs(world["project"])


@given("the project has already been initialised from its code")
def _given_already_initialised(world: dict[str, Any]) -> None:
    result = CliRunner().invoke(
        main,
        ["init", "--yes", "--mode", "bootstrap", "--project", str(world["project"])],
    )
    assert result.exit_code == 0, result.output


@given("an import step that adds a domain the rules will not accept without a parent")
def _given_an_import_that_adds_an_orphan(monkeypatch: pytest.MonkeyPatch) -> None:
    """Append one parentless `domain` to `imported.yml` after the real import.

    `init` writes `domain-needs-parent` at error severity in the same run, so a
    verdict that reads everything `init` wrote must exit 1 here. A verdict that
    reads an index taken before the import step ran sees nothing and exits 0,
    which is the defect (`imported.yml` was written after the reindex).
    """
    real = import_docs

    def adds_an_orphan(project_root: Path, docs_dir: Path) -> list[dict[str, str]]:
        results = real(project_root, docs_dir)
        imported = project_root / ".beadloom" / "_graph" / "imported.yml"
        data = yaml.safe_load(imported.read_text(encoding="utf-8")) if imported.exists() else {}
        data = data or {"nodes": []}
        data.setdefault("nodes", []).append(
            {
                "ref_id": THE_ADDED_ORPHAN,
                "kind": "domain",
                "summary": "A domain with no parent, added after the import.",
            }
        )
        imported.write_text(
            yaml.safe_dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        return results

    monkeypatch.setattr("beadloom.onboarding.scanner.init_flow.import_docs", adds_an_orphan)


@when("beadloom init is run over the code and the docs together")
def _when_init_both_is_run(world: dict[str, Any]) -> None:
    world["init"] = CliRunner().invoke(
        main,
        ["init", "--yes", "--mode", "both", "--project", str(world["project"])],
    )


@when("beadloom init is run with the import flag")
def _when_init_import_is_run(world: dict[str, Any]) -> None:
    world["init"] = CliRunner().invoke(
        main,
        [
            "init",
            "--import",
            str(world["project"] / "docs"),
            "--project",
            str(world["project"]),
        ],
    )
    assert world["init"].exit_code == 0, world["init"].output


@then("every domain in the graph on disk has an outgoing part_of edge")
def _then_every_domain_on_disk_is_parented(world: dict[str, Any]) -> None:
    nodes, edges = _graph_on_disk(world["project"])
    parented = {e["src"] for e in edges if e["kind"] == "part_of"}
    domains = [n["ref_id"] for n in nodes if n.get("kind") == "domain"]
    orphans = [ref for ref in domains if ref not in parented]
    assert not orphans, f"domain nodes with no part_of edge: {orphans}"
    # Anti-vacuity: a graph holding no domain would satisfy the claim above
    # without the import step having written one.
    assert len(domains) > 1, f"fixture produced no imported domain: {domains}"


@then("the graph on disk passes the rules on disk beside it")
def _then_the_graph_on_disk_is_clean(world: dict[str, Any]) -> None:
    """The adopter's next command, not the one `init` took its verdict from.

    `lint` is run with a reindex so what is judged is the graph as it stands on
    disk. That is precisely the difference the finding turned on: `init` read an
    index written before its last graph file, and reported clean over it.
    """
    result = lint(world["project"], reindex=incremental_reindex)
    assert not result.has_errors, [
        (v.rule_name, v.from_ref_id, v.message) for v in result.violations
    ]
    # Anti-vacuity: a project whose rules file never loaded evaluates nothing
    # and has no errors to report.
    assert result.rules_evaluated > 0, "no rule was evaluated, so nothing was checked"


# ---------------------------------------------------------------------------
# BDL-067 `.15` — the mode this epic never varied, and the two entry points
# that have to agree about it
# ---------------------------------------------------------------------------

#: The mode both scenarios run. Every scenario above pins `bootstrap`, which is
#: how `.14`'s defect stayed invisible: it lived in the mode that runs the second
#: writer as well as the first.
THE_MODE = "both"


def _the_wizard_answering(mode: str) -> list[str]:
    """The wizard's answers for *mode*: the mode, then the graph review.

    The review prompt is shown only when the run produced nodes to review, which
    is the modes that bootstrap. `edit` is the one answer that takes no verdict
    and has its own scenario above, so the answer here is `yes`.
    """
    return [mode, "yes"] if mode in ("bootstrap", "both") else [mode]


@when(
    "the project is initialised twice over, once with the mode flag and once "
    "through the wizard"
)
def _when_initialised_through_both_entry_points(
    world: dict[str, Any], tmp_path: Path
) -> None:
    """Two copies of one project, one entry point each.

    Copied before either run so the two start from the same bytes: a difference
    in the fixture would make the comparison say nothing. The wizard's copy
    declines the doc-skeleton prompt, which keeps the scenario about the verdict.
    """
    by_flag = tmp_path / "through-the-flag" / world["project"].name
    by_wizard = tmp_path / "through-the-wizard" / world["project"].name
    shutil.copytree(world["project"], by_flag)
    shutil.copytree(world["project"], by_wizard)

    world["by_flag"] = by_flag
    world["by_wizard"] = by_wizard
    world["flag_run"] = CliRunner().invoke(
        main, ["init", "--yes", "--mode", THE_MODE, "--project", str(by_flag)]
    )
    with (
        patch("rich.prompt.Prompt.ask", side_effect=_the_wizard_answering(THE_MODE)),
        patch("rich.prompt.Confirm.ask", return_value=False),
    ):
        world["wizard_run"] = CliRunner().invoke(
            main, ["init", "--project", str(by_wizard)]
        )


@then("the two runs report the same verdict")
def _then_the_two_runs_agree(world: dict[str, Any]) -> None:
    """Neither run is asserted to be right. What is asserted is that they agree.

    Measured on the pre-`.14` tree over this fixture: the flag exited 0 and the
    wizard exited 1, because only one of the two had re-indexed after the last
    graph file the run wrote.
    """
    flag_run = world["flag_run"]
    wizard_run = world["wizard_run"]
    assert flag_run.exit_code == wizard_run.exit_code, (
        f"`init --yes --mode {THE_MODE}` exited {flag_run.exit_code} and the "
        f"wizard answering {THE_MODE!r} exited {wizard_run.exit_code} over the "
        f"same project.\n--- the flag ---\n{flag_run.output}\n"
        f"--- the wizard ---\n{wizard_run.output}"
    )


@then("each run leaves a graph that passes the rules on disk beside it")
def _then_both_trees_are_clean(world: dict[str, Any]) -> None:
    """The adopter's next command, on each of the two trees.

    Agreement alone would be satisfied by two runs that are wrong together, so
    the trees are linted as they stand on disk — with a reindex, which is exactly
    the difference the finding turned on.
    """
    for root in (world["by_flag"], world["by_wizard"]):
        result = lint(root, reindex=incremental_reindex)
        assert not result.has_errors, (
            root.parent.name,
            [(v.rule_name, v.from_ref_id, v.message) for v in result.violations],
        )
        # Anti-vacuity: a project whose rules file never loaded evaluates
        # nothing and has no errors to report.
        assert result.rules_evaluated > 0, root.parent.name


@then("neither run reports success")
def _then_neither_run_succeeded(world: dict[str, Any]) -> None:
    for label in ("flag_run", "wizard_run"):
        assert world[label].exit_code != 0, (label, world[label].output)


@then("each run names the rule the gate will name")
def _then_both_runs_name_the_rule(world: dict[str, Any]) -> None:
    for label in ("flag_run", "wizard_run"):
        assert THE_RULE in world[label].output, (label, world[label].output)


# --- BDL-067 `.17` — the consolidation cycle ------------------------------
#
# Four findings with one cause: an instrument scoped to one shape, met by the
# neighbouring shape. The steps below are each stated over the population that
# actually varies — the distinct ref_ids in a graph, the graph files a run did
# and did not write, the branches that announce a scaffold, and the renderings
# `beadloom ci` can choose between.

#: A project whose name is also the name of one of its own source directories.
#: `bootstrap_project` writes the root service node under the project name and
#: its top-level attachment loop skips the cluster whose sanitized name equals
#: that name, so this shape — and only this shape — leaves two unparented
#: `service` entries under one ref_id.
A_NAME_THAT_IS_ALSO_A_SOURCE_DIR = "core"

#: A second source directory, so the project has a cluster the loop does attach.
#: Without it the graph would hold nothing for the import to be measured against.
A_SECOND_SOURCE_DIR = "orders"

#: The graph file an earlier run leaves behind, and the unparented domain in it.
#: Written directly rather than by running `init` twice: the claim is about a
#: file this run did not write, and a file put there by another command of ours
#: is the same fact with a slower fixture.
AN_EARLIER_RUNS_GRAPH_FILE = "imported.yml"
THE_INHERITED_ORPHAN = "payments"

#: What the report says when the failing node came out of a file the run found
#: rather than wrote, and the path it names so the adopter can check it.
THE_GRAPH_FILE_WAS_ALREADY_THERE = "did not write the graph file"
THE_INHERITED_GRAPH_PATH = ".beadloom/_graph/imported.yml"


def _project_named_after_a_source_dir(root: Path) -> Path:
    """A repository called `core` that also holds `src/core/`.

    `core`, `api`, `web` and `app` are ordinary repository names, which is why
    the review called the root-counting defect a release blocker rather than a
    corner: every run of `init` on such a project exited 1.
    """
    project = root / A_NAME_THAT_IS_ALSO_A_SOURCE_DIR
    for source_dir in (A_NAME_THAT_IS_ALSO_A_SOURCE_DIR, A_SECOND_SOURCE_DIR):
        (project / "src" / source_dir).mkdir(parents=True)
        (project / "src" / source_dir / "index.ts").write_text(
            "export const x = 1;\n", encoding="utf-8"
        )
    (project / "package.json").write_text(
        json.dumps(
            {"name": A_NAME_THAT_IS_ALSO_A_SOURCE_DIR, "version": "0.4.1"}, indent=2
        )
        + "\n",
        encoding="utf-8",
    )
    return project


@given("a project named after one of its own source directories")
def _given_a_project_named_after_its_own_source_dir(
    world: dict[str, Any], tmp_path: Path
) -> None:
    world["project"] = _project_named_after_a_source_dir(tmp_path)


@given("a graph file an earlier run left behind holding a domain with no parent")
def _given_an_inherited_graph_file(world: dict[str, Any]) -> None:
    graph_dir = world["project"] / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True, exist_ok=True)
    (graph_dir / AN_EARLIER_RUNS_GRAPH_FILE).write_text(
        yaml.safe_dump(
            {
                "nodes": [
                    {
                        "ref_id": THE_INHERITED_ORPHAN,
                        "kind": "domain",
                        "summary": "Imported from payments.md",
                    }
                ]
            },
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )


@then("the command says the graph file was already there")
def _then_init_says_the_graph_file_predates_it(world: dict[str, Any]) -> None:
    """The counterpart of "the rules file was already there", for the node.

    The report had the first and not the second, so a run that met an inherited
    graph said the opposite of the truth about it.
    """
    result = world["init"]
    assert result.exit_code != 0, result.output
    assert THE_GRAPH_FILE_WAS_ALREADY_THERE in result.output, result.output
    assert THE_INHERITED_GRAPH_PATH in result.output, result.output
    assert THE_INHERITED_ORPHAN in result.output, result.output


@then("the command announced a scaffold before it withdrew the claim")
def _then_the_branch_announced_something(world: dict[str, Any]) -> None:
    """Anti-vacuity, stated without naming any one branch's wording.

    Each branch spells its claim differently, and a step that spelled one would
    be the same instrument the finding is about. What every branch shares is
    that it printed something before the withdrawal.
    """
    result = world["init"]
    withdrawn = result.output.find(WITHDRAWN_COMPLETION_CLAIM)
    assert withdrawn != -1, result.output
    announced = [line for line in result.output[:withdrawn].splitlines() if line.strip()]
    assert announced, result.output


@then("the command names the failing gate step and what it will say")
def _then_init_names_the_step_and_its_summary(world: dict[str, Any]) -> None:
    from beadloom.application.gate import lint_step

    step = lint_step(world["project"])
    assert not step.passed, "the fixture is green, so there is no promise to check"
    world["gate_step"] = step
    result = world["init"]
    assert step.name in result.output, result.output
    assert step.summary in result.output, result.output


@then("every rendering the gate offers prints both of those")
def _then_every_renderer_prints_them(world: dict[str, Any]) -> None:
    """Read off `ci`'s own `click.Choice`, so a fourth renderer is covered.

    `ci` picks `rich` only on a TTY and `github` otherwise, and the github
    renderer builds its own step line, so a report that quoted one rendering was
    false in exactly the scripted context `--yes` serves.
    """
    from beadloom.application.gate import GateResult
    from beadloom.services.commands.federation import _format_gate, ci

    option = next(p for p in ci.params if p.name == "fmt")
    formats = tuple(str(choice) for choice in getattr(option.type, "choices", ()))
    assert len(formats) > 1, formats

    step = world["gate_step"]
    for fmt in formats:
        rendered = _format_gate(GateResult(steps=[step]), fmt)
        assert step.name in rendered, (fmt, rendered)
        assert step.summary in rendered, (fmt, rendered)


@then("the command quotes no rendering's own step line")
def _then_no_renderers_line_is_quoted(world: dict[str, Any]) -> None:
    """Stating the fact and quoting a spelling of it are different promises.

    A line a renderer builds is that renderer's shape, so quoting it makes the
    promise false wherever a different renderer runs. Until BDL-067 `.17` the
    report quoted `gate_step_line`, which is what `rich` prints and what a
    non-TTY `beadloom ci` never does.
    """
    from beadloom.application.gate import GateResult
    from beadloom.services.commands.federation import _format_gate, ci

    option = next(p for p in ci.params if p.name == "fmt")
    formats = tuple(str(choice) for choice in getattr(option.type, "choices", ()))
    output = world["init"].output
    step = world["gate_step"]

    for fmt in formats:
        rendered = _format_gate(GateResult(steps=[step]), fmt)
        lines_about_the_step = [
            line.strip() for line in rendered.splitlines() if step.name in line.strip()
        ]
        # Anti-vacuity: a renderer that never mentions the step would make the
        # claim below hold over an empty list.
        assert lines_about_the_step, (fmt, rendered)
        quoted = [line for line in lines_about_the_step if line in output]
        assert quoted == [], (fmt, quoted, output)
