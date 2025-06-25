import subprocess
import matplotlib.pyplot as plt
import numpy as np
import re
import os
from datetime import datetime
import pandas as pd

def create_output_directory():
    # Create a directory with current datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f"cpu_test_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)
    return output_dir

def capture_perf_data():
    # Run the perf command WITHOUT stress-ng
    cmd = ["sudo", "perf", "stat", "-a", "-e", "cpu-clock,cycles", 
           "-I", "100", "--interval-count", "100", "-x", ","]
    
    try:
        # Use check_output to capture stderr instead of stdout
        result = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
        print("Raw output:")
        print(result)
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error running perf: {e}")
        return e.output

def parse_perf_output(output):
    # Initialize data structures
    data = {
        'time': [],
        'cpu_clock': [],
        'cycles': [],
        'cpu_util': []
    }
    
    # Split output into lines
    lines = output.split('\n')
    
    # Process lines in pairs (cpu-clock and cycles)
    for i in range(0, len(lines), 2):
        try:
            # Get the cpu-clock line
            clock_line = lines[i].strip()
            clock_parts = clock_line.split(',')
            
            # Skip if not enough parts
            if len(clock_parts) < 6:
                continue
                
            # Extract time and cpu-clock
            time = float(clock_parts[0])
            cpu_clock = float(clock_parts[1])
            cpu_util = float(clock_parts[4].strip('%'))
            
            # Get the cycles line
            cycles_line = lines[i + 1].strip()
            cycles_parts = cycles_line.split(',')
            
            # Skip if not enough parts
            if len(cycles_parts) < 6:
                continue
                
            # Extract cycles
            cycles = float(cycles_parts[1])
            
            # Add to data
            data['time'].append(time)
            data['cpu_clock'].append(cpu_clock)
            data['cycles'].append(cycles)
            data['cpu_util'].append(cpu_util)
            
        except (IndexError, ValueError) as e:
            print(f"Warning: Failed to parse line {i}: {str(e)}")
            continue
    
    # Print some debug info
    print(f"Parsed {len(data['time'])} data points")
    if len(data['time']) > 0:
        print(f"First time point: {data['time'][0]}")
        print(f"Last time point: {data['time'][-1]}")
        print(f"First cycles: {data['cycles'][0]}")
        print(f"Last cycles: {data['cycles'][-1]}")
    
    return data

def plot_metrics(data, output_dir):
    # Create subplots
    fig, axs = plt.subplots(1, 2, figsize=(15, 5))
    fig.suptitle('Performance Metrics Over Time')
    
    # Plot CPU Utilization
    axs[0].plot(data['time'], data['cpu_util'])
    axs[0].set_title('CPU Utilization')
    axs[0].set_xlabel('Time (s)')
    axs[0].set_ylabel('Utilization')
    
    # Plot Cycles
    axs[1].plot(data['time'], data['cycles'])
    axs[1].set_title('Cycles')
    axs[1].set_xlabel('Time (s)')
    axs[1].set_ylabel('Cycles')
    
    # Save the main plot
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'performance_metrics.png'))
    plt.close()
    
    # Save the raw data as CSV
    df = pd.DataFrame(data)
    df.to_csv(os.path.join(output_dir, 'perf_data.csv'), index=False)
    
    print(f"Results saved in directory: {output_dir}")
    print("Files saved:")
    print("- performance_metrics.png (main metrics)")
    print("- perf_data.csv (raw data)")

if __name__ == "__main__":
    # Create output directory
    output_dir = create_output_directory()
    
    # Capture the data
    output = capture_perf_data()
    
    # Parse the data
    data = parse_perf_output(output)
    
    # Plot the data
    plot_metrics(data, output_dir)

if __name__ == "__main__":
    # Create output directory
    output_dir = create_output_directory()
    
    # Capture the data
    output = capture_perf_data()
    
    # Parse the data
    data = parse_perf_output(output)
    
    # Plot the data
    plot_metrics(data, output_dir)
