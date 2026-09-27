"""What the tests of init's verdict share: its branches, modes and bindings, and the sabotages."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import yaml
from click.testing import CliRunner

from beadloom.onboarding.scanner.bootstrap import bootstrap_project
from beadloom.services.cli import main
from beadloom.services.commands import setup as init_command
from tests.support.adopter_project import typescript_project

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

#: The rule `generate_rules` writes for every graph that holds a domain, and the
#: rule BDL-UX #192's reporter read out of `lint --strict` after a green `init`.
THE_RULE = "domain-needs-parent"


#: The two BINDINGS of `bootstrap_project`, which are not the branches and must
#: not be counted as though they were. `init --yes` and the default wizard both
#: run inside `init_flow`, which binds the function at import time, so ONE patch
#: sabotages both; `init --bootstrap` imports it from the package inside the
#: command body and has to be sabotaged separately.
INIT_FLOW_BINDING = "beadloom.onboarding.scanner.init_flow.bootstrap_project"


PACKAGE_BINDING = "beadloom.onboarding.bootstrap_project"


@dataclass(frozen=True)
class InitBranch:
    """One branch of `init` that writes a bootstrap graph, and how to reach it.

    A branch is a path through the `init` command body; a binding is a name
    `bootstrap_project` is reachable under. Two branches can share one binding,
    and two of these three do — which is why this type carries both and why the
    parametrisation is over branches.
    """

    #: How the branch is spelled on the command line, for the test id.
    name: str
    #: The arguments that select it. Empty for the default wizard.
    argv: tuple[str, ...]
    #: The name of `bootstrap_project` this branch calls.
    binding: str
    #: The `if` conditions in `init`'s body the branch sits under, as the source
    #: spells them, outermost first. Empty for the fallthrough wizard. This is
    #: what
    #: `tests/unit/application/source_derivation/test_init_branches_that_reach_the_bootstrap.py`
    #: matches the tuple below against the command's own source, so a fourth branch fails a
    #: test instead of merely going untested (BDL-067 `.7`).
    guard: tuple[str, ...]
    #: The wizard's answers, in order: init mode, then the graph review.
    prompts: tuple[str, ...] = field(default_factory=tuple)


#: Every branch of `init` that reaches `bootstrap_project`. Three branches, two
#: bindings. A fourth branch belongs in this tuple on the day it is written.
THE_BRANCHES = (
    InitBranch("--yes", ("--yes", "--mode", "bootstrap"), INIT_FLOW_BINDING, ("non_interactive",)),
    InitBranch("--bootstrap", ("--bootstrap",), PACKAGE_BINDING, ("bootstrap",)),
    InitBranch("wizard", (), INIT_FLOW_BINDING, (), prompts=("bootstrap", "yes")),
)


def _the_modes_the_flag_offers() -> tuple[str, ...]:
    """The `--mode` values, read off the command's own `click.Choice`.

    Not written out, for the reason `THE_BRANCHES` is checked against `init`'s
    source in
    `tests/unit/application/source_derivation/test_init_branches_that_reach_the_bootstrap.py`: a
    mode added to the flag and not to a tuple here would be a mode with no case, and
    a case that is not written is a case that does not fail.

    It lives in this module rather than in `tests/test_init_agrees_across_its_
    modes.py`, which is where BDL-067 `.15` wrote it, because `.17` needs the
    same axis here and that module already imports from this one. One derivation
    of one fact, in the module the other imports.
    """
    option = next(p for p in init_command.init.params if p.name == "init_mode")
    choices = getattr(option.type, "choices", ())
    return tuple(str(choice) for choice in choices)


#: Every mode `init` accepts, derived once at import.
THE_MODES = _the_modes_the_flag_offers()


#: A `rules.yml` the ADOPTER wrote: valid, loadable, and failed by any graph the
#: bootstrap writes. `generate_rules` dropped `service-needs-parent` for exactly
#: the reason it fails here — the root service node has no parent by definition
#: — so a project carrying a hand-written rule of that name is a project whose
#: red verdict is its own. This is the review's reproduction of BDL-067 `.9`,
#: moved into the suite.
THE_ADOPTERS_RULE = "service-needs-parent"


A_RULES_FILE_THE_ADOPTER_WROTE = """\
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


THE_BUG_REPORT_REQUEST = "please report it"


#: The first word of the failure report, used to place the withdrawal line.
THE_FAILURE_REPORT = "Error:"


