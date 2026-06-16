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

mkdir -p /opt/tracer/output
echo "timestamp_ms,proxy_rx_video_bytes,proxy_tx_video_bytes" > /opt/tracer/output/trace.csv

FILTER="tcp and (((src host ${DASH_SERVER_IP} and src port 80 and dst host ${DASH_PROXY_IP}) or (src host ${DASH_PROXY_IP} and src port 80 and (dst host ${DASH_CLIENT_IP} or dst host ${DASH_GATEWAY_IP}))))"

echo "Monitoring interface: $NETIF" >&2
echo "DASH server: $DASH_SERVER_IP  proxy: $DASH_PROXY_IP  client: $DASH_CLIENT_IP  gateway: $DASH_GATEWAY_IP" >&2
echo "tcpdump filter: $FILTER" >&2

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
