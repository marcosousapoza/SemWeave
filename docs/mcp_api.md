# SemWeave MCP API Reference

## Running the Server

```bash
# From a project directory containing mcp.config.json
python -m semweave

# Or specify the project root via environment variable
SEMWEAVE_PROJECT_ROOT=/path/to/project python -m semweave
```

## Discovery Tools

These tools return metadata only — no raw file content.

### `get_schema()`
Returns the project's annotation configuration so the agent understands the vocabulary.

**Returns:** `{annotation_prefix, begin_keyword, end_keyword, comment_styles, roles, fields, anchor_field}`

### `list_roles()`
Returns the list of configured node roles.

**Returns:** `string[]`

### `find_nodes(role?, name?, file?)`
Search for nodes matching optional filters. All parameters are optional.

**Parameters:**
| Name   | Type          | Description                |
|--------|---------------|----------------------------|
| `role` | string\|null  | Filter by node role        |
| `name` | string\|null  | Filter by exact node name  |
| `file` | string\|null  | Filter by relative file path |

**Returns:** Array of node summaries `{id, role, name, anchors, file, preview, children_count}`

### `get_node(handle)`
Get full metadata for a single node.

**Parameters:**
| Name     | Type   | Description |
|----------|--------|-------------|
| `handle` | string | Node ID     |

**Returns:** Full node object or `{error: "..."}`

### `get_children(handle)`
List direct children of a node.

**Returns:** Array of node summaries

### `get_ancestors(handle)`
List ancestors from immediate parent up to root.

**Returns:** Array of node summaries (parent first, root last)

### `find_by_anchor(anchor)`
Find the node that owns a given anchor.

**Parameters:**
| Name     | Type   | Description          |
|----------|--------|----------------------|
| `anchor` | string | Anchor identifier    |

**Returns:** Node summary or `{error: "..."}`

### `find_references(anchor)`
Find all nodes whose content contains references to an anchor.

**Returns:** Array of node summaries (excludes the node that owns the anchor)

## Content Tools

These tools return raw file content with annotation comments stripped.

### `read_node(handle)`
Read the full content of a node.

**Returns:** `{id, file, content}`

### `read_span(handle, start_offset?, end_offset?)`
Read a line range within a node's content.

**Parameters:**
| Name           | Type      | Default | Description                    |
|----------------|-----------|---------|--------------------------------|
| `handle`       | string    | —       | Node ID                        |
| `start_offset` | int       | 0       | Start line (0-indexed)         |
| `end_offset`   | int\|null | null    | End line (exclusive, null=end) |

**Returns:** `{id, file, content, total_lines, start_offset, end_offset}`

### `read_surrounding_context(handle, lines_before?, lines_after?)`
Read content around a node including surrounding file context.

**Parameters:**
| Name           | Type | Default | Description              |
|----------------|------|---------|--------------------------|
| `handle`       | string | —     | Node ID                  |
| `lines_before` | int  | 5       | Lines before the node    |
| `lines_after`  | int  | 5       | Lines after the node     |

**Returns:** `{id, file, before, content, after}`

## Write Tools

Structure-aware editing. All edits trigger a full graph rebuild.

### `replace_node(handle, new_content)`
Replace the content between a node's begin/end annotations. The annotations themselves are preserved.

**Returns:** `{success: true, file, handle}` or `{error: "..."}`

### `insert_before(handle, content)`
Insert content immediately before a node's begin annotation.

**Returns:** `{success: true, file}` or `{error: "..."}`

### `insert_after(handle, content)`
Insert content immediately after a node's end annotation.

**Returns:** `{success: true, file}` or `{error: "..."}`

### `delete_node(handle)`
Delete a node including its begin/end annotations and all content.

**Returns:** `{success: true, file, deleted_handle}` or `{error: "..."}`

## Important Notes

- **Node IDs are line-dependent.** After write operations that shift line numbers, previously returned node IDs become stale. Always use the updated graph after writes.
- **Annotation stripping.** All content reads strip annotation comment lines by default (configurable via `hide_annotations` in config).
- **Single-file edits.** All write operations work within a single file. Cross-file edits require multiple tool calls.
