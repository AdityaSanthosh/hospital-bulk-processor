# 🐳 Docker Documentation

Complete guide for running the Hospital Bulk Processor API with Docker.

## Table of Contents

- [Quick Start](#quick-start)
- [Prerequisites](#prerequisites)
- [Building the Image](#building-the-image)
- [Running the Container](#running-the-container)
- [Docker Compose](#docker-compose)
- [Make Commands](#make-commands)
- [Configuration](#configuration)
- [Development vs Production](#development-vs-production)
- [Troubleshooting](#troubleshooting)
- [Advanced Usage](#advanced-usage)

## Quick Start

The fastest way to get started:

```bash
# Build and start in one command
docker-compose up --build

# Or use the build script
./docker-build.sh
docker-compose up
```

Access the API at: http://localhost:8000/docs

## Prerequisites

- **Docker**: Version 20.10 or higher
- **Docker Compose**: Version 1.29 or higher

### Install Docker

- **macOS**: [Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/)
- **Windows**: [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/)
- **Linux**: [Docker Engine](https://docs.docker.com/engine/install/)

Verify installation:
```bash
docker --version
docker-compose --version
```

## Building the Image

### Using Docker Compose (Recommended)

```bash
docker-compose build
```

### Using the Build Script

```bash
chmod +x docker-build.sh
./docker-build.sh
```

### Using Docker Directly

```bash
docker build -t hospital-bulk-processor:latest .
```

### Build Options

**No cache (fresh build):**
```bash
docker-compose build --no-cache
```

**With specific tag:**
```bash
docker build -t hospital-bulk-processor:v1.0.0 .
```

## Running the Container

### Using Docker Compose (Recommended)

**Foreground (with logs):**
```bash
docker-compose up
```

**Background (detached):**
```bash
docker-compose up -d
```

**Stop containers:**
```bash
docker-compose down
```

### Using Docker Directly

```bash
docker run -p 8000:8000 --env-file .env hospital-bulk-processor:latest
```

**With custom port:**
```bash
docker run -p 9000:8000 --env-file .env hospital-bulk-processor:latest
```

**With environment variables:**
```bash
docker run -p 8000:8000 \
  -e HOSPITAL_API_BASE_URL=https://hospital-directory.onrender.com \
  -e MAX_CSV_ROWS=20 \
  -e PORT=8000 \
  hospital-bulk-processor:latest
```

## Docker Compose

### Production Configuration

File: `docker-compose.yml`

```bash
# Start in production mode
docker-compose up

# Start in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Development Configuration

File: `docker-compose.dev.yml`

Features:
- Hot reload enabled
- Code mounted as volume (changes reflect immediately)
- More verbose logging

```bash
# Start in development mode
docker-compose -f docker-compose.dev.yml up

# Start in background
docker-compose -f docker-compose.dev.yml up -d

# Stop
docker-compose -f docker-compose.dev.yml down
```

### Common Docker Compose Commands

```bash
# Build the image
docker-compose build

# Start services
docker-compose up

# Start in background
docker-compose up -d

# View logs
docker-compose logs -f

# View logs for specific service
docker-compose logs -f app

# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v

# Restart services
docker-compose restart

# Show running containers
docker-compose ps

# Execute command in container
docker-compose exec app <command>

# Open shell in container
docker-compose exec app /bin/bash

# Scale services (if needed)
docker-compose up -d --scale app=3
```

## Make Commands

The `Makefile` provides convenient shortcuts for Docker operations.

### Basic Commands

```bash
make help           # Show all available commands
make build          # Build Docker image
make up             # Start in production mode
make up-d           # Start in background
make down           # Stop containers
make restart        # Restart containers
make logs           # View logs
make status         # Show container status
```

### Development Commands

```bash
make dev            # Start in development mode (hot reload)
make dev-d          # Start in dev mode (background)
make shell          # Open bash shell in container
make python-shell   # Open Python REPL in container
make test           # Run tests in container
```

### Maintenance Commands

```bash
make clean          # Remove containers and volumes
make clean-images   # Remove Docker images
make clean-all      # Full cleanup
make rebuild        # Rebuild from scratch
make health         # Check service health
make test-upload    # Test CSV upload with sample file
```

### Example Workflow

```bash
# First time setup
make build

# Start development server
make dev-d

# View logs
make logs

# Test the API
make health
make test-upload

# Open shell to debug
make shell

# Stop when done
make down
```

## Configuration

### Environment Variables

Create a `.env` file from the example:

```bash
cp .env.example .env
```

Available variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `HOSPITAL_API_BASE_URL` | `https://hospital-directory.onrender.com` | External API base URL |
| `MAX_CSV_ROWS` | `20` | Maximum rows in CSV |
| `UPLOAD_MAX_SIZE_MB` | `5` | Max file size in MB |
| `HOST` | `0.0.0.0` | Server host |
| `PORT` | `8000` | Server port |

### Customizing docker-compose.yml

**Change port mapping:**
```yaml
ports:
  - "9000:8000"  # Access on port 9000
```

**Add custom environment variables:**
```yaml
environment:
  - CUSTOM_VAR=value
  - DEBUG=true
```

**Mount additional volumes:**
```yaml
volumes:
  - ./data:/app/data
  - ./logs:/app/logs
```

## Development vs Production

### Development Mode

**Features:**
- Hot reload enabled (code changes auto-reload)
- Code mounted as volume
- More verbose logging
- Interactive mode

**Start:**
```bash
docker-compose -f docker-compose.dev.yml up
# or
make dev
```

**Best for:**
- Local development
- Testing changes quickly
- Debugging

### Production Mode

**Features:**
- Optimized for performance
- No hot reload
- Code baked into image
- Production-ready settings
- Health checks enabled

**Start:**
```bash
docker-compose up -d
# or
make prod
```

**Best for:**
- Production deployments
- Staging environments
- Performance testing

## Troubleshooting

### Common Issues

#### Port Already in Use

**Problem:** Port 8000 is already occupied

**Solution:**
```bash
# Option 1: Stop the other service
docker-compose down

# Option 2: Change the port in docker-compose.yml
ports:
  - "9000:8000"
```

#### Container Exits Immediately

**Problem:** Container starts and stops right away

**Solution:**
```bash
# Check logs
docker-compose logs

# Check container status
docker-compose ps

# Rebuild without cache
docker-compose build --no-cache
```

#### Cannot Connect to External API

**Problem:** Cannot reach hospital-directory.onrender.com

**Solution:**
```bash
# Test from host
curl https://hospital-directory.onrender.com/docs

# Test from container
docker-compose exec app curl https://hospital-directory.onrender.com/docs

# Check DNS
docker-compose exec app ping hospital-directory.onrender.com
```

#### Permission Denied

**Problem:** Cannot execute scripts

**Solution:**
```bash
chmod +x docker-build.sh start.sh
```

#### Image Build Fails

**Problem:** Docker build errors

**Solution:**
```bash
# Clear Docker cache
docker system prune -a

# Rebuild without cache
docker-compose build --no-cache

# Check Dockerfile syntax
docker build -t test .
```

#### Container Runs but API Not Accessible

**Problem:** Container running but can't access http://localhost:8000

**Solution:**
```bash
# Check if container is running
docker-compose ps

# Check port mapping
docker-compose port app 8000

# Check logs for errors
docker-compose logs app

# Try accessing from container
docker-compose exec app curl http://localhost:8000/health
```

### Debugging Commands

```bash
# View detailed logs
docker-compose logs -f --tail=100

# Inspect container
docker inspect hospital-bulk-processor

# Check resource usage
docker stats hospital-bulk-processor

# View container processes
docker-compose exec app ps aux

# Check network connectivity
docker-compose exec app ping google.com

# View environment variables
docker-compose exec app env
```

## Advanced Usage

### Multi-Stage Builds

For smaller production images, use multi-stage builds:

```dockerfile
# Builder stage
FROM python:3.10-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# Runtime stage
FROM python:3.10-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY app/ ./app/
ENV PATH=/root/.local/bin:$PATH
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Custom Networks

Connect to external services:

```yaml
services:
  app:
    networks:
      - hospital-network
      - external-network

networks:
  hospital-network:
    driver: bridge
  external-network:
    external: true
```

### Health Checks

Monitor container health:

```bash
# Check health status
docker inspect --format='{{.State.Health.Status}}' hospital-bulk-processor

# View health check logs
docker inspect --format='{{json .State.Health}}' hospital-bulk-processor | python -m json.tool
```

### Volume Management

```bash
# List volumes
docker volume ls

# Inspect volume
docker volume inspect hospital-bulk-processor_data

# Remove unused volumes
docker volume prune

# Backup volume
docker run --rm -v hospital-bulk-processor_data:/data -v $(pwd):/backup alpine tar czf /backup/data-backup.tar.gz -C /data .
```

### Docker Compose Override

Create `docker-compose.override.yml` for local customizations:

```yaml
version: '3.8'

services:
  app:
    ports:
      - "9000:8000"  # Custom port
    environment:
      - DEBUG=true
    volumes:
      - ./custom-config.yml:/app/config.yml
```

This file is automatically used by docker-compose and ignored by git.

### CI/CD Integration

**GitHub Actions example:**

```yaml
name: Docker Build

on: [push]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Build Docker image
        run: docker build -t hospital-bulk-processor .
      - name: Run tests
        run: docker run hospital-bulk-processor python test_setup.py
```

### Resource Limits

Limit container resources:

```yaml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
```

### Logging Configuration

Custom logging driver:

```yaml
services:
  app:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

## Best Practices

1. **Use .dockerignore**: Exclude unnecessary files from build context
2. **Layer caching**: Order Dockerfile commands from least to most frequently changing
3. **Non-root user**: Run container as non-root for security
4. **Health checks**: Always include health check endpoints
5. **Environment variables**: Never hardcode secrets in Dockerfile
6. **Volume mounts**: Use volumes for persistent data
7. **Network isolation**: Use Docker networks for service communication
8. **Resource limits**: Set memory and CPU limits in production
9. **Multi-stage builds**: Reduce final image size
10. **Regular updates**: Keep base images and dependencies updated

## Security Considerations

- Container runs as non-root user (appuser)
- No sensitive data in Dockerfile
- Use secrets management for production
- Keep base images updated
- Scan images for vulnerabilities: `docker scan hospital-bulk-processor`
- Use official base images only
- Minimize attack surface (slim images)

## Performance Optimization

- Use slim base images (python:3.10-slim)
- Multi-stage builds to reduce size
- Layer caching for faster builds
- Resource limits to prevent resource exhaustion
- Health checks for automatic recovery
- Async I/O for better throughput

## Useful Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [FastAPI in Docker](https://fastapi.tiangolo.com/deployment/docker/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)

---

For more information, see the main [README.md](README.md) file.