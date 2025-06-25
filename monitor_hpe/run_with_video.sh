#!/bin/bash
# filepath: /home/user/MeasurementsDTs/monitor_hpe/run_with_video.sh

# Get video file from argument or use default
VIDEO_FILE=${1:-sample.mp4}

# Verify the video exists
if [ ! -f "/home/user/MeasurementsDTs/videos/$VIDEO_FILE" ]; then
    echo "Error: Video file not found: /home/user/MeasurementsDTs/videos/$VIDEO_FILE"
    echo "Available videos:"
    ls -la /home/user/MeasurementsDTs/videos/
    exit 1
fi

# Export variable for docker-compose
export VIDEO_FILE

# Run the experiment
echo "Running experiment with video: $VIDEO_FILE"
./run_experiment.sh