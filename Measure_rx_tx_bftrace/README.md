# Network Traffic Monitoring Scripts

This directory contains scripts for comprehensive network traffic analysis and monitoring.

## Main Script: run_traffic_analysis.sh

The main script that orchestrates the complete traffic analysis process:

1. Cleans up previous container environments
2. Builds necessary Docker images
3. Sets up a test environment with:
   - Iperf server and client for traffic generation
   - Tcpdump container for packet capture
   - BPFtrace container for detailed traffic analysis
4. Runs a 60-second traffic test
5. Captures network traffic data in multiple formats

The script uses the BPFtrace scripts in this directory to provide detailed traffic analysis while capturing raw packet data for further analysis.

## Prerequisites

### System Requirements
- Linux kernel version 4.17 or higher (for BPFtrace support)
- BPFtrace version 0.13.0 or higher
- Root privileges required for kernel probe access

### Dependencies
- bpftrace (package name: bpftrace)
- Linux kernel headers matching your running kernel
- libbpf development libraries

### Installation (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install bpftrace linux-headers-$(uname -r)
```

### Installation (CentOS/RHEL)
```bash
sudo yum install bpftrace kernel-headers
```

## Scripts Available

### 1. `capture_traffic.bt`
- Basic network traffic monitoring script (used by run_traffic_analysis)
- Tracks all network traffic on the system
- Shows both incoming (RX) and outgoing (TX) traffic
- Reports every 10ms
- Used internally by run_traffic_analysis for comprehensive traffic analysis

### 2. `capture_traffic_container.bt`
- Specialized version for container traffic monitoring
- Separates container traffic into dedicated counters
- Useful for identifying container-specific network usage
- Reports every 10ms

### 3. `capture_traffic_port.bt`
- Port-specific traffic monitoring
- Filters traffic by a specific port number
- Usage: `sudo ./capture_traffic_port.bt -p <port_number>`
- Example: `sudo ./capture_traffic_port.bt -p 80` for HTTP traffic
- Reports every 10ms

## Features Common to All Scripts

### 10ms Reporting Interval
All scripts use a 10ms reporting interval:
- **Purpose**: Provides real-time monitoring without overwhelming output
- **Functionality**: 
  - Counts bytes in real-time using kernel probes
  - Displays accumulated counts every 10ms
  - Clears counters after display for next interval
- **Important Notes**:
  - The 10ms interval only affects display timing
  - Actual traffic counting happens immediately at kernel level
  - Does not affect packet boundaries or transfer accuracy
  - Provides a balance between real-time monitoring and readability

## Usage

### Basic Usage
```bash
sudo ./capture_traffic.bt
```

### Container-Specific Usage
```bash
sudo ./capture_traffic_container.bt
```

### Port-Specific Usage
```bash
sudo ./capture_traffic_port.bt -p <port_number>
```

## Required Permissions
All scripts require root permissions to access kernel probes:
```bash
sudo ./script_name
```

## Output Format
All scripts display:
- Current time (in nanoseconds since start)
- RX (Receive) traffic statistics
- TX (Transmit) traffic statistics
- Clear separator between intervals
