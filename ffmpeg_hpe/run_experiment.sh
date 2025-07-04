#!/bin/bash
set -e

# Ensure bc is installed
if ! command -v bc &> /dev/null; then
  echo "Installing bc (required for timestamp alignment)..."
  apt-get update && apt-get install -y bc || yum install -y bc
fi

measure_container_startup() {
  local container_name=$1
  local start_time=$2
  
  # Try exact name first, then pattern match as fallback
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

# Add after measure_container_startup() function (around line 27)

capture_diagnostics() {
  echo "[DEBUG] ===== CAPTURING DIAGNOSTICS ====="
  echo "[DEBUG] NVIDIA GPU Status:"
  nvidia-smi || echo "nvidia-smi failed - no GPU or driver issue"
  
  echo "[DEBUG] Docker containers:"
  docker ps -a
  
  echo "[DEBUG] HPE container logs:"
  docker logs $(docker ps -a -qf "name=hpe" --last 1) 2>&1 || echo "No logs available"
  
  echo "[DEBUG] Video stream availability:"
  curl -I "$STREAM_URL" 2>&1 || echo "Stream not accessible"
  
  echo "[DEBUG] ===== END DIAGNOSTICS ====="
}

# Get current timestamp and CPU info for results directory
timestamp=$(date +%Y%m%d_%H%M%S)
cpu_model=$(lscpu | grep "Model name" | sed 's/.*: *//g' | tr -s ' ' '_' | tr -d ',()/')
start_time=$(date +%s)

# Container type from first argument (default to "hpe")
container_type=${1:-hpe}
arguments=${2:-""}

results_dir="results_${container_type}_${cpu_model}_${timestamp}"
mkdir -p "$results_dir"
mkdir -p "$results_dir/logs"
mkdir -p "$results_dir/traces"
mkdir -p "$results_dir/perf"

# Clean up old CSV files before starting a new experiment
echo "Cleaning up old CSV files..."
rm -f ./results/*.csv ./traces/*.csv ./perf_monitor/output/*.csv 2>/dev/null || true

echo "Preparing results directory: $results_dir"

COMPOSE_FILE="docker-compose.yaml"
HPE_SERVICE="hpe"
H264_CONTAINER_NAME="h264-streaming-server"  # Added this line to define the container name

# Stop and remove existing containers
echo "Stopping and removing existing containers..."
docker compose -f $COMPOSE_FILE down --remove-orphans

touch "$results_dir/container_timing.txt"
echo "Container Instantiation Timing:" > "$results_dir/container_timing.txt"

# Start h264-streaming-server with force-recreate
echo "Starting h264-streaming-server with force-recreate..."
docker compose -f $COMPOSE_FILE up -d --force-recreate h264-streaming-server

# Debug container health status
echo "[DEBUG] H264_CONTAINER_NAME=$H264_CONTAINER_NAME"
echo "[DEBUG] Health status: $(docker inspect --format='{{.State.Health.Status}}' h264-streaming-server 2>/dev/null)"

# Wait for healthcheck to pass - add timeout
wait_start=$(date +%s)
wait_timeout=60  # 60 seconds max to wait for streaming server
while [[ $(docker inspect --format='{{.State.Health.Status}}' $H264_CONTAINER_NAME 2>/dev/null) != "healthy" ]]; do
  echo "Waiting for h264-streaming-server to become healthy..."
  
  # Check if we've waited too long
  current=$(date +%s)
  if [ $((current - wait_start)) -gt $wait_timeout ]; then
    echo "[WARNING] Streaming server healthcheck timed out, continuing anyway..."
    break
  fi
  
  sleep 2
done

# Get streaming server IP directly
STREAM_SERVER_IP=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' $H264_CONTAINER_NAME)
STREAM_URL="http://${STREAM_SERVER_IP}:8089/stream.h264"
echo "[DEBUG] Using direct IP for stream: $STREAM_URL"

# Start hpe container with the detected URL as input
hpe_start=$(date +%s.%N)
echo "Building and starting hpe container with stream input..."

# Check if method is GPU-based (alphapose or openpose)
if [[ "$1" == "alphapose" || "$arguments" == *"--method alphapose"* || 
      "$1" == "openpose" || "$arguments" == *"--method openpose"* ]]; then
  echo "[DEBUG] Using GPU-accelerated method (alphapose or openpose)"
  # No GPU flags here - they're in docker-compose.yaml
  docker compose -f $COMPOSE_FILE run -d --name hpe --rm \
    hpe python3 main.py --method "$1" --input "$STREAM_URL" --save_image --device GPU
else
  echo "[DEBUG] Using CPU-based method (movenet)"
  docker compose -f $COMPOSE_FILE run -d --name hpe --rm \
    hpe python3 main.py --method movenet --input "$STREAM_URL"
fi

measure_container_startup "$HPE_SERVICE" "$hpe_start"

# Capture initial logs immediately after starting
echo "[DEBUG] Capturing initial HPE container logs..."
sleep 2  # Give container a moment to start logging
docker logs $(docker ps -qf "name=hpe") > "$results_dir/logs/hpe_startup.log" 2>&1
echo "[DEBUG] HPE startup logs:"
tail -n 20 "$results_dir/logs/hpe_startup.log"

# Capture more frequent logs to catch any error messages
docker logs $(docker ps -qf "name=hpe") | tee "$results_dir/logs/hpe_startup_full.log"

# Start and measure perf_monitor container
perf_monitor_start=$(date +%s.%N)
echo "[DEBUG] Starting performance monitoring..."
docker compose -f $COMPOSE_FILE up -d perf_monitor
docker compose -f $COMPOSE_FILE up -d trace_container
# Add GPU metrics monitoring
docker compose -f $COMPOSE_FILE up -d gpu-metrics
PERF_MONITOR_CONTAINER=$(docker ps -qf "name=perf_monitor")
TRACE_CONTAINER=$(docker ps -qf "name=.*trace_container.*")
GPU_METRICS_CONTAINER=$(docker ps -qf "name=gpu-metrics")
measure_container_startup "perf_monitor" "$perf_monitor_start"
measure_container_startup "trace_container" "$perf_monitor_start"
measure_container_startup "gpu-metrics" "$perf_monitor_start"

# Create pids directory if it doesn't exist
mkdir -p ./pids

# Get all PIDs inside the hpe container
echo "[DEBUG] Getting all PIDs inside the hpe container..."
HPE_CONTAINER=$(docker ps -qf "name=.*hpe.*")
if [ -n "$HPE_CONTAINER" ]; then
  for attempt in {1..3}; do
    echo "[DEBUG] PID collection attempt $attempt..."
    # Fixed command syntax - ensure 'ps -ef' is executed inside the container
    if docker exec $HPE_CONTAINER ps -ef > ./pids/hpe.pid 2>/dev/null; then
      echo "[DEBUG] Updated hpe.pid contents:"
      cat ./pids/hpe.pid
      break
    else
      echo "[WARNING] Attempt $attempt failed, waiting 2s before retry"
      sleep 2
    fi
  done
fi

# Replace the user input section with automatic HPE container monitoring
echo "Waiting for HPE container to complete processing..."
HPE_RUNNING=true
HPE_MONITOR_START=$(date +%s)
MAX_WAIT_TIME=307  # 5 minutes timeout

# Increase timeout for AlphaPose which takes longer to initialize
if [[ "$1" == "alphapose" ]]; then
  MAX_WAIT_TIME=600  # 10 minutes for AlphaPose
fi

while $HPE_RUNNING; do
  # Check if container exists
  if ! docker ps -q --filter name=hpe > /dev/null 2>&1; then
    echo "[DEBUG] HPE container no longer running, ending experiment..."
    capture_diagnostics  # <-- Add this line
    HPE_RUNNING=false
    break
  fi
  
  # Check container status
  CONTAINER_STATUS=$(docker inspect --format='{{.State.Status}}' $HPE_CONTAINER 2>/dev/null || echo "exited")
  echo "HPE container status: $CONTAINER_STATUS"
  
  if [[ "$CONTAINER_STATUS" != "running" ]]; then
    echo "[WARNING] HPE container has stopped with status: $CONTAINER_STATUS"
    capture_diagnostics  # <-- Add this line
    HPE_RUNNING=false
    break
  fi
  
  # Capture logs during monitoring (add before the sleep line)
  echo "[DEBUG] Current HPE logs (last 5 lines):"
  docker logs --tail 5 $HPE_CONTAINER 2>&1 || echo "[WARNING] Failed to get logs"
  
  echo "Container still running, waiting (5s)"
  sleep 5
  
  # Check timeout
  CURRENT_TIME=$(date +%s)
  ELAPSED_TIME=$((CURRENT_TIME - HPE_MONITOR_START))
  if [ $ELAPSED_TIME -gt $MAX_WAIT_TIME ]; then
    echo "[WARNING] Reached maximum wait time of ${MAX_WAIT_TIME}s, forcing experiment end"
    docker stop $HPE_CONTAINER >/dev/null 2>&1 || true
    HPE_RUNNING=false
  fi
done

echo "[DEBUG] Ending the experiment..."

# Collect performance data after experiment completion
if [ -n "$PERF_MONITOR_CONTAINER" ]; then
  if docker exec $PERF_MONITOR_CONTAINER ls -la /output/aggregated_metrics.csv 2>/dev/null; then
    echo "[DEBUG] Found aggregated_metrics.csv, copying performance monitoring data..."
    docker cp "$PERF_MONITOR_CONTAINER:/output/aggregated_metrics.csv" "$results_dir/perf/performance_data.csv"
    chmod -R u+rw "$results_dir"
    echo "Copied perf_monitor output to $results_dir/perf/performance_data.csv"
  else
    echo "[WARNING] Could not find aggregated_metrics.csv in perf_monitor container."
  fi
fi

# Copy trace files after experiment
if [ -n "$TRACE_CONTAINER" ]; then
  echo "[DEBUG] Copying network trace data from trace_container..."
  if docker exec $TRACE_CONTAINER ls -la /opt/tracer/output/trace.csv 2>/dev/null; then
    echo "[DEBUG] Found trace.csv, copying trace data..."
    docker cp "$TRACE_CONTAINER:/opt/tracer/output/trace.csv" "$results_dir/traces/trace.csv" && \
    echo "Copied trace file to $results_dir/traces/trace.csv" || \
    echo "[ERROR] Failed to copy trace file"
  else
    echo "[WARNING] Could not find trace.csv in trace_container."
  fi
fi

# Collect container logs before stopping
echo "[DEBUG] Collecting container logs..."
container_list=("hpe" "perf_monitor" "trace_container" "gpu-metrics")
for container in "${container_list[@]}"
do
  # More flexible pattern matching to find the container ID
  container_id=$(docker ps -qf "name=.*${container}.*")
  if [ -n "$container_id" ]; then
    echo "[DEBUG] Saving logs for $container container..."
    docker logs $container_id > "$results_dir/logs/$container.log" 2>&1
    echo "Saved logs for $container to $results_dir/logs/$container.log"
  else
    echo "[WARNING] Container $container not found, skipping log collection."
  fi
done

# Copy all CSVs produced by hpe service (in ./results) to the results_dir
if compgen -G "./results/*.csv" > /dev/null; then
  echo "[DEBUG] Copying hpe output CSVs from ./results to $results_dir ..."
  cp ./results/*.csv "$results_dir/"
  echo "Copied hpe output CSVs to $results_dir/"
else
  echo "[DEBUG] No hpe output CSVs found in ./results."
fi

# After collecting performance data
# Collect GPU metrics data
if [ -n "$GPU_METRICS_CONTAINER" ]; then
  if docker exec $GPU_METRICS_CONTAINER ls -la /output/gpu_metrics.csv 2>/dev/null; then
    echo "[DEBUG] Found gpu_metrics.csv, copying GPU monitoring data..."
    docker cp "$GPU_METRICS_CONTAINER:/output/gpu_metrics.csv" "$results_dir/perf/gpu_metrics.csv"
    chmod -R u+rw "$results_dir"
    echo "Copied GPU metrics to $results_dir/perf/gpu_metrics.csv"
  else
    echo "[WARNING] Could not find gpu_metrics.csv in gpu-metrics container."
  fi
fi

echo "[DEBUG] Stopping and cleaning up containers..."
docker compose -f $COMPOSE_FILE down

end_time=$(date +%s)
duration=$((end_time - start_time))
echo "Experiment completed in $duration seconds."
echo "Results are saved in the directory: $results_dir"
