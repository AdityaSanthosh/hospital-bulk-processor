"""
Test script to verify the Hospital Bulk Processor setup
"""

import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from app.models import HospitalProcessingResult
from app.services import BulkHospitalProcessor, HospitalAPIClient
from app.utils import CSVValidator


def test_imports():
    """Test that all modules import correctly"""
    print("✓ All modules imported successfully")


def test_models():
    """Test Pydantic models"""

    # Test HospitalProcessingResult
    result = HospitalProcessingResult(
        row=1, hospital_id=123, name="Test Hospital", status="created_and_activated"
    )
    assert result.row == 1
    assert result.name == "Test Hospital"

    print("✓ Pydantic models working correctly")


def test_csv_validator():
    """Test CSV validator constants"""
    assert CSVValidator.MAX_ROWS == 20
    assert CSVValidator.REQUIRED_HEADERS == ["name", "address"]
    assert CSVValidator.OPTIONAL_HEADERS == ["phone"]
    print("✓ CSV validator configured correctly")


def test_api_client():
    """Test API client initialization"""
    client = HospitalAPIClient(base_url="https://hospital-directory.onrender.com")
    assert client.base_url == "https://hospital-directory.onrender.com"
    assert client.timeout == 30.0
    print("✓ API client initialized correctly")


def test_bulk_processor():
    """Test bulk processor initialization"""
    client = HospitalAPIClient(base_url="https://hospital-directory.onrender.com")
    processor = BulkHospitalProcessor(api_client=client)
    assert processor.api_client is not None
    print("✓ Bulk processor initialized correctly")


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("Hospital Bulk Processor - Setup Verification")
    print("=" * 60 + "\n")

    try:
        test_imports()
        test_models()
        test_csv_validator()
        test_api_client()
        test_bulk_processor()

        print("\n" + "=" * 60)
        print("✓ All tests passed! Setup is complete.")
        print("=" * 60 + "\n")
        print("Next steps:")
        print("1. Start the server: uvicorn app.main:app --reload")
        print("2. Open docs: http://localhost:8000/docs")
        print(
            "3. Test with: curl -X POST http://localhost:8000/hospitals/bulk -F 'file=@sample_hospitals.csv'"
        )
        print()

        return 0
    except Exception as e:
        print(f"\n✗ Test failed: {str(e)}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
