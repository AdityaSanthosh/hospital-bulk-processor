#!/bin/bash

# Hospital Bulk Processor - Polling Test Script
# This script demonstrates the polling endpoint for progress tracking

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BASE_URL="${BASE_URL:-http://localhost:8000}"
CSV_FILE="${CSV_FILE:-sample_hospitals.csv}"
POLL_INTERVAL="${POLL_INTERVAL:-2}"

echo "============================================================"
echo "Hospital Bulk Processor - Polling Test"
echo "============================================================"
echo ""

# Check if server is running
echo -e "${BLUE}Checking server health...${NC}"
if ! curl -s "$BASE_URL/health" > /dev/null 2>&1; then
    echo -e "${RED}❌ Error: Cannot connect to server at $BASE_URL${NC}"
    echo ""
    echo "Please start the server first:"
    echo "  docker-compose up"
    echo "  or"
    echo "  uvicorn app.main:app --reload"
    exit 1
fi
echo -e "${GREEN}✅ Server is healthy${NC}"
echo ""

# Check if CSV file exists
if [ ! -f "$CSV_FILE" ]; then
    echo -e "${RED}❌ Error: CSV file not found: $CSV_FILE${NC}"
    exit 1
fi

# Upload CSV file
echo -e "${BLUE}📤 Uploading CSV file: $CSV_FILE${NC}"
echo "------------------------------------------------------------"

UPLOAD_RESPONSE=$(curl -s -X POST "$BASE_URL/hospitals/bulk" \
  -H "accept: application/json" \
  -F "file=@$CSV_FILE")

# Check if upload was successful
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Upload failed${NC}"
    exit 1
fi

# Extract job_id from response
JOB_ID=$(echo "$UPLOAD_RESPONSE" | grep -o '"job_id":"[^"]*"' | cut -d'"' -f4)
TOTAL=$(echo "$UPLOAD_RESPONSE" | grep -o '"total_hospitals":[0-9]*' | cut -d':' -f2)

if [ -z "$JOB_ID" ]; then
    echo -e "${RED}❌ Failed to get job ID from response${NC}"
    echo "Response: $UPLOAD_RESPONSE"
    exit 1
fi

echo -e "${GREEN}✅ Upload successful!${NC}"
echo "   Job ID: $JOB_ID"
echo "   Total hospitals: $TOTAL"
echo ""

# Poll for status
echo -e "${BLUE}🔄 Polling job status (every ${POLL_INTERVAL}s)...${NC}"
echo "============================================================"
echo ""

START_TIME=$(date +%s)
PREVIOUS_PROCESSED=0

while true; do
    # Get job status
    STATUS_RESPONSE=$(curl -s "$BASE_URL/hospitals/bulk/status/$JOB_ID")

    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Error getting status${NC}"
        break
    fi

    # Parse JSON response (using grep and cut for simplicity)
    STATUS=$(echo "$STATUS_RESPONSE" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    PROCESSED=$(echo "$STATUS_RESPONSE" | grep -o '"processed_hospitals":[0-9]*' | cut -d':' -f2)
    FAILED=$(echo "$STATUS_RESPONSE" | grep -o '"failed_hospitals":[0-9]*' | cut -d':' -f2)
    PROGRESS=$(echo "$STATUS_RESPONSE" | grep -o '"progress_percentage":[0-9.]*' | cut -d':' -f2)
    CURRENT=$(echo "$STATUS_RESPONSE" | grep -o '"current_hospital":"[^"]*"' | head -1 | cut -d'"' -f4)

    # Calculate elapsed time
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - START_TIME))

    # Display progress on same line
    echo -ne "\r⏱️  Elapsed: ${ELAPSED}s | Progress: ${PROGRESS}% (${PROCESSED}/${TOTAL}) | Failed: ${FAILED} | Status: ${STATUS}     "

    # Show newly completed hospitals
    if [ "$PROCESSED" -gt "$PREVIOUS_PROCESSED" ] && [ -n "$CURRENT" ]; then
        echo ""
        echo "   ✓ Completed: $CURRENT"
        PREVIOUS_PROCESSED=$PROCESSED
    fi

    # Check if job is complete
    if [ "$STATUS" = "completed" ]; then
        echo ""
        echo ""
        echo "============================================================"
        echo -e "${GREEN}✅ Job completed successfully!${NC}"
        echo "------------------------------------------------------------"

        # Display final results
        BATCH_ID=$(echo "$STATUS_RESPONSE" | grep -o '"batch_id":"[^"]*"' | cut -d'"' -f4)
        PROC_TIME=$(echo "$STATUS_RESPONSE" | grep -o '"processing_time_seconds":[0-9.]*' | cut -d':' -f2)
        ACTIVATED=$(echo "$STATUS_RESPONSE" | grep -o '"batch_activated":[a-z]*' | cut -d':' -f2)

        echo "Batch ID: $BATCH_ID"
        echo "Total Hospitals: $TOTAL"
        echo "Processed: $PROCESSED"
        echo "Failed: $FAILED"
        echo "Processing Time: ${PROC_TIME}s"
        echo "Batch Activated: $ACTIVATED"
        echo ""

        break
    elif [ "$STATUS" = "failed" ]; then
        echo ""
        echo ""
        echo "============================================================"
        echo -e "${RED}❌ Job failed!${NC}"
        ERROR=$(echo "$STATUS_RESPONSE" | grep -o '"error":"[^"]*"' | cut -d'"' -f4)
        echo "Error: $ERROR"
        break
    fi

    # Wait before next poll
    sleep "$POLL_INTERVAL"
done

echo ""
echo "============================================================"
echo ""
echo -e "${BLUE}📊 You can check the job status anytime using:${NC}"
echo "  curl $BASE_URL/hospitals/bulk/status/$JOB_ID | jq"
echo ""
echo -e "${BLUE}📋 Or view all jobs:${NC}"
echo "  curl $BASE_URL/hospitals/bulk/jobs | jq"
echo ""
echo "============================================================"
echo -e "${GREEN}✨ Test completed!${NC}"
echo ""
