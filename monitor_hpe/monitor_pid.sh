#!/bin/bash

# Script to monitor CPU, memory, and network TX/RX for a given PID and export to CSV
# Uses bftrace for network monitoring with 500ms interval

# Get PID from environment variable
if [ -z "$TARGET_PID_FILE" ]; then
  echo "Error: TARGET_PID_FILE environment variable not set"
  exit 1
fi

# Set output directory - using fixed path that matches the volume mount
OUTPUT_DIR="/output"
OUTPUT_FILE="$OUTPUT_DIR/pid_metrics.csv"
NETSTATS_FILE="$OUTPUT_DIR/network_stats.csv"

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Debug output
echo "Starting monitoring script..."
echo "PID file: $TARGET_PID_FILE"
echo "Output file: $OUTPUT_FILE"

# Function to initialize CSV files
init_csv_files() {
    # Main metrics CSV
    echo "timestamp,pid,cpu_percent,mem_rss_kb,tx_bytes,rx_bytes" > "$OUTPUT_FILE"
    # Network stats CSV
    echo "timestamp,pid,interface,bytes,sent" > "$NETSTATS_FILE"
}

# Function to write metrics with retry logic
write_metrics() {
    local timestamp=$1
    local pid=$2
    local cpu=$3
    local mem=$4
    local tx=$5
    local rx=$6
    
    # Create a temporary file
    local temp_line=$(mktemp)
    echo "$timestamp,$pid,${cpu:-0},${mem:-0},${tx:-0},${rx:-0}" > "$temp_line"
    
    # Use flock to prevent concurrent writes
    (
        flock -x 200
        # Append the line to the output file
        cat "$temp_line" >> "$OUTPUT_FILE"
        # Force sync to disk
        sync "$OUTPUT_FILE"
    ) 200>"$OUTPUT_FILE.lock"
    
    # Clean up
    rm -f "$temp_line"
}

# Function to write network stats
write_net_stats() {
    local timestamp=$1
    local pid=$2
    local interface=$3
    local bytes=$4
    local sent=$5
    
    # Create a temporary file
    local temp_line=$(mktemp)
    echo "$timestamp,$pid,$interface,$bytes,$sent" >> "$NETSTATS_FILE"
    
    # Use flock to prevent concurrent writes
    (
        flock -x 201
        # Append the line to the network stats file
        cat "$temp_line" >> "$NETSTATS_FILE"
        # Force sync to disk
        sync "$NETSTATS_FILE"
    ) 201>"$NETSTATS_FILE.lock"
    
    # Clean up
    rm -f "$temp_line"
}

# Function to clean up
cleanup() {
    echo "Cleaning up..."
    # Remove lock files
    rm -f "$OUTPUT_FILE.lock" "$NETSTATS_FILE.lock"
    # Kill bpftrace process if running
    if [ -n "$bpftrace_pid" ]; then
        kill -TERM "$bpftrace_pid" 2>/dev/null
        wait "$bpftrace_pid" 2>/dev/null
    fi
    # Don't exit here to allow cleanup to be used for both signals and normal exit
}

# Initialize CSV files
init_csv_files

# Trap Ctrl+C and other signals to clean up
trap cleanup INT TERM EXIT

# Wait for PID file to be created with a timeout
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

# Read PID from file
PID=$(cat "$TARGET_PID_FILE" 2>/dev/null)
if [ -z "$PID" ]; then
    echo "Error: Could not read PID from $TARGET_PID_FILE"
    exit 1
fi

echo "Monitoring PID: $PID"

# Create a FIFO for bftrace output
FIFO_PATH="/tmp/bftrace_fifo_$PID"
rm -f "$FIFO_PATH"
mkfifo "$FIFO_PATH"

# Start bftrace in the background with 10ms interval
bpftrace -e '
    tracepoint:syscalls:sys_enter_sendto /pid == '$PID'/ { @tx_bytes += args->size; }
    tracepoint:net:netif_receive_skb /pid == '$PID'/ { @rx_bytes += args->len; }

    interval:ms:10
    {
        $now = nsecs;
        if (@count++ > 0) {
            $elapsed = ($now - @start) / 1000000000;  // Convert to seconds
            $tx_rate = @tx_bytes * 8 / $elapsed / 1000000;  // Mbits/s
            $rx_rate = @rx_bytes * 8 / $elapsed / 1000000;  // Mbits/s
            
            printf("%d %llu %llu (TX: %.2f Mbit/s, RX: %.2f Mbit/s)\n", 
                    '$PID', @tx_bytes, @rx_bytes, $tx_rate, $rx_rate) > "'$FIFO_PATH'";
        }
        
        @start = $now;
        @tx_bytes = 0;
        @rx_bytes = 0;
    }
' &
bpftrace_pid=$!

# Read from FIFO in the background
while read -r line; do
    if [[ $line =~ ^([0-9]+)[[:space:]]+([0-9]+)[[:space:]]+([0-9]+) ]]; then
        pid="${BASH_REMATCH[1]}"
        tx_bytes="${BASH_REMATCH[2]}"
        rx_bytes="${BASH_REMATCH[3]}"
        timestamp=$(date +%s.%N)
        
        # Write to network stats CSV
        write_net_stats "$timestamp" "$pid" "eth0" "$tx_bytes" "1"  # 1 for sent
        write_net_stats "$timestamp" "$pid" "eth0" "$rx_bytes" "0"  # 0 for received
    fi
done < "$FIFO_PATH" &
fifo_reader_pid=$!

# Main monitoring loop
while true; do
    # Get current timestamp (in seconds since epoch with nanosecond precision)
    timestamp=$(date +%s.%N)
    
    # Check if PID is still running
    if ! ps -p "$PID" > /dev/null 2>&1; then
        echo "Process $PID is no longer running. Exiting..."
        break
    fi
    
    # Get CPU usage for the process
    cpu_percent=$(ps -p "$PID" -o %cpu --no-headers | awk '{print $1}')
    
    # Get memory usage (RSS in KB)
    mem_rss_kb=$(grep VmRSS /proc/$PID/status 2>/dev/null | awk '{print $2}')
    
    # Get network stats from bftrace (dummy values for now, updated via FIFO)
    tx_bytes=0
    rx_bytes=0
    
    # Write metrics with error handling
    if ! write_metrics "$timestamp" "$PID" "$cpu_percent" "$mem_rss_kb" "$tx_bytes" "$rx_bytes"; then
        echo "Warning: Failed to write metrics at $(date)" >&2
    fi
    
    # Sleep for 500ms
    sleep 0.5
done

# Clean up
cleanup
echo "Data collection complete. CSV file saved at $OUTPUT_FILE"