# Askari Patrol MCP Server

Small utility and MCP server wrapper for interacting with the Askari Patrol / GuardTour API.
Contains a lightweight HTTP client and an MCP (Multi-Channel Processor) server scaffold to expose tooling and formatters (including WhatsApp formatter examples).

## Features

- HTTP client utilities for the Askari Patrol API
- Formatting helpers for messaging channels (client/formatters/)
- Minimal MCP server scaffold to expose tools and workflows (server/mcp.py)
- Unit tests and basic developer tooling

## Installation

```bash
uv sync
```

## Usage

```bash
uv run python -m askari_patrol_server.server
```

## Development

```bash
# Run tests
uv run pytest

# Format code
uv run ruff format .

# Lint code
uv run ruff check .
```
