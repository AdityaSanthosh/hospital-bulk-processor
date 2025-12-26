"""Celery tasks"""

import asyncio
import logging
import time
from typing import Any, List
from uuid import UUID, uuid4

# if TYPE_CHECKING:
#     from celery import Task
from app.domain.schemas import (
    BulkCreateResponse,
    HospitalCreate,
    HospitalProcessingResult,
    JobStatus,
)
from app.external.hospital_api_client import HospitalAPIClient
from app.repositories.job_repository import job_repository
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="process_bulk_hospitals")
def process_bulk_hospitals_task(job_id: str, hospitals_data: List[dict]) -> Any:
    """
    Celery task to process bulk hospital uploads

    Args:
        job_id: Job identifier
        hospitals_data: List of hospital dictionaries
    """
    logger.info(
        f"Starting Celery task for job {job_id} with {len(hospitals_data)} hospitals"
    )

    # Run async code in event loop
    result = asyncio.run(_process_hospitals_async(job_id, hospitals_data))

    logger.info(f"Completed Celery task for job {job_id}")
    return result


async def _process_hospitals_async(job_id: str, hospitals_data: List[dict]):
    """
    Async hospital processing logic with auto-activation and graceful fallback

    Flow:
    1. Create all hospitals
    2. If all succeed: Try to auto-activate
       - If activation succeeds: Mark as "created_and_activated"
       - If activation fails: Keep as "created", user can manually activate
    3. If some fail: Don't activate, user can review and manually activate
    4. Never rollback - hospitals persist regardless of activation status
    """
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
        logger.info(
            f"Processing {len(hospitals)} hospitals concurrently for job {job_id}"
        )
        results = await _create_hospitals_concurrently(api_client, hospitals, batch_id)

        # Calculate results
        failed_count = sum(1 for r in results if r.status == "failed")
        success_count = len(results) - failed_count

        batch_activated = False
        activation_attempted = False

        # Try to auto-activate ONLY if all succeeded
        if failed_count == 0:
            logger.info(
                f"All hospitals created successfully. Attempting to auto-activate batch {batch_id}..."
            )
            activation_attempted = True

            try:
                activation_success, activation_error = await api_client.activate_batch(
                    batch_id
                )

                if activation_success:
                    batch_activated = True
                    # Update all hospital results to indicate activation
                    for result in results:
                        result.status = "created_and_activated"
                    logger.info(f"✅ Batch {batch_id} auto-activated successfully")
                else:
                    logger.warning(
                        f"⚠️  Auto-activation failed: {activation_error}. "
                        f"Batch {batch_id} is created but NOT activated. "
                        f"User can manually activate via PATCH /batch/{batch_id}/activate"
                    )
                    # Keep hospitals as "created" (don't rollback)

            except Exception as e:
                logger.error(
                    f"⚠️  Exception during auto-activation: {e}. "
                    f"Batch {batch_id} is created but NOT activated. "
                    f"User can manually activate later."
                )
                # Keep hospitals as "created" (don't rollback)
        else:
            logger.info(
                f"ℹ️  {failed_count} hospitals failed. Batch {batch_id} created but NOT activated. "
                f"User can review failures and decide whether to manually activate."
            )

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

        # Log final status
        if batch_activated:
            logger.info(
                f"✅ Job {job_id} completed: {success_count} succeeded, {failed_count} failed, "
                f"batch ACTIVATED"
            )
        elif activation_attempted:
            logger.warning(
                f"⚠️  Job {job_id} completed: {success_count} succeeded, {failed_count} failed, "
                f"batch created but ACTIVATION FAILED. Manual activation available at "
                f"PATCH /batch/{batch_id}/activate"
            )
        else:
            logger.info(
                f"ℹ️  Job {job_id} completed: {success_count} succeeded, {failed_count} failed, "
                f"batch created but NOT activated (had failures). Manual activation available at "
                f"PATCH /batch/{batch_id}/activate"
            )

        return bulk_response.model_dump()

    except Exception as e:
        error_msg = f"Error processing hospitals: {str(e)}"
        logger.exception(f"Job {job_id} failed: {error_msg}")
        job_repository.set_error(job_id, error_msg)
        raise


async def _create_hospitals_concurrently(
    api_client: HospitalAPIClient, hospitals: List[HospitalCreate], batch_id: UUID
) -> List[HospitalProcessingResult]:
    """Create hospitals concurrently"""
    tasks = [
        _create_single_hospital(api_client, hospital, batch_id)
        for hospital in hospitals
    ]
    return await asyncio.gather(*tasks, return_exceptions=False)


async def _create_single_hospital(
    api_client: HospitalAPIClient, hospital_data: HospitalCreate, batch_id: UUID
) -> HospitalProcessingResult:
    """Create a single hospital"""
    try:
        hospital, error = await api_client.create_hospital(
            name=hospital_data.name,
            address=hospital_data.address,
            phone=hospital_data.phone,
            batch_id=batch_id,
        )

        if hospital:
            return HospitalProcessingResult(
                row=hospital_data.row_number,
                hospital_id=hospital.id,
                name=hospital_data.name,
                status="created",  # Will be updated to "created_and_activated" if auto-activation succeeds
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
