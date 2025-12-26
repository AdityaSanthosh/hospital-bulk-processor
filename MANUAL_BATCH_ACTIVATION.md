# Manual Batch Activation Implementation

## Summary

Removed automatic batch activation and rollback logic. Instead, batch activation is now a **manual, explicit step** controlled by the API consumer via a new endpoint.

## Design Philosophy

**Separation of Concerns**: Creation and activation are separate operations
- ✅ **Create**: Bulk create hospitals → Get batch_id
- ✅ **Review**: Check results, verify success rate
- ✅ **Activate**: Manually activate when ready via PATCH endpoint

## What Changed

### Before (Automatic):
```
Upload CSV → Process → All succeed? → Auto-activate
                     ↓ Any fail? → Auto-rollback (DELETE batch)
```

**Problems:**
- ❌ No control over activation
- ❌ Automatic rollback deletes good hospitals too
- ❌ Can't review results before activation
- ❌ Activation failure = total failure

### After (Manual):
```
Upload CSV → Process → Return batch_id (always)
                     ↓
            Consumer reviews results
                     ↓
            Consumer calls PATCH /activate (when ready)
```

**Benefits:**
- ✅ Full control over activation timing
- ✅ Review results before activating
- ✅ No automatic rollback (hospitals persist)
- ✅ Activation is independent operation
- ✅ Can retry activation without reprocessing

---

## New Workflow

### Step 1: Upload CSV
```bash
curl -X POST http://localhost:8000/api/v1/hospitals/bulk \
     -H "Idempotency-Key: $(uuidgen)" \
     -F "file=@hospitals.csv"
```

**Response:**
```json
{
  "job_id": "abc-123",
  "status": "pending",
  "message": "Job submitted successfully",
  "total_hospitals": 10
}
```

### Step 2: Poll for Completion
```bash
curl http://localhost:8000/api/v1/hospitals/status/abc-123
```

**Response (completed):**
```json
{
  "job_id": "abc-123",
  "status": "completed",
  "total_hospitals": 10,
  "processed_hospitals": 10,
  "failed_hospitals": 0,
  "progress_percentage": 100.0,
  "result": {
    "batch_id": "550e8400-e29b-41d4-a716-446655440000",
    "total_hospitals": 10,
    "processed_hospitals": 10,
    "failed_hospitals": 0,
    "batch_activated": false,  // ← Always false now
    "hospitals": [...]
  }
}
```

### Step 3: Review Results
```bash
# Check the results
# - How many succeeded?
# - How many failed?
# - Review failed_hospitals array
# - Decide if acceptable to activate
```

### Step 4: Activate Batch
```bash
BATCH_ID="550e8400-e29b-41d4-a716-446655440000"

curl -X PATCH http://localhost:8000/api/v1/hospitals/bulk/batch/$BATCH_ID/activate
```

**Response:**
```json
{
  "batch_id": "550e8400-e29b-41d4-a716-446655440000",
  "activated": true,
  "message": "Batch activated successfully"
}
```

---

## New Endpoint

### PATCH `/api/v1/hospitals/bulk/batch/{batch_id}/activate`

**Purpose:** Manually activate a batch of hospitals

**Request:**
```bash
PATCH /api/v1/hospitals/bulk/batch/550e8400-e29b-41d4-a716-446655440000/activate
```

**Response (Success):**
```json
{
  "batch_id": "550e8400-e29b-41d4-a716-446655440000",
  "activated": true,
  "message": "Batch activated successfully",
  "error_message": null
}
```

**Response (Failure):**
```json
{
  "batch_id": "550e8400-e29b-41d4-a716-446655440000",
  "activated": false,
  "message": "Batch activation failed",
  "error_message": "Batch not found or already active"
}
```

**Features:**
- ✅ Idempotent (safe to call multiple times)
- ✅ Uses existing circuit breaker + retry logic
- ✅ Returns clear success/failure status
- ✅ Independent of job processing

---

## Changes to Processing Logic

### `app/tasks/tasks.py`

**Removed:**
```python
# OLD: Automatic activation
if failed_count == 0:
    activation_success, _ = await api_client.activate_batch(batch_id)
    if activation_success:
        batch_activated = True
    else:
        # Rollback on activation failure
        await api_client.delete_batch(batch_id)
else:
    # Rollback on processing failures
    await api_client.delete_batch(batch_id)
```

**New:**
```python
# NEW: No automatic activation, no rollback
bulk_response = BulkCreateResponse(
    batch_id=batch_id,
    total_hospitals=len(hospitals_data),
    processed_hospitals=success_count,
    failed_hospitals=failed_count,
    processing_time_seconds=round(processing_time, 2),
    batch_activated=False,  # Always false, manual activation required
    hospitals=results,
)
```

**Key Changes:**
1. ❌ Removed `activate_batch()` call from processing
2. ❌ Removed `delete_batch()` rollback logic
3. ✅ Always set `batch_activated=False`
4. ✅ Always complete job successfully (even with failures)
5. ✅ Batch persists regardless of failures

---

## Schema Changes

### `app/domain/schemas.py`

**Added:**
```python
class BatchActivateResponse(BaseModel):
    """Response for batch activation"""
    
    batch_id: UUID
    activated: bool
    message: str
    error_message: Optional[str] = None
```

**Updated:**
```python
class BulkCreateResponse(BaseModel):
    batch_activated: bool  # Always False now (manual activation required)
```

---

## Decision Matrix: When to Activate?

