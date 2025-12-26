"""Hospital API Client with resilience patterns"""

import logging
from typing import Optional, Tuple
from uuid import UUID

import httpx
from tenacity import (
    before_sleep_log,
    retry,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings
from app.core.resilience import (
    hospital_api_circuit_breaker,
    rate_limiter,
)
from app.domain.exceptions import ExternalAPIException
from app.domain.schemas import HospitalResponse

logger = logging.getLogger(__name__)


class HospitalAPIClient:
    """Client for Hospital Directory API with resilience patterns"""

    def __init__(self):
        self.base_url = settings.hospital_api_base_url.rstrip("/")
        self.timeout = settings.hospital_api_timeout
        logger.info(f"Hospital API Client initialized: {self.base_url}")

    @hospital_api_circuit_breaker
    @retry(
        stop=stop_after_attempt(settings.retry_max_attempts),
        wait=wait_exponential(
            min=settings.retry_min_wait,
            max=settings.retry_max_wait,
        ),
        before_sleep=before_sleep_log(logger, logging.INFO),
        reraise=True,
    )
    async def create_hospital(
        self, name: str, address: str, phone: Optional[str], batch_id: UUID
    ) -> Tuple[Optional[HospitalResponse], Optional[str]]:
        """
        Create a single hospital with retry and circuit breaker

        Returns:
            Tuple of (HospitalResponse, error_message)
        """
        # Apply rate limiting
        await rate_limiter.acquire()

        url = f"{self.base_url}/hospitals/"
        payload = {
            "name": name,
            "address": address,
            "phone": phone,
            "creation_batch_id": str(batch_id),
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.debug(f"Creating hospital: {name}")
                response = await client.post(url, json=payload)

                if response.status_code in [200, 201]:
                    data = response.json()
                    hospital = HospitalResponse(**data)
                    logger.info(
                        f"Hospital created successfully: {name} (ID: {hospital.id})"
                    )
                    return hospital, None
                else:
                    error_msg = f"API returned status {response.status_code}"
                    try:
                        error_data = response.json()
                        error_msg = f"{error_msg}: {error_data}"
                    except Exception:
                        error_msg = f"{error_msg}: {response.text}"

                    logger.error(f"Failed to create hospital '{name}': {error_msg}")
                    return None, error_msg

        except httpx.TimeoutException as e:
            error_msg = f"Request timeout: {str(e)}"
            logger.error(f"Timeout creating hospital '{name}': {error_msg}")
            raise ExternalAPIException(error_msg)
        except httpx.RequestError as e:
            error_msg = f"Request error: {str(e)}"
            logger.error(f"Request error creating hospital '{name}': {error_msg}")
            raise ExternalAPIException(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"Unexpected error creating hospital '{name}': {error_msg}")
            raise ExternalAPIException(error_msg)

    @hospital_api_circuit_breaker
    @retry(
        stop=stop_after_attempt(settings.retry_max_attempts),
        wait=wait_exponential(
            min=settings.retry_min_wait,
            max=settings.retry_max_wait,
        ),
        before_sleep=before_sleep_log(logger, logging.INFO),
        reraise=True,
    )
    async def activate_batch(self, batch_id: UUID) -> Tuple[bool, Optional[str]]:
        """
        Activate a batch with retry and circuit breaker

        Returns:
            Tuple of (success, error_message)
        """
        await rate_limiter.acquire()

        url = f"{self.base_url}/batches/{batch_id}/activate"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.debug(f"Activating batch: {batch_id}")
                response = await client.post(url)

                if response.status_code in [200, 204]:
                    logger.info(f"Batch activated successfully: {batch_id}")
                    return True, None
                else:
                    error_msg = f"API returned status {response.status_code}"
                    try:
                        error_data = response.json()
                        error_msg = f"{error_msg}: {error_data}"
                    except Exception:
                        error_msg = f"{error_msg}: {response.text}"

                    logger.error(f"Failed to activate batch {batch_id}: {error_msg}")
                    return False, error_msg

        except Exception as e:
            error_msg = f"Error activating batch: {str(e)}"
            logger.error(f"Error activating batch {batch_id}: {error_msg}")
            return False, error_msg

    @hospital_api_circuit_breaker
    @retry(
        stop=stop_after_attempt(settings.retry_max_attempts),
        wait=wait_exponential(
            min=settings.retry_min_wait,
            max=settings.retry_max_wait,
        ),
        before_sleep=before_sleep_log(logger, logging.INFO),
        reraise=True,
    )
    async def delete_batch(self, batch_id: UUID) -> Tuple[bool, Optional[str]]:
        """
        Delete a batch (rollback) with retry and circuit breaker

        Returns:
            Tuple of (success, error_message)
        """
        await rate_limiter.acquire()

        url = f"{self.base_url}/batches/{batch_id}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.debug(f"Deleting batch: {batch_id}")
                response = await client.delete(url)

                if response.status_code in [200, 204]:
                    logger.info(f"Batch deleted successfully: {batch_id}")
                    return True, None
                else:
                    error_msg = f"API returned status {response.status_code}"
                    try:
                        error_data = response.json()
                        error_msg = f"{error_msg}: {error_data}"
                    except Exception:
                        error_msg = f"{error_msg}: {response.text}"

                    logger.warning(f"Failed to delete batch {batch_id}: {error_msg}")
                    return False, error_msg

        except Exception as e:
            error_msg = f"Error deleting batch: {str(e)}"
            logger.warning(f"Error deleting batch {batch_id}: {error_msg}")
            return False, error_msg
