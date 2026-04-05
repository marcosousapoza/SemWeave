"""Build a NodeGraph from annotated project files."""

from __future__ import annotations

import hashlib
from pathlib import Path

from semweave.config.schema import SemWeaveConfig
from semweave.core.parser import ParsedAnnotation, parse_file
from semweave.model.graph import NodeGraph
from semweave.model.node import Node
from semweave.traversal.scanner import scan_project


def _make_node_id(file_rel: str, start_line: int) -> str:
    """Generate a deterministic node ID from file path and start line."""
    raw = f"{file_rel}:{start_line}"
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def _generate_preview(lines: list[str], content_start: int, content_end: int, max_len: int = 100) -> str:
    """Generate a preview string from content lines."""
    content_lines = lines[content_start - 1 : content_end]
    text = " ".join(line.strip() for line in content_lines if line.strip())
    if len(text) > max_len:
        return text[:max_len] + "..."
    return text


def _build_nodes_from_annotations(
    file_rel: str,
    lines: list[str],
    annotations: list[ParsedAnnotation],
    config: SemWeaveConfig,
) -> list[Node]:
    """Build Node objects from paired begin/end annotations in a single file."""
    nodes: list[Node] = []
    stack: list[tuple[ParsedAnnotation, str]] = []  # (begin_annotation, node_id)

    for ann in annotations:
        if ann.type == "begin":
            node_id = _make_node_id(file_rel, ann.line_number)
            stack.append((ann, node_id))

        elif ann.type == "end":
            if not stack:
                continue  # Error already caught by parser

            begin_ann, node_id = stack.pop()
            parent_id = stack[-1][1] if stack else None

            # Extract known fields
            fields = dict(begin_ann.fields)
            role = str(fields.pop("role", begin_ann.node_type or "region"))
            name = fields.pop("name", None)
            if isinstance(name, list):
                name = name[0] if name else None
            elif isinstance(name, str):
                pass  # already a string

            anchor_field = config.node_schema.anchor_field
            anchors_val = fields.pop(anchor_field, [])
            if isinstance(anchors_val, str):
                anchors = [anchors_val]
            else:
                anchors = list(anchors_val)

            content_start = begin_ann.line_number + 1
            content_end = ann.line_number - 1

            node = Node(
                id=node_id,
                role=role,
                name=name,
                anchors=anchors,
                file=file_rel,
                start_line=begin_ann.line_number,
                end_line=ann.line_number,
                content_start=content_start,
                content_end=max(content_end, content_start),
                parent_id=parent_id,
                metadata={k: v for k, v in fields.items()},
                preview=_generate_preview(lines, content_start, content_end),
            )
            nodes.append(node)

    return nodes


def _assign_children(nodes: list[Node]) -> None:
    """Populate children_ids based on parent_id relationships."""
    id_to_node = {n.id: n for n in nodes}
    for node in nodes:
        if node.parent_id and node.parent_id in id_to_node:
            parent = id_to_node[node.parent_id]
            if node.id not in parent.children_ids:
                parent.children_ids.append(node.id)


def build_graph(root: Path, config: SemWeaveConfig) -> NodeGraph:
    """Build a complete NodeGraph by scanning and parsing all project files.

    Returns the graph along with any parse errors encountered.
    """
    root = root.resolve()
    graph = NodeGraph()
    all_nodes: list[Node] = []

    files = scan_project(root, config.traversal)

    for file_path in files:
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeDecodeError):
            continue

        lines = text.splitlines()
        file_rel = str(file_path.relative_to(root))

        result = parse_file(file_rel, lines, config)
        if not result.annotations:
            continue

        nodes = _build_nodes_from_annotations(file_rel, lines, result.annotations, config)
        all_nodes.extend(nodes)

    _assign_children(all_nodes)

    for node in all_nodes:
        graph.add_node(node)

    return graph
