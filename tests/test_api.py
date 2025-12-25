"""
API Integration Tests
Tests for FastAPI endpoints and HTTP interactions
"""

import asyncio
from io import BytesIO

import pytest



@pytest.mark.integration
class TestHealthEndpoints:
    """Test health and info endpoints"""

    @pytest.mark.asyncio
    async def test_root_endpoint(self, async_client):
        """Test root endpoint returns API information"""
        response = await async_client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Hospital Bulk Processor API"
        assert data["version"] == "1.0.0"
        assert data["status"] == "running"
        assert "endpoints" in data

    @pytest.mark.asyncio
    async def test_health_endpoint(self, async_client):
        """Test health check endpoint"""
        response = await async_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "hospital_api_url" in data
        assert "max_csv_rows" in data
        assert "job_stats" in data

    @pytest.mark.asyncio
    async def test_docs_endpoint_accessible(self, async_client):
        """Test that API docs are accessible"""
        response = await async_client.get("/docs")

        assert response.status_code == 200
        assert "html" in response.headers["content-type"]


@pytest.mark.integration
class TestBulkUploadEndpoint:
    """Test bulk hospital upload endpoint"""

    @pytest.mark.asyncio
    async def test_upload_csv_returns_job_id(self, async_client, sample_csv_file):
        """Test that CSV upload returns job ID immediately"""
        with open(sample_csv_file, "rb") as f:
            response = await async_client.post(
                "/hospitals/bulk",
                files={"file": ("test.csv", f, "text/csv")},
            )

        assert response.status_code == 202
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "pending"
        assert data["total_hospitals"] == 3
        assert "Use the job_id to check status" in data["message"]

    @pytest.mark.asyncio
    async def test_upload_invalid_file_type(self, async_client, tmp_path):
        """Test upload with invalid file type"""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("name,address,phone\nHospital,Address,Phone")

        with open(txt_file, "rb") as f:
            response = await async_client.post(
                "/hospitals/bulk",
                files={"file": ("test.txt", f, "text/plain")},
            )

        assert response.status_code == 400
        assert "csv" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_upload_missing_required_columns(self, async_client, tmp_path):
        """Test upload with missing required columns"""
        csv_file = tmp_path / "missing.csv"
        csv_file.write_text("name,phone\nHospital,555-0000")

        with open(csv_file, "rb") as f:
            response = await async_client.post(
                "/hospitals/bulk",
                files={"file": ("missing.csv", f, "text/csv")},
            )

        assert response.status_code == 400
        assert "address" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_upload_oversized_csv(self, async_client, oversized_csv_file):
        """Test upload with too many rows"""
        with open(oversized_csv_file, "rb") as f:
            response = await async_client.post(
                "/hospitals/bulk",
                files={"file": ("oversized.csv", f, "text/csv")},
            )

        assert response.status_code == 400
        assert "maximum" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_upload_empty_csv(self, async_client, tmp_path):
        """Test upload with empty CSV"""
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("name,address,phone")

        with open(csv_file, "rb") as f:
            response = await async_client.post(
                "/hospitals/bulk",
                files={"file": ("empty.csv", f, "text/csv")},
            )

        assert response.status_code == 400
        assert "no valid data" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_upload_csv_with_optional_phone(self, async_client, tmp_path):
        """Test upload with optional phone field missing"""
        csv_file = tmp_path / "no_phone.csv"
        csv_file.write_text("name,address,phone\nHospital,Address,")

        with open(csv_file, "rb") as f:
            response = await async_client.post(
                "/hospitals/bulk",
                files={"file": ("no_phone.csv", f, "text/csv")},
            )

        assert response.status_code == 202
        data = response.json()
        assert data["total_hospitals"] == 1

    @pytest.mark.asyncio
    async def test_upload_without_file(self, async_client):
        """Test upload endpoint without file"""
        response = await async_client.post("/hospitals/bulk")

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_upload_large_valid_csv(self, async_client, large_csv_file):
        """Test upload with maximum allowed rows (20)"""
        with open(large_csv_file, "rb") as f:
            response = await async_client.post(
                "/hospitals/bulk",
                files={"file": ("large.csv", f, "text/csv")},
            )

        assert response.status_code == 202
        data = response.json()
        assert data["total_hospitals"] == 20


