# Idempotency Implementation with Redis

## Overview

Mandatory client-provided idempotency keys stored in Redis for request deduplication only.

## Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ POST /bulk + Idempotency-Key: abc-123
       ▼
┌─────────────────┐
│   FastAPI API   │
└────┬───────┬────┘
     │       │
     │       │ Check cache
     │       ▼
     │  ┌─────────┐
     │  │  Redis  │  idempotency:abc-123 → {job_id, status, ...}
     │  │  (TTL=  │  Auto-expires after 5 minutes
     │  │  5 min) │
     │  └─────────┘
     │
     │ Cache miss → Process request
     ▼
┌─────────────┐
│   Submit    │
│    Job      │
└─────────────┘
```

## Configuration

### Settings (`app/config.py`)
```python
idempotency_cache_ttl: int = 300  # 5 minutes
```

### Environment Variables
```bash
IDEMPOTENCY_CACHE_TTL=300  # 5 minutes
```

## Implementation

### Redis Store (`app/core/idempotency.py`)
```python
class RedisIdempotencyStore:
    """Redis-backed idempotency store with TTL"""
    
    def __init__(self, ttl: int = 300):
        self.ttl = ttl  # 5 minutes
    
    def get(self, key: str) -> Optional[dict]:
        """Get cached response (None if expired or not found)"""
    
    def set(self, key: str, value: dict) -> bool:
        """Cache response with TTL"""
    
    def delete(self, key: str) -> bool:
        """Manually delete cached response"""
```

**Key Features:**
- ✅ Redis storage with automatic TTL expiration
- ✅ Namespaced keys: `idempotency:{key}`
- ✅ JSON serialization
- ✅ Error handling (returns None on Redis failure)
- ✅ Connection pooling

### API Endpoint (`app/api/v1/endpoints/hospitals.py`)
```python
async def bulk_create_hospitals(
    file: UploadFile,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),  # REQUIRED
):
    """
    Idempotency-Key header is REQUIRED.
    Client must generate unique value per upload attempt.
    """
```

**Validation:**
- ❌ Missing header → 422 Unprocessable Entity
- ❌ Empty string → 400 Bad Request
- ✅ Valid key → Proceeds with caching

### Service Layer (`app/services/job_service.py`)
```python
def submit_bulk_job(hospitals, idempotency_key):
    # Check cache
    cached_response = idempotency_store.get(idempotency_key)
    if cached_response:
        return JobSubmitResponse(**cached_response)
    
    # Process request
    job = create_job(hospitals)
    response = JobSubmitResponse(...)
    
    # Cache response
    idempotency_store.set(idempotency_key, response.model_dump())
    
    return response
```

## Client Usage

### Generate Idempotency Key

#### Option 1: UUID (Recommended)
```bash
# Generate UUID
KEY=$(uuidgen)  # macOS/Linux
KEY=$(python -c "import uuid; print(uuid.uuid4())")  # Python

# Use in request
curl -H "Idempotency-Key: $KEY" \
     -F "file=@hospitals.csv" \
     http://localhost:8000/api/v1/hospitals/bulk
```

#### Option 2: Timestamp + Random
```bash
KEY="upload-$(date +%s)-$(openssl rand -hex 4)"
curl -H "Idempotency-Key: $KEY" ...
```

#### Option 3: Semantic (User-specific)
```bash
KEY="batch-user123-$(date +%Y%m%d%H%M%S)"
curl -H "Idempotency-Key: $KEY" ...
```

### Retry Pattern

```python
import uuid
import httpx

def upload_hospitals(file_path, max_retries=3):
    # Generate key ONCE per upload attempt
    idempotency_key = str(uuid.uuid4())
    
    for attempt in range(max_retries):
        try:
            response = httpx.post(
                "http://localhost:8000/api/v1/hospitals/bulk",
                headers={"Idempotency-Key": idempotency_key},  # Same key!
                files={"file": open(file_path, "rb")}
            )
            
            if response.status_code == 202:
                return response.json()
            elif response.status_code in (500, 503):
                # Retry with SAME key
                time.sleep(2 ** attempt)
                continue
            else:
                raise Exception(f"Error: {response.text}")
                
        except httpx.NetworkError:
            # Network error - retry with SAME key
            time.sleep(2 ** attempt)
            continue
    
    raise Exception("Max retries exceeded")
```

## Behavior Examples

### Scenario 1: Network Retry (Success)
```
10:00:00 - Request 1 with key "abc-123"
           → Network timeout
10:00:05 - Request 2 with key "abc-123" (retry)
           → Cache MISS (first request never reached server)
           → Processes job
           → Returns {"job_id": "job-001"}
           → Cached in Redis (TTL: 5 min)
