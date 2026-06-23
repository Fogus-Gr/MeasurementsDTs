#!/bin/bash
set -e

# run_experiment_cpu.sh — CPU-only experiment runner (no GPU metrics)
#
# Orchestrates the full experiment lifecycle:
#   1. Clean up previous containers and CSVs
#   2. Start the H.264 streaming server and wait for healthcheck
#   3. Start the HPE container (CPU device, OpenVINO backends)
#   4. Start monitoring sidecars (perf_monitor for CPU/memory, bcc-tracer for RX)
#   5. Poll until HPE container exits
#   6. Copy all CSVs and logs into results_<method>_<cores>CPU_<video>_<timestamp>/
#   7. Tear everything down
#
# Usage:
#   ./run_experiment_cpu.sh movenet
#   ./run_experiment_cpu.sh openpose
#   ./run_experiment_cpu.sh ae1 --max_frames 500
#   ./run_experiment_cpu.sh hrnet --timeout 60

timestamp=$(date +%Y%m%d_%H%M%S)
cpu_threads=$(lscpu | awk '/^CPU\(s\):/ {print $2; exit}')

# Step 1: Ensure bc is installed (for floating point math)
if ! command -v bc &> /dev/null; then
  echo "Installing bc (required for timestamp alignment)..."
  apt-get update && apt-get install -y bc
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

# Step 3: Diagnostics function
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

# Step 4: Prepare results directory
container_type="${1:-movenet}"

# Load VIDEO_FILE from .env.cpu if not set
if [[ -z "$VIDEO_FILE" ]]; then
  if [ -f .env.cpu ]; then
    export $(grep -E '^VIDEO_FILE=' .env.cpu | xargs)
  fi
fi

if [[ -z "$VIDEO_FILE" ]]; then
  echo "[ERROR] VIDEO_FILE environment variable is not set. Please set it in .env.cpu"
  exit 1
fi

VIDEO_FILE_BASENAME=$(basename "$VIDEO_FILE")
if [[ "$VIDEO_FILE_BASENAME" == "" || "$VIDEO_FILE_BASENAME" == "." || "$VIDEO_FILE_BASENAME" == "/" ]]; then
  VIDEO_FILE_BASENAME="unknown"
fi

device_type=""
start_time=$(date +%s)
mkdir -p ./logs ./traces/bcc ./perf

# Step 5: Cleanup
echo "[DEBUG] Cleaning previous run artifacts..."
rm -f ./results/*.csv ./traces/*.csv 2>/dev/null || true
rm -f ./csv/*.csv 2>/dev/null || true
rm -rf ./tracer_output/* 2>/dev/null || true

echo "Preparing experiment workspace..."

# Step 6: Compose file and container names
docker_compose_file="docker-compose.cpu.yaml"
env_file=".env.cpu"
HPE_SERVICE="hpe"
H264_CONTAINER_NAME="h264-streaming-server"

# Step 7: Stop and remove existing containers
echo "Stopping and removing existing containers..."
docker compose --env-file $env_file -f $docker_compose_file down -v --remove-orphans
docker rm -f hpe bcc-tracer 2>/dev/null || true

# Step 8: Start the streaming server
echo "Starting h264-streaming-server..."
docker compose --env-file $env_file -f $docker_compose_file up -d h264-streaming-server

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

# Step 10: Configure HPE environment — always CPU on this rig
arguments="$*"

export HPE_METHOD="${1:-movenet}"
shift || true
export HPE_EXTRA_ARGS="$*"
export HPE_INPUT="http://h264-streaming-server:8089/stream.h264"
export HPE_DEVICE="CPU"

# Allow explicit --device override (though GPU won't work without hardware)
if [[ "$arguments" == *"--device GPU"* ]]; then
  export HPE_DEVICE="GPU"
elif [[ "$arguments" == *"--device CPU"* ]]; then
  export HPE_DEVICE="CPU"
fi

echo "Selected configuration:"
echo "Method: $HPE_METHOD"
echo "Device: $HPE_DEVICE"
echo "Input: $HPE_INPUT"
echo "Extra args: ${HPE_EXTRA_ARGS:-<none>}"

device_type="${HPE_DEVICE}"

# Create results dir with correct device type
results_dir="results_${container_type}_${cpu_threads}cores_${device_type}_${VIDEO_FILE_BASENAME}_${timestamp}"
mkdir -p "$results_dir/logs" "$results_dir/traces/bcc" "$results_dir/perf"
mkdir -p ./pids
echo "Results directory: $results_dir"

# Initialize timing file
touch "$results_dir/container_timing.txt"
echo "Container Instantiation Timing:" > "$results_dir/container_timing.txt"

# Step 11: Start performance monitoring
perf_monitor_start=$(date +%s.%N)
echo "[DEBUG] Starting monitoring containers..."
docker compose --env-file $env_file -f $docker_compose_file up -d --build perf_monitor
measure_container_startup "perf_monitor" "$perf_monitor_start"

# Step 12: Start HPE container
hpe_start=$(date +%s.%N)
docker compose --env-file $env_file -f $docker_compose_file up -d hpe
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

# Step 13: Start BCC tracer (no gpu-metrics on CPU-only rig)
bcc_start=$(date +%s.%N)
echo "[DEBUG] Starting BCC monitoring container..."
docker compose --env-file $env_file -f $docker_compose_file up -d bcc-tracer

PERF_MONITOR_CONTAINER=$(docker ps -qf "name=perf_monitor")
TRACE_CONTAINER=$(docker ps -qf "name=.*bcc-tracer.*")

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
docker logs $(docker ps -qf "name=^/hpe$") > "$results_dir/logs/hpe_startup.log" 2>&1
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

# Step 15: Collect results
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

# BCC tracer outputs
if [ -n "$TRACE_CONTAINER" ]; then
  echo "[DEBUG] Collecting BCC tracer outputs..."
  docker cp "$TRACE_CONTAINER:/opt/tracer/output/hpe_video_rx.csv" "$results_dir/traces/bcc/video_rx.csv" 2>/dev/null || true
  echo "[DEBUG] Copied BCC trace data (or skipped if not present)"
  docker cp "$TRACE_CONTAINER:/opt/tracer/output/logs" "$results_dir/traces/bcc/" 2>/dev/null || true
  echo "[DEBUG] Copied BCC logs (or skipped)"
  docker logs "$TRACE_CONTAINER" 2>&1 | grep "Monitoring HPE traffic on port" > "$results_dir/traces/bcc/port_info.txt" 2>/dev/null || true
  echo "[DEBUG] Extracted port info (or skipped)"
fi

# Container logs — no gpu-metrics on CPU rig
container_list=("hpe" "perf_monitor" "bcc-tracer")
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

# Step 16: Cleanup — no gpu-metrics
echo "[DEBUG] Stopping and cleaning up containers..."
docker compose --env-file $env_file -f $docker_compose_file down --remove-orphans --volumes
docker rm -f hpe h264-streaming-server perf_monitor bcc-tracer 2>/dev/null || true

# Final timing
end_time=$(date +%s)
duration=$((end_time - start_time))
echo "Experiment completed in $duration seconds."
echo "Results saved in: $results_dir"

# Verify collected data
echo "[DEBUG] Collected data summary:"
tree -h "$results_dir" | head -20
