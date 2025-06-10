import pandas as pd
import matplotlib.pyplot as plt

def plot_traffic(csv_file, resample_interval='100ms'):
    df = pd.read_csv(csv_file)
    df = df[df['Command'].str.contains('iperf', case=False)]

    if df.empty:
        print("No iperf data to plot.")
        return

    # Convert timestamp to datetime and set as index
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    df.set_index('Timestamp', inplace=True)

    # Convert Bytes to MB
    df['MBytes'] = df['Bytes'] / (1024 * 1024)

    # Resample by interval (e.g., 100ms)
    rx = df[df['Type'] == 'RX'].resample(resample_interval)['MBytes'].sum()
    tx = df[df['Type'] == 'TX'].resample(resample_interval)['MBytes'].sum()

    plt.figure(figsize=(16, 7), dpi=120)
    plt.plot(rx.index, rx.values, label='RX (MB)', marker='o', linewidth=2)
    if not tx.empty:
        plt.plot(tx.index, tx.values, label='TX (MB)', marker='s', linewidth=2)

    plt.xlabel('Time')
    plt.ylabel('Traffic (MB per interval)')
    plt.title(f'Network Traffic (RX/TX) for iperf3 [{resample_interval} bins]')
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('traffic_plot.png')
    plt.show()

if __name__ == "__main__":
    plot_traffic('traffic_report.csv', resample_interval='100ms')