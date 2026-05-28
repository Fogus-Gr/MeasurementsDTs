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

---

## Resolution Analysis (May 2026)

**Status: RESOLVED** — This report is obsolete. All issues described here were caused by a combination of a pre-RTSP streaming architecture and a disabled BPF filter, both of which have since been fixed.

### Root Cause Identification

**Branch and date context:** This report was written on the `cuda-dev` branch on July 6 2025, during the HTTP streaming phase of the project. The companion document `AlphaPose_HTTP_Streaming_Optimization.md` confirms the setup at the time: FFmpeg pushing `-c:v copy -f mpegts` over HTTP to a custom server, with AlphaPose consuming it via `http://<host>:8089/stream.h264`.

Every problem described in this report maps to a specific bug or architectural decision that has since been addressed:

| Original complaint | Actual root cause | Fix |
|---|---|---|
| bpftrace undercounting (~339 MB vs ~420 MB TX) | Bug #1 — the IP/port BPF filter in `bcc_rx_bytes.py` was **disabled**, so it was counting all TCP traffic indiscriminately, not just the video stream. The 339 MB figure is unreliable for a different reason than this report guessed. | Re-enabled in commit `256a21c` |
| "bpftrace may start late or end early" | The entrypoint did not wait for HPE to establish its RTSP connection before attaching the socket filter | Fixed: `entrypoint.sh` now runs `detect_hpe_port()` with a retry loop before starting the tracer |
| "Docker stats are the most comprehensive measurement" | This was the correct workaround at the time, before `bcc-tracer` was working correctly | Superseded: `hpe_video_rx.csv` from `bcc-tracer` is now the authoritative RX source. Docker stats are no longer needed for this purpose. |
| HTTP/MPEG-TS streaming architecture | The entire transport layer was HTTP-based, which introduced its own framing and connection-management complexity | Replaced: the full stack was migrated to RTSP/MediaMTX + NVENC in `feat/rtsp-mediamtx-migration`, which is what `ffmpeg_hpe/` uses today |

### The 833 MB vs 420 MB Discrepancy Explained

The report did not identify the most likely cause of the 833 MB → 420 MB drop. `-c:v copy -f mpegts` remuxes the MP4 into an MPEG-TS container — it does not stream the MP4 file byte-for-byte. The MP4 container includes a `moov` atom (metadata) and `mdat` atom (media data), while MPEG-TS uses fixed 188-byte transport stream packets. The resulting stream size depends on the actual encoded video bitrate, not the file size. A 833 MB MP4 at a high container overhead ratio can easily produce a ~420 MB MPEG-TS stream. This is expected behaviour, not a measurement error.

The 339 MB bpftrace figure being lower than 420 MB TX is explained by the disabled IP/port filter: the filter was not counting all video stream packets, producing an undercount unrelated to payload vs. wire-byte differences.

### Current Authoritative Measurement Approach

The tcpdump/tshark approach proposed in the "Steps" section above is superseded. The current setup provides equivalent functionality without the overhead of writing a full pcap to disk:

- **RX bytes:** `traces/bcc/hpe_video_rx.csv` — produced by `bcc_rx_bytes.py` with the IP/port BPF filter active, polling at 10ms intervals, measuring wire bytes (Ethernet frame length including all protocol headers, ~4% overhead above pure video payload — consistent across all runs and therefore valid for relative comparisons).
- **TX bytes:** `network_stats.csv` from `perf_monitor` — produced by `bpftrace sys_enter_sendto`, PID-filtered to the HPE process.
- **Never use** the RX column from `network_stats.csv` — it uses `netif_receive_skb` which fires in softirq context and always reads ~0 (known open issue #12).
