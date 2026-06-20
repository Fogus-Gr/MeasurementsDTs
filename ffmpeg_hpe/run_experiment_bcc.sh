#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

timestamp=$(date +%Y%m%d_%H%M%S)
cpu_threads=$(lscpu | awk '/^CPU\(s\):/ {print $2; exit}')

# Step 1: Ensure bc is installed (for floating point math)
if ! command -v bc &> /dev/null; then
  echo "Installing bc (required for timestamp alignment)..."
  apt-get update && apt-get install -y bc || yum install -y bc
fi

# Step 2: Function to measure container startup time
measure_container_startup() {
  local container_name=$1
  local start_time=$2
  local container_id=$(docker ps -q --filter "name=^/${container_name}$" 2>/dev/null)
  if [ -z "$container_id" ]; then
    container_id=$(docker ps -qf "name=.*${container_name}.*")
  fi
  if [ -n "$container_id" ]; then
    local current_time=$(date +%s.%N)
    local time_diff=$(echo "$current_time - $start_time" | bc)
    echo "Container $container_name instantiation time: $time_diff seconds" >> "$results_dir/container_timing.txt"
    echo "[DEBUG] $container_name took $time_diff seconds to instantiate"
  else
    echo "[WARNING] Could not find container $container_name to measure startup time"
  fi
}

# Resolve a machine-aware resource profile for the current HPE method/device.
resolve_resource_profile() {
  local method="$1"
  local device="$2"
  local total_vcpus
  local total_mem_gib
  local streamer_cpus
  local hpe_cpus
  local hpe_mem_limit_gib
  local hpe_mem_reservation_gib
  local ov_threads_default

  total_vcpus=$(nproc 2>/dev/null || getconf _NPROCESSORS_ONLN 2>/dev/null || echo 4)
  total_mem_gib=$(awk '/MemTotal:/ {printf "%d\n", ($2 + 1048575) / 1048576; exit}' /proc/meminfo)

  if [ -z "$total_vcpus" ] || [ "$total_vcpus" -lt 3 ]; then
    echo "[ERROR] This experiment requires at least 3 vCPUs. Found: ${total_vcpus:-unknown}"
    exit 1
  fi

  if [ "$device" = "GPU" ]; then
    streamer_cpus=$(awk -v total="$total_vcpus" 'BEGIN {v=total*0.25; if (v<1.0) v=1.0; if (v>2.0) v=2.0; printf "%.1f", v}')
    hpe_mem_limit_gib=$(awk -v total="$total_mem_gib" 'BEGIN {v=total*0.25; if (v<8) v=8; if (v>16) v=16; printf "%d", int(v+0.5)}')
    ov_threads_default=$(awk -v total="$total_vcpus" -v streamer="$streamer_cpus" 'BEGIN {v=total-streamer; if (v<2) v=2; if (v>4) v=4; printf "%d", int(v+0.5)}')
  else
    streamer_cpus=$(awk -v total="$total_vcpus" 'BEGIN {v=total*0.375; if (v<1.5) v=1.5; if (v>2.5) v=2.5; printf "%.1f", v}')
    hpe_mem_limit_gib=$(awk -v total="$total_mem_gib" 'BEGIN {v=total*0.20; if (v<4) v=4; if (v>16) v=16; printf "%d", int(v+0.5)}')
    ov_threads_default=$(awk -v total="$total_vcpus" -v streamer="$streamer_cpus" 'BEGIN {v=total-streamer; if (v<2) v=2; printf "%d", int(v+0.5)}')
  fi

  hpe_cpus=$(awk -v total="$total_vcpus" -v streamer="$streamer_cpus" 'BEGIN {v=total-streamer; if (v<1.0) v=1.0; printf "%.1f", v}')
  hpe_mem_reservation_gib=$(awk -v value="$hpe_mem_limit_gib" 'BEGIN {printf "%d", int(value*0.75 + 0.5)}')

  : "${STREAMER_CPUS:=$streamer_cpus}"
  : "${STREAMER_RESERVATION_CPUS:=$streamer_cpus}"
  : "${HPE_CPUS:=$hpe_cpus}"
  : "${HPE_MEMORY_LIMIT:=${hpe_mem_limit_gib}G}"
  : "${HPE_MEMORY_RESERVATION:=${hpe_mem_reservation_gib}G}"
  : "${OV_MODE:=latency}"
  : "${OV_STREAMS:=1}"
  : "${OV_THREADS:=$ov_threads_default}"
  : "${OV_CPU_PINNING:=true}"
  : "${OV_HYPER_THREADING:=false}"

  export STREAMER_CPUS STREAMER_RESERVATION_CPUS HPE_CPUS
  export HPE_MEMORY_LIMIT HPE_MEMORY_RESERVATION
  export OV_MODE OV_STREAMS OV_THREADS OV_CPU_PINNING OV_HYPER_THREADING

  echo "[INFO] Detected ${total_vcpus} vCPUs and ${total_mem_gib} GiB RAM on this host"
  echo "[INFO] Selected ffmpeg_hpe profile: method=${method} device=${device}"
  echo "[INFO] Streamer CPUs: ${STREAMER_CPUS} (reservation: ${STREAMER_RESERVATION_CPUS})"
  echo "[INFO] HPE CPUs: ${HPE_CPUS}"
  echo "[INFO] HPE memory: ${HPE_MEMORY_LIMIT} (reservation: ${HPE_MEMORY_RESERVATION})"
  echo "[INFO] OV_THREADS: ${OV_THREADS}"
}

