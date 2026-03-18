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

IMAGE_NAME := ghcr.io/kiraboibrahim/askari-patrol-mcp-server

docker-build:
	docker build -t $(IMAGE_NAME):latest .

docker-push:
	docker push $(IMAGE_NAME):latest

dev:
	make -j2 server whatsapp

# Deployment
# Usage: make deploy [vps_ip=...] [vps_user=legitsystems]
deploy: docker-build docker-push
	ssh $(vps_user)@$(vps_ip) "cd ~/docker-apps/askariagent && git pull origin main && docker compose -f docker-compose.prod.yml pull && docker compose -f docker-compose.prod.yml up -d"

# Dozzle User Management
# Usage: make dozzle-user user=admin pass=password [email=...] [name=...]
dozzle-user:
	PYTHONPATH=$(PYTHONPATH) uv run python scripts/manage_dozzle.py "$(user)" "$(pass)" "$(email)" "$(name)"
