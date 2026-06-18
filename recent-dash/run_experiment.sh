#!/bin/bash
set -e

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR"

# bc is required for timestamp/startup timing. Install it on the host first.
if ! command -v bc &> /dev/null; then
  echo "[ERROR] Missing required host command: bc" >&2
  echo "Install bc before running this experiment." >&2
  exit 1
fi

DASH_MANIFEST=${DASH_MANIFEST:-manifest_single.mpd}
export DASH_MANIFEST
if [ ! -f "segments/$DASH_MANIFEST" ]; then
  echo "[ERROR] Missing DASH manifest: recent-dash/segments/$DASH_MANIFEST" >&2
  echo "Restore the migrated DASH segments into recent-dash/segments/ before running this rig." >&2
  exit 1
fi

measure_container_startup() {
  local container_name=$1
  local start_time=$2
  local container_id
  container_id=$(docker ps -qf "name=dash-caching-$container_name")

  if [ -n "$container_id" ]; then
    local current_time
    local time_diff
    current_time=$(date +%s.%N)
    time_diff=$(echo "$current_time - $start_time" | bc)

    echo "Container $container_name instantiation time: $time_diff seconds" >> "$results_dir/container_timing.txt"
    echo "[DEBUG] $container_name took $time_diff seconds to instantiate"
  else
    echo "[WARNING] Could not find container $container_name to measure startup time"
  fi
}

wait_for_container() {
  local container_name=$1
  local waited=0
  local container_id=""

  while [ "$waited" -lt "$readiness_timeout_seconds" ]; do
    container_id=$(docker ps -qf "name=dash-caching-$container_name")
    if [ -n "$container_id" ]; then
      echo "$container_id"
      return 0
    fi
    echo "[DEBUG] Waiting for $container_name container... (${waited}s elapsed)" >&2
    sleep "$readiness_poll_seconds"
    waited=$((waited + readiness_poll_seconds))
  done

  echo "[ERROR] Timed out waiting for $container_name container after ${readiness_timeout_seconds}s" >&2
  return 1
}

