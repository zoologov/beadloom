# beadloom:domain=graph
# beadloom:feature=rule-engine
"""``graph-summary-facts`` — hold a node's summary to the numbers the project computes.

**One responsibility:** read the numeric and version claims out of every node
``summary`` in the index and say, for each one, whether it agrees with the same
fact computed from the project.

A ``summary`` is the sentence every other surface quotes — ``beadloom ctx``,
``prime``, the generated site, the agent adapters — and until this rule nothing
compared it against anything. Measured on this repository at BDL-062: the root
node claimed ``v1.5.0`` against a computed ``3.0.0``, and ``mcp-server`` claimed
``14 tools`` against a catalogue of 18. Both had been wrong across three major
releases without a single check going red.

**Nothing about "a number in prose" is decided here.** The extraction is
:meth:`~beadloom.doc_sync.DocScanner.scan_line` and the comparison is
:func:`~beadloom.doc_sync.compare_facts` — the same version pattern, the same
keyword table, the same clause-scoped proximity and the same per-fact tolerances
the documentation audit has been repairing since BDL-057. A second, subtly
different notion of "a version" or a second keyword table beside them is how the
next drift class starts, so this module owns neither. What it owns is the graph
side: which prose to read, and what to report about each answer.

Four answers, and the fourth is why the rule exists:

``agrees``
    A claim was found and it matches. Counted, reported in the population clause
    every finding carries, no finding of its own.
``disagrees``
    A claim was found and it differs. A finding at the rule's own severity,
    naming the node, the claimed value and the computed value.
``no claim``
    The summary states nothing checkable. Counted separately — it is not the
    same as a summary that was checked.
``unverifiable``
    A claim was found for a fact this project could not compute. Reported as its
    own finding, carrying the project's own reason verbatim from
    :attr:`~beadloom.doc_sync.FactSet.not_applicable`.

``unverifiable`` never folds into a pass. A project whose version cannot be
resolved and a project whose every summary checked out must not be described by
the same word, and the reason belongs to the fact registry that declined —
inventing a wording here would be a second account of the same refusal.

Severity ships ``error``: unlike a convention check, a number that contradicts
the project it describes is wrong in every house style, and there is nothing for
an adopter to disagree with.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from beadloom.doc_sync import DocScanner, FactRegistry, FactSet, compare_facts
from beadloom.graph.rules.types import Violation, liveness_finding

if TYPE_CHECKING:
    import sqlite3

    from beadloom.graph.rules.types import SummaryFactsRule

#: ``rule_type`` of every non-liveness finding this module produces.
SUMMARY_FACTS_RULE_TYPE = "graph_summary_facts"

#: What to do about a summary that contradicts the project it describes.
SUMMARY_FACTS_HINT = (
    "correct the number in the node's `summary:` in the graph YAML, or — if the "
    "summary is right and the project moved — fix what the project computes. A "
    "summary is quoted by `ctx`, `prime` and every generated page, so a stale "
    "number there is repeated everywhere before anyone reads the code"
)

#: What to do about a claim naming a fact the project declined to compute.
UNVERIFIABLE_HINT = (
    "make the fact computable (the reason above names what is missing), declare "
    "the project's own value under `docs_audit.extra_facts` in "
    "`.beadloom/config.yml`, or reword the summary so it states no number that "
    "cannot be checked"
)

#: What to do about a graph in which no summary states a checkable number.
NO_CLAIM_HINT = (
    "nothing is wrong with a graph whose summaries state no numbers — but this "
    "rule verified none of them, so it must not be read as having cleared them"
)


@dataclass(frozen=True)
class Claim:
    """One number a node's summary states, and what the project says about it."""

    ref_id: str
    summary: str
    fact_name: str
    claimed: str
    #: The project's computed value, or ``None`` when it declined to compute one.
    computed: str | None
    #: Where the computed value came from, or the reason there is none.
    provenance: str


