"""Tests for configuration loading and validation."""

import json
from pathlib import Path

import pytest

from semweave.config.schema import (
    CommentStyle,
    FieldSpec,
    NodeSchema,
    SemWeaveConfig,
    TraversalConfig,
)
from semweave.config.loader import load_config
from semweave.config.defaults import DEFAULT_CONFIG


class TestCommentStyle:
    def test_prefix_only(self):
        style = CommentStyle(prefix="%")
        assert style.prefix == "%"
        assert style.suffix is None

    def test_prefix_and_suffix(self):
        style = CommentStyle(prefix="<!--", suffix="-->")
        assert style.prefix == "<!--"
        assert style.suffix == "-->"


class TestNodeSchema:
    def test_defaults(self):
        schema = NodeSchema(roles=["section"])
        assert schema.anchor_field == "anchors"
        assert schema.fields == []

    def test_with_fields(self):
        schema = NodeSchema(
            roles=["section", "definition"],
            fields=[
                FieldSpec(name="role", required=True),
                FieldSpec(name="anchors", type="list"),
            ],
        )
        assert len(schema.fields) == 2
        assert schema.fields[0].required is True
        assert schema.fields[1].type == "list"


class TestSemWeaveConfig:
    def test_minimal(self):
        config = SemWeaveConfig(
            comment_styles=[CommentStyle(prefix="%")],
            node_schema=NodeSchema(roles=["section"]),
        )
        assert config.annotation_prefix == "mcp:"
        assert config.begin_keyword == "begin"
        assert config.end_keyword == "end"
        assert config.hide_annotations is True

    def test_full(self):
        config = SemWeaveConfig(
            comment_styles=[
                CommentStyle(prefix="%"),
                CommentStyle(prefix="<!--", suffix="-->"),
            ],
            annotation_prefix="sw:",
            node_schema=NodeSchema(
                roles=["section", "definition", "example"],
                fields=[FieldSpec(name="role", required=True)],
                anchor_field="labels",
            ),
            traversal=TraversalConfig(
                include=["**/*.tex"],
                exclude=["build/**"],
                extensions=[".tex"],
                root="main.tex",
            ),
            hide_annotations=False,
            begin_keyword="start",
            end_keyword="stop",
        )
        assert config.annotation_prefix == "sw:"
        assert config.node_schema.anchor_field == "labels"
        assert config.traversal.root == "main.tex"
        assert config.begin_keyword == "start"

    def test_from_json(self):
        data = {
            "comment_styles": [{"prefix": "%"}],
            "node_schema": {
                "roles": ["section", "definition"],
                "fields": [{"name": "role", "required": True}],
            },
        }
        config = SemWeaveConfig.model_validate(data)
        assert len(config.comment_styles) == 1
        assert config.node_schema.roles == ["section", "definition"]


class TestLoadConfig:
    def test_loads_from_file(self, tmp_path: Path):
        config_data = {
            "comment_styles": [{"prefix": "//"}],
            "annotation_prefix": "test:",
            "node_schema": {
                "roles": ["block"],
                "fields": [],
            },
        }
        config_file = tmp_path / "mcp.config.json"
        config_file.write_text(json.dumps(config_data))

        config = load_config(tmp_path)
        assert config.annotation_prefix == "test:"
        assert config.comment_styles[0].prefix == "//"

    def test_falls_back_to_default(self, tmp_path: Path):
        config = load_config(tmp_path)
        assert config == DEFAULT_CONFIG

    def test_default_config_valid(self):
        assert len(DEFAULT_CONFIG.comment_styles) > 0
        assert len(DEFAULT_CONFIG.node_schema.roles) > 0
