# Quick Start Guide - Hospital Bulk Processor v2.0

## 🚀 Get Running in 5 Minutes

### Prerequisites
```bash
# Check Python version (need 3.10+)
python --version

# Install Redis (choose one)
docker run -d -p 6379:6379 redis:7-alpine    # Docker
brew install redis && brew services start redis  # macOS
sudo apt install redis-server && sudo systemctl start redis  # Linux
```

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Configure Environment
```bash
cp .env.example .env
# Edit .env if you need custom settings
```

### Step 3: Start Everything
```bash
./start_dev.sh
```

That's it! 🎉

---

## 📡 Test the API

### 1. Check Health
```bash
curl http://localhost:8000/health
```

### 2. Upload CSV
```bash
curl -X POST http://localhost:8000/api/v1/hospitals/bulk \
  -F "file=@sample_hospitals.csv" \
  -H "Idempotency-Key: test-123"
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Job accepted and queued for processing...",
  "total_hospitals": 3,
  "idempotency_key": "test-123"
}
```

### 3. Check Status
```bash
curl http://localhost:8000/api/v1/hospitals/status/YOUR_JOB_ID
```

### 4. View API Docs
Open in browser: http://localhost:8000/api/v1/docs

---

## 🎯 Key Features You Get

✅ **Celery** - Distributed background processing  
✅ **Rate Limiting** - 10 req/s to external API  
✅ **Circuit Breaker** - Fails fast when API is down  
✅ **Auto Retry** - 3 attempts with exponential backoff  
✅ **Idempotency** - Safe retries with idempotency keys  
✅ **API Versioning** - `/api/v1/` prefix  

---

## 🔧 Manual Startup (if script doesn't work)

### Terminal 1: Redis
```bash
docker run -d -p 6379:6379 redis:7-alpine
```

### Terminal 2: Celery Worker
```bash
celery -A celery_worker.celery_app worker --loglevel=info
```

### Terminal 3: FastAPI Server
```bash
python app/main.py
# or
uvicorn app.main:app --reload --port 8000
```

---

## 📦 Project Structure

```
app/
├── api/v1/endpoints/      # API endpoints
├── core/                  # Resilience patterns
├── domain/                # Schemas & business logic
├── services/              # Application services & use cases
├── tasks/                 # Background tasks (Celery)
├── external/              # External API clients
├── repositories/          # Data access layer
└── utils/                 # CSV validator
```

---

## 🐛 Troubleshooting

### Redis not running?
```bash
# Check if Redis is running
redis-cli ping
# Should return: PONG

# If not, start it
docker run -d -p 6379:6379 redis:7-alpine
```

### Port 8000 already in use?
```bash
# Change port in .env
PORT=8001

# Or kill the process
lsof -ti:8000 | xargs kill -9
```

### Celery can't connect?
```bash
# Check Redis connection
redis-cli ping

# Check Celery broker URL in .env
CELERY_BROKER_URL=redis://localhost:6379/0
```

---

## 📚 More Information

- **Architecture**: See [ARCHITECTURE.md](ARCHITECTURE.md)
- **Migration Guide**: See [MIGRATION_SUMMARY.md](MIGRATION_SUMMARY.md)
- **Full README**: See [README.md](README.md)
- **API Docs**: http://localhost:8000/api/v1/docs

---

## 🎉 You're Done!

Your production-ready API with:
- ✅ Distributed processing (Celery)
- ✅ Fault tolerance (Circuit Breaker)
- ✅ Safe retries (Idempotency)
- ✅ Rate limiting
- ✅ Clean architecture

Happy coding! 🚀
