#!/bin/bash
set -eo pipefail

LOG_DIR="/opt/tracer/output/logs"
mkdir -p "$LOG_DIR"
exec > >(tee -a "$LOG_DIR/bcc-tracer.log")
exec 2>&1

echo "[INFO] Starting HPE traffic monitor at $(date)"

# Configuration - using host networking via service:hpe
STREAMER_IP=$(getent hosts ${STREAMER_IP:-h264-streaming-server} | awk '{ print $1 }')
STREAMER_PORT=${STREAMER_PORT:-8089}  # Default to 8089 if not set
INTERFACE=$(ip route | awk '/default/ {print $5}')
MAX_ATTEMPTS=10
ATTEMPT_WAIT=3

# Verify interface exists
if ! ip link show $INTERFACE >/dev/null; then
    echo "[ERROR] Interface $INTERFACE not found! Available:"
    ip -br a
    exit 1
fi

echo "[INFO] Network Configuration:"
echo "  Streamer: $STREAMER_IP:$STREAMER_PORT"
echo "  Interface: $INTERFACE"

# Wait for HPE to establish connection
echo "[INFO] Waiting for HPE to connect to streamer..."
for i in $(seq 1 $MAX_ATTEMPTS); do
    if ss -ntp | grep -q ":$STREAMER_PORT"; then
        break
    fi
    sleep $ATTEMPT_WAIT
done

# Get HPE's port from established connections
HPE_PORT=$(ss -ntp | awk '/:8089/ {split($4, a, ":"); print a[length(a)]}' | head -1)
if [ -z "$HPE_PORT" ]; then
    echo "[ERROR] Failed to detect HPE port after $MAX_ATTEMPTS attempts"
    echo "[DEBUG] Current connections:"
    ss -ntp
    exit 1
fi

echo "[SUCCESS] Monitoring HPE traffic on port $HPE_PORT"
exec python3 /app/bcc_rx_bytes.py "$STREAMER_IP" "$STREAMER_PORT" "$HPE_PORT"