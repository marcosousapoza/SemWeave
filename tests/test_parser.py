"""Tests for comment adapters and annotation parsing."""

import pytest

from semweave.adapters.comments import CommentAdapter
from semweave.config.schema import CommentStyle, FieldSpec, NodeSchema, SemWeaveConfig
from semweave.core.parser import (
    FileParseResult,
    parse_annotation_content,
    parse_fields,
    parse_file,
)


# -- Fixtures --

def latex_config() -> SemWeaveConfig:
    return SemWeaveConfig(
        comment_styles=[CommentStyle(prefix="%")],
        node_schema=NodeSchema(
            roles=["section", "definition", "example", "region"],
            fields=[FieldSpec(name="role", required=True)],
        ),
    )


def html_config() -> SemWeaveConfig:
    return SemWeaveConfig(
        comment_styles=[CommentStyle(prefix="<!--", suffix="-->")],
        node_schema=NodeSchema(
            roles=["section", "definition", "example", "region"],
            fields=[FieldSpec(name="role", required=True)],
        ),
    )


def multi_config() -> SemWeaveConfig:
    return SemWeaveConfig(
        comment_styles=[
            CommentStyle(prefix="%"),
            CommentStyle(prefix="<!--", suffix="-->"),
            CommentStyle(prefix="//"),
        ],
        node_schema=NodeSchema(
            roles=["section", "definition", "example", "region"],
            fields=[FieldSpec(name="role", required=True)],
        ),
    )


# -- CommentAdapter tests --

class TestCommentAdapter:
    def test_latex_annotation(self):
        adapter = CommentAdapter([CommentStyle(prefix="%")], "mcp:")
        result = adapter.extract_annotation("% mcp: begin region role=section name=intro")
        assert result == "begin region role=section name=intro"

    def test_html_annotation(self):
        adapter = CommentAdapter([CommentStyle(prefix="<!--", suffix="-->")], "mcp:")
        result = adapter.extract_annotation("<!-- mcp: begin region role=section name=intro -->")
        assert result == "begin region role=section name=intro"

    def test_slash_annotation(self):
        adapter = CommentAdapter([CommentStyle(prefix="//")], "mcp:")
        result = adapter.extract_annotation("// mcp: begin region role=section")
        assert result == "begin region role=section"

    def test_not_an_annotation(self):
        adapter = CommentAdapter([CommentStyle(prefix="%")], "mcp:")
        assert adapter.extract_annotation("% This is a regular comment") is None
        assert adapter.extract_annotation("regular text") is None

    def test_html_without_suffix(self):
        adapter = CommentAdapter([CommentStyle(prefix="<!--", suffix="-->")], "mcp:")
        assert adapter.extract_annotation("<!-- mcp: begin region") is None

    def test_is_annotation(self):
        adapter = CommentAdapter([CommentStyle(prefix="%")], "mcp:")
        assert adapter.is_annotation("% mcp: begin region role=section") is True
        assert adapter.is_annotation("% regular comment") is False
        assert adapter.is_annotation("text") is False

    def test_strip_annotations(self):
        adapter = CommentAdapter([CommentStyle(prefix="%")], "mcp:")
        lines = [
            "% mcp: begin region role=section",
            "Hello world",
            "% This is a regular comment",
            "% mcp: end",
        ]
        stripped = adapter.strip_annotations(lines)
        assert stripped == ["Hello world", "% This is a regular comment"]

    def test_end_annotation(self):
        adapter = CommentAdapter([CommentStyle(prefix="%")], "mcp:")
        result = adapter.extract_annotation("% mcp: end")
        assert result == "end"


# -- Field parsing tests --

