"""Tests for the node graph."""

import pytest

from semweave.model.node import Node, NodeSummary
from semweave.model.graph import NodeGraph


def make_node(
    id: str = "test.tex:1",
    role: str = "section",
    name: str | None = "intro",
    anchors: list[str] | None = None,
    file: str = "test.tex",
    start_line: int = 1,
    end_line: int = 10,
    parent_id: str | None = None,
    children_ids: list[str] | None = None,
) -> Node:
    return Node(
        id=id,
        role=role,
        name=name,
        anchors=anchors or [],
        file=file,
        start_line=start_line,
        end_line=end_line,
        content_start=start_line + 1,
        content_end=end_line - 1,
        parent_id=parent_id,
        children_ids=children_ids or [],
        preview="Some content here...",
    )


class TestNode:
    def test_create(self):
        node = make_node()
        assert node.id == "test.tex:1"
        assert node.role == "section"

    def test_summary(self):
        node = make_node(children_ids=["child1", "child2"])
        summary = NodeSummary.from_node(node)
        assert summary.id == node.id
        assert summary.children_count == 2


class TestNodeGraph:
    def test_add_and_get(self):
        graph = NodeGraph()
        node = make_node()
        graph.add_node(node)
        assert graph.get_node("test.tex:1") == node

    def test_get_nonexistent(self):
        graph = NodeGraph()
        assert graph.get_node("nope") is None

    def test_anchor_index(self):
        graph = NodeGraph()
        node = make_node(anchors=["sec:intro", "sec:overview"])
        graph.add_node(node)
        assert graph.find_by_anchor("sec:intro") == node
        assert graph.find_by_anchor("sec:overview") == node
        assert graph.find_by_anchor("sec:missing") is None

    def test_file_index(self):
        graph = NodeGraph()
        n1 = make_node(id="a.tex:1", file="a.tex")
        n2 = make_node(id="a.tex:20", file="a.tex")
        n3 = make_node(id="b.tex:1", file="b.tex")
        graph.add_node(n1)
        graph.add_node(n2)
        graph.add_node(n3)

        results = graph.find_nodes(file="a.tex")
        assert len(results) == 2

    def test_role_index(self):
        graph = NodeGraph()
        n1 = make_node(id="a:1", role="section")
        n2 = make_node(id="a:10", role="definition")
        n3 = make_node(id="a:20", role="section")
        graph.add_node(n1)
        graph.add_node(n2)
        graph.add_node(n3)

        results = graph.find_nodes(role="section")
        assert len(results) == 2
        results = graph.find_nodes(role="definition")
        assert len(results) == 1

    def test_find_by_name(self):
        graph = NodeGraph()
        n1 = make_node(id="a:1", name="intro")
        n2 = make_node(id="a:10", name="methods")
        graph.add_node(n1)
        graph.add_node(n2)

        results = graph.find_nodes(name="intro")
        assert len(results) == 1
        assert results[0].name == "intro"

    def test_combined_filters(self):
        graph = NodeGraph()
        n1 = make_node(id="a:1", role="section", file="a.tex", name="intro")
        n2 = make_node(id="a:10", role="section", file="a.tex", name="methods")
        n3 = make_node(id="b:1", role="section", file="b.tex", name="intro")
        graph.add_node(n1)
        graph.add_node(n2)
        graph.add_node(n3)

        results = graph.find_nodes(role="section", file="a.tex", name="intro")
        assert len(results) == 1
        assert results[0].id == "a:1"

    def test_children(self):
        graph = NodeGraph()
        parent = make_node(id="p:1", children_ids=["c:2", "c:5"])
        child1 = make_node(id="c:2", parent_id="p:1")
        child2 = make_node(id="c:5", parent_id="p:1")
        graph.add_node(parent)
        graph.add_node(child1)
        graph.add_node(child2)

        children = graph.get_children("p:1")
        assert len(children) == 2

    def test_ancestors(self):
        graph = NodeGraph()
        root = make_node(id="r:1")
        mid = make_node(id="m:3", parent_id="r:1")
        leaf = make_node(id="l:5", parent_id="m:3")
        graph.add_node(root)
        graph.add_node(mid)
        graph.add_node(leaf)

        ancestors = graph.get_ancestors("l:5")
        assert len(ancestors) == 2
        assert ancestors[0].id == "m:3"
        assert ancestors[1].id == "r:1"

    def test_root_nodes(self):
        graph = NodeGraph()
        n1 = make_node(id="a:1", parent_id=None)
        n2 = make_node(id="a:5", parent_id="a:1")
        n3 = make_node(id="b:1", parent_id=None)
        graph.add_node(n1)
        graph.add_node(n2)
        graph.add_node(n3)

        roots = graph.get_root_nodes()
        assert len(roots) == 2
