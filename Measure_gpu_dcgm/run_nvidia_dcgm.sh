#!/bin/bash
# filepath: /home/user/MeasurementsDTs/Measure_gpu_dcgm/run_nvidia_dcgm.sh

OUTFILE="gpu_stats.csv"

HEADER="timestamp,pstate,power.draw,temperature.gpu,utilization.gpu,utilization.memory,memory.total,memory.free,memory.used"
echo "$HEADER" > "$OUTFILE"

# Start the logging loop in the background (subshell)
(
    while true; do
        nvidia-smi --query-gpu=timestamp,pstate,power.draw,temperature.gpu,utilization.gpu,utilization.memory,memory.total,memory.free,memory.used --format=csv,noheader,nounits
        sleep 0.5
    done
) >> "$OUTFILE" &
LOOP_PID=$!

echo "GPU statistics are being logged to $OUTFILE"
echo "Press ENTER to stop logging and plot the results."
read

# Stop the background logging loop
kill $LOOP_PID

# Wait for the loop to exit
wait $LOOP_PID 2>/dev/null

# Proceed to plotting
python3 plot_smi_output.py