# Step 3: Enhanced diagnostics function with BCC support
capture_diagnostics() {
  echo "[DEBUG] ===== START DIAGNOSTICS ====="
  echo "[DEBUG] Docker containers:"
  docker ps -a
  echo "[DEBUG] HPE container logs:"
  HPE_CONTAINER_ID=$(docker ps -a -q --filter "name=^/hpe$")
  if [ -n "$HPE_CONTAINER_ID" ]; then
    echo "[DEBUG] HPE container ID: $HPE_CONTAINER_ID"
    docker logs "$HPE_CONTAINER_ID" 2>&1
  else
    echo "No HPE container found"
  fi
  echo "[DEBUG] BCC Tracer status:"
  TRACE_CONTAINER=$(docker ps -aqf "name=.*bcc-tracer.*")
  if [ -n "$TRACE_CONTAINER" ]; then
    docker logs "$TRACE_CONTAINER" 2>&1 | tail -n 20
    echo "[DEBUG] BCC Network connections:"
    docker exec "$TRACE_CONTAINER" ss -tulnp 2>/dev/null || echo "Could not check network connections"
  fi
  echo "[DEBUG] Video stream availability:"
  curl --max-time 3 -I "$STREAM_URL" 2>&1 || echo "Stream not accessible"
  echo "[DEBUG] ===== END DIAGNOSTICS ====="
}

# Step 4: Prepare results directory with BCC subdirectory
# Use HPE_METHOD as container_type for results dir naming
container_type="${1:-movenet}"

