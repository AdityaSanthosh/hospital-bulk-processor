# Auto-Activation with Graceful Fallback

## Summary

Hybrid approach: **Auto-activate when possible, graceful fallback when not**.

Best of both worlds - convenience of automation with safety of manual control.

---

## Design Philosophy

**Intelligent Activation Strategy:**
- ✅ **Auto-activate** when all succeed (convenient, automatic)
- ✅ **Graceful fallback** when activation fails (no data loss)
- ✅ **Manual control** when needed (flexibility)
- ✅ **No rollback** ever (hospitals persist)

---

## How It Works

### Scenario 1: Perfect Batch (All Succeed + Activation Works)
```
Upload CSV → All hospitals created successfully (100% success)
          ↓
          Try auto-activation
          ↓
          ✅ Activation succeeds
          ↓
          Status: "created_and_activated"
          batch_activated: true
```

**Result:** Fully automated, no manual action needed! 🎉

---

### Scenario 2: All Created but Activation Fails
```
Upload CSV → All hospitals created successfully (100% success)
          ↓
          Try auto-activation
          ↓
          ⚠️  Activation fails (network timeout, API error, etc.)
          ↓
          Status: "created" (NOT "created_and_activated")
          batch_activated: false
          ↓
          Batch persists (NO ROLLBACK)
          ↓
          User can manually activate via PATCH endpoint
```

**Result:** Hospitals safe, user has control to retry activation

---

### Scenario 3: Partial Failures (Some Hospitals Fail)
```
Upload CSV → 8/10 hospitals created, 2 failed
          ↓
          Skip auto-activation (had failures)
          ↓
          Status: "created" for successful ones, "failed" for others
          batch_activated: false
          ↓
          User reviews failures
          ↓
          User decides: Accept 80% success? → Manual activation via PATCH
```

**Result:** User decides if partial success is acceptable

---

### Scenario 4: All Fail
```
Upload CSV → 0/10 hospitals created, all failed
          ↓
          Skip auto-activation (nothing to activate)
          ↓
          Status: "failed" for all
          batch_activated: false
          ↓
          User reviews errors and fixes CSV
```

**Result:** Clear failure, nothing to activate

---

## Benefits Comparison

| Feature | Old (Manual Only) | New (Auto + Fallback) |
|---------|-------------------|----------------------|
| **Convenience** | ❌ Always manual | ✅ Auto when possible |
| **Control** | ✅ Full control | ✅ Full control |
| **Retry-able** | ✅ Can retry | ✅ Can retry |
| **No Data Loss** | ✅ Never rollback | ✅ Never rollback |
| **Graceful Degradation** | N/A | ✅ Falls back smoothly |
| **Best UX** | ❌ Extra step | ✅ Automatic when possible |

---

## Response Structure

### When Auto-Activation Succeeds:
```json
{
  "job_id": "abc-123",
  "status": "completed",
  "result": {
    "batch_id": "550e8400-e29b-41d4-a716-446655440000",
    "total_hospitals": 10,
    "processed_hospitals": 10,
    "failed_hospitals": 0,
    "batch_activated": true,  // ← Auto-activated! ✅
    "hospitals": [
      {
        "row": 1,
        "hospital_id": 123,
        "name": "City Hospital",
        "status": "created_and_activated",  // ← Note the status
        "error_message": null
      },
      // ... more hospitals with "created_and_activated"
    ]
  }
}
```

**What this means:** You're done! No action needed. 🎉

---

### When Auto-Activation Fails:
```json
{
  "job_id": "abc-123",
  "status": "completed",
  "result": {
    "batch_id": "550e8400-e29b-41d4-a716-446655440000",
    "total_hospitals": 10,
    "processed_hospitals": 10,
    "failed_hospitals": 0,
    "batch_activated": false,  // ← Activation failed ⚠️
    "hospitals": [
      {
        "row": 1,
        "hospital_id": 123,
        "name": "City Hospital",
        "status": "created",  // ← Created but NOT activated
        "error_message": null
      },
      // ... more hospitals with "created"
    ]
  }
}
```

**What to do:**
```bash
# Retry activation manually
curl -X PATCH http://localhost:8000/api/v1/hospitals/bulk/batch/550e8400-.../activate
```

---

### When Some Hospitals Fail:
```json
{
  "job_id": "abc-123",
  "status": "completed",
  "result": {
    "batch_id": "550e8400-e29b-41d4-a716-446655440000",
    "total_hospitals": 10,
    "processed_hospitals": 8,
    "failed_hospitals": 2,
    "batch_activated": false,  // ← Not activated (had failures)
    "hospitals": [
      {
        "row": 1,
        "hospital_id": 123,
        "name": "City Hospital",
        "status": "created",  // ← Success
        "error_message": null
      },
      {
        "row": 2,
        "hospital_id": null,
        "name": "Invalid Hospital",
        "status": "failed",  // ← Failure
        "error_message": "Validation error: Invalid address"
      },
      // ... mix of "created" and "failed"
    ]
  }
}
```

