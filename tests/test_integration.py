"""Integration tests: end-to-end flows across multiple formats."""

import json
import shutil
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from semweave.config.loader import load_config
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
    delete_node,
    find_by_anchor,
    find_nodes,
    find_references,
    get_ancestors,
    get_children,
    get_node,
    get_schema,
    insert_after,
    insert_before,
    list_roles,
    read_node,
    read_span,
    read_surrounding_context,
    replace_node,
)


EXAMPLES_DIR = Path(__file__).parent.parent / "examples"
FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _make_ctx(root: Path, config: SemWeaveConfig) -> MagicMock:
    graph = build_graph(root, config)
    ctx = MagicMock()
    ctx.lifespan_context = {
        "graph": graph,
        "config": config,
        "project_root": root,
    }
    return ctx


class TestLatexExample:
    """End-to-end tests against the LaTeX example project."""

    def test_full_flow(self):
        config = load_config(EXAMPLES_DIR / "latex")
        ctx = _make_ctx(EXAMPLES_DIR / "latex", config)

        # Discovery
        schema = get_schema(ctx)
        assert "theorem" in schema["roles"]

        roles = list_roles(ctx)
        assert "section" in roles

        all_nodes = find_nodes(ctx)
        assert len(all_nodes) >= 5  # intro, background, main-results + nested

        # Find by anchor
        intro = find_by_anchor(ctx, "sec:intro")
        assert intro["name"] == "introduction"

        background = find_by_anchor(ctx, "sec:background")
        assert background["name"] == "background"

        # Hierarchy
        children = get_children(ctx, background["id"])
        child_names = [c["name"] for c in children]
        assert "graph-def" in child_names
        assert "tree-def" in child_names

        # Read content (no annotations)
        content = read_node(ctx, intro["id"])
        assert "mcp:" not in content["content"]
        assert "Introduction" in content["content"] or "paper demonstrates" in content["content"]

        # References: tree-def references def:graph
        refs = find_references(ctx, "def:graph")
        ref_names = [r["name"] for r in refs]
        assert "tree-def" in ref_names

    def test_ancestors(self):
        config = load_config(EXAMPLES_DIR / "latex")
        ctx = _make_ctx(EXAMPLES_DIR / "latex", config)

        thm = find_by_anchor(ctx, "thm:main")
        assert thm is not None
        ancestors = get_ancestors(ctx, thm["id"])
        ancestor_names = [a["name"] for a in ancestors]
        assert "main-results" in ancestor_names


class TestMarkdownExample:
    """End-to-end tests against the Markdown example project."""

    def test_full_flow(self):
        config = load_config(EXAMPLES_DIR / "markdown")
        ctx = _make_ctx(EXAMPLES_DIR / "markdown", config)

        all_nodes = find_nodes(ctx)
        assert len(all_nodes) >= 5

        # Nested structure
        start = find_by_anchor(ctx, "sec:start")
        assert start is not None
        children = get_children(ctx, start["id"])
        assert len(children) >= 2  # prerequisites, installation

        # Content reading
        content = read_node(ctx, start["id"])
        assert "mcp:" not in content["content"]

    def test_cross_references(self):
        config = load_config(EXAMPLES_DIR / "markdown")
        ctx = _make_ctx(EXAMPLES_DIR / "markdown", config)

        # Configuration section references sec:start
        refs = find_references(ctx, "sec:start")
        ref_names = [r["name"] for r in refs]
        assert "configuration" in ref_names


class TestHtmlExample:
    """End-to-end tests against the HTML example project."""

    def test_full_flow(self):
        config = load_config(EXAMPLES_DIR / "html")
        ctx = _make_ctx(EXAMPLES_DIR / "html", config)

        all_nodes = find_nodes(ctx)
        assert len(all_nodes) >= 4

        header = find_by_anchor(ctx, "sec:header")
        assert header is not None

        api = find_by_anchor(ctx, "sec:api")
        children = get_children(ctx, api["id"])
        assert len(children) == 2  # find-nodes, read-node definitions


class TestMultiFormatFixtures:
    """Tests across the test fixtures directory."""

    def test_latex_fixtures(self):
        config = SemWeaveConfig(
            comment_styles=[CommentStyle(prefix="%")],
            node_schema=NodeSchema(
                roles=["section", "definition", "example", "region"],
                fields=[FieldSpec(name="role", required=True)],
            ),
            traversal=TraversalConfig(extensions=[".tex"]),
        )
        graph = build_graph(FIXTURES_DIR / "latex", config)
        assert len(graph.nodes) == 5

    def test_markdown_fixtures(self):
        config = SemWeaveConfig(
            comment_styles=[CommentStyle(prefix="<!--", suffix="-->")],
            node_schema=NodeSchema(
                roles=["section", "definition", "example", "region"],
                fields=[FieldSpec(name="role", required=True)],
            ),
            traversal=TraversalConfig(extensions=[".md"]),
        )
        graph = build_graph(FIXTURES_DIR / "markdown", config)
        assert len(graph.nodes) == 3

    def test_html_fixtures(self):
        config = SemWeaveConfig(
            comment_styles=[CommentStyle(prefix="<!--", suffix="-->")],
            node_schema=NodeSchema(
                roles=["section", "definition", "example", "code", "region"],
                fields=[FieldSpec(name="role", required=True)],
            ),
            traversal=TraversalConfig(extensions=[".html"]),
        )
        graph = build_graph(FIXTURES_DIR / "html", config)
        assert len(graph.nodes) == 3


