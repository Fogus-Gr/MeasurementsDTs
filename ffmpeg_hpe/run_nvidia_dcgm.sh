#!/bin/bash
# Containerized GPU metrics logger

# Set default values
OUTPUT_DIR=${METRICS_OUTPUT_DIR:-/output}
OUTPUT_FILE="${OUTPUT_DIR}/gpu_stats.csv"
SLEEP_INTERVAL=${METRICS_INTERVAL:-0.5}
DURATION=${METRICS_DURATION:-0}  # 0 means run indefinitely

# Create output directory if it doesn't exist
mkdir -p "${OUTPUT_DIR}"

# Function to handle cleanup
cleanup() {
    echo "Stopping GPU metrics collection..."
    if [ -n "${LOOP_PID}" ]; then
        kill -TERM "${LOOP_PID}" 2>/dev/null
        wait "${LOOP_PID}" 2>/dev/null
    fi
    
    echo "GPU metrics collection stopped. Data saved to ${OUTPUT_FILE}"
    exit 0
}

# Set up trap to catch termination signals
trap cleanup INT TERM

# Write CSV header
# Note: timestamp is now in Unix epoch format (seconds since 1970-01-01 00:00:00 UTC)
HEADER="timestamp_epoch,pstate,power.draw,temperature.gpu,utilization.gpu,utilization.memory,memory.total,memory.free,memory.used"
echo "${HEADER}" > "${OUTPUT_FILE}"

# Check if nvidia-smi is available
if ! command -v nvidia-smi &> /dev/null; then
    echo "Error: nvidia-smi not found. Make sure NVIDIA drivers are installed." >&2
    exit 1
fi

echo "Starting GPU metrics collection..."
echo "  Output: ${OUTPUT_FILE}"
echo "  Interval: ${SLEEP_INTERVAL} seconds"
[ "${DURATION}" -gt 0 ] && echo "  Duration: ${DURATION} seconds"

# Start the monitoring loop in the background
(
    START_TIME=$(date +%s)
    while true; do
        # Check if duration limit is reached
        if [ "${DURATION}" -gt 0 ]; then
            CURRENT_TIME=$(date +%s)
            ELAPSED=$((CURRENT_TIME - START_TIME))
            if [ "${ELAPSED}" -ge "${DURATION}" ]; then
                break
            fi
        fi
        
        # Get GPU stats and process the output to convert timestamp to epoch
        nvidia-smi \
            --query-gpu=timestamp,pstate,power.draw,temperature.gpu,utilization.gpu,utilization.memory,memory.total,memory.free,memory.used \
            --format=csv,noheader,nounits 2>/dev/null | while IFS=, read -r timestamp rest; do
            # Convert timestamp to Unix epoch (seconds since 1970-01-01 00:00:00 UTC)
            # Using date command to parse the timestamp and convert to epoch
            epoch_time=$(date -d "${timestamp}" +%s 2>/dev/null || date +%s)
            echo "${epoch_time},${rest}"
        done >> "${OUTPUT_FILE}" || break
            
        sleep "${SLEEP_INTERVAL}"
    done
) &

LOOP_PID=$!

# Wait for the monitoring process to complete
wait "${LOOP_PID}" 2>/dev/null

# Clean up
cleanup
