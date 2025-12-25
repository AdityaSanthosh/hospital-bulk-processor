"""In-memory job repository"""
import logging
from datetime import datetime, timezone
from typing import Dict, Optional
from uuid import uuid4

from app.domain.exceptions import JobNotFoundException
from app.domain.schemas import BulkCreateResponse, JobStatus

logger = logging.getLogger(__name__)


class Job:
    """Job domain model"""
    
    def __init__(self, job_id: str, total_hospitals: int):
        self.job_id = job_id
        self.status = JobStatus.PENDING
        self.total_hospitals = total_hospitals
        self.processed_hospitals = 0
        self.failed_hospitals = 0
        self.started_at = datetime.now(timezone.utc)
        self.completed_at: Optional[datetime] = None
        self.result: Optional[BulkCreateResponse] = None
        self.error: Optional[str] = None
    
    @property
    def progress_percentage(self) -> float:
        """Calculate progress percentage"""
        if self.total_hospitals == 0:
            return 0.0
        return round((self.processed_hospitals / self.total_hospitals) * 100, 2)
    
    @property
    def processing_time_seconds(self) -> float:
        """Calculate processing time"""
        if self.completed_at:
            return round((self.completed_at - self.started_at).total_seconds(), 2)
        return round((datetime.now(timezone.utc) - self.started_at).total_seconds(), 2)


class JobRepository:
    """In-memory job repository"""
    
    def __init__(self):
        self._jobs: Dict[str, Job] = {}
        logger.info("JobRepository initialized (in-memory)")
    
    def create(self, total_hospitals: int) -> Job:
        """Create a new job"""
        job_id = str(uuid4())
        job = Job(job_id=job_id, total_hospitals=total_hospitals)
        self._jobs[job_id] = job
        logger.info(f"Job created: {job_id} (total_hospitals: {total_hospitals})")
        return job
    
    def get(self, job_id: str) -> Optional[Job]:
        """Get job by ID"""
        return self._jobs.get(job_id)
    
    def get_or_raise(self, job_id: str) -> Job:
        """Get job or raise exception"""
        job = self.get(job_id)
        if not job:
            raise JobNotFoundException(f"Job {job_id} not found")
        return job
    
    def update_status(self, job_id: str, status: JobStatus) -> None:
        """Update job status"""
        job = self.get_or_raise(job_id)
        job.status = status
        if status in [JobStatus.COMPLETED, JobStatus.FAILED]:
            job.completed_at = datetime.now(timezone.utc)
        logger.info(f"Job {job_id} status updated: {status}")
    
    def set_result(self, job_id: str, result: BulkCreateResponse) -> None:
        """Set job result"""
        job = self.get_or_raise(job_id)
        job.result = result
        job.processed_hospitals = result.processed_hospitals
        job.failed_hospitals = result.failed_hospitals
        logger.info(f"Job {job_id} result set")
    
    def set_error(self, job_id: str, error: str) -> None:
        """Set job error"""
        job = self.get_or_raise(job_id)
        job.error = error
        job.status = JobStatus.FAILED
        job.completed_at = datetime.now(timezone.utc)
        logger.error(f"Job {job_id} failed: {error}")
    
    def get_all(self) -> Dict[str, Job]:
        """Get all jobs"""
        return self._jobs.copy()


# Global instance
job_repository = JobRepository()
