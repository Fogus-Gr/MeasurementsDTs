import matplotlib.pyplot as plt
import pandas as pd
import sys
import os

# Trims to first nonzero RX interval and resets x-axis to start from zero

if len(sys.argv) < 2:
    print("Usage: python3 plot_rx_bytes_trimmed_reset.py <path/to/hpe_video_rx.csv>")
    sys.exit(1)

csv_path = sys.argv[1]
if not os.path.exists(csv_path):
    print(f"File not found: {csv_path}")
    sys.exit(1)

# Read the CSV
df = pd.read_csv(csv_path)

# Trim to start from the first nonzero RX interval
first_nonzero = df.iloc[:,1].ne(0).idxmax()
print(f"Trimming {first_nonzero} rows. First nonzero RX bytes at row {first_nonzero}.")
df = df.loc[first_nonzero:].reset_index(drop=True)

# Reset x-axis to start from zero
df.iloc[:,0] = df.iloc[:,0] - df.iloc[0,0]

# Plot
out_path = os.path.join(os.path.dirname(csv_path), "rx_bytes_trimmed_reset_plot.png")
plt.figure(figsize=(15,5))
plt.plot(df.iloc[:,0], df.iloc[:,1], drawstyle='steps-post')
plt.xlabel("Time since first RX (ms)")
plt.ylabel("RX bytes per 10ms")
plt.title("Per-10ms RX Traffic (Trimmed, Time Zeroed)")
plt.tight_layout()
plt.savefig(out_path)
print(f"Saved: {out_path}")
