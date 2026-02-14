# Graph Format

YAML format for describing the project architecture graph.

## Specification

### File Location

The graph is stored in `.beadloom/_graph/*.yml`. All files with the `.yml` extension in this directory are loaded during reindex, sorted by name.

### YAML Structure

```yaml
nodes:
  - ref_id: my-service        # Unique identifier (required)
    kind: service              # Node type (required)
    summary: "Description"     # Brief description (required)
    source: src/my_service/    # Path to source code (optional)
    docs:                      # Linked documents (optional)
      - docs/my-service.md
    # Any additional fields go into extra (JSON)

edges:
  - src: my-service            # Source ref_id (required)
    dst: core                  # Destination ref_id (required)
    kind: part_of              # Edge type (required)
```

### Node Types (node kind)

| Kind | Description |
|------|----------|
| `domain` | Domain area |
| `feature` | Feature |
| `service` | Service / module |
| `entity` | Data entity |
| `adr` | Architecture Decision Record |

### Edge Types (edge kind)

| Kind | Description | BFS Priority |
|------|----------|---------------|
| `part_of` | A is part of B | 1 |
| `touches_entity` | A touches entity B | 2 |
| `uses` | A uses B | 3 |
| `implements` | A implements B | 3 |
| `depends_on` | A depends on B | 4 |
| `touches_code` | A touches code of B | 5 |

### The docs Field

An array of paths to documents linked to the node. Paths are specified relative to the project root (e.g., `docs/spec.md`). During reindex, a doc_path → ref_id mapping is built to link chunks to graph nodes.

## Invariants

- `ref_id` must be unique across all YAML files
- `kind` for nodes is restricted to: domain, feature, service, entity, adr
- `kind` for edges is restricted to: part_of, depends_on, uses, implements, touches_entity, touches_code
- Edges referencing non-existent nodes are skipped with a warning
- Duplicate ref_id values are skipped with an error

## Constraints

- Files must be valid YAML
- UTF-8 encoding
- Only files with the `.yml` extension (not `.yaml`)
