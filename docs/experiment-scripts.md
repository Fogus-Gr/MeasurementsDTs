# Experiment Scripts — Deep Dive

## Overview

This document provides detailed reference for all experiment orchestration and monitoring scripts in the HPE benchmarking pipeline. Scripts are organized by location and purpose: full end-to-end experiment runners, local process monitors, and standalone metrics collectors.

---

## ffmpeg_hpe/run_experiment.sh (251 lines)

### Purpose

End-to-end orchestration of HPE inference with streaming, performance monitoring, and container lifecycle management. This is the **"basic" experiment runner** — it collects CPU, memory, and GPU metrics but does **not** include BCC/BPF kernel-level network tracing. Use `run_experiment_bcc.sh` when network RX tracing is required.

### Arguments

| Position | Value | Example |
|----------|-------|---------|
| `$1` | HPE method name | `alphapose`, `movenet`, `openpose`, `hrnet`, `ae1` |

### Environment Variables

| Variable | Source | Description |
|----------|--------|-------------|
| `HPE_METHOD` | `$1` argument | Selects which HPE backend to run |
| `HPE_INPUT` | Derived from server IP | `http://<IP>:8089/stream.h264` |
| `HPE_DEVICE` | Method-based default | `GPU` for alphapose/openpose; `CPU` for all others |
| CPU model | `lscpu` output | Used in results directory naming |

### Step-by-Step Flow

1. **Install dependencies** — installs `bc` for floating-point arithmetic in timing calculations.
2. **Define helper functions**:
   - `measure_container_startup()` — calculates container instantiation time by comparing timestamps.
   - `capture_diagnostics()` — logs current system state, container logs, and stream availability for post-mortem analysis.
3. **Prepare run metadata**:
   - Generate timestamp
   - Read CPU model from `lscpu`
   - Create results directory: `results_${method}_${cpu_model}_${timestamp}`
   - Create subdirectories: `logs/`, `traces/`, `perf/`
4. **Cleanup stale artifacts** — remove old CSV files from `./results/`, `./traces/`, `./perf_monitor/output/`.
5. **Stop old containers** — `docker compose down -v --remove-orphans`.
6. **Start streaming server** — poll healthcheck endpoint; wait up to **60 seconds** before continuing.
7. **Extract server IP** — using `docker inspect`:
   ```bash
   docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' <container>
   ```
8. **Configure and start HPE container** — set `HPE_METHOD`, `HPE_INPUT`, `HPE_DEVICE` and bring up the HPE service.
9. **Start monitoring stack** — launch `perf_monitor`, optional `trace_container`, and `gpu-metrics` services.
10. **Extract HPE PIDs** — `docker exec hpe ps -ef > ./pids/hpe.pid`.
11. **Poll loop** — check container status every **5 seconds** until the HPE container exits.
12. **Collect results** — copy metrics files from containers into `$results_dir`.
13. **Cleanup** — `docker compose down --remove-orphans --volumes`.

### Output Files

| Path | Contents |
|------|----------|
| `$results_dir/container_timing.txt` | Container startup/stop timestamps |
| `$results_dir/logs/` | Logs from hpe, perf_monitor, trace_container, gpu-metrics |
| `$results_dir/perf/performance_data.csv` | CPU/memory performance data |
| `$results_dir/traces/trace.csv` | Trace events |
| `$results_dir/gpu/gpu_metrics.csv` | GPU utilization, memory, power, temperature |

### Error Handling

- **Streaming server timeout**: if the healthcheck does not pass within 60 seconds, the script calls `capture_diagnostics()` and continues anyway.
- **Container exit detection**: polling loop detects HPE container exit via `docker inspect` state.

---

## ffmpeg_hpe/run_experiment_bcc.sh (271 lines)

### Purpose

Enhanced experiment runner with **BCC (BPF Compiler Collection)** kernel-level network tracing. This is the **"production" experiment runner** — recommended for full benchmarks where network RX byte measurement at the kernel level is required.

### Arguments

| Position | Value | Example |
|----------|-------|---------|
| `$1` | HPE method name | `alphapose`, `movenet` |
| `$2` | *(optional)* Device override | `--device CPU` or `--device GPU` |

### Key Differences from run_experiment.sh

| Feature | run_experiment.sh | run_experiment_bcc.sh |
|---------|-------------------|----------------------|
| Network tracing | None | BCC/BPF kernel-level RX tracing |
| CPU thread count | Not extracted | Extracted via `lscpu \| awk '/^CPU\(s\):/ {print $2}'` |
| VIDEO_FILE | N/A | Loaded from `.env` if not in environment |
| Results dir naming | `method_cpu_timestamp` | `method_threads-cores_device_videoname_timestamp` |
| Tracer output cleanup | Yes | `rm -rf ./tracer_output && mkdir -p ./tracer_output` |
| BCC startup wait | None | Extra **8-second** wait for BPF compilation |
| Port detection | None | Monitors logs for detected HPE video port |
| Extra data collected | — | `video_rx.csv`, BCC tracer logs |

