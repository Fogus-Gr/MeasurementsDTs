#!/bin/sh
set -e

# Default values can be overridden by environment variables
STREAMER_CONTAINER=${STREAMER_CONTAINER:-streamer}
HPE_CONTAINER=${HPE_CONTAINER:-hpe}
DURATION=${DURATION:-30}
INTERVAL=${INTERVAL:-0.1}
OUTPUT_FILE=${OUTPUT_FILE:-/results/network.csv}

# Execute the monitoring script
python3 /app/network_monitor.py \
    --streamer "$STREAMER_CONTAINER" \
    --hpe "$HPE_CONTAINER" \
    --duration "$DURATION" \
    --interval "$INTERVAL" \
    --output "$OUTPUT_FILE"

# Keep container running if needed for debugging
if [ "$DEBUG" = "true" ]; then
    echo "Debug mode enabled. Keeping container running..."
    tail -f /dev/null
fi
