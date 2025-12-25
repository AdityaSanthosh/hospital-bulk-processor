"""
Unit Tests for Hospital Bulk Processor
Tests for models, utilities, and basic functionality
"""

from datetime import datetime
from uuid import uuid4

import pytest

from app.job_manager import Job, JobManager
from app.models import (
    BulkCreateResponse,
    HospitalCreateRequest,
    HospitalProcessingResult,
    HospitalResponse,
    JobStatus,
    JobStatusResponse,
    JobSubmitResponse,
)
from app.utils import CSVValidator


class TestModels:
    """Test Pydantic models"""

    def test_hospital_create_request(self):
        """Test HospitalCreateRequest model"""
        batch_id = uuid4()
        hospital = HospitalCreateRequest(
            name="Test Hospital",
            address="123 Test St",
            phone="555-0000",
            creation_batch_id=batch_id,
        )

        assert hospital.name == "Test Hospital"
        assert hospital.address == "123 Test St"
        assert hospital.phone == "555-0000"
        assert hospital.creation_batch_id == batch_id

    def test_hospital_response(self):
        """Test HospitalResponse model"""
        batch_id = uuid4()
        created_at = datetime.datetime.now(datetime.timezone.utc)

        hospital = HospitalResponse(
            id=123,
            name="Test Hospital",
            address="123 Test St",
            phone="555-0000",
            creation_batch_id=batch_id,
            active=True,
            created_at=created_at,
        )

        assert hospital.id == 123
        assert hospital.active is True

    def test_hospital_processing_result(self):
        """Test HospitalProcessingResult model"""
        result = HospitalProcessingResult(
            row=1,
            hospital_id=123,
            name="Test Hospital",
            status="created_and_activated",
            error_message=None,
        )

        assert result.row == 1
        assert result.hospital_id == 123
        assert result.status == "created_and_activated"
        assert result.error_message is None

    def test_hospital_processing_result_failed(self):
        """Test HospitalProcessingResult with failure"""
        result = HospitalProcessingResult(
            row=1,
            hospital_id=None,
            name="Failed Hospital",
            status="failed",
            error_message="Connection timeout",
        )

        assert result.hospital_id is None
        assert result.status == "failed"
        assert result.error_message == "Connection timeout"

    def test_bulk_create_response(self):
        """Test BulkCreateResponse model"""
        batch_id = uuid4()
        hospitals = [
            HospitalProcessingResult(
                row=1,
                hospital_id=123,
                name="Hospital 1",
                status="created_and_activated",
            )
        ]

        response = BulkCreateResponse(
            batch_id=batch_id,
            total_hospitals=1,
            processed_hospitals=1,
            failed_hospitals=0,
            processing_time_seconds=2.5,
            batch_activated=True,
            hospitals=hospitals,
        )

        assert response.total_hospitals == 1
        assert response.processed_hospitals == 1
        assert response.failed_hospitals == 0
        assert response.batch_activated is True

    def test_job_status_enum(self):
        """Test JobStatus enum"""
        assert JobStatus.PENDING == "pending"
        assert JobStatus.PROCESSING == "processing"
        assert JobStatus.COMPLETED == "completed"
        assert JobStatus.FAILED == "failed"

    def test_job_submit_response(self):
        """Test JobSubmitResponse model"""
        response = JobSubmitResponse(
            job_id="test-job-123",
            status=JobStatus.PENDING,
            message="Job accepted",
            total_hospitals=10,
        )

        assert response.job_id == "test-job-123"
        assert response.status == JobStatus.PENDING
        assert response.total_hospitals == 10

    def test_job_status_response(self):
        """Test JobStatusResponse model"""
        started_at = datetime.datetime.now(datetime.timezone.utc)

        response = JobStatusResponse(
            job_id="test-job-123",
            status=JobStatus.PROCESSING,
            total_hospitals=10,
            processed_hospitals=5,
            failed_hospitals=0,
            progress_percentage=50.0,
            message="Processing...",
            started_at=started_at,
            completed_at=None,
            processing_time_seconds=5.0,
            estimated_time_remaining_seconds=5.0,
            current_hospital="Hospital 5",
            recent_updates=[],
            result=None,
            error=None,
        )

        assert response.progress_percentage == 50.0
        assert response.processed_hospitals == 5
        assert response.current_hospital == "Hospital 5"


