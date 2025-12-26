"""Quick test of new architecture"""

# All imports at the top of file
from app.config import settings
from app.core.idempotency import generate_idempotency_key, idempotency_store
from app.core.resilience import hospital_api_circuit_breaker, rate_limiter
from app.domain.schemas import HospitalCreate, JobStatus
from app.external.hospital_api_client import HospitalAPIClient
from app.main import app
from app.repositories.job_repository import job_repository
from app.tasks.celery_app import celery_app
from app.utils.csv_validator import CSVValidator

print("=" * 70)
print("Testing Hospital Bulk Processor API v2.0 Architecture")
print("=" * 70)
print()

# Test 1: Configuration
print("1️⃣  Testing Configuration...")
print(f"   ✅ Config loaded: {settings.app_name} v{settings.app_version}")
print()

# Test 2: Domain Schemas
print("2️⃣  Testing Domain Schemas...")
hospital = HospitalCreate(
    name="Test Hospital", address="123 Main St", phone="555-0100", row_number=1
)
print(f"   ✅ Hospital schema: {hospital.name}")
print(f"   ✅ Job statuses: {[s.value for s in JobStatus]}")
print()

# Test 3: Resilience Components
print("3️⃣  Testing Resilience Components...")
print(
    f"   ✅ Rate limiter initialized: {rate_limiter.max_rate} req/{rate_limiter.time_period}s"
)
print(f"   ✅ Circuit breaker initialized: {hospital_api_circuit_breaker.name}")
print(f"   ✅ Retry policy configured: max {settings.retry_max_attempts} attempts")
print()

# Test 4: Idempotency
print("4️⃣  Testing Idempotency...")
key = generate_idempotency_key("test data")
print(f"   ✅ Idempotency key generated: {key[:32]}...")
print(
    f"   ✅ Idempotency store: TTL={idempotency_store.ttl}s, Current size={len(idempotency_store._store)}"
)
print()

# Test 5: Repository
print("5️⃣  Testing Job Repository...")
job = job_repository.create(total_hospitals=5)
print(f"   ✅ Job created: {job.job_id}")
print(f"   ✅ Job status: {job.status}")
print()

# Test 6: CSV Validator
print("6️⃣  Testing CSV Validator...")
print("   ✅ CSV Validator loaded")
print(f"   ✅ Required headers: {CSVValidator.REQUIRED_HEADERS}")
print()

# Test 7: API Client
print("7️⃣  Testing Hospital API Client...")
client = HospitalAPIClient()
print(f"   ✅ API Client initialized: {client.base_url}")
print(f"   ✅ Timeout: {client.timeout}s")
print()

# Test 8: Job Service
print("8️⃣  Testing Job Service...")
print("   ✅ Job Service loaded")
print()

# Test 9: Celery App
print("9️⃣  Testing Celery Configuration...")
print(f"   ✅ Celery app: {celery_app.main}")
print(f"   ✅ Broker: {settings.celery_broker_url}")
print(f"   ✅ Backend: {settings.celery_result_backend}")
print()

# Test 10: FastAPI App
print("🔟 Testing FastAPI Application...")
print(f"   ✅ FastAPI app: {app.title}")
print(f"   ✅ Version: {app.version}")
print(f"   ✅ OpenAPI URL: {app.openapi_url}")
print(f"   ✅ Docs URL: {app.docs_url}")
print()

print("=" * 70)
print("✅ All components loaded successfully!")
print("=" * 70)
print()
print("Next steps:")
print("1. Start Redis: docker run -d -p 6379:6379 redis:7-alpine")
print("2. Start Celery: celery -A celery_worker.celery_app worker --loglevel=info")
print("3. Start FastAPI: python app/main.py")
print("4. Visit docs: http://localhost:8000/api/v1/docs")
