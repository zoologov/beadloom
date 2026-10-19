# beadloom:domain=onboarding
# beadloom:feature=tool-reach
"""Which composed layers each declared tool reads, and which one tool lacks against another.

BDL-083 S2h (RFC D13, BDL-UX #356). Up to 9.0.0 the role files were the only
artifact composed for every tool. The core, the project layer, the STACK overlay
and the four commands were written under ``.claude/`` whatever ``tools:`` said,
so a project naming Cursor received five role files and a 17-line pointer, and
an agent on Cursor ran the flow with none of the rules the Gate's prose relies
on. Nothing compared one tool's composition with another's, so nothing said so.

This module states the reach in one table and derives the comparison from it:

* :func:`tool_targets` -- the files each tool reads the composed flow from, each
  with the artifact kind and name it is composed as. Claude reads
  ``.claude/CLAUDE.md`` and ``.claude/commands/<name>.md``; Cursor reads the same
  text as ``alwaysApply`` rules, ``.cursor/rules/beadloom-flow.mdc`` and
  ``.cursor/rules/beadloom-<name>.mdc``; both read their own role directory.
* :func:`cursor_rule_text` and :func:`rule_body` -- the form a Cursor rule takes,
  front matter and body, so the body can be compared byte for byte with the file
  Claude reads.
* :func:`layer_gaps` -- for every pair of declared tools, the layers one reads
  and the other does not, each named by the fragment it comes from.

A layer is identified by its SOURCE, the fragment file it was read from, not by
its label alone: ``core`` is the label of five different files, and a tool that
reads the commands' core and not the CLAUDE core lacks a layer that a comparison
of labels would call present.

THE STATED LIMITS. A file a tool reads is credited with the layers of its
composition when it is on disk; whether its body still IS that composition is the
drift check's verdict on the file (stale, hand-edited), not this one's, so one
cause is reported once. A layer folder named for one tool --
``.beadloom/flow/cursor/`` -- is that tool's own by declaration and is never a gap
for another.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from beadloom.onboarding.composer import (
    CLAUDE_ARTIFACT_NAME,
    COMMAND_NAMES,
    compose,
    templates_dir,
)
from beadloom.onboarding.role_adapters import TOOL_AGENT_DIRS
from beadloom.onboarding.role_composer import ROLE_NAMES

if TYPE_CHECKING:
    from beadloom.onboarding.flow_config import FlowConfig

__all__ = [
    "CURSOR_RULES_DIR",
    "LEGACY_CURSOR_POINTER",
    "TOOL_ROOTS",
    "LayerGap",
    "ReadLayer",
    "ToolTarget",
    "cursor_command_rule_relpath",
    "cursor_core_rule_relpath",
    "cursor_rule_text",
    "layer_gaps",
    "rule_body",
    "tool_targets",
]

#: The directory each tool reads its project configuration from.
TOOL_ROOTS: dict[str, Path] = {"claude": Path(".claude"), "cursor": Path(".cursor")}

#: Where Cursor reads project rules.
CURSOR_RULES_DIR = TOOL_ROOTS["cursor"] / "rules"

#: The pointer 9.0.0 wrote in place of a composed core. No command writes it any
#: more; the scaffold reports one it finds and leaves it, as it does every file
#: an older flow layout left behind.
LEGACY_CURSOR_POINTER = CURSOR_RULES_DIR / "beadloom-flow.md"

_FRONT_MATTER_FENCE = "---\n"

#: The front matter label of the core rule. No ``": "`` inside: the front matter is
#: YAML, and a plain scalar holding one does not parse.
_CORE_DESCRIPTION = (
    "Beadloom agentic flow - the composed core every agent on this project "
    "follows, the text .claude/CLAUDE.md carries"
)


def cursor_core_rule_relpath() -> Path:
    """Project-relative path of the rule carrying the composed core for Cursor."""
    return CURSOR_RULES_DIR / "beadloom-flow.mdc"


def cursor_command_rule_relpath(name: str) -> Path:
    """Project-relative path of the rule carrying one composed command for Cursor."""
    return CURSOR_RULES_DIR / f"beadloom-{name}.mdc"


def cursor_core_description() -> str:
    """The ``description:`` of the core rule's front matter."""
    return _CORE_DESCRIPTION


def cursor_command_description(name: str) -> str:
    """The ``description:`` of one command rule's front matter."""
    return f"Beadloom flow command {name} - the composed text .claude/commands/{name}.md carries"


def cursor_rule_text(body: str, *, description: str) -> str:
    """A Cursor rule applied to every request: front matter, then ``body`` unchanged."""
    return (
        f"{_FRONT_MATTER_FENCE}description: {description}\nglobs:\n"
        f"alwaysApply: true\n{_FRONT_MATTER_FENCE}{body}"
    )


def rule_body(text: str) -> str:
    """The body of a Cursor rule: everything after its front matter.

    A text that opens with no front matter is its own body, so a rule somebody
    wrote by hand is compared whole rather than cut at a line that happens to be
    a fence.
    """
    if not text.startswith(_FRONT_MATTER_FENCE):
        return text
    end = text.find(f"\n{_FRONT_MATTER_FENCE}", len(_FRONT_MATTER_FENCE) - 1)
    if end == -1:
        return text
    return text[end + 1 + len(_FRONT_MATTER_FENCE) :]


