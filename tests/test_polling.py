"""
Integration Tests for Polling Endpoints
Tests for progress tracking and job status endpoints
"""

import asyncio
import time
from uuid import uuid4

import pytest

from app.job_manager import JobManager, JobStatus
from app.models import BulkCreateResponse


@pytest.mark.polling
@pytest.mark.integration
class TestPollingEndpoints:
    """Test polling endpoint functionality"""

    @pytest.mark.asyncio
    async def test_upload_returns_job_id(self, async_client, sample_csv_file):
        """Test that CSV upload returns a job ID"""
        with open(sample_csv_file, "rb") as f:
            response = await async_client.post(
                "/hospitals/bulk",
                files={"file": ("test.csv", f, "text/csv")},
            )

        assert response.status_code == 202
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "pending"
        assert data["total_hospitals"] == 3

    @pytest.mark.asyncio
    async def test_get_job_status_pending(self, test_job_manager):
        """Test getting status of a pending job"""
        job = test_job_manager.create_job(total_hospitals=10)

        status = test_job_manager.get_job_status(job.job_id)

        assert status is not None
        assert status.status == JobStatus.PENDING
        assert status.progress_percentage == 0.0

    @pytest.mark.asyncio
    async def test_get_job_status_processing(self, test_job_manager):
        """Test getting status of a processing job"""
        job = test_job_manager.create_job(total_hospitals=10)
        test_job_manager.update_job_status(job.job_id, JobStatus.PROCESSING)

        # Simulate some progress
        for i in range(5):
            test_job_manager.update_job_progress(
                job.job_id, f"Hospital {i + 1}", success=True
            )

        status = test_job_manager.get_job_status(job.job_id)

        assert status.status == JobStatus.PROCESSING
        assert status.processed_hospitals == 5
        assert status.progress_percentage == 50.0
        assert status.estimated_time_remaining_seconds is not None

    @pytest.mark.asyncio
    async def test_get_job_status_completed(self, test_job_manager):
        """Test getting status of a completed job"""
        job = test_job_manager.create_job(total_hospitals=3)
        test_job_manager.update_job_status(job.job_id, JobStatus.PROCESSING)

        # Complete all hospitals
        for i in range(3):
            test_job_manager.update_job_progress(
                job.job_id, f"Hospital {i + 1}", success=True
            )

        # Set result and mark complete
        result = BulkCreateResponse(
            batch_id=uuid4(),
            total_hospitals=3,
            processed_hospitals=3,
            failed_hospitals=0,
            processing_time_seconds=1.5,
            batch_activated=True,
            hospitals=[],
        )
        test_job_manager.set_job_result(job.job_id, result)
        test_job_manager.update_job_status(job.job_id, JobStatus.COMPLETED)

        status = test_job_manager.get_job_status(job.job_id)

        assert status.status == JobStatus.COMPLETED
        assert status.progress_percentage == 100.0
        assert status.result is not None

    @pytest.mark.asyncio
    async def test_get_job_status_failed(self, test_job_manager):
        """Test getting status of a failed job"""
        job = test_job_manager.create_job(total_hospitals=10)
        test_job_manager.set_job_error(job.job_id, "Connection timeout")

        status = test_job_manager.get_job_status(job.job_id)

        assert status.status == JobStatus.FAILED
        assert status.error == "Connection timeout"

    @pytest.mark.asyncio
    async def test_get_job_status_not_found(self, async_client):
        """Test getting status of non-existent job"""
        response = await async_client.get("/hospitals/bulk/status/nonexistent-id")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_poll_job_until_completion(self, async_client, sample_csv_file):
        """Test polling a job until completion"""
        # Upload CSV
        with open(sample_csv_file, "rb") as f:
            upload_response = await async_client.post(
                "/hospitals/bulk",
                files={"file": ("test.csv", f, "text/csv")},
            )

        job_id = upload_response.json()["job_id"]

        # Poll until completion (with timeout)
        max_attempts = 30
        attempt = 0
        final_status = None

        while attempt < max_attempts:
            response = await async_client.get(f"/hospitals/bulk/status/{job_id}")
            assert response.status_code == 200

            status = response.json()
            final_status = status

            if status["status"] in ["completed", "failed"]:
                break

            await asyncio.sleep(0.5)
            attempt += 1

        assert final_status is not None
        assert final_status["status"] in ["completed", "failed"]

    @pytest.mark.asyncio
    async def test_progress_updates_during_processing(self, test_job_manager):
        """Test that progress updates are tracked correctly"""
        job = test_job_manager.create_job(total_hospitals=10)
        test_job_manager.update_job_status(job.job_id, JobStatus.PROCESSING)

        # Simulate processing with progress updates
        hospitals = [f"Hospital {i + 1}" for i in range(10)]

        for i, hospital in enumerate(hospitals):
            test_job_manager.update_job_progress(job.job_id, hospital, success=True)

            status = test_job_manager.get_job_status(job.job_id)
            assert status.processed_hospitals == i + 1
            assert status.current_hospital == hospital
            assert 0 <= status.progress_percentage <= 100

    @pytest.mark.asyncio
    async def test_recent_updates_in_status(self, test_job_manager):
        """Test that recent updates are included in status"""
        job = test_job_manager.create_job(total_hospitals=10)
        test_job_manager.update_job_status(job.job_id, JobStatus.PROCESSING)

        # Process several hospitals
        for i in range(10):
            test_job_manager.update_job_progress(
                job.job_id, f"Hospital {i + 1}", success=True
            )

        status = test_job_manager.get_job_status(job.job_id)

        # Should have recent updates (last 5)
        assert len(status.recent_updates) == 5
        assert status.recent_updates[-1].hospital_name == "Hospital 10"

    @pytest.mark.asyncio
    async def test_estimated_time_remaining(self, test_job_manager):
        """Test estimated time remaining calculation"""
        job = test_job_manager.create_job(total_hospitals=10)
        test_job_manager.update_job_status(job.job_id, JobStatus.PROCESSING)

        # Simulate some processing time
        job.start_time = time.time() - 10  # Started 10 seconds ago

        # Process half
        for i in range(5):
            test_job_manager.update_job_progress(
                job.job_id, f"Hospital {i + 1}", success=True
            )

        status = test_job_manager.get_job_status(job.job_id)

        # Should have ETA (approximately 10 seconds remaining)
        assert status.estimated_time_remaining_seconds is not None
        assert 5 <= status.estimated_time_remaining_seconds <= 15

    @pytest.mark.asyncio
    async def test_get_all_jobs_endpoint(self, async_client):
        """Test getting all jobs"""
        response = await async_client.get("/hospitals/bulk/jobs")

        assert response.status_code == 200
        data = response.json()
        assert "total_jobs" in data
        assert "stats" in data
        assert "jobs" in data

    @pytest.mark.asyncio
    async def test_multiple_concurrent_jobs(self, test_job_manager):
        """Test managing multiple concurrent jobs"""
        # Create multiple jobs
        jobs = []
        for i in range(5):
            job = test_job_manager.create_job(total_hospitals=10)
            test_job_manager.update_job_status(job.job_id, JobStatus.PROCESSING)
            jobs.append(job)

        # Verify all jobs are tracked
        assert len(test_job_manager.jobs) == 5
        assert test_job_manager.get_active_jobs_count() == 5

        # Complete some jobs
        test_job_manager.update_job_status(jobs[0].job_id, JobStatus.COMPLETED)
        test_job_manager.update_job_status(jobs[1].job_id, JobStatus.COMPLETED)

        assert test_job_manager.get_active_jobs_count() == 3

        stats = test_job_manager.get_stats()
        assert stats["processing_jobs"] == 3
        assert stats["completed_jobs"] == 2

    @pytest.mark.asyncio
    async def test_job_with_failures(self, test_job_manager):
        """Test job tracking with some failures"""
        job = test_job_manager.create_job(total_hospitals=10)
        test_job_manager.update_job_status(job.job_id, JobStatus.PROCESSING)

        # Process with some failures
        for i in range(10):
            success = i % 3 != 0  # Fail every 3rd hospital
            test_job_manager.update_job_progress(
                job.job_id,
                f"Hospital {i + 1}",
                success=success,
                error_message="API timeout" if not success else None,
            )

        status = test_job_manager.get_job_status(job.job_id)

        assert status.processed_hospitals == 10
        assert status.failed_hospitals == 4  # Failed on 0, 3, 6, 9

    @pytest.mark.asyncio
    async def test_health_check_includes_job_stats(self, async_client):
        """Test that health check includes job statistics"""
        response = await async_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "job_stats" in data
        assert "total_jobs" in data["job_stats"]

    @pytest.mark.asyncio
    async def test_root_endpoint_includes_polling_info(self, async_client):
        """Test that root endpoint includes polling information"""
        response = await async_client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "endpoints" in data
        assert "job_status" in data["endpoints"]
        assert "features" in data
        assert data["features"]["progress_tracking"] is True

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_full_upload_and_poll_workflow(
        self, async_client, sample_csv_file, mock_successful_api_calls
    ):
        """Test complete workflow: upload, poll, and get result"""
        # Step 1: Upload CSV
        with open(sample_csv_file, "rb") as f:
            upload_response = await async_client.post(
                "/hospitals/bulk",
                files={"file": ("test.csv", f, "text/csv")},
            )

        assert upload_response.status_code == 202
        job_id = upload_response.json()["job_id"]

        # Step 2: Immediate status check (should be pending or processing)
        status_response = await async_client.get(f"/hospitals/bulk/status/{job_id}")
        assert status_response.status_code == 200
        initial_status = status_response.json()
        assert initial_status["status"] in ["pending", "processing"]

        # Step 3: Poll until completion
        max_polls = 60
        polls = 0
        final_status = None

        while polls < max_polls:
            await asyncio.sleep(1)
            status_response = await async_client.get(f"/hospitals/bulk/status/{job_id}")

            if status_response.status_code == 200:
                status = status_response.json()
                final_status = status

                # Check progress is increasing
                if status["status"] == "processing":
                    assert 0 <= status["progress_percentage"] <= 100

                # Break if completed or failed
                if status["status"] in ["completed", "failed"]:
                    break

            polls += 1

        # Step 4: Verify final status
        assert final_status is not None
        assert (
            final_status["progress_percentage"] == 100.0
            or final_status["status"] == "failed"
        )

        # Step 5: If completed, verify result is present
        if final_status["status"] == "completed":
            assert final_status["result"] is not None
            assert final_status["result"]["batch_id"] is not None


