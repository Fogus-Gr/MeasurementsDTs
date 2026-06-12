#!/bin/bash
set -e

# bc is required for timestamp/startup timing. Install it on the host first.
if ! command -v bc &> /dev/null; then
    echo "[ERROR] Missing required host command: bc" >&2
    echo "Install bc before running this experiment." >&2
    exit 1
fi

# Define the measure_container_startup function FIRST
measure_container_startup() {
  local container_name=$1
  local start_time=$2
  local container_id=$(docker ps -qf "name=dash-caching-$container_name")
  
  if [ -n "$container_id" ]; then
    # Get container creation time from Docker
    local created_at=$(docker inspect --format='{{.Created}}' $container_id)
    local started_at=$(docker inspect --format='{{.State.StartedAt}}' $container_id)
    
    # Calculate time to instantiate (in seconds)
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

# Container type from first argument (default to "dash")
container_type=${1:-dash}
arguments=${2:-""}  # Optional second argument
experiment_duration_seconds=${EXPERIMENT_DURATION_SECONDS:-500}

# Create a uniquely named results directory
results_dir="results_${container_type}_${cpu_model}_${timestamp}"
mkdir -p "$results_dir"
mkdir -p "$results_dir/logs"
mkdir -p "$results_dir/traces"
mkdir -p "$results_dir/perf"

echo "[DEBUG] Working directory: $(pwd)"
# echo "[DEBUG] Files in current directory:"
# ls -la

# Clean up old CSV files before starting a new experiment
echo "Cleaning up old CSV files..."
rm -f ./results/*.csv ./traces/*.csv ./perf_monitor/output/*.csv 2>/dev/null || true

echo "Preparing results directory: $results_dir"

# Compose file name
COMPOSE_FILE="docker-compose.yml"
PROXY_SERVICE="http_proxy"

# Stop and remove existing containers
echo "Stopping and removing existing containers..."
docker compose -f $COMPOSE_FILE down --remove-orphans

# Create a file to store timing information
touch "$results_dir/container_timing.txt"
echo "Container Instantiation Timing:" > "$results_dir/container_timing.txt"

# Start main containers with timing
main_containers_start=$(date +%s.%N)
echo "Building and starting fresh containers..."
echo "[DEBUG] Starting all services except trace_container..."
docker compose -f $COMPOSE_FILE up http_server http_proxy http_client -d
echo "[DEBUG] Sleeping 2 seconds to allow containers to start..."
sleep 4

# Measure main container startup times
measure_container_startup "http_server" "$main_containers_start"
measure_container_startup "http_proxy" "$main_containers_start" 
measure_container_startup "http_client" "$main_containers_start"

# # Get proxy PIDs
# echo "[DEBUG] Getting proxy PIDs inside the container..."
# PROXY_PIDS=$(docker exec $PROXY_CONTAINER pgrep -f "proxy")
# echo "[DEBUG] PROXY_PIds detected: $PROXY_PIDS"


# Early in the script - detect and update PIDs immediately
echo "[DEBUG] Getting proxy container ID..."
PROXY_CONTAINER=$(docker ps -qf "name=dash-caching-http_proxy")
echo "[DEBUG] Proxy container ID: $PROXY_CONTAINER"

# Get all PIDs inside the proxy container
echo "[DEBUG] Getting all PIDs inside the proxy container..."
PROXY_PIDS=$(docker top $PROXY_CONTAINER -eo pid | awk 'NR>1 {print $1}')
echo "[DEBUG] All PIDs detected: $PROXY_PIDS"

SERVER_CONTAINER=$(docker ps -qf "name=dash-caching-http_server")
CLIENT_CONTAINER=$(docker ps -qf "name=dash-caching-http_client")
DASH_SERVER_IP=$(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$SERVER_CONTAINER")
DASH_PROXY_IP=$(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$PROXY_CONTAINER")
DASH_CLIENT_IP=$(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$CLIENT_CONTAINER")
if [ -z "$DASH_SERVER_IP" ] || [ -z "$DASH_PROXY_IP" ] || [ -z "$DASH_CLIENT_IP" ]; then
  echo "[ERROR] Could not resolve DASH container IPs for video-byte tracing." >&2
  exit 1
fi
export DASH_SERVER_IP DASH_PROXY_IP DASH_CLIENT_IP
echo "[DEBUG] DASH trace endpoints: server=$DASH_SERVER_IP proxy=$DASH_PROXY_IP client=$DASH_CLIENT_IP"

# IMPORTANT: Update dash.pid IMMEDIATELY after detection
mkdir -p ./pids
echo "$PROXY_PIDS" | grep -v "^1$" | sort -u > ./pids/dash.pid
echo "[DEBUG] Updated dash.pid contents:"
cat ./pids/dash.pid

# Build perf_monitor image before starting it
echo "[DEBUG] Building perf_monitor image..."
docker compose -f $COMPOSE_FILE build perf_monitor

# Start and measure the performance monitoring container
perf_monitor_start=$(date +%s.%N)
echo "[DEBUG] Starting performance monitoring..."
docker compose -f $COMPOSE_FILE up -d perf_monitor
PERF_MONITOR_CONTAINER=$(docker ps -qf "name=dash-caching-perf_monitor")
echo "[DEBUG] perf_monitor container ID: $PERF_MONITOR_CONTAINER"
measure_container_startup "perf_monitor" "$perf_monitor_start"

# Start and measure the trace container
trace_container_start=$(date +%s.%N)
echo "[DEBUG] Starting trace_container..."
docker compose -f $COMPOSE_FILE up -d trace_container
TRACE_CONTAINER=$(docker ps -qf "name=dash-caching-trace_container")
echo "[DEBUG] trace_container container ID: $TRACE_CONTAINER"
measure_container_startup "trace_container" "$trace_container_start"

# Get the port for the DASH client
CLIENT_PORT=$(docker port $CLIENT_CONTAINER 80 | cut -d ":" -f 2)
echo "[DEBUG] DASH client mapped port: $CLIENT_PORT"

# Print URL for DASH client
echo "DASH URL: http://localhost:$CLIENT_PORT/manifest.mpd"

# Run the experiment for a fixed duration so unattended runs are reproducible.
echo "Running experiment for ${experiment_duration_seconds} seconds..."
sleep "$experiment_duration_seconds"
echo "[DEBUG] Ending the experiment..."

# NOW collect the performance data AFTER the experiment has run
echo "[DEBUG] Collecting performance data after experiment completion..."
if [ -n "$PERF_MONITOR_CONTAINER" ]; then
  if docker exec $PERF_MONITOR_CONTAINER ls -la /output/perf_metrics.csv 2>/dev/null; then
    echo "[DEBUG] Found perf_metrics.csv, copying performance monitoring data..."
    docker cp "$PERF_MONITOR_CONTAINER:/output/perf_metrics.csv" "$results_dir/perf/perf_metrics.csv"
    chmod -R u+rw "$results_dir"
    echo "Copied perf_monitor output to $results_dir/perf/perf_metrics.csv"
  else
    echo "[WARNING] Could not find perf_metrics.csv in perf_monitor container."
  fi
fi

# Copy trace files AFTER experiment
if [ -n "$TRACE_CONTAINER" ]; then
  echo "[DEBUG] Copying network trace data from trace_container..."
  docker cp "$TRACE_CONTAINER:/opt/tracer/output/trace.csv" "$results_dir/traces/trace.csv"
  echo "Copied trace file to $results_dir/traces/trace.csv"
fi

# Collect container logs before stopping
echo "[DEBUG] Collecting container logs..."
containers=("http_server" "http_proxy" "http_client" "perf_monitor" "trace_container")
for container in "${containers[@]}"; do
  container_id=$(docker ps -qf "name=dash-caching-$container")
  if [ -n "$container_id" ]; then
    echo "[DEBUG] Saving logs for $container container..."
    docker logs $container_id > "$results_dir/logs/$container.log" 2>&1
    echo "Saved logs for $container to $results_dir/logs/$container.log"
  else
    echo "[WARNING] Container $container not found, skipping log collection."
  fi
done

# Stop and clean up
echo "[DEBUG] Stopping and cleaning up containers..."
docker compose -f $COMPOSE_FILE down

# Calculate and display script duration
end_time=$(date +%s)
duration=$((end_time - start_time))
echo "Experiment completed in $duration seconds."

# Print final message with results directory
echo "Results are saved in the directory: $results_dir"

# === Add summary block here ===
RESULTS_TXT="$results_dir/results.txt"
HTTP_SERVER_LOG="$results_dir/logs/http_server.log"
DOCKER_COMPOSE_FILE="docker-compose.yml"

# 1. Extract DASH video resolutions
RESOLUTIONS=$(grep -oP '/video_\\K[0-9]+(?=_)' "$HTTP_SERVER_LOG" | sort -u | tr '\n' ' ')
if [ -z "$RESOLUTIONS" ]; then
  RESOLUTIONS="Not found"
fi

# 2. Extract SERVICE_ADDITIONAL_PARAMETERS for http_proxy
PROXY_PARAMS=$(awk '/http_proxy:/,/- [A-Za-z_]+:/{if ($0 ~ /SERVICE_ADDITIONAL_PARAMETERS/) print $0}' "$DOCKER_COMPOSE_FILE" | head -1 | sed 's/.*SERVICE_ADDITIONAL_PARAMETERS=//')
if [ -z "$PROXY_PARAMS" ]; then
  PROXY_PARAMS="Not found"
fi

# 3. Get machine characteristics
CPU_MODEL=$(lscpu | grep "Model name" | sed 's/.*: *//g')
CPU_CORES=$(lscpu | grep "^CPU(s):" | awk '{print $2}')
MEM_TOTAL=$(free -h | awk '/^Mem:/ {print $2}')

# 4. Write to results.txt
{
  echo "==== Experiment Summary ===="
  echo "http_proxy SERVICE_ADDITIONAL_PARAMETERS: $PROXY_PARAMS"
  echo "Machine CPU Model: $CPU_MODEL"
  echo "Machine CPU Cores: $CPU_CORES"
  echo "Machine Total Memory: $MEM_TOTAL"
  echo "Experiment Directory: $results_dir"
  echo "Experiment Timestamp: $(date)"
  
  # Add container timing information
  echo ""
  echo "==== Container Instantiation Timing ===="
  if [ -f "$results_dir/container_timing.txt" ]; then
    # Skip the first line which is just the header
    tail -n +2 "$results_dir/container_timing.txt"
  else
    echo "No container timing information available"
  fi
} > "$RESULTS_TXT"

echo "Wrote summary to $RESULTS_TXT"

# echo "Aligning timestamps in CSV files..."

# # Define paths
# TRACES_FILE="$results_dir/traces/trace_${MAIN_PROXY_PID}.csv"
# METRICS_FILE="$results_dir/perf/perf_metrics.csv"
# ALIGNED_DIR="$results_dir/aligned"

# # Create aligned directory
# mkdir -p "$ALIGNED_DIR"

# # Check if both files exist
# if [ -f "$TRACES_FILE" ] && [ -f "$METRICS_FILE" ]; then
#     # Get first timestamp from each file (skip header line)
#     TRACE_FIRST_TS=$(awk -F, 'NR==2 {print $1; exit}' "$TRACES_FILE")
#     METRIC_FIRST_TS=$(awk -F, 'NR==2 {print $1; exit}' "$METRICS_FILE")
    
#     if [ -n "$TRACE_FIRST_TS" ] && [ -n "$METRIC_FIRST_TS" ]; then
#         # Calculate offset (requires bc)
#         TS_OFFSET=$(echo "$METRIC_FIRST_TS - $TRACE_FIRST_TS" | bc)
#         echo "Timestamp offset between files: $TS_OFFSET ms"
        
#         # Create version with relative time (seconds since start of first file)
#         awk -F, -v first_ts="$TRACE_FIRST_TS" 'BEGIN {OFS=","} 
#             NR==1 {print "seconds_elapsed", substr($0, index($0,",")+1); next} 
#             {printf "%.3f,%s\n", ($1-first_ts)/1000, substr($0, index($0,",")+1)}' \
#             "$TRACES_FILE" > "$ALIGNED_DIR/traces_relative.csv"
            
#         awk -F, -v first_ts="$TRACE_FIRST_TS" 'BEGIN {OFS=","} 
#             NR==1 {print "seconds_elapsed", substr($0, index($0,",")+1); next} 
#             {printf "%.3f,%s\n", ($1-first_ts)/1000, substr($0, index($0,",")+1)}' \
#             "$METRICS_FILE" > "$ALIGNED_DIR/metrics_relative.csv"
            
#         echo "Created aligned files with relative timestamps in $ALIGNED_DIR"
#     else
#         echo "Could not extract timestamps from data files."
#     fi
# else
#     echo "Missing trace or metrics files for timestamp alignment."
# fi

# echo "Experiment finished."
