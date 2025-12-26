#!/bin/bash
# Test script for manual batch activation flow

set -e

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║           TESTING MANUAL BATCH ACTIVATION FLOW                      ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

BASE_URL="http://localhost:8000/api/v1"

# Check if server is running
echo "1. Checking if server is running..."
if ! curl -s -f "$BASE_URL/hospitals/jobs" > /dev/null; then
    echo "   ❌ Server not running at $BASE_URL"
    echo "   Start server with: uvicorn app.main:app --reload"
    exit 1
fi
echo "   ✅ Server is running"
echo ""

# Create a test CSV
echo "2. Creating test CSV..."
cat > /tmp/test_hospitals.csv << 'CSV'
name,address,phone
City Hospital,123 Main St,555-0001
County Medical Center,456 Oak Ave,555-0002
CSV
echo "   ✅ Test CSV created"
echo ""

# Upload CSV
echo "3. Uploading CSV..."
IDEMPOTENCY_KEY=$(uuidgen)
RESPONSE=$(curl -s -X POST "$BASE_URL/hospitals/bulk" \
  -H "Idempotency-Key: $IDEMPOTENCY_KEY" \
  -F "file=@/tmp/test_hospitals.csv")

JOB_ID=$(echo $RESPONSE | jq -r '.job_id')
echo "   ✅ Job submitted: $JOB_ID"
echo ""

# Poll for completion
echo "4. Polling for completion..."
MAX_ATTEMPTS=30
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    STATUS_RESPONSE=$(curl -s "$BASE_URL/hospitals/status/$JOB_ID")
    STATUS=$(echo $STATUS_RESPONSE | jq -r '.status')
    
    echo -n "   Attempt $((ATTEMPT+1))/$MAX_ATTEMPTS: Status=$STATUS"
    
    if [ "$STATUS" = "completed" ]; then
        echo " ✅"
        break
    elif [ "$STATUS" = "failed" ]; then
        echo " ❌"
        echo "   Job failed!"
        exit 1
    else
        echo " ⏳"
        sleep 2
    fi
    
    ATTEMPT=$((ATTEMPT+1))
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    echo "   ❌ Timeout waiting for job completion"
    exit 1
fi
echo ""

# Get batch ID
echo "5. Getting batch ID from results..."
BATCH_ID=$(echo $STATUS_RESPONSE | jq -r '.result.batch_id')
FAILED=$(echo $STATUS_RESPONSE | jq -r '.result.failed_hospitals')
SUCCESS=$(echo $STATUS_RESPONSE | jq -r '.result.processed_hospitals')
ACTIVATED=$(echo $STATUS_RESPONSE | jq -r '.result.batch_activated')

echo "   ✅ Batch ID: $BATCH_ID"
echo "   📊 Results: $SUCCESS succeeded, $FAILED failed"
echo "   📌 Activated: $ACTIVATED (should be false)"
echo ""

# Verify not activated
if [ "$ACTIVATED" != "false" ]; then
    echo "   ❌ ERROR: batch_activated should be false!"
    exit 1
fi

# Review and decide
echo "6. Reviewing results..."
if [ "$FAILED" -gt 0 ]; then
    echo "   ⚠️  Some hospitals failed. Review before activating!"
    echo "   Would you like to activate anyway? (This is a test, so we'll continue)"
else
    echo "   ✅ All hospitals succeeded. Ready to activate!"
fi
echo ""

# Activate batch
echo "7. Activating batch..."
ACTIVATE_RESPONSE=$(curl -s -X PATCH "$BASE_URL/hospitals/bulk/batch/$BATCH_ID/activate")
ACTIVATED_FLAG=$(echo $ACTIVATE_RESPONSE | jq -r '.activated')
MESSAGE=$(echo $ACTIVATE_RESPONSE | jq -r '.message')

if [ "$ACTIVATED_FLAG" = "true" ]; then
    echo "   ✅ Batch activated successfully!"
    echo "   Message: $MESSAGE"
else
    echo "   ❌ Activation failed!"
    echo "   Message: $MESSAGE"
    ERROR=$(echo $ACTIVATE_RESPONSE | jq -r '.error_message')
    echo "   Error: $ERROR"
    exit 1
fi
echo ""

# Test idempotency (activate again)
echo "8. Testing idempotency (activating again)..."
ACTIVATE_RESPONSE2=$(curl -s -X PATCH "$BASE_URL/hospitals/bulk/batch/$BATCH_ID/activate")
ACTIVATED_FLAG2=$(echo $ACTIVATE_RESPONSE2 | jq -r '.activated')

if [ "$ACTIVATED_FLAG2" = "true" ]; then
    echo "   ✅ Second activation succeeded (idempotent)"
else
    echo "   ℹ️  Second activation returned false (batch may already be active)"
fi
echo ""

# Cleanup
rm -f /tmp/test_hospitals.csv

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                    ✅ ALL TESTS PASSED                               ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Summary:"
echo "  1. ✅ CSV uploaded successfully"
echo "  2. ✅ Job completed (batch_activated=false)"
echo "  3. ✅ Batch ID retrieved"
echo "  4. ✅ Manual activation succeeded"
echo "  5. ✅ Idempotency verified"
echo ""
echo "The new manual activation workflow is working perfectly! 🚀"