class TestJob:
    """Test Job class"""

    def test_job_initialization(self):
        """Test job initialization"""
        job = Job(job_id="test-123", total_hospitals=10)

        assert job.job_id == "test-123"
        assert job.total_hospitals == 10
        assert job.status == JobStatus.PENDING
        assert job.processed_hospitals == 0
        assert job.failed_hospitals == 0
        assert job.current_hospital is None

    def test_job_progress_percentage(self):
        """Test progress percentage calculation"""
        job = Job(job_id="test-123", total_hospitals=10)

        # Initial progress
        assert job.progress_percentage == 0.0

        # Update progress
        job.processed_hospitals = 5
        assert job.progress_percentage == 50.0

        # Complete
        job.processed_hospitals = 10
        assert job.progress_percentage == 100.0

    def test_job_progress_percentage_zero_hospitals(self):
        """Test progress percentage with zero hospitals"""
        job = Job(job_id="test-123", total_hospitals=0)
        assert job.progress_percentage == 0.0

    def test_job_update_progress_success(self):
        """Test updating job progress with success"""
        job = Job(job_id="test-123", total_hospitals=10)

        job.update_progress("Hospital 1", success=True)

        assert job.processed_hospitals == 1
        assert job.failed_hospitals == 0
        assert job.current_hospital == "Hospital 1"
        assert len(job.recent_updates) == 1
        assert job.recent_updates[0].status == "success"

    def test_job_update_progress_failure(self):
        """Test updating job progress with failure"""
        job = Job(job_id="test-123", total_hospitals=10)

        job.update_progress("Hospital 1", success=False, error_message="Failed")

        assert job.processed_hospitals == 1
        assert job.failed_hospitals == 1
        assert job.current_hospital == "Hospital 1"
        assert job.recent_updates[0].status == "failed"

    def test_job_recent_updates_limit(self):
        """Test that recent updates are limited to 10"""
        job = Job(job_id="test-123", total_hospitals=20)

        # Add 15 updates
        for i in range(15):
            job.update_progress(f"Hospital {i + 1}", success=True)

        # Should only keep last 10
        assert len(job.recent_updates) == 10
        assert job.recent_updates[0].hospital_name == "Hospital 6"
        assert job.recent_updates[-1].hospital_name == "Hospital 15"

    def test_job_estimated_time_remaining(self):
        """Test estimated time remaining calculation"""
        job = Job(job_id="test-123", total_hospitals=10)
        job.status = JobStatus.PROCESSING

        # No progress yet
        assert job.estimated_time_remaining_seconds is None

        # Simulate some progress
        import time

        job.start_time = time.time() - 10  # Started 10 seconds ago
        job.processed_hospitals = 5  # 50% done

        # Should estimate ~10 more seconds (50% remaining)
        eta = job.estimated_time_remaining_seconds
        assert eta is not None
        assert 8 <= eta <= 12  # Allow some variance

    def test_job_to_status_response(self):
        """Test converting job to status response"""
        job = Job(job_id="test-123", total_hospitals=10)
        job.status = JobStatus.PROCESSING
        job.processed_hospitals = 5

        response = job.to_status_response()

        assert response.job_id == "test-123"
        assert response.status == JobStatus.PROCESSING
        assert response.total_hospitals == 10
        assert response.processed_hospitals == 5
        assert response.progress_percentage == 50.0

    def test_job_status_messages(self):
        """Test status message generation"""
        job = Job(job_id="test-123", total_hospitals=10)

        # Pending
        job.status = JobStatus.PENDING
        response = job.to_status_response()
        assert "pending" in response.message.lower()

        # Processing
        job.status = JobStatus.PROCESSING
        job.processed_hospitals = 5
        response = job.to_status_response()
        assert "5/10" in response.message

        # Completed
        job.status = JobStatus.COMPLETED
        job.processed_hospitals = 10
        response = job.to_status_response()
        assert "success" in response.message.lower()

        # Failed
        job.status = JobStatus.FAILED
        job.error = "Test error"
        response = job.to_status_response()
        assert "failed" in response.message.lower()