@dataclass(frozen=True)
class SummaryClaims:
    """Every node summary in the index, sorted into the rule's four answers.

    The three counts that are not ``disagreeing`` exist so a reader can judge the
    verdict rather than take it. A rule that found two claims in eighty-four
    summaries has not checked eighty-four of anything, and saying "no violations"
    without saying that is the green count that is not a checked count.
    """

    agreeing: tuple[Claim, ...]
    disagreeing: tuple[Claim, ...]
    unverifiable: tuple[Claim, ...]
    #: Nodes whose summary states no number this project knows how to check.
    silent: int

    @property
    def examined(self) -> int:
        """Every node summary the index offered, claim or no claim."""
        return len(self.claimed) + self.silent

    @property
    def claimed(self) -> tuple[Claim, ...]:
        """Every claim found, whatever became of it."""
        return self.agreeing + self.disagreeing + self.unverifiable

    @property
    def is_live(self) -> bool:
        """Whether any summary stated a number at all."""
        return bool(self.claimed)

    def population(self) -> str:
        """The clause every finding carries, so no count over-claims on its own."""
        return (
            f"read from {self.examined} node summaries: {len(self.claimed)} state a "
            f"checkable fact ({len(self.agreeing)} agree, "
            f"{len(self.disagreeing)} disagree, "
            f"{len(self.unverifiable)} could not be verified) and "
            f"{self.silent} state none"
        )

    def unverifiable_reason(self) -> str:
        """Why nothing could be checked, stated in the terms that would change it."""
        return (
            f"none of the {self.examined} node summaries in this graph states a "
            f"number or version that the project computes a fact for"
        )


def _origin(ref_id: str) -> Path:
    """The ``Mention.file`` a graph summary is recorded against.

    A summary is prose without a file, and the identifier a reader needs to find
    it is the node's ``ref_id``. Recording it here is what lets the mention be
    carried through :func:`~beadloom.doc_sync.compare_facts` — which is written
    against documents — and mapped back to its node afterwards.
    """
    return Path(ref_id)


def collect_claims(conn: sqlite3.Connection, fact_set: FactSet) -> SummaryClaims:
    """Sort every node summary in the index into the rule's four answers.

    Pure over *conn* and *fact_set*: the same graph and the same facts always
    give the same answer, and neither the filesystem nor the running package is
    consulted.
    """
    scanner = DocScanner()
    summaries = {
        str(row[0]): str(row[1] or "")
        for row in conn.execute("SELECT ref_id, summary FROM nodes ORDER BY ref_id")
    }

    mentions = []
    silent = 0
    for ref_id, summary in summaries.items():
        found = scanner.scan_line(summary, origin=_origin(ref_id))
        if not found:
            silent += 1
        mentions.extend(found)

    result = compare_facts(
        fact_set.facts, mentions, not_applicable=fact_set.not_applicable
    )

    agreeing: list[Claim] = []
    disagreeing: list[Claim] = []
    for finding in result.findings:
        ref_id = str(finding.mention.file)
        claim = Claim(
            ref_id=ref_id,
            summary=summaries[ref_id],
            fact_name=finding.mention.fact_name,
            claimed=str(finding.mention.value),
            computed=str(finding.fact.value),
            provenance=finding.fact.source,
        )
        (agreeing if finding.status == "fresh" else disagreeing).append(claim)

    # `unmatched` is every mention whose fact the registry produced no value
    # for, which is exactly the population `not_applicable` explains. A fact
    # neither computed nor declined is a fact this project never declared, and
    # its reason says so rather than leaving the entry blank.
    unverifiable = [
        Claim(
            ref_id=str(mention.file),
            summary=summaries[str(mention.file)],
            fact_name=mention.fact_name,
            claimed=str(mention.value),
            computed=None,
            provenance=fact_set.not_applicable.get(
                mention.fact_name,
                f"`{mention.fact_name}` is not a fact this project declares",
            ),
        )
        for mention in result.unmatched
    ]

    return SummaryClaims(
        agreeing=tuple(agreeing),
        disagreeing=tuple(disagreeing),
        unverifiable=tuple(unverifiable),
        silent=silent,
    )


