#!/bin/bash

# Change working folder
cd /opt/http_server/

# Print instance info
echo "[SERVER] Service is stating ..."
echo "[SERVER] Using as public folder: $SERVICE_PUBLIC_FOLDER"
echo "[SERVER] Running with additional parameters: $SERVICE_ADDITIONAL_PARAMETERS"

# Start Service
# e.g. main -a 0.0.0.0 -p 80 -d ./public -r2 5.0
echo "[SERVER] ./main -a $SERVICE_IP -p $SERVICE_PORT -d $SERVICE_PUBLIC_FOLDER $SERVICE_ADDITIONAL_PARAMETERS"
./main -a $SERVICE_IP -p $SERVICE_PORT -d $SERVICE_PUBLIC_FOLDER $SERVICE_ADDITIONAL_PARAMETERS
