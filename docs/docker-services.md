# Docker Services & Infrastructure — Deep Dive

## Overview

This document provides detailed reference for all Docker images, Compose services, and container configurations used in the HPE benchmarking pipeline.

---

## Docker Images

### `Dockerfile_base` (Baseline HPE Image)

| Property | Value |
|----------|-------|
| Base image | `pytorch/pytorch:2.4.1-cuda12.1-cudnn9-devel` |
| Working directory | `/app` |
| PID directory | `/pids` (chmod 777) |
| Entrypoint | `/app/entrypoint.sh` |
| Default command | `python3 main.py` |
| CUDA arch | `TORCH_CUDA_ARCH_LIST=8.6` |

**System dependencies installed:**
- Build tools: `gcc-9`, `g++-9`, `cmake`, `git`
- Runtime libs: `libgl1-mesa-glx`, `libglib2.0-0`, `libgomp1`, `python3-tk`
- Utilities: `curl`, `ffmpeg`, `tcpdump`

**Python frameworks:**
- `PyNvCodec` — built from NVIDIA VideoProcessingFramework Git source
- `OpenVINO 2024.4.0`
- `gdown` — used for model downloads during build

**Models downloaded via `gdown` at build time:**

| Model | File |
|-------|------|
| AlphaPose backbone | `fast_res50_256x192.pth` |
| AlphaPose detector | `yolov3-spp.weights` |
| MoveNet | `movenet_multipose_lightning_256x256_FP32.bin` |
| OpenVINO HPE | `human-pose-estimation-0001`, `0005`, `0006`, `0007` |
| OpenVINO HigherHRNet | HigherHRNet IR files |

**Extension build:**  
AlphaPose C/CUDA extensions are compiled during build via `build_extensions.sh`.

---

### `Dockerfile.hpe` (Manual FFmpeg + OpenCV Build)

Same PyTorch base as `Dockerfile_base`, but with manually compiled multimedia stack:

- **FFmpeg 5.1.2** compiled with NVIDIA CUDA support:
  - `--enable-cuda-nvcc`
  - `--enable-libnpp`
  - `--enable-nonfree`
- **OpenCV 4.10.0** built from source with:
  - `WITH_CUDA=ON`
  - `WITH_CUDNN=ON`
  - `OPENCV_DNN_CUDA=ON`
  - `WITH_FFMPEG=ON`
  - `opencv_contrib` modules included

Use this image when you need hardware-accelerated video decoding via OpenCV or FFmpeg NVDEC/NVENC pipelines.

---

### `Dockerfile_combined_multistage_app` (Production Multi-Stage)

A three-stage production build minimising final image size:

#### Stage 1 — `ffmpeg-builder`

| Property | Value |
|----------|-------|
| Base | `nvidia/cuda:12.2.0-devel-ubuntu20.04` |
| Builds | `nv-codec-headers` + FFmpeg 8.0 |
| NVIDIA features | Full support: NVENC, NVDEC, libnpp, CUDA |

#### Stage 2 — `app-builder`

| Property | Value |
|----------|-------|
| Base | PyTorch base (CUDA 12.1 → upgraded to 12.2) |
| Installs | `PyAV`, `VideoProcessingFramework`, `OpenVINO` |
| Downloads | All HPE models (same as `Dockerfile_base`) |
| Builds | AlphaPose CUDA extensions |

#### Stage 3 — `runtime`

- Copies compiled artifacts from stages 1 and 2
- Installs minimal runtime dependencies only
- Sets environment:
  - `TORCH_CUDA_ARCH_LIST=8.6`
  - `PKG_CONFIG_PATH` pointing to CUDA 12.2 libraries
  - `LD_LIBRARY_PATH` for CUDA 12.2 shared libraries

---

### `Dockerfile.gpu_metrics` (GPU Metrics Collector)

| Property | Value |
|----------|-------|
| Base | `nvidia/cuda:11.8.0-base-ubuntu22.04` |
| Installs | `nvidia-utils-535` |
| Runs | `run_nvidia_dcgm.sh` |
| Purpose | Lightweight container for `nvidia-smi` polling only |

