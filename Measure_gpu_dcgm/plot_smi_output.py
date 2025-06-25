import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import sys
import os

'''
This script plots the output of nvidia-smi in CSV format.
It expects the CSV file to have the following columns:
timestamp, pstate, temp, gpu_util, mem_util, mem_total, mem_free, mem_used, power
'''

csv_file = sys.argv[1] if len(sys.argv) > 1 else "gpu_stats.csv"

# Create results directory with timestamp
run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
results_dir = f"results_{run_timestamp}"
os.makedirs(results_dir, exist_ok=True)

# Load data (adjust path if needed)
data = []
with open(csv_file, 'r') as f:
    lines = f.readlines()[3:]  # Skip headers
    for line in lines:
        parts = line.strip().split(', ')
        if len(parts) < 9:
            continue
        timestamp = datetime.strptime(parts[0], '%Y/%m/%d %H:%M:%S.%f')
        pstate = parts[1]
        power = float(parts[2].replace(' W', ''))
        temp = int(parts[3])
        gpu_util = int(parts[4].replace(' %', ''))
        mem_util = int(parts[5].replace(' %', ''))
        mem_total = int(parts[6].replace(' MiB', ''))
        mem_free = int(parts[7].replace(' MiB', ''))
        mem_used = int(parts[8].replace(' MiB', ''))
        data.append([timestamp, pstate, temp, gpu_util, mem_util, mem_total, mem_free, mem_used, power])

df = pd.DataFrame(data, columns=['timestamp', 'pstate', 'temp', 'gpu_util', 'mem_util', 'mem_total', 'mem_free', 'mem_used', 'power'])

# Plot GPU and Memory Utilization
plt.figure(figsize=(12, 5))
plt.plot(df['timestamp'], df['gpu_util'], label='GPU Utilization (%)', color='blue')
plt.plot(df['timestamp'], df['mem_util'], label='Memory Utilization (%)', color='red')
plt.title('GPU and Memory Utilization Over Time')
plt.xlabel('Time')
plt.ylabel('Utilization (%)')
plt.legend()
plt.grid()
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig(os.path.join(results_dir, 'gpu_util.png'))
plt.close()

# Plot Temperature
plt.figure(figsize=(12, 4))
plt.plot(df['timestamp'], df['temp'], label='GPU Temp (°C)', color='orange')
plt.title('GPU Temperature Over Time')
plt.xlabel('Time')
plt.ylabel('Temperature (°C)')
plt.grid()
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig(os.path.join(results_dir, 'gpu_temp.png'))
plt.close()

# Plot Memory Usage
plt.figure(figsize=(12, 4))
plt.plot(df['timestamp'], df['mem_used'], label='Used Memory (MiB)', color='purple')
plt.plot(df['timestamp'], df['mem_free'], label='Free Memory (MiB)', color='green')
plt.title('GPU Memory Usage Over Time')
plt.xlabel('Time')
plt.ylabel('Memory (MiB)')
plt.legend()
plt.grid()
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig(os.path.join(results_dir, 'gpu_mem.png'))
plt.close()

# Plot Power States
pstate_map = {'P0': 0, 'P2': 2, 'P5': 5, 'P8': 8}
df['pstate_num'] = df['pstate'].map(pstate_map)
plt.figure(figsize=(12, 3))
plt.step(df['timestamp'], df['pstate_num'], where='post', color='black')
plt.title('GPU Power State (P-State) Over Time')
plt.xlabel('Time')
plt.ylabel('P-State')
plt.yticks([0, 2, 5, 8], ['P0 (Max Perf)', 'P2', 'P5', 'P8 (Idle)'])
plt.grid()
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig(os.path.join(results_dir, 'gpu_pstate.png'))
plt.close()

# Plot Power Consumption
plt.figure(figsize=(12, 4))
plt.plot(df['timestamp'], df['power'], label='Power Draw (W)', color='magenta')
plt.title('GPU Power Consumption Over Time')
plt.xlabel('Time')
plt.ylabel('Power (Watts)')
plt.grid()
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig(os.path.join(results_dir, 'gpu_power.png'))
plt.close()