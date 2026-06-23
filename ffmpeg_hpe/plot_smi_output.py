# Minimal plotting script for GPU metrics
import sys
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

def main(csv_path):
    df = pd.read_csv(csv_path)
    # The timestamp is a float (seconds since epoch)
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
    plt.figure(figsize=(15, 5))
    plt.plot(df['timestamp'], df['gpu_utilization'], label='GPU Utilization', marker='.')
    plt.plot(df['timestamp'], df['temperature'], label='GPU Temp (C)', marker='.')
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    plt.legend()
    plt.title('GPU Metrics Over Time')
    plt.xlabel('Time')
    plt.grid(True)
    plt.savefig(csv_path.replace('.csv', '.png'))
    print('Plot saved')

if __name__ == '__main__':
    main(sys.argv[1])
