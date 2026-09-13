"""The CLI reference states the two population shapes a pipeline parses.

BDL-070 B6 (`beadloom-5tcc.7`). `docs/services/cli.md` documents both
machine-readable forms of a layer rule's population — the JSON keys under
`summary.layer_populations[]` and the porcelain record that leads the output.
Release B narrowed both: `own_tags`/`inherited` collapsed into one
`population`, so `LayerReach.to_dict` lost three keys and the porcelain record
lost a field. The rule-engine SPEC was brought into line and this file was not,
because nothing in the automated path points at it: `sync-check` reads `[ok]`
on it, and it was in neither the brief's changed-file inventory nor its
specification set.

Prose going stale is a documentation problem. These two lines are not prose:
they are the shapes a consumer splits on. A consumer that split the porcelain
record on `:` and read field 7 got the skipped count where the document
promised it the inherited one.

Both expectations here are DERIVED from the code — the key set from
`LayerReach.to_dict`, the field count from the line `format_porcelain` really
emits — so this module cannot pass by agreeing with a second copy of the
document's own claim.
"""

from __future__ import annotations

import re
from pathlib import Path

from beadloom.graph.linter import POPULATION_MARKER, LintResult, format_porcelain
from beadloom.graph.rules.layer_reach import LayerReach
from beadloom.graph.rules.layers import LayerPopulation

CLI_DOC = Path(__file__).resolve().parents[1] / "docs" / "services" / "cli.md"

#: The clause of the `json` bullet that names the keys, anchored on the key the
#: document introduces them with. A reword that moves them out of this shape
#: fails here rather than passing quietly, which is the point of the module.
_JSON_KEYS_CLAUSE = re.compile(r"`layer_populations\[\]`[^;]*?judged — (?P<keys>[^;]+);")

#: Every documented porcelain template, wherever in the file it is written.
_PORCELAIN_TEMPLATE = re.compile(
    rf"`{re.escape(POPULATION_MARKER)}layer_population:(?P<rest>[^`]+)`"
)

_A_REACH = LayerReach(
    rule_name="architecture-layers",
    edge_kind="depends_on",
    population=LayerPopulation(evaluated=357, skipped_untagged=8),
)


def _doc_text() -> str:
    return CLI_DOC.read_text(encoding="utf-8")


def _emitted_population_line() -> str:
    porcelain = format_porcelain(LintResult(layer_populations=[_A_REACH]))
    marked = [line for line in porcelain.splitlines() if line.startswith(POPULATION_MARKER)]
    assert len(marked) == 1, f"expected one marked population line, got {marked!r}"
    return marked[0]


class TestTheDocumentedJsonKeysAreTheKeysTheCodeEmits:
    """`summary.layer_populations[]` — named one by one, because a consumer reads a name."""

    def test_the_clause_naming_the_keys_is_present(self) -> None:
        assert _JSON_KEYS_CLAUSE.search(_doc_text()) is not None, (
            f"{CLI_DOC} no longer names the keys of summary.layer_populations[] in a shape "
            "this check can read; the contract is still parsed by consumers, so state it"
        )

    def test_the_documented_keys_are_exactly_the_emitted_keys(self) -> None:
        match = _JSON_KEYS_CLAUSE.search(_doc_text())
        assert match is not None
        documented = re.findall(r"`([a-z_]+)`", match.group("keys"))

        assert documented == list(_A_REACH.to_dict()), (
            f"{CLI_DOC} documents {documented} for summary.layer_populations[]; "
            f"LayerReach.to_dict emits {list(_A_REACH.to_dict())}"
        )


class TestTheDocumentedPorcelainRecordHasTheFieldsThatAreEmitted:
    """The marked line a consumer splits on `:`."""

    def test_at_least_one_template_is_documented(self) -> None:
        assert _PORCELAIN_TEMPLATE.search(_doc_text()) is not None, (
            f"{CLI_DOC} no longer shows the porcelain population record"
        )

    def test_every_documented_template_has_the_emitted_field_count(self) -> None:
        emitted = _emitted_population_line().removeprefix(POPULATION_MARKER).split(":")
        documented_templates = _PORCELAIN_TEMPLATE.findall(_doc_text())

        for rest in documented_templates:
            fields = ["layer_population", *rest.split(":")]
            assert len(fields) == len(emitted), (
                f"{CLI_DOC} documents {len(fields)} colon-separated fields "
                f"({fields}); format_porcelain emits {len(emitted)} ({emitted})"
            )

    def test_the_placeholder_names_follow_the_emitted_order(self) -> None:
        """`<rule>:<edge_kind>:…` — the names a reader maps onto the values."""
        emitted_keys = list(_A_REACH.to_dict())
        for rest in _PORCELAIN_TEMPLATE.findall(_doc_text()):
            placeholders = [f.strip("<>") for f in rest.split(":")]

            assert placeholders[: len(emitted_keys) - 1] == emitted_keys[:-1], (
                f"{CLI_DOC} documents placeholders {placeholders}; "
                f"the emitted record carries {emitted_keys}"
            )
