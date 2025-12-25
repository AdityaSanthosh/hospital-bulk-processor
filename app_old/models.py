from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class HospitalCreateRequest(BaseModel):
    """Model for creating a single hospital in the external API"""

    name: str = Field(..., min_length=1, max_length=255)
    address: str = Field(..., min_length=1, max_length=500)
    phone: Optional[str] = Field(None, max_length=50)
    creation_batch_id: UUID


class HospitalResponse(BaseModel):
    """Model for hospital response from external API"""

    id: int
    name: str
    address: str
    phone: Optional[str]
    creation_batch_id: UUID
    active: bool
    created_at: datetime


class HospitalProcessingResult(BaseModel):
    """Result for a single hospital processing"""

    row: int
    hospital_id: Optional[int] = None
    name: str
    status: str  # "created_and_activated", "failed"
    error_message: Optional[str] = None


class BulkCreateResponse(BaseModel):
    """Response model for bulk hospital creation"""

    batch_id: UUID
    total_hospitals: int
    processed_hospitals: int
    failed_hospitals: int
    processing_time_seconds: float
    batch_activated: bool
    hospitals: List[HospitalProcessingResult]


class ErrorResponse(BaseModel):
    """Model for error responses"""

    detail: str
    error_type: Optional[str] = None


class JobStatus(str, Enum):
    """Enumeration of job statuses"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobSubmitResponse(BaseModel):
    """Response model when a job is submitted"""

    job_id: str
    status: JobStatus
    message: str
    total_hospitals: int


class JobProgressUpdate(BaseModel):
    """Progress update for a single hospital"""

    hospital_name: str
    status: str
    timestamp: datetime


class JobStatusResponse(BaseModel):
    """Response model for job status queries"""

    job_id: str
    status: JobStatus
    total_hospitals: int
    processed_hospitals: int
    failed_hospitals: int
    progress_percentage: float
    message: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    processing_time_seconds: Optional[float] = None
    estimated_time_remaining_seconds: Optional[float] = None
    current_hospital: Optional[str] = None
    recent_updates: List[JobProgressUpdate] = []
    result: Optional[BulkCreateResponse] = None
    error: Optional[str] = None
