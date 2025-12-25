# Hospital Bulk Processor API v2.0

Production-ready FastAPI application for bulk processing hospital records with enterprise patterns.

## 🏗️ Architecture

### Layered Architecture
```
├── Presentation Layer (API)
│   └── app/api/v1/endpoints/
├── Application Layer (Use Cases)
│   └── app/application/
├── Domain Layer (Business Logic)
│   └── app/domain/
└── Infrastructure Layer (External Services)
    ├── app/infrastructure/external/
    ├── app/infrastructure/celery/
    └── app/infrastructure/repositories/
```

### Key Features

✅ **Celery Integration** - Distributed task processing with Redis  
✅ **Rate Limiting** - Prevents overwhelming external APIs  
✅ **Circuit Breaker** - Fails fast when external services are down  
✅ **Retry Mechanism** - Exponential backoff for transient failures  
✅ **Idempotency** - Safe retries with idempotency keys  
✅ **API Versioning** - `/api/v1/` prefix for future compatibility  
✅ **Layered Architecture** - Clean separation of concerns  

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Redis (for Celery)

### Installation

1. **Install dependencies**
```bash
pip install -r requirements.txt
```

2. **Start Redis**
```bash
# Using Docker
docker run -d -p 6379:6379 redis:7-alpine

# Or using Homebrew (macOS)
brew install redis
brew services start redis
```

3. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your settings
```

4. **Start Celery worker**
```bash
celery -A celery_worker.celery_app worker --loglevel=info
```

5. **Start FastAPI server**
```bash
python app/main.py
# Or
uvicorn app.main:app --reload --port 8000
```

## 📡 API Endpoints

### Submit Bulk Upload
```bash
POST /api/v1/hospitals/bulk
```

**With Idempotency:**
```bash
curl -X POST http://localhost:8000/api/v1/hospitals/bulk \
     -H "Idempotency-Key: my-unique-key-123" \
     -F "file=@hospitals.csv"
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Job accepted and queued for processing...",
  "total_hospitals": 10,
  "idempotency_key": "abc123..."
}
```

### Get Job Status
```bash
GET /api/v1/hospitals/status/{job_id}
```

**Example:**
```bash
curl http://localhost:8000/api/v1/hospitals/status/550e8400-e29b-41d4-a716-446655440000
```

## 🔧 Configuration

All configuration is in `app/config.py` and can be overridden via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Redis URL for Celery |
| `RATE_LIMIT_REQUESTS` | `10` | Max requests per period |
| `RATE_LIMIT_PERIOD` | `1.0` | Period in seconds |
| `RETRY_MAX_ATTEMPTS` | `3` | Max retry attempts |
| `CIRCUIT_BREAKER_FAILURE_THRESHOLD` | `5` | Failures before opening circuit |
| `CIRCUIT_BREAKER_RECOVERY_TIMEOUT` | `60` | Seconds before retry |

## 🛡️ Resilience Patterns

### Rate Limiting
Prevents overwhelming the external Hospital API:
```python
rate_limiter = RateLimiter(max_rate=10, time_period=1.0)
```

### Circuit Breaker
Fails fast when external API is down:
```python
@hospital_api_circuit_breaker
async def create_hospital(...):
    # Stops calling after 5 failures
    # Retries after 60 seconds
```

### Retry with Exponential Backoff
```python
@RetryPolicy.with_retry(max_attempts=3)
async def create_hospital(...):
    # Retries with exponential backoff
    # 2s, 4s, 8s delays
```

### Idempotency
Safe retries with idempotency keys:
```bash
# Same key returns cached response
curl -H "Idempotency-Key: unique-123" ...
```

## 📊 Monitoring

### Logs
All operations are logged to console with structured format:
```
2024-01-15 10:30:15 - app.infrastructure.external.hospital_api_client - INFO - Hospital created successfully: General Hospital (ID: 101)
2024-01-15 10:30:16 - app.core.resilience - WARNING - Circuit breaker 'hospital_api' state changed: closed -> open
```

### Health Check
```bash
curl http://localhost:8000/health
```

## 🧪 Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=app tests/
```

## 📦 Project Structure

```
hospital-bulk-processor/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application
│   ├── config.py                  # Configuration
│   │
│   ├── api/
│   │   └── v1/
│   │       └── endpoints/
│   │           └── hospitals.py   # API endpoints
│   │
│   ├── core/
│   │   ├── resilience.py         # Rate limiter, circuit breaker, retry
│   │   └── idempotency.py        # Idempotency store
│   │
│   ├── domain/
│   │   ├── schemas.py            # Pydantic models
│   │   └── exceptions.py         # Domain exceptions
│   │
│   ├── application/
│   │   └── job_service.py        # Job orchestration
│   │
│   ├── infrastructure/
│   │   ├── celery/
│   │   │   ├── celery_app.py     # Celery configuration
│   │   │   └── tasks.py          # Celery tasks
│   │   ├── external/
│   │   │   └── hospital_api_client.py  # External API client
│   │   └── repositories/
│   │       └── job_repository.py # Job storage
│   │
│   └── utils/
│       └── csv_validator.py      # CSV validation
│
├── celery_worker.py              # Celery worker entrypoint
├── requirements.txt
└── .env.example
```

## 🔄 Migration from v1.0

The old code is backed up in `app_old/`. Key changes:

- ✅ FastAPI `BackgroundTasks` → **Celery**
- ✅ Custom `JobManager` → **Repository pattern**
- ✅ Direct API calls → **Rate limiting + Circuit breaker + Retry**
- ✅ No idempotency → **Idempotency keys**
- ✅ Single file → **Layered architecture**
- ✅ No versioning → **API v1**

## 📝 License

MIT
