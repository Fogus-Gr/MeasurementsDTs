# monitor_hpe — Usage Guide

## Overview

The `monitor_hpe` experiment rig measures baseline HPE inference performance with CPU/memory monitoring. It automatically configures resource allocation based on the HPE method being tested.

---

## Quick Start

### Basic Usage

```bash
cd monitor_hpe

# Run with default method (movenet) and default video
./run_experiment.sh

# Run with specific method
./run_experiment.sh movenet

# Run with specific method and video
./run_experiment.sh openpose rangeOfMotion/hd_00_00.mp4
```

---

## Automatic Resource Allocation

The script automatically configures CPU and memory allocation based on the HPE method:

### Lightweight Models (movenet, ae1, ae2, ae3)

```
CPU:    6 cores (reserved: 4 cores)
Memory: 6GB (reserved: 4GB)
OpenVINO Threads: 6
Device: CPU
```

**Rationale:** These models are lightweight and benefit from multi-threading without excessive memory usage.

### Heavy Models (hrnet)

```
CPU:    6 cores (reserved: 4 cores)
Memory: 9GB (reserved: 6GB)
OpenVINO Threads: 6
Device: CPU
```

**Rationale:** HigherHRNet requires more memory for larger feature maps.

### GPU Models (alphapose, openpose)

```
CPU:    4 cores (reserved: 2 cores)
Memory: 8GB (reserved: 6GB)
OpenVINO Threads: 4
Device: GPU
```

**Rationale:** GPU methods use less CPU but need more memory for GPU buffers.

---

## Resource Distribution (8-vCPU VM)

```
┌─────────────────────────────────────────────────────────┐
│                    8-vCPU Cloud VM                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  HPE Service                                            │
│  ├─ Lightweight models: 6 vCPUs + 6GB RAM              │
│  ├─ Heavy models:       6 vCPUs + 9GB RAM              │
│  └─ GPU models:         4 vCPUs + 8GB RAM              │
│                                                         │
│  Monitor Service                                        │
│  └─ All methods:        2 vCPUs + 512MB RAM            │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Command-Line Arguments

```bash
./run_experiment.sh [METHOD] [VIDEO_FILE]
```

### Arguments

| Argument | Description | Default |
|---|---|---|
| `METHOD` | HPE method to test | `movenet` |
| `VIDEO_FILE` | Video file path (relative to `/videos/`) | `ultimatum/hd_00_00.mp4` |

### Supported Methods

| Method | Type | Device | Description |
|---|---|---|---|
| `movenet` | OpenVINO | CPU | Lightweight single-person pose estimation |
| `ae1` | OpenVINO | CPU | EfficientHRNet variant 1 |
| `ae2` | OpenVINO | CPU | EfficientHRNet variant 2 |
| `ae3` | OpenVINO | CPU | EfficientHRNet variant 3 |
| `hrnet` | OpenVINO | CPU | HigherHRNet multi-person pose estimation |
| `openpose` | OpenVINO | CPU/GPU | Multi-person pose estimation |
| `alphapose` | PyTorch | GPU | High-accuracy pose estimation |

---

## Examples

### Test MoveNet on Default Video

```bash
./run_experiment.sh movenet
```

**Output:**
```
[INFO] Configuration:
  Method: movenet
  Device: CPU
  Video: ultimatum/hd_00_00.mp4
  CPU Allocation: 6.0 cores (reserved: 4.0)
  Memory: 6G (reserved: 4G)
  OpenVINO Threads: 6
```

### Test HigherHRNet on Custom Video

```bash
./run_experiment.sh hrnet rangeOfMotion/vga_01_01.mp4
```

### Test AlphaPose (GPU)

```bash
./run_experiment.sh alphapose ultimatum/hd_00_00.mp4
```

---

## Manual Resource Override

You can override the automatic allocation by setting environment variables:

```bash
# Use 4 threads instead of 6
OV_THREADS=4 HPE_CPU_LIMIT=4.0 ./run_experiment.sh movenet

# Disable CPU pinning
OV_CPU_PINNING=false ./run_experiment.sh movenet