10:00:10 - Request 3 with key "abc-123" (retry)
           → Cache HIT
           → Returns {"job_id": "job-001"} (same response)
           → No duplicate processing ✅
```

### Scenario 2: Accidental Double-Click
```
10:00:00 - User clicks "Upload" with key "xyz-789"
           → Processes job
           → Returns {"job_id": "job-002"}
           → Cached
10:00:01 - User clicks "Upload" again (impatient) with key "xyz-789"
           → Cache HIT
           → Returns {"job_id": "job-002"} (same response)
           → No duplicate job ✅
```

### Scenario 3: Intentional Re-upload
```
10:00:00 - Upload CSV with key "key-1"
           → Processes job
           → Returns {"job_id": "job-003"}
10:10:00 - User uploads SAME CSV with key "key-2" (different key!)
           → Cache MISS (different key)
           → Processes job again
           → Returns {"job_id": "job-004"}
           → Business logic handles duplicate hospitals ✅
```

### Scenario 4: TTL Expiration
```
10:00:00 - Upload with key "old-key"
           → Cached (TTL: 5 min)
10:06:00 - Upload with key "old-key" (same key after 6 minutes)
           → Cache MISS (expired)
           → Processes as new request
           → New job created
```

## Redis Operations

### Check Cached Keys
```bash
# List all idempotency keys
redis-cli KEYS "idempotency:*"

# Get value for specific key
redis-cli GET "idempotency:your-key-here"

# Check TTL
redis-cli TTL "idempotency:your-key-here"
# Returns: seconds remaining (-1 = no expiry, -2 = doesn't exist)
```

### Manual Management
```bash
# Delete specific key (force re-processing)
redis-cli DEL "idempotency:your-key-here"

# Flush all idempotency keys (danger!)
redis-cli --scan --pattern "idempotency:*" | xargs redis-cli DEL

# Set custom TTL
redis-cli EXPIRE "idempotency:your-key" 600  # 10 minutes
```

## Separation of Concerns

### ✅ Idempotency (Technical)
**Purpose:** Prevent duplicate REQUESTS  
**Scope:** Network retries, double-clicks, client errors  
**Storage:** Redis (5-minute TTL)  
**Key:** Client-provided unique identifier  

### ✅ Duplicate Detection (Business Logic)
**Purpose:** Prevent duplicate HOSPITALS in system  
**Scope:** Data integrity, business rules  
**Storage:** External Hospital API validates  
**Key:** Hospital name + address  

### Example
```
Request 1: Key="key-1", CSV=[Hospital A, Hospital B]
→ Creates hospitals
→ Returns: [A: created, B: created]

Request 2: Key="key-1", CSV=[Hospital A, Hospital B] (retry within 5 min)
→ Cache HIT
→ Returns: [A: created, B: created] (same response, no processing)
→ Idempotency worked ✅

Request 3: Key="key-2", CSV=[Hospital A, Hospital B] (different key)
→ Cache MISS
→ Processes again
→ External API says: "Hospital A already exists"
→ Returns: [A: already_exists, B: already_exists]
→ Business logic worked ✅
```

## Error Handling

### Redis Connection Failure
```python
try:
    cached = idempotency_store.get(key)
except Exception as e:
    logger.error(f"Redis error: {e}")
    cached = None  # Proceed without cache

# Application continues to work (degraded mode)
```

### Invalid Key Format
```python
if not idempotency_key or not idempotency_key.strip():
    raise HTTPException(
        status_code=400,
        detail="Idempotency-Key required. Use UUID or unique value."
    )
```

## Monitoring

### Metrics to Track
- ✅ Cache hit rate (idempotency working)
- ✅ Cache miss rate (new requests)
- ✅ Redis connection errors
- ✅ Average TTL at retrieval time

### Logging
```
INFO - Idempotency cache HIT for key: 550e8400...
INFO - Idempotency cache MISS for key: 7f3a2b1c...
INFO - Idempotency cache SET for key: 9d4e5f2a... (TTL: 300s)
ERROR - Redis error on GET: Connection refused
```

## Summary

| Aspect | Implementation |
|--------|----------------|
| **Storage** | Redis with 5-minute TTL |
| **Key Source** | Client-provided (mandatory) |
| **Purpose** | Request deduplication only |
| **Scope** | Network retries, double-clicks |
| **Business Logic** | Separate (handled by worker) |
| **Failure Mode** | Degrades gracefully (no cache) |

**Key Principle:** Idempotency is for request deduplication, NOT for business logic or data validation.
