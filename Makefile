.PHONY: help build up down restart logs shell test clean dev prod

# Default target
help:
	@echo "Hospital Bulk Processor - Docker Commands"
	@echo "==========================================="
	@echo ""
	@echo "Available commands:"
	@echo "  make build       - Build Docker image"
	@echo "  make up          - Start containers in production mode"
	@echo "  make down        - Stop and remove containers"
	@echo "  make restart     - Restart containers"
	@echo "  make logs        - View container logs"
	@echo "  make shell       - Open shell in container"
	@echo "  make test        - Run tests in container"
	@echo "  make clean       - Remove containers, images, and volumes"
	@echo "  make dev         - Start in development mode (hot reload)"
	@echo "  make prod        - Start in production mode"
	@echo "  make status      - Show container status"
	@echo ""

# Build Docker image
build:
	@echo "Building Docker image..."
	docker-compose build

# Start containers in production mode
up:
	@echo "Starting containers in production mode..."
	docker-compose up

# Start containers in background
up-d:
	@echo "Starting containers in background..."
	docker-compose up -d
	@echo "Containers started!"
	@echo "API: http://localhost:8000"
	@echo "Docs: http://localhost:8000/docs"

# Start in development mode with hot reload
dev:
	@echo "Starting in development mode (hot reload)..."
	docker-compose -f docker-compose.dev.yml up

# Start in development mode (background)
dev-d:
	@echo "Starting in development mode (background)..."
	docker-compose -f docker-compose.dev.yml up -d
	@echo "Development server started!"
	@echo "API: http://localhost:8000"
	@echo "Docs: http://localhost:8000/docs"

# Production mode
prod:
	@echo "Starting in production mode..."
	docker-compose up -d
	@echo "Production server started!"

# Stop containers
down:
	@echo "Stopping containers..."
	docker-compose down

# Stop and remove everything
down-all:
	@echo "Stopping containers and removing volumes..."
	docker-compose down -v

# Restart containers
restart:
	@echo "Restarting containers..."
	docker-compose restart

# View logs
logs:
	docker-compose logs -f

# View logs for specific service
logs-app:
	docker-compose logs -f app

# Open shell in container
shell:
	docker-compose exec app /bin/bash

# Run Python shell in container
python-shell:
	docker-compose exec app python

# Check container status
status:
	docker-compose ps

# Run tests
test:
	docker-compose exec app python test_setup.py

# Clean everything
clean:
	@echo "Cleaning up Docker resources..."
	docker-compose down -v --remove-orphans
	docker system prune -f
	@echo "Cleanup complete!"

# Clean images
clean-images:
	@echo "Removing Docker images..."
	docker rmi hospital-bulk-processor:latest || true
	@echo "Images removed!"

# Full clean (including images)
clean-all: clean clean-images
	@echo "Full cleanup complete!"

# Rebuild from scratch
rebuild:
	@echo "Rebuilding from scratch..."
	docker-compose down -v
	docker-compose build --no-cache
	docker-compose up -d
	@echo "Rebuild complete!"

# Check health
health:
	@echo "Checking health status..."
	curl -s http://localhost:8000/health | python -m json.tool || echo "Service not available"

# Test upload with sample CSV
test-upload:
	@echo "Testing CSV upload..."
	curl -X POST "http://localhost:8000/hospitals/bulk" \
		-H "accept: application/json" \
		-F "file=@sample_hospitals.csv"

# Install dependencies locally (for development)
install:
	python -m venv venv
	. venv/bin/activate && pip install -r requirements.txt

# Format code
format:
	docker-compose exec app python -m black app/ || echo "Black not installed"

# Lint code
lint:
	docker-compose exec app python -m pylint app/ || echo "Pylint not installed"