class TestMalformedAnnotations:
    """Tests for handling malformed annotations gracefully."""

    def test_bad_nesting_still_builds(self):
        config = SemWeaveConfig(
            comment_styles=[CommentStyle(prefix="%")],
            node_schema=NodeSchema(
                roles=["section", "region"],
                fields=[FieldSpec(name="role", required=True)],
            ),
            traversal=TraversalConfig(extensions=[".tex"]),
        )
        # Should not raise - malformed files are handled gracefully
        graph = build_graph(FIXTURES_DIR / "malformed", config)
        # May produce partial results but should not crash
        assert isinstance(graph, NodeGraph)


class TestWriteIntegration:
    """Integration tests for write operations with real files."""

    def test_edit_cycle(self, tmp_path):
        """Full cycle: build -> read -> edit -> rebuild -> verify."""
        config = SemWeaveConfig(
            comment_styles=[CommentStyle(prefix="%")],
            node_schema=NodeSchema(
                roles=["section", "definition"],
                fields=[FieldSpec(name="role", required=True)],
            ),
        )

        (tmp_path / "doc.tex").write_text(
            "\\title{Test}\n"
            "% mcp: begin region role=section name=alpha anchors=[sec:alpha]\n"
            "Alpha content.\n"
            "% mcp: end\n"
            "% mcp: begin region role=section name=beta anchors=[sec:beta]\n"
            "Beta content.\n"
            "% mcp: end\n"
        )

        ctx = _make_ctx(tmp_path, config)

        # Read original
        alpha = find_by_anchor(ctx, "sec:alpha")
        content = read_node(ctx, alpha["id"])
        assert "Alpha content" in content["content"]

        # Replace
        result = replace_node(ctx, alpha["id"], "New alpha content.\n")
        assert result.get("success") is True

        # Re-read via updated graph
        ctx2 = _make_ctx(tmp_path, config)
        alpha2 = find_by_anchor(ctx2, "sec:alpha")
        content2 = read_node(ctx2, alpha2["id"])
        assert "New alpha content" in content2["content"]
        assert "Alpha content." not in content2["content"]

        # Beta should be unchanged
        beta = find_by_anchor(ctx2, "sec:beta")
        beta_content = read_node(ctx2, beta["id"])
        assert "Beta content" in beta_content["content"]

    def test_insert_and_delete_cycle(self, tmp_path):
        config = SemWeaveConfig(
            comment_styles=[CommentStyle(prefix="%")],
            node_schema=NodeSchema(
                roles=["section"],
                fields=[FieldSpec(name="role", required=True)],
            ),
        )

        (tmp_path / "doc.tex").write_text(
            "% mcp: begin region role=section name=only anchors=[sec:only]\n"
            "Only section.\n"
            "% mcp: end\n"
        )

        ctx = _make_ctx(tmp_path, config)
        node = find_by_anchor(ctx, "sec:only")

        # Insert before
        insert_before(ctx, node["id"], "Preamble text.\n")
        text = (tmp_path / "doc.tex").read_text()
        assert text.startswith("Preamble text.\n")

        # Insert after
        ctx2 = _make_ctx(tmp_path, config)
        node2 = find_by_anchor(ctx2, "sec:only")
        insert_after(ctx2, node2["id"], "Postamble text.\n")
        text2 = (tmp_path / "doc.tex").read_text()
        assert "Postamble text." in text2

        # Delete
        ctx3 = _make_ctx(tmp_path, config)
        node3 = find_by_anchor(ctx3, "sec:only")
        delete_node(ctx3, node3["id"])
        text3 = (tmp_path / "doc.tex").read_text()
        assert "Only section." not in text3
        assert "Preamble text." in text3
        assert "Postamble text." in text3


class TestConfigDrivenBehavior:
    """Tests that config changes alter system behavior."""

    def test_custom_prefix(self, tmp_path):
        config = SemWeaveConfig(
            comment_styles=[CommentStyle(prefix="%")],
            annotation_prefix="sw:",
            node_schema=NodeSchema(
                roles=["section"],
                fields=[FieldSpec(name="role", required=True)],
            ),
        )

        (tmp_path / "doc.tex").write_text(
            "% sw: begin region role=section name=custom\n"
            "Custom prefix content.\n"
            "% sw: end\n"
        )

        graph = build_graph(tmp_path, config)
        assert len(graph.nodes) == 1
        node = list(graph.nodes.values())[0]
        assert node.name == "custom"

    def test_custom_keywords(self, tmp_path):
        config = SemWeaveConfig(
            comment_styles=[CommentStyle(prefix="%")],
            begin_keyword="start",
            end_keyword="stop",
            node_schema=NodeSchema(
                roles=["section"],
                fields=[FieldSpec(name="role", required=True)],
            ),
        )

        (tmp_path / "doc.tex").write_text(
            "% mcp: start region role=section name=custom\n"
            "Custom keyword content.\n"
            "% mcp: stop\n"
        )

        graph = build_graph(tmp_path, config)
        assert len(graph.nodes) == 1

    def test_hide_annotations_false(self, tmp_path):
        config = SemWeaveConfig(
            comment_styles=[CommentStyle(prefix="%")],
            hide_annotations=False,
            node_schema=NodeSchema(
                roles=["section"],
                fields=[FieldSpec(name="role", required=True)],
            ),
        )

        (tmp_path / "doc.tex").write_text(
            "% mcp: begin region role=section name=visible\n"
            "Content here.\n"
            "% mcp: end\n"
        )

        ctx = _make_ctx(tmp_path, config)
        nodes = find_nodes(ctx)
        content = read_node(ctx, nodes[0]["id"])
        # With hide_annotations=False, annotations are NOT stripped
        # Content between begin/end doesn't include the annotations themselves
        # but nested annotations would be preserved
        assert "Content here" in content["content"]
