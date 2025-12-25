"""Job service - orchestrates job operations"""
import logging
from typing import List

from app.core.idempotency import generate_idempotency_key, idempotency_store
from app.domain.exceptions import JobNotFoundException
from app.domain.schemas import (
    HospitalCreate,
    JobStatus,
    JobStatusResponse,
    JobSubmitResponse,
)
from app.infrastructure.celery.tasks import process_bulk_hospitals_task
from app.infrastructure.repositories.job_repository import job_repository

logger = logging.getLogger(__name__)


class JobService:
    """Service for job operations"""
    
    @staticmethod
    def submit_bulk_job(
        hospitals: List[HospitalCreate],
        idempotency_key: str
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
            logger.info(f"Returning cached response for idempotency key: {idempotency_key[:16]}...")
            return JobSubmitResponse(**cached_response)
        
        # Create job
        job = job_repository.create(total_hospitals=len(hospitals))
        
        # Convert to dict for Celery
        hospitals_data = [h.model_dump() for h in hospitals]
        
        # Submit to Celery
        logger.info(f"Submitting job {job.job_id} to Celery with {len(hospitals)} hospitals")
        process_bulk_hospitals_task.delay(job.job_id, hospitals_data)
        
        # Build response
        response = JobSubmitResponse(
            job_id=job.job_id,
            status=JobStatus.PENDING,
            message="Job accepted and queued for processing. Use the job_id to check status.",
            total_hospitals=len(hospitals),
            idempotency_key=idempotency_key,
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
