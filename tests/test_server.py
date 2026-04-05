"""Tests for the MCP server tools."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from semweave.config.schema import (
    CommentStyle,
    FieldSpec,
    NodeSchema,
    SemWeaveConfig,
    TraversalConfig,
)
from semweave.model.graph import NodeGraph
from semweave.traversal.builder import build_graph
from semweave.mcp_server.server import (
    find_by_anchor,
    find_nodes,
    find_references,
    get_ancestors,
    get_children,
    get_node,
    get_schema,
    list_roles,
    read_node,
    read_span,
    read_surrounding_context,
)


def _make_ctx(project_root: Path, config: SemWeaveConfig) -> MagicMock:
    """Create a mock context with real graph data."""
    graph = build_graph(project_root, config)
    ctx = MagicMock()
    ctx.lifespan_context = {
        "graph": graph,
        "config": config,
        "project_root": project_root,
    }
    return ctx


class TestDiscoveryTools:
    def test_get_schema(self, sample_project):
        root, config = sample_project
        ctx = _make_ctx(root, config)
        result = get_schema(ctx)
        assert result["annotation_prefix"] == "mcp:"
        assert "section" in result["roles"]
        assert len(result["comment_styles"]) == 1

    def test_list_roles(self, sample_project):
        root, config = sample_project
        ctx = _make_ctx(root, config)
        result = list_roles(ctx)
        assert "section" in result
        assert "definition" in result

    def test_find_nodes_all(self, sample_project):
        root, config = sample_project
        ctx = _make_ctx(root, config)
        result = find_nodes(ctx)
        assert len(result) == 3  # intro, methods, algo

    def test_find_nodes_by_role(self, sample_project):
        root, config = sample_project
        ctx = _make_ctx(root, config)
        result = find_nodes(ctx, role="section")
        assert len(result) == 2  # intro, methods

    def test_find_nodes_by_name(self, sample_project):
        root, config = sample_project
        ctx = _make_ctx(root, config)
        result = find_nodes(ctx, name="intro")
        assert len(result) == 1
        assert result[0]["name"] == "intro"

    def test_get_node(self, sample_project):
        root, config = sample_project
        ctx = _make_ctx(root, config)
        nodes = find_nodes(ctx)
        handle = nodes[0]["id"]
        result = get_node(ctx, handle)
        assert "error" not in result
        assert result["id"] == handle

    def test_get_node_not_found(self, sample_project):
        root, config = sample_project
        ctx = _make_ctx(root, config)
        result = get_node(ctx, "nonexistent")
        assert "error" in result

    def test_get_children(self, sample_project):
        root, config = sample_project
        ctx = _make_ctx(root, config)
        # Find methods node (has algo as child)
        methods_nodes = find_nodes(ctx, name="methods")
        assert len(methods_nodes) == 1
        children = get_children(ctx, methods_nodes[0]["id"])
        assert len(children) == 1
        assert children[0]["name"] == "algo"

    def test_get_ancestors(self, sample_project):
        root, config = sample_project
        ctx = _make_ctx(root, config)
        # Find algo node (child of methods)
        algo_nodes = find_nodes(ctx, name="algo")
        assert len(algo_nodes) == 1
        ancestors = get_ancestors(ctx, algo_nodes[0]["id"])
        assert len(ancestors) == 1
        assert ancestors[0]["name"] == "methods"

    def test_find_by_anchor(self, sample_project):
        root, config = sample_project
        ctx = _make_ctx(root, config)
        result = find_by_anchor(ctx, "sec:intro")
        assert "error" not in result
        assert result["name"] == "intro"

    def test_find_by_anchor_not_found(self, sample_project):
        root, config = sample_project
        ctx = _make_ctx(root, config)
        result = find_by_anchor(ctx, "nonexistent")
        assert "error" in result

    def test_find_references(self, sample_project):
        root, config = sample_project
        ctx = _make_ctx(root, config)
        # algo node content references sec:intro
        result = find_references(ctx, "sec:intro")
        assert len(result) >= 1
        names = [r["name"] for r in result]
        assert "algo" in names


class TestContentTools:
    def test_read_node(self, sample_project):
        root, config = sample_project
        ctx = _make_ctx(root, config)
        intro = find_by_anchor(ctx, "sec:intro")
        result = read_node(ctx, intro["id"])
        assert "error" not in result
        assert "Introduction" in result["content"]
        # Should not contain annotation comments
        assert "mcp:" not in result["content"]

    def test_read_node_not_found(self, sample_project):
        root, config = sample_project
        ctx = _make_ctx(root, config)
        result = read_node(ctx, "nonexistent")
        assert "error" in result

    def test_read_span(self, sample_project):
        root, config = sample_project
        ctx = _make_ctx(root, config)
        intro = find_by_anchor(ctx, "sec:intro")
        result = read_span(ctx, intro["id"], start_offset=0, end_offset=1)
        assert "error" not in result
        assert result["start_offset"] == 0
        assert result["end_offset"] == 1

    def test_read_surrounding_context(self, sample_project):
        root, config = sample_project
        ctx = _make_ctx(root, config)
        intro = find_by_anchor(ctx, "sec:intro")
        result = read_surrounding_context(ctx, intro["id"], lines_before=2, lines_after=2)
        assert "error" not in result
        assert "before" in result
        assert "content" in result
        assert "after" in result
        assert "mcp:" not in result["content"]

    def test_no_annotation_leakage(self, sample_project):
        root, config = sample_project
        ctx = _make_ctx(root, config)
        # Read the methods node which has inner annotations
        methods = find_by_anchor(ctx, "sec:methods")
        result = read_node(ctx, methods["id"])
        # The content should not contain any mcp: annotations
        assert "mcp:" not in result["content"]