No model files or Python stack — kept intentionally minimal.

---

## Docker Compose Services

### `ffmpeg_hpe/docker-compose.yaml` (Primary Experiment Compose)

This is the main compose file used for benchmarking experiments.

---

#### `rtsp-broker` + `streamer` (replaced `h264-streaming-server`)

> The old `h264-streaming-server` built from `rtsp-ipcam/` has been removed. Streaming is now handled by two pre-built images in `ffmpeg_hpe/docker-compose.yaml`:
> - **`rtsp-broker`** (`bluenviron/mediamtx:1-ffmpeg`) — RTSP broker on port `8554`
> - **`streamer`** (`jrottenberg/ffmpeg:4.4-nvidia`) — FFmpeg/NVENC producer, mounts `../videos:/data:ro`

---

#### `hpe` (Main Workload)

Runs the HPE inference pipeline against the video stream.

| Property | Value |
|----------|-------|
| Build context | Project root (`Dockerfile_optimized_multistage_v4`) |
| Runtime | `${HPE_RUNTIME:-runc}` (`nvidia` only for GPU methods) |
| Shared memory | `8gb` |
| Depends on | `rtsp-broker`, `streamer` (`service_started`) |

**Volumes:**

| Host | Container | Mode |
|------|-----------|------|
| `./results` | `/output` | `rw` |
| `../videos` | `/videos` | `ro` |

**Environment variables:**

| Variable | Value |
|----------|-------|
| `NVIDIA_VISIBLE_DEVICES` | `${NVIDIA_VISIBLE_DEVICES:-all}` for GPU methods, `none` for CPU-only methods |
| `CUDA_VISIBLE_DEVICES` | `0` |
| `PYTHONUNBUFFERED` | `1` |
| `WAIT_HOSTS` | `rtsp-broker:8554` |
| `WAIT_HOSTS_TIMEOUT` | `30` |
| `PYTORCH_CUDA_ALLOC_CONF` | `max_split_size_mb:32` |
| `OPENCV_FFMPEG_OPEN_TIMEOUT` | `300000` (5 min) |
| `OPENCV_FFMPEG_READ_TIMEOUT` | `300000` (5 min) |
| `OPENCV_FFMPEG_CAPTURE_OPTIONS` | `rtsp_transport;tcp` |

**Command:**
```bash
python3 main.py \
  --method ${HPE_METHOD} \
  --input ${HPE_INPUT} \
  --csv \
  --output_dir /output/ \
  --device ${HPE_DEVICE} \
  --measurement_interval_ms 10
```

**Healthcheck:**
```
test: pgrep -f "python.*main.py"
interval: 30s
```

**Resource limits:**

| Resource | Limit |
|----------|-------|
| CPU | 4.0 |
| Memory | 16G |
| NVIDIA GPUs | all |

---

#### `gpu-metrics`

Runs `nvidia-smi` polling in a sidecar container alongside the HPE workload.

| Property | Value |
|----------|-------|
| Build | `Dockerfile.gpu_metrics` |
| Runtime | `nvidia` |
| Depends on | `rtsp-broker`, `hpe` |

**Volumes:** `./results:/output`

**Environment:** `NVIDIA_VISIBLE_DEVICES=all`

**Healthcheck:** `pgrep -f "nvidia-smi"`, interval 30s

---

#### `perf_monitor`

Collects host-level performance metrics (CPU, memory, I/O) alongside the HPE run.

| Property | Value |
|----------|-------|
| Build context | `../recent-dash/perf_monitor` |
| PID namespace | `host` |
| User | `root` |
| Privileged | `true` |
| Depends on | `rtsp-broker`, `hpe` |

**Capabilities:** `SYS_ADMIN`, `NET_ADMIN`, `NET_RAW`, `IPC_LOCK`

**Volumes:**

