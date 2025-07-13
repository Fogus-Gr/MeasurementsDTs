#!/bin/bash
set -e

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
timestamp=$(date +%Y%m%d_%H%M%S)
cpu_model=$(lscpu | grep "Model name" | sed 's/.*: *//g' | sed 's/ with [0-9]\+ [Cc]ores//' | tr -s ' ' '_' | tr -d ',()/')
cpu_threads=$(lscpu | awk '/^CPU\(s\):/ {print $2; exit}')
cpu_model="${cpu_model}_${cpu_threads}"
start_time=$(date +%s)
container_type=${1:-hpe}
arguments=${2:-""}
results_dir="results_${container_type}_${cpu_model}_${timestamp}"
mkdir -p "$results_dir/logs" "$results_dir/traces/bcc" "$results_dir/perf"

# Step 5: Enhanced cleanup including BCC tracer outputs
echo "[DEBUG] Cleaning previous run artifacts..."
rm -f ./results/*.csv ./traces/*.csv ./perf_monitor/output/*.csv 2>/dev/null || true
rm -f ./csv/*.csv 2>/dev/null || true
rm -rf ./tracer_output/* 2>/dev/null || true

echo "Preparing results directory: $results_dir"

# Step 6: Compose file and container names
docker_compose_file="docker-compose.yaml"
HPE_SERVICE="hpe"
H264_CONTAINER_NAME="h264-streaming-server"

# Step 7: Stop and remove existing containers
echo "Stopping and removing existing containers..."
docker compose -f $docker_compose_file down -v --remove-orphans
docker rm -f hpe bcc-tracer 2>/dev/null || true

# Initialize timing file
touch "$results_dir/container_timing.txt"
echo "Container Instantiation Timing:" > "$results_dir/container_timing.txt"

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
export HPE_METHOD="$1"
export HPE_INPUT="http://h264-streaming-server:8089/stream.h264"
export HPE_DEVICE="CPU"
if [[ "$1" == "alphapose" || "$arguments" == *"--method alphapose"* ]]; then
  export HPE_DEVICE="GPU"
elif [[ "$1" == "hrnetet" || "$arguments" == *"--method hrnetet"* ]]; then
  export HPE_DEVICE="CPU"
elif [[ "$1" == "openpose" || "$arguments" == *"--method openpose"* ]]; then
  export HPE_DEVICE="CPU"
elif [[ "$arguments" == *"--device GPU"* ]]; then
  export HPE_DEVICE="GPU"
elif [[ "$arguments" == *"--device CPU"* ]]; then
  export HPE_DEVICE="CPU"
fi

# Step 11: Start HPE container
docker compose -f $docker_compose_file up -d hpe
hpe_start=$(date +%s.%N)
measure_container_startup "$HPE_SERVICE" "$hpe_start"

# Step 12: Start monitoring containers with BCC support
perf_monitor_start=$(date +%s.%N)
echo "[DEBUG] Starting monitoring containers..."
docker compose -f $docker_compose_file up -d perf_monitor
docker compose -f $docker_compose_file up -d gpu-metrics
docker compose -f $docker_compose_file up -d bcc-tracer

PERF_MONITOR_CONTAINER=$(docker ps -qf "name=perf_monitor")
GPU_METRICS_CONTAINER=$(docker ps -qf "name=gpu-metrics")
TRACE_CONTAINER=$(docker ps -qf "name=.*bcc-tracer.*")

measure_container_startup "perf_monitor" "$perf_monitor_start"
measure_container_startup "gpu-metrics" "$perf_monitor_start"

# Special handling for BCC tracer
bcc_start=$(date +%s.%N)
echo "[DEBUG] Waiting for BCC tracer to initialize..."
sleep 8  # Extra time for BCC compilation and port detection
measure_container_startup "bcc-tracer" "$bcc_start"

# Verify BCC tracer status
for i in {1..10}; do
  if docker logs $TRACE_CONTAINER 2>&1 | grep -q "Detected HPE video port"; then
    echo "[DEBUG] BCC tracer successfully initialized"
    detected_port=$(docker logs $TRACE_CONTAINER 2>&1 | grep "Detected HPE video port" | awk '{print $NF}')
    echo "BCC detected HPE video port: $detected_port" >> "$results_dir/container_timing.txt"
    break
  fi
  sleep 2
done

# Step 13: Collect initial logs
sleep 2  # Allow containers to stabilize
docker logs $(docker ps -qf "name=^/hpe$") > "$results_dir/logs/hpe_startup.log" 2>&1
docker logs $TRACE_CONTAINER > "$results_dir/logs/bcc_tracer_startup.log" 2>&1

# Step 14: Monitor experiment progress
HPE_MONITOR_START=$(date +%s)
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

# Step 15: Enhanced data collection
echo "[DEBUG] Collecting experiment results..."

# Performance data
if [ -n "$PERF_MONITOR_CONTAINER" ]; then
  docker cp "$PERF_MONITOR_CONTAINER:/output/aggregated_metrics.csv" "$results_dir/perf/performance_data.csv" 2>/dev/null || \
    echo "[WARNING] Failed to copy performance data"
fi

# GPU metrics
mkdir -p "$results_dir/gpu"
[ -f ./results/gpu_metrics.csv ] && cp ./results/gpu_metrics.csv "$results_dir/gpu/"

# BCC tracer outputs
if [ -n "$TRACE_CONTAINER" ]; then
  echo "[DEBUG] Collecting BCC tracer outputs..."
  docker cp "$TRACE_CONTAINER:/opt/tracer/output/hpe_video_rx.csv" "$results_dir/traces/bcc/video_rx.csv" 2>/dev/null || \
    echo "[WARNING] Failed to copy BCC trace data"
  
  docker cp "$TRACE_CONTAINER:/opt/tracer/output/logs" "$results_dir/traces/bcc/" 2>/dev/null || \
    echo "[WARNING] Failed to copy BCC logs"
  
  docker logs $TRACE_CONTAINER 2>&1 | grep "Detected HPE video port" > "$results_dir/traces/bcc/port_info.txt"
fi

# Container logs
container_list=("hpe" "perf_monitor" "bcc-tracer" "gpu-metrics")
for container in "${container_list[@]}"; do
  container_id=$(docker ps -aqf "name=^/${container}$")
  [ -n "$container_id" ] && docker logs $container_id > "$results_dir/logs/$container.log" 2>&1
done

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