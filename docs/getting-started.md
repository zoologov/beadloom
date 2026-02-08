# Getting Started

Getting started with Beadloom.

## Requirement

- Python 3.10+
- uv (recommended) or pip

## Installation

```bash
uv tool install beadloom
# or
pip install beadloom
```

## Specification

### Step 1: Initialization

```bash
cd your-project

# Automatically generate graph from code structure
beadloom init --bootstrap
```

This will create:
- `.beadloom/_graph/services.yml` — initial graph
- `.beadloom/config.yml` — project configuration

### Step 2: Refine the graph

Open `.beadloom/_graph/services.yml` and refine:
- Node names and descriptions
- Relationships between components
- Documentation bindings (the `docs` field)

### Step 3: Indexing

```bash
beadloom reindex
```

### Step 4: Verification

```bash
# Statistics
beadloom status

# Graph validation
beadloom doctor

# Context for a node
beadloom ctx my-service

# Graph visualization
beadloom graph
```

### Step 5: Configure MCP for AI agents

```bash
beadloom setup-mcp
```

This will create `.mcp.json` with configuration for Claude Code and other MCP-compatible agents.

## Limits

- code_indexer supports only Python files
- Documentation is indexed only from `docs/`
- Graph is described only in YAML (.yml)
- Maximum documentation chunk size: 2000 characters
