"""Job service - orchestrates job operations"""

import logging
from datetime import datetime, timezone
from typing import List

from fastapi import HTTPException
from kombu.exceptions import OperationalError

from app.core.idempotency import idempotency_store
from app.domain.exceptions import JobNotFoundException
from app.domain.schemas import (
    HospitalCreate,
    JobListResponse,
    JobStatus,
    JobStatusResponse,
    JobSubmitResponse,
    JobSummary,
)
from app.repositories.job_repository import job_repository
from app.tasks.tasks import process_bulk_hospitals_task

logger = logging.getLogger(__name__)


class JobService:
    """Service for job operations"""

    @staticmethod
    def submit_bulk_job(
        hospitals: List[HospitalCreate], idempotency_key: str
    ) -> JobSubmitResponse:
        """
        Submit a bulk processing job with idempotency

        Args:
            hospitals: List of hospitals to process
            idempotency_key: Idempotency key for safe retries

        Returns:
            JobSubmitResponse
        """
        # Check idempotency cache
        cached_response = idempotency_store.get(idempotency_key)
        if cached_response:
            logger.info(
                f"Returning cached response for idempotency key: {idempotency_key[:16]}..."
            )
            return JobSubmitResponse(**cached_response)

        # Create job
        job = job_repository.create(total_hospitals=len(hospitals))

        # Convert to dict for Celery
        hospitals_data = [h.model_dump() for h in hospitals]

        # Submit to Celery with fail-fast error handling
        logger.info(
            f"Submitting job {job.job_id} to Celery with {len(hospitals)} hospitals"
        )
        try:
            # Use delay() - Celery config handles fail-fast behavior
            process_bulk_hospitals_task.delay(job.job_id, hospitals_data)  # type: ignore[attr-defined]
        except OperationalError as e:
            logger.error(f"Message queue unavailable: {e}")
            # Clean up the job that was created
            job_repository.update_status(job.job_id, JobStatus.FAILED)
            job_repository.set_error(job.job_id, "Message queue unavailable")
            raise HTTPException(
                status_code=503,
                detail="Service temporarily unavailable. Please try again later.",
            )
        except Exception as e:
            logger.exception(f"Unexpected error submitting job to queue: {e}")
            job_repository.update_status(job.job_id, JobStatus.FAILED)
            job_repository.set_error(job.job_id, f"Failed to queue job: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Failed to submit job for processing. Please try again later.",
            )

        # Build response
        response = JobSubmitResponse(
            job_id=job.job_id,
            status=JobStatus.PENDING,
            message="Job accepted and queued for processing. Use the job_id to check status.",
            total_hospitals=len(hospitals),
        )

        # Cache response for idempotency
        idempotency_store.set(idempotency_key, response.model_dump())

        logger.info(f"Job {job.job_id} submitted successfully")
        return response

    @staticmethod
    def get_job_status(job_id: str) -> JobStatusResponse:
        """
        Get job status

        Args:
            job_id: Job identifier

        Returns:
            JobStatusResponse

        Raises:
            JobNotFoundException: If job not found
        """
        job = job_repository.get(job_id)

        if not job:
            raise JobNotFoundException(f"Job with ID '{job_id}' not found")

        # Build message
        if job.status == JobStatus.PENDING:
            message = "Job is pending, waiting to start processing"
        elif job.status == JobStatus.PROCESSING:
            message = f"Processing hospitals: {job.processed_hospitals}/{job.total_hospitals} completed"
        elif job.status == JobStatus.COMPLETED:
            if job.failed_hospitals > 0:
                message = f"Processing completed with {job.failed_hospitals} failures"
            else:
                message = "All hospitals processed successfully"
        elif job.status == JobStatus.FAILED:
            message = f"Job failed: {job.error}"
        else:
            message = "Unknown status"

        return JobStatusResponse(
            job_id=job.job_id,
            status=job.status,
            total_hospitals=job.total_hospitals,
            processed_hospitals=job.processed_hospitals,
            failed_hospitals=job.failed_hospitals,
            progress_percentage=job.progress_percentage,
            message=message,
            started_at=job.started_at,
            completed_at=job.completed_at,
            processing_time_seconds=job.processing_time_seconds,
            result=job.result,
            error=job.error,
        )

    @staticmethod
    def get_all_jobs() -> JobListResponse:
        """
        Get all jobs (current and historical)

        Returns:
            JobListResponse with all jobs
        """

        all_jobs = job_repository.get_all()

        # Normalize datetimes to timezone-aware UTC before building summaries.
        # This avoids comparisons between offset-naive and offset-aware datetimes.
        def _ensure_aware_utc(dt):
            if dt is None:
                return None
            if dt.tzinfo is None:
                # Treat naive datetimes as UTC
                return dt.replace(tzinfo=timezone.utc)
            # Convert any aware datetime to UTC
            return dt.astimezone(timezone.utc)

        job_summaries = []
        for job_id, job in all_jobs.items():
            started_at = _ensure_aware_utc(job.started_at)
            completed_at = _ensure_aware_utc(job.completed_at)

            summary = JobSummary(
                job_id=job.job_id,
                status=job.status,
                total_hospitals=job.total_hospitals,
                processed_hospitals=job.processed_hospitals,
                failed_hospitals=job.failed_hospitals,
                progress_percentage=job.progress_percentage,
                started_at=started_at,
                completed_at=completed_at,
                processing_time_seconds=job.processing_time_seconds,
            )
            job_summaries.append(summary)

        # Sort by started_at (most recent first). Treat jobs that haven't started as oldest.
        job_summaries.sort(
            key=lambda x: x.started_at or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )

        logger.info(f"Retrieved {len(job_summaries)} jobs")

        return JobListResponse(total_jobs=len(job_summaries), jobs=job_summaries)