@pytest.mark.integration
class TestStatusEndpoint:
    """Test job status polling endpoint"""

    @pytest.mark.asyncio
    async def test_get_status_after_upload(self, async_client, sample_csv_file):
        """Test getting status after CSV upload"""
        # Upload CSV
        with open(sample_csv_file, "rb") as f:
            upload_response = await async_client.post(
                "/hospitals/bulk",
                files={"file": ("test.csv", f, "text/csv")},
            )

        job_id = upload_response.json()["job_id"]

        # Get status
        status_response = await async_client.get(f"/hospitals/bulk/status/{job_id}")

        assert status_response.status_code == 200
        data = status_response.json()
        assert data["job_id"] == job_id
        assert data["status"] in ["pending", "processing", "completed", "failed"]
        assert data["total_hospitals"] == 3
        assert "progress_percentage" in data

    @pytest.mark.asyncio
    async def test_get_status_nonexistent_job(self, async_client):
        """Test getting status of non-existent job"""
        response = await async_client.get("/hospitals/bulk/status/fake-job-id")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_status_includes_progress_info(self, async_client, sample_csv_file):
        """Test that status includes all progress information"""
        # Upload CSV
        with open(sample_csv_file, "rb") as f:
            upload_response = await async_client.post(
                "/hospitals/bulk",
                files={"file": ("test.csv", f, "text/csv")},
            )

        job_id = upload_response.json()["job_id"]

        # Get status
        status_response = await async_client.get(f"/hospitals/bulk/status/{job_id}")

        data = status_response.json()
        assert "progress_percentage" in data
        assert "processed_hospitals" in data
        assert "failed_hospitals" in data
        assert "message" in data
        assert "started_at" in data

    @pytest.mark.asyncio
    async def test_status_includes_eta_during_processing(
        self, async_client, large_csv_file
    ):
        """Test that status includes ETA during processing"""
        # Upload large CSV
        with open(large_csv_file, "rb") as f:
            upload_response = await async_client.post(
                "/hospitals/bulk",
                files={"file": ("large.csv", f, "text/csv")},
            )

        job_id = upload_response.json()["job_id"]

        # Wait a bit for processing to start
        await asyncio.sleep(1)

        # Get status
        status_response = await async_client.get(f"/hospitals/bulk/status/{job_id}")

        data = status_response.json()
        # ETA should be present if processing
        if data["status"] == "processing" and data["processed_hospitals"] > 0:
            assert "estimated_time_remaining_seconds" in data


@pytest.mark.integration
class TestAllJobsEndpoint:
    """Test endpoint to get all jobs"""

    @pytest.mark.asyncio
    async def test_get_all_jobs_empty(self, async_client, reset_job_manager):
        """Test getting all jobs when none exist"""
        response = await async_client.get("/hospitals/bulk/jobs")

        assert response.status_code == 200
        data = response.json()
        assert data["total_jobs"] == 0
        assert "stats" in data
        assert "jobs" in data

    @pytest.mark.asyncio
    async def test_get_all_jobs_after_uploads(
        self, async_client, sample_csv_file, reset_job_manager
    ):
        """Test getting all jobs after multiple uploads"""
        # Upload multiple CSVs
        for i in range(3):
            with open(sample_csv_file, "rb") as f:
                await async_client.post(
                    "/hospitals/bulk",
                    files={"file": (f"test{i}.csv", f, "text/csv")},
                )

        # Get all jobs
        response = await async_client.get("/hospitals/bulk/jobs")

        assert response.status_code == 200
        data = response.json()
        assert data["total_jobs"] >= 3
        assert len(data["jobs"]) >= 3

    @pytest.mark.asyncio
    async def test_all_jobs_includes_stats(self, async_client, sample_csv_file):
        """Test that all jobs endpoint includes statistics"""
        # Upload CSV
        with open(sample_csv_file, "rb") as f:
            await async_client.post(
                "/hospitals/bulk",
                files={"file": ("test.csv", f, "text/csv")},
            )

        # Get all jobs
        response = await async_client.get("/hospitals/bulk/jobs")

        data = response.json()
        assert "stats" in data
        stats = data["stats"]
        assert "total_jobs" in stats
        assert "pending_jobs" in stats
        assert "processing_jobs" in stats
        assert "completed_jobs" in stats
        assert "failed_jobs" in stats


@pytest.mark.integration
class TestBackgroundProcessing:
    """Test background job processing"""

    @pytest.mark.asyncio
    async def test_background_task_starts_immediately(
        self, async_client, sample_csv_file
    ):
        """Test that background processing starts after upload"""
        # Upload CSV
        with open(sample_csv_file, "rb") as f:
            upload_response = await async_client.post(
                "/hospitals/bulk",
                files={"file": ("test.csv", f, "text/csv")},
            )

        job_id = upload_response.json()["job_id"]

        # Wait a moment
        await asyncio.sleep(0.5)

        # Check status - should be processing or completed
        status_response = await async_client.get(f"/hospitals/bulk/status/{job_id}")

        data = status_response.json()
        # Job should have started
        assert data["status"] in ["processing", "completed", "failed"]

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_job_completes_eventually(self, async_client, sample_csv_file):
        """Test that job completes successfully"""
        # Upload CSV
        with open(sample_csv_file, "rb") as f:
            upload_response = await async_client.post(
                "/hospitals/bulk",
                files={"file": ("test.csv", f, "text/csv")},
            )

        job_id = upload_response.json()["job_id"]

        # Poll until completion (with timeout)
        max_wait = 60
        waited = 0

        while waited < max_wait:
            status_response = await async_client.get(f"/hospitals/bulk/status/{job_id}")
            data = status_response.json()

            if data["status"] in ["completed", "failed"]:
                break

            await asyncio.sleep(1)
            waited += 1

        # Should be complete
        assert data["status"] in ["completed", "failed"]
        if data["status"] == "completed":
            assert data["result"] is not None


