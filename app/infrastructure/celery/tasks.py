"""Celery tasks"""
import asyncio
import logging
import time
from typing import List
from uuid import UUID, uuid4

from app.domain.schemas import (
    BulkCreateResponse,
    HospitalCreate,
    HospitalProcessingResult,
    JobStatus,
)
from app.infrastructure.celery.celery_app import celery_app
from app.infrastructure.external.hospital_api_client import HospitalAPIClient
from app.infrastructure.repositories.job_repository import job_repository

logger = logging.getLogger(__name__)


@celery_app.task(name="process_bulk_hospitals")
def process_bulk_hospitals_task(job_id: str, hospitals_data: List[dict]):
    """
    Celery task to process bulk hospital uploads
    
    Args:
        job_id: Job identifier
        hospitals_data: List of hospital dictionaries
    """
    logger.info(f"Starting Celery task for job {job_id} with {len(hospitals_data)} hospitals")
    
    # Run async code in event loop
    result = asyncio.run(_process_hospitals_async(job_id, hospitals_data))
    
    logger.info(f"Completed Celery task for job {job_id}")
    return result


async def _process_hospitals_async(job_id: str, hospitals_data: List[dict]):
    """Async hospital processing logic"""
    try:
        # Update job status
        job_repository.update_status(job_id, JobStatus.PROCESSING)
        
        start_time = time.time()
        batch_id = uuid4()
        
        # Convert dicts to HospitalCreate objects
        hospitals = [HospitalCreate(**h) for h in hospitals_data]
        
        # Create API client
        api_client = HospitalAPIClient()
        
        # Process hospitals concurrently
        logger.info(f"Processing {len(hospitals)} hospitals concurrently for job {job_id}")
        results = await _create_hospitals_concurrently(
            api_client, hospitals, batch_id
        )
        
        # Calculate results
        failed_count = sum(1 for r in results if r.status == "failed")
        success_count = len(results) - failed_count
        
        batch_activated = False
        
        # Only activate if all succeeded
        if failed_count == 0:
            logger.info(f"All hospitals created successfully, activating batch {batch_id}")
            activation_success, activation_error = await api_client.activate_batch(batch_id)
            
            if activation_success:
                batch_activated = True
                for result in results:
                    result.status = "created_and_activated"
                logger.info(f"Batch {batch_id} activated successfully")
            else:
                logger.error(f"Batch activation failed: {activation_error}. Rolling back...")
                # Rollback
                await api_client.delete_batch(batch_id)
                for result in results:
                    result.status = "failed"
                    result.error_message = f"Batch activation failed: {activation_error}"
                failed_count = len(results)
                success_count = 0
        else:
            logger.warning(f"{failed_count} hospitals failed. Rolling back batch {batch_id}...")
            # Rollback
            await api_client.delete_batch(batch_id)
        
        processing_time = time.time() - start_time
        
        # Build response
        bulk_response = BulkCreateResponse(
            batch_id=batch_id,
            total_hospitals=len(hospitals_data),
            processed_hospitals=success_count,
            failed_hospitals=failed_count,
            processing_time_seconds=round(processing_time, 2),
            batch_activated=batch_activated,
            hospitals=results,
        )
        
        # Update job with result
        job_repository.set_result(job_id, bulk_response)
        job_repository.update_status(job_id, JobStatus.COMPLETED)
        
        logger.info(
            f"Job {job_id} completed: {success_count} succeeded, {failed_count} failed, "
            f"batch_activated={batch_activated}"
        )
        
        return bulk_response.model_dump()
        
    except Exception as e:
        error_msg = f"Error processing hospitals: {str(e)}"
        logger.exception(f"Job {job_id} failed: {error_msg}")
        job_repository.set_error(job_id, error_msg)
        raise


async def _create_hospitals_concurrently(
    api_client: HospitalAPIClient,
    hospitals: List[HospitalCreate],
    batch_id: UUID
) -> List[HospitalProcessingResult]:
    """Create hospitals concurrently"""
    tasks = [
        _create_single_hospital(api_client, hospital, batch_id)
        for hospital in hospitals
    ]
    return await asyncio.gather(*tasks, return_exceptions=False)


async def _create_single_hospital(
    api_client: HospitalAPIClient,
    hospital_data: HospitalCreate,
    batch_id: UUID
) -> HospitalProcessingResult:
    """Create a single hospital"""
    try:
        hospital, error = await api_client.create_hospital(
            name=hospital_data.name,
            address=hospital_data.address,
            phone=hospital_data.phone,
            batch_id=batch_id
        )
        
        if hospital:
            return HospitalProcessingResult(
                row=hospital_data.row_number,
                hospital_id=hospital.id,
                name=hospital_data.name,
                status="created",
                error_message=None,
            )
        else:
            return HospitalProcessingResult(
                row=hospital_data.row_number,
                hospital_id=None,
                name=hospital_data.name,
                status="failed",
                error_message=error,
            )
    except Exception as e:
        logger.exception(f"Unexpected error creating hospital '{hospital_data.name}'")
        return HospitalProcessingResult(
            row=hospital_data.row_number,
            hospital_id=None,
            name=hospital_data.name,
            status="failed",
            error_message=f"Unexpected error: {str(e)}",
        )
