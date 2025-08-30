#!/bin/bash
# set -x # Commented out for production

OUTPUT_DIR="/output"
PID_FILE="/pids/dash.pid"
OUTPUT_FILE="${OUTPUT_DIR}/perf_metrics.csv"
INTERVAL=1 # pidstat works best with intervals of 1 second or more

# Ensure output directory exists and we can write to it
mkdir -p "$OUTPUT_DIR"
touch "$OUTPUT_FILE" || { echo "Cannot write to output file"; exit 1; }

echo "timestamp,total_cpu_percent,total_mem_rss_kb,active_pids" > "$OUTPUT_FILE"

echo "[INFO] Starting monitoring script with pidstat (Interval: ${INTERVAL}s)..."

# Main monitoring loop
while true; do
  # Check if the PID file exists and is readable
  if [ ! -f "$PID_FILE" ] || [ ! -r "$PID_FILE" ]; then
    echo "[WARN] PID file not found or not readable at $PID_FILE. Sleeping for ${INTERVAL}s."
    sleep $INTERVAL
    continue
  fi

  # Read all PIDs into a comma-separated string for pidstat
  PIDS=$(cat "$PID_FILE" | tr '\n' ',' | sed 's/,$//')

  if [ -z "$PIDS" ]; then
    echo "[WARN] PID file is empty. Sleeping for ${INTERVAL}s."
    sleep $INTERVAL
    continue
  fi

  # --- Use pidstat for accurate interval-based CPU and memory ---
  # pidstat -p $PIDS -u -r $INTERVAL 1
  # This command samples for $INTERVAL seconds and then prints the average over that interval.
  # The output is parsed to get the total CPU and Memory.
  
  # We run pidstat in the background to capture its output without blocking the timestamp
  # Note: The actual metrics will correspond to the end of the interval.
  
  metrics=$(pidstat -p $PIDS -u -r $INTERVAL 1 | tail -n +4)
  
  # If pidstat returned no data (all pids died), then we record zeros
  if [ -z "$metrics" ]; then
      total_cpu="0"
      total_mem="0"
      active_pids=0
  else
      # Use awk for powerful column-based processing
      totals=$(echo "$metrics" | awk '
        { 
          cpu_sum += $8;   # %CPU column
          mem_sum += $7;   # RSS (kB) column
          count++ 
        } 
        END { 
          print cpu_sum, mem_sum, count 
        }
      ')
      
      total_cpu=$(echo $totals | cut -d ' ' -f 1)
      total_mem=$(echo $totals | cut -d ' ' -f 2)
      active_pids=$(echo $totals | cut -d ' ' -f 3)
  fi

  timestamp=$(date +%s%3N)
  echo "$timestamp,$total_cpu,$total_mem,$active_pids" >> "$OUTPUT_FILE"

  # No extra sleep is needed because pidstat's interval handles the delay
done