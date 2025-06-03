#!/bin/bash

# Script to monitor CPU, memory, and network TX/RX for a given PID and export to CSV

# Check if PID is provided
if [ -z "$1" ]; then
  echo "Usage: $0 <target_pid>"
  exit 1
fi

PID=$1
OUTPUT_FILE="/tmp/pid_metrics.csv"
INTERVAL=0.5  # Sampling interval in seconds (500ms)
DURATION=60   # Total duration in seconds

# Initialize CSV file with headers
echo "timestamp,pid,cpu_percent,mem_rss_kb,tx_bytes,rx_bytes" > "$OUTPUT_FILE"

# Temporary files for perf and bpftrace output
PERF_OUT="/tmp/perf_tmp.txt"
BPFTRACE_OUT="/tmp/bpftrace_tmp.txt"
ERROR_LOG="/tmp/error.log"

# Verify PID exists
if ! ps -p "$PID" > /dev/null; then
  echo "Error: PID $PID does not exist"
  exit 1
fi

# Start bpftrace to monitor network TX/RX bytes
bpftrace -e "
  kprobe:tcp_sendmsg /pid == $PID/ {
    @tx_bytes = @tx_bytes + arg2;
  }
  kprobe:tcp_recvmsg /pid == $PID/ {
    @rx_bytes = @rx_bytes + arg2;
  }
  interval:ms:500 {
    printf(\"%d %d\\n\", @tx_bytes, @rx_bytes);
    clear(@tx_bytes); clear(@rx_bytes);
  }
" > "$BPFTRACE_OUT" 2>> "$ERROR_LOG" &

BPFTRACE_PID=$!

# Start perf stat to monitor CPU usage
perf stat -p "$PID" -e task-clock -I 500 --per-task 2> "$PERF_OUT" 1>&2 &

PERF_PID=$!

# Function to clean up
cleanup() {
  kill $BPFTRACE_PID $PERF_PID 2>/dev/null
  rm -f "$PERF_OUT" "$BPFTRACE_OUT" "$ERROR_LOG"
}

# Trap Ctrl+C to clean up
trap cleanup EXIT

# Collect data for the specified duration
START_TIME=$(date +%s)
while [ $(( $(date +%s) - $START_TIME )) -lt $DURATION ]; do
  # Get current timestamp with millisecond precision
  TIMESTAMP=$(date +%s.%N | cut -d. -f1-14)

  # Read perf stat output (CPU usage as %CPU)
  if [ -f "$PERF_OUT" ]; then
    # Get the latest task-clock line for the PID
    PERF_LINE=$(tail -n 10 "$PERF_OUT" | grep -E "task-clock.*\s+$PID\s*$" | tail -n 1)
    if [ -n "$PERF_LINE" ]; then
      TASK_CLOCK=$(echo "$PERF_LINE" | awk '{print $1}' | tr -d ',')
      if [ -n "$TASK_CLOCK" ] && [[ "$TASK_CLOCK" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
        # Convert task to clock (clock) to %CPU
        CPU_PERCENT=$(echo "$TASK_CLOCK / 500 * 100" | bc -l | awk '{printf "%.2f", $1}')
      else
        CPU_PERCENT=0
        echo "Debug: Invalid task-clock value '$TASK_CLOCK' at $TIMESTAMP" >> /tmp/debug.log
      fi
    else
      CPU_PERCENT=0
      echo "Debug: No valid perf task-clock data for PID $PID at $TIMESTAMP: $(tail -n 1 "$PERF_OUT")" >> /tmp/debug.log
    fi
  else
    CPU_PERCENT=0
    echo "Debug: No perf output file at $TIMESTAMP" >> /tmp/debug.log
  fi

  # Read RSS from /proc/<pid>/status
  if [ -f "/proc/$PID/status" ]; then
    MEM_RSS=$(grep "^VmRSS:" "/proc/$PID/status" | awk '{print $2}')
    if [ -z "$MEM_RSS" ] || ! [[ "$MEM_RSS" =~ ^[0-9]+$ ]]; then
      MEM_RSS=0
      echo "Debug: Invalid or missing VmRSS at $TIMESTAMP" >> /tmp/debug.log
    fi
  else
    MEM_RSS=0
    echo "Debug: No /proc/$PID/status at $TIMESTAMP" >> /tmp/debug.log
  fi

  # Read bpftrace output (TX/RX bytes)
  if [ -f "$BPFTRACE_OUT" ]; then
    # Get the latest numeric line, skip non-numeric
    LAST_LINE=$(tail -n 1 "$BPFTRACE_OUT" | grep -E "^[0-9]+ [0-9]+$")
    if [ -n "$LAST_LINE" ]; then
      TX_BYTES=$(echo "$LAST_LINE" | awk '{print $1}')
      RX_BYTES=$(echo "$LAST_LINE" | awk '{print $2}')
    else
      TX_BYTES=0
      RX_BYTES=0
    fi
  else
    TX_BYTES=0
    RX_BYTES=0
    echo "Debug: No bpftrace output at $TIMESTAMP" >> /tmp/debug.log
  fi

  # Write to CSV
  echo "$TIMESTAMP,$PID,$CPU_PERCENT,$MEM_RSS,$TX_BYTES,$RX_BYTES" >> "$OUTPUT_FILE"

  sleep "$INTERVAL"
done

# Clean up
cleanup

echo "Data collection complete. CSV file saved at $OUTPUT_FILE"