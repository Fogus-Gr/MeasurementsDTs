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
  local container_id=$(docker ps -qf "name=${container_name}")
  if [ -n "$container_id" ]; then
    local created_at=$(docker inspect --format='{{.Created}}' $container_id)
    local started_at=$(docker inspect --format='{{.State.StartedAt}}' $container_id)
    local current_time=$(date +%s.%N)
    local time_diff=$(echo "$current_time - $start_time" | bc)
    echo "Container $container_name instantiation time: $time_diff seconds" >> "$results_dir/container_timing.txt"
    echo "[DEBUG] $container_name took $time_diff seconds to instantiate"
  else
    echo "[WARNING] Could not find container $container_name to measure startup time"
  fi
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

# Wait for healthcheck to pass
while [[ $(docker inspect --format='{{.State.Health.Status}}' $H264_CONTAINER_NAME 2>/dev/null) != "healthy" ]]; do
  echo "Waiting for h264-streaming-server to become healthy..."
  sleep 2
done

# Extract the stream URL from logs and replace localhost with container name
STREAM_URL=$(docker logs $H264_CONTAINER_NAME 2>&1 | grep "Test with VLC:" | tail -1 | awk -F': ' '{print $2}' | sed 's/localhost/h264-streaming-server/')
echo "[DEBUG] Original stream URL: $(docker logs $H264_CONTAINER_NAME 2>&1 | grep "Test with VLC:" | tail -1 | awk -F': ' '{print $2}')"
echo "[DEBUG] Modified stream URL: $STREAM_URL"

# Start hpe container with the detected URL as input
hpe_start=$(date +%s.%N)
echo "Building and starting hpe container with stream input..."
docker compose -f $COMPOSE_FILE run -d --name hpe --rm hpe python3 main.py --method movenet --input "$STREAM_URL"
measure_container_startup "$HPE_SERVICE" "$hpe_start"

# Start and measure perf_monitor container
perf_monitor_start=$(date +%s.%N)
echo "[DEBUG] Starting performance monitoring..."
docker compose -f $COMPOSE_FILE up -d perf_monitor
docker compose -f $COMPOSE_FILE up -d trace_container
PERF_MONITOR_CONTAINER=$(docker ps -qf "name=perf_monitor")
TRACE_CONTAINER=$(docker ps -qf "name=.*trace_container.*")
measure_container_startup "perf_monitor" "$perf_monitor_start"
measure_container_startup "trace_container" "$perf_monitor_start"

# Create pids directory if it doesn't exist
mkdir -p ./pids

# Get all PIDs inside the hpe container
echo "[DEBUG] Getting all PIDs inside the hpe container..."
HPE_CONTAINER=$(docker ps -qf "name=.*hpe.*")
if [ -n "$HPE_CONTAINER" ]; then
  # Ensure proper command format for docker exec
  HPE_PIDS=$(docker exec $HPE_CONTAINER sh -c "ps aux | awk '{print \$2}' | grep -v PID")
  if [ $? -eq 0 ]; then
    echo "$HPE_PIDS" | sort -u > ./pids/hpe.pid
    echo "[DEBUG] Updated hpe.pid contents:"
    cat ./pids/hpe.pid
  else
    echo "[WARNING] Failed to get PIDs from container"
    touch ./pids/hpe.pid  # Create empty file so perf_monitor doesn't fail
  fi
else
  echo "[WARNING] HPE container not found, skipping PID collection."
  touch ./pids/hpe.pid  # Create empty file so perf_monitor doesn't fail
fi

# Replace the user input section with automatic HPE container monitoring
echo "Waiting for HPE container to complete processing..."
HPE_RUNNING=true
HPE_MONITOR_START=$(date +%s)
MAX_WAIT_TIME=300  # 5 minutes timeout

while $HPE_RUNNING; do
  # More reliable container detection
  if ! docker ps | grep -q "hpe"; then
    echo "[DEBUG] HPE container has exited, ending experiment..."
    HPE_RUNNING=false
  else
    echo "HPE container still running... waiting (5s)"
    sleep 5
    
    # Add timeout safety
    CURRENT_TIME=$(date +%s)
    ELAPSED_TIME=$((CURRENT_TIME - HPE_MONITOR_START))
    if [ $ELAPSED_TIME -gt $MAX_WAIT_TIME ]; then
      echo "[WARNING] Reached maximum wait time of ${MAX_WAIT_TIME}s, forcing experiment end"
      HPE_RUNNING=false
    fi
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
container_list=("hpe" "perf_monitor" "trace_container")
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

echo "[DEBUG] Stopping and cleaning up containers..."
docker compose -f $COMPOSE_FILE down

end_time=$(date +%s)
duration=$((end_time - start_time))
echo "Experiment completed in $duration seconds."
echo "Results are saved in the directory: $results_dir"
