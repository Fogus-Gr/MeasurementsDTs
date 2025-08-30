#!/usr/bin/env bash
# filepath: /home/user/MeasurementsDTs/measure_flops.sh
set -euo pipefail

# Usage:
#   ./measure_flops.sh python3 your_hpe_script.py

# 1) Setup
CMD=("$@")
OUT=perf
CPU_LOG=cpu_mem_log.csv
GPU_LOG=gpu_log.csv
FLOP_LOG=flops_log.csv

rm -f ${OUT}.ncu-rep ${OUT}.csv "$CPU_LOG" "$GPU_LOG" "$FLOP_LOG"

echo "📈 Measuring FLOPS + CPU + GPU utilization for: ${CMD[*]}"

# 2) Get SM clock
SM_CLK=$(nvidia-smi --query-gpu=clocks.current.sm --format=csv,noheader,nounits)
if [[ "$SM_CLK" == "N/A" || -z "$SM_CLK" ]]; then
  echo "❌ ERROR: SM clock not available" >&2; exit 1
fi

# 3) Start GPU monitor
echo "timestamp,util.gpu %,mem.used MB" > "$GPU_LOG"
nvidia-smi --query-gpu=timestamp,utilization.gpu,memory.used \
           --format=csv,nounits -lms 500 >> "$GPU_LOG" &
GPU_MON_PID=$!

# 4) Start workload in background
"${CMD[@]}" &
PID=$!

# 5) Start CPU/memory monitor
echo "timestamp,cpu_percent,mem_rss_kb" > "$CPU_LOG"
(while kill -0 "$PID" 2>/dev/null; do
    ts=$(date +%s.%3N)
    stats=$(ps -o %cpu=,rss= -p "$PID" | awk '{print $1","$2}')
    echo "$ts,$stats" >> "$CPU_LOG"
    sleep 0.5
done) &
CPU_MON_PID=$!

6) Profile with Nsight Compute

ncu \
  --target-processes all \
  --metrics sm__inst_executed_pipe_fma.sum,sm__cycles_elapsed.sum,sm__inst_executed_pipe_tensor.sum,sm__inst_executed_pipe_tensor_op_hmma.sum,sm__inst_executed_pipe_tensor_op_dmma.sum,dram__bytes.sum,dram__throughput.avg.pct_of_peak_sustained_elapsed,sm__average_warp_latency.sum,l1tex__t_sectors_pipe_lsu_mem_global_op_ld.sum \
  --set base \
  --force-overwrite \
  --launch-skip 0 \
  --launch-count 3 \
  -o ${OUT} \
  "${CMD[@]}"

wait $PID

# 7) Stop monitors
kill $CPU_MON_PID $GPU_MON_PID 2>/dev/null || true

# 8) Export & parse ncu results
: <<'END_COMMENT'
ncu --import ${OUT}.ncu-rep --csv --export ${OUT}.csv --force-overwrite

FMA=$(grep -m1 sm__inst_executed_pipe_fma.sum ${OUT}.csv | cut -d',' -f2)
CYC=$(grep -m1 sm__cycles_elapsed.sum ${OUT}.csv | cut -d',' -f2)
TENSOR=$(grep -m1 sm__inst_executed_pipe_tensor.sum ${OUT}.csv | cut -d',' -f2)
DRAM_BYTES=$(grep -m1 dram__bytes.sum ${OUT}.csv | cut -d',' -f2)
LATENCY=$(grep -m1 sm__average_warp_latency.sum ${OUT}.csv | cut -d',' -f2)

if [[ -z "$FMA" || -z "$CYC" ]]; then
  echo "❌ ERROR: could not parse counters" >&2
  exit 1
fi

9) Compute FLOPS, TOPS, Bandwidth, Latency
python3 - <<EOF | tee "$FLOP_LOG"
sm_clk = float("$SM_CLK") * 1e6
fma = float("$FMA")
cycles = float("$CYC")
tensor = float("$TENSOR") if "$TENSOR" else 0
dram_bytes = float("$DRAM_BYTES") if "$DRAM_BYTES" else 0
latency = float("$LATENCY") if "$LATENCY" else 0

time_s = cycles / sm_clk if sm_clk > 0 else 0
flops = (fma * 2) / time_s / 1e9 if time_s > 0 else 0
tops = tensor / time_s / 1e12 if time_s > 0 else 0
bandwidth = dram_bytes / time_s / 1e9 if time_s > 0 else 0

print(f"🔢 FMA instructions: {fma:.0f}")
print(f"⏱️  Cycles elapsed:   {cycles:.0f}")
print(f"▶️  Measured GFLOPS:  {flops:.2f}")
print(f"▶️  Measured TOPS:    {tops:.2f}")
print(f"▶️  Bandwidth (GB/s): {bandwidth:.2f}")
print(f"▶️  Avg Warp Latency: {latency:.2f}")
EOF

# Generate gpu_log_elapsed.csv with elapsed seconds for plotting
awk -F, 'NR==3{
  split($1,a,"[ /:.]");
  start=mktime(a[1]" "a[2]" "a[3]" "a[4]" "a[5]" "a[6]);
  start_ms=a[7]
}
NR>2{
  split($1,b,"[ /:.]");
  t=mktime(b[1]" "b[2]" "b[3]" "b[4]" "b[5]" "b[6]);
  ms=b[7];
  elapsed=(t-start)+(ms-start_ms)/1000;
  print elapsed "," $2 "," $3
}' gpu_log.csv > gpu_log_elapsed.csv



# Generate cpu_mem_log_elapsed.csv with elapsed seconds for plotting
awk -F, 'NR==2{start=$1}
NR>1{
  elapsed=($1-start);
  print elapsed "," $2 "," $3
}' "$CPU_LOG" > cpu_mem_log_elapsed.csv

echo "  CPU (elapsed): cpu_mem_log_elapsed.csv"


echo "✅ Logs:"
echo "  CPU:    $CPU_LOG"
echo "  GPU:    $GPU_LOG"
echo "  GPU (elapsed): gpu_log_elapsed.csv"