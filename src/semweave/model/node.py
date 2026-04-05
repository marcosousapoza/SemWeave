"""Node model for the SemWeave annotation graph."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Node(BaseModel):
    """A single annotated region in a project file.

    Each node corresponds to a begin/end annotation pair and represents
    a structured region of content.
    """

    id: str = Field(description="Deterministic identifier (file:start_line)")
    role: str = Field(description="Node role from the configured set")
    name: str | None = Field(default=None, description="Optional user-defined name")
    anchors: list[str] = Field(
        default_factory=list, description="Anchor identifiers for cross-referencing"
    )
    file: str = Field(description="Relative path to the file containing this node")
    start_line: int = Field(description="1-indexed line number of the begin annotation")
    end_line: int = Field(description="1-indexed line number of the end annotation")
    content_start: int = Field(description="First line of content (after begin annotation)")
    content_end: int = Field(description="Last line of content (before end annotation)")
    parent_id: str | None = Field(default=None, description="ID of the parent node")
    children_ids: list[str] = Field(
        default_factory=list, description="IDs of direct child nodes"
    )
    metadata: dict[str, str | list[str]] = Field(
        default_factory=dict, description="Arbitrary key-value metadata from annotation"
    )
    preview: str = Field(default="", description="First ~100 characters of content")


class NodeSummary(BaseModel):
    """Lightweight node representation for discovery responses."""

    id: str
    role: str
    name: str | None = None
    anchors: list[str] = Field(default_factory=list)
    file: str
    preview: str = ""
    children_count: int = 0

    @classmethod
    def from_node(cls, node: Node) -> NodeSummary:
        return cls(
            id=node.id,
            role=node.role,
            name=node.name,
            anchors=node.anchors,
            file=node.file,
            preview=node.preview,
            children_count=len(node.children_ids),
        )
