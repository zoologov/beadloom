# Doc Sync Engine

Mechanism for tracking synchronization between documentation and code.

## Specification

### How It Works

Doc Sync Engine compares document and code hashes to detect desynchronization:

1. **build_sync_state** — finds doc↔code pairs that share the same ref_id
2. **check_sync** — compares current file hashes with those stored in sync_state

### Sync Pair

```python
@dataclass
class SyncPair:
    ref_id: str
    doc_path: str
    code_path: str
    doc_hash: str
    code_hash: str
```

### Statuses

| Status | Description |
|--------|----------|
| `ok` | Document and code are synchronized |
| `stale` | Hash has changed — update needed |

### Git Hook Integration

Beadloom can install a pre-commit hook for automatic checking:

```bash
# Warning mode (does not block commit)
beadloom install-hooks --mode warn

# Blocking mode (blocks commit on stale docs)
beadloom install-hooks --mode block
```

## Invariants

- A doc↔code pair is determined by a shared ref_id
- doc_path is taken from the docs table (linked to a node via ref_id)
- code_path is taken from code_symbols (via annotations pointing to a ref_id)
- When staleness is detected, the status is updated in the sync_state table

## API

Module `src/beadloom/sync_engine.py`:

- `build_sync_state(conn)` → `list[SyncPair]`
- `check_sync(conn)` → `list[dict]` with fields ref_id, doc_path, code_path, status

## Testing

Tests: `tests/test_sync_engine.py`, `tests/test_cli_sync_check.py`, `tests/test_cli_sync_update.py`
