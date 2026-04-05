# SemWeave

Language-agnostic MCP tool for annotation-driven structured navigation, selective retrieval, and structure-aware editing over arbitrary document and code projects.

## What It Does

SemWeave builds a semantic node graph over a project using declarative annotations embedded in comments. It does not parse the underlying language — instead, it extracts structure from annotation comments and treats the rest of the file as opaque content.

This enables AI agents to:
- **Discover structure** across a project
- **Locate precise regions** via nodes and anchors
- **Retrieve only relevant content** (annotations stripped)
- **Perform safe, structure-aware edits**

## Quick Start

### Install

```bash
pip install -e ".[dev]"
```

### Configure

Create `mcp.config.json` in your project root:

```json
{
  "comment_styles": [{"prefix": "%"}],
  "node_schema": {
    "roles": ["section", "definition", "example"],
    "fields": [{"name": "role", "required": true}]
  }
}
```

### Annotate

Add annotations to your files using comment syntax:

```latex
% mcp: begin region role=section name=introduction anchors=[sec:intro]
\section{Introduction}
This is the introduction.
% mcp: end
```

### Run

```bash
python -m semweave
```

## Annotation Syntax

**Begin marker:**
```
<comment_prefix> <annotation_prefix> begin <node_type> <key=value fields>
```

**End marker:**
```
<comment_prefix> <annotation_prefix> end
```

Supports any comment style — LaTeX (`%`), HTML/Markdown (`<!-- -->`), C-style (`//`), Python (`#`), etc.

## MCP Tools

| Category  | Tools |
|-----------|-------|
| Discovery | `get_schema`, `list_roles`, `find_nodes`, `get_node`, `get_children`, `get_ancestors`, `find_by_anchor`, `find_references` |
| Content   | `read_node`, `read_span`, `read_surrounding_context` |
| Write     | `replace_node`, `insert_before`, `insert_after`, `delete_node` |

See [docs/mcp_api.md](docs/mcp_api.md) for the full API reference.

## Documentation

- [Architecture](docs/architecture.md)
- [Configuration Schema](docs/schema.md)
- [MCP API Reference](docs/mcp_api.md)
- [Agent Annotation Skill](skills/annotate.md)

## Examples

- [`examples/latex/`](examples/latex/) — LaTeX document with sections, theorems, and proofs
- [`examples/markdown/`](examples/markdown/) — Markdown documentation with nested sections
- [`examples/html/`](examples/html/) — HTML page with structured regions

## License

GPL-3.0 — see [LICENSE](LICENSE).
