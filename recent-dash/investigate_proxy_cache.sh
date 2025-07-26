#!/bin/bash
set -e

# Find the proxy container name or ID
echo "[INFO] Locating http_proxy container..."
PROXY_CONTAINER=$(docker ps --filter 'name=dash-caching-http_proxy' --format '{{.Names}}' | head -1)
if [ -z "$PROXY_CONTAINER" ]; then
  echo "[ERROR] Could not find http_proxy container."
  exit 1
fi
echo "[INFO] Using container: $PROXY_CONTAINER"

# Print SERVICE_ADDITIONAL_PARAMETERS and cache folder
echo "[INFO] Fetching environment variables..."
docker exec $PROXY_CONTAINER printenv | grep -E 'SERVICE_CACHE_FOLDER|SERVICE_ADDITIONAL_PARAMETERS|HTTP_SERVER_DOMAIN|HTTP_SERVER_PORT'

CACHE_DIR=$(docker exec $PROXY_CONTAINER printenv SERVICE_CACHE_FOLDER)
if [ -z "$CACHE_DIR" ]; then
  CACHE_DIR="./cache"
fi

# Check if cache directory exists and is writable
echo "[INFO] Checking cache directory: $CACHE_DIR"
docker exec $PROXY_CONTAINER bash -c "ls -ld $CACHE_DIR && touch $CACHE_DIR/.cache_test && rm $CACHE_DIR/.cache_test" && \
  echo "[OK] Cache directory exists and is writable." || \
  echo "[ERROR] Cache directory missing or not writable!"

# Show last 50 lines of proxy logs
echo "[INFO] Last 50 lines of proxy logs:"
docker logs --tail 50 $PROXY_CONTAINER

# List contents of cache directory
echo "[INFO] Listing contents of cache directory: $CACHE_DIR"
docker exec $PROXY_CONTAINER ls -l $CACHE_DIR || echo "[WARN] Could not list cache directory."

# Optionally clear cache directory
echo -n "Do you want to clear the cache directory? [y/N]: "
read -r CLEAR_CACHE
if [[ "$CLEAR_CACHE" =~ ^[Yy]$ ]]; then
  echo "[INFO] Clearing cache directory..."
  docker exec $PROXY_CONTAINER rm -rf $CACHE_DIR/*
  echo "[INFO] Cache directory cleared."
fi

echo "[INFO] Investigation complete. Review the above output for errors or missing files."
echo "[INFO] Next steps:"
echo "- If the cache directory is empty after requests, check proxy logs for errors."
echo "- Ensure SERVICE_ADDITIONAL_PARAMETERS and cache folder are set correctly."
echo "- Try making a video request and rerun this script to see if files appear in the cache." 