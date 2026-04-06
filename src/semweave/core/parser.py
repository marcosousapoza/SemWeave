"""Annotation parser for extracting structure from file content."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field

from semweave.adapters.comments import CommentAdapter
from semweave.config.schema import SemWeaveConfig


class ParsedAnnotation(BaseModel):
    """A single parsed annotation (begin or end)."""

    type: Literal["begin", "end"]
    node_type: str | None = None  # Only present for begin annotations
    fields: dict[str, str | list[str]] = Field(default_factory=dict)
    line_number: int  # 1-indexed


class FileParseResult(BaseModel):
    """Result of parsing a single file for annotations."""

    annotations: list[ParsedAnnotation] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


# Pattern for key=value and key=[list,items]
_FIELD_PATTERN = re.compile(
    r'(\w+)=\[([^\]]*)\]|(\w+)=("(?:[^"\\]|\\.)*"|[^\s]+)'
)


def parse_fields(text: str) -> dict[str, str | list[str]]:
    """Parse key=value fields from annotation content.

    Supports:
        key=value           -> {"key": "value"}
        key=[a,b,c]         -> {"key": ["a", "b", "c"]}
        key="quoted value"  -> {"key": "quoted value"}
    """
    fields: dict[str, str | list[str]] = {}
    for match in _FIELD_PATTERN.finditer(text):
        if match.group(1) is not None:
            # key=[list,items]
            key = match.group(1)
            items = [item.strip() for item in match.group(2).split(",") if item.strip()]
            fields[key] = items
        else:
            # key=value or key="quoted"
            key = match.group(3)
            value = match.group(4)
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            fields[key] = value
    return fields


def parse_annotation_content(
    content: str, line_number: int, config: SemWeaveConfig
) -> ParsedAnnotation | None:
    """Parse the body of an annotation after the prefix has been stripped.

    Example content: "begin region role=section name=intro anchors=[sec:intro]"
    """
    parts = content.split(None, 2)  # Split into at most 3 parts
    if not parts:
        return None

    keyword = parts[0].lower()

    if keyword == config.end_keyword:
        return ParsedAnnotation(type="end", line_number=line_number)

    if keyword == config.begin_keyword:
        node_type = parts[1] if len(parts) > 1 else None
        rest = parts[2] if len(parts) > 2 else ""
        fields = parse_fields(rest)
        return ParsedAnnotation(
            type="begin",
            node_type=node_type,
            fields=fields,
            line_number=line_number,
        )

    return None


def parse_file(
    file_path: str,
    lines: list[str],
    config: SemWeaveConfig,
) -> FileParseResult:
    """Parse a file for SemWeave annotations.

    Scans each line for annotation comments, extracts begin/end markers,
    and validates proper nesting.
    """
    adapter = CommentAdapter(config.comment_styles, config.annotation_prefix)
    result = FileParseResult()
    nesting_depth = 0

    for i, line in enumerate(lines):
        line_num = i + 1  # 1-indexed
        annotation_content = adapter.extract_annotation(line)
        if annotation_content is None:
            continue

        parsed = parse_annotation_content(annotation_content, line_num, config)
        if parsed is None:
            result.errors.append(
                f"{file_path}:{line_num}: unrecognized annotation: {annotation_content}"
            )
            continue

        if parsed.type == "begin":
            nesting_depth += 1
            # Validate role if roles are configured
            role = parsed.fields.get("role")
            if role and isinstance(role, str) and config.node_schema.roles:
                if role not in config.node_schema.roles:
                    result.errors.append(
                        f"{file_path}:{line_num}: unknown role '{role}', "
                        f"allowed: {config.node_schema.roles}"
                    )
            result.annotations.append(parsed)

        elif parsed.type == "end":
            if nesting_depth <= 0:
                result.errors.append(
                    f"{file_path}:{line_num}: 'end' without matching 'begin'"
                )
            else:
                nesting_depth -= 1
            result.annotations.append(parsed)

    if nesting_depth > 0:
        result.errors.append(
            f"{file_path}: {nesting_depth} unclosed region(s) at end of file"
        )

    return result
