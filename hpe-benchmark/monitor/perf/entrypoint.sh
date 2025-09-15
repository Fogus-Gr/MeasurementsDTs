#!/bin/sh
set -e

# Default values can be overridden by environment variables
MONITORED_CONTAINER=${MONITORED_CONTAINER:-hpe}
DURATION=${DURATION:-30}
INTERVAL=${INTERVAL:-0.5}
OUTPUT_FILE=${OUTPUT_FILE:-/results/performance.csv}

# Execute the monitoring script
python3 /app/perf_monitor.py \
    --container "$MONITORED_CONTAINER" \
    --duration "$DURATION" \
    --interval "$INTERVAL" \
    --output "$OUTPUT_FILE"

# Keep container running if needed for debugging
if [ "$DEBUG" = "true" ]; then
    echo "Debug mode enabled. Keeping container running..."
    tail -f /dev/null
fi
