# beadloom:domain=application
# beadloom:feature=impact
"""The answer as a dictionary and as text, from one computation.

Two renderings of one answer rather than two answers. The JSON is the whole
structure; the text is the same structure read aloud, and both begin with the
SEED and the rule that derived it — because a reader who does not know what the
answer was computed over cannot tell a right answer from a confident wrong one,
which is the failure mode this command was measured against before it was built.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from beadloom.application.impact.axes import THE_TARGET_SEAT

if TYPE_CHECKING:
    from beadloom.application.impact.answer import ImpactAnswer, Population
    from beadloom.application.impact.axes import Command

#: What a branch with no enclosing condition is called in the text. The
#: fallthrough is the branch a binding-shaped count cannot see, so it is spelled
#: rather than left as an empty line.
_FALLTHROUGH = "(fallthrough)"

#: How a count taken over a caller of the target is spelled. A branch count with
#: no seat is the shape BDL-067 was misled by, so the seat is written beside
#: every count that is not the target's own.
_FROM_A_CALLERS_SEAT = ", read from a caller's seat"


def answer_to_dict(answer: ImpactAnswer) -> dict[str, Any]:
    """The whole answer as plain data, field for field."""
    return {
        "target": answer.target,
        "root": answer.root,
        "seed_rule": {
            "name": answer.seed_rule,
            "statement": answer.seed_rule_statement,
            "effects": [{"name": name, "statement": text} for name, text in answer.effect_rules],
        },
        "seeds": [
            {
                "name": seed.name,
                "path": seed.path.as_posix(),
                "lineno": seed.lineno,
                "effect": seed.effect,
            }
            for seed in answer.seeds
        ],
        "co_writers": _population_to_dict(answer.co_writers),
        "callers": _population_to_dict(answer.callers),
        "commands": [_command_to_dict(command) for command in answer.commands],
        "boundary": {
            "resolved": answer.boundary.resolved,
            "target_node": answer.boundary.target_node,
            "target_domain": answer.boundary.target_domain,
            "nodes_touched": list(answer.boundary.nodes_touched),
            "domains_touched": list(answer.boundary.domains_touched),
            "leaves_the_target_node": answer.boundary.leaves_the_target_node,
            "leaves_the_target_domain": answer.boundary.leaves_the_target_domain,
        },
        "unresolved": [
            {"kind": gap.kind, "detail": gap.detail, "where": gap.where}
            for gap in answer.unresolved
        ],
    }


def _population_to_dict(population: Population) -> dict[str, Any]:
    return {
        "resolved": population.resolved,
        "reason": population.reason,
        "sites": [
            {
                "name": site.name,
                "path": site.path,
                "lineno": site.lineno,
                "node": site.node,
                "domain": site.domain,
            }
            for site in population.sites
        ],
    }


def _command_to_dict(command: Command) -> dict[str, Any]:
    return {
        "name": command.name,
        "path": command.path.as_posix(),
        "lineno": command.lineno,
        "node": command.node,
        "domain": command.domain,
        "narrowed_to_the_seeds": command.narrowed_to_the_seeds,
        "seat": command.seat,
        "branches": [
            {
                "guard": list(branch.guard),
                "callees": list(branch.callees),
                "linenos": list(branch.linenos),
            }
            for branch in command.branches
        ],
        "exits": list(command.exits),
    }


def render_impact(answer: ImpactAnswer) -> str:
    """The answer as text, seed first."""
    lines = [
        f"# impact: {answer.target}",
        f"root swept: {answer.root}",
        "",
        f"## seed — rule `{answer.seed_rule}`",
        answer.seed_rule_statement,
        "",
    ]
    if answer.seeds:
        lines += [
            f"- {seed.name} ({seed.effect}) — {seed.path.as_posix()}:{seed.lineno}"
            for seed in answer.seeds
        ]
    else:
        lines.append("- none. Every axis below the seed is unresolved, not empty.")
    lines += ["", "## who else commits through it"]
    lines += _population_lines(answer.co_writers)
    lines += ["", "## who else calls this"]
    lines += _population_lines(answer.callers)
    lines += ["", "## branches and exit forms"]
    for command in answer.commands:
        if not command.branches and not command.exits:
            continue
        scope = "reaching a seed" if command.narrowed_to_the_seeds else "every call"
        seat = "" if command.seat == THE_TARGET_SEAT else _FROM_A_CALLERS_SEAT
        lines.append(
            f"- {command.name} ({command.path.as_posix()}:{command.lineno}): "
            f"{len(command.branches)} branch(es), {scope}{seat}"
        )
        lines += [
            f"    - {' and '.join(branch.guard) or _FALLTHROUGH}: "
            f"{', '.join(branch.callees)}"
            for branch in command.branches
        ]
        if command.exits:
            lines.append(f"    ends by: {'; '.join(command.exits)}")
    lines += ["", "## boundary (from the graph, and nothing else)"]
    if answer.boundary.resolved:
        lines += [
            f"- target node: {answer.boundary.target_node or 'none'}"
            f" (domain: {answer.boundary.target_domain or 'none'})",
            f"- nodes touched: {', '.join(answer.boundary.nodes_touched) or 'none'}",
            f"- leaves the target's node: {answer.boundary.leaves_the_target_node}",
            f"- leaves the target's domain: {answer.boundary.leaves_the_target_domain}",
        ]
    else:
        lines.append("- unresolved: there was no index to read ownership from.")
    lines += ["", f"## unresolved ({len(answer.unresolved)})"]
    lines += [
        f"- [{gap.kind}] {gap.detail}" + (f" — {gap.where}" if gap.where else "")
        for gap in answer.unresolved
    ] or ["- nothing this derivation knows it could not resolve."]
    return "\n".join(lines)


def _population_lines(population: Population) -> list[str]:
    """One axis, read aloud — the caveat first, and then whatever it did find.

    An unresolved axis that HAS sites is a partial answer, not an absent one, so
    the sites are printed under the caveat rather than replaced by it. Hiding
    them would trade the silence BDL-068 `.15` closed for a second one.
    """
    found = [
        f"- {site.name} — {site.path}:{site.lineno}"
        + (f" [{site.node}]" if site.node else " [no node]")
        for site in population.sites
    ]
    if not population.resolved:
        return [f"- unresolved: {population.reason}", *found]
    return found or ["- none found."]
