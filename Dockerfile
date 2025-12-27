# hospital-bulk-processor/Dockerfile
#
# Small, pragmatic Dockerfile for the toy project.
# - Installs system build deps (for some Python packages that may require compilation)
# - Installs Python dependencies from requirements.txt
# - Copies project files
# - Runs Gunicorn with Uvicorn worker by default (can be overridden to run celery)
#
# Usage:
#  - Build: docker build -t hospital-bulk-processor:latest .
#  - Run web (default): docker run -p 8000:8000 --env CELERY_BROKER_URL=redis://... hospital-bulk-processor
#  - Run worker: docker run --env CELERY_BROKER_URL=redis://... hospital-bulk-processor celery -A celery_worker.celery_app worker --pool=solo --loglevel=info
#
FROM python:3.11-slim

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    PIP_NO_CACHE_DIR=1 \
    PATH="/home/app/.local/bin:$PATH"

# Install minimal build tools and curl for healthcheck (kept small)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       gcc \
       libpq-dev \
       curl \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd --create-home --shell /bin/bash app

WORKDIR /app

# Copy only requirements first to leverage Docker cache
COPY requirements.txt /app/requirements.txt

# Upgrade pip & install requirements as non-root user into the user-local binary path
# Using --user so we don't need to manage virtualenvs inside the image.
RUN pip install --upgrade pip setuptools wheel \
    && pip install --user -r /app/requirements.txt

# Copy the rest of the application
COPY . /app

# Ensure app files are owned by the app user
RUN chown -R app:app /app

USER app

# Expose the default port used by the app
EXPOSE 8000

# Healthcheck (optional): use the /health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Default command: run the web server. Override the command to run a worker:
#   docker run ... hospital-bulk-processor celery -A celery_worker.celery_app worker --pool=solo --loglevel=info
CMD ["gunicorn", "-w", "1", "-k", "uvicorn.workers.UvicornWorker", "app.main:app", "--bind", "0.0.0.0:8000"]