class TestJobManager:
    """Test JobManager class"""

    def test_job_manager_initialization(self):
        """Test job manager initialization"""
        manager = JobManager(max_jobs=100, job_ttl_seconds=300)

        assert manager.max_jobs == 100
        assert manager.job_ttl_seconds == 300
        assert len(manager.jobs) == 0

    def test_create_job(self):
        """Test creating a job"""
        manager = JobManager()

        job = manager.create_job(total_hospitals=10)

        assert job is not None
        assert job.total_hospitals == 10
        assert job.status == JobStatus.PENDING
        assert job.job_id in manager.jobs

    def test_get_job(self):
        """Test getting a job by ID"""
        manager = JobManager()

        job = manager.create_job(total_hospitals=10)
        job_id = job.job_id

        retrieved_job = manager.get_job(job_id)

        assert retrieved_job is not None
        assert retrieved_job.job_id == job_id

    def test_get_nonexistent_job(self):
        """Test getting a non-existent job"""
        manager = JobManager()

        job = manager.get_job("nonexistent-id")

        assert job is None

    def test_update_job_status(self):
        """Test updating job status"""
        manager = JobManager()

        job = manager.create_job(total_hospitals=10)
        job_id = job.job_id

        manager.update_job_status(job_id, JobStatus.PROCESSING)

        assert job.status == JobStatus.PROCESSING

    def test_update_job_status_completed(self):
        """Test updating job status to completed sets timestamp"""
        manager = JobManager()

        job = manager.create_job(total_hospitals=10)
        job_id = job.job_id

        assert job.completed_at is None

        manager.update_job_status(job_id, JobStatus.COMPLETED)

        assert job.status == JobStatus.COMPLETED
        assert job.completed_at is not None

    def test_update_job_progress(self):
        """Test updating job progress"""
        manager = JobManager()

        job = manager.create_job(total_hospitals=10)
        job_id = job.job_id

        manager.update_job_progress(job_id, "Hospital 1", success=True)

        assert job.processed_hospitals == 1
        assert job.current_hospital == "Hospital 1"

    def test_set_job_result(self):
        """Test setting job result"""
        manager = JobManager()

        job = manager.create_job(total_hospitals=10)
        job_id = job.job_id

        result = BulkCreateResponse(
            batch_id=uuid4(),
            total_hospitals=10,
            processed_hospitals=10,
            failed_hospitals=0,
            processing_time_seconds=5.0,
            batch_activated=True,
            hospitals=[],
        )

        manager.set_job_result(job_id, result)

        assert job.result is not None
        assert job.result.total_hospitals == 10

    def test_set_job_error(self):
        """Test setting job error"""
        manager = JobManager()

        job = manager.create_job(total_hospitals=10)
        job_id = job.job_id

        manager.set_job_error(job_id, "Test error message")

        assert job.error == "Test error message"
        assert job.status == JobStatus.FAILED
        assert job.completed_at is not None

    def test_get_job_status(self):
        """Test getting job status response"""
        manager = JobManager()

        job = manager.create_job(total_hospitals=10)
        job_id = job.job_id

        status = manager.get_job_status(job_id)

        assert status is not None
        assert status.job_id == job_id
        assert status.total_hospitals == 10

    def test_get_job_status_nonexistent(self):
        """Test getting status of non-existent job"""
        manager = JobManager()

        status = manager.get_job_status("nonexistent-id")

        assert status is None

    def test_get_all_jobs(self):
        """Test getting all jobs"""
        manager = JobManager()

        # Create multiple jobs
        manager.create_job(total_hospitals=5)
        manager.create_job(total_hospitals=10)
        manager.create_job(total_hospitals=15)

        all_jobs = manager.get_all_jobs()

        assert len(all_jobs) == 3

    def test_get_stats(self):
        """Test getting job statistics"""
        manager = JobManager()

        # Create jobs with different statuses
        job1 = manager.create_job(total_hospitals=10)
        job2 = manager.create_job(total_hospitals=10)
        job3 = manager.create_job(total_hospitals=10)

        manager.update_job_status(job1.job_id, JobStatus.PROCESSING)
        manager.update_job_status(job2.job_id, JobStatus.COMPLETED)
        manager.update_job_status(job3.job_id, JobStatus.FAILED)

        stats = manager.get_stats()

        assert stats["total_jobs"] == 3
        assert stats["pending_jobs"] == 0
        assert stats["processing_jobs"] == 1
        assert stats["completed_jobs"] == 1
        assert stats["failed_jobs"] == 1

    def test_get_active_jobs_count(self):
        """Test getting count of active jobs"""
        manager = JobManager()

        job1 = manager.create_job(total_hospitals=10)
        job2 = manager.create_job(total_hospitals=10)
        job3 = manager.create_job(total_hospitals=10)

        manager.update_job_status(job1.job_id, JobStatus.PROCESSING)
        manager.update_job_status(job2.job_id, JobStatus.PROCESSING)
        manager.update_job_status(job3.job_id, JobStatus.COMPLETED)

        assert manager.get_active_jobs_count() == 2

    def test_cleanup_old_jobs(self):
        """Test cleanup of old jobs when max is exceeded"""
        manager = JobManager(max_jobs=3, job_ttl_seconds=300)

        # Create 5 jobs (exceeds max)
        for i in range(5):
            job = manager.create_job(total_hospitals=10)
            manager.update_job_status(job.job_id, JobStatus.COMPLETED)

        # Should only keep max_jobs
        assert len(manager.jobs) <= 3


