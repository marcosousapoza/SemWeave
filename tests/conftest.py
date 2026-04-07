"""Shared test fixtures for SemWeave tests."""

import json
from pathlib import Path
from unittest.mock import MagicMock

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


@pytest.fixture
def multi_project_ctx(tmp_path: Path) -> MagicMock:
    """Create a mock context with two separate projects."""
    config_data = {"comment_styles": [{"prefix": "%"}], "node_schema": {"roles": ["section"]}}

    # Project A
    root_a = tmp_path / "proj_a"
    root_a.mkdir()
    (root_a / "mcp.config.json").write_text(json.dumps(config_data))
    (root_a / "a.tex").write_text(
        "% mcp: begin region role=section name=alpha anchors=[sec:alpha]\n"
        "Alpha content\n"
        "% mcp: end\n"
    )
    config_a = SemWeaveConfig.model_validate(config_data)
    graph_a = build_graph(root_a, config_a, project_id="proj_a")

    # Project B
    root_b = tmp_path / "proj_b"
    root_b.mkdir()
    (root_b / "mcp.config.json").write_text(json.dumps(config_data))
    (root_b / "b.tex").write_text(
        "% mcp: begin region role=section name=beta anchors=[sec:beta]\n"
        "Beta content\n"
        "% mcp: end\n"
    )
    config_b = SemWeaveConfig.model_validate(config_data)
    graph_b = build_graph(root_b, config_b, project_id="proj_b")

    ctx = MagicMock()
    ctx.lifespan_context = {
        "projects": {
            "proj_a": {"graph": graph_a, "config": config_a, "project_root": root_a},
            "proj_b": {"graph": graph_b, "config": config_b, "project_root": root_b},
        },
        "default_project": "proj_a",
    }
    return ctx
