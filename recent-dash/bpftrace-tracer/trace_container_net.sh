#!/bin/bash
echo "trace_container_net.sh started, monitoring network interface" >&2
set -ex

# Get network information from environment variables
NETIF=${NETIF:-"eth0"}  # Default to eth0 if not specified
echo "Monitoring interface: $NETIF" >&2

# Calculate UNIX epoch offset in ms
EPOCH_MS=$(($(date +%s%3N) - $(cat /proc/uptime | awk '{print int($1)*1000 }')))
echo "EPOCH_MS calculated as $EPOCH_MS" >&2

# Create bpftrace script
BT_SCRIPT=$(mktemp /tmp/trace_net_XXXX.bt)
trap "rm -f $BT_SCRIPT" EXIT

cat > "$BT_SCRIPT" <<'EOF'
// Variables are automatically initialized to 0 when first used

tracepoint:net:net_dev_queue
/str(args->name) == "NETIF_VALUE"/
{
  @tx += args->len;
}

tracepoint:net:netif_receive_skb
/str(args->name) == "NETIF_VALUE"/
{
  @rx += args->len;
}

interval:ms:10
{
  $ts = EPOCH_MS_VALUE + (nsecs / 1000000);  // Add epoch offset
  printf("%llu,%llu,%llu\n", $ts, @rx, @tx);
  clear(@rx); clear(@tx);
}
EOF

# Replace placeholders
sed -i "s/NETIF_VALUE/$NETIF/g" "$BT_SCRIPT"
sed -i "s/EPOCH_MS_VALUE/$EPOCH_MS/g" "$BT_SCRIPT"

echo "bpftrace script written to $BT_SCRIPT" >&2

# Run bpftrace and write output to trace.csv
mkdir -p /opt/tracer/output
echo "timestamp_ms,rx_bytes,tx_bytes" > /opt/tracer/output/trace.csv
echo "Starting bpftrace..." >&2

if ! bpftrace "$BT_SCRIPT" >> /opt/tracer/output/trace.csv; then
  echo "ERROR: bpftrace failed to run properly" >&2
  exit 1
fi

echo "bpftrace finished, trace written to /opt/tracer/output/trace.csv" >&2

# Check if the trace file has data
if [ "$(wc -l < "/opt/tracer/output/trace.csv")" -le 1 ]; then
  echo "[WARNING] Trace file appears to be empty (only header)" >&2
fi

# Keep container running until stopped
tail -f /dev/null