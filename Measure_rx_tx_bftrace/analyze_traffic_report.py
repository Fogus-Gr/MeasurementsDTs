import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Load traffic report data
df = pd.read_csv('results_20250606_102926/traffic_report.csv')

# Convert timestamp to datetime
df['Timestamp'] = pd.to_datetime(df['Timestamp'])

# Print time range for debugging
print("\nData Time Range:")
print(f"Start time: {df['Timestamp'].min()}")
print(f"End time: {df['Timestamp'].max()}")
print(f"Number of unique time points: {df['Timestamp'].nunique()}")

# Set Timestamp as index
df.set_index('Timestamp', inplace=True)

# Resample to 100ms bins (change '100ms' to '10ms' or '1s' as needed)
df_rx = df[df['Type'] == 'RX'].resample('100ms').agg({'Bytes': 'sum'}).rename(columns={'Bytes': 'rx_bytes'})
df_tx = df[df['Type'] == 'TX'].resample('100ms').agg({'Bytes': 'sum'}).rename(columns={'Bytes': 'tx_bytes'})

# Merge RX and TX on Timestamp
df_plot = pd.merge(df_rx, df_tx, left_index=True, right_index=True, how='outer').fillna(0)

# Reset index for plotting
df_plot = df_plot.reset_index()

# Convert bytes to MB
df_plot['rx_bytes'] = df_plot['rx_bytes'] / (1024 * 1024)
df_plot['tx_bytes'] = df_plot['tx_bytes'] / (1024 * 1024)

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
