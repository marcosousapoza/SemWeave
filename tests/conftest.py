"""Shared test fixtures for SemWeave tests."""

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
from semweave.model.graph import NodeGraph
from semweave.traversal.builder import build_graph

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def latex_config() -> SemWeaveConfig:
    return SemWeaveConfig(
        comment_styles=[CommentStyle(prefix="%")],
        node_schema=NodeSchema(
            roles=["section", "definition", "example", "region"],
            fields=[FieldSpec(name="role", required=True)],
        ),
        traversal=TraversalConfig(extensions=[".tex"]),
    )


@pytest.fixture
def html_config() -> SemWeaveConfig:
    return SemWeaveConfig(
        comment_styles=[CommentStyle(prefix="<!--", suffix="-->")],
        node_schema=NodeSchema(
            roles=["section", "definition", "example", "code", "region"],
            fields=[FieldSpec(name="role", required=True)],
        ),
        traversal=TraversalConfig(extensions=[".html"]),
    )


@pytest.fixture
def multi_config() -> SemWeaveConfig:
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


@pytest.fixture
def latex_graph(latex_config: SemWeaveConfig) -> NodeGraph:
    return build_graph(FIXTURES_DIR / "latex", latex_config)


@pytest.fixture
def sample_project(tmp_path: Path) -> tuple[Path, SemWeaveConfig]:
    """Create a temporary project with annotated files and config."""
    config_data = {
        "comment_styles": [{"prefix": "%"}],
        "node_schema": {
            "roles": ["section", "definition", "example"],
            "fields": [{"name": "role", "required": True}],
        },
    }
    (tmp_path / "mcp.config.json").write_text(json.dumps(config_data))

    (tmp_path / "main.tex").write_text(
        "\\documentclass{article}\n"
        "% mcp: begin region role=section name=intro anchors=[sec:intro]\n"
        "\\section{Introduction}\n"
        "This is the introduction.\n"
        "% mcp: end\n"
        "% mcp: begin region role=section name=methods anchors=[sec:methods]\n"
        "\\section{Methods}\n"
        "% mcp: begin region role=definition name=algo anchors=[def:algo]\n"
        "Our algorithm is defined here.\n"
        "It references sec:intro.\n"
        "% mcp: end\n"
        "% mcp: end\n"
        "\\end{document}\n"
    )

    config = SemWeaveConfig.model_validate(config_data)
    return tmp_path, config
