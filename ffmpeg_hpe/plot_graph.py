# Copy of plot_graph.py from monitor_hpe
# This script is used for plotting experiment results

import sys
import pandas as pd
import matplotlib.pyplot as plt

def main(csv_path):
    df = pd.read_csv(csv_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
    plt.figure(figsize=(15, 5))
    plt.plot(df['timestamp'], df['cpu_percent'])
    plt.title('CPU Usage Over Time')
    plt.ylabel('CPU %')
    plt.grid(True)
    out_path = csv_path.replace('.csv', '.png')
    plt.savefig(out_path)
    print(f'Plot saved to {out_path}')

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python plot_graph.py <csv_file>')
        sys.exit(1)
    main(sys.argv[1])
