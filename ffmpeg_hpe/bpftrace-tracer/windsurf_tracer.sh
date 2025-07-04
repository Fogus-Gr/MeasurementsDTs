#!/bin/bash
# filepath: /home/user/MeasurementsDTs/ffmpeg_hpe/bpftrace-tracer/trace_video_traffic.sh
echo "Video traffic tracer started, monitoring HTTP stream traffic" >&2
set -ex

# Configuration
NETIF=${NETIF:-"eth0"}
TARGET_PORT=${TARGET_PORT:-"8089"}
SAMPLE_RATE_MS=${SAMPLE_RATE_MS:-"100"}  # Reduced from 10ms to 100ms for lower overhead
OUTPUT_DIR="/opt/tracer/output"
OUTPUT_FILE="$OUTPUT_DIR/trace.csv"

# Ensure output directory exists
mkdir -p "$OUTPUT_DIR"
echo "timestamp_ms,rx_video_bytes" > "$OUTPUT_FILE"

# Calculate UNIX epoch offset in ms
EPOCH_MS=$(($(date +%s%3N) - $(awk '{print int($1)*1000}' /proc/uptime)))
echo "EPOCH_MS calculated as $EPOCH_MS" >&2

# Create bpftrace script
BT_SCRIPT=$(mktemp /tmp/trace_video_XXXX.bt)
trap "rm -f $BT_SCRIPT" EXIT

cat > "$BT_SCRIPT" <<EOF
#include <net/sock.h>
#include <net/tcp_states.h>

// Track TCP traffic on specific port
kprobe:tcp_v4_rcv
{
    // Get socket pointer
    \$sk = (struct sock *)arg0;
    
    // Check if this is our target port
    if (\$sk->__sk_common.skc_dport == htons($TARGET_PORT)) {
        @rx_bytes = \$sk->sk_rmem_alloc.ctr.counter;
    }
}

// Sample at regular intervals
interval:ms:$SAMPLE_RATE_MS
{
    \$ts = $EPOCH_MS + (nsecs / 1000000);
    printf("%llu,%llu\\n", \$ts, @rx_bytes);
    clear(@rx_bytes);
}
EOF

echo "Starting bpftrace with optimized tracer..." >&2
if ! bpftrace -v "$BT_SCRIPT" >> "$OUTPUT_FILE"; then
    echo "ERROR: bpftrace failed to run" >&2
    exit 1
fi