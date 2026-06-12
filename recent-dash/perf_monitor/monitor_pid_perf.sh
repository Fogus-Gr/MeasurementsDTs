#!/bin/bash
# set -x # Commented out for production

OUTPUT_DIR="${OUTPUT_DIR:-/output}"
PID_FILE="${PID_FILE:-/pids/dash.pid}"
OUTPUT_FILE="${OUTPUT_DIR}/perf_metrics.csv"
INTERVAL="${INTERVAL:-0.5}"
CLK_TCK=$(getconf CLK_TCK)

mkdir -p "$OUTPUT_DIR"
touch "$OUTPUT_FILE" || { echo "Cannot write to output file"; exit 1; }

echo "timestamp,total_cpu_percent,total_mem_rss_kb,active_pids" > "$OUTPUT_FILE"
echo "[INFO] Starting /proc delta monitoring (Interval: ${INTERVAL}s, PID file: ${PID_FILE})..."

declare -A prev_ticks
declare -A prev_wall_ns

read_cpu_ticks() {
  awk '{print $14+$15}' "/proc/$1/stat" 2>/dev/null || echo ""
}

read_mem_rss_kb() {
  awk '/VmRSS/ {print $2; exit}' "/proc/$1/status" 2>/dev/null || echo "0"
}

while true; do
  if [ ! -f "$PID_FILE" ] || [ ! -r "$PID_FILE" ]; then
    echo "[WARN] PID file not found or not readable at $PID_FILE. Sleeping for ${INTERVAL}s."
    sleep "$INTERVAL"
    continue
  fi

  PIDS=$(tr '\n' ' ' < "$PID_FILE")
  if [ -z "$PIDS" ]; then
    echo "[WARN] PID file is empty. Sleeping for ${INTERVAL}s."
    sleep "$INTERVAL"
    continue
  fi

  timestamp=$(date +%s%3N)
  now_ns=$(date +%s%N)
  total_cpu="0.00"
  total_mem=0
  active_pids=0
  seen_pids=" "

  for pid in $PIDS; do
    case "$pid" in
      ''|*[!0-9]*)
        continue
        ;;
    esac

    if [ ! -r "/proc/$pid/stat" ]; then
      unset "prev_ticks[$pid]"
      unset "prev_wall_ns[$pid]"
      continue
    fi

    curr_ticks=$(read_cpu_ticks "$pid")
    if [ -z "$curr_ticks" ]; then
      continue
    fi

    mem_rss_kb=$(read_mem_rss_kb "$pid")
    total_mem=$((total_mem + mem_rss_kb))
    active_pids=$((active_pids + 1))
    seen_pids="${seen_pids}${pid} "

    prev_tick=${prev_ticks[$pid]:-}
    prev_wall=${prev_wall_ns[$pid]:-}
    cpu_percent="0.00"

    if [ -n "$prev_tick" ] && [ -n "$prev_wall" ]; then
      delta_ticks=$((curr_ticks - prev_tick))
      delta_wall_ns=$((now_ns - prev_wall))
      cpu_percent=$(awk -v ticks="$delta_ticks" -v clk="$CLK_TCK" -v ns="$delta_wall_ns" '
        BEGIN {
          if (ns > 0 && clk > 0) {
            printf "%.2f", ticks * 100000000000 / (clk * ns)
          } else {
            printf "0.00"
          }
        }
      ')
    fi

    total_cpu=$(awk -v a="$total_cpu" -v b="$cpu_percent" 'BEGIN {printf "%.2f", a + b}')
    prev_ticks[$pid]=$curr_ticks
    prev_wall_ns[$pid]=$now_ns
  done

  for tracked_pid in "${!prev_ticks[@]}"; do
    case "$seen_pids" in
      *" $tracked_pid "*) ;;
      *)
        unset "prev_ticks[$tracked_pid]"
        unset "prev_wall_ns[$tracked_pid]"
        ;;
    esac
  done

  echo "$timestamp,$total_cpu,$total_mem,$active_pids" >> "$OUTPUT_FILE"
  sleep "$INTERVAL"
done
