#!/bin/bash
# filepath: /home/user/MeasurementsDTs/monitor/monitor_pid.sh

# Script to monitor CPU (CPUs utilized), memory, and network TX/RX for a given PID and export to CSV

if [ -z "$1" ]; then
  echo "Usage: $0 <target_pid>"
  exit 1
fi

PID=$1
OUTPUT_FILE="/tmp/pid_metrics.csv"
INTERVAL=0.5  # Sampling interval in seconds (500ms)
DURATION=60   # Total duration in seconds

echo "timestamp,pid,cpu_utilized,mem_rss_kb,tx_bytes,rx_bytes" > "$OUTPUT_FILE"

PERF_OUT="/tmp/perf_tmp.txt"
BPFTRACE_OUT="/tmp/bpftrace_tmp.txt"

if ! ps -p "$PID" > /dev/null; then
  echo "Error: PID $PID does not exist"
  exit 1
fi

# Start bpftrace to monitor network TX/RX bytes
bpftrace -e "
  kprobe:tcp_sendmsg /pid == $PID/ {
    @tx_bytes[pid] = @tx_bytes[pid] + arg2;
  }
  kprobe:tcp_recvmsg /pid == $PID/ {
    @rx_bytes[pid] = @rx_bytes[pid] + arg2;
  }
  kprobe:sendto /pid == $PID/ {
    @tx_bytes[pid] = @tx_bytes[pid] + arg2;
  }
  kprobe:recvfrom /pid == $PID/ {
    @rx_bytes[pid] = @rx_bytes[pid] + arg2;
  }
  interval:ms:500 {
    printf(\"%d %d\\n\", @tx_bytes[$PID], @rx_bytes[$PID]);
    clear(@tx_bytes); clear(@rx_bytes);
  }
" > "$BPFTRACE_OUT" 2>/dev/null &

BPFTRACE_PID=$!

# Start perf stat to monitor CPU usage (CPUs utilized)
sudo perf stat -p "$PID" -e cpu-clock -I 500 2> "$PERF_OUT" 1>&2 &

PERF_PID=$!

cleanup() {
  kill $BPFTRACE_PID $PERF_PID 2>/dev/null
  rm -f "$PERF_OUT" "$BPFTRACE_OUT"
}
trap cleanup EXIT

START_TIME=$(date +%s)
while [ $(( $(date +%s) - $START_TIME )) -lt "$DURATION" ]; do
  TIMESTAMP=$(date +%s.%N | cut -b1-14)

  # Read perf stat output (CPUs utilized)
  if [ -f "$PERF_OUT" ]; then
    PERF_LINE=$(tail -n 10 "$PERF_OUT" | grep -E "cpu-clock.*msec" | tail -n 1)
    if [ -n "$PERF_LINE" ]; then
      # Robust extraction of CPUs utilized value
      CPU_UTIL=$(echo "$PERF_LINE" | grep -oP '#\s+\K[0-9.]+(?=\s+CPUs utilized)')
      if [ -z "$CPU_UTIL" ]; then
        CPU_UTIL=0
        echo "Debug: Could not extract CPUs utilized at $TIMESTAMP" >> /tmp/debug.log
      fi
    else
      CPU_UTIL=0
      echo "Debug: No valid perf cpu-clock data at $TIMESTAMP: $(tail -n 1 "$PERF_OUT")" >> /tmp/debug.log
    fi
  else
    CPU_UTIL=0
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

  echo "$TIMESTAMP,$PID,$CPU_UTIL,$MEM_RSS,$TX_BYTES,$RX_BYTES" >> "$OUTPUT_FILE"
  sleep "$INTERVAL"
done

cleanup

echo "Data collection complete. CSV file saved at $OUTPUT_FILE"