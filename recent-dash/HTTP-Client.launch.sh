#!/bin/bash

# Change working folder
cd /opt/http_local/

# If a domain was given for the target server, convert it to IP
eval '[[ -z "$HTTP_PROXY_DOMAIN" ]] || HTTP_PROXY_IP=$(getent hosts $HTTP_PROXY_DOMAIN | awk "{ print \$1 }" )'
#echo "Using HTTP Server IP $HTTP_PROXY_IP"

# Print instance info
echo "[CLIENT] Service is stating ..."
echo "[CLIENT] Listening at $SERVICE_IP:$SERVICE_PORT and forwarding to proxy $HTTP_PROXY_IP:$HTTP_PROXY_PORT"
echo "[CLIENT] Using as public folder: $SERVICE_PUBLIC_FOLDER"

# Start Service
# e.g. ./local -a 0.0.0.0 -p 80 -sa $HTTP_PROXY_IP -sp $HTTP_PROXY_PORT -d ./public
echo "[CLIENT] ./local -a $SERVICE_IP -p $SERVICE_PORT -sa $HTTP_PROXY_IP -sp $HTTP_PROXY_PORT -d $SERVICE_PUBLIC_FOLDER"
./local -a $SERVICE_IP -p $SERVICE_PORT -sa $HTTP_PROXY_IP -sp $HTTP_PROXY_PORT -d $SERVICE_PUBLIC_FOLDER
