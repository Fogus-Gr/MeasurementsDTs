#!/bin/bash
# filepath: /app/run_perf_plot.sh

PID_FILE="/pids/dash.pid"

if [ ! -f "$PID_FILE" ]; then
  echo "PID file $PID_FILE not found!"
  exit 1
fi

for PID in $(cat "$PID_FILE"); do
  if ps -p "$PID" > /dev/null 2>&1; then
    echo "Running perf for PID $PID"
    sudo perf stat -p "$PID" -e cpu-clock,cycles -I 100 --interval-count 100 -x , 2> "perf_output_${PID}.txt"
  else
    echo "PID $PID is not running, skipping."
  fi
done

# Now run the Python script for each output
for PID in $(cat "$PID_FILE"); do
  if [ -f "perf_output_${PID}.txt" ]; then
    /usr/bin/python3 /app/plot_perf_metrics.py "perf_output_${PID}.txt"
  fi
done