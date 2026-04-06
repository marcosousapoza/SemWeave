"""Load and validate SemWeave configuration."""

from __future__ import annotations

import json
from pathlib import Path

from semweave.config.defaults import DEFAULT_CONFIG
from semweave.config.schema import SemWeaveConfig

CONFIG_FILENAME = "mcp.config.json"


def find_config(start: Path) -> Path | None:
    """Search for mcp.config.json starting from `start` and walking up."""
    current = start.resolve()
    while True:
        candidate = current / CONFIG_FILENAME
        if candidate.is_file():
            return candidate
        parent = current.parent
        if parent == current:
            return None
        current = parent


def load_config(project_root: Path) -> SemWeaveConfig:
    """Load configuration from mcp.config.json in the project root.

    Falls back to default configuration if no config file is found.
    """
    config_path = find_config(project_root)
    if config_path is None:
        return DEFAULT_CONFIG

    with open(config_path) as f:
        data = json.load(f)

    return SemWeaveConfig.model_validate(data)
