#!/bin/bash
# filepath: /home/user/MeasurementsDTs/ffmpeg_hpe/bpftrace-tracer/trace_video_traffic.sh
echo "Video traffic tracer started, monitoring HTTP stream traffic" >&2
set -ex

# Get network information from environment variables
NETIF=${NETIF:-"eth0"}  # Default to eth0 if not specified
TARGET_PORT=${TARGET_PORT:-"8089"}  # Default to the streaming port
echo "Monitoring interface: $NETIF for traffic on port $TARGET_PORT" >&2

# Add verification variables
VERIFICATION_ENABLED=true
TCPDUMP_OUTPUT="/tmp/tcpdump_verification.pcap"

# Calculate UNIX epoch offset in ms
EPOCH_MS=$(($(date +%s%3N) - $(cat /proc/uptime | awk '{print int($1)*1000 }')))
echo "EPOCH_MS calculated as $EPOCH_MS" >&2

# Create bpftrace script
BT_SCRIPT=$(mktemp /tmp/trace_video_XXXX.bt)
trap "rm -f $BT_SCRIPT; [ -n \"$TCPDUMP_PID\" ] && kill $TCPDUMP_PID 2>/dev/null" EXIT

# Start verification with tcpdump if enabled
if [ "$VERIFICATION_ENABLED" = true ]; then
  echo "Starting verification with tcpdump on $NETIF port $TARGET_PORT" >&2
  # Ensure tcpdump is installed
  if ! command -v tcpdump &> /dev/null; then
    echo "Warning: tcpdump not found, installing..." >&2
    apt-get update && apt-get install -y tcpdump
  fi
  
  # Start tcpdump in background, capturing to file
  tcpdump -i "$NETIF" -nn "port $TARGET_PORT" -w "$TCPDUMP_OUTPUT" 2>/dev/null &
  TCPDUMP_PID=$!
  echo "Tcpdump started with PID $TCPDUMP_PID" >&2
fi

cat > "$BT_SCRIPT" <<'EOF'
// Using same probes as the working script

tracepoint:net:netif_receive_skb
/str(args->name) == "NETIF_VALUE"/
{
  @rx += args->len;
}

interval:ms:10
{
  $ts = EPOCH_MS_VALUE + (nsecs / 1000000);  // Add epoch offset
  printf("%llu,%llu\n", $ts, @rx);
  clear(@rx);
}
EOF

# Replace placeholders
sed -i "s/NETIF_VALUE/$NETIF/g" "$BT_SCRIPT"
sed -i "s/EPOCH_MS_VALUE/$EPOCH_MS/g" "$BT_SCRIPT"

echo "bpftrace script written to $BT_SCRIPT" >&2

# Run bpftrace and write output to trace.csv
mkdir -p /opt/tracer/output
echo "timestamp_ms,rx_video_bytes" > /opt/tracer/output/trace.csv
echo "Starting bpftrace..." >&2

if ! bpftrace "$BT_SCRIPT" >> /opt/tracer/output/trace.csv; then
  echo "ERROR: bpftrace failed to run properly" >&2
  exit 1
fi

echo "bpftrace finished, trace written to /opt/tracer/output/trace.csv" >&2

# Process verification data if enabled
if [ "$VERIFICATION_ENABLED" = true ] && [ -n "$TCPDUMP_PID" ]; then
  echo "Stopping tcpdump verification..." >&2
  kill -TERM "$TCPDUMP_PID" 2>/dev/null
  wait "$TCPDUMP_PID" 2>/dev/null || true
  
  # Process the tcpdump file and calculate total bytes
  if [ -f "$TCPDUMP_OUTPUT" ]; then
    echo "Analyzing tcpdump capture..." >&2
    
    # Calculate total bytes from trace.csv
    TOTAL_RX_BYTES=$(awk -F, 'NR>1 {sum+=$2} END {print sum}' /opt/tracer/output/trace.csv)
    
    # Calculate total bytes from tcpdump
    RX_BYTES=$(tcpdump -r "$TCPDUMP_OUTPUT" -nn "dst port $TARGET_PORT" 2>/dev/null | awk '{sum+=$NF} END {print sum}')
    
    echo "-------- VERIFICATION RESULTS --------" >&2
    echo "BPFTrace measured: RX=$TOTAL_RX_BYTES bytes" >&2
    echo "TCPDump measured: RX=$RX_BYTES bytes" >&2
    
    if [ "$RX_BYTES" -ne 0 ]; then
      DIFF_PCT=$(echo "scale=2; ($RX_BYTES-$TOTAL_RX_BYTES)*100/$RX_BYTES" | bc)
      echo "Difference: $(($RX_BYTES-$TOTAL_RX_BYTES)) bytes ($DIFF_PCT%)" >&2
    fi
    echo "---------------------------------------" >&2
    
    # Save verification to file
    echo "timestamp,tool,rx_bytes" > /opt/tracer/output/verification.csv
    echo "$(date +%s),bpftrace,$TOTAL_RX_BYTES" >> /opt/tracer/output/verification.csv
    echo "$(date +%s),tcpdump,$RX_BYTES" >> /opt/tracer/output/verification.csv
    
    # Add note about accuracy to trace.csv file
    echo "# Verification: BPFTrace measured $TOTAL_RX_BYTES bytes, TCPDump measured $RX_BYTES bytes" >> /opt/tracer/output/trace.csv
    
    rm -f "$TCPDUMP_OUTPUT"
  fi
fi

# Check if the trace file has data
if [ "$(wc -l < "/opt/tracer/output/trace.csv")" -le 1 ]; then
  echo "[WARNING] Trace file appears to be empty (only header)" >&2
fi

# Keep container running until stopped
tail -f /dev/null