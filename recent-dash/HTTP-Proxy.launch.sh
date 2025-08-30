#!/bin/bash

# Change working folder
cd /opt/http_proxy/

# If a domain was given for the target server, convert it to IP
eval '[[ -z "$HTTP_SERVER_DOMAIN" ]] || HTTP_SERVER_IP=$(getent hosts $HTTP_SERVER_DOMAIN | awk "{ print \$1 }" )'
#echo "Using HTTP Server IP $HTTP_SERVER_IP"

# Print instance info
echo "[PROXY] Service is stating ..."
echo "[PROXY] Forwarding traffic from $SERVICE_IP:$SERVICE_PORT to $HTTP_SERVER_IP:$HTTP_SERVER_PORT"
echo "[PROXY] Using as cache folder: $SERVICE_CACHE_FOLDER"
echo "[PROXY] Running with additional parameters: $SERVICE_ADDITIONAL_PARAMETERS"

# Start Service
# e.g. ./proxy -a 0.0.0.0 -p 80 -sa $HTTP_SERVER_IP -sp $HTTP_SERVER_PORT -d ./cache -al swg -r1 15.0 -r2 5.0 -l 250 -dl predictive -c random -s 1 -n 131
echo "[PROXY] ./proxy -a $SERVICE_IP -p $SERVICE_PORT -sa $HTTP_SERVER_IP -sp $HTTP_SERVER_PORT -d $SERVICE_CACHE_FOLDER $SERVICE_ADDITIONAL_PARAMETERS"
./proxy -a $SERVICE_IP -p $SERVICE_PORT -sa $HTTP_SERVER_IP -sp $HTTP_SERVER_PORT -d $SERVICE_CACHE_FOLDER $SERVICE_ADDITIONAL_PARAMETERS
