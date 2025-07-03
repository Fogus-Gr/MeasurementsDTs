#!/bin/bash
set -e

# Start GPU metrics collection in the background if ENABLE_GPU_METRICS is set
if [ "${ENABLE_GPU_METRICS:-0}" = "1" ]; then
    echo "Starting GPU metrics collection..."
    ./run_nvidia_dcgm.sh &
    METRICS_PID=$!
    # Give it a moment to start
    sleep 2
fi

# Execute the main command
if [ "$#" -gt 0 ]; then
    # If arguments are passed, use them as the command
    exec "$@"
else
    # Otherwise, use the default command from Dockerfile
    exec python3 main.py
fi

# Cleanup
if [ -n "${METRICS_PID}" ]; then
    kill -TERM "$METRICS_PID" 2>/dev/null
fi