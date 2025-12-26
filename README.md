# Hospital Bulk Processor API v2.0

Production-ready FastAPI application for bulk processing hospital records with enterprise patterns.

## 🏗️ Architecture

### Layered Architecture
```
├── Presentation Layer (API)
│   └── app/api/v1/endpoints/
├── Application Layer (Use Cases)
│   └── app/services/
├── Domain Layer (Business Logic)
│   └── app/domain/
├── Background Tasks
│   └── app/tasks/
├── External Integrations
│   └── app/external/
└── Data Access
    └── app/repositories/
```

### Key Features

✅ **Celery Integration** - Distributed task processing with Redis  
✅ **Rate Limiting** - Prevents overwhelming external APIs  
✅ **Circuit Breaker** - Fails fast when external services are down  
✅ **Retry Mechanism** - Exponential backoff for transient failures  
✅ **Idempotency** - Safe retries with idempotency keys  
✅ **API Versioning** - `/api/v1/` prefix for future compatibility  
✅ **Layered Architecture** - Clean separation of concerns  
✅ **Fail-Fast Publishing** - Immediate failure detection when Redis is down (1-2s, not 30s+)  

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

**Idempotency-Key header is REQUIRED:**
```bash
# Generate UUID for idempotency key
curl -X POST http://localhost:8000/api/v1/hospitals/bulk \
     -H "Idempotency-Key: $(uuidgen)" \
     -F "file=@hospitals.csv"

# Or use your own unique key
curl -X POST http://localhost:8000/api/v1/hospitals/bulk \
     -H "Idempotency-Key: upload-2024-12-25-abc123" \
     -F "file=@hospitals.csv"
```

**Response (202 Accepted):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Job accepted and queued for processing...",
  "total_hospitals": 10
}
```

**Idempotency Behavior:**
- Same key within 5 minutes → Returns cached response (no duplicate processing)
- Different key with same CSV → Creates new job (business logic handles data duplicates)
- Stored in Redis with 5-minute TTL

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
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=2, max=10),
)
async def create_hospital(...):
    # Retries with exponential backoff
    # Using tenacity library: https://github.com/jd/tenacity
```

### Idempotency (Mandatory)
```bash
# Required: Client must provide unique key per upload attempt
curl -H "Idempotency-Key: $(uuidgen)" \
     -F "file=@hospitals.csv" \
     http://localhost:8000/api/v1/hospitals/bulk

# Same key within 5 minutes = cached response (request deduplication)
# Different key = new request (business logic handles data duplicates)
```

**Key Generation Examples:**
```bash
# UUID (recommended)
uuidgen  # macOS/Linux
# Or: python -c "import uuid; print(uuid.uuid4())"

# Timestamp-based
echo "upload-$(date +%s)-$(openssl rand -hex 4)"

# Semantic
echo "batch-user123-$(date +%Y%m%d%H%M%S)"
```

## 📊 Monitoring

### Logs
All operations are logged to console with structured format:
```
2024-01-15 10:30:15 - app.external.hospital_api_client - INFO - Hospital created successfully: General Hospital (ID: 101)
2024-01-15 10:30:16 - app.core.resilience - WARNING - Circuit breaker 'hospital_api' state changed: closed -> open
```

### Health Check
```bash
curl http://localhost:8000/health
```

### Redis for Idempotency
Idempotency keys are stored in Redis with 5-minute TTL:
```bash
# Check stored keys
redis-cli KEYS "idempotency:*"

# Check TTL for a key
redis-cli TTL "idempotency:your-key-here"

# Manual cleanup (if needed)
redis-cli DEL "idempotency:your-key-here"
```

## 🚨 Redis Fail-Fast Behavior

When Redis is unavailable, the application **fails immediately** (1-2 seconds) instead of retrying for 30+ seconds.

### Behavior
```
Redis DOWN → Job submission fails fast (1-2s) → Returns 503 to user
Redis UP   → Job queued successfully → Returns 202 Accepted
```

### Response When Redis is Down
```json
{
  "detail": "Service temporarily unavailable. The message queue is currently down. Please try again later."
}
```
**HTTP Status**: `503 Service Unavailable`

### Configuration
The fail-fast behavior is controlled by these settings in `.env`:

```bash
# Fail immediately when publishing (no retries)
CELERY_TASK_PUBLISH_RETRY=false
CELERY_TASK_PUBLISH_MAX_RETRIES=0

# Fast timeouts for quick failure detection
CELERY_REDIS_SOCKET_CONNECT_TIMEOUT=1
CELERY_REDIS_SOCKET_TIMEOUT=2
CELERY_REDIS_RETRY_ON_TIMEOUT=false
```

### Testing Fail-Fast Behavior
```bash
# 1. Stop Redis
redis-cli shutdown

# 2. Run test script
python test_redis_failfast.py

# 3. Observe immediate failure (1-2 seconds)
# Expected: Job submission fails quickly with clear error

# 4. Start Redis
brew services start redis

# 5. Test again - should succeed
python test_redis_failfast.py
```

### Why Fail-Fast?
- ✅ **Quick user feedback** - No long timeouts
- ✅ **Clear error messages** - Users know to retry later
- ✅ **No resource exhaustion** - Prevents retry loops
- ✅ **Better UX** - Fast failures > slow timeouts

📖 **Detailed documentation**: See [docs/REDIS_FAILFAST.md](docs/REDIS_FAILFAST.md)

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
│   ├── services/
│   │   └── job_service.py        # Job orchestration
│   │
│   ├── tasks/
│   │   ├── celery_app.py         # Celery configuration
│   │   └── tasks.py              # Celery tasks
│   │
│   ├── external/
│   │   └── hospital_api_client.py  # External API client
│   │
│   ├── repositories/
│   │   └── job_repository.py     # Job storage
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
