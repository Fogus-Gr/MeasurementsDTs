#!/bin/bash
# filepath: /home/user/MeasurementsDTs/ffmpeg_hpe/bpftrace-tracer/trace_video_traffic.sh

# Ensure output directory exists
mkdir -p /opt/tracer/output

# Capture 10 packets on port 8089 to detect dynamic port
tcpdump -i any -c 10 port 8089 > /tmp/tcpdump.out 2>> /opt/tracer/output/error.log

# Extract the dynamic port used by 172.18.0.3 from tcpdump output
DYNAMIC_PORT=$(grep "172.18.0.2.8089 > 172.18.0.3" /tmp/tcpdump.out | sed -n 's/.* > .*\.\([0-9]\+\):.*/\1/p' | head -1)
if [ -z "$DYNAMIC_PORT" ]; then
    echo "ERROR: Could not determine dynamic port for 172.18.0.3" >&2
    exit 1
fi
echo "Dynamic port identified: $DYNAMIC_PORT" >&2

# Define the HPE IP in hexadecimal (172.18.0.3 -> 0xAC120003)
HPE_IP_HEX=0xAC120003

# Create the bpftrace script to trace traffic on the dynamic port
cat <<EOF > /tmp/trace.bt
tracepoint:net:netif_receive_skb
{
    @rx_all += args->len;
}
interval:ms:10
{
    \$ts = nsecs / 1000000;
    printf("%llu,%llu\\n", \$ts, @rx_all);
    clear(@rx_all);
}
EOF

# Add header to the output file
echo "timestamp_ms,rx_video_bytes" > /opt/tracer/output/trace.csv

# Run bpftrace and append output to trace.csv, errors to error.log
if ! bpftrace /tmp/trace.bt >> /opt/tracer/output/trace.csv 2>> /opt/tracer/output/error.log; then
    echo "ERROR: bpftrace failed to run properly. Details from error.log:" >&2
    cat /opt/tracer/output/error.log >&2
    # Do NOT exit, just continue
fi

# Check if the trace file has data (more than just the header)
if [ "$(wc -l < "/opt/tracer/output/trace.csv")" -le 1 ]; then
    echo "[WARNING] Trace file appears to be empty (only header)" >&2
fi

# Keep container running until stopped
tail -f /dev/null