class TestParseFields:
    def test_simple_fields(self):
        fields = parse_fields("role=section name=intro")
        assert fields == {"role": "section", "name": "intro"}

    def test_list_field(self):
        fields = parse_fields("anchors=[sec:intro,sec:overview]")
        assert fields == {"anchors": ["sec:intro", "sec:overview"]}

    def test_mixed_fields(self):
        fields = parse_fields("role=section name=intro anchors=[sec:intro]")
        assert fields == {
            "role": "section",
            "name": "intro",
            "anchors": ["sec:intro"],
        }

    def test_quoted_value(self):
        fields = parse_fields('name="my section" role=section')
        assert fields == {"name": "my section", "role": "section"}

    def test_empty(self):
        fields = parse_fields("")
        assert fields == {}

    def test_empty_list(self):
        fields = parse_fields("anchors=[]")
        assert fields == {"anchors": []}


# -- Annotation content parsing tests --

class TestParseAnnotationContent:
    def test_begin(self):
        config = latex_config()
        result = parse_annotation_content(
            "begin region role=section name=intro", 1, config
        )
        assert result is not None
        assert result.type == "begin"
        assert result.node_type == "region"
        assert result.fields == {"role": "section", "name": "intro"}

    def test_end(self):
        config = latex_config()
        result = parse_annotation_content("end", 10, config)
        assert result is not None
        assert result.type == "end"
        assert result.line_number == 10

    def test_begin_with_anchors(self):
        config = latex_config()
        result = parse_annotation_content(
            "begin region role=section anchors=[sec:intro,sec:1]", 1, config
        )
        assert result is not None
        assert result.fields["anchors"] == ["sec:intro", "sec:1"]

    def test_unrecognized(self):
        config = latex_config()
        result = parse_annotation_content("unknown stuff", 1, config)
        assert result is None


# -- File parsing tests --

class TestParseFile:
    def test_simple_latex(self):
        config = latex_config()
        lines = [
            "\\documentclass{article}",
            "% mcp: begin region role=section name=intro",
            "\\section{Introduction}",
            "Some content here.",
            "% mcp: end",
            "\\end{document}",
        ]
        result = parse_file("test.tex", lines, config)
        assert len(result.annotations) == 2
        assert result.annotations[0].type == "begin"
        assert result.annotations[0].line_number == 2
        assert result.annotations[0].fields["role"] == "section"
        assert result.annotations[1].type == "end"
        assert result.annotations[1].line_number == 5
        assert len(result.errors) == 0

    def test_html_annotations(self):
        config = html_config()
        lines = [
            "<html>",
            "<!-- mcp: begin region role=section name=header -->",
            "<h1>Title</h1>",
            "<!-- mcp: end -->",
            "</html>",
        ]
        result = parse_file("test.html", lines, config)
        assert len(result.annotations) == 2
        assert len(result.errors) == 0

    def test_nested_regions(self):
        config = latex_config()
        lines = [
            "% mcp: begin region role=section name=chapter1",
            "Chapter 1",
            "% mcp: begin region role=definition name=def1",
            "A definition",
            "% mcp: end",
            "More content",
            "% mcp: end",
        ]
        result = parse_file("test.tex", lines, config)
        assert len(result.annotations) == 4
        assert len(result.errors) == 0

    def test_unclosed_region(self):
        config = latex_config()
        lines = [
            "% mcp: begin region role=section name=intro",
            "Some content",
        ]
        result = parse_file("test.tex", lines, config)
        assert len(result.errors) == 1
        assert "unclosed" in result.errors[0]

    def test_extra_end(self):
        config = latex_config()
        lines = [
            "Some content",
            "% mcp: end",
        ]
        result = parse_file("test.tex", lines, config)
        assert len(result.errors) == 1
        assert "without matching" in result.errors[0]

    def test_unknown_role(self):
        config = latex_config()
        lines = [
            "% mcp: begin region role=unknown_role",
            "content",
            "% mcp: end",
        ]
        result = parse_file("test.tex", lines, config)
        assert any("unknown role" in e for e in result.errors)

    def test_no_annotations(self):
        config = latex_config()
        lines = ["Just regular content", "% regular comment", "more text"]
        result = parse_file("test.tex", lines, config)
        assert len(result.annotations) == 0
        assert len(result.errors) == 0
