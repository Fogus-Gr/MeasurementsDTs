#!/bin/bash

echo "============================================"
echo "    Direct H.264 Streaming Server"
echo "============================================"
echo
echo "Starting HTTP H.264 streaming server..."
echo "Server will listen on port ${SERVER_PORT}"
echo
echo "Usage: $0 [video_file] [port]"
echo
echo "Test URLs:"
echo "  VLC: http://localhost:8080/stream.h264"
echo "  FFplay: ffplay http://localhost:8080/stream.h264"
echo
echo "Press Ctrl+C to stop the server"
echo "============================================"
echo

# Default video file (update this path as needed)
VIDEO_FILE="${1:-/path/to/your/video.mp4}"
PORT="${2:-8080}"

if [ ! -f "$VIDEO_FILE" ]; then
    echo "Error: Video file not found: $VIDEO_FILE"
    echo "Usage: $0 <video_file> [port]"
    echo "Example: $0 /home/user/video.mp4 8080"
    exit 1
fi

python3 direct_stream_server.py --video "$VIDEO_FILE" --port "$PORT"
