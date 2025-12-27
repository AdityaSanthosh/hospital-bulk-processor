# Idempotency Key Removed from Response

## What Changed

**Removed** `idempotency_key` from the API response.

### Before
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Job accepted and queued for processing...",
  "total_hospitals": 10,
  "idempotency_key": "abc123..."  // ← Removed
}
```

### After
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Job accepted and queued for processing...",
  "total_hospitals": 10
}
```

## Why?

The idempotency key in the response was **pointless**:

1. ❌ **Server generates it** - Client didn't create it
2. ❌ **Can't be reused** - Based on CSV content hash
3. ❌ **No retry value** - If network fails, client can't use it
4. ❌ **Just noise** - Clutters the response with useless data

## How Idempotency Still Works

### Option 1: Client Provides Key (Explicit)

```bash
curl -X POST /api/v1/hospitals/bulk \
  -H "Idempotency-Key: my-unique-key-123" \
  -F "file=@hospitals.csv"
```

- Client controls the key
- Safe retries with same key
- Server caches response

### Option 2: Server Generates Key (Automatic)

```bash
curl -X POST /api/v1/hospitals/bulk \
  -F "file=@hospitals.csv"
```

- Server generates key from CSV content hash
- Same CSV = same key = deduplicated automatically
- Client doesn't need to know

## Implementation Details

### Server-Side (What Changed)

**Schema:**
```python
class JobSubmitResponse(BaseModel):
    job_id: str
    status: JobStatus
    message: str
    total_hospitals: int
    # idempotency_key: str  ← REMOVED
```

**Service:**
```python
response = JobSubmitResponse(
    job_id=job.job_id,
    status=JobStatus.PENDING,
    message="Job accepted and queued for processing...",
    total_hospitals=len(hospitals),
    # idempotency_key removed from here
)
```

### Server-Side (What Stayed the Same)

- ✅ Idempotency checking still works
- ✅ Server generates key if not provided
- ✅ Cache still prevents duplicate processing
- ✅ Same CSV = same response

**Unchanged logic:**
```python
# Generate key if not provided
if not idempotency_key:
    csv_content = ",".join([f"{h.name}{h.address}" for h in hospitals])
    idempotency_key = generate_idempotency_key(csv_content)

# Check cache (still works)
cached_response = idempotency_store.get(idempotency_key)
if cached_response:
    return JobSubmitResponse(**cached_response)

# Cache response (still works)
idempotency_store.set(idempotency_key, response.model_dump())
```

## Benefits

1. ✅ **Cleaner API** - No unnecessary fields
2. ✅ **Less confusion** - Client doesn't wonder "what do I do with this?"
3. ✅ **Industry standard** - Matches Stripe, AWS, etc.
4. ✅ **Simpler response** - Easier to document and understand

## Real-World Comparison

### Stripe API
```bash
curl -H "Idempotency-Key: abc123" ...

# Response (NO key returned)
{
  "id": "ch_1234",
  "amount": 1000,
  "status": "succeeded"
}
```

### Your API (Now Matches!)
```bash
curl -H "Idempotency-Key: abc123" ...

# Response (NO key returned)
{
  "job_id": "550e8400-...",
  "status": "pending",
  "total_hospitals": 10
}
```

## Migration Guide

If you have clients consuming this API:

### No Changes Needed!

The idempotency key was never useful to clients, so removing it has **no impact** on functionality.

Clients should:
- ✅ Continue sending `Idempotency-Key` header (optional)
- ✅ Use `job_id` to check status
- ✅ Ignore the removed field (it was useless anyway)

## Summary

**The idempotency key is still used internally for deduplication**, but it's no longer cluttering the API response with data clients can't use.

This aligns with industry best practices where:
- Client provides key OR server generates it
- Key is used for cache lookup internally
- Response contains only useful data for the client
