# Business Booking & Ecommerce Platform

A business booking and ecommerce platform with AI integration capabilities for appointment scheduling, product management, and order tracking.

## Overview

### 1. Core
The core directory contains fundamental application code:

- **Configuration**: Settings, constants, and configuration parameters used throughout the application.
- **Utilities**: Helper functions, decorators, middleware, and other utility classes or functions.
- **Custom Exceptions**: Custom exception classes that are used throughout the application.

### 2. Routes
The routes directory defines HTTP routes (endpoints) for the FastAPI application:

- **Chat Routes**: Endpoints for AI chat functionality with various models (OpenAI, Google, Groq).

### 3. Services
The services directory contains business logic:

- **Database Operations**: CRUD operations and other database-related logic.
- **AI Services**: Integration with OpenAI, Google Gemini, and Groq AI models.

## Setup

### Install dependencies
```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project dependencies
uv sync
```

## How to Run

This project uses [Just](https://github.com/casey/just) as a command runner. Just provides a convenient way to run common development tasks.

### Quick Start
```bash
# Setup the project
just setup

# Start development server
just dev

# Run tests
just test
```

### Available Commands

#### Setup and Development
```bash
just setup        # Install dependencies
just dev          # Start development server with hot reload
just run          # Start production server
```

#### Testing
```bash
just test         # Run all tests
```

#### Code Quality
```bash
just lint         # Run linters
just format       # Format code with ruff
just typecheck    # Run mypy type checker
```

#### Docker (Single Container)
```bash
just docker-build # Build Docker image
just docker-run   # Run in Docker container
just docker-stop  # Stop Docker container
just docker-logs  # View Docker container logs
just docker-clean # Clean up Docker resources
```

#### Docker Compose (Full Stack)
```bash
just setup-env    # Create .env file from example
just compose-up   # Start all services (app, database, redis, chromadb)
just compose-down # Stop all services
just compose-logs # View logs from all services
just compose-status # Show status of all services
```

#### Maintenance
```bash
just clean        # Clean generated files and caches
just update       # Update dependencies
just install-hooks# Install pre-commit hooks
just info         # Show project information
just help         # Show detailed help
```

### Manual Commands (if you prefer not to use Just)

#### Main API Server
```bash
uv run uvicorn src.backend.web.rest.main:app --reload
```


#### Run Tests
```bash
uv run pytest
```

## Features

- **AI Integration**: Support for OpenAI GPT-4o, Google Gemini Pro/Lite, and Groq models
- **RESTful API**: FastAPI-based REST API with automatic documentation
- **Async Support**: Full async/await support for better performance
- **Type Safety**: Comprehensive type hints and validation with Pydantic
- **Database Support**: PostgreSQL with business schema and indexing
- **Caching**: Redis for session management and caching
- **Vector Storage**: ChromaDB for embeddings and semantic search
- **Containerization**: Full Docker Compose setup for easy deployment

## Docker Compose Setup

The application includes a comprehensive Docker Compose configuration with the following services:

### Services Included

- **booking-app**: Main FastAPI application for business operations
- **postgres**: PostgreSQL database with business schema and sample data
- **redis**: Redis for caching and session storage
- **chromadb**: ChromaDB for vector storage and embeddings
- **nginx**: Reverse proxy with load balancing (production profile)

### Quick Start with Docker Compose

1. **Setup environment**:
   ```bash
   just setup-env  # Creates .env file from env.example
   # Edit .env file with your API keys
   ```

2. **Start all services**:
   ```bash
   just compose-up
   ```

3. **View logs**:
   ```bash
   just compose-logs
   ```

4. **Stop services**:
   ```bash
   just compose-down
   ```

### Available URLs

- **Main API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379
- **ChromaDB**: http://localhost:8001
- **Nginx** (production): http://localhost

### Data Persistence

All data is persisted using Docker volumes:
- `postgres_data`: Database data
- `redis_data`: Redis data

