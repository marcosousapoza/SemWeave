# Project Guide

<!-- mcp: begin region role=section name=getting-started anchors=[sec:start] -->
## Getting Started

Welcome to the project! This guide will help you get up and running.

<!-- mcp: begin region role=note name=prerequisites anchors=[note:prereqs] -->
### Prerequisites

- Python 3.10 or later
- pip or uv package manager
- A terminal with shell access

<!-- mcp: end -->

<!-- mcp: begin region role=code name=installation anchors=[code:install] -->
### Installation

```bash
pip install semweave
```

Or install from source:

```bash
git clone https://github.com/example/project.git
cd project
pip install -e ".[dev]"
```

<!-- mcp: end -->

<!-- mcp: end -->

<!-- mcp: begin region role=section name=configuration anchors=[sec:config] -->
## Configuration

Create an `mcp.config.json` file in your project root. See the
[Getting Started](#sec:start) section for installation instructions.

<!-- mcp: begin region role=definition name=config-schema anchors=[def:config] -->
### Config Schema

The configuration file supports the following top-level keys:

- `comment_styles`: Array of comment syntax definitions
- `annotation_prefix`: The prefix for annotations (default: `mcp:`)
- `node_schema`: Defines allowed roles and fields
- `traversal`: File discovery settings

<!-- mcp: end -->

<!-- mcp: begin region role=example name=config-example anchors=[ex:config] -->
### Example Configuration

```json
{
  "comment_styles": [{"prefix": "<!--", "suffix": "-->"}],
  "node_schema": {
    "roles": ["section", "definition", "example"],
    "fields": [{"name": "role", "required": true}]
  }
}
```

<!-- mcp: end -->

<!-- mcp: end -->

<!-- mcp: begin region role=section name=usage anchors=[sec:usage] -->
## Usage

Run the MCP server:

```bash
python -m semweave
```

The server will scan your project for annotations and expose navigation
tools via the MCP protocol. See [Configuration](#sec:config) for setup.

<!-- mcp: end -->
