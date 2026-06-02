import matplotlib
matplotlib.use('Agg')
import pandas as pd
import matplotlib.pyplot as plt
import os
import sys


def plot_metrics(pid_csv, rx_csv):
    try:
        # Read and validate pid_metrics CSV
        df_pid = pd.read_csv(pid_csv)
        required_pid_cols = {'timestamp', 'cpu_percent', 'mem_rss_kb'}
        missing = required_pid_cols - set(df_pid.columns)
        if missing:
            print('Error: {} is missing columns: {}'.format(pid_csv, missing), file=sys.stderr)
            sys.exit(1)
        if df_pid.empty:
            print('Error: {} is empty'.format(pid_csv), file=sys.stderr)
            sys.exit(1)
        df_pid['timestamp'] = pd.to_numeric(df_pid['timestamp'], errors='coerce')
        df_pid = df_pid.dropna(subset=['timestamp'])
        if df_pid.empty:
            print('Error: {} has no valid timestamp rows'.format(pid_csv), file=sys.stderr)
            sys.exit(1)

        # Compute elapsed seconds from first timestamp
        t0_pid = df_pid['timestamp'].iloc[0]
        df_pid['elapsed'] = df_pid['timestamp'] - t0_pid

        # Read and validate hpe_video_rx CSV
        df_rx = pd.read_csv(rx_csv)
        required_rx_cols = {'timestamp', 'rx_bytes'}
        # Accept the actual column name used in the CSV (timestamp_ms or timestamp)
        if 'timestamp_ms' in df_rx.columns and 'timestamp' not in df_rx.columns:
            df_rx = df_rx.rename(columns={'timestamp_ms': 'timestamp'})
        if 'rx_video_bytes_delta' in df_rx.columns and 'rx_bytes' not in df_rx.columns:
            df_rx = df_rx.rename(columns={'rx_video_bytes_delta': 'rx_bytes'})
        missing = {'timestamp', 'rx_bytes'} - set(df_rx.columns)
        if missing:
            print('Error: {} is missing columns: {}'.format(rx_csv, missing), file=sys.stderr)
            sys.exit(1)
        if df_rx.empty:
            print('Error: {} is empty'.format(rx_csv), file=sys.stderr)
            sys.exit(1)
        df_rx['timestamp'] = pd.to_numeric(df_rx['timestamp'], errors='coerce')
        df_rx = df_rx.dropna(subset=['timestamp'])
        if df_rx.empty:
            print('Error: {} has no valid timestamp rows'.format(rx_csv), file=sys.stderr)
            sys.exit(1)

        t0_rx = df_rx['timestamp'].iloc[0]
        df_rx['elapsed'] = df_rx['timestamp'] - t0_rx

        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(15, 12))

        # Subplot 1: CPU usage
        ax1.plot(df_pid['elapsed'], df_pid['cpu_percent'], label='CPU Usage')
        ax1.set_title('CPU Usage Over Time')
        ax1.set_ylabel('CPU Usage (%)')
        ax1.set_xlabel('Elapsed Time (s)')
        ax1.grid(True)
        ax1.legend()

        # Subplot 2: Memory usage
        ax2.plot(df_pid['elapsed'], df_pid['mem_rss_kb'] / 1024, label='Memory Usage')
        ax2.set_title('Memory Usage Over Time')
        ax2.set_ylabel('Memory Usage (MB)')
        ax2.set_xlabel('Elapsed Time (s)')
        ax2.grid(True)
        ax2.legend()

        # Subplot 3: RX bytes
        ax3.plot(df_rx['elapsed'], df_rx['rx_bytes'], label='RX Bytes', color='tab:green')
        ax3.set_title('RX Bytes Over Time')
        ax3.set_ylabel('RX Bytes')
        ax3.set_xlabel('Elapsed Time (s)')
        ax3.grid(True)
        ax3.legend()

        plt.suptitle('ffmpeg_hpe Monitoring Metrics - {}'.format(os.path.basename(pid_csv)))
        plt.tight_layout()

        output_file = os.path.splitext(pid_csv)[0] + '.png'
        plt.savefig(output_file)
        print('Saved plot to: {}'.format(output_file))
    except FileNotFoundError as e:
        print('Error: {}'.format(e), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print('Error plotting metrics: {}'.format(e), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python plot_graph.py <pid_metrics_csv> <hpe_video_rx_csv>", file=sys.stderr)
        sys.exit(1)

    pid_metrics_csv = sys.argv[1]
    hpe_video_rx_csv = sys.argv[2]

    plot_metrics(pid_metrics_csv, hpe_video_rx_csv)
