#!/bin/bash

# Script to monitor CPU, memory, and network TX/RX for a given PID and export to CSV
# Uses bpftrace for network monitoring with 500ms interval

# Get PID file from environment variable or default
TARGET_PID_FILE="${TARGET_PID_FILE:-/pids/hpe.pid}"

# Set output directory - using fixed path that matches the volume mount
OUTPUT_DIR="/output"
OUTPUT_FILE="$OUTPUT_DIR/pid_metrics.csv"
NETSTATS_FILE="$OUTPUT_DIR/network_stats.csv"

mkdir -p "$OUTPUT_DIR"

# Debug output
echo "Starting monitoring script..."
echo "PID file: $TARGET_PID_FILE"
echo "Output file: $OUTPUT_FILE"

init_csv_files() {
    echo "timestamp,pid,cpu_percent,mem_rss_kb,tx_bytes,rx_bytes" > "$OUTPUT_FILE"
    echo "timestamp,pid,interface,bytes,sent" > "$NETSTATS_FILE"
}

write_metrics() {
    local timestamp=$1
    local pid=$2
    local cpu=$3
    local mem=$4
    local tx=$5
    local rx=$6
    local temp_line=$(mktemp)
    echo "$timestamp,$pid,${cpu:-0},${mem:-0},${tx:-0},${rx:-0}" > "$temp_line"
    (
        flock -x 200
        cat "$temp_line" >> "$OUTPUT_FILE"
        sync "$OUTPUT_FILE"
    ) 200>"$OUTPUT_FILE.lock"
    rm -f "$temp_line"
}

write_net_stats() {
    local timestamp=$1
    local pid=$2
    local interface=$3
    local bytes=$4
    local sent=$5
    local temp_line=$(mktemp)
    # Write to temp file first (not directly to output file)
    echo "$timestamp,$pid,$interface,$bytes,$sent" > "$temp_line"
    (
        flock -x 201
        cat "$temp_line" >> "$NETSTATS_FILE"
        sync "$NETSTATS_FILE"
    ) 201>"$NETSTATS_FILE.lock"
    rm -f "$temp_line"
}

cleanup() {
    echo "Cleaning up..."
    rm -f "$OUTPUT_FILE.lock" "$NETSTATS_FILE.lock"
    if [ -n "$bpftrace_pid" ]; then
        kill -TERM "$bpftrace_pid" 2>/dev/null
        wait "$bpftrace_pid" 2>/dev/null
    fi
}

init_csv_files
trap cleanup INT TERM EXIT

TIMEOUT=30
START_TIME=$(date +%s)
while [ ! -f "$TARGET_PID_FILE" ]; do
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - START_TIME))
    if [ $ELAPSED -ge $TIMEOUT ]; then
        echo "Error: Timeout waiting for PID file: $TARGET_PID_FILE"
        exit 1
    fi
    echo "Waiting for PID file... (${ELAPSED}s / ${TIMEOUT}s)"
    sleep 1
done

PID=$(cat "$TARGET_PID_FILE" 2>/dev/null)
if [ -z "$PID" ]; then
    echo "Error: Could not read PID from $TARGET_PID_FILE"
    exit 1
fi

echo "Monitoring PID: $PID"

FIFO_PATH="/tmp/bftrace_fifo_$PID"
rm -f "$FIFO_PATH"
mkfifo "$FIFO_PATH"

bpftrace -e '
    tracepoint:syscalls:sys_enter_sendto /pid == '$PID'/ { @tx_bytes += args->size; }
    tracepoint:net:netif_receive_skb /pid == '$PID'/ { @rx_bytes += args->len; }
    interval:ms:500  # Changed from 10ms to 500ms
    {
        $now = nsecs;
        if (@count++ > 0) {
            $elapsed = ($now - @start) / 1000000000;
            $tx_rate = @tx_bytes * 8 / $elapsed / 1000000;
            $rx_rate = @rx_bytes * 8 / $elapsed / 1000000;
            printf("%d %llu %llu (TX: %.2f Mbit/s, RX: %.2f Mbit/s)\n", \
                    '$PID', @tx_bytes, @rx_bytes, $tx_rate, $rx_rate) > "'$FIFO_PATH'";
        }
        @start = $now;
        @tx_bytes = 0;
        @rx_bytes = 0;
    }
' &
bpftrace_pid=$!

while read -r line; do
    if [[ $line =~ ^([0-9]+)[[:space:]]+([0-9]+)[[:space:]]+([0-9]+) ]]; then
        pid="${BASH_REMATCH[1]}"
        tx_bytes="${BASH_REMATCH[2]}"
        rx_bytes="${BASH_REMATCH[3]}"
        timestamp=$(date +%s.%N)
        write_net_stats "$timestamp" "$pid" "eth0" "$tx_bytes" "1"
        write_net_stats "$timestamp" "$pid" "eth0" "$rx_bytes" "0"
    fi
done < "$FIFO_PATH" &
fifo_reader_pid=$!

# Get number of cores
NUM_CORES=$(nproc)

while true; do
    timestamp=$(date +%s.%N)
    if ! ps -p "$PID" > /dev/null 2>&1; then
        echo "Process $PID is no longer running. Exiting..."
        break
    fi
    cpu_percent=$(ps -p "$PID" -o %cpu --no-headers | awk '{print $1}')
    # If you want percentage of total capacity (like Docker stats)
    normalized_cpu=$(echo "scale=2; $cpu_percent * 100 / $NUM_CORES" | bc)
    mem_rss_kb=$(grep VmRSS /proc/$PID/status 2>/dev/null | awk '{print $2}')
    tx_bytes=0
    rx_bytes=0
    if ! write_metrics "$timestamp" "$PID" "$normalized_cpu" "$mem_rss_kb" "$tx_bytes" "$rx_bytes"; then
        echo "Warning: Failed to write metrics at $(date)" >&2
    fi
    sleep 0.5
done

cleanup
echo "Data collection complete. CSV file saved at $OUTPUT_FILE"