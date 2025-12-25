"""Hospital bulk processing endpoints"""
import logging

from fastapi import APIRouter, File, Header, HTTPException, UploadFile

from app.application.job_service import JobService
from app.core.idempotency import generate_idempotency_key
from app.domain.exceptions import JobNotFoundException
from app.domain.schemas import ErrorResponse, JobStatusResponse, JobSubmitResponse
from app.utils.csv_validator import CSVValidator

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/bulk",
    response_model=JobSubmitResponse,
    status_code=202,
    responses={
        202: {"description": "Job accepted and processing started"},
        400: {"model": ErrorResponse, "description": "Invalid request or CSV format"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def bulk_create_hospitals(
    file: UploadFile = File(..., description="CSV file with hospital data"),
    idempotency_key: str = Header(None, alias="Idempotency-Key")
):
    """
    Bulk create hospitals from CSV file with Celery processing
    
    **CSV Format:**
    - Required columns: name, address
    - Optional columns: phone
    - Maximum rows: 20
    
    **Idempotency:**
    - Provide `Idempotency-Key` header for safe retries
    - Same key will return cached response if job already submitted
    
    **Processing:**
    1. Validates CSV format and content
    2. Returns immediately with a job ID
    3. Processes hospitals in background via Celery
    4. Use job ID to check progress via `/api/v1/hospitals/status/{job_id}`
    
    **Example:**
    ```bash
    curl -X POST http://localhost:8000/api/v1/hospitals/bulk \\
         -H "Idempotency-Key: my-unique-key-123" \\
         -F "file=@hospitals.csv"
    ```
    """
    try:
        # Validate and parse CSV
        hospitals = await CSVValidator.validate_and_parse_csv(file)
        
        # Generate idempotency key if not provided
        if not idempotency_key:
            csv_content = ",".join([f"{h.name}{h.address}" for h in hospitals])
            idempotency_key = generate_idempotency_key(csv_content)
            logger.info(f"Generated idempotency key: {idempotency_key[:16]}...")
        
        # Submit job
        response = JobService.submit_bulk_job(hospitals, idempotency_key)
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error in bulk_create_hospitals")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get(
    "/status/{job_id}",
    response_model=JobStatusResponse,
    responses={
        200: {"description": "Job status retrieved successfully"},
        404: {"model": ErrorResponse, "description": "Job not found"},
    },
)
async def get_job_status(job_id: str):
    """
    Get the status of a bulk processing job
    
    **Polling Endpoint:**
    Use this endpoint to track the progress of your CSV upload.
    
    **Usage:**
    1. Submit a CSV via `/api/v1/hospitals/bulk` to get a job_id
    2. Poll this endpoint every 2-5 seconds with the job_id
    3. Monitor `progress_percentage` and `processed_hospitals`
    4. When `status` is "completed", get the final result
    5. If `status` is "failed", check the `error` field
    
    **Example:**
    ```bash
    curl http://localhost:8000/api/v1/hospitals/status/YOUR_JOB_ID
    ```
    """
    try:
        status = JobService.get_job_status(job_id)
        return status
    except JobNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception(f"Error getting job status for {job_id}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
