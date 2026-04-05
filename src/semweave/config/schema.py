"""Configuration schema for SemWeave projects."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CommentStyle(BaseModel):
    """Defines how comments are written in a file format."""

    prefix: str = Field(description="Comment opening token, e.g. '%', '//', '<!--'")
    suffix: str | None = Field(
        default=None, description="Comment closing token, e.g. '-->' for HTML"
    )


class FieldSpec(BaseModel):
    """Specification for a metadata field on annotation nodes."""

    name: str
    required: bool = False
    type: Literal["str", "list"] = "str"


class NodeSchema(BaseModel):
    """Defines the allowed structure for annotation nodes."""

    roles: list[str] = Field(
        description="Finite set of allowed node roles, e.g. ['section', 'definition', 'example']"
    )
    fields: list[FieldSpec] = Field(
        default_factory=list,
        description="Field specifications for node annotations",
    )
    anchor_field: str = Field(
        default="anchors",
        description="Name of the field used for anchor identifiers",
    )


class TraversalConfig(BaseModel):
    """Controls which files are scanned for annotations."""

    include: list[str] = Field(
        default_factory=lambda: ["**/*"],
        description="Glob patterns for files to include",
    )
    exclude: list[str] = Field(
        default_factory=list,
        description="Glob patterns for files to exclude",
    )
    extensions: list[str] | None = Field(
        default=None,
        description="If set, only scan files with these extensions (e.g. ['.tex', '.md'])",
    )
    root: str | None = Field(
        default=None,
        description="Optional logical root file for the project",
    )


class SemWeaveConfig(BaseModel):
    """Top-level configuration for a SemWeave project."""

    comment_styles: list[CommentStyle] = Field(
        description="Comment syntax definitions for the project's file formats"
    )
    annotation_prefix: str = Field(
        default="mcp:",
        description="Prefix that identifies SemWeave annotations within comments",
    )
    node_schema: NodeSchema = Field(
        description="Schema defining allowed roles and fields for nodes"
    )
    traversal: TraversalConfig = Field(
        default_factory=TraversalConfig,
        description="File traversal configuration",
    )
    hide_annotations: bool = Field(
        default=True,
        description="Whether to strip annotation comments from content reads",
    )
    begin_keyword: str = Field(
        default="begin",
        description="Keyword that starts an annotated region",
    )
    end_keyword: str = Field(
        default="end",
        description="Keyword that ends an annotated region",
    )
