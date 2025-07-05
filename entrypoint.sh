#!/bin/bash

echo "Write our PID to the shared file"
if [ -n "$PID_FILE" ]; then
  echo $$ > "$PID_FILE"
  echo "Wrote PID $$ to $PID_FILE"
fi

# Test connectivity to streaming server with fallback to wget if curl isn't available
echo "Testing connection to streaming server..."
for i in {1..5}; do
  if command -v curl &> /dev/null; then
    if curl -s --head "http://172.18.0.2:8089/stream.h264" | grep -q "HTTP"; then
      echo "Successfully connected to streaming server with curl"
      break
    fi
  elif command -v wget &> /dev/null; then
    if wget -q --spider "http://172.18.0.2:8089/stream.h264"; then
      echo "Successfully connected to streaming server with wget"
      break
    fi
  fi
  echo "Waiting for streaming server (attempt $i)..."
  sleep 2
done

# Show command that will be executed
echo "About to execute: $@"

# Execute the command passed to docker run
exec "$@"