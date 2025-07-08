#!/bin/bash
# filepath: /home/user/MeasurementsDTs/ffmpeg_hpe/bpftrace-tracer/trace_video_traffic.sh
echo "Video traffic tracer started, monitoring HTTP stream traffic" >&2
set -ex

# Get network information from environment variables
NETIF=${NETIF:-"eth0"}
TARGET_PORT=${TARGET_PORT:-"8089"}
echo "Monitoring interface: $NETIF for traffic on port $TARGET_PORT" >&2

# Start tcpdump in the background to capture port 8089 traffic
TCPDUMP_FILE="/opt/tracer/output/tcpdump_8089.log"
echo "Starting tcpdump to capture port $TARGET_PORT traffic on interface $NETIF (or all if NETIF=any)..." >&2
tcpdump -i any tcp port "$TARGET_PORT" -nn -tt > "$TCPDUMP_FILE" 2>&1 &
TCPDUMP_PID=$!

# Ensure tcpdump is killed on script exit
cleanup() {
  kill $TCPDUMP_PID 2>/dev/null || true

  rm -f "$BT_SCRIPT"
}
trap cleanup EXIT

# Calculate UNIX epoch offset in ms
EPOCH_MS=$(($(date +%s%3N) - $(cat /proc/uptime | awk '{print int($1)*1000 }')))
echo "EPOCH_MS calculated as $EPOCH_MS" >&2

# Create bpftrace script for RX bytes on a specific TCP port every 10ms
BT_SCRIPT=$(mktemp /tmp/trace_video_XXXX.bt)
trap "rm -f $BT_SCRIPT" EXIT

cat > "$BT_SCRIPT" <<EOF
#include <linux/socket.h>
#include <linux/net.h>
#include <linux/inet.h>

kprobe:tcp_v4_rcv
{
  $sk = (struct sock *)arg0;
  $dport = ((ntohs(((struct inet_sock *)$sk)->inet_dport)));
  if ($dport == $TARGET_PORT) {
    @rx_bytes += ((struct sk_buff *)arg1)->len;
  }
}

interval:ms:10
{
  printf("%llu,%d\n", nsecs/1000000, @rx_bytes);
  clear(@rx_bytes);
}
EOF

# Replace $TARGET_PORT in the script with the actual port number
sed -i "s/\$TARGET_PORT/$TARGET_PORT/g" "$BT_SCRIPT"

echo "bpftrace script written to $BT_SCRIPT" >&2

# Run bpftrace and write output to trace.csv
mkdir -p /opt/tracer/output
echo "timestamp_ms,rx_video_bytes" > /opt/tracer/output/trace.csv
echo "Starting bpftrace..." >&2

if ! bpftrace "$BT_SCRIPT" >> /opt/tracer/output/trace.csv 2>> /opt/tracer/output/error.log; then
  echo "ERROR: bpftrace failed to run properly. See error.log for details." >&2
  exit 1
fi

echo "bpftrace finished, trace written to /opt/tracer/output/trace.csv" >&2

# Check if the trace file has data
if [ "$(wc -l < "/opt/tracer/output/trace.csv")" -le 1 ]; then
  echo "[WARNING] Trace file appears to be empty (only header)" >&2
fi

# Summarize tcpdump results for comparison
if [ -f "$TCPDUMP_FILE" ]; then
  TCPDUMP_BYTES=$(grep 'length' "$TCPDUMP_FILE" | awk '{for(i=1;i<=NF;i++) if($i=="length") sum+=$(i+1);} END{print sum+0}')
  echo "[TCPDUMP] Total bytes captured on port $TARGET_PORT: $TCPDUMP_BYTES" >&2
else
  echo "[TCPDUMP] No tcpdump log found at $TCPDUMP_FILE" >&2
fi

# Keep container running until stopped
tail -f /dev/null