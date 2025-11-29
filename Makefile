.PHONY: server whatsapp test lint format clean docker-up docker-down docker-build docker-push

PYTHONPATH := src

# Load environment variables from .env file if it exists
ifneq (,$(wildcard .env))
    include .env
    export
endif

# Run MCP server
server:
	PYTHONPATH=$(PYTHONPATH) uv run python -m askari_patrol_server.server

# Run WhatsApp client
whatsapp:
	PYTHONPATH=$(PYTHONPATH) uv run python -m askari_patrol_client.whatsapp_client

# Run chat script
chat:
	PYTHONPATH=$(PYTHONPATH) uv run python scripts/chat.py

# Run tests
test:
	uv run pytest

# Run tests with coverage
test-cov:
	uv run pytest --cov=src --cov-report=term-missing

# Lint code
lint:
	uv run ruff check src scripts

# Format code
format:
	uv run ruff format src scripts

# Fix lint issues
fix:
	uv run ruff check --fix src scripts

# Install dependencies
install:
	uv sync

# Clean up
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .ruff_cache

# Docker
docker-up:
	docker compose up --build

docker-down:
	docker compose down

docker-build:
	docker build -t harmless138/dojohub:askariagent-1.0.0 .

docker-push:
	docker push harmless138/dojohub:askariagent-1.0.0

dev:
	make -j2 server whatsapp