### BCC-Specific Steps

After starting the HPE container and base monitoring services:

1. Start the `bcc-tracer` container.
2. Sleep **8 seconds** to allow kernel BPF program compilation.
3. Check tracer logs for confirmation strings:
   - `"Detected HPE video port"`
   - `"Monitoring HPE traffic on port"`
4. Extract the detected port number from logs.
5. Record port detection info in `container_timing.txt`.

### Additional Data Collected

| Path | Contents |
|------|----------|
| `$results_dir/traces/bcc/video_rx.csv` | RX bytes per 10 ms interval |
| `$results_dir/traces/bcc/logs/` | BCC tracer container logs |
| `container_timing.txt` (appended) | Detected port and tracer startup time |

---

## monitor_hpe/run_experiment.sh (138 lines)

### Purpose

Local process monitoring **without streaming** — intended for comparative baseline measurements where the HPE process runs locally and is monitored via Docker Compose without an external video stream.

### Flow

1. Create results directory: `results_cpu_${cpu_info}_${timestamp}`.
2. Export `RESULTS_DIR` env var for `docker-compose` volume mapping.
3. `docker compose down` then `up -d --no-build --force-recreate`.
4. Wait **5 seconds** for container stabilization.
5. Monitor loop: check container status every **1 second** until containers stop.
6. On exit: save container logs, then generate plots:
   ```bash
   python3 plot_graph.py
   ```

### Output

| Path | Contents |
|------|----------|
| `$results_dir/logs/hpe_container.log` | HPE container stdout/stderr |
| `$results_dir/logs/monitor_container.log` | Monitor container stdout/stderr |
| `$results_dir/pid_metrics.csv` | Per-PID CPU and memory timeseries |
| `$results_dir/pid_metrics.png` / `cpu_usage.png` | Auto-generated performance plot |

---

## monitor_hpe/run_with_video.sh (20 lines)

### Purpose

Thin wrapper that sets `VIDEO_FILE` before delegating to `run_experiment.sh`. Useful for quickly switching the input video without editing environment files.

### Usage

```bash
./run_with_video.sh                       # Uses default: sample.mp4
./run_with_video.sh sample.mp4            # Explicit default
./run_with_video.sh hd_00_00.mp4          # Specific video file
```

### Flow

1. Accept `$1` as video filename (default: `sample.mp4`).
2. Validate the file exists at `/home/user/MeasurementsDTs/videos/$VIDEO_FILE`.
3. `export VIDEO_FILE`.
4. Exec `./run_experiment.sh`.

---

## Monitoring Scripts

### ffmpeg_hpe/monitor_pid.sh (151 lines)

#### Purpose

Monitor a **single process by PID file** for CPU usage, memory (RSS), and network I/O using `bpftrace`. Outputs structured CSV files for offline analysis.

#### Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `TARGET_PID_FILE` | `/pids/hpe.pid` | Path to file containing target PID |
| Output dir | `/output/` | Where CSV files are written |

#### CSV Output Formats

**`/output/pid_metrics.csv`**
```
timestamp,pid,cpu_percent,mem_rss_kb,tx_bytes,rx_bytes
```

**`/output/network_stats.csv`**
```
timestamp,pid,interface,bytes,sent
```
> `sent` field: `1` = transmitted, `0` = received

#### Flow

1. Initialize CSV files with headers.
2. Wait up to **30 seconds** for the PID file to appear.
3. Read PID from file; create named FIFO: `/tmp/bftrace_fifo_${PID}`.
4. Launch `bpftrace` in background, tracing:
   - `tracepoint:syscalls:sys_enter_sendto` → TX bytes
   - `tracepoint:net:netif_receive_skb` → RX bytes
   - Interval output: **500 ms**
   - Format: `PID TX_bytes RX_bytes (TX: %.2f Mbit/s, RX: %.2f Mbit/s)`
5. Background reader: drains FIFO and appends to `network_stats.csv`.
6. Main loop (every **0.5 s**):
   - Verify PID is still alive via `kill -0`.
   - Read CPU% from `ps -p $PID -o %cpu`, normalized by core count.
   - Read RSS from `/proc/$PID/status` (`VmRSS` field).
   - Append row to `pid_metrics.csv`.
7. Cleanup on exit: remove FIFO, send `SIGTERM` to bpftrace.

---

