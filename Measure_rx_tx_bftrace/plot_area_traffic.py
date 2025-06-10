"""
plot_area_traffic.py

This script reads a CSV file containing timestamped network traffic data (RX/TX bytes)
from iperf3, aggregates the data into time bins (default: 1s, can be changed), and
plots a filled area chart (like Docker stats) showing received and sent data over time.

Usage:
    python3 plot_area_traffic.py

You can adjust the resample_interval (e.g., '10ms', '100ms', '1s') for different time resolutions.
"""

import pandas as pd
import matplotlib.pyplot as plt

def plot_area_traffic(csv_file, resample_interval='1s'):
    # Read CSV and filter for iperf traffic
    df = pd.read_csv(csv_file)
    df = df[df['Command'].str.contains('iperf', case=False)]

    if df.empty:
        print("No iperf data to plot.")
        return

    # Convert 'Timestamp' to datetime and set as index for resampling
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    df.set_index('Timestamp', inplace=True)

    print("Data after filtering:")
    print(df.head())
    print("Data range:", df.index.min(), df.index.max())

    # Convert Bytes to KB for easier interpretation
    df['KBytes'] = df['Bytes'] / 1024

    # Resample RX and TX data by the chosen interval and sum bytes in each bin
    rx = df[df['Type'] == 'RX'].resample(resample_interval)['KBytes'].sum()
    tx = df[df['Type'] == 'TX'].resample(resample_interval)['KBytes'].sum()

    # Combine RX and TX into one DataFrame for plotting
    traffic = pd.DataFrame({'Data received': rx, 'Data sent': tx}).fillna(0)

    print("Traffic after resample:")
    print(traffic.head())
    print(traffic.tail())

    # Plot as a filled area (stacked) chart
    plt.figure(figsize=(10, 5))
    plt.stackplot(
        traffic.index,
        traffic['Data received'],
        traffic['Data sent'],
        labels=['Data received', 'Data sent'],
        colors=['#8B4513', '#4B0082'],
        alpha=0.6
    )
    plt.legend(loc='upper left')
    plt.ylabel('KB')
    plt.xlabel('Time')
    plt.title('Network I/O')
    plt.xticks(rotation=30)
    plt.tight_layout()
    plt.savefig('traffic_area_plot.png')
    plt.show()

if __name__ == "__main__":
    # You can change the resample_interval for finer or coarser bins
    plot_area_traffic('results_20250606_102926/traffic_report.csv', resample_interval='10ms')