**What to do:**
1. Review the failures
2. Decide if 80% success is acceptable
3. If yes: Manually activate the batch
4. If no: Fix errors and resubmit

---

## Hospital Status Values

| Status | Meaning | Activation State | Action Needed |
|--------|---------|------------------|---------------|
| **"created_and_activated"** | Created AND activated | ✅ Active | None, all good |
| **"created"** | Created but NOT activated | ⚠️ Inactive | Manual activation available |
| **"failed"** | Creation failed | ❌ N/A | Fix data and resubmit |

---

## Decision Tree

```
Upload CSV & Create Hospitals
         ↓
All hospitals created successfully?
├─ YES (100% success)
│  ├─ Try auto-activation
│  │  ├─ Activation succeeds?
│  │  │  ├─ YES → ✅ Status: "created_and_activated", batch_activated: true
│  │  │  │         DONE! No action needed.
│  │  │  │
│  │  │  └─ NO → ⚠️ Status: "created", batch_activated: false
│  │  │           Manual activation available via PATCH endpoint
│  │  │           User can retry activation
│
└─ NO (some failures)
   └─ Skip auto-activation
      ├─ Status: Mix of "created" and "failed", batch_activated: false
      ├─ User reviews failures
      └─ User decides: Acceptable? → Manual activation via PATCH
                       Not acceptable? → Fix and resubmit
```

---

## Naming: Why Keep `job_repository`?

**Question:** Should we rename `job_repository` to `batch_repository`?

**Answer:** ❌ **No, keep it as `job_repository`**

### Reasoning:

```
┌─────────────────────────────────────────────────────────┐
│  job_repository (Our System)                            │
│  ├─ Manages: Celery job metadata                        │
│  ├─ Tracks: Job lifecycle (pending → processing → done) │
│  ├─ Stores: Job results (which include batch info)      │
│  └─ Purpose: Track the WORK being done                  │
└─────────────────────────────────────────────────────────┘
                        ↓ creates
┌─────────────────────────────────────────────────────────┐
│  batch (External Hospital API)                          │
│  ├─ Lives on: External Hospital Directory API           │
│  ├─ Created by: HospitalAPIClient                       │
│  ├─ Is a: GROUP of hospitals                            │
│  └─ Purpose: The RESULT of the work                     │
└─────────────────────────────────────────────────────────┘
```

### Analogy:

```
Job = "The work of processing a CSV file"
Batch = "The group of hospitals created by that work"

job_repository tracks the WORK (the job)
External API tracks the BATCHES (the result)
```

### Separation of Concerns:

| Repository | Manages | Storage | Scope |
|------------|---------|---------|-------|
| `job_repository` | Jobs (work units) | Our database/cache | Internal |
| Batch data | Hospital batches | External API | External |

**Conclusion:** `job_repository` is the **correct name**! It manages jobs, not batches. 👍

---

## Implementation Details

### In `app/tasks/tasks.py`:

```python
async def _process_hospitals_async(job_id: str, hospitals_data: List[dict]):
    # 1. Create all hospitals
    results = await _create_hospitals_concurrently(...)
    
    # 2. Calculate results
    failed_count = sum(1 for r in results if r.status == "failed")
    
    # 3. Try auto-activation if all succeeded
    if failed_count == 0:
        try:
            activation_success, _ = await api_client.activate_batch(batch_id)
            
            if activation_success:
                # ✅ Update status to "created_and_activated"
                for result in results:
                    result.status = "created_and_activated"
                batch_activated = True
            else:
                # ⚠️ Keep as "created", no rollback
                batch_activated = False
        except Exception:
            # ⚠️ Keep as "created", no rollback
            batch_activated = False
    else:
        # ℹ️ Had failures, don't auto-activate
        batch_activated = False
    
    # 4. Return result (never rollback)
    return BulkCreateResponse(
        batch_activated=batch_activated,
        hospitals=results,  # Always persist
        ...
    )
```

### Key Points:

1. ✅ **Try auto-activation only if all succeed**
2. ✅ **Catch activation failures gracefully**
3. ✅ **Update status to "created_and_activated" only if activation succeeds**
4. ✅ **Never rollback - hospitals always persist**
5. ✅ **Return clear status for manual intervention**

---

## Logs to Monitor

