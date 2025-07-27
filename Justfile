set shell := ["bash", "-cuexa"]

# Variables
IMAGE_NAME := "diary-app"
CONTAINER_NAME := "diary-container"

# Default target: setup environment
default: setup

# Setup: Install dependencies using uv
setup:
  @echo "Setting up development environment..."
  uv sync
  @echo "Setup complete!"

# Development server with hot reload
dev:
  @echo "Starting development server..."
  uv run uvicorn src.backend.web.rest.main:app --reload --host 0.0.0.0 --port 8000

# Production server
run:
  @echo "Starting production server..."
  uv run uvicorn src.backend.web.rest.main:app --host 0.0.0.0 --port 8000

# API server (alias for dev)
api-server: dev

# Run all tests
test:
  @echo "Running tests..."
  uv run pytest

# Test MCP server specifically
mcp-test:
  @echo "Testing MCP server..."
  uv run python src/backend/mcp/test_server.py

# Test Booking MCP server
booking-test:
  @echo "Testing Booking MCP server..."
  uv run python src/backend/mcp/test_booking_server.py

# Run MCP server standalone
mcp-server:
  @echo "Starting MCP server..."
  uv run python src/backend/mcp/run_server.py

# Run Booking MCP server standalone
booking-server:
  @echo "Starting Booking MCP server..."
  uv run python src/backend/mcp/booking_server.py

# Lint code
lint:
  @echo "Running linters..."
  uv run ruff check .
  uv run ruff format --check .
  @echo "Running type checker (warnings only)..."
  -uv run mypy src/ || echo "mypy found type issues (non-blocking)"

# Format code
format:
  @echo "Formatting code..."
  uv run ruff format .
  uv run ruff check --fix .

# Type checking
typecheck:
  @echo "Running type checker..."
  uv run mypy src/

# Clean up generated files and caches
clean:
  @echo "Cleaning up..."
  find . -type f -name "*.pyc" -delete
  find . -type d -name "__pycache__" -delete
  find . -type d -name "*.egg-info" -exec rm -rf {} +
  rm -rf .pytest_cache
  rm -rf .mypy_cache
  rm -rf .ruff_cache
  rm -rf dist/
  rm -rf build/
  rm -rf data/
  rm -rf test_data/
  @echo "Cleanup complete!"

# Build Docker image
docker-build:
  @echo "Building Docker image: {{IMAGE_NAME}}"
  docker build -t {{IMAGE_NAME}} .
  @echo "Docker image built successfully!"

# Run Docker container (single container)
docker-run: docker-build
  @echo "Stopping existing container if running..."
  docker stop {{CONTAINER_NAME}} 2>/dev/null || true
  docker rm {{CONTAINER_NAME}} 2>/dev/null || true
  @echo "Starting Docker container: {{CONTAINER_NAME}}"
  docker run --name {{CONTAINER_NAME}} --env-file .env -d -p 8000:8000 {{IMAGE_NAME}}
  @echo "Container started! API available at http://localhost:8000"

# Stop Docker container
docker-stop:
  @echo "Stopping Docker container: {{CONTAINER_NAME}}"
  docker stop {{CONTAINER_NAME}} || true

# View Docker container logs
docker-logs:
  @echo "Showing logs for container: {{CONTAINER_NAME}}"
  docker logs -f {{CONTAINER_NAME}}

# Clean up Docker images and containers
docker-clean:
  @echo "Cleaning up Docker resources..."
  docker stop {{CONTAINER_NAME}} 2>/dev/null || true
  docker rm {{CONTAINER_NAME}} 2>/dev/null || true
  docker rmi {{IMAGE_NAME}} 2>/dev/null || true
  @echo "Docker cleanup complete!"

# Docker Compose Commands
# =====================

# Start all services with docker-compose
compose-up:
  @echo "Starting all services with docker-compose..."
  docker-compose up -d
  @echo "Services started! API available at http://localhost:8000"

# Start services and view logs
compose-up-logs:
  @echo "Starting all services with docker-compose and showing logs..."
  docker-compose up

# Stop all services
compose-down:
  @echo "Stopping all services..."
  docker-compose down
  @echo "All services stopped!"

# Stop and remove all data
compose-down-volumes:
  @echo "Stopping all services and removing volumes..."
  docker-compose down -v
  @echo "All services stopped and data removed!"

# Rebuild and restart services
compose-rebuild:
  @echo "Rebuilding and restarting services..."
  docker-compose down
  docker-compose build --no-cache
  docker-compose up -d
  @echo "Services rebuilt and restarted!"

