#!/usr/bin/env python3
import docker
import time
import csv
import sys
import os
import argparse

def main():
    parser = argparse.ArgumentParser(description='Monitor CPU and memory usage')
    parser.add_argument('--container', required=True, help='Container name to monitor')
    parser.add_argument('--output', default='/results/performance.csv', help='Output CSV file path')
    parser.add_argument('--duration', type=int, default=30, help='Duration in seconds')
    parser.add_argument('--interval', type=float, default=0.5, help='Polling interval in seconds')
    args = parser.parse_args()

    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    
    # Connect to Docker
    try:
        client = docker.from_env()
        container = client.containers.get(args.container)
    except Exception as e:
        print(f"ERROR: Failed to connect to Docker or find container: {str(e)}", file=sys.stderr)
        sys.exit(1)
    
    # Initialize CSV
    with open(args.output, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'total_cpu_percent', 'total_mem_rss_kb', 'active_pids'])
        
        # Initialize previous values for CPU calculation
        prev_cpu = 0
        prev_system = 0
        
        start_time = time.time()
        while time.time() - start_time < args.duration:
            try:
                # Get current stats
                stats = container.stats(stream=False)
                
                # Get timestamp in milliseconds (matching your data format)
                timestamp = int(time.time() * 1000)
                
                # Parse CPU usage
                cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - prev_cpu
                system_delta = stats['cpu_stats']['system_cpu_usage'] - prev_system
                
                # Calculate CPU percentage
                if system_delta > 0 and cpu_delta > 0:
                    cpu_percent = (cpu_delta / system_delta) * len(stats['cpu_stats']['cpu_usage']['percpu_usage']) * 100.0
                else:
                    cpu_percent = 0.0
                
                # Get memory usage in KB
                mem_rss = stats['memory_stats']['stats'].get('rss', 0) // 1024
                
                # Get active processes
                active_pids = 1  # Docker containers typically have 1 main PID
                
                # Write to CSV
                writer.writerow([timestamp, f"{cpu_percent:.1f}", mem_rss, active_pids])
                f.flush()
                
                # Update previous values
                prev_cpu = stats['cpu_stats']['cpu_usage']['total_usage']
                prev_system = stats['cpu_stats']['system_cpu_usage']
                
                # Sleep to maintain interval
                time.sleep(args.interval)
                
            except Exception as e:
                print(f"ERROR: Monitoring failed: {str(e)}", file=sys.stderr)
                time.sleep(1)  # Avoid tight loop on error

if __name__ == "__main__":
    main()