def _strip_part_of_edges(project_root: Path) -> None:
    """Remove every `part_of` edge from the graph the bootstrap just wrote."""
    services = project_root / ".beadloom" / "_graph" / "services.yml"
    data = yaml.safe_load(services.read_text(encoding="utf-8"))
    kept = [e for e in data.get("edges", []) if e.get("kind") != "part_of"]
    if kept:
        data["edges"] = kept
    else:
        # `bootstrap_project` writes no `edges:` key at all when there are none,
        # so the sabotaged file keeps the shape #192 was reported against.
        data.pop("edges", None)
    services.write_text(
        yaml.safe_dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def a_bootstrap_that_forgets_the_edge(monkeypatch: pytest.MonkeyPatch, binding: str) -> None:
    """Patch one binding of `bootstrap_project` into a self-contradicting one.

    The rules half is untouched: the real `generate_rules` still writes
    `domain-needs-parent`. Only the graph half loses the edge that rule requires.
    """
    real = bootstrap_project

    def forgetful(project_root: Path, **kwargs: Any) -> dict[str, Any]:
        result = real(project_root, **kwargs)
        _strip_part_of_edges(project_root)
        result["edges"] = [e for e in result["edges"] if e["kind"] != "part_of"]
        result["edges_generated"] = len(result["edges"])
        return result

    monkeypatch.setattr(binding, forgetful)


def lint_strict(project_root: Path) -> int:
    return CliRunner().invoke(main, ["lint", "--strict", "--project", str(project_root)]).exit_code


#: The orphan the import sabotage adds. Added rather than carved out of what
#: `import_docs` writes, so the instrument says the same thing before and after
#: the post-condition landed.
THE_ADDED_ORPHAN = "ledger"


def an_import_that_adds_an_orphan(monkeypatch: pytest.MonkeyPatch) -> None:
    """Append one parentless `domain` to `imported.yml` after the real import.

    `init` writes `domain-needs-parent` at error severity in the same run, so a
    verdict that reads everything `init` wrote must exit 1. The reindex used to
    sit inside the bootstrap block, ahead of the file this writes, so the verdict
    judged an index that predated it and reported clean.
    """
    from beadloom.onboarding.scanner.doc_classify import import_docs as real

    def adds_an_orphan(project_root: Path, docs_dir: Path) -> list[dict[str, str]]:
        results = real(project_root, docs_dir)
        imported = project_root / ".beadloom" / "_graph" / "imported.yml"
        data = yaml.safe_load(imported.read_text(encoding="utf-8")) if imported.exists() else {}
        data = data or {"nodes": []}
        data.setdefault("nodes", []).append(
            {"ref_id": THE_ADDED_ORPHAN, "kind": "domain", "summary": "No parent."}
        )
        imported.write_text(
            yaml.safe_dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        return results

    monkeypatch.setattr("beadloom.onboarding.scanner.init_flow.import_docs", adds_an_orphan)


def _the_formats_ci_offers() -> tuple[str, ...]:
    """The `--format` values, read off `ci`'s own `click.Choice`.

    Derived for the reason `THE_MODES` is: a fourth renderer added to the flag
    and not to a list here would be a renderer with no case, and `init`'s promise
    about what `beadloom ci` prints is a promise about whichever one runs.
    """
    from beadloom.services.commands.federation import ci

    option = next(p for p in ci.params if p.name == "fmt")
    choices = getattr(option.type, "choices", ())
    return tuple(str(choice) for choice in choices)


#: Every rendering `beadloom ci` can produce, derived once at import.
THE_GATE_FORMATS = _the_formats_ci_offers()


#: A rules file the ADOPTER wrote, requiring what the bootstrap's own generated
#: rule requires. Written by hand so that `bootstrap_project` — which never
#: rewrites a rules file already on disk — leaves it alone and the run meets a
#: rule it did not author.
A_DOMAIN_RULE_THE_ADOPTER_WROTE = """\
version: 1
rules:
  - name: domain-needs-parent
    description: Every domain must have a part_of edge
    require:
      for:
        kind: domain
      has_edge_to: {}
      edge_kind: part_of
"""


#: Documents whose text matches none of `classify_doc`'s patterns, so each falls
#: through to the `other` branch and is written as a `domain` node in
#: `imported.yml` — the second writer, and the one `--mode bootstrap` never runs.
UNCLASSIFIABLE_DOCS = {
    "payments.md": "# Payments\n\nHow money moves through the shop.\n",
    "billing.md": "# Billing\n\nWho is charged, and when.\n",
}


#: The two graph files `init` can write, by the name each writer gives it.
THE_BOOTSTRAP_FILE = "services.yml"


#: The modes that run the bootstrap, and therefore the modes in which `init`
#: writes `rules.yml` and takes a verdict. Written here and bound to behaviour by
#: `test_the_modes_that_write_the_bootstrap_file_are_the_ones_declared`, so the
#: constant cannot quietly fall behind `init_flow`'s `mode in (...)` conditions.
THE_MODES_THAT_BOOTSTRAP = ("bootstrap", "both")


def a_project_with_code_and_docs(tmp_path: Path, name: str = "orders-web") -> Path:
    """A flat `src/index.ts` plus documents the classifier reads as domains.

    Both writers have something to write here, which is what makes one fixture
    usable for all three modes: `--mode bootstrap` ignores the docs, `--mode
    import` ignores the code, and `--mode both` writes two graph files.
    """
    project = typescript_project(tmp_path / name).root
    docs = project / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    for filename, text in UNCLASSIFIABLE_DOCS.items():
        (docs / filename).write_text(text, encoding="utf-8")
    return project


def graph_on_disk(project_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Every node and edge under `.beadloom/_graph/`, whichever file wrote it.

    Read off the files rather than off a writer's return value: the finding this
    module covers is that one writer's post-condition said nothing about the
    other's output, and a fixture that asked one writer what it wrote would
    repeat that mistake.
    """
    graph_dir = project_root / ".beadloom" / "_graph"
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    for path in sorted(graph_dir.glob("*.yml")):
        if path.name == "rules.yml":
            continue
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        nodes.extend(data.get("nodes") or [])
        edges.extend(data.get("edges") or [])
    return nodes, edges
