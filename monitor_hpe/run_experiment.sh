#!/bin/bash

# Script to run the monitoring experiment from scratch

# Change to the correct directory
cd $(dirname "$0")

# Get current timestamp and CPU info for results directory
timestamp=$(date +%Y%m%d_%H%M%S)
cpu_info=$(lscpu | grep "Model name" | cut -d: -f2 | sed 's/^[ \t]*//;s/  */_/g' | cut -d' ' -f1-3)
results_dir="results_cpu_${cpu_info}_${timestamp}"

# Create necessary directories
echo "Creating directories..."
mkdir -p "$results_dir/logs"
mkdir -p "pids"
mkdir -p "results"  # For Docker volume

# Set log file paths
hpe_log="$results_dir/logs/hpe_container.log"
monitor_log="$results_dir/logs/monitor_container.log"

# Clean up old PID files but keep results
echo "Cleaning up old PID files..."
rm -f pids/*

# Ensure results directory exists and is empty
echo "Preparing results directory..."
rm -f results/*.csv results/*.png 2>/dev/null || true

# Export the results directory for docker-compose
RESULTS_DIR="$results_dir"
export RESULTS_DIR

# Stop and remove existing containers
echo "Stopping and removing existing containers..."
docker compose -f docker-compose.yaml down

# Start containers without rebuilding
echo "Starting containers..."
docker compose -f docker-compose.yaml up -d --no-build --force-recreate

# Wait for containers to start
echo "Waiting for containers to start..."
sleep 5

# Check if containers are running
echo "Checking container status:"
docker ps | grep -E "monitor-hpe|monitor-monitor"

# Show PID file contents
echo "PID file contents:"
if [ -f "pids/hpe.pid" ]; then
    cat pids/hpe.pid
else
    echo "No PID file found yet"
fi

# Wait for experiment to complete
echo "Experiment started. Monitor container will run continuously."
# echo "Use Ctrl+C to stop the script when you want to end the experiment."

# Function to check if containers are still running
check_containers() {
    docker ps | grep -q -E "monitor-hpe|monitor-monitor"
    return $?
}

# Trap Ctrl+C to clean up
trap 'echo "Stopping experiment..."; docker compose -f docker-compose.yaml down; exit 0' SIGINT

# Monitor containers until they stop
while check_containers; do
    sleep 1
    echo -n "."
done

echo "\nContainers have stopped. Cleaning up..."

# Save container logs first
echo "Saving container logs to $results_dir/logs/..."
docker compose -f docker-compose.yaml logs hpe > "$hpe_log" 2>&1
docker compose -f docker-compose.yaml logs monitor > "$monitor_log" 2>&1

# Check and copy results from the Docker volume
if [ -f "results/pid_metrics.csv" ]; then
    # Copy results to the timestamped directory
    echo "Saving metrics data..."
    cp -v results/pid_metrics.csv "$results_dir/"
    
    # Generate plots
    echo "Generating plots..."
    if python3 plot_graph.py "$results_dir/pid_metrics.csv" 2>/dev/null; then
        echo "Successfully generated plot: $results_dir/pid_metrics.png"
    else
        echo "Warning: Failed to generate plots"
        echo "Trying alternative plot generation method..."
        # Try alternative plot generation if the first attempt fails
        python3 -c "
import pandas as pd
import matplotlib.pyplot as plt
df = pd.read_csv('$results_dir/pid_metrics.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
plt.figure(figsize=(15, 5))
plt.plot(df['timestamp'], df['cpu_percent'])
plt.title('CPU Usage Over Time')
plt.ylabel('CPU %')
plt.grid(True)
plt.savefig('$results_dir/cpu_usage.png')
print('Generated simple CPU plot')
"
    fi
    
    # Verify files were created
    if [ -f "$results_dir/pid_metrics.png" ] || [ -f "$results_dir/cpu_usage.png" ]; then
        echo "Successfully generated plot"
    else
        echo "Warning: Plot file was not created successfully"
        echo "Debug: Current directory: $(pwd)"
        echo "Debug: Files in results/:"
        ls -la results/ 2>/dev/null || echo "No files in results/"
    fi
else
    echo "Warning: No metrics CSV file found in results/ directory"
    echo "Debug: Current directory: $(pwd)"
    echo "Debug: Contents of results/:"
    ls -la results/ 2>/dev/null || echo "No results directory found"
    
    echo "Checking for other CSV files..."
    find . -name "*.csv" -type f
fi

# Clean up containers
docker compose -f docker-compose.yaml down

echo "Results saved in: $results_dir"
exit 0
