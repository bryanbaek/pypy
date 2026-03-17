set shell := ["bash", "-cuexa"]

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

# View logs for database
compose-logs-db:
  @echo "Showing logs for database..."
  docker-compose logs -f postgres

# Show status of all services
compose-status:
  @echo "Status of all services:"
  docker-compose ps

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