# Load all env variables from the rig-local .env if present and not already set
if [ -f "$SCRIPT_DIR/.env" ]; then
  while IFS= read -r line || [ -n "$line" ]; do
    # Skip comments and empty lines
    if [[ "$line" =~ ^[[:space:]]*# ]] || [[ -z "$line" ]]; then
      continue
    fi
    # Extract key and value
    key=$(echo "$line" | cut -d'=' -f1 | xargs)
    val=$(echo "$line" | cut -d'=' -f2- | xargs)
    # Set only if not already set in environment
    if [ -z "${!key}" ]; then
      export "$key=$val"
    fi
  done < "$SCRIPT_DIR/.env"
fi

# Require VIDEO_FILE to be set, else exit with error
if [[ -z "$VIDEO_FILE" ]]; then
  echo "[ERROR] VIDEO_FILE environment variable is not set. Please set it in your environment or in the .env file."
  exit 1
fi

VIDEO_FILE_INPUT="$VIDEO_FILE"
if [[ "$VIDEO_FILE_INPUT" == /app/videos/* ]]; then
  VIDEO_FILE_RELATIVE="${VIDEO_FILE_INPUT#/app/videos/}"
  VIDEO_FILE_CONTAINER="$VIDEO_FILE_INPUT"
elif [[ "$VIDEO_FILE_INPUT" == /videos/* ]]; then
  VIDEO_FILE_RELATIVE="${VIDEO_FILE_INPUT#/videos/}"
  VIDEO_FILE_CONTAINER="$VIDEO_FILE_INPUT"
elif [[ "$VIDEO_FILE_INPUT" == /* ]]; then
  VIDEO_FILE_RELATIVE="$(basename "$VIDEO_FILE_INPUT")"
  VIDEO_FILE_CONTAINER="$VIDEO_FILE_INPUT"
else
  VIDEO_FILE_RELATIVE="$VIDEO_FILE_INPUT"
  VIDEO_FILE_CONTAINER="/videos/$VIDEO_FILE_INPUT"
fi

export VIDEO_FILE="$VIDEO_FILE_CONTAINER"

VIDEO_FILE_BASENAME=$(basename "$VIDEO_FILE_RELATIVE")
if [[ "$VIDEO_FILE_BASENAME" == "" || "$VIDEO_FILE_BASENAME" == "." || "$VIDEO_FILE_BASENAME" == "/" ]]; then
  VIDEO_FILE_BASENAME="unknown"
fi

# Placeholder - will be resolved after Step 10
device_type=""
start_time=$(date +%s)
# NOTE: results_dir created AFTER device configuration in Step 10
mkdir -p ./logs ./traces/bcc ./perf

# Step 5: Enhanced cleanup including BCC tracer outputs
echo "[DEBUG] Cleaning previous run artifacts..."
rm -f ./results/*.csv ./traces/*.csv 2>/dev/null || true
rm -f ./csv/*.csv 2>/dev/null || true
rm -rf ./tracer_output/* 2>/dev/null || true

arguments="$*"
export HPE_METHOD="${1:-movenet}"
if [[ "$HPE_METHOD" == "alphapose" || "$arguments" == *"--method alphapose"* ]]; then
  export HPE_DEVICE="GPU"
elif [[ "$HPE_METHOD" == hrnet* ]]; then
  export HPE_DEVICE="CPU"
else
  export HPE_DEVICE="CPU"
fi

if [[ "$arguments" == *"--device GPU"* ]]; then
  export HPE_DEVICE="GPU"
elif [[ "$arguments" == *"--device CPU"* ]]; then
  export HPE_DEVICE="CPU"
fi

resolve_resource_profile "$HPE_METHOD" "$HPE_DEVICE"

echo "Preparing experiment workspace..."

# Step 6: Compose file and container names
docker_compose_file="docker-compose.yaml"
HPE_SERVICE="hpe"
H264_CONTAINER_NAME="h264-streaming-server"

# Step 7: Stop and remove existing containers
echo "Stopping and removing existing containers..."
docker compose -f $docker_compose_file down -v --remove-orphans
docker rm -f hpe bcc-tracer 2>/dev/null || true

# Step 8: Start the streaming server
echo "Starting h264-streaming-server..."
docker compose -f $docker_compose_file up -d h264-streaming-server

# Wait for healthcheck
wait_start=$(date +%s)
wait_timeout=60
while [[ $(docker inspect --format='{{.State.Health.Status}}' $H264_CONTAINER_NAME 2>/dev/null) != "healthy" ]]; do
  echo "Waiting for h264-streaming-server to become healthy..."
  current=$(date +%s)
  if [ $((current - wait_start)) -gt $wait_timeout ]; then
    echo "[WARNING] Streaming server healthcheck timed out, continuing anyway..."
    break
  fi
  sleep 2
done

# Step 9: Get streaming server IP
STREAM_SERVER_IP=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' $H264_CONTAINER_NAME)
STREAM_URL="http://${STREAM_SERVER_IP}:8089/stream.h264"
echo "[DEBUG] Using direct IP for stream: $STREAM_URL"

# Step 10: Configure HPE environment
arguments="$*"  # Capture all arguments

shift || true
export HPE_EXTRA_ARGS="$*"
export HPE_INPUT="http://h264-streaming-server:8089/stream.h264"
export HPE_DEVICE="${HPE_DEVICE:-CPU}"

echo "Selected configuration:"
echo "Method: $HPE_METHOD"
echo "Device: $HPE_DEVICE"
echo "Input: $HPE_INPUT"
echo "Extra args: ${HPE_EXTRA_ARGS:-<none>}"

# Resolve device type from configuration
device_type="${HPE_DEVICE:-CPU}"
if [[ -z "$device_type" ]]; then
  device_type="CPU"
fi

# Create results dir with correct device type
results_dir="results_${container_type}_${cpu_threads}cores_${device_type}_${VIDEO_FILE_BASENAME}_${timestamp}"
mkdir -p "$results_dir/logs" "$results_dir/traces/bcc" "$results_dir/perf"
mkdir -p ./pids
echo "Results directory: $results_dir"

# Initialize timing file after results_dir is known.
touch "$results_dir/container_timing.txt"
echo "Container Instantiation Timing:" > "$results_dir/container_timing.txt"

# Step 11: Start performance monitoring before HPE exists.
perf_monitor_start=$(date +%s.%N)
echo "[DEBUG] Starting monitoring containers..."
docker compose -f $docker_compose_file up -d --build perf_monitor
measure_container_startup "perf_monitor" "$perf_monitor_start"

# Step 12: Start HPE container
hpe_start=$(date +%s.%N)
docker compose -f $docker_compose_file up -d hpe
measure_container_startup "$HPE_SERVICE" "$hpe_start"

# Write the HPE host PID for process-level monitoring.
# entrypoint.sh uses exec "$@", so python3 main.py becomes PID 1 inside the
# container. docker inspect .State.Pid returns the host PID of that process,
# which is the exact process the monitor should sample.
HPE_CONTAINER=$(docker ps -qf "name=^/hpe$")
if [ -n "$HPE_CONTAINER" ]; then
  for attempt in {1..5}; do
    HPE_HOST_PID=$(docker inspect --format='{{.State.Pid}}' "$HPE_CONTAINER" 2>/dev/null || true)
    if [ -n "$HPE_HOST_PID" ] && [ "$HPE_HOST_PID" != "0" ]; then
      echo "$HPE_HOST_PID" > ./pids/hpe.pid
      echo "[DEBUG] HPE host PID written to pids/hpe.pid: $HPE_HOST_PID"
      echo "HPE host PID (process-level monitor target): $HPE_HOST_PID" >> "$results_dir/container_timing.txt"
      break
    fi
    echo "[DEBUG] Waiting for HPE host PID (attempt $attempt/5)..."
    sleep 1
  done
  if [ ! -s ./pids/hpe.pid ]; then
    echo "[WARNING] Could not find HPE host PID — perf_monitor will keep waiting for pids/hpe.pid"
  fi
fi

# Special handling for BCC tracer
bcc_start=$(date +%s.%N)
echo "[DEBUG] Starting GPU and BCC monitoring containers..."
gpu_start=$(date +%s.%N)
docker compose -f $docker_compose_file up -d gpu-metrics
docker compose -f $docker_compose_file up -d bcc-tracer

PERF_MONITOR_CONTAINER=$(docker ps -qf "name=perf_monitor")
GPU_METRICS_CONTAINER=$(docker ps -qf "name=gpu-metrics")
TRACE_CONTAINER=$(docker ps -qf "name=.*bcc-tracer.*")

measure_container_startup "gpu-metrics" "$gpu_start"

# Special handling for BCC tracer
echo "[DEBUG] Waiting for BCC tracer to initialize..."
sleep 8  # Extra time for BCC compilation and port detection
measure_container_startup "bcc-tracer" "$bcc_start"

# Verify BCC tracer status
detected_port=""
for i in {1..10}; do
  docker logs $TRACE_CONTAINER 2>&1 | tail -n 10
  if docker logs $TRACE_CONTAINER 2>&1 | grep -q "Monitoring HPE traffic on port"; then
    echo "[DEBUG] BCC tracer successfully initialized"
    detected_port=$(docker logs $TRACE_CONTAINER 2>&1 | grep "Monitoring HPE traffic on port" | awk '{print $NF}')
    echo "BCC detected HPE video port: $detected_port" >> "$results_dir/container_timing.txt"
  fi
  sleep 2
done

if [[ -z "$detected_port" ]]; then
  echo "[WARNING] BCC tracer did not detect HPE video port after 20 seconds."
fi
echo "[DEBUG] waiting for experiment to finish..."

# Step 13b: Collect initial logs
sleep 2  # Allow containers to stabilize
HPE_CONTAINER_ID=$(docker ps -qf "name=^/hpe$")
if [ -n "$HPE_CONTAINER_ID" ]; then
  docker logs "$HPE_CONTAINER_ID" > "$results_dir/logs/hpe_startup.log" 2>&1
else
  echo "[WARNING] HPE container not running at startup log collection" > "$results_dir/logs/hpe_startup.log"
fi
docker logs $TRACE_CONTAINER > "$results_dir/logs/bcc_tracer_startup.log" 2>&1

# Step 14: Monitor experiment progress
while true; do
  HPE_CONTAINER=$(docker ps -q --filter "name=^/hpe$")
  if [ -z "$HPE_CONTAINER" ]; then
    echo "[DEBUG] HPE container stopped, ending experiment..."
    capture_diagnostics
    break
  fi
  CONTAINER_STATUS=$(docker inspect --format='{{.State.Status}}' $HPE_CONTAINER 2>/dev/null || echo "exited")
  if [[ "$CONTAINER_STATUS" != "running" ]]; then
    echo "[WARNING] HPE container has stopped with status: $CONTAINER_STATUS"
    capture_diagnostics
    break
  fi
  sleep 5
done

# Check HPE container exit code — distinguishes clean exit from crash/OOM
HPE_CONTAINER_FINAL=$(docker ps -aqf "name=^/hpe$")
if [ -n "$HPE_CONTAINER_FINAL" ]; then
  hpe_exit_code=$(docker inspect --format='{{.State.ExitCode}}' "$HPE_CONTAINER_FINAL" 2>/dev/null || echo "unknown")
  echo "[INFO] HPE container exit code: $hpe_exit_code" | tee -a "$results_dir/logs/hpe_exit.log"
  if [ "$hpe_exit_code" != "0" ] && [ "$hpe_exit_code" != "unknown" ]; then
    echo "[WARNING] HPE container exited with non-zero code ($hpe_exit_code) — results may be incomplete"
  fi
fi

# Step 15: Enhanced data collection
echo "[DEBUG] Collecting experiment results..."

# Performance data — loop over all filenames written by perf_monitor variants
mkdir -p "$results_dir/perf"
if [ -n "$PERF_MONITOR_CONTAINER" ]; then
  for perf_file in perf_metrics.csv pid_metrics.csv network_stats.csv; do
    if docker exec $PERF_MONITOR_CONTAINER ls -la /output/$perf_file 2>/dev/null || false; then
      docker cp "$PERF_MONITOR_CONTAINER:/output/$perf_file" "$results_dir/perf/$perf_file" && \
      echo "Copied $perf_file to $results_dir/perf/$perf_file" || \
      echo "[WARNING] Failed to copy $perf_file"
    fi
  done
  chmod -R u+rw "$results_dir"
fi

# GPU metrics
mkdir -p "$results_dir/gpu"
[ -f ./results/gpu_metrics.csv ] && cp ./results/gpu_metrics.csv "$results_dir/gpu/"

# BCC tracer outputs
if [ -n "$TRACE_CONTAINER" ]; then
  echo "[DEBUG] Collecting BCC tracer outputs..."
  docker cp "$TRACE_CONTAINER:/opt/tracer/output/hpe_video_rx.csv" "$results_dir/traces/bcc/video_rx.csv" 2>/dev/null || true
  echo "[DEBUG] Copied BCC trace data (or skipped if not present)"
  docker cp "$TRACE_CONTAINER:/opt/tracer/output/logs" "$results_dir/traces/bcc/" 2>/dev/null || true
  echo "[DEBUG] Copied BCC logs (or skipped)"
  if [[ -n "$detected_port" ]]; then
    echo "BCC detected HPE video port: $detected_port" > "$results_dir/traces/bcc/port_info.txt"
  else
    docker logs "$TRACE_CONTAINER" 2>&1 | grep "Monitoring HPE traffic on port" > "$results_dir/traces/bcc/port_info.txt" 2>/dev/null || true
  fi
  echo "[DEBUG] Extracted port info (or skipped)"
fi

# Container logs
container_list=("hpe" "perf_monitor" "bcc-tracer" "gpu-metrics")
for container in "${container_list[@]}"; do
  container_id=$(docker ps -aqf "name=^/${container}$")
  [ -n "$container_id" ] && docker logs $container_id > "$results_dir/logs/$container.log" 2>&1
done

# HPE output — read from bind-mounted host path (container has already exited)
mkdir -p "$results_dir/hpe_output"
echo "[DEBUG] Checking for HPE output files in $(pwd)/results/..."
ls -la ./results/*.csv 2>/dev/null || echo "[DEBUG] No CSV files found in ./results/"
# Only copy HPE-specific outputs (JSON and Tx), not monitoring sidecar outputs
if ls ./results/*_JSON.csv ./results/*_Tx.csv 1>/dev/null 2>&1; then
  cp ./results/*_JSON.csv "$results_dir/hpe_output/" 2>/dev/null || true
  cp ./results/*_Tx.csv "$results_dir/hpe_output/" 2>/dev/null || true
  echo "Copied HPE output files to $results_dir/hpe_output/"
  ls "$results_dir/hpe_output/"
else
  echo "[WARNING] No HPE CSV files (JSON/Tx) found in ./results/"
fi

# Step 16: Cleanup
echo "[DEBUG] Stopping and cleaning up containers..."
docker compose -f $docker_compose_file down --remove-orphans --volumes
docker rm -f hpe h264-streaming-server gpu-metrics perf_monitor bcc-tracer 2>/dev/null || true

# Final timing
end_time=$(date +%s)
duration=$((end_time - start_time))
echo "Experiment completed in $duration seconds."
echo "Results saved in: $results_dir"

# Verify collected data
echo "[DEBUG] Collected data summary:"
tree -h "$results_dir" | head -20
