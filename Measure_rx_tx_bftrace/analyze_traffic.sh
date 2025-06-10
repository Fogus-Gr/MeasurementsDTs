#!/bin/bash

# Create pcap directory if it doesn't exist
mkdir -p pcap

# Start Docker containers
docker compose up -d

# Wait for 1 minutes
echo "Test running for 1 minutes..."
sleep 60

# Stop the containers
docker compose down

# Get BPFtrace output
echo "=== Generating Traffic Report ==="
docker compose logs bpftrace > traffic_report.txt

# Process BPFtrace output to generate CSV
awk -F' ' '{
    if ($2 == "SAMPLE") {
        printf "%s,%s,%s,%s,%s,%s,%s,%s\n", 
            $1, "", "", "", "", "", "", "0";
    } else {
        printf "%s,%s,%s,%s,%s,%s,%s,%s\n", 
            $1, $3, $6, "", "", $8, "", "";
    }
}' traffic_report.txt > traffic_report.csv

# Generate sampled report
echo "=== Generating Sampled Report ==="
awk -F' ' '/SAMPLE/ {print}' traffic_report.txt | \
    awk -F' ' '{
        printf "%s,%s,%s,%s,%s,%s,%s,%s\n", 
            $1, "", "", "", "", "", "", "0";
    }' > traffic_report_sampled.csv

# Calculate statistics
echo "=== Traffic Statistics ==="
total_send=0
total_recv=0
lines=$(wc -l < traffic_report.txt)

# Calculate send and receive totals
while read -r line; do
    if [[ $line == *"->"* ]]; then
        bytes=${line##* }
        total_send=$((total_send + bytes))
    elif [[ $line == *"<-"* ]]; then
        bytes=${line##* }
        total_recv=$((total_recv + bytes))
    fi
done < traffic_report.txt

echo "Total sent bytes: $total_send"
echo "Total received bytes: $total_recv"
echo "Total samples: $lines"

# Check if pcap file exists
if [ ! -f "pcap/traffic.pcap" ]; then
    echo "Error: pcap/traffic.pcap file not found"
    exit 1
fi

# Analyze pcap file using tshark with 10ms sampling
echo "=== Traffic Statistics ==="
tshark -r pcap/traffic.pcap -q -z io,stat,0.01

# Get detailed TCP statistics
echo -e "\n=== TCP Statistics ==="
tshark -r pcap/traffic.pcap -q -z conv,tcp

# Get packet size distribution
echo -e "\n=== Packet Size Distribution ==="
tshark -r pcap/traffic.pcap -q -z endpoints,tcp

# Get top conversations
echo -e "\n=== Top Conversations ==="
tshark -r pcap/traffic.pcap -q -z conv,tcp

# Get detailed statistics for RX/TX bytes
echo -e "\n=== Detailed RX/TX Statistics ==="
tshark -r pcap/traffic.pcap -q -z io,stat,0.01 | \
    awk '/^\s*Bytes/ {rx_bytes+=$3; tx_bytes+=$4} END {print "Total RX bytes: " rx_bytes; print "Total TX bytes: " tx_bytes}'

# Generate a CSV file with detailed packet information
echo -e "\n=== Generating Detailed Packet Report ==="
tshark -r pcap/traffic.pcap -T fields -e frame.time -e ip.src -e ip.dst -e tcp.srcport -e tcp.dstport -e frame.len -e tcp.flags -e tcp.analysis.ack_rtt > traffic_report.csv

# Generate a sampled CSV with 10ms intervals
echo -e "\n=== Generating Sampled Packet Report ==="
tshark -r pcap/traffic.pcap -T fields -e frame.time -e ip.src -e ip.dst -e tcp.srcport -e tcp.dstport -e frame.len -e tcp.flags -e tcp.analysis.ack_rtt -2 -R "frame.time_relative <= 0.01" > traffic_report_sampled.csv

# Filter the CSV files to show only iperf3 traffic
echo -e "\n=== Filtering CSV files for iperf3 traffic ==="
awk -F, '$5 == 5201 || $6 == 5201' traffic_report.csv > traffic_report_filtered.csv
awk -F, '$5 == 5201 || $6 == 5201' traffic_report_sampled.csv > traffic_report_sampled_filtered.csv

# Generate plot
echo -e "\n=== Generating Traffic Plot ==="
python3 plot_traffic.py

echo -e "\nAnalysis complete. Check traffic_report.csv for detailed packet information."
echo "Plot saved as traffic_plot.png"
