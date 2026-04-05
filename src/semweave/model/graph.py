"""Node graph for indexing and traversing annotated regions."""

from __future__ import annotations

from collections import defaultdict

from semweave.model.node import Node, NodeSummary


class NodeGraph:
    """Index of all annotated nodes across a project.

    Provides lookup by ID, anchor, file, and role, as well as
    hierarchical traversal (parent/children) and graph traversal (references).
    """

    def __init__(self) -> None:
        self.nodes: dict[str, Node] = {}
        self.anchor_index: dict[str, str] = {}
        self.file_index: dict[str, list[str]] = defaultdict(list)
        self.role_index: dict[str, list[str]] = defaultdict(list)

    def add_node(self, node: Node) -> None:
        """Add a node to the graph and update all indices."""
        self.nodes[node.id] = node
        for anchor in node.anchors:
            self.anchor_index[anchor] = node.id
        self.file_index[node.file].append(node.id)
        self.role_index[node.role].append(node.id)

    def get_node(self, node_id: str) -> Node | None:
        """Get a node by its ID."""
        return self.nodes.get(node_id)

    def get_children(self, node_id: str) -> list[Node]:
        """Get direct children of a node."""
        node = self.nodes.get(node_id)
        if node is None:
            return []
        return [self.nodes[cid] for cid in node.children_ids if cid in self.nodes]

    def get_ancestors(self, node_id: str) -> list[Node]:
        """Get ancestors from node up to root (inclusive of immediate parent)."""
        ancestors = []
        current = self.nodes.get(node_id)
        if current is None:
            return []
        while current.parent_id is not None:
            parent = self.nodes.get(current.parent_id)
            if parent is None:
                break
            ancestors.append(parent)
            current = parent
        return ancestors

    def find_by_anchor(self, anchor: str) -> Node | None:
        """Find the node that owns a given anchor."""
        node_id = self.anchor_index.get(anchor)
        if node_id is None:
            return None
        return self.nodes.get(node_id)

    def find_nodes(
        self,
        role: str | None = None,
        name: str | None = None,
        file: str | None = None,
    ) -> list[Node]:
        """Find nodes matching optional filters."""
        if role is not None:
            candidates = [
                self.nodes[nid]
                for nid in self.role_index.get(role, [])
                if nid in self.nodes
            ]
        else:
            candidates = list(self.nodes.values())

        if file is not None:
            if role is None:
                candidates = [
                    self.nodes[nid]
                    for nid in self.file_index.get(file, [])
                    if nid in self.nodes
                ]
            else:
                candidates = [n for n in candidates if n.file == file]

        if name is not None:
            candidates = [n for n in candidates if n.name == name]

        return candidates

    def get_root_nodes(self) -> list[Node]:
        """Get all nodes that have no parent."""
        return [n for n in self.nodes.values() if n.parent_id is None]

    def get_summaries(self, nodes: list[Node]) -> list[NodeSummary]:
        """Convert a list of nodes to summaries."""
        return [NodeSummary.from_node(n) for n in nodes]
