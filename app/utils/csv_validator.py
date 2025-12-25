"""CSV validation utility"""
import csv
import io
import logging
from typing import List, Tuple

from fastapi import HTTPException, UploadFile

from app.config import settings
from app.domain.schemas import HospitalCreate

logger = logging.getLogger(__name__)


class CSVValidator:
    """CSV validation and parsing"""
    
    REQUIRED_HEADERS = ["name", "address"]
    MAX_FILE_SIZE_MB = settings.max_file_size_mb
    
    @staticmethod
    async def validate_and_parse_csv(
        file: UploadFile,
        max_rows: int = None
    ) -> List[HospitalCreate]:
        """
        Validate and parse CSV file
        
        Returns:
            List of HospitalCreate objects
            
        Raises:
            HTTPException: If validation fails
        """
        max_rows = max_rows or settings.max_csv_rows
        
        # Validate filename
        if not file.filename or not file.filename.endswith(".csv"):
            raise HTTPException(status_code=400, detail="File must be a CSV file")
        
        # Read and validate file size
        try:
            content = await file.read()
            max_size_bytes = CSVValidator.MAX_FILE_SIZE_MB * 1024 * 1024
            
            if len(content) > max_size_bytes:
                raise HTTPException(
                    status_code=400,
                    detail=f"File size exceeds {CSVValidator.MAX_FILE_SIZE_MB}MB limit",
                )
            
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
        errors = []
        row_number = 1  # Start from 1 (header is row 0)
        
        for row in csv_reader:
            row_number += 1
            
            # Normalize keys
            normalized_row = {
                k.strip().lower(): v.strip() if v else "" for k, v in row.items()
            }
            
            # Extract fields
            name = normalized_row.get("name", "").strip()
            address = normalized_row.get("address", "").strip()
            phone = normalized_row.get("phone", "").strip()
            
            # Validate
            row_errors = []
            if not name:
                row_errors.append(f"Row {row_number}: 'name' is required")
            if not address:
                row_errors.append(f"Row {row_number}: 'address' is required")
            
            if row_errors:
                errors.extend(row_errors)
                continue
            
            # Add to parsed data
            hospital_data = HospitalCreate(
                name=name,
                address=address,
                phone=phone if phone else None,
                row_number=row_number,
            )
            parsed_data.append(hospital_data)
        
        # Check max rows
        if len(parsed_data) > max_rows:
            raise HTTPException(
                status_code=400,
                detail=f"CSV exceeds maximum allowed rows ({max_rows})",
            )
        
        # Check if we have data
        if not parsed_data and not errors:
            raise HTTPException(
                status_code=400, detail="CSV file contains no valid data rows"
            )
        
        # If there are validation errors, raise exception
        if errors:
            raise HTTPException(
                status_code=400, detail=f"CSV validation failed: {'; '.join(errors)}"
            )
        
        logger.info(f"CSV validated successfully: {len(parsed_data)} hospitals")
        return parsed_data