@dataclass(frozen=True)
class ToolTarget:
    """One file a tool reads the composed flow from, and what it is composed as."""

    tool: str
    relpath: Path
    kind: str
    name: str


def tool_targets(tool: str) -> tuple[ToolTarget, ...]:
    """Every file ``tool`` reads the composed flow from: the core, the commands, the roles."""
    if tool == "cursor":
        core = ToolTarget(tool, cursor_core_rule_relpath(), "cursor", CLAUDE_ARTIFACT_NAME)
        commands = tuple(
            ToolTarget(tool, cursor_command_rule_relpath(name), "commands", name)
            for name in COMMAND_NAMES
        )
    else:
        root = TOOL_ROOTS[tool]
        core = ToolTarget(
            tool, root / f"{CLAUDE_ARTIFACT_NAME}.md", "claude", CLAUDE_ARTIFACT_NAME
        )
        commands = tuple(
            ToolTarget(tool, root / "commands" / f"{name}.md", "commands", name)
            for name in COMMAND_NAMES
        )
    roles = tuple(
        ToolTarget(tool, TOOL_AGENT_DIRS[tool] / f"{role}.md", "roles", role)
        for role in ROLE_NAMES
    )
    return (core, *commands, *roles)


@dataclass(frozen=True, order=True)
class ReadLayer:
    """One layer a tool reads, named by the fragment it comes from.

    ``label`` is ``core``, ``architecture:<a>``, ``stack:<s>`` or ``project``;
    ``source`` is the fragment's path -- under the package's ``templates/`` for a
    shipped layer, project-relative for the project layer.
    """

    label: str
    source: str


#: The order a gap lists its layers in: the order they compose in.
_LABEL_RANK = {"core": 0, "architecture": 1, "stack": 2, "project": 3}


def _rank(layer: ReadLayer) -> tuple[int, str, str]:
    family = layer.label.split(":")[0]
    return (_LABEL_RANK.get(family, len(_LABEL_RANK)), layer.label, layer.source)


@dataclass(frozen=True)
class LayerGap:
    """The layers declared tool ``against`` reads and declared tool ``tool`` does not."""

    tool: str
    against: str
    layers: tuple[ReadLayer, ...]

    @property
    def file(self) -> str:
        """The directory the lacking tool reads its configuration from."""
        return str(TOOL_ROOTS[self.tool])

    @property
    def why(self) -> str:
        """What is missing, by layer, in the words a reader of the files needs."""
        return (
            f"`{self.tool}` lacks {len(self.layers)} layer(s) `{self.against}` reads: "
            f"{_describe(self.layers)} -- an agent on `{self.tool}` runs the flow "
            "without them"
        )

    @property
    def remediation(self) -> str:
        """The command that composes every declared tool from the same layers."""
        return (
            "run `beadloom setup-agentic-flow` or `beadloom config-check --fix`: "
            f"both compose every tool `tools:` declares, `{self.tool}` included, "
            "from the same layers"
        )


def _describe(layers: tuple[ReadLayer, ...]) -> str:
    """Shipped layers by count, the project layer by path: the adopter's files are named."""
    grouped: dict[str, list[str]] = {}
    for layer in sorted(layers, key=_rank):
        grouped.setdefault(layer.label, []).append(layer.source)
    parts = []
    for label, sources in grouped.items():
        if label == "project":
            parts.append(f"project ({', '.join(sources)})")
        else:
            parts.append(f"{label} ({len(sources)} fragment(s))")
    return ", ".join(parts)


def _display(source: str) -> str:
    """A shipped fragment's path from the package's ``templates/`` folder, else as read."""
    path = Path(source)
    root = templates_dir()
    if path.is_absolute() and path.is_relative_to(root):
        return str(Path(root.name) / path.relative_to(root))
    return source


def _layers_read(project_root: Path, config: FlowConfig, tool: str) -> frozenset[ReadLayer]:
    """The layers of every file ``tool`` reads that is on disk, its own layers left out."""
    read: set[ReadLayer] = set()
    for target in tool_targets(tool):
        if not (project_root / target.relpath).is_file():
            continue
        composition = compose(target.kind, target.name, config=config, project_root=project_root)
        for fragment in composition.fragments:
            if fragment.layer.startswith("project:"):
                continue  # a layer folder named for one tool is that tool's own
            label = "core" if fragment.layer.startswith("core") else fragment.layer
            read.add(ReadLayer(label, _display(fragment.source)))
    return frozenset(read)


def layer_gaps(project_root: Path, config: FlowConfig) -> tuple[LayerGap, ...]:
    """Every declared tool that lacks a layer another declared tool reads.

    The population is ``config.tools``: a project declaring one tool has nothing
    to compare and answers empty, which is a fact about the population rather
    than a pass over it.
    """
    reads = {tool: _layers_read(project_root, config, tool) for tool in config.tools}
    gaps: list[LayerGap] = []
    for tool in config.tools:
        for other in config.tools:
            if other == tool:
                continue
            lacking = reads[other] - reads[tool]
            if lacking:
                gaps.append(LayerGap(tool, other, tuple(sorted(lacking, key=_rank))))
    return tuple(gaps)
