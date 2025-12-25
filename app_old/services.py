import asyncio
import time
from typing import Dict, List, Optional, Tuple
from uuid import UUID, uuid4

import httpx

from app.models import (
    BulkCreateResponse,
    HospitalProcessingResult,
    HospitalResponse,
    JobStatus,
)


class HospitalAPIClient:
    """Client for interacting with the Hospital Directory API"""

    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def create_hospital(
        self, name: str, address: str, phone: str | None, batch_id: UUID
    ) -> Tuple[HospitalResponse | None, str | None]:
        """
        Create a single hospital via the API.

        Returns:
            Tuple of (HospitalResponse, error_message)
        """
        url = f"{self.base_url}/hospitals/"
        payload = {
            "name": name,
            "address": address,
            "phone": phone,
            "creation_batch_id": str(batch_id),
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)

                if response.status_code == 200 or response.status_code == 201:
                    data = response.json()
                    hospital = HospitalResponse(**data)
                    return hospital, None
                else:
                    error_msg = f"API returned status {response.status_code}"
                    try:
                        error_detail = response.json()
                        error_msg = f"{error_msg}: {error_detail}"
                    except:
                        error_msg = f"{error_msg}: {response.text}"
                    return None, error_msg

        except httpx.TimeoutException:
            return None, "Request timeout"
        except httpx.RequestError as e:
            return None, f"Network error: {str(e)}"
        except Exception as e:
            return None, f"Unexpected error: {str(e)}"

    async def activate_batch(self, batch_id: UUID) -> Tuple[bool, str | None]:
        """
        Activate all hospitals in a batch.

        Returns:
            Tuple of (success, error_message)
        """
        url = f"{self.base_url}/hospitals/batch/{batch_id}/activate"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.patch(url)

                if response.status_code == 200:
                    return True, None
                else:
                    error_msg = (
                        f"Failed to activate batch. Status: {response.status_code}"
                    )
                    try:
                        error_detail = response.json()
                        error_msg = f"{error_msg}: {error_detail}"
                    except:
                        error_msg = f"{error_msg}: {response.text}"
                    return False, error_msg

        except httpx.TimeoutException:
            return False, "Request timeout while activating batch"
        except httpx.RequestError as e:
            return False, f"Network error while activating batch: {str(e)}"
        except Exception as e:
            return False, f"Unexpected error while activating batch: {str(e)}"

    async def delete_batch(self, batch_id: UUID) -> Tuple[bool, str | None]:
        """
        Delete all hospitals in a batch (rollback on failure).

        Returns:
            Tuple of (success, error_message)
        """
        url = f"{self.base_url}/hospitals/batch/{batch_id}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.delete(url)

                if response.status_code == 200 or response.status_code == 204:
                    return True, None
                else:
                    return (
                        False,
                        f"Failed to delete batch. Status: {response.status_code}",
                    )

        except Exception as e:
            return False, f"Error deleting batch: {str(e)}"


class BulkHospitalProcessor:
    """Service for processing bulk hospital creation"""

    def __init__(self, api_client: HospitalAPIClient, job_manager=None):
        self.api_client = api_client
        self.job_manager = job_manager

    async def process_bulk_upload(
        self, hospitals_data: List[Dict[str, object]], job_id: Optional[str] = None
    ) -> BulkCreateResponse:
        """
        Process bulk hospital creation with concurrent API calls.

        Args:
            hospitals_data: List of hospital data dictionaries
            job_id: Optional job ID for progress tracking

        Returns:
            BulkCreateResponse with processing results
        """
        start_time = time.time()
        batch_id = uuid4()

        # Update job status to processing
        if job_id and self.job_manager:
            self.job_manager.update_job_status(job_id, JobStatus.PROCESSING)

        # Process hospitals concurrently
        results = await self._create_hospitals_concurrently(
            hospitals_data, batch_id, job_id
        )

        # Check if all hospitals were created successfully
        failed_count = sum(1 for r in results if r.status == "failed")
        success_count = len(results) - failed_count

        batch_activated = False

        # Only activate batch if all hospitals were created successfully
        if failed_count == 0:
            activation_success, activation_error = await self.api_client.activate_batch(
                batch_id
            )

            if activation_success:
                batch_activated = True
                # Update status for all results
                for result in results:
                    result.status = "created_and_activated"
            else:
                # Activation failed - rollback by deleting the batch
                await self.api_client.delete_batch(batch_id)
                # Update all results to failed
                for result in results:
                    result.status = "failed"
                    result.error_message = (
                        f"Batch activation failed: {activation_error}"
                    )
                failed_count = len(results)
                success_count = 0
        else:
            # Some hospitals failed - delete the entire batch (rollback)
            await self.api_client.delete_batch(batch_id)

        processing_time = time.time() - start_time

        return BulkCreateResponse(
            batch_id=batch_id,
            total_hospitals=len(hospitals_data),
            processed_hospitals=success_count,
            failed_hospitals=failed_count,
            processing_time_seconds=round(processing_time, 2),
            batch_activated=batch_activated,
            hospitals=results,
        )

    async def _create_hospitals_concurrently(
        self,
        hospitals_data: List[Dict[str, any]],
        batch_id: UUID,
        job_id: Optional[str] = None,
    ) -> List[HospitalProcessingResult]:
        """
        Create hospitals concurrently using asyncio.gather.

        Args:
            hospitals_data: List of hospital data
            batch_id: UUID for the batch
            job_id: Optional job ID for progress tracking

        Returns:
            List of HospitalProcessingResult
        """
        # Create tasks for concurrent execution
        tasks = [
            self._create_single_hospital(hospital_data, batch_id, job_id)
            for hospital_data in hospitals_data
        ]

        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results and handle any exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Handle unexpected exceptions
                processed_results.append(
                    HospitalProcessingResult(
                        row=hospitals_data[i]["row_number"],
                        hospital_id=None,
                        name=hospitals_data[i]["name"],
                        status="failed",
                        error_message=f"Unexpected error: {str(result)}",
                    )
                )
            else:
                processed_results.append(result)

        return processed_results

    async def _create_single_hospital(
        self,
        hospital_data: Dict[str, any],
        batch_id: UUID,
        job_id: Optional[str] = None,
    ) -> HospitalProcessingResult:
        """
        Create a single hospital and return the result.

        Args:
            hospital_data: Dictionary with hospital information
            batch_id: UUID for the batch
            job_id: Optional job ID for progress tracking

        Returns:
            HospitalProcessingResult
        """
        name = hospital_data["name"]
        address = hospital_data["address"]
        phone = hospital_data.get("phone")
        row_number = hospital_data["row_number"]

        hospital, error = await self.api_client.create_hospital(
            name=name, address=address, phone=phone, batch_id=batch_id
        )

        # Update progress if job tracking is enabled
        if job_id and self.job_manager:
            success = hospital is not None
            self.job_manager.update_job_progress(
                job_id=job_id, hospital_name=name, success=success, error_message=error
            )

        if hospital:
            return HospitalProcessingResult(
                row=row_number,
                hospital_id=hospital.id,
                name=name,
                status="created",  # Will be updated to "created_and_activated" after batch activation
                error_message=None,
            )
        else:
            return HospitalProcessingResult(
                row=row_number,
                hospital_id=None,
                name=name,
                status="failed",
                error_message=error,
            )