### Success Path:
```bash
# All created successfully
grep "All hospitals created successfully" logs/

# Auto-activation attempted
grep "Attempting to auto-activate batch" logs/

# Auto-activation succeeded
grep "auto-activated successfully" logs/
```

### Fallback Path:
```bash
# Auto-activation failed
grep "Auto-activation failed" logs/

# Manual activation available
grep "Manual activation available" logs/

# Had failures, no auto-activation
grep "hospitals failed.*NOT activated" logs/
```

### Manual Activation:
```bash
# User manually activating
grep "Activating batch" logs/

# Manual activation succeeded
grep "Batch.*activated successfully" logs/
```

---

## Example Client Code

### JavaScript/TypeScript:

```javascript
async function uploadAndActivate(csvFile) {
  // 1. Upload CSV
  const job = await uploadCSV(csvFile);
  console.log(`Job submitted: ${job.job_id}`);
  
  // 2. Poll for completion
  const result = await pollJobStatus(job.job_id);
  
  // 3. Check activation status
  if (result.result.batch_activated) {
    // ✅ Auto-activated successfully!
    console.log('✅ Success! Batch auto-activated.');
    console.log(`Activated ${result.result.processed_hospitals} hospitals`);
    return { success: true, result };
  }
  
  // 4. Handle fallback scenarios
  if (result.result.failed_hospitals > 0) {
    // Some hospitals failed
    console.warn(
      `⚠️  Partial success: ${result.result.processed_hospitals}/${result.result.total_hospitals} succeeded`
    );
    console.log('Review failures before manually activating');
    
    // Let user decide
    const shouldActivate = await askUser('Activate anyway?');
    if (!shouldActivate) {
      return { success: false, reason: 'User declined partial activation' };
    }
  } else {
    // All succeeded but activation failed
    console.warn('⚠️  Auto-activation failed, retrying manually...');
  }
  
  // 5. Manual activation
  const activation = await activateBatch(result.result.batch_id);
  
  if (activation.activated) {
    console.log('✅ Manually activated successfully!');
    return { success: true, result, manualActivation: true };
  } else {
    console.error('❌ Manual activation failed:', activation.error_message);
    return { success: false, error: activation.error_message };
  }
}

async function uploadCSV(file) {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await fetch('http://localhost:8000/api/v1/hospitals/bulk', {
    method: 'POST',
    headers: {
      'Idempotency-Key': crypto.randomUUID(),
    },
    body: formData,
  });
  
  return response.json();
}

async function pollJobStatus(jobId) {
  while (true) {
    const response = await fetch(`http://localhost:8000/api/v1/hospitals/status/${jobId}`);
    const status = await response.json();
    
    if (status.status === 'completed' || status.status === 'failed') {
      return status;
    }
    
    console.log(`Progress: ${status.progress_percentage}%`);
    await sleep(2000); // Poll every 2 seconds
  }
}

async function activateBatch(batchId) {
  const response = await fetch(
    `http://localhost:8000/api/v1/hospitals/bulk/batch/${batchId}/activate`,
    { method: 'PATCH' }
  );
  return response.json();
}
```

### Python:

```python
import time
import requests
from uuid import uuid4

def upload_and_activate(csv_file_path):
    """Upload CSV and handle auto-activation with fallback"""
    
    # 1. Upload CSV
    with open(csv_file_path, 'rb') as f:
        response = requests.post(
            'http://localhost:8000/api/v1/hospitals/bulk',
            files={'file': f},
            headers={'Idempotency-Key': str(uuid4())},
        )
    job = response.json()
    print(f"Job submitted: {job['job_id']}")
    
    # 2. Poll for completion
    result = poll_job_status(job['job_id'])
    
    # 3. Check activation status
    if result['result']['batch_activated']:
        # ✅ Auto-activated!
        print(f"✅ Success! {result['result']['processed_hospitals']} hospitals activated")
        return {'success': True, 'result': result}
    
    # 4. Handle fallback
    batch_id = result['result']['batch_id']
    failed = result['result']['failed_hospitals']
    
    if failed > 0:
        print(f"⚠️  {failed} hospitals failed. Review before activating.")
        # User decides whether to proceed
        return {'success': False, 'needs_review': True, 'result': result}
    else:
        print("⚠️  Auto-activation failed, retrying manually...")
    
    # 5. Manual activation
    activation = activate_batch(batch_id)
    
    if activation['activated']:
        print("✅ Manually activated successfully!")
        return {'success': True, 'result': result, 'manual': True}
    else:
        print(f"❌ Activation failed: {activation['error_message']}")
        return {'success': False, 'error': activation['error_message']}

