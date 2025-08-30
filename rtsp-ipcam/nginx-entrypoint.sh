#!/bin/sh
set -e

# Process the template file
envsubst < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf

# Check if configuration is valid
nginx -t

# Start Nginx in foreground
exec nginx -g 'daemon off;'