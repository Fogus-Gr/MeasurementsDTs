#!/bin/bash
set -e

# Start GPU metrics collection in the background if ENABLE_GPU_METRICS is set
if [ "${ENABLE_GPU_METRICS:-0}" = "1" ]; then
    echo "Starting GPU metrics collection..."
    ./run_nvidia_dcgm.sh &
    METRICS_PID=$!
    sleep 2

    # Stop GPU metrics on exit — trap must be registered before exec replaces this shell
    trap 'kill -TERM "$METRICS_PID" 2>/dev/null; wait "$METRICS_PID" 2>/dev/null' EXIT
fi

# exec replaces this shell process; the EXIT trap above fires when the child exits
if [ "$#" -gt 0 ]; then
    exec "$@"
else
    exec python3 main.py
fi