# Report on RX/TX Traffic Discrepancy

## Overview

You are streaming a video file (833 MB, H.264, 1920x1080, 5:07 duration) from a container using a direct HTTP server with FFmpeg and `-c:v copy -f mpegts`. The goal is to have the RX bytes in the HPE container match the original file size as closely as possible.

## Observed Data

- **Original video file size:** 833 MB
- **Docker stats (TX from streaming container):** ~420 MB
- **bpftrace trace.csv (RX in HPE container):** ~339 MB

## What Each Measurement Means

| Source                | What it measures                        | Value   |
|-----------------------|-----------------------------------------|---------|
| Original MP4 file     | File size on disk                       | 833 MB  |
| Docker TX (streamer)  | All bytes sent (incl. overhead)         | 420 MB  |
| Docker RX (HPE)       | All bytes received (incl. overhead)     | ~420 MB |
| bpftrace trace.csv    | RX bytes (likely payload only, sampled) | 339 MB  |

## Why the Discrepancy?

### 1. Protocol and Container Overhead
- **HTTP, MPEG-TS, TCP/IP headers** add overhead to the network stream, but this should make TX/RX slightly higher than the original file, not lower.

### 2. bpftrace Script Limitations
- The bpftrace script may only count application payload bytes, not protocol overhead.
- It may miss some packets due to sampling, buffer overflows, or kernel filtering.
- If the script attaches to a specific kernel event, it may not see all traffic.
- If the script starts late or ends early, it will miss some traffic.

### 3. Partial Stream Consumption
- If AlphaPose or the HPE container does not read the entire stream (e.g., due to early exit, frame skipping, or errors), RX will be less than the original file size.
- If the client disconnects before the stream ends, the server may not send the entire file.

### 4. Docker Stats vs. bpftrace
- **Docker stats** are comprehensive and include all bytes sent/received by the container, including protocol overhead and retransmissions.
- **bpftrace** may undercount due to technical limitations or only counting payload bytes.

## How to Diagnose Further

- **Check streaming server logs:** Did it stream the entire file? Did the client disconnect early?
- **Check AlphaPose logs:** Did it process all frames? Did it exit early?
- **Compare the duration of the stream as seen by the HPE container** to the original video duration.
- **Try saving the stream to a file in the HPE container** (using `curl` or `ffmpeg`) and compare the file size to the original.

## Conclusion

- The streaming container is likely not at fault if it streams the whole file.
- The bpftrace script is likely undercounting due to kernel probe limitations or missing protocol overhead.
- AlphaPose or the HPE container may not be reading the entire stream if it exits early or skips frames.
- Docker stats are the most comprehensive measurement for total network traffic.

**For scientific proof, use Docker stats and ensure the client reads the entire stream.**


## Steps:

1) Install tcpdump in the hpe container (if not already present):
```shell
docker exec -it hpe apt-get update
docker exec -it hpe apt-get install -y tcpdump
```

2) Capture all RX packets on the main interface (e.g., eth0):

```shell
docker exec -it hpe tcpdump -i eth0 -w /output/hpe_rx.pcap
```

3) After the experiment, process the pcap file on the host:
```shell
tshark -r ./csv/hpe_rx.pcap -T fields -e frame.time_epoch -e frame.len > rx_times.csv
```
4) Summarize RX bytes per 10ms in Python:

This method **will show spikes** in RX traffic in your plot, and the CSV will feature timestamps suitable for plotting.

### Details:

- The `rx_times.csv` file contains one line per packet with:
  - **UNIX timestamp** (with sub-second precision, e.g., `1720701234.123456`)
  - **Packet length** (in bytes)

- The Python script bins these by 10ms intervals:
  - The `bin` column is essentially the UNIX timestamp in 10ms units (e.g., `int(timestamp * 100)`).
  - The output `rx_10ms.csv` will have the bin number and total bytes for each 10ms interval.

- **Spikes:**  
  If there is a burst of RX traffic in a particular 10ms window, the corresponding value in the CSV will be higher, and this will appear as a spike in your plot.

- **Timestamps:**  
  The bin numbers can be converted back to UNIX time by dividing by 100.  
  If you want the CSV to include the actual UNIX timestamp for each bin, you can modify the script:

```python
import pandas as pd
df = pd.read_csv('rx_times.csv', sep='\t', names=['time', 'len'])
df['time'] = df['time'].astype(float)
df['len'] = df['len'].astype(int)
df['bin'] = (df['time'] * 100).astype(int)  # 10ms bins
summary = df.groupby('bin')['len'].sum().reset_index()
summary['timestamp'] = summary['bin'] / 100  # UNIX timestamp in seconds
summary[['timestamp', 'len']].to_csv('rx_10ms.csv', index=False)
```
Now, `rx_10ms.csv` will have columns: `timestamp,len` (timestamp in seconds, bytes in 10ms).

---