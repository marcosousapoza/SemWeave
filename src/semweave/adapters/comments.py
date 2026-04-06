"""Comment style adapter for detecting and stripping annotation comments."""

from __future__ import annotations

from semweave.config.schema import CommentStyle


class CommentAdapter:
    """Detects and extracts annotation content from comment lines.

    Supports both prefix-only comments (e.g. `%`, `//`, `#`) and
    prefix+suffix comments (e.g. `<!-- -->`).
    """

    def __init__(self, styles: list[CommentStyle], annotation_prefix: str) -> None:
        self.styles = styles
        self.annotation_prefix = annotation_prefix

    def extract_annotation(self, line: str) -> str | None:
        """Extract the annotation body from a comment line.

        Returns the content after the annotation prefix, or None if the line
        is not an annotation comment.

        Example:
            "% mcp: begin section name=intro" -> "begin section name=intro"
            "<!-- mcp: begin section name=intro -->" -> "begin section name=intro"
            "regular text" -> None
        """
        stripped = line.strip()
        for style in self.styles:
            content = self._try_extract(stripped, style)
            if content is not None:
                return content
        return None

    def _try_extract(self, stripped: str, style: CommentStyle) -> str | None:
        """Try to extract annotation content using a specific comment style."""
        if not stripped.startswith(style.prefix):
            return None

        # Remove prefix
        inner = stripped[len(style.prefix) :].strip()

        # Remove suffix if present
        if style.suffix is not None:
            if not stripped.endswith(style.suffix):
                return None
            inner = inner[: -len(style.suffix)].strip()

        # Check for annotation prefix
        if not inner.startswith(self.annotation_prefix):
            return None

        # Return content after annotation prefix
        return inner[len(self.annotation_prefix) :].strip()

    def is_annotation(self, line: str) -> bool:
        """Check if a line is an annotation comment."""
        return self.extract_annotation(line) is not None

    def strip_annotations(self, lines: list[str]) -> list[str]:
        """Return lines with annotation comment lines removed."""
        return [line for line in lines if not self.is_annotation(line)]
