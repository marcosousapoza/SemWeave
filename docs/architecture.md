# SemWeave Architecture

## Overview

SemWeave is a language-agnostic MCP (Model Context Protocol) server that builds a semantic node graph over annotated project files. It enables AI agents to discover structure, navigate hierarchies, retrieve content, and perform safe edits.

## Design Principles

1. **Annotation-first**: Structure is declared through comments, not inferred from language syntax
2. **Graph-based**: Nodes form both a hierarchy (nesting) and a reference graph (anchors)
3. **Language-agnostic**: Only depends on comment syntax and file traversal
4. **Context-efficient**: Discovery returns metadata only; content on explicit request
5. **Structure-aware editing**: All edits operate on node handles, not raw offsets

## Data Flow

```
mcp.config.json
    │
    ▼
SemWeaveConfig (Pydantic validation)
    │
    ▼
CommentAdapter (comment style → annotation extraction)
    │
    ▼
Scanner (file discovery via include/exclude patterns)
    │
    ▼
Parser (extract begin/end annotations, parse fields)
    │
    ▼
Builder (pair annotations → Node objects, assign hierarchy)
    │
    ▼
NodeGraph (indexed by id, anchor, role, file)
    │
    ▼
MCP Tools (FastMCP server exposing discovery, read, write)
```

## Module Structure

### `config/` — Configuration
- `schema.py`: Pydantic models for `mcp.config.json`
- `loader.py`: Find and load configuration
- `defaults.py`: Fallback configuration when no config file exists

### `adapters/` — Comment Syntax
- `comments.py`: `CommentAdapter` class that extracts annotation content from comment lines, supporting prefix-only (`%`, `//`, `#`) and prefix+suffix (`<!-- -->`) styles

### `core/` — Annotation Parsing
- `parser.py`: Parse annotation content into `ParsedAnnotation` objects, validate nesting, extract fields

### `model/` — Data Structures
- `node.py`: `Node` and `NodeSummary` Pydantic models
- `graph.py`: `NodeGraph` with indexed lookups (by id, anchor, role, file)

### `traversal/` — Project Scanning
- `scanner.py`: File discovery with glob patterns
- `builder.py`: Full pipeline from files → parsed annotations → NodeGraph

### `mcp_server/` — MCP Interface
- `server.py`: FastMCP server with lifespan initialization and all tool definitions

## Key Design Decisions

### Node IDs
Node IDs are deterministic hashes of `{file_path}:{start_line}`. This ensures stable handles across rebuilds of the same content, but IDs change when line numbers shift due to edits.

### Graph Rebuild After Writes
After any write operation, the entire graph is rebuilt from scratch. This is simple and correct. The rebuild cost is negligible for typical annotation-scale projects.

### Annotation Stripping
Content reading tools always strip annotation comment lines. Agents never see the SemWeave annotations in returned content, keeping the focus on actual document/code content.

### Lifespan Pattern
The MCP server uses FastMCP's lifespan context to load configuration and build the graph once at startup. The graph is stored in the lifespan context and updated in-place after write operations.
