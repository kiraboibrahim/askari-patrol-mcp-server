# Askari Patrol MCP Server

Small utility library and MCP server wrapper for interacting with the Askari Patrol GuardTour API.

- Core client implementation: [`api.AskariPatrolClient`](src/api.py)
- Data shapes and response schemas: [`schemas`](src/schemas.py)
- Minimal entrypoint: [`main.main`](src/main.py)
- MCP server scaffolding: [`server.mcp`](src/server.py)

Requirements
- Python >= 3.12 (see [.python-version](.python-version))
- Dependencies listed in [pyproject.toml](pyproject.toml)

Installation

1. Create and activate a virtual environment (recommended):
```python
python -m venv .venv
source .venv/bin/activate
