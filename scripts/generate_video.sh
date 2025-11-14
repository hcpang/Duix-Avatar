#!/bin/bash
# Duix Avatar Video Generation Script (Bash version)
# Usage: ./generate_video.sh <audio_path> <video_path>

if [ $# -lt 2 ]; then
    echo "Usage: $0 <audio_path> <video_path>"
    echo ""
    echo "Example:"
    echo "  $0 'D:/duix_avatar_data/face2face/temp/audio.wav' 'D:/duix_avatar_data/face2face/temp/20251113182348159.mp4'"
    exit 1
fi

AUDIO_PATH="$1"
VIDEO_PATH="$2"
TASK_CODE=$(uuidgen 2>/dev/null || cat /proc/sys/kernel/random/uuid 2>/dev/null || echo "task-$(date +%s)")

VIDEO_SUBMIT_URL="http://127.0.0.1:8383/easy/submit"
VIDEO_QUERY_URL="http://127.0.0.1:8383/easy/query"

echo "Submitting video generation task..."
echo "  Audio: $AUDIO_PATH"
echo "  Video: $VIDEO_PATH"
echo "  Task Code: $TASK_CODE"
echo ""

# Submit the task
SUBMIT_RESPONSE=$(curl -s -X POST "$VIDEO_SUBMIT_URL" \
  -H "Content-Type: application/json" \
  -d "{
    \"audio_url\": \"$AUDIO_PATH\",
    \"video_url\": \"$VIDEO_PATH\",
    \"code\": \"$TASK_CODE\",
    \"chaofen\": 0,
    \"watermark_switch\": 0,
    \"pn\": 1
  }")

echo "Submit Response:"
echo "$SUBMIT_RESPONSE" | python -m json.tool 2>/dev/null || echo "$SUBMIT_RESPONSE"
echo ""

# Check if submission was successful
if ! echo "$SUBMIT_RESPONSE" | grep -q '"code": 10000'; then
    echo "Error: Failed to submit task"
    exit 1
fi

# Poll for completion
echo "Waiting for video generation to complete..."
MAX_WAIT=600  # 10 minutes
ELAPSED=0
INTERVAL=2

while [ $ELAPSED -lt $MAX_WAIT ]; do
    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))

    STATUS_RESPONSE=$(curl -s "$VIDEO_QUERY_URL?code=$TASK_CODE")

    # Check if task completed
    if echo "$STATUS_RESPONSE" | grep -q '"status": 2'; then
        echo ""
        echo "✓ Video generation completed!"
        RESULT_PATH=$(echo "$STATUS_RESPONSE" | grep -o '"result": "[^"]*"' | cut -d'"' -f4)
        echo "  Output: D:/duix_avatar_data/face2face/$RESULT_PATH"
        exit 0
    fi

    # Check if task failed
    if echo "$STATUS_RESPONSE" | grep -q '"status": 3'; then
        echo ""
        echo "✗ Video generation failed"
        echo "$STATUS_RESPONSE" | python -m json.tool 2>/dev/null || echo "$STATUS_RESPONSE"
        exit 1
    fi

    # Show progress
    if echo "$STATUS_RESPONSE" | grep -q '"status": 1'; then
        PROGRESS=$(echo "$STATUS_RESPONSE" | grep -o '"progress": [0-9]*' | grep -o '[0-9]*')
        MSG=$(echo "$STATUS_RESPONSE" | grep -o '"msg": "[^"]*"' | cut -d'"' -f4)
        echo "  Progress: $PROGRESS% - $MSG"
    fi
done

echo ""
echo "✗ Timeout: Video generation did not complete within $MAX_WAIT seconds"
exit 1
