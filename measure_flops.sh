#!/usr/bin/env bash
set -euo pipefail

# ----------------------------------------
# measure_flops.sh
#   – collects SM‐clock, FMA & cycle counts,
#     computes ops/cycle & GFLOPS
# Usage:
#   chmod +x measure_flops.sh
#   ./measure_flops.sh python3 main.py --method alphapose --input video.mp4
# ----------------------------------------

if [ $# -lt 1 ]; then
  echo "Usage: $0 <your command and args…>" >&2
  exit 1
fi

# 1) Grab current SM clock (MHz)
SM_CLK=$(nvidia-smi --query-gpu=clocks.current.sm \
                   --format=csv,noheader,nounits)
echo "📈 SM clock: ${SM_CLK} MHz"

# 2) Clean up old profiles
OUT=perf
rm -f ${OUT}.ncu-rep ${OUT}.csv

# 3) Make sure ncu is available
if ! command -v ncu &>/dev/null; then
  echo "❌ ERROR: 'ncu' not found. Install CUDA + Nsight Compute CLI." >&2
  exit 1
fi

# 4) Run your workload under Nsight Compute
#    –--target-processes all : attach to main Python + any children
#    –--metrics …           : only the two counters we need
#    –--set base            : minimal instrumentation (skips heavy graph API)
#    –--force-overwrite     : non-interactive overwrite
echo "▶️ Profiling command:" "$@"
ncu \
  --target-processes all \
  --metrics sm__inst_executed_pipe_fma.sum,sm__cycles_elapsed.sum \
  --set base \
  --force-overwrite \
  -o ${OUT} \
  "$@"

# 5) Export the .ncu-rep to CSV
ncu --import ${OUT}.ncu-rep \
    --csv \
    --export ${OUT}.csv \
    --force-overwrite

# 6) Extract FMA & cycle sums
FMA=$(grep -m1 sm__inst_executed_pipe_fma.sum ${OUT}.csv | cut -d',' -f2)
CYC=$(grep -m1 sm__cycles_elapsed.sum       ${OUT}.csv | cut -d',' -f2)

if [[ -z "$FMA" || -z "$CYC" ]]; then
  echo "❌ ERROR: could not parse counters from ${OUT}.csv" >&2
  exit 1
fi

echo "🔢 FMA instructions: $FMA"
echo "⏱️  Cycles elapsed:   $CYC"

# 7) Compute ops/cycle & measured GFLOPS
python3 - <<EOF
ops     = $FMA * 2           # each FMA = 2 FLOPs (mul+add)
cycles  = $CYC
clk_hz  = $SM_CLK * 1e6      # MHz → Hz
time_s  = cycles / clk_hz
print(f"▶️  Ops per cycle:      {ops/cycles:.2f}")
print(f"▶️  Measured GFLOPS:     {ops/time_s/1e9:.2f}")
EOF
