"""The graph-files medium's verdict over a set of graph files."""

from __future__ import annotations

from beadloom.application.waves import (
    MEDIUM_GRAPH_FILES,
    STATUS_PASSED,
    GraphFile,
    GraphInput,
    WaveEnvironment,
    check_media,
)


def graph_files_verdict(files: tuple[GraphFile, ...]) -> str:
    indexed = frozenset(ref for file in files for ref in file.nodes)
    environment = WaveEnvironment(graph_input=GraphInput(files=files, indexed=indexed))
    check = next(
        c for c in check_media((), environment=environment) if c.medium == MEDIUM_GRAPH_FILES
    )
    assert check.status == STATUS_PASSED
    return check.detail
