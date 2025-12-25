import csv
import io
from typing import Dict, List, Tuple

from fastapi import HTTPException, UploadFile


class CSVValidator:
    """Validator for CSV file uploads"""

    REQUIRED_HEADERS = ["name", "address"]
    OPTIONAL_HEADERS = ["phone"]
    MAX_ROWS = 20
    MAX_FILE_SIZE_MB = 5

    @staticmethod
    async def validate_and_parse_csv(
        file: UploadFile, max_rows: int = MAX_ROWS
    ) -> Tuple[List[Dict[str, str]], List[str]]:
        """
        Validate and parse CSV file.

        Args:
            file: Uploaded CSV file
            max_rows: Maximum number of rows allowed

        Returns:
            Tuple of (parsed_data, errors)

        Raises:
            HTTPException: If file validation fails
        """
        errors = []

        # Validate file extension
        if not file.filename or not file.filename.endswith(".csv"):
            raise HTTPException(status_code=400, detail="File must be a CSV file")

        # Read file content
        try:
            content = await file.read()

            # Validate file size (5MB = 5 * 1024 * 1024 bytes)
            max_size_bytes = CSVValidator.MAX_FILE_SIZE_MB * 1024 * 1024
            if len(content) > max_size_bytes:
                raise HTTPException(
                    status_code=400,
                    detail=f"File size exceeds {CSVValidator.MAX_FILE_SIZE_MB}MB limit",
                )

            # Decode content
            content_str = content.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="File must be UTF-8 encoded")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")

        # Parse CSV
        csv_reader = csv.DictReader(io.StringIO(content_str))

        # Validate headers
        if not csv_reader.fieldnames:
            raise HTTPException(
                status_code=400, detail="CSV file is empty or has no headers"
            )

        headers = [h.strip().lower() for h in csv_reader.fieldnames]

        # Check required headers
        for required_header in CSVValidator.REQUIRED_HEADERS:
            if required_header not in headers:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required column: '{required_header}'",
                )

        # Parse rows
        parsed_data = []
        row_number = 1  # Start from 1 (header is row 0)

        for row in csv_reader:
            row_number += 1

            # Check max rows limit
            if len(parsed_data) >= max_rows:
                raise HTTPException(
                    status_code=400,
                    detail=f"CSV exceeds maximum allowed rows ({max_rows})",
                )

            # Normalize keys to lowercase
            normalized_row = {
                k.strip().lower(): v.strip() if v else "" for k, v in row.items()
            }

            # Validate required fields
            name = normalized_row.get("name", "").strip()
            address = normalized_row.get("address", "").strip()
            phone = normalized_row.get("phone", "").strip()

            row_errors = []

            if not name:
                row_errors.append(f"Row {row_number}: 'name' is required")

            if not address:
                row_errors.append(f"Row {row_number}: 'address' is required")

            if row_errors:
                errors.extend(row_errors)
                continue

            # Add validated row
            hospital_data = {
                "name": name,
                "address": address,
                "phone": phone if phone else None,
                "row_number": row_number,
            }

            parsed_data.append(hospital_data)

        # Check if we have any data
        if not parsed_data and not errors:
            raise HTTPException(
                status_code=400, detail="CSV file contains no valid data rows"
            )

        # If there are validation errors, raise exception
        if errors:
            raise HTTPException(
                status_code=400, detail=f"CSV validation failed: {'; '.join(errors)}"
            )

        return parsed_data, errors


def format_processing_time(seconds: float) -> str:
    """Format processing time in a human-readable format"""
    if seconds < 1:
        return f"{seconds * 1000:.2f}ms"
    elif seconds < 60:
        return f"{seconds:.2f}s"
    else:
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds:.2f}s"
