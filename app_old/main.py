import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.job_manager import job_manager
from app.models import (
    ErrorResponse,
    JobStatus,
    JobStatusResponse,
    JobSubmitResponse,
)
from app.services import BulkHospitalProcessor, HospitalAPIClient
from app.utils import CSVValidator

load_dotenv()

# Configuration
HOSPITAL_API_BASE_URL = os.getenv("HOSPITAL_API_BASE_URL", "")
MAX_CSV_ROWS = int(os.getenv("MAX_CSV_ROWS", "20"))
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup
    job_manager.start_cleanup_task()
    print("Job manager cleanup task started")

    yield

    # Shutdown
    job_manager.stop_cleanup_task()
    print("Job manager cleanup task stopped")


# Initialize FastAPI app
app = FastAPI(
    title="Hospital Bulk Processor API",
    description="API for bulk processing hospital records via CSV upload",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
api_client = HospitalAPIClient(base_url=HOSPITAL_API_BASE_URL)
bulk_processor = BulkHospitalProcessor(api_client=api_client, job_manager=job_manager)


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Hospital Bulk Processor API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "docs": "/docs",
            "bulk_upload": "/hospitals/bulk",
            "job_status": "/hospitals/bulk/status/{job_id}",
            "all_jobs": "/hospitals/bulk/jobs",
            "health": "/health",
        },
        "features": {
            "progress_tracking": True,
            "background_processing": True,
            "concurrent_processing": True,
        },
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    job_stats = job_manager.get_stats()
    return {
        "status": "healthy",
        "hospital_api_url": HOSPITAL_API_BASE_URL,
        "max_csv_rows": MAX_CSV_ROWS,
        "job_stats": job_stats,
    }


@app.post(
    "/hospitals/bulk",
    response_model=JobSubmitResponse,
    responses={
        202: {"description": "Job accepted and processing started"},
        400: {"model": ErrorResponse, "description": "Invalid request or CSV format"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    status_code=202,
)
async def bulk_create_hospitals(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(
        ..., description="CSV file with hospital data (name, address, phone)"
    ),
):
    """
    Bulk create hospitals from CSV file with background processing.

    **CSV Format:**
    - Required columns: name, address
    - Optional columns: phone
    - Maximum rows: 20

    **Processing:**
    1. Validates CSV format and content
    2. Returns immediately with a job ID
    3. Processes hospitals in the background
    4. Use the job ID to check progress via `/hospitals/bulk/status/{job_id}`

    **Example CSV:**
    ```
    name,address,phone
    General Hospital,123 Main St,555-1234
    City Medical Center,456 Oak Ave,555-5678
    ```

    **Response:**
    Returns a job ID that can be used to track progress.

    **Next Step:**
    Poll `/hospitals/bulk/status/{job_id}` to get real-time progress updates.
    """
    try:
        # Validate and parse CSV
        hospitals_data, errors = await CSVValidator.validate_and_parse_csv(
            file, max_rows=MAX_CSV_ROWS
        )

        # Create job
        job = job_manager.create_job(total_hospitals=len(hospitals_data))

        # Schedule background processing
        background_tasks.add_task(
            process_hospitals_background, job.job_id, hospitals_data
        )

        return JobSubmitResponse(
            job_id=job.job_id,
            status=JobStatus.PENDING,
            message="Job accepted and queued for processing. Use the job_id to check status.",
            total_hospitals=len(hospitals_data),
        )

    except HTTPException:
        # Re-raise HTTP exceptions from validation
        raise
    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get(
    "/hospitals/bulk/status/{job_id}",
    response_model=JobStatusResponse,
    responses={
        200: {"description": "Job status retrieved successfully"},
        404: {"model": ErrorResponse, "description": "Job not found"},
    },
)
async def get_job_status(job_id: str):
    """
    Get the status of a bulk processing job.

    **Polling Endpoint:**
    Use this endpoint to track the progress of your CSV upload.

    **Usage:**
    1. Submit a CSV via `/hospitals/bulk` to get a job_id
    2. Poll this endpoint every 2-5 seconds with the job_id
    3. Monitor `progress_percentage` and `processed_hospitals`
    4. When `status` is "completed", get the final result
    5. If `status` is "failed", check the `error` field

    **Response Fields:**
    - `status`: pending, processing, completed, or failed
    - `progress_percentage`: 0-100% completion
    - `processed_hospitals`: Number of hospitals processed so far
    - `estimated_time_remaining_seconds`: Estimated time to completion
    - `current_hospital`: Name of hospital currently being processed
    - `recent_updates`: Last 5 hospital processing updates
    - `result`: Full result when status is "completed"

    **Example:**
    ```bash
    # Poll every 2 seconds
    while true; do
        curl http://localhost:8000/hospitals/bulk/status/YOUR_JOB_ID
        sleep 2
    done
    ```
    """
    job_status = job_manager.get_job_status(job_id)

    if not job_status:
        raise HTTPException(
            status_code=404,
            detail=f"Job with ID '{job_id}' not found. It may have expired or never existed.",
        )

    return job_status


@app.get("/hospitals/bulk/jobs", responses={200: {"description": "List of all jobs"}})
async def get_all_jobs():
    """
    Get status of all jobs.

    **Usage:**
    Use this endpoint to see all current and recent jobs in the system.

    **Response:**
    List of all jobs with their current status.
    """
    jobs = job_manager.get_all_jobs()
    stats = job_manager.get_stats()

    return {"total_jobs": len(jobs), "stats": stats, "jobs": jobs}


async def process_hospitals_background(job_id: str, hospitals_data: list):
    """
    Background task to process hospitals.

    Args:
        job_id: Job identifier
        hospitals_data: List of hospital data to process
    """
    try:
        # Update job status to processing
        job_manager.update_job_status(job_id, JobStatus.PROCESSING)

        # Process the hospitals
        result = await bulk_processor.process_bulk_upload(hospitals_data, job_id=job_id)

        # Update job with result
        job_manager.set_job_result(job_id, result)
        job_manager.update_job_status(job_id, JobStatus.COMPLETED)

    except Exception as e:
        # Handle any errors
        error_message = f"Error processing hospitals: {str(e)}"
        job_manager.set_job_error(job_id, error_message)
        print(f"Job {job_id} failed: {error_message}")


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom exception handler for HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error_type": "validation_error"
            if exc.status_code == 400
            else "server_error",
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """General exception handler for unexpected errors"""
    return JSONResponse(
        status_code=500,
        content={
            "detail": f"An unexpected error occurred: {str(exc)}",
            "error_type": "internal_error",
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=True)
