#!/bin/bash

# Script to run the monitoring experiment from scratch

# Change to the correct directory
cd $(dirname "$0")

# Parse command-line arguments
HPE_METHOD="${1:-movenet}"
VIDEO_FILE="${2:-ultimatum/hd_00_00.mp4}"

# Auto-detect available vCPUs
TOTAL_VCPUS=$(nproc)
echo "[INFO] Detected $TOTAL_VCPUS vCPUs on this system"

# Validate minimum requirements
if [ "$TOTAL_VCPUS" -lt 4 ]; then
    echo "[ERROR] This experiment requires at least 4 vCPUs. Found: $TOTAL_VCPUS"
    exit 1
fi

# Calculate resource allocation (reserve 2 vCPUs for monitoring, rest for HPE)
# For VMs with 4 vCPUs: 2 for HPE, 2 for monitoring
# For VMs with 8 vCPUs: 6 for HPE, 2 for monitoring
# For VMs with 16 vCPUs: 14 for HPE, 2 for monitoring
MONITOR_VCPUS=2
HPE_VCPUS=$((TOTAL_VCPUS - MONITOR_VCPUS))

# Ensure HPE gets at least 2 vCPUs
if [ "$HPE_VCPUS" -lt 2 ]; then
    HPE_VCPUS=2
    MONITOR_VCPUS=$((TOTAL_VCPUS - HPE_VCPUS))
fi

# Determine device and fine-tune resources based on method
case "$HPE_METHOD" in
  alphapose|openpose)
    # GPU methods - use fewer CPU cores but more memory
    export HPE_DEVICE="GPU"
    # GPU methods don't benefit as much from many CPU threads
    export OV_THREADS=$(( HPE_VCPUS < 4 ? HPE_VCPUS : 4 ))
    export HPE_CPU_LIMIT="${HPE_VCPUS}.0"
    export HPE_CPU_RESERVATION=$(awk "BEGIN {printf \"%.1f\", $HPE_VCPUS * 0.5}")
    export HPE_MEMORY_LIMIT="8G"
    export HPE_MEMORY_RESERVATION="6G"
    ;;
  movenet|ae1|ae2|ae3)
    # Lightweight OpenVINO models - scale threads with available vCPUs
    export HPE_DEVICE="CPU"
    export OV_THREADS=$HPE_VCPUS
    export HPE_CPU_LIMIT="${HPE_VCPUS}.0"
    export HPE_CPU_RESERVATION=$(awk "BEGIN {printf \"%.1f\", $HPE_VCPUS * 0.67}")
    # Memory scales with vCPUs: 1GB per vCPU, minimum 4GB
    MEM_GB=$(( HPE_VCPUS > 4 ? HPE_VCPUS : 4 ))
    export HPE_MEMORY_LIMIT="${MEM_GB}G"
    export HPE_MEMORY_RESERVATION=$(awk "BEGIN {printf \"%.0f\", $MEM_GB * 0.67}")G
    ;;
  hrnet)
    # HigherHRNet - heavier model, needs more memory
    export HPE_DEVICE="CPU"
    export OV_THREADS=$HPE_VCPUS
    export HPE_CPU_LIMIT="${HPE_VCPUS}.0"
    export HPE_CPU_RESERVATION=$(awk "BEGIN {printf \"%.1f\", $HPE_VCPUS * 0.67}")
    # HigherHRNet needs more memory: 1.5GB per vCPU, minimum 6GB
    MEM_GB=$(awk "BEGIN {printf \"%.0f\", $HPE_VCPUS * 1.5}")
    MEM_GB=$(( MEM_GB > 6 ? MEM_GB : 6 ))
    export HPE_MEMORY_LIMIT="${MEM_GB}G"
    export HPE_MEMORY_RESERVATION=$(awk "BEGIN {printf \"%.0f\", $MEM_GB * 0.75}")G
    ;;
  *)
    echo "[WARNING] Unknown method '$HPE_METHOD', using default settings"
    export HPE_DEVICE="CPU"
    export OV_THREADS=$HPE_VCPUS
    export HPE_CPU_LIMIT="${HPE_VCPUS}.0"
    export HPE_CPU_RESERVATION=$(awk "BEGIN {printf \"%.1f\", $HPE_VCPUS * 0.67}")
    MEM_GB=$(( HPE_VCPUS > 4 ? HPE_VCPUS : 4 ))
    export HPE_MEMORY_LIMIT="${MEM_GB}G"
    export HPE_MEMORY_RESERVATION=$(awk "BEGIN {printf \"%.0f\", $MEM_GB * 0.67}")G
    ;;
esac

# OpenVINO configuration
export OV_MODE="latency"
export OV_CPU_PINNING="true"
export OV_HYPER_THREADING="false"

# Export for docker-compose
export HPE_METHOD
export VIDEO_FILE

echo "[INFO] System Configuration:"
echo "  Total vCPUs: $TOTAL_VCPUS"
echo "  HPE vCPUs: $HPE_VCPUS"
echo "  Monitor vCPUs: $MONITOR_VCPUS"
echo ""
echo "[INFO] Experiment Configuration:"
echo "  Method: $HPE_METHOD"
echo "  Device: $HPE_DEVICE"
echo "  Video: $VIDEO_FILE"
echo "  CPU Allocation: $HPE_CPU_LIMIT cores (reserved: $HPE_CPU_RESERVATION)"
echo "  Memory: $HPE_MEMORY_LIMIT (reserved: $HPE_MEMORY_RESERVATION)"
echo "  OpenVINO Threads: $OV_THREADS"
echo ""

# Get current timestamp and CPU info for results directory
timestamp=$(date +%Y%m%d_%H%M%S)
cpu_info=$(lscpu | grep "Model name" | cut -d: -f2 | sed 's/^[ \t]*//;s/  */_/g' | cut -d' ' -f1-3)
results_dir="results_${HPE_METHOD}_${TOTAL_VCPUS}vcpu_${timestamp}"

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
     docker ps | grep -q "monitor-hpe"
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
