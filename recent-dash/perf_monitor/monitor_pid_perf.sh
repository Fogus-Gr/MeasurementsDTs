#!/bin/bash
set -x  # Debug mode

TARGET_PID_FILE="/pids/dash.pid"
OUTPUT_DIR="/output"
OUTPUT_FILE="${OUTPUT_DIR}/aggregated_metrics.csv"
INTERVAL=0.5  # Sampling interval in seconds

# Ensure output directory exists
mkdir -p "$OUTPUT_DIR"

# Write CSV header if file doesn't exist or is empty
echo "timestamp,total_cpu_percent,total_mem_rss_kb,active_pids" > "$OUTPUT_FILE"

echo "[DEBUG] Starting monitoring script..."

# Main monitoring loop
while true; do
  timestamp=$(date +%s%3N)
  total_cpu_percent=0
  total_mem_rss_kb=0
  active_pids=0
  
  # Get updated PIDs from file every iteration
  if [ -f "$TARGET_PID_FILE" ]; then
    PIDS=($(cat "$TARGET_PID_FILE"))
    
    # Process each PID
    for PID in "${PIDS[@]}"; do
      if ps -p $PID >/dev/null 2>&1; then
        active_pids=$((active_pids + 1))
        
        # Get CPU and memory stats
        cpu=$(ps -p $PID -o %cpu= | tr -d ' ' || echo "0")
        mem=$(ps -p $PID -o rss= | tr -d ' ' || echo "0")
        
        # Properly handle floating point with bc
        total_cpu_percent=$(echo "$total_cpu_percent + $cpu" | bc)
        total_mem_rss_kb=$(echo "$total_mem_rss_kb + $mem" | bc)
      fi
    done
  else
    # Fallback to system-wide metrics if no PID file
    total_cpu_percent=$(top -bn1 | grep "Cpu(s)" | awk '{print $2 + $4}')
    total_mem_rss_kb=$(free -k | grep "Mem:" | awk '{print $3}')
    active_pids=1  # Just to have some data
  fi
  
  # Write data to CSV
  echo "$timestamp,$total_cpu_percent,$total_mem_rss_kb,$active_pids" >> "$OUTPUT_FILE"
  
  # Sleep before next sample
  sleep $INTERVAL || true  # Continue even if sleep is interrupted
done