@pytest.mark.integration
class TestConcurrentUploads:
    """Test concurrent CSV uploads"""

    @pytest.mark.asyncio
    async def test_multiple_concurrent_uploads(
        self, async_client, sample_csv_file, reset_job_manager
    ):
        """Test uploading multiple CSVs concurrently"""
        # Upload 5 CSVs concurrently
        tasks = []
        for i in range(5):
            with open(sample_csv_file, "rb") as f:
                content = f.read()

            async def upload_csv(content, name):
                return await async_client.post(
                    "/hospitals/bulk",
                    files={"file": (name, BytesIO(content), "text/csv")},
                )

            tasks.append(upload_csv(content, f"test{i}.csv"))

        responses = await asyncio.gather(*tasks)

        # All should succeed
        for response in responses:
            assert response.status_code == 202
            assert "job_id" in response.json()

        # Verify all jobs are tracked
        all_jobs_response = await async_client.get("/hospitals/bulk/jobs")
        data = all_jobs_response.json()
        assert data["total_jobs"] >= 5


@pytest.mark.integration
class TestErrorHandling:
    """Test API error handling"""

    @pytest.mark.asyncio
    async def test_invalid_csv_format_error(self, async_client, tmp_path):
        """Test error handling for invalid CSV format"""
        csv_file = tmp_path / "invalid.csv"
        csv_file.write_text("not,a,valid\ncsv,format,file")

        with open(csv_file, "rb") as f:
            response = await async_client.post(
                "/hospitals/bulk",
                files={"file": ("invalid.csv", f, "text/csv")},
            )

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "error_type" in data

    @pytest.mark.asyncio
    async def test_malformed_csv_error(self, async_client, tmp_path):
        """Test error handling for malformed CSV"""
        csv_file = tmp_path / "malformed.csv"
        csv_file.write_text("name,address,phone\n,,,\nHospital,,")

        with open(csv_file, "rb") as f:
            response = await async_client.post(
                "/hospitals/bulk",
                files={"file": ("malformed.csv", f, "text/csv")},
            )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_status_endpoint_error_for_invalid_id(self, async_client):
        """Test status endpoint with invalid job ID"""
        response = await async_client.get("/hospitals/bulk/status/invalid-format-123")

        assert response.status_code == 404
        data = response.json()
        assert "error_type" in data


@pytest.mark.integration
class TestAPIDocumentation:
    """Test API documentation and OpenAPI schema"""

    @pytest.mark.asyncio
    async def test_openapi_schema_available(self, async_client):
        """Test that OpenAPI schema is available"""
        response = await async_client.get("/openapi.json")

        assert response.status_code == 200
        schema = response.json()
        assert "openapi" in schema
        assert "paths" in schema
        assert "/hospitals/bulk" in schema["paths"]
        assert "/hospitals/bulk/status/{job_id}" in schema["paths"]

    @pytest.mark.asyncio
    async def test_swagger_ui_available(self, async_client):
        """Test that Swagger UI is accessible"""
        response = await async_client.get("/docs")

        assert response.status_code == 200
        assert "html" in response.headers["content-type"].lower()

    @pytest.mark.asyncio
    async def test_redoc_available(self, async_client):
        """Test that ReDoc is accessible"""
        response = await async_client.get("/redoc")

        assert response.status_code == 200
        assert "html" in response.headers["content-type"].lower()


@pytest.mark.integration
class TestRateLimitAndPerformance:
    """Test rate limiting and performance characteristics"""

    @pytest.mark.asyncio
    async def test_rapid_status_checks(self, async_client, sample_csv_file):
        """Test rapid consecutive status checks"""
        # Upload CSV
        with open(sample_csv_file, "rb") as f:
            upload_response = await async_client.post(
                "/hospitals/bulk",
                files={"file": ("test.csv", f, "text/csv")},
            )

        job_id = upload_response.json()["job_id"]

        # Make 50 rapid status checks
        tasks = [
            async_client.get(f"/hospitals/bulk/status/{job_id}") for _ in range(50)
        ]

        responses = await asyncio.gather(*tasks)

        # All should succeed
        for response in responses:
            assert response.status_code in [200, 404]  # 404 if job expired

    @pytest.mark.asyncio
    async def test_health_check_performance(self, async_client):
        """Test health check endpoint response time"""
        import time

        start = time.time()
        response = await async_client.get("/health")
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 1.0  # Should respond quickly
