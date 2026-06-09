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
  echo "[DEBUG] RTSP broker availability (host-side, MediaMTX publishes 8554):"
  # NOTE: probe localhost from the host. `rtsp-broker` is a docker-bridge DNS
  # name and is only resolvable from inside containers on streaming-network.
  if command -v nc >/dev/null 2>&1; then
    nc -z localhost 8554 2>&1 && echo "RTSP port 8554 reachable on localhost" || echo "RTSP port 8554 not reachable on localhost"
  else
    (echo > /dev/tcp/127.0.0.1/8554) 2>/dev/null \
      && echo "RTSP port 8554 reachable on localhost (bash /dev/tcp)" \
      || echo "RTSP port 8554 not reachable on localhost"
  fi
  echo "[DEBUG] ===== END DIAGNOSTICS ====="
}

# Step 4: Prepare results directory and experiment metadata
timestamp=$(date +%Y%m%d_%H%M%S)
cpu_model=$(lscpu | grep "Model name" | sed 's/.*: *//g' | tr -s ' ' '_' | tr -d ',()/')
start_time=$(date +%s)
container_type=${1:-movenet}
arguments=${2:-""}
results_dir="results_${container_type}_${cpu_model}_${timestamp}"
mkdir -p "$results_dir/logs" "$results_dir/traces" "$results_dir/perf"

# Step 4b: Auto-detect available vCPUs and compute dynamic resource allocation.
# Sidecars (streamer 0.75, perf_monitor 0.25, bcc-tracer 0.5, gpu-metrics 0.1)
# consume ~1.6 CPUs at peak; we reserve 2 to give headroom and keep HPE
# measurements uncontaminated by scheduler contention.
TOTAL_VCPUS=$(nproc)
echo "[INFO] Detected $TOTAL_VCPUS vCPUs on this system"

if [ "$TOTAL_VCPUS" -lt 4 ]; then
  echo "[ERROR] This experiment requires at least 4 vCPUs. Found: $TOTAL_VCPUS"
  exit 1
fi

SIDECAR_VCPUS=2
HPE_VCPUS=$((TOTAL_VCPUS - SIDECAR_VCPUS))
if [ "$HPE_VCPUS" -lt 2 ]; then
  HPE_VCPUS=2
fi

# Per-method resource tuning — resolved here so docker-compose picks up the
# exported vars when the hpe service is started in Step 10.
# HPE_METHOD is parsed in Step 9; we default to the CLI arg now so the case
# block can run before any containers start.
_METHOD_PREVIEW="${1:-alphapose}"
case "$_METHOD_PREVIEW" in
  alphapose|openpose)
    # GPU methods: PyTorch/CUDA does the heavy lifting; cap OV_THREADS at 4
    # (used only for pre/post-processing on CPU).
    export OV_THREADS=$(( HPE_VCPUS < 4 ? HPE_VCPUS : 4 ))
    export HPE_CPU_LIMIT="${HPE_VCPUS}.0"
    export HPE_CPU_RESERVATION=$(awk "BEGIN {printf \"%.1f\", $HPE_VCPUS * 0.5}")
    export HPE_MEMORY_LIMIT="8G"
    export HPE_MEMORY_RESERVATION="6G"
    ;;
  movenet|ae1|ae2|ae3)
    # Lightweight OpenVINO models: scale threads with available vCPUs.
    # Memory: 1 GB per vCPU, minimum 4 GB.
    export OV_THREADS=$HPE_VCPUS
    export HPE_CPU_LIMIT="${HPE_VCPUS}.0"
    export HPE_CPU_RESERVATION=$(awk "BEGIN {printf \"%.1f\", $HPE_VCPUS * 0.67}")
    MEM_GB=$(( HPE_VCPUS > 4 ? HPE_VCPUS : 4 ))
    export HPE_MEMORY_LIMIT="${MEM_GB}G"
    export HPE_MEMORY_RESERVATION=$(awk "BEGIN {printf \"%.0f\", $MEM_GB * 0.67}")G
    ;;
  hrnet)
    # HigherHRNet: heavier model, needs more memory.
    # Memory: 1.5 GB per vCPU, minimum 6 GB.
    export OV_THREADS=$HPE_VCPUS
    export HPE_CPU_LIMIT="${HPE_VCPUS}.0"
    export HPE_CPU_RESERVATION=$(awk "BEGIN {printf \"%.1f\", $HPE_VCPUS * 0.67}")
    MEM_GB=$(awk "BEGIN {printf \"%.0f\", $HPE_VCPUS * 1.5}")
    MEM_GB=$(( MEM_GB > 6 ? MEM_GB : 6 ))
    export HPE_MEMORY_LIMIT="${MEM_GB}G"
    export HPE_MEMORY_RESERVATION=$(awk "BEGIN {printf \"%.0f\", $MEM_GB * 0.75}")G
    ;;
  *)
    echo "[WARNING] Unknown method '$_METHOD_PREVIEW', using default resource settings"
    export OV_THREADS=$HPE_VCPUS
    export HPE_CPU_LIMIT="${HPE_VCPUS}.0"
    export HPE_CPU_RESERVATION=$(awk "BEGIN {printf \"%.1f\", $HPE_VCPUS * 0.67}")
    MEM_GB=$(( HPE_VCPUS > 4 ? HPE_VCPUS : 4 ))
    export HPE_MEMORY_LIMIT="${MEM_GB}G"
    export HPE_MEMORY_RESERVATION=$(awk "BEGIN {printf \"%.0f\", $MEM_GB * 0.67}")G
    ;;