### monitor_hpe/monitor_pid.sh (204 lines)

#### Key Differences from ffmpeg_hpe Version

| Aspect | ffmpeg_hpe/monitor_pid.sh | monitor_hpe/monitor_pid.sh |
|--------|--------------------------|---------------------------|
| Sampling interval | 500 ms | **10 ms** |
| Network stats write frequency | Every 500 ms | More frequent (matches 10 ms loop) |
| Bpftrace output | Raw bytes | Includes Mbit/s rate calculations |
| Signal handling | Basic | Explicit `INT`/`TERM`/`EXIT` trap + cleanup |

> The `monitor_hpe` variant is designed for higher-resolution profiling where sub-second granularity matters. Use it when analyzing short-duration bursts or latency spikes.

---

## GPU & CPU Metrics Scripts

### Measure_gpu_dcgm/run_nvidia_dcgm.sh (29 lines)

#### Purpose

Continuous GPU metrics collection via `nvidia-smi`, writing time-series data to CSV. Designed to run in a sidecar container alongside the HPE workload.

#### Flow

1. Create `/output` directory.
2. Write CSV header:
   ```
   timestamp,pstate,power.draw,temperature.gpu,utilization.gpu,utilization.memory,memory.total,memory.free,memory.used
   ```
3. Background loop: query `nvidia-smi` every **0.5 seconds**, append to `/output/gpu_stats.csv`.
4. Wait for `ENTER` keypress to stop.
5. Kill background loop.

#### nvidia-smi Query

```bash
nvidia-smi \
  --query-gpu=timestamp,pstate,power.draw,temperature.gpu,\
utilization.gpu,utilization.memory,memory.total,memory.free,memory.used \
  --format=csv,noheader,nounits
```

---

### Measure_plot_cpu_perf/run_perf_plot.sh (25 lines)

#### Purpose

Run the Linux `perf stat` tool against target processes and generate performance plots. Requires root/sudo access.

#### Flow

1. Read PID file: `/pids/dash.pid`.
2. For each PID in the file:
   ```bash
   sudo perf stat -p <PID> -e cpu-clock,cycles -I 100 --interval-count 100 -x ,
   ```
   Output written to: `perf_output_${PID}.txt`
3. Generate plot:
   ```bash
   python3 /app/plot_perf_metrics.py "perf_output_${PID}.txt"
   ```

#### Requirements

- Linux `perf` tool installed (`linux-tools-common` or equivalent).
- `sudo` / root access for `perf stat`.
- PID file present at `/pids/dash.pid`.
- `plot_perf_metrics.py` available at `/app/`.

---

## Script Decision Guide

| Goal | Script | Location |
|------|--------|----------|
| Full benchmark with network tracing | `run_experiment_bcc.sh` | `ffmpeg_hpe/` |
| Quick GPU + CPU metrics, no network trace | `run_experiment.sh` | `ffmpeg_hpe/` |
| Local process monitoring (no streaming) | `run_experiment.sh` | `monitor_hpe/` |
| Run with a specific video file | `run_with_video.sh` | `monitor_hpe/` |
| Standalone GPU metrics (sidecar) | `run_nvidia_dcgm.sh` | `Measure_gpu_dcgm/` |
| CPU perf stat + plot | `run_perf_plot.sh` | `Measure_plot_cpu_perf/` |

---

## Common Patterns

### Pre-Run Cleanup

Always clean up stale state before starting a new experiment run to avoid contaminating results:

```bash
docker compose down -v --remove-orphans
rm -f ./results/*.csv ./traces/*.csv ./perf_monitor/output/*.csv
rm -rf ./tracer_output
mkdir -p ./tracer_output
```

### Post-Run Data Inspection

```bash
# Verify output directory structure and sizes
tree -h results_*/

# List key output files
ls -lh results_*/perf/ results_*/gpu/ results_*/traces/bcc/

# Validate row counts
wc -l results_*/perf/performance_data.csv

# Inspect BCC network trace header
head -3 results_*/traces/bcc/video_rx.csv

# Sum total RX bytes and convert to MB
awk -F, 'NR>1 {sum+=$2} END {print sum/1024/1024 " MB"}' \
  results_*/traces/bcc/video_rx.csv
```

### Checking BCC Port Detection

```bash
# Confirm the tracer attached to the correct port
grep -E "Detected|Monitoring" results_*/logs/trace_container.log

# Cross-reference with container_timing.txt
cat results_*/container_timing.txt
```

### Comparing Across Runs

```bash
# Compare GPU utilization across two runs
paste -d',' \
  results_alphapose_*/gpu/gpu_metrics.csv \
  results_movenet_*/gpu/gpu_metrics.csv | column -t -s','
```
