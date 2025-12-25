# 🧪 Testing Guide

Comprehensive testing documentation for the Hospital Bulk Processor API.

## Table of Contents

- [Overview](#overview)
- [Test Structure](#test-structure)
- [Running Tests](#running-tests)
- [Test Categories](#test-categories)
- [Writing Tests](#writing-tests)
- [Test Coverage](#test-coverage)
- [Continuous Integration](#continuous-integration)

## Overview

This project uses **pytest** as the testing framework with comprehensive test coverage including:

- ✅ Unit tests for models, utilities, and business logic
- ✅ Integration tests for API endpoints
- ✅ Polling endpoint tests for progress tracking
- ✅ Performance tests
- ✅ Error handling tests

## Test Structure

```
tests/
├── __init__.py           # Test package initialization
├── conftest.py          # Pytest fixtures and configuration
├── test_unit.py         # Unit tests (models, job manager, utilities)
├── test_api.py          # API integration tests
└── test_polling.py      # Polling endpoint tests
```

### Test Configuration

- **pytest.ini**: Main pytest configuration
- **conftest.py**: Shared fixtures and test utilities
- **Coverage**: Configured to track coverage across all app modules

## Running Tests

### Prerequisites

```bash
# Install dependencies (including test dependencies)
pip install -r requirements.txt
```

### Run All Tests

```bash
# Run all tests with verbose output
pytest

# Run with coverage report
pytest --cov=app --cov-report=term-missing

# Run with detailed output
pytest -v
```

### Run Specific Test Categories

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only polling tests
pytest -m polling

# Run only async tests
pytest -m asyncio

# Exclude slow tests
pytest -m "not slow"
```

### Run Specific Test Files

```bash
# Run unit tests only
pytest tests/test_unit.py

# Run API tests only
pytest tests/test_api.py

# Run polling tests only
pytest tests/test_polling.py
```

### Run Specific Test Classes or Functions

```bash
# Run a specific test class
pytest tests/test_unit.py::TestModels

# Run a specific test function
pytest tests/test_unit.py::TestModels::test_hospital_create_request

# Run tests matching a pattern
pytest -k "test_upload"
```

### Docker Testing

```bash
# Run tests in Docker container
docker-compose exec app pytest

# Run with coverage in Docker
docker-compose exec app pytest --cov=app

# Or using Make
make test
```

## Test Categories

### Unit Tests (`test_unit.py`)

**Purpose**: Test individual components in isolation

**Coverage**:
- Pydantic models validation
- Job and JobManager functionality
- CSV validation utilities
- Progress calculation
- Status message generation

**Examples**:
```bash
# Run all unit tests
pytest tests/test_unit.py -v

# Run only model tests
pytest tests/test_unit.py::TestModels -v

# Run only job manager tests
pytest tests/test_unit.py::TestJobManager -v
```

**Key Tests**:
- `test_hospital_create_request`: Validates hospital creation model
- `test_job_progress_percentage`: Tests progress calculation
- `test_job_update_progress`: Tests progress tracking
- `test_validate_csv_success`: Tests CSV validation

### Integration Tests (`test_api.py`)

**Purpose**: Test API endpoints and HTTP interactions

**Coverage**:
- Health and info endpoints
- CSV upload endpoint
- Job status endpoint
- All jobs endpoint
- Background processing
- Error handling

**Examples**:
```bash
# Run all API tests
pytest tests/test_api.py -v

# Run only upload tests
pytest tests/test_api.py::TestBulkUploadEndpoint -v

# Run error handling tests
pytest tests/test_api.py::TestErrorHandling -v
```

**Key Tests**:
- `test_upload_csv_returns_job_id`: Tests CSV upload returns job ID
- `test_upload_invalid_file_type`: Tests file validation
- `test_get_status_after_upload`: Tests status polling
- `test_multiple_concurrent_uploads`: Tests concurrent uploads

### Polling Tests (`test_polling.py`)

**Purpose**: Test progress tracking and polling functionality

**Coverage**:
- Job status polling
- Progress updates
- ETA calculation
- Recent updates tracking
- Job lifecycle management

**Examples**:
```bash
# Run all polling tests
pytest tests/test_polling.py -v

# Run only progress tracking tests
pytest -k "progress" tests/test_polling.py -v

# Run performance tests
pytest tests/test_polling.py::TestPollingPerformance -v
```

**Key Tests**:
- `test_poll_job_until_completion`: Tests complete polling workflow
- `test_progress_updates_during_processing`: Tests real-time updates
- `test_estimated_time_remaining`: Tests ETA calculation
- `test_status_endpoint_response_time`: Tests performance

## Writing Tests

### Basic Test Structure

```python
import pytest
from app.models import JobStatus

class TestYourFeature:
    """Test description"""
    
    def test_something(self):
        """Test a synchronous function"""
        result = your_function()
        assert result == expected
    
    @pytest.mark.asyncio
    async def test_async_something(self):
        """Test an async function"""
        result = await your_async_function()
        assert result == expected
```

### Using Fixtures

```python
@pytest.mark.asyncio
async def test_with_fixtures(async_client, sample_csv_file):
    """Test using fixtures from conftest.py"""
    with open(sample_csv_file, 'rb') as f:
        response = await async_client.post(
            "/hospitals/bulk",
            files={"file": ("test.csv", f, "text/csv")}
        )
    
    assert response.status_code == 202
```

### Available Fixtures

From `conftest.py`:

- `test_client`: Synchronous FastAPI test client
- `async_client`: Async FastAPI test client
- `test_job_manager`: Fresh job manager instance
- `sample_csv_file`: Sample CSV with 3 hospitals
- `large_csv_file`: Large CSV with 20 hospitals
- `invalid_csv_file`: Invalid CSV for error testing
- `mock_successful_api_calls`: Mock successful API responses
- `mock_failed_api_calls`: Mock failed API responses

### Marking Tests

```python
@pytest.mark.unit
def test_unit_functionality():
    """Mark as unit test"""
    pass

@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_endpoint():
    """Mark as integration and async test"""
    pass

@pytest.mark.slow
def test_long_running():
    """Mark as slow test"""
    pass

@pytest.mark.polling
def test_polling_feature():
    """Mark as polling test"""
    pass
```

### Testing Error Scenarios

```python
import pytest
from fastapi import HTTPException

@pytest.mark.asyncio
async def test_error_handling(async_client, invalid_csv_file):
    """Test that errors are handled correctly"""
    with open(invalid_csv_file, 'rb') as f:
        response = await async_client.post(
            "/hospitals/bulk",
            files={"file": ("invalid.csv", f, "text/csv")}
        )
    
    assert response.status_code == 400
    assert "error" in response.json()
```

## Test Coverage

### View Coverage Report

```bash
# Terminal report
pytest --cov=app --cov-report=term-missing

# HTML report (opens in browser)
pytest --cov=app --cov-report=html
open htmlcov/index.html

# XML report (for CI/CD)
pytest --cov=app --cov-report=xml
```

### Coverage Goals

- **Overall**: > 80%
- **Models**: > 95%
- **Core Logic**: > 85%
- **API Endpoints**: > 80%

### Current Coverage

Run this to see current coverage:
```bash
pytest --cov=app --cov-report=term-missing
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.10
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    
    - name: Run tests
      run: |
        pytest --cov=app --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v2
      with:
        file: ./coverage.xml
```

### Pre-commit Hooks

Create `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: pytest-check
        name: pytest-check
        entry: pytest
        language: system
        pass_filenames: false
        always_run: true
        args: ["-x", "--tb=short"]
```

Install:
```bash
pip install pre-commit
pre-commit install
```

## Test Commands Reference

### Quick Commands

```bash
# Fast: Run only unit tests
pytest tests/test_unit.py -v

# Medium: Run unit + API tests
pytest tests/test_unit.py tests/test_api.py -v

# Full: Run all tests with coverage
pytest --cov=app --cov-report=term-missing

# Watch mode (requires pytest-watch)
ptw -- -v

# Parallel execution (requires pytest-xdist)
pytest -n auto
```

### Common Patterns

```bash
# Run specific test by name
pytest -k "test_upload_csv" -v

# Run tests that failed last time
pytest --lf

# Run tests in order of last failure
pytest --ff

# Stop on first failure
pytest -x

# Show local variables on failure
pytest -l

# Verbose with captured output
pytest -vv -s

# Generate test report
pytest --html=report.html --self-contained-html
```

### Debug Mode

```bash
# Drop into debugger on failure
pytest --pdb

# Drop into debugger at start of test
pytest --trace

# Print all output (disable capture)
pytest -s

# Show 10 slowest tests
pytest --durations=10
```

## Best Practices

### 1. Test Isolation

```python
# Good: Each test is independent
def test_feature_a():
    job = create_job()
    assert job.status == "pending"

def test_feature_b():
    job = create_job()  # Fresh instance
    assert job.total_hospitals == 10

# Bad: Tests depend on each other
job = None

def test_setup():
    global job
    job = create_job()

def test_use_job():
    assert job.status == "pending"  # Depends on test_setup
```

### 2. Clear Test Names

```python
# Good: Descriptive names
def test_upload_csv_returns_job_id_with_status_202():
    pass

def test_job_progress_increases_after_hospital_processing():
    pass

# Bad: Unclear names
def test_1():
    pass

def test_stuff():
    pass
```

### 3. Arrange-Act-Assert Pattern

```python
def test_job_progress_calculation():
    # Arrange: Set up test data
    job = Job(job_id="test-123", total_hospitals=10)
    job.processed_hospitals = 5
    
    # Act: Execute the functionality
    progress = job.progress_percentage
    
    # Assert: Verify the results
    assert progress == 50.0
```

### 4. Test One Thing

```python
# Good: Tests one specific behavior
def test_job_progress_is_zero_initially():
    job = Job(job_id="test", total_hospitals=10)
    assert job.progress_percentage == 0.0

def test_job_progress_is_fifty_at_midpoint():
    job = Job(job_id="test", total_hospitals=10)
    job.processed_hospitals = 5
    assert job.progress_percentage == 50.0

# Bad: Tests multiple things
def test_job_progress():
    job = Job(job_id="test", total_hospitals=10)
    assert job.progress_percentage == 0.0
    job.processed_hospitals = 5
    assert job.progress_percentage == 50.0
    job.processed_hospitals = 10
    assert job.progress_percentage == 100.0
```

### 5. Use Fixtures for Setup

```python
# Good: Use fixtures
@pytest.fixture
def job_with_progress():
    job = Job(job_id="test", total_hospitals=10)
    job.processed_hospitals = 5
    return job

def test_job_at_50_percent(job_with_progress):
    assert job_with_progress.progress_percentage == 50.0

# Bad: Duplicate setup in each test
def test_1():
    job = Job(job_id="test", total_hospitals=10)
    job.processed_hospitals = 5
    assert job.progress_percentage == 50.0

def test_2():
    job = Job(job_id="test", total_hospitals=10)
    job.processed_hospitals = 5
    assert job.current_hospital is not None
```

## Troubleshooting

### Tests Fail Locally But Pass in CI

```bash
# Ensure clean environment
rm -rf .pytest_cache __pycache__
pip install -r requirements.txt --force-reinstall
pytest
```

### Import Errors

```bash
# Add project to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest

# Or use editable install
pip install -e .
```

### Async Tests Not Running

```bash
# Install pytest-asyncio
pip install pytest-asyncio

# Ensure pytest.ini has asyncio_mode = auto
```

### Slow Tests

```bash
# Find slow tests
pytest --durations=10

# Run only fast tests
pytest -m "not slow"

# Use parallel execution
pip install pytest-xdist
pytest -n auto
```

## Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Pytest Fixtures](https://docs.pytest.org/en/stable/fixture.html)
- [Coverage.py](https://coverage.readthedocs.io/)

---

**Happy Testing! 🧪✨**

For questions or issues, refer to the main [README.md](README.md) documentation.