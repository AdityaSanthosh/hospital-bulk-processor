"""Pydantic schemas for API requests and responses"""
from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Job processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class HospitalCreate(BaseModel):
    """Hospital creation data"""
    name: str
    address: str
    phone: Optional[str] = None
    row_number: int


class HospitalResponse(BaseModel):
    """Hospital API response"""
    id: int
    name: str
    address: str
    phone: Optional[str] = None
    is_active: bool
    creation_batch_id: Optional[UUID] = None


class HospitalProcessingResult(BaseModel):
    """Result of processing a single hospital"""
    row: int
    hospital_id: Optional[int] = None
    name: str
    status: str  # "created", "created_and_activated", "failed"
    error_message: Optional[str] = None


class BulkCreateResponse(BaseModel):
    """Response for bulk hospital creation"""
    batch_id: UUID
    total_hospitals: int
    processed_hospitals: int
    failed_hospitals: int
    processing_time_seconds: float
    batch_activated: bool
    hospitals: List[HospitalProcessingResult]


class JobSubmitResponse(BaseModel):
    """Response when job is submitted"""
    job_id: str
    status: JobStatus
    message: str
    total_hospitals: int
    idempotency_key: str


class JobStatusResponse(BaseModel):
    """Job status response"""
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
    result: Optional[BulkCreateResponse] = None
    error: Optional[str] = None


class ErrorResponse(BaseModel):
    """Error response"""
    detail: str
    error_type: str
