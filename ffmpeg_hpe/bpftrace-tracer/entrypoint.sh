#!/bin/bash
set -eo pipefail

LOG_DIR="/opt/tracer/output/logs"
mkdir -p "$LOG_DIR"
exec > >(tee -a "$LOG_DIR/bcc-tracer.log")
exec 2>&1

echo "[INFO] Starting HPE traffic monitor at $(date)"

# Configuration - using host networking via service:hpe
STREAMER_IP=$(getent hosts "${STREAMER_IP:-rtsp-broker}" | awk '{ print $1 }')
STREAMER_PORT=${STREAMER_PORT:-8554}  # Default to 8554 (MediaMTX RTSP) if not set
INTERFACE=${BCC_INTERFACE:-$(ip route | awk '/default/ {print $5; exit}')}
if [ -z "$INTERFACE" ]; then
    INTERFACE=$(ip -o link show | awk -F': ' '$2 != "lo" {sub(/@.*/, "", $2); print $2; exit}')
fi
MAX_ATTEMPTS=10
ATTEMPT_WAIT=3

if [ -z "$STREAMER_IP" ]; then
    echo "[ERROR] Failed to resolve STREAMER_IP"
    exit 1
fi

# Verify interface exists
if ! ip link show "$INTERFACE" >/dev/null; then
    echo "[ERROR] Interface $INTERFACE not found! Available:"
    ip -br a
    exit 1
fi

echo "[INFO] Network Configuration:"
echo "  Streamer: $STREAMER_IP:$STREAMER_PORT"
echo "  Interface: $INTERFACE"

detect_hpe_port() {
    ss -ntp | awk -v ip="$STREAMER_IP" -v port="$STREAMER_PORT" '
        $1 == "ESTAB" && $5 == ip ":" port {
            local_addr = $4
            sub(/^.*:/, "", local_addr)
            print local_addr
            exit
        }
    '
}

# Wait for HPE to establish connection to the RTSP broker
echo "[INFO] Waiting for HPE to connect to streamer on port $STREAMER_PORT..."
for i in $(seq 1 $MAX_ATTEMPTS); do
    HPE_PORT=$(detect_hpe_port)
    if [ -n "$HPE_PORT" ]; then
        break
    fi
    sleep $ATTEMPT_WAIT
done

if [ -z "$HPE_PORT" ]; then
    echo "[ERROR] Failed to detect HPE port after $MAX_ATTEMPTS attempts"
    echo "[DEBUG] Current connections:"
    ss -ntp
    exit 1
fi

echo "[SUCCESS] Monitoring HPE traffic on port $HPE_PORT"
exec python3 /app/bcc_rx_bytes.py "$STREAMER_IP" "$STREAMER_PORT" "$HPE_PORT" "$INTERFACE"
