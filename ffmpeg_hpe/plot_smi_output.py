# Minimal plotting script for GPU metrics
import sys
import pandas as pd
import matplotlib.pyplot as plt

def main(csv_path):
    df = pd.read_csv(csv_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    plt.figure(figsize=(15, 5))
    plt.plot(df['timestamp'], df['utilization.gpu'], label='GPU Utilization')
    plt.plot(df['timestamp'], df['temperature.gpu'], label='GPU Temp (C)')
    plt.legend()
    plt.title('GPU Metrics Over Time')
    plt.xlabel('Time')
    plt.grid(True)
    plt.savefig(csv_path.replace('.csv', '.png'))
    print('Plot saved')

if __name__ == '__main__':
    main(sys.argv[1])
