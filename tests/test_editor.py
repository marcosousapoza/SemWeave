"""Tests for structure-aware write operations."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from semweave.config.schema import (
    CommentStyle,
    FieldSpec,
    NodeSchema,
    SemWeaveConfig,
)
from semweave.traversal.builder import build_graph
from semweave.mcp_server.server import (
    delete_node,
    find_by_anchor,
    find_nodes,
    insert_after,
    insert_before,
    read_node,
    replace_node,
)


def _config() -> SemWeaveConfig:
    return SemWeaveConfig(
        comment_styles=[CommentStyle(prefix="%")],
        node_schema=NodeSchema(
            roles=["section", "definition", "example"],
            fields=[FieldSpec(name="role", required=True)],
        ),
    )


def _make_project(tmp_path: Path) -> tuple[Path, SemWeaveConfig]:
    config = _config()
    (tmp_path / "doc.tex").write_text(
        "\\documentclass{article}\n"
        "% mcp: begin region role=section name=first anchors=[sec:first]\n"
        "First section content.\n"
        "% mcp: end\n"
        "% mcp: begin region role=section name=second anchors=[sec:second]\n"
        "Second section content.\n"
        "% mcp: begin region role=definition name=inner anchors=[def:inner]\n"
        "Inner definition.\n"
        "% mcp: end\n"
        "% mcp: end\n"
        "\\end{document}\n"
    )
    return tmp_path, config


def _make_ctx(root: Path, config: SemWeaveConfig) -> MagicMock:
    graph = build_graph(root, config)
    ctx = MagicMock()
    ctx.lifespan_context = {
        "graph": graph,
        "config": config,
        "project_root": root,
    }
    return ctx


class TestReplaceNode:
    def test_replace_content(self, tmp_path):
        root, config = _make_project(tmp_path)
        ctx = _make_ctx(root, config)

        node = find_by_anchor(ctx, "sec:first")
        result = replace_node(ctx, node["id"], "Replaced content.\n")
        assert result.get("success") is True

        # Verify file content
        text = (root / "doc.tex").read_text()
        assert "Replaced content." in text
        assert "First section content." not in text
        # Annotations should still be there
        assert "% mcp: begin region role=section name=first" in text
        assert "% mcp: end" in text

    def test_replace_preserves_siblings(self, tmp_path):
        root, config = _make_project(tmp_path)
        ctx = _make_ctx(root, config)

        node = find_by_anchor(ctx, "sec:first")
        replace_node(ctx, node["id"], "New first.\n")

        text = (root / "doc.tex").read_text()
        assert "Second section content." in text
        assert "Inner definition." in text

    def test_replace_nonexistent(self, tmp_path):
        root, config = _make_project(tmp_path)
        ctx = _make_ctx(root, config)
        result = replace_node(ctx, "nonexistent", "content")
        assert "error" in result

    def test_graph_rebuilt_after_replace(self, tmp_path):
        root, config = _make_project(tmp_path)
        ctx = _make_ctx(root, config)

        node = find_by_anchor(ctx, "sec:first")
        replace_node(ctx, node["id"], "New content.\n")

        # Graph should be rebuilt
        new_graph = ctx.lifespan_context["graph"]
        first = new_graph.find_by_anchor("sec:first")
        assert first is not None


class TestInsertBefore:
    def test_insert_before(self, tmp_path):
        root, config = _make_project(tmp_path)
        ctx = _make_ctx(root, config)

        node = find_by_anchor(ctx, "sec:second")
        result = insert_before(ctx, node["id"], "% Inserted before second\n")
        assert result.get("success") is True

        text = (root / "doc.tex").read_text()
        lines = text.splitlines()
        # Find the inserted line
        idx = next(i for i, l in enumerate(lines) if "Inserted before second" in l)
        # Next line should be the begin annotation of second
        assert "begin region role=section name=second" in lines[idx + 1]

    def test_insert_before_nonexistent(self, tmp_path):
        root, config = _make_project(tmp_path)
        ctx = _make_ctx(root, config)
        result = insert_before(ctx, "nonexistent", "content")
        assert "error" in result


class TestInsertAfter:
    def test_insert_after(self, tmp_path):
        root, config = _make_project(tmp_path)
        ctx = _make_ctx(root, config)

        node = find_by_anchor(ctx, "sec:first")
        result = insert_after(ctx, node["id"], "% Inserted after first\n")
        assert result.get("success") is True

        text = (root / "doc.tex").read_text()
        lines = text.splitlines()
        # Find the inserted line
        idx = next(i for i, l in enumerate(lines) if "Inserted after first" in l)
        # Previous line should be the end annotation of first
        assert "% mcp: end" in lines[idx - 1]


class TestDeleteNode:
    def test_delete_leaf(self, tmp_path):
        root, config = _make_project(tmp_path)
        ctx = _make_ctx(root, config)

        node = find_by_anchor(ctx, "sec:first")
        result = delete_node(ctx, node["id"])
        assert result.get("success") is True

        text = (root / "doc.tex").read_text()
        assert "First section content." not in text
        assert "sec:first" not in text
        # Second should still be there
        assert "Second section content." in text

    def test_delete_rebuilds_graph(self, tmp_path):
        root, config = _make_project(tmp_path)
        ctx = _make_ctx(root, config)

        node = find_by_anchor(ctx, "sec:first")
        delete_node(ctx, node["id"])

        new_graph = ctx.lifespan_context["graph"]
        assert new_graph.find_by_anchor("sec:first") is None
        assert new_graph.find_by_anchor("sec:second") is not None

    def test_delete_parent_with_children(self, tmp_path):
        root, config = _make_project(tmp_path)
        ctx = _make_ctx(root, config)

        # Delete the second section which has inner definition
        node = find_by_anchor(ctx, "sec:second")
        result = delete_node(ctx, node["id"])
        assert result.get("success") is True

        text = (root / "doc.tex").read_text()
        assert "Second section content." not in text
        assert "Inner definition." not in text

    def test_delete_nonexistent(self, tmp_path):
        root, config = _make_project(tmp_path)
        ctx = _make_ctx(root, config)
        result = delete_node(ctx, "nonexistent")
        assert "error" in result
