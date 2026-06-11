# beadloom:domain=ai_agents
"""Governed AI-agent harnesses that ship inside the installed ``beadloom`` package.

This domain hosts deterministic, seam-isolated harnesses that orchestrate
external AI agents (Goose + a model) over Beadloom's own read APIs and the
``beadloom`` / ``bd`` shell commands. The first inhabitant is the
:mod:`beadloom.ai_agents.ai_techwriter` harness (BDL-047/049/050), moved here
from the former ``tools/ai_techwriter`` repo-tooling package (BDL-051 / S2) so
it is graph-tracked, lint-governed, and shipped as part of the wheel — adopters
run it directly via ``python -m beadloom.ai_agents.ai_techwriter`` (no
vendoring).

Boundary (``ai_agents`` rule in ``.beadloom/_graph/rules.yml``): ``ai_agents``
MAY consume ``application`` / ``context_oracle`` / ``graph`` / ``doc_sync`` read
APIs + stdlib + the ``beadloom`` / ``bd`` shells; it MUST NOT be imported BY the
core domains (it is a leaf consumer, never a dependency of the core).
"""

from __future__ import annotations