| Scenario | Failed Count | Activate? | Reason |
|----------|--------------|-----------|--------|
| **Perfect batch** | 0 | ✅ Yes | All succeeded |
| **Few failures** | 1-2 | ⚠️ Maybe | Acceptable loss? |
| **Many failures** | 5+ | ❌ No | Too many errors |
| **All failures** | All | ❌ No | Nothing to activate |

**You decide based on your business requirements!**

---

## Benefits

### 1. **Control & Flexibility**
- Review results before committing
- Decide activation based on success rate
- Can investigate failures first

### 2. **No Data Loss**
- Successfully created hospitals persist
- No automatic rollback
- Can fix individual failures later

### 3. **Retry-able Activation**
- Activation failure doesn't affect created hospitals
- Can retry activation without reprocessing CSV
- Idempotent activation endpoint

### 4. **Clearer Semantics**
- Creation = persist hospitals
- Activation = make them active
- Separate concerns, separate endpoints

### 5. **Better Error Handling**
- Creation errors vs activation errors are distinct
- Can handle each type differently
- More granular control

---

## Migration Notes

### Breaking Changes
- ✅ **API remains backward compatible** (same endpoints)
- ⚠️ **Behavior change**: `batch_activated` always `false` in job result
- ⚠️ **New step required**: Must call activation endpoint

### Client Updates Required

**Before (old clients):**
```javascript
// Old: Wait for job, assume activated
const jobResult = await pollJobStatus(jobId);
if (jobResult.status === 'completed') {
  // Assume hospitals are active
  console.log('Done!');
}
```

**After (new clients):**
```javascript
// New: Wait for job, then activate
const jobResult = await pollJobStatus(jobId);
if (jobResult.status === 'completed') {
  const batchId = jobResult.result.batch_id;
  
  // Review results
  if (jobResult.result.failed_hospitals === 0) {
    // Activate batch
    const activation = await activateBatch(batchId);
    console.log('Activated!', activation);
  } else {
    console.log('Some failures, review before activating');
  }
}
```

---

## Testing

### Test Scenario 1: Happy Path
```bash
# 1. Upload
JOB_ID=$(curl -X POST http://localhost:8000/api/v1/hospitals/bulk \
  -H "Idempotency-Key: $(uuidgen)" \
  -F "file=@hospitals.csv" | jq -r '.job_id')

# 2. Wait for completion
while true; do
  STATUS=$(curl http://localhost:8000/api/v1/hospitals/status/$JOB_ID | jq -r '.status')
  if [ "$STATUS" = "completed" ]; then break; fi
  sleep 2
done

# 3. Get batch ID
BATCH_ID=$(curl http://localhost:8000/api/v1/hospitals/status/$JOB_ID | jq -r '.result.batch_id')

# 4. Activate
curl -X PATCH http://localhost:8000/api/v1/hospitals/bulk/batch/$BATCH_ID/activate
```

### Test Scenario 2: Partial Failures
```bash
# Same as above, but check failed count first
FAILED=$(curl http://localhost:8000/api/v1/hospitals/status/$JOB_ID | jq -r '.result.failed_hospitals')

if [ "$FAILED" -eq 0 ]; then
  echo "All succeeded, activating..."
  curl -X PATCH http://localhost:8000/api/v1/hospitals/bulk/batch/$BATCH_ID/activate
else
  echo "Some failures ($FAILED), review before activating"
fi
```

### Test Scenario 3: Idempotent Activation
```bash
# Activate twice (should be safe)
curl -X PATCH http://localhost:8000/api/v1/hospitals/bulk/batch/$BATCH_ID/activate
curl -X PATCH http://localhost:8000/api/v1/hospitals/bulk/batch/$BATCH_ID/activate
# Both should succeed
```

---

## Monitoring

### Metrics to Track

1. **Activation Rate**: % of batches activated vs created
2. **Activation Latency**: Time between job completion and activation
3. **Manual Review Time**: Time users spend reviewing before activating
4. **Activation Failures**: How often activation fails

### Logs to Watch

```bash
# Job completion
grep "Job.*completed.*ready for activation" logs/

# Activation attempts
grep "Activating batch" logs/

# Activation success
grep "Batch.*activated successfully" logs/

# Activation failures
grep "Failed to activate batch" logs/
```

---

## Future Enhancements

1. **Batch Status Endpoint**: `GET /batches/{batch_id}/status`
   - Check if batch is activated
   - See which hospitals are in the batch

2. **Rollback Endpoint**: `DELETE /batches/{batch_id}`
   - Manual rollback if needed
   - Delete entire batch

3. **Partial Activation**: Activate only successful hospitals
   - Skip failed ones
   - More granular control

4. **Auto-activation Config**: Optional auto-activation flag
   - For clients that want old behavior
   - Configurable per request

---

## Documentation Updates

Updated files:
- ✅ `README.md` - Added manual activation workflow
- ✅ `ARCHITECTURE.md` - Updated processing flow diagram
- ✅ API endpoint docstrings - Added activation step
- ✅ OpenAPI/Swagger - New endpoint documented

---

## Summary

**What You Get:**
- ✅ Manual control over batch activation
- ✅ No automatic rollback (data persists)
- ✅ Review results before committing
- ✅ Retry-able activation
- ✅ Clearer separation of concerns

**What You Must Do:**
- ⚠️ Call activation endpoint after job completes
- ⚠️ Review results before activating
- ⚠️ Handle activation failures separately

**The Endpoint:**
```
PATCH /api/v1/hospitals/bulk/batch/{batch_id}/activate
```

**Simple as that!** 🚀
