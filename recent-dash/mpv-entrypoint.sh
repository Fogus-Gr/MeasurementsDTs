#!/bin/sh
set -eu

PLAYER_URL=${DASH_PLAYER_URL:-http://http_client/manifest.mpd}
RETRY_DELAY_SECONDS=${DASH_PLAYER_RETRY_DELAY_SECONDS:-1}
WARMUP_SECONDS=${DASH_PLAYER_WARMUP_SECONDS:-30}
START_DELAY_SECONDS=${DASH_PLAYER_START_DELAY_SECONDS:-5}

if command -v curl >/dev/null 2>&1; then
  waited=0
  while [ "$waited" -lt "$WARMUP_SECONDS" ]; do
    if curl -fsS --max-time 2 "$PLAYER_URL" >/dev/null; then
      break
    fi
    echo "[PLAYER] Waiting for DASH manifest at $PLAYER_URL (${waited}s elapsed)" >&2
    sleep "$RETRY_DELAY_SECONDS"
    waited=$((waited + RETRY_DELAY_SECONDS))
  done
fi

# Validate manifest content
manifest_size=$(curl -fsS --max-time 2 -o /dev/null -w '%{size_download}' "$PLAYER_URL" 2>/dev/null || echo "0")
if [ "$manifest_size" -lt 100 ]; then
  echo "[PLAYER] WARNING: Manifest appears empty or too small (${manifest_size} bytes)" >&2
fi

if [ "$START_DELAY_SECONDS" -gt 0 ]; then
  echo "[PLAYER] Waiting ${START_DELAY_SECONDS}s before starting mpv" >&2
  sleep "$START_DELAY_SECONDS"
fi

while true; do
  echo "[PLAYER] Starting mpv against $PLAYER_URL" >&2
  : > /tmp/mpv.log
  set +e
  mpv \
    --vo=null \
    --ao=null \
    --no-terminal \
    --force-window=no \
    --msg-level=all=info \
    --log-file=/tmp/mpv.log \
    --no-ytdl \
    --demuxer-lavf-format=dash \
    --demuxer-lavf-o=reconnect=1,reconnect_streamed=1,reconnect_delay_max=5,reconnect_on_network_error=1 \
    --demuxer-readahead-secs=30 \
    --speed=1 \
    "$PLAYER_URL"
  rc=$?
  set -e
  if [ -f /tmp/mpv.log ]; then
    tail -40 /tmp/mpv.log >&2 || true
  fi
  echo "[PLAYER] mpv exited with $rc; restarting in ${RETRY_DELAY_SECONDS}s" >&2
  sleep "$RETRY_DELAY_SECONDS"
done
