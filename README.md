# Askari Patrol MCP Server

Small utility and MCP server wrapper for interacting with the Askari Patrol / GuardTour API.
Contains a lightweight HTTP client and an MCP (Model Context Processor) server scaffold to expose tooling.

## Features

- HTTP client utilities for the Askari Patrol API
- Minimal MCP server scaffold to expose tools and workflows
- Unit tests and basic developer tooling

## Installation

```bash
# Install dependencies
make install
```

## Usage

```bash
# Run MCP Server
make server

# Run WhatsApp Client
make whatsapp
```

## Development

```bash
# Run tests
make test

# Format code
make format

# Lint code
make lint

# Automatically fix lint issues
make fix
```

## Running the Command Line Chat Client

```bash

# Open first terminal(tab)
make server

# Open second terminal(tab)
make chat
```
