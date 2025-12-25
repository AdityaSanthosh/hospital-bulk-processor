#!/bin/bash

# Development startup script

echo "==================================================================="
echo "  Hospital Bulk Processor API v2.0 - Development Mode"
echo "==================================================================="
echo ""

# Check if Redis is running
if ! redis-cli ping > /dev/null 2>&1; then
    echo "❌ Redis is not running!"
    echo ""
    echo "Please start Redis first:"
    echo "  - Docker: docker run -d -p 6379:6379 redis:7-alpine"
    echo "  - macOS:  brew services start redis"
    echo "  - Linux:  sudo systemctl start redis"
    echo ""
    exit 1
fi

echo "✅ Redis is running"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    cp .env.example .env
    echo "✅ .env file created. Please review and update if needed."
    echo ""
fi

echo "Starting services..."
echo ""

# Start Celery worker in background
echo "🔄 Starting Celery worker..."
celery -A celery_worker.celery_app worker --loglevel=info > celery.log 2>&1 &
CELERY_PID=$!
echo "✅ Celery worker started (PID: $CELERY_PID)"
echo "   Logs: tail -f celery.log"
echo ""

# Wait a moment for Celery to start
sleep 2

# Start FastAPI server
echo "🚀 Starting FastAPI server..."
echo ""
python app/main.py

# Cleanup on exit
trap "echo ''; echo 'Stopping Celery worker...'; kill $CELERY_PID 2>/dev/null" EXIT