def summary_facts_inert_reason(
    conn: sqlite3.Connection, project_root: Path | None
) -> str | None:
    """Why the rule can check nothing against this graph, or ``None`` when it can.

    Shared with :mod:`.liveness` so the count ``lint`` prints and the finding the
    rule writes cannot disagree about whether it stood down.
    """
    claims = collect_claims(conn, _facts_for(conn, project_root))
    if claims.is_live:
        return None
    return claims.unverifiable_reason()


def _facts_for(conn: sqlite3.Connection, project_root: Path | None) -> FactSet:
    """What this project computes about itself, as the audit's registry sees it."""
    return FactRegistry().collect_set(project_root or Path.cwd(), conn)


def _disagreement(rule: SummaryFactsRule, claims: SummaryClaims, claim: Claim) -> Violation:
    """One summary whose number contradicts the project it describes."""
    return Violation(
        rule_name=rule.name,
        rule_description=rule.description,
        rule_type=SUMMARY_FACTS_RULE_TYPE,
        severity=rule.severity,
        file_path=None,
        line_number=None,
        from_ref_id=claim.ref_id,
        to_ref_id=None,
        message=(
            f"`{claim.ref_id}` summary states {claim.fact_name} {claim.claimed} but "
            f"this project computes {claim.computed} ({claim.provenance}); the "
            f'summary reads "{claim.summary}" — {claims.population()}'
        ),
        remediation=SUMMARY_FACTS_HINT,
    )


def _unverifiable(rule: SummaryFactsRule, claims: SummaryClaims, claim: Claim) -> Violation:
    """One summary stating a number about a fact this project could not compute."""
    return liveness_finding(
        rule_name=rule.name,
        rule_description=rule.description,
        message=(
            f"Rule '{rule.name}' could not be verified for `{claim.ref_id}`: its "
            f"summary states {claim.fact_name} {claim.claimed}, and this project "
            f"declares no value to check it against — {claim.provenance}. The claim "
            f"is neither confirmed nor contradicted — {claims.population()}"
        ),
        remediation=UNVERIFIABLE_HINT,
    )


def evaluate_summary_facts_rules(
    conn: sqlite3.Connection,
    rules: list[SummaryFactsRule],
    *,
    project_root: Path | None = None,
    fact_set: FactSet | None = None,
) -> list[Violation]:
    """Report every node summary whose number contradicts the project.

    *fact_set* is the facts to check against. It defaults to what
    :class:`~beadloom.doc_sync.FactRegistry` computes for *project_root*, and is
    accepted directly so a caller that has already collected them does not pay
    for a second collection.

    A graph in which no summary states a checkable number reports **that**, as a
    ``rule_liveness`` finding, instead of returning an empty list a reader would
    take for a pass.
    """
    if not rules:
        return []

    facts = fact_set if fact_set is not None else _facts_for(conn, project_root)
    claims = collect_claims(conn, facts)

    violations: list[Violation] = []
    for rule in rules:
        if not claims.is_live:
            violations.append(
                liveness_finding(
                    rule_name=rule.name,
                    rule_description=rule.description,
                    message=(
                        f"Rule '{rule.name}' checked nothing: "
                        f"{claims.unverifiable_reason()}. No summary was cleared — "
                        f"a graph whose summaries state no numbers has not been "
                        f"verified, it has been skipped"
                    ),
                    remediation=NO_CLAIM_HINT,
                )
            )
            continue
        violations.extend(_disagreement(rule, claims, claim) for claim in claims.disagreeing)
        violations.extend(_unverifiable(rule, claims, claim) for claim in claims.unverifiable)
    return violations
