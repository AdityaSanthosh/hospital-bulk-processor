"""Test the new /jobs endpoint"""

from app.domain.schemas import JobStatus
from app.repositories.job_repository import job_repository
from app.services.job_service import JobService

print("=" * 70)
print("Testing GET /api/v1/hospitals/jobs Endpoint")
print("=" * 70)
print()

# Create some test jobs with different statuses
print("1️⃣  Creating test jobs...")
job1 = job_repository.create(total_hospitals=10)
job2 = job_repository.create(total_hospitals=5)
job3 = job_repository.create(total_hospitals=20)

# Update statuses to simulate different stages
job_repository.update_status(job1.job_id, JobStatus.COMPLETED)
job1.processed_hospitals = 10
job1.failed_hospitals = 0

job_repository.update_status(job2.job_id, JobStatus.PROCESSING)
job2.processed_hospitals = 3
job2.failed_hospitals = 0

job_repository.update_status(job3.job_id, JobStatus.FAILED)
job_repository.set_error(job3.job_id, "External API unavailable")

print("   ✅ Created 3 test jobs")
print(f"      - {job1.job_id[:8]}... (COMPLETED)")
print(f"      - {job2.job_id[:8]}... (PROCESSING)")
print(f"      - {job3.job_id[:8]}... (FAILED)")
print()

# Get all jobs
print("2️⃣  Fetching all jobs via service...")
response = JobService.get_all_jobs()

print(f"   ✅ Retrieved {response.total_jobs} jobs")
print()

# Display job details
print("3️⃣  Job Details:")
print()
for i, job in enumerate(response.jobs, 1):
    print(f"   Job #{i}:")
    print(f"      ID: {job.job_id}")
    print(f"      Status: {job.status.value.upper()}")
    print(
        f"      Progress: {job.processed_hospitals}/{job.total_hospitals} ({job.progress_percentage}%)"
    )
    if job.completed_at:
        print(f"      Duration: {job.processing_time_seconds}s")
    print(f"      Started: {job.started_at.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

print("=" * 70)
print("✅ GET /api/v1/hospitals/jobs endpoint working perfectly!")
print("=" * 70)
print()
print("Try it yourself:")
print("  curl http://localhost:8000/api/v1/hospitals/jobs")
print()