# Use throughput mode instead of latency
OV_MODE=throughput ./run_experiment.sh movenet
```

### Available Override Variables

| Variable | Description | Default |
|---|---|---|
| `OV_THREADS` | OpenVINO CPU threads | Method-dependent (4-6) |
| `OV_MODE` | Performance mode (`latency` or `throughput`) | `latency` |
| `OV_CPU_PINNING` | Pin threads to cores (`true` or `false`) | `true` |
| `OV_HYPER_THREADING` | Use logical cores (`true` or `false`) | `false` |
| `HPE_CPU_LIMIT` | Maximum CPU cores | Method-dependent |
| `HPE_CPU_RESERVATION` | Guaranteed CPU cores | Method-dependent |
| `HPE_MEMORY_LIMIT` | Maximum memory | Method-dependent |
| `HPE_MEMORY_RESERVATION` | Guaranteed memory | Method-dependent |

---

## Output

### Results Directory

Each run creates a timestamped results directory:

```
results_<method>_<cpu_model>_<timestamp>/
├── logs/
│   ├── hpe_container.log       # HPE container logs
│   └── monitor_container.log   # Monitor container logs
├── pid_metrics.csv             # CPU/memory metrics over time
└── pid_metrics.png             # Visualization (if generated)
```

### Metrics CSV Format

```csv
timestamp,pid,cpu_percent,mem_rss_kb,tx_bytes,rx_bytes
1716825600.123,12345,450.5,2097152,1048576,524288
1716825600.623,12345,455.2,2099200,1050624,526336
...
```

**Columns:**
- `timestamp`: Unix timestamp (seconds with nanosecond precision)
- `pid`: Process ID of the HPE container
- `cpu_percent`: CPU usage percentage (600% = 6 cores at 100%)
- `mem_rss_kb`: Resident Set Size memory in kilobytes (divide by 1024 for MB)
- `tx_bytes`: Transmitted bytes (TX only; see note below)
- `rx_bytes`: Received bytes (always 0 in this file; see note below)

**Note on Network Metrics:**
- `tx_bytes` in this file contains valid TX (transmitted) data from bpftrace
- `rx_bytes` is always 0 here due to kernel softirq context limitations
- For accurate RX data, use `traces/bcc/hpe_video_rx.csv` from the `bcc-tracer` container (if enabled in `ffmpeg_hpe` rig)

---

## Verification

### Check Resource Allocation

```bash
# Start experiment
./run_experiment.sh movenet

# In another terminal, check actual resource usage
docker stats

# Expected output for movenet:
# CONTAINER       CPU %     MEM USAGE
# monitor-hpe     ~600%     ~2-4GB
# monitor-monitor ~50-100%  ~100MB
```

### Verify OpenVINO Configuration

```bash
# Check HPE container logs
docker logs monitor-hpe-hpe-1 | grep "OpenVINO Configuration" -A 10

# Expected output:
# [OpenVINO Configuration]
#   Requested settings: threads=6, mode=latency, streams=None
#   Effective settings:
#     Performance mode: LATENCY
#     CPU threads: 6
#     CPU streams: 1
#     CPU pinning: True
#     Hyper-threading: False
```

---

## Troubleshooting

### Issue: Low CPU Usage

**Symptom:** `docker stats` shows HPE at ~100% instead of ~600%

**Possible Causes:**
1. Video decoding bottleneck (I/O limited)
2. Model doesn't parallelize well
3. OpenVINO threads not set correctly

**Solution:**
```bash
# Check OpenVINO configuration
docker exec monitor-hpe-hpe-1 env | grep OV_

# Should show:
# OV_THREADS=6
# OV_MODE=latency
# OV_CPU_PINNING=true
```

### Issue: Out of Memory

**Symptom:** Container crashes with OOM error

**Solution:**
```bash
# Increase memory limit
HPE_MEMORY_LIMIT=12G ./run_experiment.sh hrnet
```

### Issue: Monitor Service Interfering

**Symptom:** Inconsistent FPS, high variance

**Solution:** Monitor service already limited to 2 cores. Check if other processes are running on the host.

---

## Performance Expectations

### Throughput Comparison (8-vCPU VM)

| Method | 1 Thread | 6 Threads | Speedup |
|---|---|---|---|
| MoveNet | 15 FPS | 40-50 FPS | 2.7-3.3x |
| EfficientHRNet (ae1) | 8 FPS | 25-30 FPS | 3.1-3.8x |
| HigherHRNet (hrnet) | 5 FPS | 20-25 FPS | 4.0-5.0x |
| OpenPose | 3 FPS | 15-18 FPS | 5.0-6.0x |

**Note:** Actual FPS depends on video resolution, CPU model, and system load.

---

## Related Files

- `docker-compose.yaml` — Service definitions with dynamic resource allocation
- `run_experiment.sh` — Experiment orchestration with automatic configuration
- `monitor_pid.sh` — bpftrace monitoring script
- `plot_graph.py` — Results visualization
- `RESOURCE_ALLOCATION.md` — Detailed resource allocation guide
- `SCALING_GUIDE.md` — Auto-scaling behavior for different VM sizes
- `USAGE.md` — Complete usage guide with examples

---

## See Also

- [SCALING_GUIDE.md](SCALING_GUIDE.md) — Auto-scaling for 4-32 vCPU VMs
- [RESOURCE_ALLOCATION.md](RESOURCE_ALLOCATION.md) — Technical resource allocation details
- [../README.md](../README.md) — Main project README
- [../AGENTS.md](../AGENTS.md) — Agent guidance for working in this repository
- [../ffmpeg_hpe/](../ffmpeg_hpe/) — Full monitoring stack with RTSP streaming
- [../COMPLETE_AUDIT_SUMMARY.md](../COMPLETE_AUDIT_SUMMARY.md) — Complete audit and fixes summary
