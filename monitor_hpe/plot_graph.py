import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os
import sys
from datetime import datetime

# Read CSV file from command line argument
def plot_metrics(csv_file):
    # Read CSV file
    df = pd.read_csv(csv_file)
    
    # Convert timestamp to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
    
    # Create figure with two subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), sharex=True)
    
    # Plot CPU usage
    ax1.plot(df['timestamp'], df['cpu_percent'], label='CPU Usage')
    ax1.set_title('CPU Usage Over Time')
    ax1.set_ylabel('CPU Usage (%)')
    ax1.grid(True)
    ax1.legend()
    
    # Plot Memory usage
    ax2.plot(df['timestamp'], df['mem_rss_kb'] / 1024, label='Memory Usage')
    ax2.set_title('Memory Usage Over Time')
    ax2.set_ylabel('Memory Usage (MB)')
    ax2.grid(True)
    ax2.legend()
    
    # Format x-axis dates
    plt.gcf().autofmt_xdate()
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    
    # Add title with filename
    plt.suptitle(f'Monitoring Metrics - {os.path.basename(csv_file)}')
    
    # Save plot as PNG in the same directory
    output_file = os.path.splitext(csv_file)[0] + '.png'
    plt.savefig(output_file)
    print(f"Saved plot to: {output_file}")
    
    # Show plot
    plt.show()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python plot_graph.py <csv_file>")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    if not os.path.exists(csv_file):
        print(f"Error: File not found: {csv_file}")
        sys.exit(1)
    
    plot_metrics(csv_file)
