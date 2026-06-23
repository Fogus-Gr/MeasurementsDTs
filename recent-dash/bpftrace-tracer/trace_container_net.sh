#!/bin/bash
echo "trace_container_net.sh started, monitoring DASH video traffic" >&2
set -eo pipefail

NETIF=${NETIF:-any}
TRACE_INTERVAL_MS=${TRACE_INTERVAL_MS:-10}

if [ -z "$DASH_SERVER_IP" ] || [ -z "$DASH_PROXY_IP" ] || [ -z "$DASH_CLIENT_IP" ]; then
  echo "[ERROR] DASH_SERVER_IP, DASH_PROXY_IP, and DASH_CLIENT_IP are required." >&2
  exit 1
fi

DASH_GATEWAY_IP=${DASH_GATEWAY_IP:-${DASH_CLIENT_IP%.*}.1}

if [ "$NETIF" = "auto" ]; then
  NETIF=$(ip route | awk '/default/ {print $5; exit}')
fi
if [ -z "$NETIF" ]; then
  NETIF=$(ip -o link show | awk -F': ' '$2 != "lo" {sub(/@.*/, "", $2); print $2; exit}')
fi
if [ "$NETIF" != "any" ] && { [ -z "$NETIF" ] || ! ip link show "$NETIF" >/dev/null 2>&1; }; then
  echo "[ERROR] Could not detect network interface. Set NETIF to any or a valid interface." >&2
  ip -br link >&2 || true
  exit 1
fi

# If NETIF is still "any", try to find the docker bridge for our target network.
# On a host-networked container, tcpdump -i any sees each packet twice (once on
# the veth pair, once on the bridge interface), causing exactly 2x counting.
# Capturing on the specific bridge interface avoids this double-counting.
if [ "$NETIF" = "any" ]; then
  bridge_if=$(ip route get "$DASH_SERVER_IP" 2>/dev/null | grep -oP 'dev \K\S+')
  if [ -n "$bridge_if" ] && [ "$bridge_if" != "lo" ]; then
    echo "[INFO] Auto-detected Docker bridge interface: $bridge_if (replacing NETIF=any to avoid double-counting)" >&2
    NETIF="$bridge_if"
  else
    echo "[WARN] Could not auto-detect bridge interface for $DASH_SERVER_IP; using NETIF=any (may double-count)" >&2
  fi
fi

mkdir -p /opt/tracer/output
echo "timestamp_ms,proxy_rx_video_bytes,proxy_tx_video_bytes" > /opt/tracer/output/trace.csv
REQUEST_LOG=/opt/tracer/output/served_segments.log
echo "timestamp_ms,resolution,segment" > "$REQUEST_LOG"

cleanup() {
  pkill -INT tcpdump 2>/dev/null || true
}
trap cleanup INT TERM EXIT

FILTER="tcp and (((src host ${DASH_SERVER_IP} and src port 80 and dst host ${DASH_PROXY_IP}) or (src host ${DASH_PROXY_IP} and src port 80 and (dst host ${DASH_CLIENT_IP} or dst host ${DASH_GATEWAY_IP}))))"
if [ -n "$DASH_PLAYER_IP" ]; then
  REQUEST_FILTER="tcp and dst port 80 and dst host ${DASH_CLIENT_IP} and (src host ${DASH_PLAYER_IP} or src host ${DASH_GATEWAY_IP})"
else
  REQUEST_FILTER="tcp and dst port 80 and dst host ${DASH_CLIENT_IP}"
fi

echo "Monitoring interface: $NETIF" >&2
echo "DASH server: $DASH_SERVER_IP  proxy: $DASH_PROXY_IP  client: $DASH_CLIENT_IP  gateway: $DASH_GATEWAY_IP" >&2
echo "tcpdump filter: $FILTER" >&2

# Capture the player request paths so the results show which DASH segments were
# actually requested during the experiment.
echo "request capture filter: $REQUEST_FILTER" >&2
tcpdump -i "$NETIF" -n -tt -l -s 0 -A "$REQUEST_FILTER" 2>/opt/tracer/output/tcpdump_requests.err | \
gawk '
function record(path) {
  gsub(/\r$/, "", path)
  key = current_ts_ms "," path
  if (key == last_key) {
    return
  }
  last_key = key
  if (path ~ /^\/video_audio_[^[:space:]]+$/) {
    printf "%s,audio,%s\n", current_ts_ms, substr(path, 2)
    fflush()
  } else if (match(path, /^\/video_([0-9]+)_[^[:space:]]+$/, seg)) {
    printf "%s,%s,%s\n", current_ts_ms, seg[1], substr(path, 2)
    fflush()
  }
}
{
  if (match($0, /^([0-9]+\.[0-9]+) /, m)) {
    current_ts_ms = int(m[1] * 1000)
  }
  if (match($0, /GET[[:space:]]+([^[:space:]]+)[[:space:]]+HTTP\/[0-9.]+/, req)) {
    path = req[1]
    sub(/^https?:\/\/[^/]+/, "", path)
    record(path)
  }
}' >> "$REQUEST_LOG" &

# Count TCP payload bytes for DASH HTTP responses only:
# - server:80 -> proxy = proxy RX from origin
# - proxy:80 -> client/gateway = proxy TX to player-facing client path
tcpdump -i "$NETIF" -n -tt -l -s 96 "$FILTER" 2>/opt/tracer/output/tcpdump.err | \
gawk -v interval_ms="$TRACE_INTERVAL_MS" \
     -v server="$DASH_SERVER_IP" \
     -v proxy="$DASH_PROXY_IP" \
     -v client="$DASH_CLIENT_IP" \
     -v gateway="$DASH_GATEWAY_IP" '
function emit_until(bucket) {
  while (current_bucket != "" && bucket > current_bucket) {
    printf "%d,%d,%d\n", current_bucket, rx_bytes, tx_bytes
    fflush()
    rx_bytes = 0
    tx_bytes = 0
    current_bucket += interval_ms
  }
}
{
  if (!match($0, /IP ([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)\.[0-9]+ > ([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)\.[0-9]+:.* length ([0-9]+)/, m)) {
    next
  }

  ts_ms = int($1 * 1000)
  bucket = int(ts_ms / interval_ms) * interval_ms
  if (current_bucket == "") {
    current_bucket = bucket
  }
  emit_until(bucket)

  src = m[1]
  dst = m[2]
  len = m[3] + 0
  if (src == server && dst == proxy) {
    rx_bytes += len
  } else if (src == proxy && (dst == client || dst == gateway)) {
    tx_bytes += len
  }
}
END {
  if (current_bucket != "") {
    printf "%d,%d,%d\n", current_bucket, rx_bytes, tx_bytes
  }
}' >> /opt/tracer/output/trace.csv
