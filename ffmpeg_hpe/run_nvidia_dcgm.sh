#!/bin/bash
# Containerized GPU metrics logger

set -e

# Set default values
OUTPUT_DIR=${METRICS_OUTPUT_DIR:-/output}
OUTPUT_FILE="${OUTPUT_DIR}/gpu_metrics.csv"
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

# Create header for CSV
HEADER="timestamp,gpu_id,gpu_utilization,mem_utilization,temperature,power_usage"
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
        
        timestamp=$(date +%s.%N)
        
        # Get GPU stats with nvidia-smi
        nvidia-smi --query-gpu=index,utilization.gpu,utilization.memory,temperature.gpu,power.draw --format=csv,noheader,nounits | while read -r line; do
            # Process each GPU
            gpu_id=$(echo "$line" | awk -F, '{print $1}' | xargs)
            gpu_util=$(echo "$line" | awk -F, '{print $2}' | xargs)
            mem_util=$(echo "$line" | awk -F, '{print $3}' | xargs)
            temp=$(echo "$line" | awk -F, '{print $4}' | xargs)
            power=$(echo "$line" | awk -F, '{print $5}' | xargs)
            
            # Write to CSV
            echo "$timestamp,$gpu_id,$gpu_util,$mem_util,$temp,$power" >> "$OUTPUT_FILE"
        done || break
            
        sleep "${SLEEP_INTERVAL}"
    done
) &

LOOP_PID=$!

# Wait for the monitoring process to complete
wait "${LOOP_PID}" 2>/dev/null

# Clean up
cleanup
