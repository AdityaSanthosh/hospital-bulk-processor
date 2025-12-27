# Redis Fail-Fast Configuration

## Overview

This application is configured to **fail immediately** when Redis is unavailable during message publishing, rather than retrying multiple times. This ensures users receive quick feedback instead of experiencing long timeouts.

## Configuration Strategy

### Fail-Fast Approach
- ✅ **Quick failure detection** (1-2 seconds)
- ✅ **Immediate user feedback** (503 Service Unavailable)
- ✅ **No resource exhaustion** from retry loops
- ✅ **Clean error messages** for users
- ✅ **Graceful degradation**

### When Redis Goes Down

```
User uploads CSV → API attempts to queue job → Redis unavailable
                                              ↓
                                    Fails immediately (1-2s)
                                              ↓
                                    Returns 503 to user
                                              ↓
                        "Service temporarily unavailable. 
                         The message queue is currently down. 
                         Please try again later."
```

## Configuration Settings

### 1. Task Publishing (Fail Fast)

**Purpose**: Control behavior when publishing messages to Redis.

```python
# app/config.py
celery_task_publish_retry: bool = False          # Don't retry on publish failure
celery_task_publish_max_retries: int = 0         # 0 retries = fail immediately
celery_task_publish_timeout: int = 2             # 2 second timeout
```

**Environment Variables**:
```bash
CELERY_TASK_PUBLISH_RETRY=false
CELERY_TASK_PUBLISH_MAX_RETRIES=0
CELERY_TASK_PUBLISH_TIMEOUT=2
```

### 2. Redis Socket Settings (Fast Timeouts)

**Purpose**: Detect Redis connection failures quickly.

```python
# app/config.py
celery_redis_socket_connect_timeout: int = 1     # 1 second to connect
celery_redis_socket_timeout: int = 2             # 2 second for operations
celery_redis_retry_on_timeout: bool = False      # Don't retry on timeout
```

**Environment Variables**:
```bash
CELERY_REDIS_SOCKET_CONNECT_TIMEOUT=1
CELERY_REDIS_SOCKET_TIMEOUT=2
CELERY_REDIS_RETRY_ON_TIMEOUT=false
```

### 3. Broker Connection (Startup Only)

**Purpose**: These settings apply to **app startup** and **worker startup**, NOT runtime publishing.

```python
# app/config.py
celery_broker_connection_retry: bool = True              # Retry on startup
celery_broker_connection_retry_on_startup: bool = True   # Retry on startup
celery_broker_connection_max_retries: int = 3            # Max 3 retries on startup
celery_broker_connection_timeout: int = 2                # 2 second timeout per attempt
celery_broker_pool_limit: int = 10                       # Connection pool size
```

**Environment Variables**:
```bash
CELERY_BROKER_CONNECTION_RETRY=true
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP=true
CELERY_BROKER_CONNECTION_MAX_RETRIES=3
CELERY_BROKER_CONNECTION_TIMEOUT=2
CELERY_BROKER_POOL_LIMIT=10
```

**Note**: These only affect **initialization**, not runtime message publishing.

## Complete Configuration

### Celery App Configuration (`app/tasks/celery_app.py`)

```python
celery_app.conf.update(
    # Task Publishing (FAIL FAST)
    task_publish_retry=False,                    # ← KEY: Fail immediately
    task_publish_retry_policy={
        "max_retries": 0,                        # ← KEY: No retries
        "interval_start": 0,
        "interval_step": 0.1,
        "interval_max": 0.2,
    },
    
    # Broker Transport Options
    broker_transport_options={
        "socket_connect_timeout": 1,             # ← Fast timeout
        "socket_timeout": 2,                     # ← Fast timeout
        "socket_keepalive": False,
        "retry_on_timeout": False,               # ← Don't retry
        "max_connections": 10,
        "health_check_interval": 30,
        "visibility_timeout": 43200,
    },
    
    # Redis Backend Settings
    redis_socket_connect_timeout=1,              # ← Fast timeout
    redis_socket_timeout=2,                      # ← Fast timeout
    redis_socket_keepalive=False,
    redis_retry_on_timeout=False,                # ← Don't retry
    redis_max_connections=10,
)
```

## Error Handling in API

### Service Layer (`app/services/job_service.py`)

```python
try:
    # Attempt to publish message to Redis
    process_bulk_hospitals_task.delay(job.job_id, hospitals_data)
    
except OperationalError as e:
    # Redis connection failed - fail fast
    logger.error(f"Message queue unavailable: {e}")
    
    # Clean up job
    job_repository.update_status(job.job_id, JobStatus.FAILED)
    job_repository.set_error(job.job_id, "Message queue unavailable")
    
    # Return 503 to user
    raise HTTPException(
        status_code=503,
        detail="Service temporarily unavailable. The message queue is currently down. Please try again later."
    )
```

### API Response

**When Redis is DOWN**:
```json
{
  "detail": "Service temporarily unavailable. The message queue is currently down. Please try again later."
}
```
**HTTP Status**: `503 Service Unavailable`

