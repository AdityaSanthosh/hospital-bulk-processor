"""Hospital bulk processing endpoints"""

import logging
from uuid import UUID

from fastapi import APIRouter, File, Header, HTTPException, UploadFile

from app.domain.exceptions import JobNotFoundException
from app.domain.schemas import (
    BatchActivateResponse,
    ErrorResponse,
    JobListResponse,
    JobStatusResponse,
    JobSubmitResponse,
)
from app.external.hospital_api_client import HospitalAPIClient
from app.services.job_service import JobService
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
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
    """
    Bulk create hospitals from CSV file with Celery processing

    **CSV Format:**
    - Required columns: name, address
    - Optional columns: phone
    - Maximum rows: 20

    **Idempotency:**
    - REQUIRED: Provide `Idempotency-Key` header for safe retries
    - Client must generate unique value per upload attempt (UUID recommended)
    - Same key within 5 minutes = cached response (no duplicate processing)
    - Use for request deduplication only (business logic handles data duplicates)

    **Idempotency Key Examples:**
    - UUID: "550e8400-e29b-41d4-a716-446655440000"
    - Timestamp-based: "upload-2024-12-25-10-30-45-abc123"
    - Semantic: "batch-{user_id}-{timestamp}"

    **Processing Flow:**
    1. Validates CSV format and content
    2. Returns immediately with a job ID
    3. Processes hospitals in background via Celery
    4. **Auto-activates batch if all hospitals succeed**
    5. **If activation fails**: Batch remains created, manual activation available
    6. **If any hospital fails**: Batch NOT activated, review and manually activate if acceptable

    **Auto-Activation Behavior:**
    - ✅ All hospitals succeed → Attempts auto-activation
      - If activation succeeds: Status = "created_and_activated", batch_activated = true
      - If activation fails: Status = "created", batch_activated = false
    - ⚠️ Some hospitals fail → No auto-activation, batch_activated = false

    **Manual Activation (Fallback):**
    After job completes, if `batch_activated=false`, you can manually activate:
    ```bash
    PATCH /api/v1/hospitals/bulk/batch/{batch_id}/activate
    ```

    **Example:**
    ```bash
    curl -X POST http://localhost:8000/api/v1/hospitals/bulk \\
         -H "Idempotency-Key: $(uuidgen)" \\
         -F "file=@hospitals.csv"
    ```

    **Note on Duplicates:**
    - Idempotency only prevents duplicate REQUESTS (network retries, double-clicks)
    - Duplicate hospitals in CSV are handled by business logic in the worker
    - External API will reject or return existing hospitals

    **Note on Rollback:**
    - No automatic rollback - hospitals persist even if activation fails
    - Successfully created hospitals remain in the system
    - Manual activation can be retried without reprocessing
    """
    try:
        # Validate idempotency key
        if not idempotency_key or not idempotency_key.strip():
            raise HTTPException(
                status_code=400,
                detail="Idempotency-Key header is required. Provide a unique value per upload attempt (e.g., UUID).",
            )

        logger.info(
            f"Processing request with idempotency key: {idempotency_key[:16]}..."
        )

        # Validate and parse CSV
        hospitals = await CSVValidator.validate_and_parse_csv(file)

        # Submit job (idempotency handled in service)
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
    4. When `status` is "completed", get the batch_id from `result.batch_id`
    5. Activate the batch via `/api/v1/hospitals/bulk/batch/{batch_id}/activate`
    6. If `status` is "failed", check the `error` field

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


@router.patch(
    "/bulk/batch/{batch_id}/activate",
    response_model=BatchActivateResponse,
    responses={
        200: {"description": "Batch activated successfully"},
        400: {"model": ErrorResponse, "description": "Activation failed"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def activate_batch(batch_id: UUID):
    """
    Activate a batch of hospitals

    **Manual Activation:**
    After bulk creation completes successfully, use this endpoint to activate the batch.
    This gives you control to review the results before making hospitals active.

    **Workflow:**
    1. Upload CSV via `/api/v1/hospitals/bulk` → Get job_id
    2. Poll `/api/v1/hospitals/status/{job_id}` → Wait for completion
    3. Review results (check failed_hospitals count, etc.)
    4. Call this endpoint with the batch_id to activate
    5. All hospitals in the batch become active

    **When to Activate:**
    - ✅ All hospitals created successfully (failed_hospitals = 0)
    - ✅ You've reviewed the results and are satisfied
    - ❌ Don't activate if there were failures (unless acceptable)

    **Idempotent:**
    - Safe to call multiple times with the same batch_id
    - If already activated, returns success

    **Example:**
    ```bash
    # Get batch_id from job status result
    BATCH_ID="550e8400-e29b-41d4-a716-446655440000"

    curl -X PATCH http://localhost:8000/api/v1/hospitals/bulk/batch/$BATCH_ID/activate
    ```

    **Response:**
    ```json
    {
      "batch_id": "550e8400-e29b-41d4-a716-446655440000",
      "activated": true,
      "message": "Batch activated successfully"
    }
    ```
    """
    try:
        logger.info(f"Activating batch {batch_id}")

        # Create API client and activate batch
        api_client = HospitalAPIClient()
        success, error_message = await api_client.activate_batch(batch_id)

        if success:
            logger.info(f"Batch {batch_id} activated successfully")
            return BatchActivateResponse(
                batch_id=batch_id,
                activated=True,
                message="Batch activated successfully",
            )
        else:
            logger.error(f"Failed to activate batch {batch_id}: {error_message}")
            return BatchActivateResponse(
                batch_id=batch_id,
                activated=False,
                message="Batch activation failed",
                error_message=error_message,
            )

    except Exception as e:
        logger.exception(f"Error activating batch {batch_id}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get(
    "/jobs",
    response_model=JobListResponse,
    responses={
        200: {"description": "List of all jobs retrieved successfully"},
    },
)
async def get_all_jobs():
    """
    Get all jobs (current and historical)

    **List Endpoint:**
    Use this endpoint to see all jobs that have been submitted to the system.

    **Response:**
    Returns a list of all jobs with summary information, sorted by most recent first.

    **Usage:**
    ```bash
    curl http://localhost:8000/api/v1/hospitals/jobs
    ```

    **Response Example:**
    ```json
    {
      "total_jobs": 5,
      "jobs": [
        {
          "job_id": "abc-123",
          "status": "completed",
          "total_hospitals": 10,
          "processed_hospitals": 10,
          "failed_hospitals": 0,
          "progress_percentage": 100.0,
          "started_at": "2024-01-15T10:30:00Z",
          "completed_at": "2024-01-15T10:30:25Z",
          "processing_time_seconds": 25.3
        },
        ...
      ]
    }
    ```
    """
    try:
        jobs = JobService.get_all_jobs()
        return jobs
    except Exception as e:
        logger.exception("Error getting all jobs")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
