"""Tests for file scanning and graph building."""

from pathlib import Path

import pytest

from semweave.config.schema import (
    CommentStyle,
    FieldSpec,
    NodeSchema,
    SemWeaveConfig,
    TraversalConfig,
)
from semweave.traversal.scanner import scan_project
from semweave.traversal.builder import build_graph


FIXTURES = Path(__file__).parent / "fixtures"


def test_config() -> SemWeaveConfig:
    return SemWeaveConfig(
        comment_styles=[
            CommentStyle(prefix="%"),
            CommentStyle(prefix="<!--", suffix="-->"),
        ],
        node_schema=NodeSchema(
            roles=["section", "definition", "example", "code", "region"],
            fields=[FieldSpec(name="role", required=True)],
        ),
    )


class TestScanner:
    def test_scan_all(self, tmp_path: Path):
        (tmp_path / "a.tex").write_text("hello")
        (tmp_path / "b.md").write_text("world")
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "c.txt").write_text("nested")

        config = TraversalConfig()
        files = scan_project(tmp_path, config)
        names = [f.name for f in files]
        assert "a.tex" in names
        assert "b.md" in names
        assert "c.txt" in names

    def test_extension_filter(self, tmp_path: Path):
        (tmp_path / "a.tex").write_text("hello")
        (tmp_path / "b.md").write_text("world")

        config = TraversalConfig(extensions=[".tex"])
        files = scan_project(tmp_path, config)
        assert len(files) == 1
        assert files[0].name == "a.tex"

    def test_exclude_pattern(self, tmp_path: Path):
        (tmp_path / "a.tex").write_text("hello")
        sub = tmp_path / "build"
        sub.mkdir()
        (sub / "b.tex").write_text("built")

        config = TraversalConfig(exclude=["build/*"])
        files = scan_project(tmp_path, config)
        names = [f.name for f in files]
        assert "a.tex" in names
        assert "b.tex" not in names

    def test_skips_git_dir(self, tmp_path: Path):
        (tmp_path / "a.tex").write_text("hello")
        git = tmp_path / ".git"
        git.mkdir()
        (git / "config").write_text("gitconfig")

        config = TraversalConfig()
        files = scan_project(tmp_path, config)
        assert all(".git" not in str(f) for f in files)


class TestBuildGraph:
    def test_latex_fixture(self):
        config = test_config()
        config.traversal = TraversalConfig(extensions=[".tex"])
        graph = build_graph(FIXTURES / "latex", config)

        # Should have: introduction, methods, algorithm, example1, conclusion
        assert len(graph.nodes) == 5

        # Check anchor lookup
        intro = graph.find_by_anchor("sec:intro")
        assert intro is not None
        assert intro.name == "introduction"

        algo = graph.find_by_anchor("def:algo")
        assert algo is not None
        assert algo.name == "algorithm"

    def test_markdown_fixture(self):
        config = test_config()
        config.traversal = TraversalConfig(extensions=[".md"])
        graph = build_graph(FIXTURES / "markdown", config)

        # Should have: overview, key-concepts, usage
        assert len(graph.nodes) == 3

        overview = graph.find_by_anchor("sec:overview")
        assert overview is not None

    def test_html_fixture(self):
        config = test_config()
        config.traversal = TraversalConfig(extensions=[".html"])
        graph = build_graph(FIXTURES / "html", config)

        # Should have: header, main, example
        assert len(graph.nodes) == 3

    def test_nesting_relationships(self):
        config = test_config()
        config.traversal = TraversalConfig(extensions=[".tex"])
        graph = build_graph(FIXTURES / "latex", config)

        methods = graph.find_by_anchor("sec:methods")
        assert methods is not None
        assert len(methods.children_ids) == 2

        algo = graph.find_by_anchor("def:algo")
        assert algo is not None
        assert algo.parent_id == methods.id

    def test_ancestors(self):
        config = test_config()
        config.traversal = TraversalConfig(extensions=[".tex"])
        graph = build_graph(FIXTURES / "latex", config)

        algo = graph.find_by_anchor("def:algo")
        assert algo is not None
        ancestors = graph.get_ancestors(algo.id)
        assert len(ancestors) == 1  # methods is the parent
        assert ancestors[0].name == "methods"

    def test_root_nodes(self):
        config = test_config()
        config.traversal = TraversalConfig(extensions=[".tex"])
        graph = build_graph(FIXTURES / "latex", config)

        roots = graph.get_root_nodes()
        # intro, methods, conclusion are roots
        assert len(roots) == 3

    def test_role_index(self):
        config = test_config()
        config.traversal = TraversalConfig(extensions=[".tex"])
        graph = build_graph(FIXTURES / "latex", config)

        sections = graph.find_nodes(role="section")
        assert len(sections) == 3  # intro, methods, conclusion

        definitions = graph.find_nodes(role="definition")
        assert len(definitions) == 1

    def test_preview_generated(self):
        config = test_config()
        config.traversal = TraversalConfig(extensions=[".tex"])
        graph = build_graph(FIXTURES / "latex", config)

        intro = graph.find_by_anchor("sec:intro")
        assert intro is not None
        assert len(intro.preview) > 0

    def test_node_id_deterministic(self):
        config = test_config()
        config.traversal = TraversalConfig(extensions=[".tex"])

        graph1 = build_graph(FIXTURES / "latex", config)
        graph2 = build_graph(FIXTURES / "latex", config)

        for nid in graph1.nodes:
            assert nid in graph2.nodes
