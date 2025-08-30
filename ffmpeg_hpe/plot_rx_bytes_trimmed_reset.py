import matplotlib.pyplot as plt
import pandas as pd

# resets the x-axis to start from zero after trimming


# Path to your CSV file
csv_path = "/home/user/MeasurementsDTs/ffmpeg_hpe/results_alphapose_AMD_EPYC_7551P_32-Core_Processor_20250711_142932/traces/bcc/video_rx.csv"

# Read the CSV (skip header, handle extra columns if present)
df = pd.read_csv(csv_path)

# Trim to start from the first nonzero RX interval
first_nonzero = df.iloc[:,1].ne(0).idxmax()
print(f"Trimming {first_nonzero} rows. First nonzero RX bytes at row {first_nonzero}.")
df = df.loc[first_nonzero:].reset_index(drop=True)

# Reset x-axis to start from zero
df.iloc[:,0] = df.iloc[:,0] - df.iloc[0,0]

# Plot
plt.figure(figsize=(15,5))
plt.plot(df.iloc[:,0], df.iloc[:,1], drawstyle='steps-post')
plt.xlabel("Time since first RX (ms)")
plt.ylabel("RX bytes per 10ms")
plt.title("Per-10ms RX Traffic (Trimmed, Time Zeroed)")
plt.tight_layout()
plt.savefig("rx_bytes_plot.png")
# plt.show()  # Do not display, only save