http_url_ok() {
  local url=$1
  if command -v curl >/dev/null 2>&1; then
    curl -fsS --max-time 2 "$url" >/dev/null
    return $?
  fi
  if command -v wget >/dev/null 2>&1; then
    wget -q --timeout=2 -O /dev/null "$url"
    return $?
  fi

  local rest=${url#http://}
  local host_port=${rest%%/*}
  local path="/${rest#*/}"
  local host=${host_port%%:*}
  local port=${host_port##*:}
  if [ "$host" = "$port" ]; then
    port=80
  fi

  exec 3<>"/dev/tcp/$host/$port" || return 1
  printf 'GET %s HTTP/1.0\r\nHost: %s\r\n\r\n' "$path" "$host" >&3
  local status=""
  IFS= read -r status <&3 || true
  exec 3<&-
  exec 3>&-
  [[ "$status" =~ ^HTTP/[0-9.]+[[:space:]](2|3)[0-9][0-9] ]]
}

wait_for_http_url() {
  local name=$1
  local url=$2
  local waited=0

  while [ "$waited" -lt "$readiness_timeout_seconds" ]; do
    if http_url_ok "$url"; then
      echo "[DEBUG] $name ready at $url"
      return 0
    fi
    echo "[DEBUG] Waiting for $name at $url... (${waited}s elapsed)"
    sleep "$readiness_poll_seconds"
    waited=$((waited + readiness_poll_seconds))
  done

  echo "[ERROR] Timed out waiting for $name at $url after ${readiness_timeout_seconds}s" >&2
  return 1
}

wait_for_trace_ready() {
  local container_id=$1
  local waited=0

  while [ "$waited" -lt "$readiness_timeout_seconds" ]; do
    if docker logs "$container_id" 2>&1 | grep -q "tcpdump filter:"; then
      echo "[DEBUG] trace_container is ready to capture DASH traffic"
      return 0
    fi
    echo "[DEBUG] Waiting for trace_container readiness... (${waited}s elapsed)" >&2
    sleep "$readiness_poll_seconds"
    waited=$((waited + readiness_poll_seconds))
  done

  echo "[ERROR] Timed out waiting for trace_container readiness after ${readiness_timeout_seconds}s" >&2
  return 1
}

timestamp=$(date +%Y%m%d_%H%M%S)
cpu_model=$(lscpu | grep "Model name" | sed 's/.*: *//g' | tr -s ' ' '_' | tr -d ',()/')
start_time=$(date +%s)

container_type=${1:-dash}
experiment_duration_seconds=${EXPERIMENT_DURATION_SECONDS:-500}
readiness_timeout_seconds=${READINESS_TIMEOUT_SECONDS:-60}
readiness_poll_seconds=${READINESS_POLL_SECONDS:-2}
enable_dash_player=${ENABLE_DASH_PLAYER:-1}
DASH_SERVER_IP=${DASH_SERVER_IP:-172.28.0.2}
DASH_PROXY_IP=${DASH_PROXY_IP:-172.28.0.3}
DASH_CLIENT_IP=${DASH_CLIENT_IP:-172.28.0.4}
DASH_PLAYER_URL="http://http_client/manifest.mpd"
export DASH_SERVER_IP DASH_PROXY_IP DASH_CLIENT_IP DASH_PLAYER_URL

results_dir="results_${container_type}_${cpu_model}_${timestamp}"
mkdir -p "$results_dir/logs" "$results_dir/traces" "$results_dir/perf"

echo "[DEBUG] Working directory: $(pwd)"
echo "Cleaning up old CSV files..."
rm -f ./results/*.csv ./traces/*.csv ./traces/*.log ./traces/*.err 2>/dev/null || true

echo "Preparing results directory: $results_dir"

COMPOSE_FILE="docker-compose.yml"

echo "Stopping and removing existing containers..."
docker compose -f "$COMPOSE_FILE" down --remove-orphans

touch "$results_dir/container_timing.txt"
echo "Container Instantiation Timing:" > "$results_dir/container_timing.txt"

main_containers_start=$(date +%s.%N)
echo "Building and starting fresh DASH containers..."
docker compose -f "$COMPOSE_FILE" up -d http_server http_proxy http_client

SERVER_CONTAINER=$(wait_for_container "http_server")
PROXY_CONTAINER=$(wait_for_container "http_proxy")
CLIENT_CONTAINER=$(wait_for_container "http_client")

measure_container_startup "http_server" "$main_containers_start"
measure_container_startup "http_proxy" "$main_containers_start"
measure_container_startup "http_client" "$main_containers_start"

echo "[DEBUG] Proxy container ID: $PROXY_CONTAINER"
PROXY_PORT=$(docker port "$PROXY_CONTAINER" 80 | cut -d ":" -f 2)
if [ -z "$PROXY_PORT" ]; then
  echo "[ERROR] Could not resolve DASH proxy host port." >&2
  exit 1
fi
PROXY_URL="http://localhost:$PROXY_PORT/manifest.mpd"
wait_for_http_url "DASH proxy manifest" "$PROXY_URL"

echo "[DEBUG] Getting all PIDs inside the proxy container..."
PROXY_PIDS=$(docker top "$PROXY_CONTAINER" -eo pid | awk 'NR>1 {print $1}')
echo "[DEBUG] All PIDs detected: $PROXY_PIDS"
CLIENT_PORT=$(docker port "$CLIENT_CONTAINER" 80 | cut -d ":" -f 2)
if [ -z "$CLIENT_PORT" ]; then
  echo "[ERROR] Could not resolve DASH client host port." >&2
  exit 1
fi
CLIENT_URL="http://localhost:$CLIENT_PORT/manifest.mpd"
wait_for_http_url "DASH client manifest" "$CLIENT_URL"

DASH_SERVER_IP=$(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$SERVER_CONTAINER")
DASH_PROXY_IP=$(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$PROXY_CONTAINER")
DASH_CLIENT_IP=$(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$CLIENT_CONTAINER")
if [ -z "$DASH_SERVER_IP" ] || [ -z "$DASH_PROXY_IP" ] || [ -z "$DASH_CLIENT_IP" ]; then
  echo "[ERROR] Could not resolve DASH container IPs for video-byte tracing." >&2
  exit 1
fi
export DASH_SERVER_IP DASH_PROXY_IP DASH_CLIENT_IP
echo "[DEBUG] DASH trace endpoints: server=$DASH_SERVER_IP proxy=$DASH_PROXY_IP client=$DASH_CLIENT_IP"
echo "[DEBUG] DASH proxy URL: $PROXY_URL"

mkdir -p ./pids
echo "$PROXY_PIDS" | grep -v "^1$" | sort -u > ./pids/dash.pid
echo "[DEBUG] Updated dash.pid contents:"
cat ./pids/dash.pid

echo "[DEBUG] Building perf_monitor image..."
docker compose -f "$COMPOSE_FILE" build perf_monitor trace_container mpv

perf_monitor_start=$(date +%s.%N)
echo "[DEBUG] Starting performance monitoring..."
docker compose -f "$COMPOSE_FILE" up -d perf_monitor
PERF_MONITOR_CONTAINER=$(docker ps -qf "name=dash-caching-perf_monitor")
echo "[DEBUG] perf_monitor container ID: $PERF_MONITOR_CONTAINER"
measure_container_startup "perf_monitor" "$perf_monitor_start"

trace_container_start=$(date +%s.%N)
echo "[DEBUG] Starting trace_container..."
docker compose -f "$COMPOSE_FILE" up -d trace_container
TRACE_CONTAINER=$(docker ps -qf "name=dash-caching-trace_container")
echo "[DEBUG] trace_container container ID: $TRACE_CONTAINER"
measure_container_startup "trace_container" "$trace_container_start"
wait_for_trace_ready "$TRACE_CONTAINER"

PLAYER_CONTAINER=""
DASH_PLAYER_IP=""
if [ "$enable_dash_player" != "0" ]; then
  player_start=$(date +%s.%N)
  echo "[DEBUG] Starting DASH player container..."
  docker compose -f "$COMPOSE_FILE" up -d mpv
  PLAYER_CONTAINER=$(wait_for_container "mpv")
  echo "[DEBUG] mpv container ID: $PLAYER_CONTAINER"
  DASH_PLAYER_IP=$(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$PLAYER_CONTAINER")
  if [ -z "$DASH_PLAYER_IP" ]; then
    echo "[ERROR] Could not resolve DASH player container IP." >&2
    exit 1
  fi
  export DASH_PLAYER_IP
  echo "[DEBUG] DASH player IP: $DASH_PLAYER_IP"
  echo "[DEBUG] DASH player URL: $DASH_PLAYER_URL"
  echo "[DEBUG] DASH trace endpoints: server=$DASH_SERVER_IP proxy=$DASH_PROXY_IP client=$DASH_CLIENT_IP player=$DASH_PLAYER_IP"
  measure_container_startup "mpv" "$player_start"
else
  echo "[DEBUG] DASH player container disabled by ENABLE_DASH_PLAYER=0"
fi
echo "DASH player URL: $DASH_PLAYER_URL"

echo "Running experiment for ${experiment_duration_seconds} seconds..."
elapsed=0
check_interval=30
while [ "$elapsed" -lt "$experiment_duration_seconds" ]; do
  sleep "$check_interval"
  elapsed=$((elapsed + check_interval))
  if [ -n "$PLAYER_CONTAINER" ]; then
    player_status=$(docker inspect -f '{{.State.Status}}' "$PLAYER_CONTAINER" 2>/dev/null || echo "unknown")
    player_restarts=$(docker inspect -f '{{.RestartCount}}' "$PLAYER_CONTAINER" 2>/dev/null || echo "?")
    echo "[HEALTH] ${elapsed}s elapsed | mpv status=$player_status restarts=$player_restarts"
  fi
done
echo "[DEBUG] Ending the experiment..."

# Collect mpv internal playback log
if [ -n "$PLAYER_CONTAINER" ]; then
  echo "[DEBUG] Copying mpv internal log..."
  docker cp "$PLAYER_CONTAINER:/tmp/mpv.log" "$results_dir/logs/mpv_internal.log" 2>/dev/null || \
    echo "[WARNING] Could not copy mpv internal log" >&2
fi

echo "[DEBUG] Collecting performance data after experiment completion..."
if [ -n "$PERF_MONITOR_CONTAINER" ]; then
  if docker exec "$PERF_MONITOR_CONTAINER" ls -la /output/perf_metrics.csv 2>/dev/null; then
    docker cp "$PERF_MONITOR_CONTAINER:/output/perf_metrics.csv" "$results_dir/perf/perf_metrics.csv"
    chmod -R u+rw "$results_dir"
    echo "Copied perf_monitor output to $results_dir/perf/perf_metrics.csv"
  else
    echo "[WARNING] Could not find perf_metrics.csv in perf_monitor container."
  fi
fi

if [ -n "$TRACE_CONTAINER" ]; then
  docker exec "$TRACE_CONTAINER" pkill -INT tcpdump 2>/dev/null || true
  sleep 2
  echo "[DEBUG] Copying network trace data from trace_container..."
  docker cp "$TRACE_CONTAINER:/opt/tracer/output/trace.csv" "$results_dir/traces/trace.csv"
  echo "Copied trace file to $results_dir/traces/trace.csv"
  docker cp "$TRACE_CONTAINER:/opt/tracer/output/served_segments.log" "$results_dir/traces/served_segments.log" 2>/dev/null || \
    echo "[WARNING] Could not copy served_segments.log from trace_container"
  echo "Copied served segment log to $results_dir/traces/served_segments.log"
fi

echo "[DEBUG] Collecting container logs..."
containers=("http_server" "http_proxy" "http_client" "perf_monitor" "trace_container")
if [ -n "$PLAYER_CONTAINER" ]; then
  containers+=("mpv")
fi
for container in "${containers[@]}"; do
  container_id=$(docker ps -aqf "name=dash-caching-$container")
  if [ -n "$container_id" ]; then
    docker logs "$container_id" > "$results_dir/logs/$container.log" 2>&1
    echo "Saved logs for $container to $results_dir/logs/$container.log"
  else
    echo "[WARNING] Container $container not found, skipping log collection."
  fi
done

echo "[DEBUG] Stopping and cleaning up containers..."
docker compose -f "$COMPOSE_FILE" down --remove-orphans

end_time=$(date +%s)
duration=$((end_time - start_time))
echo "Experiment completed in $duration seconds."
echo "Results are saved in the directory: $results_dir"

RESULTS_TXT="$results_dir/results.txt"
SEGMENTS_LOG="$results_dir/traces/served_segments.log"
DOCKER_COMPOSE_FILE="docker-compose.yml"

RESOLUTIONS="Not found"
if [ -f "$SEGMENTS_LOG" ]; then
  RESOLUTIONS=$(cut -d',' -f2 "$SEGMENTS_LOG" 2>/dev/null | sed -n 's/^video_\([0-9]\+\).*/\1/p' | sort -u | tr '\n' ' ')
  if [ -z "$RESOLUTIONS" ]; then
    RESOLUTIONS="Not found"
  fi
fi

SEGMENTS_OBSERVED="Not found"
if [ -f "$SEGMENTS_LOG" ]; then
  SEGMENTS_OBSERVED=$(cut -d',' -f2 "$SEGMENTS_LOG" 2>/dev/null | sort -u | tr '\n' ' ')
  if [ -z "$SEGMENTS_OBSERVED" ]; then
    SEGMENTS_OBSERVED="Not found"
  fi
fi

PROXY_PARAMS_DISPLAY=${PROXY_PARAMS:--al swg -r1 8.3 -r2 3.6 -l 3000 -dl fixed -c random -s 600 -n 65}
if [ -z "$PROXY_PARAMS_DISPLAY" ]; then
  PROXY_PARAMS_DISPLAY="Not found"
fi

CPU_MODEL=$(lscpu | grep "Model name" | sed 's/.*: *//g')
CPU_CORES=$(lscpu | grep "^CPU(s):" | awk '{print $2}')
MEM_TOTAL=$(free -h | awk '/^Mem:/ {print $2}')

{
  echo "==== Experiment Summary ===="
  echo "http_proxy SERVICE_ADDITIONAL_PARAMETERS: $PROXY_PARAMS_DISPLAY"
  echo "DASH manifest: $DASH_MANIFEST"
  echo "DASH proxy URL: $PROXY_URL"
  echo "DASH player URL: $DASH_PLAYER_URL"
  if [ -n "$PLAYER_CONTAINER" ]; then
    echo "DASH player container: mpv"
  else
    echo "DASH player container: disabled"
  fi
  if [ -n "$DASH_PLAYER_IP" ]; then
    echo "DASH trace endpoints: server=$DASH_SERVER_IP proxy=$DASH_PROXY_IP client=$DASH_CLIENT_IP player=$DASH_PLAYER_IP"
  else
    echo "DASH trace endpoints: server=$DASH_SERVER_IP proxy=$DASH_PROXY_IP client=$DASH_CLIENT_IP player=disabled"
  fi
  echo "Machine CPU Model: $CPU_MODEL"
  echo "Machine CPU Cores: $CPU_CORES"
  echo "Machine Total Memory: $MEM_TOTAL"
  echo "Experiment Directory: $results_dir"
  echo "Experiment Timestamp: $(date)"
  echo ""
  echo "==== Container Instantiation Timing ===="
  if [ -f "$results_dir/container_timing.txt" ]; then
    tail -n +2 "$results_dir/container_timing.txt"
  else
    echo "No container timing information available"
  fi
  echo ""
  echo "==== DASH Resolutions Seen In Request Log ===="
  echo "$RESOLUTIONS"
  echo ""
  echo "==== DASH Segments Seen In Request Log ===="
  echo "$SEGMENTS_OBSERVED"
} > "$RESULTS_TXT"

echo "Wrote summary to $RESULTS_TXT"
