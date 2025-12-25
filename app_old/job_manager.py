"""
Job Manager for Background Processing and Progress Tracking
Manages job lifecycle, progress updates, and status tracking
"""

import asyncio
import datetime
import time
from collections import deque

# from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

from app.models import (
    BulkCreateResponse,
    JobProgressUpdate,
    JobStatus,
    JobStatusResponse,
)


class Job:
    """Represents a background processing job"""

    def __init__(self, job_id: str, total_hospitals: int):
        self.job_id = job_id
        self.status = JobStatus.PENDING
        self.total_hospitals = total_hospitals
        self.processed_hospitals = 0
        self.failed_hospitals = 0
        self.started_at = datetime.datetime.now(datetime.timezone.utc)
        self.completed_at: Optional[datetime.datetime] = None
        self.current_hospital: Optional[str] = None
        self.recent_updates: deque = deque(maxlen=10)
        self.result: Optional[BulkCreateResponse] = None
        self.error: Optional[str] = None
        self.start_time = time.time()

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
        return round(time.time() - self.start_time, 2)

    @property
    def estimated_time_remaining_seconds(self) -> Optional[float]:
        """Estimate remaining time based on current progress"""
        if self.processed_hospitals == 0 or self.status != JobStatus.PROCESSING:
            return None

        elapsed = time.time() - self.start_time
        avg_time_per_hospital = elapsed / self.processed_hospitals
        remaining_hospitals = self.total_hospitals - self.processed_hospitals
        estimated = avg_time_per_hospital * remaining_hospitals

        return round(estimated, 2) if estimated > 0 else 0.0

    def update_progress(
        self, hospital_name: str, success: bool, error_message: Optional[str] = None
    ):
        """Update job progress with hospital processing result"""
        self.processed_hospitals += 1
        if not success:
            self.failed_hospitals += 1

        self.current_hospital = hospital_name

        # Add to recent updates (keep last 10)
        update = JobProgressUpdate(
            hospital_name=hospital_name,
            status="success" if success else "failed",
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        self.recent_updates.append(update)

    def to_status_response(self) -> JobStatusResponse:
        """Convert job to status response"""
        message = self._get_status_message()

        return JobStatusResponse(
            job_id=self.job_id,
            status=self.status,
            total_hospitals=self.total_hospitals,
            processed_hospitals=self.processed_hospitals,
            failed_hospitals=self.failed_hospitals,
            progress_percentage=self.progress_percentage,
            message=message,
            started_at=self.started_at,
            completed_at=self.completed_at,
            processing_time_seconds=self.processing_time_seconds,
            estimated_time_remaining_seconds=self.estimated_time_remaining_seconds,
            current_hospital=self.current_hospital,
            recent_updates=list(self.recent_updates),  # Last 10 updates
            result=self.result,
            error=self.error,
        )

    def _get_status_message(self) -> str:
        """Generate status message based on current state"""
        if self.status == JobStatus.PENDING:
            return "Job is pending, waiting to start processing"
        elif self.status == JobStatus.PROCESSING:
            return f"Processing hospitals: {self.processed_hospitals}/{self.total_hospitals} completed"
        elif self.status == JobStatus.COMPLETED:
            if self.failed_hospitals > 0:
                return f"Processing completed with {self.failed_hospitals} failures"
            return "All hospitals processed successfully"
        elif self.status == JobStatus.FAILED:
            return f"Job failed: {self.error}"
        return "Unknown status"


class JobManager:
    """Manages background jobs and their lifecycle"""

    def __init__(self, max_jobs: int = 1000, job_ttl_seconds: int = 3600):
        """
        Initialize job manager

        Args:
            max_jobs: Maximum number of jobs to keep in memory
            job_ttl_seconds: Time to live for completed jobs (1 hour default)
        """
        self.jobs: Dict[str, Job] = {}
        self.max_jobs = max_jobs
        self.job_ttl_seconds = job_ttl_seconds
        self._cleanup_task: Optional[asyncio.Task] = None

    def create_job(self, total_hospitals: int) -> Job:
        """
        Create a new job

        Args:
            total_hospitals: Total number of hospitals to process

        Returns:
            Created job instance
        """
        job_id = str(uuid4())
        job = Job(job_id=job_id, total_hospitals=total_hospitals)
        self.jobs[job_id] = job

        # Clean up old jobs if we exceed max
        self._cleanup_old_jobs()

        return job

    def get_job(self, job_id: str) -> Optional[Job]:
        """
        Get job by ID

        Args:
            job_id: Job identifier

        Returns:
            Job instance or None if not found
        """
        return self.jobs.get(job_id)

    def update_job_status(self, job_id: str, status: JobStatus):
        """
        Update job status

        Args:
            job_id: Job identifier
            status: New status
        """
        job = self.jobs.get(job_id)
        if job:
            job.status = status
            if status in [JobStatus.COMPLETED, JobStatus.FAILED]:
                job.completed_at = datetime.datetime.now(datetime.timezone.utc)

    def update_job_progress(
        self,
        job_id: str,
        hospital_name: str,
        success: bool,
        error_message: Optional[str] = None,
    ):
        """
        Update job progress

        Args:
            job_id: Job identifier
            hospital_name: Name of hospital being processed
            success: Whether processing was successful
            error_message: Error message if failed
        """
        job = self.jobs.get(job_id)
        if job:
            job.update_progress(hospital_name, success, error_message)

    def set_job_result(self, job_id: str, result: BulkCreateResponse):
        """
        Set job result

        Args:
            job_id: Job identifier
            result: Processing result
        """
        job = self.jobs.get(job_id)
        if job:
            job.result = result

    def set_job_error(self, job_id: str, error: str):
        """
        Set job error

        Args:
            job_id: Job identifier
            error: Error message
        """
        job = self.jobs.get(job_id)
        if job:
            job.error = error
            job.status = JobStatus.FAILED
            job.completed_at = datetime.datetime.now(datetime.timezone.utc)

    def get_job_status(self, job_id: str) -> Optional[JobStatusResponse]:
        """
        Get job status response

        Args:
            job_id: Job identifier

        Returns:
            Job status response or None if not found
        """
        job = self.jobs.get(job_id)
        if job:
            return job.to_status_response()
        return None

    def _cleanup_old_jobs(self):
        """Remove old completed jobs to prevent memory issues"""
        if len(self.jobs) <= self.max_jobs:
            return

        # Sort jobs by completion time
        completed_jobs = [
            (job_id, job)
            for job_id, job in self.jobs.items()
            if job.status in [JobStatus.COMPLETED, JobStatus.FAILED]
            and job.completed_at
        ]

        if not completed_jobs:
            return

        # Sort by completion time (oldest first)
        # Type guard: completed_at is guaranteed to be non-None due to filter above
        completed_jobs.sort(
            key=lambda x: x[1].completed_at
            or datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
        )

        # Remove oldest jobs until we're under the limit
        jobs_to_remove = len(self.jobs) - self.max_jobs
        for i in range(min(jobs_to_remove, len(completed_jobs))):
            job_id = completed_jobs[i][0]
            del self.jobs[job_id]

    async def cleanup_expired_jobs(self):
        """Periodically clean up expired jobs (background task)"""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes

                current_time = datetime.datetime.now(datetime.timezone.utc)
                expired_jobs = []

                for job_id, job in self.jobs.items():
                    if job.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
                        if job.completed_at:
                            age_seconds = (
                                current_time - job.completed_at
                            ).total_seconds()
                            if age_seconds > self.job_ttl_seconds:
                                expired_jobs.append(job_id)

                # Remove expired jobs
                for job_id in expired_jobs:
                    del self.jobs[job_id]

                if expired_jobs:
                    print(f"Cleaned up {len(expired_jobs)} expired jobs")

            except Exception as e:
                print(f"Error in cleanup task: {e}")

    def start_cleanup_task(self):
        """Start the background cleanup task"""
        if not self._cleanup_task:
            self._cleanup_task = asyncio.create_task(self.cleanup_expired_jobs())

    def stop_cleanup_task(self):
        """Stop the background cleanup task"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            self._cleanup_task = None

    def get_all_jobs(self) -> List[JobStatusResponse]:
        """Get status of all jobs"""
        return [job.to_status_response() for job in self.jobs.values()]

    def get_active_jobs_count(self) -> int:
        """Get count of active (processing) jobs"""
        return sum(
            1 for job in self.jobs.values() if job.status == JobStatus.PROCESSING
        )

    def get_stats(self) -> Dict:
        """Get job manager statistics"""
        return {
            "total_jobs": len(self.jobs),
            "pending_jobs": sum(
                1 for job in self.jobs.values() if job.status == JobStatus.PENDING
            ),
            "processing_jobs": sum(
                1 for job in self.jobs.values() if job.status == JobStatus.PROCESSING
            ),
            "completed_jobs": sum(
                1 for job in self.jobs.values() if job.status == JobStatus.COMPLETED
            ),
            "failed_jobs": sum(
                1 for job in self.jobs.values() if job.status == JobStatus.FAILED
            ),
        }


# Global job manager instance
job_manager = JobManager()
