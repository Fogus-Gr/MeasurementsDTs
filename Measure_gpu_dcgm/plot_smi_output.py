import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# Load data (adjust path if needed)
data = []
with open('double_trouble.txt', 'r') as f:
    lines = f.readlines()[3:]  # Skip headers
    for line in lines:
        parts = line.strip().split(', ')
        if len(parts) < 8:
            continue
        timestamp = datetime.strptime(parts[0], '%Y/%m/%d %H:%M:%S.%f')
        pstate = parts[1]
        temp = int(parts[2])
        gpu_util = int(parts[3].replace(' %', ''))
        mem_util = int(parts[4].replace(' %', ''))
        mem_total = int(parts[5].replace(' MiB', ''))
        mem_free = int(parts[6].replace(' MiB', ''))
        mem_used = int(parts[7].replace(' MiB', ''))
        data.append([timestamp, pstate, temp, gpu_util, mem_util, mem_total, mem_free, mem_used])

df = pd.DataFrame(data, columns=['timestamp', 'pstate', 'temp', 'gpu_util', 'mem_util', 'mem_total', 'mem_free', 'mem_used'])

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
plt.show()

# Plot Temperature
plt.figure(figsize=(12, 4))
plt.plot(df['timestamp'], df['temp'], label='GPU Temp (°C)', color='orange')
plt.title('GPU Temperature Over Time')
plt.xlabel('Time')
plt.ylabel('Temperature (°C)')
plt.grid()
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

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
plt.show()

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
plt.show()