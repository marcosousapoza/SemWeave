# SemWeave Configuration Schema

## Config File

SemWeave projects are configured via `mcp.config.json` in the project root.

## Full Schema

```json
{
  "comment_styles": [
    {
      "prefix": "%",
      "suffix": null
    },
    {
      "prefix": "<!--",
      "suffix": "-->"
    }
  ],
  "annotation_prefix": "mcp:",
  "node_schema": {
    "roles": ["section", "definition", "example", "theorem", "proof", "note", "code"],
    "fields": [
      {"name": "role", "required": true, "type": "str"},
      {"name": "name", "required": false, "type": "str"},
      {"name": "anchors", "required": false, "type": "list"}
    ],
    "anchor_field": "anchors"
  },
  "traversal": {
    "include": ["**/*"],
    "exclude": [],
    "extensions": [".tex", ".md", ".html"],
    "root": null
  },
  "hide_annotations": true,
  "begin_keyword": "begin",
  "end_keyword": "end"
}
```

## Field Reference

### `comment_styles` (required)
Array of comment syntax definitions.

| Field    | Type          | Description                              |
|----------|---------------|------------------------------------------|
| `prefix` | string        | Comment opening token (e.g. `%`, `//`)   |
| `suffix` | string\|null  | Comment closing token (e.g. `-->`)       |

### `annotation_prefix` (default: `"mcp:"`)
The prefix that identifies SemWeave annotations within comments.

### `node_schema` (required)
Defines the structure vocabulary for the project.

| Field          | Type          | Description                                |
|----------------|---------------|--------------------------------------------|
| `roles`        | string[]      | Finite set of allowed node roles           |
| `fields`       | FieldSpec[]   | Field specifications for annotations       |
| `anchor_field` | string        | Name of the field used for anchors         |

### `traversal` (optional)
Controls which files are scanned.

| Field        | Type           | Default    | Description                        |
|--------------|----------------|------------|------------------------------------|
| `include`    | string[]       | `["**/*"]` | Glob patterns for files to include |
| `exclude`    | string[]       | `[]`       | Glob patterns for files to exclude |
| `extensions` | string[]\|null | `null`     | Filter by file extension           |
| `root`       | string\|null   | `null`     | Optional logical root file         |

### `hide_annotations` (default: `true`)
Whether to strip annotation comments from content reads.

### `begin_keyword` / `end_keyword` (default: `"begin"` / `"end"`)
Keywords that start and end annotated regions.

## Annotation Syntax

### Begin marker
```
<comment_prefix> <annotation_prefix> <begin_keyword> <node_type> <key=value fields>
```

### End marker
```
<comment_prefix> <annotation_prefix> <end_keyword>
```

### Field syntax
- `key=value` — string field
- `key=[a,b,c]` — list field
- `key="quoted value"` — quoted string field

## Node Model

Each annotated region produces a node with:

| Field           | Type              | Description                          |
|-----------------|-------------------|--------------------------------------|
| `id`            | string            | Deterministic handle                 |
| `role`          | string            | From configured roles                |
| `name`          | string\|null      | User-defined name                    |
| `anchors`       | string[]          | Cross-reference identifiers          |
| `file`          | string            | Relative file path                   |
| `start_line`    | int               | Line of begin annotation (1-indexed) |
| `end_line`      | int               | Line of end annotation (1-indexed)   |
| `content_start` | int               | First content line                   |
| `content_end`   | int               | Last content line                    |
| `parent_id`     | string\|null      | ID of enclosing node                 |
| `children_ids`  | string[]          | IDs of nested nodes                  |
| `metadata`      | dict              | Extra key-value pairs                |
| `preview`       | string            | First ~100 chars of content          |
