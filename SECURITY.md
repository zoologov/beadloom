# Security Policy

## Reporting Security Issues

If you discover a security vulnerability in Beadloom, please report it responsibly:

**Email**: Open a private security advisory on GitHub.

Please include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We will respond within 48 hours and work with you to address the issue.

## Security Considerations

### Database Security

Beadloom stores index data locally in:
- SQLite database (`.beadloom/beadloom.db`) — local only, gitignored
- YAML graph files (`.beadloom/_graph/*.yml`) — committed to git

**Important**:
- Do not store sensitive information (passwords, API keys, secrets) in graph node summaries or documentation chunks
- Graph YAML files are committed to git and will be visible to anyone with repository access
- Beadloom does not encrypt data at rest (it's a local development tool)

### MCP Server Security

- The MCP server runs over **stdio** transport only (no network exposure)
- It provides both read and write access to the architecture graph:
  - **Read operations** (12 tools): `get_context`, `get_graph`, `list_nodes`, `sync_check`, `get_status`, `search`, `generate_docs`, `prime`, `why`, `diff`, `lint`, `docs_audit`
  - **Write operations** (2 tools): `update_node` (modifies node summary/source in YAML and SQLite), `mark_synced` (updates sync state)
- Write operations modify local files only (YAML graph + SQLite index)
- The server opens the SQLite database in WAL mode

### Code Indexer Security

- The tree-sitter code indexer **parses** source code — it does not execute it
- Annotations (`# beadloom:key=value`) are read from comments only
- No user code is ever `eval`'d or `exec`'d

### SQL Injection Protection

Beadloom uses parameterized SQL queries throughout. Dynamic `IN (...)` clauses use placeholder generation (`?,?,?`) with bound parameters — no string interpolation of user data into SQL.

### Dependency Security

Beadloom has minimal runtime dependencies:
- `click` — CLI framework
- `rich` — Terminal formatting
- `pyyaml` — YAML parsing
- `tree-sitter` / `tree-sitter-python` — Code parsing
- `mcp` — Model Context Protocol SDK

All dependencies are pinned in `pyproject.toml` and regularly updated.

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| main    | :white_check_mark: |
| < 1.0   | :x:                |

Once version 1.0 is released, we will support the latest major version and one previous major version.

## Best Practices

1. **Don't index secrets** — Never put API keys, passwords, or credentials in files that beadloom indexes
2. **Review graph YAML** — Check `.beadloom/_graph/` files before committing sensitive project details
3. **Use private repos** — If your documentation contains proprietary information, use private git repositories
4. **Regular updates** — Keep beadloom updated: `uv tool install beadloom --upgrade`

## Known Limitations

- Beadloom is designed for **development/internal use**, not production secret management
- Index data is stored in plain text (SQLite and YAML)
- No built-in encryption or access control (relies on filesystem permissions)
- No audit logging beyond git history

For sensitive workflows, consider using beadloom only for non-sensitive documentation tracking.

## Security Updates

Security updates will be announced via:
- GitHub Security Advisories
- Release notes on GitHub
- Git commit messages (tagged with `[security]`)

Subscribe to the repository for notifications.
