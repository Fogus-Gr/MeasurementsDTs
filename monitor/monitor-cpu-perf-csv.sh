#!/bin/bash
# filepath: /home/user/MeasurementsDTs/monitor/monitor-cpu-perf-csv.sh

# Script to monitor CPU utilization of a process by PID using perf and export to CSV
#!/bin/bash

DURATION=60
INTERVAL=0.5
INTERVAL_MS=500  # 0.5 seconds = 500 milliseconds
OUTPUT_FILE="cpu_utilization.csv"
PID=$1
if [ -z "$PID" ]; then
    echo "Usage: $0 <pid>"
    exit 1
fi
if ! ps -p $PID > /dev/null; then
    echo "Error: PID $PID does not exist"
    exit 1
fi
# Initialize CSV file with headers
if [ -f $OUTPUT_FILE ]; then
    rm $OUTPUT_FILE
fi

echo "Timestamp,CPU_Utilization" > $OUTPUT_FILE

end_time=$((SECONDS + DURATION))

while [ $SECONDS -lt $end_time ]; do
    timestamp=$(date +"%Y-%m-%d %H:%M:%S.%3N")
    cpu_util=$(perf stat -p $PID -e cpu-clock --interval-print $INTERVAL_MS 2>&1 | awk '/cpu-clock/ {print $(NF-1)}')
    echo "$timestamp,$cpu_util" >> $OUTPUT_FILE
    sleep $INTERVAL
done