**When Redis is UP**:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Job accepted and queued for processing. Use the job_id to check status.",
  "total_hospitals": 10
}
```
**HTTP Status**: `202 Accepted`

## Testing Fail-Fast Behavior

### Using the Test Script

```bash
# 1. Stop Redis
redis-cli shutdown
# OR
brew services stop redis
# OR
docker stop redis-container

# 2. Run test script
python test_redis_failfast.py

# Expected output: Fails in 1-2 seconds with clear error message

# 3. Start Redis
brew services start redis
# OR
docker start redis-container

# 4. Run test again - should succeed
python test_redis_failfast.py
```

### Manual Testing with cURL

```bash
# Stop Redis first
redis-cli shutdown

# Try to upload CSV
curl -X POST http://localhost:8000/api/v1/hospitals/bulk \
  -H "Idempotency-Key: test-123" \
  -F "file=@sample_hospitals.csv"

# Expected response (within 1-2 seconds):
# {
#   "detail": "Service temporarily unavailable. The message queue is currently down. Please try again later."
# }
# HTTP Status: 503
```

## Behavior Comparison

### Before (Default Celery Behavior)
```
User uploads CSV
    ↓
Attempts to queue job
    ↓
Redis is down
    ↓
Retry 1... (wait)
Retry 2... (wait)
Retry 3... (wait)
...
Retry 20... (wait)      ← Takes 30+ seconds!
    ↓
Finally fails
    ↓
User gets timeout error
```

### After (Fail-Fast Configuration)
```
User uploads CSV
    ↓
Attempts to queue job
    ↓
Redis is down
    ↓
Fails immediately (1-2 seconds)  ← Fast!
    ↓
Returns 503 to user with clear message
    ↓
User knows to try again later
```

## Production Recommendations

### For High Availability

If you need the system to stay up even when Redis is down, consider:

1. **Redis Sentinel** (Automatic Failover)
```python
celery_broker_url = 'sentinel://sentinel1:26379;sentinel://sentinel2:26379'
broker_transport_options = {
    'master_name': 'mymaster',
    'sentinel_kwargs': {'password': 'sentinel_pass'},
}
```

2. **Redis Cluster** (Distributed)
```python
celery_broker_url = 'redis://redis1:6379/0;redis://redis2:6379/0;redis://redis3:6379/0'
```

3. **Alternative Queue Backend**
```python
# Use RabbitMQ instead (more resilient)
celery_broker_url = 'amqp://user:pass@rabbitmq:5672//'
```

### For Different Fail-Fast Behavior

If you want **some** retries but not 20:

```bash
# Allow 2-3 quick retries
CELERY_TASK_PUBLISH_RETRY=true
CELERY_TASK_PUBLISH_MAX_RETRIES=2
CELERY_REDIS_SOCKET_CONNECT_TIMEOUT=1
CELERY_REDIS_SOCKET_TIMEOUT=1
```

This will retry 2 times quickly (~3-4 seconds total).

## Monitoring and Alerts

### Health Check Endpoint

The application includes a health check that verifies Redis connectivity:

```bash
curl http://localhost:8000/health
```

**Response when Redis is down**:
```json
{
  "status": "unhealthy",
  "redis": "down",
  "message": "Message queue unavailable"
}
```

### Recommended Monitoring

1. **Monitor Redis availability**
   - Set up alerts when Redis is unreachable
   - Track connection errors in logs

2. **Monitor 503 error rate**
   - Spike in 503 errors = Redis is down
   - Alert operations team immediately

3. **Track job submission failures**
   - Log all `OperationalError` exceptions
   - Dashboard showing successful vs failed submissions

## Summary

| Setting | Value | Purpose |
|---------|-------|---------|
| `task_publish_retry` | `false` | Don't retry publishing |
| `task_publish_max_retries` | `0` | No retries = fail fast |
| `redis_socket_connect_timeout` | `1` | Fast connection detection |
| `redis_socket_timeout` | `2` | Fast operation timeout |
| `redis_retry_on_timeout` | `false` | Don't retry timeouts |

**Result**: 
- ✅ Fails in **1-2 seconds** instead of 30+ seconds
- ✅ Returns **503** with clear message
- ✅ User knows to **retry later**
- ✅ No resource exhaustion from retry loops

## Troubleshooting

### Problem: Still seeing long retry cycles

**Solution**: Ensure settings are loaded
```bash
# Check environment variables are set
env | grep CELERY

# Verify config in Python
python -c "from app.config import settings; print(settings.celery_task_publish_retry)"
# Should print: False

# Check Celery app config
python -c "from app.tasks.celery_app import celery_app; print(celery_app.conf.task_publish_retry)"
# Should print: False
```

### Problem: Getting connection refused errors

**Solution**: This is expected when Redis is down. The fail-fast behavior is working correctly.

### Problem: Jobs not processing even when Redis is up

**Solution**: Make sure Celery worker is running
```bash
celery -A app.tasks.celery_app worker --loglevel=info
```

## References

- [Celery Configuration Documentation](https://docs.celeryq.dev/en/stable/userguide/configuration.html)
- [Redis Transport Options](https://docs.celeryq.dev/en/stable/getting-started/backends-and-brokers/redis.html)
- [Kombu Connection Retry](https://kombu.readthedocs.io/en/stable/userguide/connections.html)