class TestCSVValidator:
    """Test CSV validation utilities"""

    def test_validator_constants(self):
        """Test validator class constants"""
        assert CSVValidator.REQUIRED_HEADERS == ["name", "address"]
        assert CSVValidator.OPTIONAL_HEADERS == ["phone"]
        assert CSVValidator.MAX_ROWS == 20
        assert CSVValidator.MAX_FILE_SIZE_MB == 5

    @pytest.mark.asyncio
    async def test_validate_csv_success(self, sample_csv_file):
        """Test successful CSV validation"""
        from fastapi import UploadFile

        with open(sample_csv_file, "rb") as f:
            upload_file = UploadFile(
                filename="test.csv",
                file=f,
            )

            data, errors = await CSVValidator.validate_and_parse_csv(upload_file)

            assert len(data) == 3
            assert len(errors) == 0
            assert data[0]["name"] == "General Hospital"

    @pytest.mark.asyncio
    async def test_validate_csv_missing_headers(self, invalid_csv_file):
        """Test CSV validation with missing required headers"""
        from fastapi import HTTPException, UploadFile

        with open(invalid_csv_file, "rb") as f:
            upload_file = UploadFile(
                filename="invalid.csv",
                file=f,
            )

            with pytest.raises(HTTPException) as exc_info:
                await CSVValidator.validate_and_parse_csv(upload_file)

            assert exc_info.value.status_code == 400
            assert "address" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_validate_csv_exceeds_max_rows(self, oversized_csv_file):
        """Test CSV validation with too many rows"""
        from fastapi import HTTPException, UploadFile

        with open(oversized_csv_file, "rb") as f:
            upload_file = UploadFile(
                filename="oversized.csv",
                file=f,
            )

            with pytest.raises(HTTPException) as exc_info:
                await CSVValidator.validate_and_parse_csv(upload_file)

            assert exc_info.value.status_code == 400
            assert "maximum" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_validate_csv_wrong_extension(self, tmp_path):
        """Test CSV validation with wrong file extension"""
        from fastapi import HTTPException, UploadFile

        txt_file = tmp_path / "test.txt"
        txt_file.write_text("name,address,phone")

        with open(txt_file, "rb") as f:
            upload_file = UploadFile(
                filename="test.txt",
                file=f,
            )

            with pytest.raises(HTTPException) as exc_info:
                await CSVValidator.validate_and_parse_csv(upload_file)

            assert exc_info.value.status_code == 400
            assert "csv" in str(exc_info.value.detail).lower()
