import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Load traffic report data
df = pd.read_csv('results_20250606_095029/traffic_report.csv')

# Convert timestamp to datetime
df['Timestamp'] = pd.to_datetime(df['Timestamp'])

# Print time range for debugging
print("\nData Time Range:")
print(f"Start time: {df['Timestamp'].min()}")
print(f"End time: {df['Timestamp'].max()}")
print(f"Number of unique time points: {df['Timestamp'].nunique()}")

# Separate RX and TX data
df_rx = df[df['Type'] == 'RX'].copy()
df_tx = df[df['Type'] == 'TX'].copy()

# Group by actual timestamp to get total bytes per timestamp
df_rx = df_rx.groupby('Timestamp')['Bytes'].sum().reset_index()
df_tx = df_tx.groupby('Timestamp')['Bytes'].sum().reset_index()

# Convert bytes to MB for better readability
df_rx['rx_bytes'] = df_rx['Bytes'] / (1024 * 1024)
df_tx['tx_bytes'] = df_tx['Bytes'] / (1024 * 1024)

# Merge RX and TX data on Timestamp
df_plot = pd.merge(df_rx[['Timestamp', 'rx_bytes']], df_tx[['Timestamp', 'tx_bytes']], on='Timestamp', how='outer').fillna(0)

# Plot RX and TX traffic over actual time
plt.style.use('seaborn')
plt.figure(figsize=(16, 7))
plt.plot(df_plot['Timestamp'], df_plot['rx_bytes'], label='RX Traffic', marker='o')
plt.plot(df_plot['Timestamp'], df_plot['tx_bytes'], label='TX Traffic', marker='s')
plt.title('Network Traffic Over Time')
plt.xlabel('Time')
plt.ylabel('MB per sample')
plt.legend()
plt.grid(True, linestyle='--', alpha=0.6)
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('traffic_over_time.png')
plt.show()

# Box plot of traffic distribution
plt.figure(figsize=(12, 6))
sns.boxplot(data=df_plot[['rx_bytes', 'tx_bytes']])
plt.title('Traffic Distribution')
plt.ylabel('MB per sample')
plt.savefig('traffic_distribution.png')
plt.close()

# Create summary statistics
stats = df_plot[['rx_bytes', 'tx_bytes']].describe()
stats.to_csv('traffic_stats.csv')

# Print basic statistics
print("\nNetwork Traffic Statistics:")
print("Total RX Traffic: {:.2f} GB".format(df_plot['rx_bytes'].sum() / 1024))
print("Total TX Traffic: {:.2f} GB".format(df_plot['tx_bytes'].sum() / 1024))
print("Average RX Rate: {:.2f} MB/sample".format(df_plot['rx_bytes'].mean()))
print("Average TX Rate: {:.2f} MB/sample".format(df_plot['tx_bytes'].mean()))
