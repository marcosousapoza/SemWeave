"""Structure-aware editing operations for annotated files."""

from __future__ import annotations

from pathlib import Path

from semweave.config.schema import SemWeaveConfig
from semweave.model.graph import NodeGraph
from semweave.model.node import Node
from semweave.traversal.builder import build_graph


class EditError(Exception):
    """Raised when an edit operation cannot be performed."""


def _read_lines(project_root: Path, file_rel: str) -> list[str]:
    file_path = project_root / file_rel
    return file_path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)


def _write_lines(project_root: Path, file_rel: str, lines: list[str]) -> None:
    file_path = project_root / file_rel
    file_path.write_text("".join(lines), encoding="utf-8")


def _get_node(graph: NodeGraph, handle: str) -> Node:
    node = graph.get_node(handle)
    if node is None:
        raise EditError(f"Node not found: {handle}")
    return node


def replace_node_content(
    graph: NodeGraph,
    handle: str,
    new_content: str,
    project_root: Path,
    config: SemWeaveConfig,
) -> NodeGraph:
    """Replace content between a node's begin/end annotations."""
    node = _get_node(graph, handle)
    lines = _read_lines(project_root, node.file)

    new_lines = new_content.splitlines(keepends=True)
    if new_content and not new_content.endswith("\n"):
        new_lines.append("\n")

    before = lines[: node.content_start - 1]
    after = lines[node.content_end :]
    result = before + new_lines + after

    _write_lines(project_root, node.file, result)
    return build_graph(project_root, config)


def insert_before_node(
    graph: NodeGraph,
    handle: str,
    content: str,
    project_root: Path,
    config: SemWeaveConfig,
) -> NodeGraph:
    """Insert content before a node's begin annotation."""
    node = _get_node(graph, handle)
    lines = _read_lines(project_root, node.file)

    insert_lines = content.splitlines(keepends=True)
    if content and not content.endswith("\n"):
        insert_lines.append("\n")

    insert_pos = node.start_line - 1
    result = lines[:insert_pos] + insert_lines + lines[insert_pos:]

    _write_lines(project_root, node.file, result)
    return build_graph(project_root, config)


def insert_after_node(
    graph: NodeGraph,
    handle: str,
    content: str,
    project_root: Path,
    config: SemWeaveConfig,
) -> NodeGraph:
    """Insert content after a node's end annotation."""
    node = _get_node(graph, handle)
    lines = _read_lines(project_root, node.file)

    insert_lines = content.splitlines(keepends=True)
    if content and not content.endswith("\n"):
        insert_lines.append("\n")

    insert_pos = node.end_line
    result = lines[:insert_pos] + insert_lines + lines[insert_pos:]

    _write_lines(project_root, node.file, result)
    return build_graph(project_root, config)


def delete_node_region(
    graph: NodeGraph,
    handle: str,
    project_root: Path,
    config: SemWeaveConfig,
) -> NodeGraph:
    """Delete a node including its annotations and all content."""
    node = _get_node(graph, handle)
    lines = _read_lines(project_root, node.file)

    before = lines[: node.start_line - 1]
    after = lines[node.end_line :]
    result = before + after

    _write_lines(project_root, node.file, result)
    return build_graph(project_root, config)
