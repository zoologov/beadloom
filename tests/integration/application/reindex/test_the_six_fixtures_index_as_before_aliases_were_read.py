"""The six adopter fixtures resolve every import as they did before aliases were read.

BDL-080 S3a (``beadloom-cwzc``). The resolver now reads tsconfig ``paths`` and ``baseUrl``,
the ``imports.aliases:`` block and React Native's platform suffixes, and the code indexer
parses ``.mjs``/``.cjs``. None of the six claimed stacks' fixtures declares any of them, so
each must index exactly as before: every stored import with its answer, every
``depends_on`` edge and every indexed file.

**The values were MEASURED, not written from the product.** They are what ``init --yes``
indexed on a copy of each fixture with the code before this bead (``ef2c35b6``), on
2026-10-09; the same measurement after the change was identical for all six, file index
included.

BDL-080 S3d (``beadloom-chdx``) added two fixtures that declare all of them; they have no
"before" and are measured by
``tests/integration/application/site/test_an_fsd_adopter_fixture_is_judged_by_the_rules_init_writes.py``.
"""

from __future__ import annotations

import shutil
import sqlite3
from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

from beadloom.services.cli import main
from tests.support.adopter_portals import FIXTURES_BY_STACK, SIX_STACKS, STORED_SUFFIX

if TYPE_CHECKING:
    from pathlib import Path

Row = tuple[object, ...]

#: Per stack: ``(file_path, line_number, import_path, resolved_ref_id)`` of every stored
#: import, sorted, as measured before this bead.
IMPORTS: dict[str, list[Row]] = {
    "go": [
        ("cmd/tidewater/main.go", 10, "example.org/tidewater/internal/storage", "storage"),
        ("cmd/tidewater/main.go", 5, "log", None),
        ("cmd/tidewater/main.go", 6, "net/http", None),
        ("cmd/tidewater/main.go", 8, "example.org/tidewater/internal/api", "api"),
        ("cmd/tidewater/main.go", 9, "example.org/tidewater/internal/catalog", "catalog"),
        ("internal/api/handler.go", 10, "example.org/tidewater/internal/catalog", "catalog"),
        ("internal/api/handler.go", 5, "encoding/json", None),
        ("internal/api/handler.go", 6, "net/http", None),
        ("internal/api/handler.go", 7, "strconv", None),
        ("internal/api/handler.go", 9, "example.org/tidewater/internal/billing", "billing"),
        ("internal/billing/billing.go", 4, "example.org/tidewater/internal/catalog", "catalog"),
        ("internal/catalog/catalog.go", 4, "example.org/tidewater/internal/storage", "storage"),
        ("internal/catalog/catalog_test.go", 4, "testing", None),
        (
            "internal/catalog/catalog_test.go",
            6,
            "example.org/tidewater/internal/storage",
            "storage",
        ),
    ],
    "java": [
        (
            "src/main/java/org/example/ledger/repository/EntryRepository.java",
            5,
            "org.example.ledger.model.Entry",
            "model",
        ),
        (
            "src/main/java/org/example/ledger/service/LedgerService.java",
            3,
            "org.example.ledger.model.Entry",
            "model",
        ),
        (
            "src/main/java/org/example/ledger/service/LedgerService.java",
            4,
            "org.example.ledger.repository.EntryRepository",
            "repository",
        ),
        (
            "src/main/java/org/example/ledger/web/LedgerController.java",
            3,
            "org.example.ledger.service.LedgerService",
            "service",
        ),
    ],
    "kotlin": [
        (
            "src/main/kotlin/org/example/orchard/planner/RoutePlanner.kt",
            3,
            "org.example.orchard.geo.Row",
            "geo",
        ),
        (
            "src/main/kotlin/org/example/orchard/planner/RoutePlanner.kt",
            4,
            "org.example.orchard.geo.distance",
            "geo",
        ),
        (
            "src/main/kotlin/org/example/orchard/routing/Main.kt",
            3,
            "org.example.orchard.geo.Row",
            "geo",
        ),
        (
            "src/main/kotlin/org/example/orchard/routing/Main.kt",
            4,
            "org.example.orchard.planner.RoutePlanner",
            "planner",
        ),
    ],
    "python": [
        ("src/parceldesk/api/routes.py", 5, "parceldesk.billing.invoice", "parceldesk-billing"),
        ("src/parceldesk/api/routes.py", 6, "parceldesk.storage.bookings", "parceldesk-storage"),
        ("src/parceldesk/billing/invoice.py", 5, "parceldesk.storage.rates", "parceldesk-storage"),
    ],
    "swift": [
        ("Sources/BeaconApp/main.swift", 1, "BeaconCore", "BeaconCore"),
        ("Sources/BeaconApp/main.swift", 2, "BeaconNetwork", "BeaconNetwork"),
        ("Sources/BeaconNetwork/Encoder.swift", 1, "BeaconCore", "BeaconCore"),
    ],
    "typescript": [
        ("src/accounts/session/session.test.ts", 1, "vitest", None),
        ("src/accounts/session/session.test.ts", 2, "./session.js", "accounts-session"),
        ("src/accounts/session/session.ts", 1, "../users/user.js", "accounts-users"),
        ("src/notes/api/main.ts", 1, "../store/noteStore.js", "notes-store"),
        ("src/notes/api/main.ts", 2, "./server.js", "notes-api"),
        ("src/notes/api/server.ts", 1, "node:http", None),
        ("src/notes/api/server.ts", 2, "../../accounts/session/session.js", "accounts-session"),
        ("src/notes/api/server.ts", 3, "../model/note.js", "notes-model"),
        ("src/notes/api/server.ts", 4, "../store/noteStore.js", "notes-store"),
        ("src/notes/model/note.test.ts", 1, "vitest", None),
        ("src/notes/model/note.test.ts", 2, "./note.js", "notes-model"),
        ("src/notes/model/note.ts", 1, "../store/limits.js", "notes-store"),
        ("src/notes/store/noteStore.ts", 1, "../model/note.js", "notes-model"),
        ("src/reports/digest/weeklyDigest.ts", 1, "../../notes/store/noteStore.js", "notes-store"),
    ],
}