# View logs for all services
compose-logs:
  @echo "Showing logs for all services..."
  docker-compose logs -f

# View logs for specific service
compose-logs-app:
  @echo "Showing logs for diary-app..."
  docker-compose logs -f diary-app

# View logs for database
compose-logs-db:
  @echo "Showing logs for database..."
  docker-compose logs -f postgres

# Show status of all services
compose-status:
  @echo "Status of all services:"
  docker-compose ps

# Execute shell in the app container
compose-shell:
  @echo "Opening shell in diary-app container..."
  docker-compose exec diary-app /bin/bash

# Execute shell in the database container
compose-shell-db:
  @echo "Opening shell in postgres container..."
  docker-compose exec postgres psql -U diary_user -d diary_db

# Run database migrations (when implemented)
compose-migrate:
  @echo "Running database migrations..."
  docker-compose exec diary-app uv run alembic upgrade head

# Start with production profile (includes nginx)
compose-prod:
  @echo "Starting production environment with nginx..."
  docker-compose --profile production up -d
  @echo "Production environment started!"
  @echo "App available at http://localhost (nginx proxy)"
  @echo "Direct app access at http://localhost:8000"

# Pull latest images
compose-pull:
  @echo "Pulling latest images..."
  docker-compose pull

# Restart specific service
compose-restart-app:
  @echo "Restarting diary-app service..."
  docker-compose restart diary-app

# Create environment file from example
setup-env:
  @echo "Creating .env file from env.example..."
  @if [ ! -f .env ]; then \
    cp env.example .env; \
    echo "✓ .env file created! Please edit it with your API keys."; \
  else \
    echo "✓ .env file already exists."; \
  fi

# Install pre-commit hooks
install-hooks:
  @echo "Installing pre-commit hooks..."
  uv run pre-commit install
  @echo "Pre-commit hooks installed!"

# Update dependencies
update:
  @echo "Updating dependencies..."
  uv lock --upgrade
  uv sync
  @echo "Dependencies updated!"

# Show project information
info:
  @echo "Project: diary"
  @echo "Description: A diary application with AI integration and MCP server"
  @echo "Python version: $(uv run python --version)"
  @echo "UV version: $(uv --version)"
  @echo "Virtual environment: .venv"
  @echo ""
  @echo "Available commands:"
  just --list

# Show help
help:
  @echo "Diary Application - Development Commands"
  @echo ""
  @echo "Setup and Development:"
  @echo "  just setup        - Install dependencies"
  @echo "  just setup-env    - Create .env file from example"
  @echo "  just dev          - Start development server"
  @echo "  just run          - Start production server"
  @echo ""
  @echo "Testing:"
  @echo "  just test         - Run all tests"
  @echo "  just mcp-test     - Test MCP server"
  @echo "  just booking-test - Test Booking MCP server"
  @echo ""
  @echo "Code Quality:"
  @echo "  just lint         - Run linters"
  @echo "  just format       - Format code"
  @echo "  just typecheck    - Run type checker"
  @echo ""
  @echo "MCP Servers:"
  @echo "  just mcp-server     - Run original MCP server"
  @echo "  just booking-server - Run Booking MCP server"
  @echo ""
  @echo "Docker (Single Container):"
  @echo "  just docker-build - Build Docker image"
  @echo "  just docker-run   - Run in Docker"
  @echo "  just docker-stop  - Stop Docker container"
  @echo "  just docker-logs  - View Docker logs"
  @echo "  just docker-clean - Clean Docker resources"
  @echo ""
  @echo "Docker Compose (Full Stack):"
  @echo "  just compose-up   - Start all services"
  @echo "  just compose-up-logs - Start services with logs"
  @echo "  just compose-down - Stop all services"
  @echo "  just compose-down-volumes - Stop and remove data"
  @echo "  just compose-rebuild - Rebuild and restart"
  @echo "  just compose-logs - View all service logs"
  @echo "  just compose-logs-app - View app logs"
  @echo "  just compose-logs-db - View database logs"
  @echo "  just compose-status - Show service status"
  @echo "  just compose-shell - Shell into app container"
  @echo "  just compose-shell-db - Shell into database"
  @echo "  just compose-prod - Start with nginx (production)"
  @echo ""
  @echo "Maintenance:"
  @echo "  just clean        - Clean generated files"
  @echo "  just update       - Update dependencies"
  @echo "  just install-hooks- Install pre-commit hooks"
  @echo "  just info         - Show project info"
