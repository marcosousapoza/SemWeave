"""SemWeave MCP server exposing annotation-driven navigation tools."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastmcp import Context, FastMCP

from semweave.adapters.comments import CommentAdapter
from semweave.config.loader import load_config
from semweave.config.schema import SemWeaveConfig
from semweave.model.graph import NodeGraph
from semweave.model.node import Node, NodeSummary
from semweave.traversal.builder import build_graph


def _get_project_root() -> Path:
    """Determine the project root from environment or cwd."""
    root = os.environ.get("SEMWEAVE_PROJECT_ROOT", os.getcwd())
    return Path(root).resolve()


@asynccontextmanager
async def lifespan(server: FastMCP):
    project_root = _get_project_root()
    config = load_config(project_root)
    graph = build_graph(project_root, config)
    yield {
        "graph": graph,
        "config": config,
        "project_root": project_root,
    }


mcp = FastMCP("SemWeave", lifespan=lifespan)


def _ctx(ctx: Context) -> tuple[NodeGraph, SemWeaveConfig, Path]:
    """Extract graph, config, and project root from the context."""
    lc = ctx.lifespan_context
    return lc["graph"], lc["config"], lc["project_root"]


def _read_file_lines(project_root: Path, file_rel: str) -> list[str]:
    """Read file lines from the project."""
    file_path = project_root / file_rel
    return file_path.read_text(encoding="utf-8", errors="replace").splitlines()


def _strip_content(
    lines: list[str], node: Node, config: SemWeaveConfig
) -> str:
    """Extract node content with annotation lines stripped."""
    adapter = CommentAdapter(config.comment_styles, config.annotation_prefix)
    content_lines = lines[node.content_start - 1 : node.content_end]
    if config.hide_annotations:
        content_lines = adapter.strip_annotations(content_lines)
    return "\n".join(content_lines)


# ── Discovery tools ──────────────────────────────────────────────────────


@mcp.tool()
def get_schema(ctx: Context) -> dict[str, Any]:
    """Get the project's annotation schema and configuration.

    Returns the configured roles, fields, annotation format, and comment styles
    so the agent understands the project's structure vocabulary.
    """
    _, config, _ = _ctx(ctx)
    return {
        "annotation_prefix": config.annotation_prefix,
        "begin_keyword": config.begin_keyword,
        "end_keyword": config.end_keyword,
        "comment_styles": [s.model_dump() for s in config.comment_styles],
        "roles": config.node_schema.roles,
        "fields": [f.model_dump() for f in config.node_schema.fields],
        "anchor_field": config.node_schema.anchor_field,
    }


@mcp.tool()
def list_roles(ctx: Context) -> list[str]:
    """List all configured node roles.

    Returns the finite set of allowed roles that nodes can have,
    as defined in the project configuration.
    """
    _, config, _ = _ctx(ctx)
    return config.node_schema.roles


@mcp.tool()
def find_nodes(
    ctx: Context,
    role: str | None = None,
    name: str | None = None,
    file: str | None = None,
) -> list[dict[str, Any]]:
    """Find nodes matching optional filters.

    Returns lightweight summaries (no raw content) for nodes matching
    the given role, name, and/or file filters. All filters are optional;
    omitting all filters returns all nodes.
    """
    graph, _, _ = _ctx(ctx)
    nodes = graph.find_nodes(role=role, name=name, file=file)
    return [NodeSummary.from_node(n).model_dump() for n in nodes]


@mcp.tool()
def get_node(ctx: Context, handle: str) -> dict[str, Any]:
    """Get full metadata for a node by its handle/ID.

    Returns all node metadata including parent, children, anchors,
    and line positions. Does not return raw content.
    """
    graph, _, _ = _ctx(ctx)
    node = graph.get_node(handle)
    if node is None:
        return {"error": f"Node not found: {handle}"}
    return node.model_dump()


@mcp.tool()
def get_children(ctx: Context, handle: str) -> list[dict[str, Any]]:
    """Get direct children of a node.

    Returns lightweight summaries of all immediate child nodes.
    """
    graph, _, _ = _ctx(ctx)
    children = graph.get_children(handle)
    return [NodeSummary.from_node(n).model_dump() for n in children]


@mcp.tool()
def get_ancestors(ctx: Context, handle: str) -> list[dict[str, Any]]:
    """Get ancestors of a node from immediate parent up to root.

    Returns a list of node summaries ordered from immediate parent to root.
    """
    graph, _, _ = _ctx(ctx)
    ancestors = graph.get_ancestors(handle)
    return [NodeSummary.from_node(n).model_dump() for n in ancestors]


@mcp.tool()
def find_by_anchor(ctx: Context, anchor: str) -> dict[str, Any]:
    """Find the node that owns a given anchor identifier.

    Anchors are unique identifiers assigned to nodes for cross-referencing.
    Returns the node summary, or an error if the anchor is not found.
    """
    graph, _, _ = _ctx(ctx)
    node = graph.find_by_anchor(anchor)
    if node is None:
        return {"error": f"Anchor not found: {anchor}"}
    return NodeSummary.from_node(node).model_dump()


@mcp.tool()
def find_references(ctx: Context, anchor: str) -> list[dict[str, Any]]:
    """Find all nodes whose content references a given anchor.

    Searches the raw content of all nodes for occurrences of the anchor
    string, returning summaries of nodes that contain references to it.
    """
    graph, config, project_root = _ctx(ctx)
    referencing: list[NodeSummary] = []

    for node in graph.nodes.values():
        try:
            lines = _read_file_lines(project_root, node.file)
            content = "\n".join(lines[node.content_start - 1 : node.content_end])
            if anchor in content:
                # Don't include the node that owns the anchor
                if anchor not in node.anchors:
                    referencing.append(NodeSummary.from_node(node))
        except (OSError, IndexError):
            continue

    return [r.model_dump() for r in referencing]


# ── Content reading tools ────────────────────────────────────────────────


@mcp.tool()
def read_node(ctx: Context, handle: str) -> dict[str, Any]:
    """Read the content of a node with annotation comments stripped.

    Returns the raw content between the node's begin and end markers,
    with all annotation comment lines removed for clean reading.
    """
    graph, config, project_root = _ctx(ctx)
    node = graph.get_node(handle)
    if node is None:
        return {"error": f"Node not found: {handle}"}

    try:
        lines = _read_file_lines(project_root, node.file)
        content = _strip_content(lines, node, config)
        return {
            "id": node.id,
            "file": node.file,
            "content": content,
        }
    except OSError as e:
        return {"error": f"Failed to read file: {e}"}


@mcp.tool()
def read_span(
    ctx: Context,
    handle: str,
    start_offset: int = 0,
    end_offset: int | None = None,
) -> dict[str, Any]:
    """Read a specific span of lines within a node's content.

    Offsets are relative to the node's content (0-indexed, after annotation stripping).
    Useful for reading only part of a large node.
    """
    graph, config, project_root = _ctx(ctx)
    node = graph.get_node(handle)
    if node is None:
        return {"error": f"Node not found: {handle}"}

    try:
        lines = _read_file_lines(project_root, node.file)
        adapter = CommentAdapter(config.comment_styles, config.annotation_prefix)
        content_lines = lines[node.content_start - 1 : node.content_end]
        if config.hide_annotations:
            content_lines = adapter.strip_annotations(content_lines)

        if end_offset is None:
            end_offset = len(content_lines)
        span = content_lines[start_offset:end_offset]

        return {
            "id": node.id,
            "file": node.file,
            "content": "\n".join(span),
            "total_lines": len(content_lines),
            "start_offset": start_offset,
            "end_offset": end_offset,
        }
    except OSError as e:
        return {"error": f"Failed to read file: {e}"}


@mcp.tool()
def read_surrounding_context(
    ctx: Context,
    handle: str,
    lines_before: int = 5,
    lines_after: int = 5,
) -> dict[str, Any]:
    """Read content around a node including surrounding context.

    Returns lines before and after the node's boundaries to provide
    context about where the node sits in its file. Annotation comments
    within the node are stripped, but surrounding content is returned as-is.
    """
    graph, config, project_root = _ctx(ctx)
    node = graph.get_node(handle)
    if node is None:
        return {"error": f"Node not found: {handle}"}

    try:
        lines = _read_file_lines(project_root, node.file)

        before_start = max(0, node.start_line - 1 - lines_before)
        before = lines[before_start : node.start_line - 1]

        after_end = min(len(lines), node.end_line + lines_after)
        after = lines[node.end_line : after_end]

        content = _strip_content(lines, node, config)

        return {
            "id": node.id,
            "file": node.file,
            "before": "\n".join(before),
            "content": content,
            "after": "\n".join(after),
        }
    except OSError as e:
        return {"error": f"Failed to read file: {e}"}


# ── Write tools ──────────────────────────────────────────────────────────


@mcp.tool()
def replace_node(ctx: Context, handle: str, new_content: str) -> dict[str, Any]:
    """Replace the content of a node while preserving its annotation boundaries.

    Replaces all lines between the begin and end annotations with new_content.
    The begin/end annotation markers are preserved. The graph is rebuilt after
    the edit to reflect changes.
    """
    graph, config, project_root = _ctx(ctx)
    node = graph.get_node(handle)
    if node is None:
        return {"error": f"Node not found: {handle}"}

    try:
        file_path = project_root / node.file
        lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)

        new_lines = new_content.splitlines(keepends=True)
        if new_content and not new_content.endswith("\n"):
            new_lines.append("\n")

        # Replace content between begin and end annotations
        before = lines[: node.content_start - 1]
        after = lines[node.content_end :]
        result = before + new_lines + after

        file_path.write_text("".join(result), encoding="utf-8")

        # Rebuild graph
        new_graph = build_graph(project_root, config)
        ctx.lifespan_context["graph"] = new_graph

        return {"success": True, "file": node.file, "handle": handle}
    except OSError as e:
        return {"error": f"Failed to write file: {e}"}


@mcp.tool()
def insert_before(ctx: Context, handle: str, content: str) -> dict[str, Any]:
    """Insert content before a node's begin annotation.

    The inserted content appears immediately before the node's opening
    annotation marker. The graph is rebuilt after the edit.
    """
    graph, config, project_root = _ctx(ctx)
    node = graph.get_node(handle)
    if node is None:
        return {"error": f"Node not found: {handle}"}

    try:
        file_path = project_root / node.file
        lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)

        insert_lines = content.splitlines(keepends=True)
        if content and not content.endswith("\n"):
            insert_lines.append("\n")

        insert_pos = node.start_line - 1
        result = lines[:insert_pos] + insert_lines + lines[insert_pos:]

        file_path.write_text("".join(result), encoding="utf-8")

        new_graph = build_graph(project_root, config)
        ctx.lifespan_context["graph"] = new_graph

        return {"success": True, "file": node.file}
    except OSError as e:
        return {"error": f"Failed to write file: {e}"}


@mcp.tool()
def insert_after(ctx: Context, handle: str, content: str) -> dict[str, Any]:
    """Insert content after a node's end annotation.

    The inserted content appears immediately after the node's closing
    annotation marker. The graph is rebuilt after the edit.
    """
    graph, config, project_root = _ctx(ctx)
    node = graph.get_node(handle)
    if node is None:
        return {"error": f"Node not found: {handle}"}

    try:
        file_path = project_root / node.file
        lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)

        insert_lines = content.splitlines(keepends=True)
        if content and not content.endswith("\n"):
            insert_lines.append("\n")

        insert_pos = node.end_line
        result = lines[:insert_pos] + insert_lines + lines[insert_pos:]

        file_path.write_text("".join(result), encoding="utf-8")

        new_graph = build_graph(project_root, config)
        ctx.lifespan_context["graph"] = new_graph

        return {"success": True, "file": node.file}
    except OSError as e:
        return {"error": f"Failed to write file: {e}"}


@mcp.tool()
def delete_node(ctx: Context, handle: str) -> dict[str, Any]:
    """Delete a node and all its content including annotation markers.

    Removes the entire region from the begin annotation through the end
    annotation (inclusive). The graph is rebuilt after the edit.
    """
    graph, config, project_root = _ctx(ctx)
    node = graph.get_node(handle)
    if node is None:
        return {"error": f"Node not found: {handle}"}

    try:
        file_path = project_root / node.file
        lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)

        before = lines[: node.start_line - 1]
        after = lines[node.end_line :]
        result = before + after

        file_path.write_text("".join(result), encoding="utf-8")

        new_graph = build_graph(project_root, config)
        ctx.lifespan_context["graph"] = new_graph

        return {"success": True, "file": node.file, "deleted_handle": handle}
    except OSError as e:
        return {"error": f"Failed to write file: {e}"}