#: Per stack: every ``depends_on`` edge ``(src, dst)``, sorted, as measured before.
EDGES: dict[str, list[Row]] = {
    "go": [
        ("api", "billing"),
        ("api", "catalog"),
        ("billing", "catalog"),
        ("catalog", "storage"),
        ("tidewater-service", "api"),
        ("tidewater-service", "catalog"),
        ("tidewater-service", "storage"),
    ],
    "java": [
        ("repository", "model"),
        ("service", "model"),
        ("service", "repository"),
        ("web", "service"),
    ],
    "kotlin": [
        ("planner", "geo"),
        ("routing", "geo"),
        ("routing", "planner"),
    ],
    "python": [
        ("parceldesk-api", "parceldesk-billing"),
        ("parceldesk-api", "parceldesk-storage"),
        ("parceldesk-billing", "parceldesk-storage"),
    ],
    "swift": [
        ("BeaconApp", "BeaconCore"),
        ("BeaconApp", "BeaconNetwork"),
        ("BeaconNetwork", "BeaconCore"),
    ],
    "typescript": [
        ("accounts-session", "accounts-users"),
        ("notes", "accounts"),
        ("notes-api", "accounts-session"),
        ("notes-api", "notes-model"),
        ("notes-api", "notes-store"),
        ("notes-model", "notes-store"),
        ("notes-store", "notes-model"),
        ("reports", "notes"),
        ("reports-digest", "notes-store"),
    ],
}

#: Per stack: how many files the index holds, as measured before.
FILES: dict[str, int] = {
    "go": 16,
    "java": 12,
    "kotlin": 11,
    "python": 17,
    "swift": 11,
    "typescript": 23,
}


def _indexed(stack: str, workdir: Path) -> Path:
    """A copy of *stack*'s fixture with its stored names restored, indexed by ``init --yes``."""
    root = workdir / stack
    shutil.copytree(FIXTURES_BY_STACK[stack].source, root)
    for stored in sorted(root.rglob(f"*{STORED_SUFFIX}")):
        stored.rename(stored.with_name(stored.name.removesuffix(STORED_SUFFIX)))
    result = CliRunner().invoke(main, ["init", "--yes", "--project", str(root)])
    assert result.exit_code == 0, result.output
    return root


def test_every_stack_is_measured() -> None:
    assert set(IMPORTS) == set(EDGES) == set(FILES) == set(SIX_STACKS)


@pytest.mark.parametrize("stack", sorted(SIX_STACKS))
def test_the_fixture_indexes_exactly_as_before(stack: str, tmp_path: Path) -> None:
    root = _indexed(stack, tmp_path)
    with sqlite3.connect(root / ".beadloom" / "beadloom.db") as conn:
        imports = conn.execute(
            "SELECT file_path, line_number, import_path, resolved_ref_id FROM code_imports"
        ).fetchall()
        edges = conn.execute(
            "SELECT src_ref_id, dst_ref_id FROM edges WHERE kind = 'depends_on'"
        ).fetchall()
        files = conn.execute("SELECT count(*) FROM file_index").fetchone()[0]
    assert sorted(map(tuple, imports), key=repr) == IMPORTS[stack]
    assert sorted(map(tuple, edges), key=repr) == EDGES[stack]
    assert files == FILES[stack]
