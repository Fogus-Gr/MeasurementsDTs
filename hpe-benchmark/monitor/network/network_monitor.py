#!/usr/bin/env python3
import docker
import time
import csv
import sys
import os
import argparse

def main():
    parser = argparse.ArgumentParser(description='Monitor network traffic between containers')
    parser.add_argument('--streamer', required=True, help='Streamer container name')
    parser.add_argument('--hpe', required=True, help='HPE container name')
    parser.add_argument('--output', default='/results/network.csv', help='Output CSV file path')
    parser.add_argument('--duration', type=int, default=30, help='Duration in seconds')
    parser.add_argument('--interval', type=float, default=0.1, help='Polling interval in seconds')
    args = parser.parse_args()

    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    
    # Connect to Docker
    try:
        client = docker.from_env()
        hpe = client.containers.get(args.hpe)
    except Exception as e:
        print(f"ERROR: Failed to connect to Docker or find HPE container: {str(e)}", file=sys.stderr)
        sys.exit(1)
    
    # Initialize CSV
    with open(args.output, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['msecond', 'json_bytes'])
        
        # Initialize previous values
        prev_rx = 0
        
        start_time = time.time()
        while time.time() - start_time < args.duration:
            try:
                # Get current stats
                stats = hpe.stats(stream=False)
                current_rx = stats["networks"]["eth0"]["rx_bytes"]
                
                # Calculate timestamp in seconds with 2 decimal places (matching your data format)
                timestamp = time.time()
                timestamp_str = f"{timestamp:.2f}"
                
                # Calculate delta (bytes received since last measurement)
                rx_delta = current_rx - prev_rx
                
                # Write to CSV
                writer.writerow([timestamp_str, rx_delta])
                f.flush()
                
                # Update previous values
                prev_rx = current_rx
                
                # Sleep to maintain interval (with drift correction)
                time.sleep(args.interval)
                
            except Exception as e:
                print(f"ERROR: Monitoring failed: {str(e)}", file=sys.stderr)
                time.sleep(1)  # Avoid tight loop on error

if __name__ == "__main__":
    main()
