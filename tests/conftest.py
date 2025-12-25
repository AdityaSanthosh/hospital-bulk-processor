"""
Pytest configuration and shared fixtures
"""

import asyncio
import os
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.job_manager import JobManager, job_manager
from app.main import app
from app.services import HospitalAPIClient


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_client() -> Generator[TestClient, None, None]:
    """Create a test client for the FastAPI app"""
    with TestClient(app) as client:
        yield client


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_api_client() -> Mock:
    """Create a mock Hospital API client"""
    client = Mock(spec=HospitalAPIClient)
    client.base_url = "https://hospital-directory.onrender.com"
    client.timeout = 30.0
    return client


@pytest.fixture
def mock_async_api_client() -> AsyncMock:
    """Create a mock async Hospital API client"""
    client = AsyncMock(spec=HospitalAPIClient)
    client.base_url = "https://hospital-directory.onrender.com"
    client.timeout = 30.0
    return client


@pytest.fixture
def test_job_manager() -> JobManager:
    """Create a fresh job manager for testing"""
    return JobManager(max_jobs=100, job_ttl_seconds=300)


@pytest.fixture
def sample_csv_content() -> str:
    """Sample CSV content for testing"""
    return """name,address,phone
General Hospital,123 Main St,555-0101
City Medical Center,456 Oak Ave,555-0102
Community Clinic,789 Pine Rd,555-0103"""


@pytest.fixture
def sample_csv_file(tmp_path, sample_csv_content):
    """Create a temporary CSV file for testing"""
    csv_file = tmp_path / "test_hospitals.csv"
    csv_file.write_text(sample_csv_content)
    return csv_file


@pytest.fixture
def large_csv_content() -> str:
    """Large CSV content (20 hospitals) for testing"""
    lines = ["name,address,phone"]
    for i in range(1, 21):
        lines.append(f"Hospital {i},Address {i},555-{i:04d}")
    return "\n".join(lines)


@pytest.fixture
def large_csv_file(tmp_path, large_csv_content):
    """Create a large CSV file with 20 hospitals"""
    csv_file = tmp_path / "large_hospitals.csv"
    csv_file.write_text(large_csv_content)
    return csv_file


@pytest.fixture
def invalid_csv_content() -> str:
    """Invalid CSV content (missing required fields)"""
    return """name,phone
Hospital Without Address,555-0101"""


@pytest.fixture
def invalid_csv_file(tmp_path, invalid_csv_content):
    """Create an invalid CSV file"""
    csv_file = tmp_path / "invalid.csv"
    csv_file.write_text(invalid_csv_content)
    return csv_file


@pytest.fixture
def oversized_csv_content() -> str:
    """Oversized CSV content (more than 20 hospitals)"""
    lines = ["name,address,phone"]
    for i in range(1, 26):  # 25 hospitals (over limit)
        lines.append(f"Hospital {i},Address {i},555-{i:04d}")
    return "\n".join(lines)


@pytest.fixture
def oversized_csv_file(tmp_path, oversized_csv_content):
    """Create an oversized CSV file"""
    csv_file = tmp_path / "oversized.csv"
    csv_file.write_text(oversized_csv_content)
    return csv_file


@pytest.fixture
def sample_hospitals_data() -> list:
    """Sample parsed hospitals data"""
    return [
        {
            "name": "General Hospital",
            "address": "123 Main St",
            "phone": "555-0101",
            "row_number": 2,
        },
        {
            "name": "City Medical Center",
            "address": "456 Oak Ave",
            "phone": "555-0102",
            "row_number": 3,
        },
        {
            "name": "Community Clinic",
            "address": "789 Pine Rd",
            "phone": "555-0103",
            "row_number": 4,
        },
    ]


@pytest.fixture
def mock_hospital_response():
    """Mock response from hospital API"""
    from datetime import datetime
    from uuid import uuid4

    from app.models import HospitalResponse

    return HospitalResponse(
        id=123,
        name="Test Hospital",
        address="123 Test St",
        phone="555-0000",
        creation_batch_id=uuid4(),
        active=False,
        created_at=datetime.datetime.now(datetime.timezone.utc),
    )


@pytest.fixture
def mock_successful_api_calls(mock_async_api_client, mock_hospital_response):
    """Configure mock API client to return successful responses"""

    async def mock_create_hospital(*args, **kwargs):
        return (mock_hospital_response, None)

    async def mock_activate_batch(*args, **kwargs):
        return (True, None)

    async def mock_delete_batch(*args, **kwargs):
        return (True, None)

    mock_async_api_client.create_hospital.side_effect = mock_create_hospital
    mock_async_api_client.activate_batch.side_effect = mock_activate_batch
    mock_async_api_client.delete_batch.side_effect = mock_delete_batch

    return mock_async_api_client


@pytest.fixture
def mock_failed_api_calls(mock_async_api_client):
    """Configure mock API client to return failed responses"""

    async def mock_create_hospital(*args, **kwargs):
        return (None, "Connection timeout")

    async def mock_activate_batch(*args, **kwargs):
        return (False, "Activation failed")

    async def mock_delete_batch(*args, **kwargs):
        return (True, None)

    mock_async_api_client.create_hospital.side_effect = mock_create_hospital
    mock_async_api_client.activate_batch.side_effect = mock_activate_batch
    mock_async_api_client.delete_batch.side_effect = mock_delete_batch

    return mock_async_api_client


@pytest.fixture
def env_vars():
    """Set test environment variables"""
    original_env = os.environ.copy()

    # Set test environment variables
    os.environ["HOSPITAL_API_BASE_URL"] = "https://hospital-directory.onrender.com"
    os.environ["MAX_CSV_ROWS"] = "20"
    os.environ["UPLOAD_MAX_SIZE_MB"] = "5"
    os.environ["HOST"] = "0.0.0.0"
    os.environ["PORT"] = "8000"

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture(autouse=True)
def reset_job_manager():
    """Reset the global job manager before each test"""
    job_manager.jobs.clear()
    if job_manager._cleanup_task:
        job_manager._cleanup_task.cancel()
        job_manager._cleanup_task = None
    yield
    job_manager.jobs.clear()
