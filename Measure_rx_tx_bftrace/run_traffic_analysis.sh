#!/bin/bash

set -e

echo "Cleaning up previous containers, networks, and volumes..."
docker compose down --volumes --remove-orphans

echo "Rebuilding all images..."
docker compose build

mkdir -p pcap

echo "Starting iperf and tcpdump containers..."
docker compose up -d iperf-server iperf-client tcpdump

echo "Waiting for iperf to initialize..."
sleep 10

echo "Starting bpftrace container..."
docker compose up -d bpftrace

echo "Waiting for iperf test to finish (60s)..."
sleep 70

echo "Stopping bpftrace container and capturing output..."
docker compose stop bpftrace

echo "Saving BPFtrace output to file..."
docker compose logs bpftrace > traffic_data.txt

echo "Converting logs to CSV format..."
python3 parse_traffic.py traffic_data.txt

echo "Stopping all containers..."
docker compose down

echo "Parsing traffic data to CSV..."
python3 parse_traffic.py output/traffic_data.txt

if [ -s traffic_report.csv ] && [ $(wc -l < traffic_report.csv) -gt 1 ]; then
    echo "Traffic data successfully captured in traffic_report.csv"
    echo "Generating traffic plot..."
    python3 plot_traffic.py
else
    echo "Warning: traffic_report.csv is empty or contains only the header."
    exit 1
fi

echo "Saving experiment artifacts..."
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULTS_DIR="results_$TIMESTAMP"
mkdir -p "$RESULTS_DIR"
mv traffic_data.txt traffic_report.csv traffic_plot.png pcap/ "$RESULTS_DIR" 2>/dev/null
cp docker-compose.yml *.py *.bt "$RESULTS_DIR"

echo "Analysis complete. Results saved to $RESULTS_DIR/"