@pytest.mark.polling
class TestPollingPerformance:
    """Test polling endpoint performance"""

    @pytest.mark.asyncio
    async def test_status_endpoint_response_time(self, test_job_manager):
        """Test that status endpoint responds quickly"""
        job = test_job_manager.create_job(total_hospitals=10)

        start = time.time()
        status = test_job_manager.get_job_status(job.job_id)
        elapsed = time.time() - start

        assert status is not None
        assert elapsed < 0.1  # Should respond in less than 100ms

    @pytest.mark.asyncio
    async def test_multiple_status_checks(self, test_job_manager):
        """Test multiple rapid status checks"""
        job = test_job_manager.create_job(total_hospitals=10)

        # Make 100 rapid status checks
        start = time.time()
        for _ in range(100):
            status = test_job_manager.get_job_status(job.job_id)
            assert status is not None

        elapsed = time.time() - start
        assert elapsed < 1.0  # 100 checks in less than 1 second


@pytest.mark.polling
class TestJobCleanup:
    """Test job cleanup functionality"""

    @pytest.mark.asyncio
    async def test_old_jobs_cleanup(self):
        """Test that old completed jobs are cleaned up"""
        manager = JobManager(max_jobs=5, job_ttl_seconds=1)

        # Create 10 completed jobs
        for i in range(10):
            job = manager.create_job(total_hospitals=5)
            manager.update_job_status(job.job_id, JobStatus.COMPLETED)

        # Should only keep max_jobs
        assert len(manager.jobs) <= 5

    @pytest.mark.asyncio
    async def test_active_jobs_not_cleaned(self):
        """Test that active jobs are not cleaned up"""
        manager = JobManager(max_jobs=5, job_ttl_seconds=1)

        # Create 10 processing jobs
        for i in range(10):
            job = manager.create_job(total_hospitals=5)
            manager.update_job_status(job.job_id, JobStatus.PROCESSING)

        # All should be kept (they're active)
        assert len(manager.jobs) == 10


@pytest.mark.polling
class TestErrorScenarios:
    """Test error handling in polling"""

    @pytest.mark.asyncio
    async def test_job_expires_during_polling(self, test_job_manager):
        """Test handling of expired jobs"""
        job = test_job_manager.create_job(total_hospitals=10)
        job_id = job.job_id

        # Manually remove job (simulating expiration)
        del test_job_manager.jobs[job_id]

        # Status should return None
        status = test_job_manager.get_job_status(job_id)
        assert status is None

    @pytest.mark.asyncio
    async def test_invalid_job_id_format(self, async_client):
        """Test status endpoint with invalid job ID format"""
        response = await async_client.get("/hospitals/bulk/status/invalid-id-format")

        # Should return 404 (not found)
        assert response.status_code == 404
