# beadloom:domain=application
# beadloom:component=mutation-scope
"""Whether a declared mutation target could run a single mutant (BDL-061 S4b).

CONTEXT Q5 decided what Beadloom owns here and what it does not: **the mutation
tool is the project's choice**, because owning a runner would break
tool-agnosticism and put a Python-only dependency inside a product that indexes
twelve languages. What Beadloom ships is the role duty (the dev and test roles
state it), the scope convention, and this check.

**The failure worth catching is a declared target that runs zero mutants.** A
mutation score is a ratio, and a target that names a moved package, a deleted
module or a directory holding no source file at all produces the strongest
possible ratio over an empty denominator. That reads as evidence of test
strength and is evidence of nothing — the same equation as BDL-UX #172/#173,
where a green count covered a surface nobody had measured.

Three findings, all ``warn``:

``mutation-outside-source``
    The target is not under any configured scan path, so whatever it mutates is
    not the code this project indexes.
``mutation-target-missing``
    The target is not on disk.
``mutation-zero-mutants``
    The target exists and holds no file in a language the project indexes.

Where this sits in the package, and why it may read ``flow.yml`` at all, is
stated once in the package docstring beside its sibling ``score``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from beadloom.infrastructure.scan_paths import resolve_scan_paths
from beadloom.onboarding.flow_config import FLOW_CONFIG_RELPATH

if TYPE_CHECKING:
    from pathlib import Path

#: The target is not under any configured scan path.
MUTATION_OUTSIDE_SOURCE = "mutation-outside-source"

#: The target is not on disk.
MUTATION_TARGET_MISSING = "mutation-target-missing"

#: The target exists and holds nothing a mutation runner could mutate.
MUTATION_ZERO_MUTANTS = "mutation-zero-mutants"

#: ``flow.yml`` key holding the declared scope.
MUTATION_KEY = "mutation"

#: Languages assumed when ``config.yml`` declares none. Python only, and stated
#: rather than silently widened: guessing that every extension is mutable would
#: turn "zero mutants" into a finding that never fires.
_DEFAULT_LANGUAGES: tuple[str, ...] = (".py",)


@dataclass(frozen=True)
class MutationScopeFinding:
    """One declared target that cannot do what declaring it claimed."""

    check: str
    target: str
    why: str
    remediation: str
    severity: str = "warn"


def load_mutation_targets(project_root: Path) -> tuple[str, ...]:
    """Targets declared under ``mutation.targets`` in ``.beadloom/flow.yml``.

    An absent file, an absent block and an empty list are all "no targets": a
    project that never opted in is not failing a check it never declared.
    """
    import yaml

    path = project_root / FLOW_CONFIG_RELPATH
    if not path.is_file():
        return ()
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        return ()
    block = data.get(MUTATION_KEY)
    if not isinstance(block, dict):
        return ()
    targets = block.get("targets")
    if isinstance(targets, str):
        return (targets,)
    if isinstance(targets, list):
        return tuple(str(t) for t in targets if isinstance(t, str))
    return ()


def _languages(project_root: Path) -> tuple[str, ...]:
    """File suffixes the project indexes, from ``.beadloom/config.yml``."""
    import yaml

    config = project_root / ".beadloom" / "config.yml"
    if not config.is_file():
        return _DEFAULT_LANGUAGES
    data = yaml.safe_load(config.read_text(encoding="utf-8")) or {}
    languages = data.get("languages") if isinstance(data, dict) else None
    if isinstance(languages, list) and languages:
        return tuple(str(entry) for entry in languages)
    return _DEFAULT_LANGUAGES


def _inside_scan_paths(target: str, scan_paths: list[str]) -> bool:
    normalised = target.strip("/")
    return any(
        normalised == scan.strip("/") or normalised.startswith(f"{scan.strip('/')}/")
        for scan in scan_paths
    )


def _holds_source(path: Path, languages: tuple[str, ...]) -> bool:
    if path.is_file():
        return path.suffix in languages
    return any(
        child.is_file() and child.suffix in languages
        for child in path.rglob("*")
    )


def check_mutation_scope(project_root: Path) -> list[MutationScopeFinding]:
    """Report every declared mutation target that would run zero mutants."""
    targets = load_mutation_targets(project_root)
    if not targets:
        return []
    scan_paths = resolve_scan_paths(project_root)
    languages = _languages(project_root)
    findings: list[MutationScopeFinding] = []

    for target in targets:
        if not _inside_scan_paths(target, scan_paths):
            findings.append(
                MutationScopeFinding(
                    check=MUTATION_OUTSIDE_SOURCE,
                    target=target,
                    why=(
                        f"the mutation target {target!r} is outside the configured "
                        f"source paths ({', '.join(scan_paths)}), so it does not "
                        f"mutate the code this project indexes"
                    ),
                    remediation=(
                        "point the target at a path under one of the scan paths, "
                        "or add its directory to `scan_paths` in "
                        ".beadloom/config.yml"
                    ),
                )
            )
            continue
        path = project_root / target
        if not path.exists():
            findings.append(
                MutationScopeFinding(
                    check=MUTATION_TARGET_MISSING,
                    target=target,
                    why=(
                        f"the mutation target {target!r} is not on disk — the run "
                        f"produces zero mutants and a mutation score computed over "
                        f"nothing"
                    ),
                    remediation=(
                        "update `mutation.targets` in .beadloom/flow.yml to the "
                        "path the code moved to, or drop the target"
                    ),
                )
            )
            continue
        if not _holds_source(path, languages):
            findings.append(
                MutationScopeFinding(
                    check=MUTATION_ZERO_MUTANTS,
                    target=target,
                    why=(
                        f"the mutation target {target!r} holds no "
                        f"{'/'.join(languages)} file — the run produces zero "
                        f"mutants and a mutation score computed over nothing"
                    ),
                    remediation=(
                        "point the target at the source it is meant to cover, or "
                        "declare the language in `languages` in "
                        ".beadloom/config.yml"
                    ),
                )
            )
    return findings
