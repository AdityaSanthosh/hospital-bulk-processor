# Resilience Quick Reference Card

## 🎯 What Changed?

### 1. Retry Logic: Custom → Tenacity
- ❌ **Before**: `@RetryPolicy.with_retry(max_attempts=3)`
- ✅ **After**: `@retry(stop=stop_after_attempt(3), wait=wait_exponential(...))`

### 2. Circuit Breaker: In-Memory → Redis-Backed
- ❌ **Before**: Each worker has separate circuit breaker state
- ✅ **After**: All workers share circuit breaker state via Redis

---

## 📊 Key Metrics to Monitor

```bash
# Circuit breaker state
redis-cli GET "pybreaker:state"           # closed | open | half-open

# Failure counter  
redis-cli GET "pybreaker:fail_counter"    # 0-5

# Watch for state changes in logs
grep "Circuit breaker.*state changed" logs/

# Watch for retry attempts in logs
grep "Retrying.*attempt" logs/
```

---

## 🔥 Quick Tests

### Test 1: Verify Redis-Backed Storage
```bash
python -c "
from app.core.resilience import hospital_api_circuit_breaker
print(type(hospital_api_circuit_breaker.breaker._state_storage).__name__)
"
# Expected: CircuitRedisStorage
```

### Test 2: Verify Tenacity Decorator
```bash
python -c "
from app.external.hospital_api_client import HospitalAPIClient
client = HospitalAPIClient()
print(hasattr(client.create_hospital, 'retry'))
"
# Expected: True
```

### Test 3: Check Redis Keys
```bash
redis-cli KEYS "pybreaker:*"
# Expected: 1) "pybreaker:state" 2) "pybreaker:fail_counter"
```

---

## 🎛️ Configuration

All in `app/config.py` or `.env`:

```bash
# Retry (tenacity)
RETRY_MAX_ATTEMPTS=3
RETRY_MIN_WAIT=2
RETRY_MAX_WAIT=10

# Circuit Breaker (Redis-backed)
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_RECOVERY_TIMEOUT=60

# Rate Limiting
RATE_LIMIT_REQUESTS=10
RATE_LIMIT_PERIOD=1.0

# Redis (shared with Celery)
CELERY_BROKER_URL=redis://localhost:6379/0
```

---

## 🚨 Troubleshooting

### Problem: Circuit breaker using in-memory storage
```bash
# Check Redis connection
redis-cli ping

# Check logs for connection errors
grep "Failed to connect to Redis" logs/
```

### Problem: No retry logs appearing
```bash
# Retries only log on 2nd+ attempt
# First attempt doesn't log (it's not a retry yet)
```

### Problem: Circuit breaker state not shared
```bash
# Verify storage type
python -c "
from app.core.resilience import hospital_api_circuit_breaker
print(type(hospital_api_circuit_breaker.breaker._state_storage).__name__)
"
# Should be: CircuitRedisStorage
```

---

## 🔄 Deployment

1. **Pull latest code**
2. **No DB migrations needed** (no schema changes)
3. **Restart Celery workers**:
   ```bash
   # Stop workers
   pkill -f "celery worker"
   
   # Start workers
   celery -A app.celery_app.celery_app worker --loglevel=info
   ```
4. **Restart FastAPI** (optional, but recommended):
   ```bash
   # Development
   uvicorn app.main:app --reload
   
   # Production
   systemctl restart your-app-service
   ```

---

## 📚 Documentation Files

- `RESILIENCE_IMPROVEMENTS_SUMMARY.md` - Complete overview of both changes
- `REDIS_CIRCUIT_BREAKER_IMPLEMENTATION.md` - Deep dive on Redis-backed circuit breaker
- `README.md` - Updated with tenacity examples
- `ARCHITECTURE.md` - Updated resilience patterns documentation

---

## 💡 Key Takeaways

1. **No breaking changes** - Same API, better implementation
2. **Redis already required** - You use it for Celery anyway
3. **10x better** - 5 failures instead of 5 × workers
4. **Production ready** - Graceful fallbacks built-in
5. **Zero config changes** - Same settings, just restart workers

---

## 📞 Need Help?

Check the logs:
```bash
# Circuit breaker events
grep "Circuit breaker" logs/ | tail -20

# Retry attempts  
grep "Retrying" logs/ | tail -20

# Redis connection issues
grep "Redis" logs/ | grep -i error
```

Monitor Redis:
```bash
# Real-time monitoring
redis-cli MONITOR | grep pybreaker

# State changes
watch -n 1 'redis-cli GET "pybreaker:state"'
```

---

## ✅ Success Checklist

- [ ] Redis is running (`redis-cli ping`)
- [ ] Circuit breaker using `CircuitRedisStorage` 
- [ ] Retry decorators from `tenacity` (not `RetryPolicy`)
- [ ] All workers restarted
- [ ] Logs show "Redis connection established for circuit breaker"
- [ ] Redis keys `pybreaker:*` exist
- [ ] No errors in diagnostics (`python -m pytest` or check imports)

**All green? You're good to go!** 🚀