| Host | Container | Mode |
|------|-----------|------|
| `./results` | `/output` | `rw` |
| `./pids` | `/pids` | `ro` |

**Environment:**
- `OUTPUT_DIR=/output`
- `EXPERIMENT_TYPE=ffmpeg_hpe`

---

#### `bcc-tracer` (Optional — BCC eBPF Network Tracing)

> Used only when running `run_experiment_bcc.sh`. Not started by default.

Attaches BCC/eBPF probes to the HPE container's network namespace to trace RX/TX traffic at the kernel level.

| Property | Value |
|----------|-------|
| Build | `./bpftrace-tracer/Dockerfile.bcc` |
| User | `root` |
| Privileged | `true` |
| seccomp | `unconfined` |
| Network | `service:hpe` (shares HPE's network namespace) |

**Volumes:**

| Host | Container | Mode |
|------|-----------|------|
| `./tracer_output` | `/opt/tracer/output` | `rw` |
| `/lib/modules` | `/lib/modules` | `ro` |
| `/usr/src` | `/usr/src` | `ro` |
| `/sys/kernel/debug` | `/sys/kernel/debug` | `rw` |

**Capabilities:** `SYS_ADMIN`, `NET_ADMIN`, `NET_RAW`, `IPC_LOCK`, `SYS_RESOURCE`

**Environment:**

| Variable | Value |
|----------|-------|
| `TARGET_CONTAINER` | `hpe` |
| `STREAMER_IP` | `rtsp-broker` |
| `PORT_DETECTION_TIMEOUT` | `30` |

> Note: Sharing the HPE network namespace (`network_mode: service:hpe`) allows the tracer to observe all packets entering and leaving the HPE container without any additional routing.

---

#### Network

```yaml
networks:
  streaming-network:
    driver: bridge
```

All services are attached to `streaming-network`.

---

### `monitor_hpe/docker-compose.yaml` (Simplified Monitoring)

Lightweight alternative compose for local monitoring experiments.

#### `hpe`

| Property | Value |
|----------|-------|
| Image | `monitor-hpe:latest` (built from `Dockerfile_base`) |
| PID namespace | `host` |
| Capabilities | `SYS_PTRACE` |
| seccomp | `unconfined` |

**Command:**
```bash
python3 main.py --method movenet --input /videos/${VIDEO_FILE:-ultimatum/hd_00_00.mp4}
```

**Resource limits:**

| Resource | Limit | Reservation |
|----------|-------|-------------|
| CPU | 4.0 | 2.0 |
| Memory | 4G | 2G |

#### `monitor`

| Property | Value |
|----------|-------|
| Build | `./Dockerfile` |
| PID namespace | `host` |
| Capabilities | `IPC_LOCK`, `SYS_ADMIN` |
| ulimits | `memlock: unlimited` |

**Command:** `/monitor_pid.sh`

**Environment:**

| Variable | Value |
|----------|-------|
| `TARGET_PID_FILE` | `/pids/hpe.pid` |
| `BPFTRACE_STRLEN` | `64` |

**Resource limits:** CPU 1.0, Memory 512M

---

---

## Container Mount Paths Reference

| Host Path | Container Path | Service | Mode |
|-----------|---------------|---------|------|
| `./results/` | `/output/` | `hpe`, `gpu-metrics`, `perf_monitor` | `rw` |
| `../videos/` | `/videos/` | `hpe` | `ro` |
| `../videos/` | `/data/` | `streamer` | `ro` |
| `./pids/` | `/pids/` | `hpe` (write), `perf_monitor` (read) | `rw` / `ro` |
| `./tracer_output/` | `/opt/tracer/output/` | `bcc-tracer` | `rw` |
| `/lib/modules` | `/lib/modules` | `bcc-tracer` | `ro` |
| `/usr/src` | `/usr/src` | `bcc-tracer` | `ro` |
| `/sys/kernel/debug` | `/sys/kernel/debug` | `bcc-tracer` | `rw` |

---

## Entrypoint Behavior (`ffmpeg_hpe/entrypoint.sh`)

1. Checks the `ENABLE_GPU_METRICS` environment variable.
2. If enabled: launches `run_nvidia_dcgm.sh` in the background and stores its PID in `METRICS_PID`.
3. Executes the passed command (or defaults to `python3 main.py`).
4. On exit or signal: sends `SIGTERM` to `METRICS_PID` to cleanly stop the metrics collector.

---

## Environment Variables Reference

| Variable | Default | Used By | Description |
|----------|---------|---------|-------------|
| `VIDEO_FILE_NAME` | (from `.env`) | `streamer` | Path to the local video file inside the producer container |
| `HPE_METHOD` | (set by script) | `hpe` | Pose estimation method (`movenet`, `alphapose`, etc.) |
| `HPE_INPUT` | (set by script) | `hpe` | Stream URL or file path |
| `HPE_DEVICE` | `GPU` | `hpe` | Inference device (`CPU` or `GPU`) |
| `HPE_RUNTIME` | `runc` / `nvidia` | `hpe` | Runtime selected by `run_experiment.sh`; `nvidia` only for GPU methods |
| `NVIDIA_VISIBLE_DEVICES` | `all` / `none` | `hpe`, `gpu-metrics` | GPU visibility for container; CPU-only HPE methods use `none` |
| `CUDA_VISIBLE_DEVICES` | `0` | `hpe` | GPU device index |
| `PYTORCH_CUDA_ALLOC_CONF` | `max_split_size_mb:32` | `hpe` | PyTorch CUDA memory allocator config |
| `OPENCV_FFMPEG_OPEN_TIMEOUT` | `300000` | `hpe` | Stream open timeout in milliseconds |
| `OPENCV_FFMPEG_READ_TIMEOUT` | `300000` | `hpe` | Stream read timeout in milliseconds |
| `PYTHONUNBUFFERED` | `1` | `hpe` | Disable Python stdout/stderr buffering |
| `TARGET_CONTAINER` | `hpe` | `bcc-tracer` | Name of container to attach eBPF probes to |
| `STREAMER_IP` | `rtsp-broker` | `bcc-tracer` | RTSP broker hostname |
| `STREAMER_PORT` | `8554` | `bcc-tracer` | RTSP port used by the broker |
| `BCC_INTERFACE` | auto-detected | `bcc-tracer` | Optional override for the raw socket interface |
| `PORT_DETECTION_TIMEOUT` | `30` | `bcc-tracer` | Seconds to wait for port detection |
| `OUTPUT_DIR` | `/output` | `perf_monitor` | Directory to write metrics output |
| `EXPERIMENT_TYPE` | `ffmpeg_hpe` | `perf_monitor` | Experiment label for output files |
| `TARGET_PID_FILE` | `/pids/hpe.pid` | `monitor` (monitor_hpe) | PID file to monitor with bpftrace |
| `BPFTRACE_STRLEN` | `64` | `monitor` (monitor_hpe) | bpftrace string buffer length |
| `ENABLE_GPU_METRICS` | (unset) | `entrypoint.sh` | Enable background GPU metrics collection |

---

## Building and Rebuilding

```bash
# Build all services
docker compose build

# Rebuild specific service without cache
docker compose build --no-cache bcc-tracer
docker compose build --no-cache gpu-metrics bcc-tracer hpe
docker compose build --no-cache hpe

# View resolved compose config (with variable substitution)
docker compose config

# Check image sizes
docker images | grep -E "hpe|h264|tracer|gpu"
```

### Typical experiment run sequence

```bash
# From ffmpeg_hpe/
cp .env.example .env         # set VIDEO_FILE_NAME and HPE_METHOD
docker compose build
docker compose up -d rtsp-broker streamer
docker compose up hpe gpu-metrics perf_monitor
```

### Running with BCC tracing enabled

```bash
# From ffmpeg_hpe/
bash run_experiment_bcc.sh
# bcc-tracer will automatically start alongside hpe
```
