# beadloom:domain=ai_agents
"""Module entrypoint: ``python -m beadloom.ai_agents.ai_techwriter``.

Delegates to the thin Click CLI (:func:`beadloom.ai_agents.ai_techwriter.cli.main`). This is
the single command BOTH CI wrappers invoke (GitHub workflow + GitLab job) —
only the trigger, the secret naming, and the ``--platform`` flag differ.
"""

from __future__ import annotations

from beadloom.ai_agents.ai_techwriter.cli import main

if __name__ == "__main__":
    main()
