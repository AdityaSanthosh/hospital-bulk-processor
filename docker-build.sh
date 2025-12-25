#!/bin/bash

# Hospital Bulk Processor - Docker Build Script
# This script builds and runs the Docker container

set -e  # Exit on error

echo "=========================================="
echo "Hospital Bulk Processor - Docker Build"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed!"
    echo "Please install Docker from https://www.docker.com/get-started"
    exit 1
fi

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Warning: docker-compose is not installed!"
    echo "You can still use 'docker build' and 'docker run' commands"
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "${YELLOW}Warning: .env file not found. Creating from .env.example...${NC}"
    cp .env.example .env
    echo "${GREEN}✓ Created .env file${NC}"
fi

echo "Building Docker image..."
echo ""

# Build the Docker image
docker build -t hospital-bulk-processor:latest .

if [ $? -eq 0 ]; then
    echo ""
    echo "${GREEN}✓ Docker image built successfully!${NC}"
    echo ""
    echo "=========================================="
    echo "Next Steps:"
    echo "=========================================="
    echo ""
    echo "1. Run with Docker Compose (recommended):"
    echo "   docker-compose up"
    echo ""
    echo "2. Run with Docker Compose in background:"
    echo "   docker-compose up -d"
    echo ""
    echo "3. Run with Docker directly:"
    echo "   docker run -p 8000:8000 --env-file .env hospital-bulk-processor:latest"
    echo ""
    echo "4. Development mode with hot reload:"
    echo "   docker-compose -f docker-compose.dev.yml up"
    echo ""
    echo "Access the API at: http://localhost:8000"
    echo "API Documentation: http://localhost:8000/docs"
    echo ""
else
    echo ""
    echo "Error: Docker build failed!"
    exit 1
fi
