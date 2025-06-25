#!/bin/bash

Write our PID to the shared file
if [ -n "$PID_FILE" ]; then
echo $$ > "$PID_FILE"
echo "Wrote PID $$$$ to $PID_FILE"
fi

exec "$@"