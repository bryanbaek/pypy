# Docker Compose Setup Guide

This document provides detailed information about the Docker Compose configuration for the Diary application.

## Architecture Overview

The application uses a microservices architecture with the following components:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Nginx       │    │   Diary App     │    │   MCP Server    │
│  (Port 80/443)  │────│   (Port 8000)   │    │   (Internal)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                ┌───────────────┼───────────────┐
                │               │               │
        ┌───────▼──────┐ ┌──────▼──────┐ ┌─────▼─────┐
        │  PostgreSQL  │ │    Redis    │ │ ChromaDB  │
        │ (Port 5432)  │ │ (Port 6379) │ │(Port 8001)│
        └──────────────┘ └─────────────┘ └───────────┘
```

## Services

### 1. diary-app (Main Application)
- **Purpose**: FastAPI web application with AI integration
- **Port**: 8000
- **Dependencies**: postgres, redis, chromadb
- **Health Check**: HTTP GET to `/`
- **Environment**: API keys, database URLs

### 2. postgres (Database)
- **Purpose**: Primary data storage
- **Image**: postgres:15-alpine
- **Port**: 5432
- **Database**: diary_db
- **User**: diary_user
- **Features**: Full-text search, UUID support, automatic schema setup

### 3. redis (Cache & Sessions)
- **Purpose**: Caching and session storage
- **Image**: redis:7-alpine
- **Port**: 6379
- **Features**: Persistence enabled, password protected

### 4. chromadb (Vector Database)
- **Purpose**: Embeddings and semantic search
- **Image**: chromadb/chroma:latest
- **Port**: 8001
- **Features**: Vector similarity search, AI embeddings storage

### 5. mcp-server (MCP Protocol)
- **Purpose**: Model Context Protocol server for AI tools
- **Dependencies**: diary-app
- **Features**: 10 diary management tools

### 6. nginx (Reverse Proxy) [Production Profile]
- **Purpose**: Load balancing, SSL termination, static file serving
- **Port**: 80, 443
- **Features**: Gzip compression, rate limiting, security headers

## Environment Configuration

### Required Environment Variables

Create `.env` file from `env.example`:

```bash
just setup-env
```

Edit the `.env` file with your settings:

```bash
# API Keys (required for AI features)
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=AIza...
GROQ_API_KEY=gsk_...

# Database (automatically configured)
DATABASE_URL=postgresql://diary_user:diary_password@postgres:5432/diary_db

# Redis (automatically configured)
REDIS_URL=redis://:redis_password@redis:6379/0

# Security
SECRET_KEY=your-secret-key-here
```

## Quick Start Commands

### Basic Operations

```bash
# Setup environment file
just setup-env

# Start all services in background
just compose-up

# Start services with live logs
just compose-up-logs

# Stop all services
just compose-down

# Stop and remove all data
just compose-down-volumes
```

### Development Workflow

```bash
# Check service status
just compose-status

# View logs
just compose-logs              # All services
just compose-logs-app          # Just the app
just compose-logs-db           # Just the database

# Restart specific service
just compose-restart-app

# Rebuild after code changes
just compose-rebuild
```

### Database Operations

```bash
# Access database shell
just compose-shell-db

# Run migrations (when implemented)
just compose-migrate

# Backup database
docker-compose exec postgres pg_dump -U diary_user diary_db > backup.sql

# Restore database
docker-compose exec -T postgres psql -U diary_user diary_db < backup.sql
```

### Application Access

```bash
# Access app container shell
just compose-shell

# Run commands in app container
docker-compose exec diary-app uv run python src/backend/mcp/test_server.py
```

## Production Deployment

### With Nginx (Recommended)

```bash
# Start with production profile (includes nginx)
just compose-prod

# Access points:
# - http://localhost (nginx proxy)
# - http://localhost:8000 (direct app access)
```

### SSL Configuration

1. Place SSL certificates in `nginx/ssl/`:
   ```
   nginx/ssl/
   ├── cert.pem
   └── key.pem
   ```

2. Uncomment HTTPS configuration in `nginx/nginx.conf`

3. Restart nginx:
   ```bash
   docker-compose restart nginx
   ```

## Data Persistence

All data is stored in Docker volumes:

```bash
# List volumes
docker volume ls | grep diary

# Backup volumes
docker run --rm -v diary_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz -C /data .

# Restore volumes
docker run --rm -v diary_postgres_data:/data -v $(pwd):/backup alpine tar xzf /backup/postgres_backup.tar.gz -C /data
```

## Monitoring and Troubleshooting

### Health Checks

All services include health checks:

```bash
# Check health status
docker-compose ps

# View health check logs
docker inspect diary-app | jq '.[].State.Health'
```

### Common Issues

1. **Port conflicts**:
   ```bash
   # Check what's using ports
   lsof -i :8000
   lsof -i :5432
   lsof -i :6379
   ```

2. **Permission issues**:
   ```bash
   # Fix volume permissions
   sudo chown -R $USER:$USER ./data
   ```

3. **Memory issues**:
   ```bash
   # Check resource usage
   docker stats
   
   # Limit memory in docker-compose.yml
   services:
     diary-app:
       deploy:
         resources:
           limits:
             memory: 512M
   ```

### Logs and Debugging

```bash
# Follow all logs
just compose-logs

# Debug specific service
docker-compose logs --tail=100 -f diary-app

# Check container resource usage
docker stats $(docker-compose ps -q)
```

## Development Tips

### Local Development with Docker

```bash
# Start only infrastructure services
docker-compose up -d postgres redis chromadb

# Run app locally
just dev

# This allows for faster development with hot reload
```

### Testing

```bash
# Run tests in container
docker-compose exec diary-app uv run pytest

# Run MCP tests
docker-compose exec diary-app uv run python src/backend/mcp/test_server.py
```

### Code Changes

```bash
# For code changes, rebuild the app
just compose-rebuild

# Or just restart the app service
just compose-restart-app
```

## Security Considerations

1. **Change default passwords** in production
2. **Use environment-specific `.env` files**
3. **Enable SSL/TLS** for production
4. **Implement proper authentication**
5. **Use secrets management** for API keys
6. **Regular security updates** for base images

## Performance Optimization

1. **Use multi-stage builds** for smaller images
2. **Implement caching strategies** with Redis
3. **Optimize database queries** and indexing
4. **Use connection pooling**
5. **Monitor resource usage** and scale accordingly

## Backup Strategy

```bash
# Daily backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker-compose exec postgres pg_dump -U diary_user diary_db > "backup_${DATE}.sql"
find . -name "backup_*.sql" -mtime +7 -delete  # Keep 7 days
``` 