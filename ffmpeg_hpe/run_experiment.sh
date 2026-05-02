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

# Step 3: Function to capture diagnostics for debugging
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
  echo "[DEBUG] Video stream availability:"
  curl --max-time 3 -I "$STREAM_URL" 2>&1 || echo "Stream not accessible"
  echo "[DEBUG] ===== END DIAGNOSTICS ====="
}

# Step 4: Prepare results directory and experiment metadata
# Get current timestamp and CPU info for results directory
# (This ensures results are organized and not overwritten)
timestamp=$(date +%Y%m%d_%H%M%S)
cpu_model=$(lscpu | grep "Model name" | sed 's/.*: *//g' | tr -s ' ' '_' | tr -d ',()/')
start_time=$(date +%s)
container_type=${1:-hpe}
arguments=${2:-""}
results_dir="results_${container_type}_${cpu_model}_${timestamp}"
mkdir -p "$results_dir/logs" "$results_dir/traces" "$results_dir/perf"

# Step 5: Clean up old CSV files before starting a new experiment
rm -f ./results/*.csv ./traces/*.csv ./perf_monitor/output/*.csv 2>/dev/null || true
rm -f ./csv/*.csv 2>/dev/null || true

echo "Preparing results directory: $results_dir"

# Step 6: Compose file and container names
docker_compose_file="docker-compose.yaml"
HPE_SERVICE="hpe"
H264_CONTAINER_NAME="h264-streaming-server"

# Step 7: Stop and remove any existing containers from previous runs
echo "Stopping and removing existing containers..."
docker compose -f $docker_compose_file down -v --remove-orphans
# Remove hpe container by name in case it lingers
docker rm -f hpe 2>/dev/null || true

touch "$results_dir/container_timing.txt"
echo "Container Instantiation Timing:" > "$results_dir/container_timing.txt"

# Step 8: Start the streaming server and wait for it to become healthy
echo "Starting h264-streaming-server with force-recreate..."
docker compose -f $docker_compose_file up -d h264-streaming-server
#docker compose -f $docker_compose_file up -d --force-recreate h264-streaming-server


# Wait for healthcheck to pass (max 60s)
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

# Step 9: Get streaming server IP and construct stream URL
STREAM_SERVER_IP=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' $H264_CONTAINER_NAME)
STREAM_URL="http://${STREAM_SERVER_IP}:8089/stream.h264"
echo "[DEBUG] Using direct IP for stream: $STREAM_URL"

# Step 10: Set environment variables for hpe service (method, input, device)
export HPE_METHOD="$1"
export HPE_INPUT="$STREAM_URL"
export HPE_DEVICE="CPU"
if [[ "$1" == "alphapose" || "$arguments" == *"--method alphapose"* || \
      "$1" == "openpose" || "$arguments" == *"--method openpose"* ]]; then
  export HPE_DEVICE="GPU"
fi

# Step 11: Start hpe container with Compose
docker compose -f $docker_compose_file up -d hpe

# Step 12: Measure hpe container startup time
hpe_start=$(date +%s.%N)
measure_container_startup "$HPE_SERVICE" "$hpe_start"

# Step 13: Capture initial logs from hpe container
sleep 2  # Give container a moment to start logging
docker logs $(docker ps -qf "name=^/hpe$") > "$results_dir/logs/hpe_startup.log" 2>&1
tail -n 20 "$results_dir/logs/hpe_startup.log"
docker logs $(docker ps -qf "name=^/hpe$") | tee "$results_dir/logs/hpe_startup_full.log"

# Step 14: Start and measure monitoring containers (perf_monitor, bcc-tracer, gpu-metrics)
perf_monitor_start=$(date +%s.%N)
echo "[DEBUG] Starting performance monitoring..."
docker compose -f $docker_compose_file up -d perf_monitor
docker compose -f $docker_compose_file up -d bcc-tracer
docker compose -f $docker_compose_file up -d gpu-metrics
PERF_MONITOR_CONTAINER=$(docker ps -qf "name=perf_monitor")
TRACE_CONTAINER=$(docker ps -qf "name=bcc-tracer")
GPU_METRICS_CONTAINER=$(docker ps -qf "name=gpu-metrics")
measure_container_startup "perf_monitor" "$perf_monitor_start"
measure_container_startup "bcc-tracer" "$perf_monitor_start"
measure_container_startup "gpu-metrics" "$perf_monitor_start"

# Step 15: Get all PIDs inside the hpe container (for monitoring)
mkdir -p ./pids
HPE_CONTAINER=$(docker ps -qf "name=^/hpe$")
if [ -n "$HPE_CONTAINER" ]; then
  for attempt in {1..3}; do
    if docker exec $HPE_CONTAINER ps -ef > ./pids/hpe.pid 2>/dev/null; then
      cat ./pids/hpe.pid
      break
    else
      sleep 2
    fi
  done
fi

# Step 16: Monitor hpe container until it exits (no timeout)
# The loop checks every 5s if the hpe container is still running
HPE_MONITOR_START=$(date +%s)
while true; do
  HPE_CONTAINER=$(docker ps -q --filter "name=^/hpe$")
  if [ -z "$HPE_CONTAINER" ]; then
    echo "[DEBUG] HPE container no longer running, ending experiment..."
    capture_diagnostics
    break
  fi
  CONTAINER_STATUS=$(docker inspect --format='{{.State.Status}}' $HPE_CONTAINER 2>/dev/null || echo "exited")
  echo "HPE container status: $CONTAINER_STATUS"
  if [[ "$CONTAINER_STATUS" != "running" ]]; then
    echo "[WARNING] HPE container has stopped with status: $CONTAINER_STATUS"
    capture_diagnostics
    break
  fi
  echo "[DEBUG] Current HPE logs (last 5 lines):"
  docker logs --tail 5 $HPE_CONTAINER 2>&1 || echo "[WARNING] Failed to get logs"
  sleep 5
done

echo "[DEBUG] Ending the experiment..."

# Step 17: Wait for the hpe container name to be fully released (avoid name conflicts)
for i in {1..10}; do
  if docker ps -a --format '{{.Names}}' | grep -wq hpe; then
    echo "[DEBUG] Waiting for hpe container name to be released..."
    sleep 1
  else
    break
  fi
done

# Step 18: Collect performance data after experiment completion
if [ -n "$PERF_MONITOR_CONTAINER" ]; then
  if docker exec $PERF_MONITOR_CONTAINER ls -la /output/aggregated_metrics.csv 2>/dev/null; then
    docker cp "$PERF_MONITOR_CONTAINER:/output/aggregated_metrics.csv" "$results_dir/perf/performance_data.csv"
    chmod -R u+rw "$results_dir"
    echo "Copied perf_monitor output to $results_dir/perf/performance_data.csv"
  else
    echo "[WARNING] Could not find aggregated_metrics.csv in perf_monitor container."
  fi
fi

# Step 19: Copy trace files after experiment
if [ -n "$TRACE_CONTAINER" ]; then
  if docker exec $TRACE_CONTAINER ls -la /opt/tracer/output/trace.csv 2>/dev/null; then
    docker cp "$TRACE_CONTAINER:/opt/tracer/output/trace.csv" "$results_dir/traces/trace.csv" && \
    echo "Copied trace file to $results_dir/traces/trace.csv" || \
    echo "[ERROR] Failed to copy trace file"
  else
    echo "[WARNING] Could not find trace.csv in bcc-tracer."
  fi
fi

# Step 20: Collect container logs before stopping
container_list=("hpe" "perf_monitor" "bcc-tracer" "gpu-metrics")
for container in "${container_list[@]}"
do
  container_id=$(docker ps -aqf "name=^/${container}$")
  if [ -n "$container_id" ]; then
    docker logs $container_id > "$results_dir/logs/$container.log" 2>&1
    echo "Saved logs for $container to $results_dir/logs/$container.log"
  else
    echo "[WARNING] Container $container not found, skipping log collection."
  fi
done

# Step 21: List files inside HPE container before cleanup (if it exists)
HPE_CONTAINER_ID=$(docker ps -aqf "name=^/hpe$")
if [ -n "$HPE_CONTAINER_ID" ]; then
  echo "[DEBUG] Listing files inside HPE container before cleanup:"
  docker exec $HPE_CONTAINER_ID ls -lh /output || echo "Could not list /output in HPE container"
fi

# Step 22: Copy GPU metrics to results_dir/gpu/gpu_metrics.csv
mkdir -p "$results_dir/gpu"
if [ -f ./results/gpu_metrics.csv ]; then
  cp ./results/gpu_metrics.csv "$results_dir/gpu/gpu_metrics.csv"
  echo "Copied GPU metrics to $results_dir/gpu/gpu_metrics.csv"
else
  echo "[WARNING] gpu_metrics.csv not found in ./results"
fi

# if compgen -G "./csv/*.csv" > /dev/null; then
#   cp ./csv/*.csv "$results_dir/"
#   echo "Copied hpe output CSVs to $results_dir/"
# else
#   echo "[DEBUG] No hpe output CSVs found in ./csv."
# fi

# Now stop and clean up containers and resources
echo "[DEBUG] Stopping and cleaning up containers..."
docker compose -f $docker_compose_file down --remove-orphans --volumes
docker rm -f hpe h264-streaming-server gpu-metrics perf_monitor bcc-tracer 2>/dev/null || true

end_time=$(date +%s)
duration=$((end_time - start_time))
echo "Experiment completed in $duration seconds."
echo "Results are saved in the directory: $results_dir"
