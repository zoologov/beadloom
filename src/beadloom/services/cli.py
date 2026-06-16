"""Beadloom CLI entry point — registration shell over ``services/commands/``.

The CLI commands live in cohesive modules under :mod:`beadloom.services.commands`
(BDL-059 S4). This module wires them onto the shared ``main`` Click group by
importing each command module for its registration side effects, then exposes
the stable public surface: ``main`` (the console-script entry,
``beadloom.services.cli:main``) plus the private helpers that the test-suite and
sibling domains import directly. Behavior is unchanged — every command name,
option, help text, output, and exit code is preserved.
"""

# beadloom:service=cli

from __future__ import annotations

# ``click`` is re-exposed here so that tests patching
# ``beadloom.services.cli.click.<attr>`` keep hitting the shared click module the
# command modules use (the patch target survived the S4 split).
import click

# Import command modules with no re-exported symbol purely for their
# registration side effects (decorators attach commands onto ``main`` / its
# sub-groups at import time).
from beadloom.services.commands import docs, setup, snapshot, status
from beadloom.services.commands._root import main

# Re-export the public + private surface that tests + sibling modules import
# from ``beadloom.services.cli`` (stable public import path across the S4 split).
# These imports also wire the remaining command modules' registration.
from beadloom.services.commands.dashboard import tui, ui
from beadloom.services.commands.docsync import (
    _bd_statuses_from_list,
    _has_active_table,
    _jsonl_is_tracked,
    _query_bd_statuses,
)
from beadloom.services.commands.federation import _format_gate_github, _parse_fail_on
from beadloom.services.commands.index_ops import _detect_link_label
from beadloom.services.commands.query import _format_markdown

# Mark the side-effect-only imports as used (they register commands on import).
_REGISTRATION_ONLY = (docs, setup, snapshot, status)

__all__ = [
    "_bd_statuses_from_list",
    "_detect_link_label",
    "_format_gate_github",
    "_format_markdown",
    "_has_active_table",
    "_jsonl_is_tracked",
    "_parse_fail_on",
    "_query_bd_statuses",
    "click",
    "main",
    "tui",
    "ui",
]