esac

export OV_MODE="latency"
export OV_CPU_PINNING="true"
export OV_HYPER_THREADING="false"

echo "[INFO] System Configuration:"
echo "  Total vCPUs:    $TOTAL_VCPUS"
echo "  HPE vCPUs:      $HPE_VCPUS  (sidecars reserved: $SIDECAR_VCPUS)"
echo "[INFO] HPE Resource Allocation:"
echo "  CPU limit:      $HPE_CPU_LIMIT  (reserved: $HPE_CPU_RESERVATION)"
echo "  Memory limit:   $HPE_MEMORY_LIMIT  (reserved: $HPE_MEMORY_RESERVATION)"
echo "  OV_THREADS:     $OV_THREADS"
echo ""

# Step 5: Clean up old CSV files and tracer output before starting a new experiment
rm -f ./results/*.csv ./traces/*.csv ./perf_monitor/output/*.csv 2>/dev/null || true
rm -f ./csv/*.csv 2>/dev/null || true
# Clean up previous BCC tracer output so stale data from prior runs is never
# mixed with the current run's results.
rm -rf ./tracer_output 2>/dev/null || true
# Pre-create the tracer_output directory so the Docker volume mount succeeds.
# If the directory doesn't exist when `docker compose up` runs, Docker creates
# it as root and the bcc-tracer container cannot write into it.
mkdir -p ./tracer_output

echo "Preparing results directory: $results_dir"

# Step 6: Compose file and container names
docker_compose_file="docker-compose.yaml"
HPE_SERVICE="hpe"
# Container names (mediamtx = RTSP broker; video-producer = FFmpeg NVENC streamer)
# are set via container_name: in docker-compose.yaml.

# Step 7: Stop and remove any existing containers from previous runs
echo "Stopping and removing existing containers..."
docker compose -f $docker_compose_file down -v --remove-orphans
docker rm -f hpe 2>/dev/null || true

touch "$results_dir/container_timing.txt"
echo "Container Instantiation Timing:" > "$results_dir/container_timing.txt"

# Step 8: Start the RTSP broker and wait for the RTSP port to accept connections.
# We do NOT use docker healthchecks here — MediaMTX is a distroless image with no
# shell, so any CMD-SHELL probe fails forever. Instead, probe the published TCP
# port 8554 from the host. This works because the rtsp-broker service publishes
# 8554:8554, and Docker only opens the host port once the container is running.
echo "Starting rtsp-broker (MediaMTX)..."
docker compose -f $docker_compose_file up -d rtsp-broker

probe_rtsp_port() {
  if command -v nc >/dev/null 2>&1; then
    nc -z localhost 8554 >/dev/null 2>&1
  else
    (echo > /dev/tcp/127.0.0.1/8554) >/dev/null 2>&1
  fi
}

wait_start=$(date +%s)
wait_timeout=60
until probe_rtsp_port; do
  echo "Waiting for rtsp-broker (MediaMTX) RTSP port 8554..."
  current=$(date +%s)
  if [ $((current - wait_start)) -gt $wait_timeout ]; then
    echo "[WARNING] RTSP broker readiness timed out after ${wait_timeout}s, continuing anyway..."
    break
  fi
  sleep 2
done
echo "[DEBUG] rtsp-broker accepting connections on localhost:8554"

# Step 9: Resolve HPE method, device, and GPU runtime before starting any containers.
# The rtsp-broker service name resolves via Docker bridge DNS.
export HPE_METHOD="${1:-alphapose}"
export HPE_INPUT="rtsp://rtsp-broker:8554/stream"
export HPE_DEVICE="CPU"

# GPU runtime: only alphapose and openpose actually use the GPU.
# For all other methods (movenet, ae1, ae2, ae3, hrnet) we set
# NVIDIA_VISIBLE_DEVICES=none so the NVIDIA container runtime is not required
# and the container can start on hosts without a GPU driver.
GPU_METHODS=("alphapose" "openpose")
HPE_RUNTIME="runc"
if [[ " ${GPU_METHODS[*]} " == *" $HPE_METHOD "* ]]; then
  export HPE_DEVICE="GPU"
  HPE_RUNTIME="nvidia"
  export NVIDIA_VISIBLE_DEVICES="${NVIDIA_VISIBLE_DEVICES:-all}"
else
  export NVIDIA_VISIBLE_DEVICES="none"
fi
export HPE_RUNTIME

echo "[DEBUG] HPE_INPUT=$HPE_INPUT  HPE_METHOD=$HPE_METHOD  HPE_DEVICE=$HPE_DEVICE  HPE_RUNTIME=$HPE_RUNTIME"

# Step 9b: Validate that the video file exists before starting the streamer.
# The streamer mounts ../videos as /data inside the container.
VIDEO_FILE="${VIDEO_FILE_NAME:-vga_01_01.mp4}"
VIDEO_HOST_PATH="$(dirname "$0")/../videos/${VIDEO_FILE}"
if [ ! -f "$VIDEO_HOST_PATH" ]; then
  echo "[ERROR] Video file not found: $VIDEO_HOST_PATH"
  echo "[ERROR] Set VIDEO_FILE_NAME to a file that exists under $(dirname "$0")/../videos/"
  exit 1
fi
echo "[DEBUG] Video file validated: $VIDEO_HOST_PATH"

# Step 9c: Start the NVENC streamer (video file validated above)
echo "Starting video-producer (FFmpeg NVENC streamer)..."
docker compose -f $docker_compose_file up -d streamer

# Step 9c: Wait for the streamer to publish the RTSP stream before starting HPE.
# Probing localhost:8554 only confirms MediaMTX is listening; it does NOT mean
# the /stream path is being published. We use ffprobe if available, otherwise
# fall back to the MediaMTX REST API.
wait_for_rtsp_stream() {
  local url="rtsp://127.0.0.1:8554/stream"
  local timeout=60
  local waited=0
  echo "[INFO] Waiting for RTSP stream to be published at $url ..."
  while [ $waited -lt $timeout ]; do
    if command -v ffprobe >/dev/null 2>&1; then
      if ffprobe -v quiet -rtsp_transport tcp \
           -read_intervals "%+#1" \
           "$url" >/dev/null 2>&1; then
        echo "[INFO] RTSP stream is live (ffprobe confirmed)."
        return 0
      fi
    else
      # Fallback: check that MediaMTX has at least one active publisher by
      # querying its REST API (port 8888 exposes the API on mediamtx:1-ffmpeg).
      if curl -sf "http://127.0.0.1:8888/v3/paths/list" 2>/dev/null \
           | grep -q '"readyTime"'; then
        echo "[INFO] RTSP stream is live (MediaMTX API confirmed)."
        return 0
      fi
    fi
    echo "[DEBUG] Stream not yet available, retrying in 2s... (${waited}s elapsed)"
    sleep 2
    waited=$((waited + 2))
  done
  echo "[ERROR] RTSP stream not confirmed after ${timeout}s; aborting experiment."
  echo "[ERROR] Check video-producer and mediamtx logs before retrying."
  return 1
}
wait_for_rtsp_stream

# Step 10: Start hpe container
hpe_start=$(date +%s.%N)
docker compose -f $docker_compose_file up -d hpe

# Step 11: Measure hpe container startup time
measure_container_startup "$HPE_SERVICE" "$hpe_start"

# Step 12: Capture initial logs from hpe container
sleep 2
docker logs $(docker ps -qf "name=^/hpe$") > "$results_dir/logs/hpe_startup.log" 2>&1
tail -n 20 "$results_dir/logs/hpe_startup.log"
docker logs $(docker ps -qf "name=^/hpe$") | tee "$results_dir/logs/hpe_startup_full.log"

# Step 13: Start and measure monitoring containers
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

# Step 14: Get the main.py PID inside the hpe container (for monitoring)
mkdir -p ./pids
HPE_CONTAINER=$(docker ps -qf "name=^/hpe$")
if [ -n "$HPE_CONTAINER" ]; then
  for attempt in {1..5}; do
    HPE_PID=$(docker exec $HPE_CONTAINER pgrep -f "python.*main.py" 2>/dev/null | head -1)
    if [ -n "$HPE_PID" ]; then
      echo "$HPE_PID" > ./pids/hpe.pid
      echo "[DEBUG] HPE main.py PID: $HPE_PID"
      break
    else
      echo "[DEBUG] Waiting for main.py to start (attempt $attempt/5)..."
      sleep 2
    fi
  done
  if [ ! -s ./pids/hpe.pid ]; then
    echo "[WARNING] Could not find main.py PID in HPE container — monitor_pid.sh will not track the process"
  fi
fi

# Step 15: Monitor hpe container until it exits
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

# Check HPE container exit code
HPE_CONTAINER_FINAL=$(docker ps -aqf "name=^/hpe$")
if [ -n "$HPE_CONTAINER_FINAL" ]; then
  hpe_exit_code=$(docker inspect --format='{{.State.ExitCode}}' "$HPE_CONTAINER_FINAL" 2>/dev/null || echo "unknown")
  echo "[INFO] HPE container exit code: $hpe_exit_code" | tee -a "$results_dir/logs/hpe_exit.log"
  if [ "$hpe_exit_code" != "0" ] && [ "$hpe_exit_code" != "unknown" ]; then
    echo "[WARNING] HPE container exited with non-zero code ($hpe_exit_code) — results may be incomplete"
  fi
fi

# Step 16: Wait for the hpe container name to be fully released
for i in {1..10}; do
  if docker ps -a --format '{{.Names}}' | grep -wq hpe; then
    echo "[DEBUG] Waiting for hpe container name to be released..."
    sleep 1
  else
    break
  fi
done

# Step 17: Collect performance data
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

# Step 18: Copy trace files
mkdir -p "$results_dir/traces/bcc"
if [ -n "$TRACE_CONTAINER" ]; then
  # Copy RX trace (incoming video bytes)
  if docker exec $TRACE_CONTAINER ls -la /opt/tracer/output/hpe_video_rx.csv 2>/dev/null || false; then
    docker cp "$TRACE_CONTAINER:/opt/tracer/output/hpe_video_rx.csv" "$results_dir/traces/bcc/hpe_video_rx.csv" && \
    echo "Copied BCC RX trace to $results_dir/traces/bcc/hpe_video_rx.csv" || \
    echo "[ERROR] Failed to copy BCC RX trace file"
  else
    echo "[WARNING] Could not find hpe_video_rx.csv in bcc-tracer."
  fi
  
  # Copy TX trace (outgoing bytes)
  if docker exec $TRACE_CONTAINER ls -la /opt/tracer/output/hpe_video_tx.csv 2>/dev/null || false; then
    docker cp "$TRACE_CONTAINER:/opt/tracer/output/hpe_video_tx.csv" "$results_dir/traces/bcc/hpe_video_tx.csv" && \
    echo "Copied BCC TX trace to $results_dir/traces/bcc/hpe_video_tx.csv" || \
    echo "[WARNING] Failed to copy BCC TX trace file"
  else
    echo "[WARNING] Could not find hpe_video_tx.csv in bcc-tracer."
  fi
  
  docker cp "$TRACE_CONTAINER:/opt/tracer/output/logs/bcc-tracer.log" "$results_dir/logs/bcc-tracer-internal.log" 2>/dev/null || true
fi

# Step 19: Collect container logs before stopping
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

# Step 20: Copy HPE output (CSVs, JSON) from bind-mounted host path
mkdir -p "$results_dir/hpe_output"
if compgen -G "./results/*.csv" > /dev/null 2>&1 || compgen -G "./results/*.json" > /dev/null 2>&1; then
  cp ./results/*.csv "$results_dir/hpe_output/" 2>/dev/null || true
  cp ./results/*.json "$results_dir/hpe_output/" 2>/dev/null || true
  echo "Copied HPE output files to $results_dir/hpe_output/"
else
  echo "[WARNING] No CSV or JSON files found in ./results — HPE may not have produced output"
fi

# Step 21: Copy GPU metrics
mkdir -p "$results_dir/gpu"
if [ -f ./results/gpu_metrics.csv ]; then
  cp ./results/gpu_metrics.csv "$results_dir/gpu/gpu_metrics.csv"
  echo "Copied GPU metrics to $results_dir/gpu/gpu_metrics.csv"
else
  echo "[WARNING] gpu_metrics.csv not found in ./results"
fi

# Step 22: Stop and clean up all containers
echo "[DEBUG] Stopping and cleaning up containers..."
docker compose -f $docker_compose_file down --remove-orphans --volumes
docker rm -f hpe mediamtx video-producer gpu-metrics perf_monitor bcc-tracer 2>/dev/null || true

end_time=$(date +%s)
duration=$((end_time - start_time))
echo "Experiment completed in $duration seconds."
echo "Results are saved in the directory: $results_dir"

# Verify collected data
echo "[DEBUG] Collected data summary:"
if command -v tree >/dev/null 2>&1; then
  tree -h "$results_dir" | head -n 20
else
  echo "[WARNING] 'tree' command not found, using 'ls' instead:"
  ls -Rlh "$results_dir"
fi

