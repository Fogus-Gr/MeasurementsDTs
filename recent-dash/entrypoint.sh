#!/bin/bash
set -e

cd /opt/http_proxy

# Start the proxy in the background
./proxy -a "$SERVICE_IP" -p "$SERVICE_PORT" -sa "$HTTP_SERVER_IP" -sp "$HTTP_SERVER_PORT" -d "$SERVICE_CACHE_FOLDER" $SERVICE_ADDITIONAL_PARAMETERS &

MAIN_PID=$!
echo $MAIN_PID > /pids/dash.pid

# Wait a moment for child processes to start
sleep 1

# Append all child PIDs (if any) to the PID file
pgrep -P $MAIN_PID >> /pids/dash.pid

# Optionally, print for debugging
echo "Proxy main PID: $MAIN_PID"
echo "Proxy child PIDs: $(pgrep -P $MAIN_PID)"

# Wait for the main process to exit
wait $MAIN_PID