def poll_job_status(job_id):
    """Poll job status until completed"""
    while True:
        response = requests.get(f'http://localhost:8000/api/v1/hospitals/status/{job_id}')
        status = response.json()
        
        if status['status'] in ['completed', 'failed']:
            return status
        
        print(f"Progress: {status['progress_percentage']}%")
        time.sleep(2)

def activate_batch(batch_id):
    """Manually activate a batch"""
    response = requests.patch(
        f'http://localhost:8000/api/v1/hospitals/bulk/batch/{batch_id}/activate'
    )
    return response.json()
```

---

## Testing Scenarios

### Test 1: Happy Path (Auto-Activation Success)
```bash
# Create CSV with valid hospitals
cat > test.csv << EOF
name,address,phone
City Hospital,123 Main St,555-0001
County Medical,456 Oak Ave,555-0002
EOF

# Upload
JOB_ID=$(curl -s -X POST http://localhost:8000/api/v1/hospitals/bulk \
  -H "Idempotency-Key: $(uuidgen)" \
  -F "file=@test.csv" | jq -r '.job_id')

# Poll until complete
while [ "$(curl -s http://localhost:8000/api/v1/hospitals/status/$JOB_ID | jq -r '.status')" != "completed" ]; do
  sleep 2
done

# Check result
curl -s http://localhost:8000/api/v1/hospitals/status/$JOB_ID | jq '.result | {
  batch_activated,
  processed_hospitals,
  failed_hospitals
}'

# Expected: batch_activated = true ✅
```

### Test 2: Auto-Activation Fails (Network Issue)
```bash
# Simulate by stopping the external API temporarily
# Or use a batch that triggers activation error

# Check that:
# - batch_activated = false
# - All hospitals have status = "created" (not "created_and_activated")
# - Manual activation endpoint available
```

### Test 3: Partial Failures
```bash
# Create CSV with some invalid data
cat > test.csv << EOF
name,address,phone
Valid Hospital,123 Main St,555-0001
,Invalid Missing Name,555-0002
Another Valid,789 Pine St,555-0003
EOF

# Upload and check:
# - processed_hospitals = 2
# - failed_hospitals = 1
# - batch_activated = false
# - Manual activation available
```

### Test 4: Manual Activation After Failure
```bash
# Get batch_id from failed auto-activation
BATCH_ID=$(curl -s http://localhost:8000/api/v1/hospitals/status/$JOB_ID | jq -r '.result.batch_id')

# Manually activate
curl -X PATCH http://localhost:8000/api/v1/hospitals/bulk/batch/$BATCH_ID/activate

# Should succeed ✅
```

---

## Migration from Manual-Only

### Before (Manual Only):
```javascript
// Old: Always manual activation
const result = await pollJobStatus(jobId);
const activation = await activateBatch(result.result.batch_id);
```

### After (Auto + Fallback):
```javascript
// New: Auto-activate with fallback
const result = await pollJobStatus(jobId);

if (result.result.batch_activated) {
  // ✅ Already activated!
  console.log('Done!');
} else {
  // ⚠️ Fallback to manual
  const activation = await activateBatch(result.result.batch_id);
}
```

**Backward Compatible:** Old code that always calls manual activation will still work (idempotent).

---

## Summary

### What You Get:

| Feature | Benefit |
|---------|---------|
| **Auto-activation** | Convenience - no manual step when everything works |
| **Graceful fallback** | Safety - no data loss if activation fails |
| **Manual control** | Flexibility - user can retry or review before activating |
| **No rollback** | Reliability - hospitals persist regardless of activation |
| **Clear status** | Observability - easy to see what happened |

### Decision Points:

```
batch_activated = true  → ✅ Done! Auto-activated successfully
batch_activated = false + failed_hospitals = 0 → ⚠️  Retry activation manually
batch_activated = false + failed_hospitals > 0 → ℹ️  Review failures, then decide
```

### The Flow:

```
Upload → Create → All succeed? → Try activate
                              → Succeeds? → ✅ Done!
                              → Fails? → ⚠️  Manual fallback
                 → Some fail? → ℹ️  Manual control
```

**Best of all worlds!** 🎯

---

## Quick Reference

| Scenario | batch_activated | Hospital Status | Action |
|----------|----------------|-----------------|--------|
| All good | `true` | `created_and_activated` | ✅ None |
| Auto-activation failed | `false` | `created` | ⚠️  PATCH /activate |
| Had failures | `false` | Mix of `created`/`failed` | ℹ️  Review, then PATCH |
| All failed | `false` | All `failed` | ❌ Fix and resubmit |

---

**Smart automation with safety nets!** 🚀