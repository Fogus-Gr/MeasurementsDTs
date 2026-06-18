import os
import sys

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd


def plot_metrics(csv_file):
    df = pd.read_csv(csv_file)
    if "timestamp" not in df.columns:
        raise ValueError("CSV must include a timestamp column")

    timestamp = pd.to_numeric(df["timestamp"], errors="coerce")
    unit = "ms" if timestamp.dropna().median() > 100000000000 else "s"
    df["timestamp"] = pd.to_datetime(timestamp, unit=unit)

    if {"total_cpu_percent", "total_mem_rss_kb"}.issubset(df.columns):
        cpu_col = "total_cpu_percent"
        mem_col = "total_mem_rss_kb"
    elif {"cpu_percent", "mem_rss_kb"}.issubset(df.columns):
        cpu_col = "cpu_percent"
        mem_col = "mem_rss_kb"
    else:
        raise ValueError("CSV must include CPU and RSS memory columns")

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 9), sharex=True)

    ax1.plot(df["timestamp"], df[cpu_col], label="CPU")
    ax1.set_title("CPU Usage Over Time")
    ax1.set_ylabel("CPU (%)")
    ax1.grid(True)
    ax1.legend()

    ax2.plot(df["timestamp"], df[mem_col] / 1024, label="Memory")
    ax2.set_title("Memory Usage Over Time")
    ax2.set_ylabel("Memory (MB)")
    ax2.grid(True)
    ax2.legend()
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))

    fig.autofmt_xdate()
    fig.suptitle("Monitoring Metrics - {}".format(os.path.basename(csv_file)))
    fig.tight_layout()

    output_file = os.path.splitext(csv_file)[0] + ".png"
    fig.savefig(output_file)
    print("Saved plot to: {}".format(output_file))

    if os.environ.get("DISPLAY"):
        plt.show()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 plot_graph.py <csv_file>")
        sys.exit(1)

    plot_metrics(sys.argv[1])
