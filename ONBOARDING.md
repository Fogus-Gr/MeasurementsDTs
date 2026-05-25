# Onboarding Guide — HPE Benchmarking Pipeline

Welcome! This guide is written for someone who is new to this project. By the end, you should be able to set up the environment, understand what each part of the codebase does, run a full benchmarking experiment, and interpret the results.

---

## Table of Contents

1. [What Is This Project?](#1-what-is-this-project)
2. [Repository Layout](#2-repository-layout)
3. [Prerequisites](#3-prerequisites)
4. [Environment Setup](#4-environment-setup)
5. [Downloading Pretrained Model Weights](#5-downloading-pretrained-model-weights)
6. [HPE Methods Available](#6-hpe-methods-available)
7. [Running HPE Locally (without Docker)](#7-running-hpe-locally-without-docker)
8. [The Experiment Pipeline](#8-the-experiment-pipeline)
9. [Running Experiments](#9-running-experiments)
10. [Results & Output](#10-results--output)
11. [Plotting & Visualization](#11-plotting--visualization)
12. [Monitoring During Experiments](#12-monitoring-during-experiments)
13. [Troubleshooting](#13-troubleshooting)
14. [Coding & Contribution Standards](#14-coding--contribution-standards)
15. [Git Branches](#15-git-branches)
16. [Tips for New Contributors](#16-tips-for-new-contributors)
17. [Quick Start (TL;DR)](#17-quick-start-tldr)

**Appendix:**
- [A. Glossary](#appendix-a-glossary)

---

## 1. What Is This Project?

This is an **end-to-end 2D Human Pose Estimation (HPE) benchmarking system**. The system:

- Streams video through Docker containers and runs different HPE models simultaneously.
- Supports multiple state-of-the-art models: **AlphaPose**, **MoveNet**, **OpenPose**, **HigherHRNet**, and **EfficientHRNet** variants.
- Collects performance metrics in parallel: CPU usage, GPU statistics (temperature, power, utilization), memory consumption, and network RX bytes at kernel level.
- The **goal** is systematic, reproducible performance evaluation and comparison of pose estimation methods on both CPU and GPU hardware.

### Pose Estimation 101 (newcomer primer)

If you have never worked with HPE before, here is the one-paragraph version:

**2D Human Pose Estimation** takes an image or video frame and outputs the pixel coordinates of human body joints — typically 17 keypoints in the COCO format (nose, eyes, ears, shoulders, elbows, wrists, hips, knees, ankles). Each detected person becomes a list of `(x, y, visibility)` triplets, optionally rendered as a stick-figure skeleton overlaid on the frame. The five backends in this repo (`alphapose`, `movenet`, `openpose`, `hrnet`, `ae1/2/3`) all solve the same problem with different speed/accuracy trade-offs:

| Backend | Approach | Strength | Trade-off |
|---|---|---|---|
| **MoveNet** | Single-stage, lightweight | Fastest on CPU; runs on edge devices | Lower accuracy on small/occluded people |
| **OpenPose** | Bottom-up, Part Affinity Fields | Robust on crowded scenes | Heavier compute |
| **HigherHRNet** (`hrnet`) | High-resolution backbone | Highest accuracy at the top end | Slow; memory-intensive |
| **EfficientHRNet** (`ae1/2/3`) | Three scaled HRNet variants | Tunable accuracy/speed | All CPU-friendly via OpenVINO |
| **AlphaPose** | Top-down (YOLO detector → pose net) | Best for clean, well-lit scenes | GPU strongly preferred |

The benchmarking platform exists to measure each backend's resource cost (CPU%, GPU%, RAM, network bandwidth, FPS) under a *realistic* video-streaming scenario — not just on a static image.

### What "benchmarking" means here

Each experiment run:
1. Starts a **video streaming server** (RTSP via MediaMTX, H.264 encoded by FFmpeg/NVENC) inside Docker.
2. Starts an **HPE inference container** that reads the stream and runs pose estimation.
3. Simultaneously starts **monitoring sidecars** that collect CPU, GPU, and network metrics.
4. Collects all outputs into a timestamped results directory.
5. Produces CSV files you can plot and compare across methods or hardware configurations.

---

## Deep-Dive Documentation

For detailed technical reference, see these companion documents in the `docs/` folder:

| Document | Description |
|----------|-------------|
| [Docker Services & Infrastructure](docs/docker-services.md) | All Dockerfiles, Compose services, volumes, environment variables, container privileges, and build commands |
| [Experiment Scripts](docs/experiment-scripts.md) | Detailed flow for every experiment and monitoring script, arguments, output files, and decision guide |
| [BCC/BPF Network Tracing](docs/bcc-bpf-tracing.md) | Kernel-level network tracing architecture, BCC program internals, port detection, kernel requirements, and troubleshooting |
| [Plotting & Data Analysis](docs/plotting-analysis.md) | All plotting scripts, input/output CSV formats, matplotlib configuration, and quick analysis commands |
| [HPE Methods](docs/hpe-methods.md) | Class hierarchy, model architectures, model files, inference pipelines, output formats, and CLI reference |

---

## 2. Repository Layout

### Folder Roles at a Glance

The top-level folders fall into three categories:

#### Experiment Rigs — have `run_experiment.sh`, orchestrate the full lifecycle

| Folder | Entry Point | What it measures |
|---|---|---|
| `ffmpeg_hpe/` | `run_experiment.sh` / `run_experiment_bcc.sh` | HPE inference on RTSP stream + full monitoring stack |
| `monitor_hpe/` | `run_experiment.sh` | HPE inference baseline — CPU/memory only, no streaming server |
| `recent-dash/` | `run_experiment.sh` | DASH/HTTP caching research — separate thread |

#### Service Implementations — provide Docker images consumed by the rigs

| Folder | Used by | Role in `docker-compose.yaml` |
|---|---|---|
| `jrottenberg/ffmpeg:4.4-nvidia` + `bluenviron/mediamtx:1-ffmpeg` | `ffmpeg_hpe/docker-compose.yaml` | Pre-built images for streamer and RTSP broker (replaced `rtsp-ipcam/`) |
| `recent-dash/perf_monitor/` | `ffmpeg_hpe/docker-compose.yaml` | Builds the `perf_monitor` container |
| `ffmpeg_hpe/bpftrace-tracer/` | `ffmpeg_hpe/docker-compose.yaml` | Builds the `bcc-tracer` container |
| `ffmpeg_hpe/Dockerfile.gpu_metrics` | `ffmpeg_hpe/docker-compose.yaml` | Builds the `gpu-metrics` container |
| `Dockerfile_base` (repo root) | `ffmpeg_hpe/` + `monitor_hpe/` | Builds the HPE application container |

#### Standalone Tools — run independently, not part of any compose stack

| Folder | What it does |
|---|---|
| `Measure_Flops/` | GPU FLOPS measurement via Nsight Compute |
| `Measure_gpu_dcgm/` | GPU power/temp/util via nvidia-smi (standalone, no compose) |
| `Measure_plot_cpu_perf/` | CPU cycles via `perf stat` |
| `optimizations/` | OpenVINO CPU thread/stream tuning scripts |
| `dev_tools/` | Local MJPEG stream server for manual testing |

```
MeasurementsDTs/
├── main.py                        # CLI entrypoint — selects HPE method and dispatches
├── alphapose_hpe.py               # AlphaPose implementation (top-down, GPU-first)
├── movenet_hpe.py                 # MoveNet implementation (lightweight, streaming-friendly)
├── openvino_base_hpe.py           # OpenVINO base: handles openpose, hrnet, ae1/2/3
├── base_hpe.py                    # Abstract base class for all HPE method implementations
├── setup.py                       # Cython/CUDA extension build for AlphaPose
├── requirements.txt               # Full Python dependency list (pinned versions)
│
├── utils/
│   ├── visualizer.py              # Keypoint drawing and annotation
│   └── evaluator.py              # Evaluation helpers
│
├── models/
│   ├── AlphaPose/                 # AlphaPose code, configs, pretrained weights
│   │   ├── alphapose/             # Core AlphaPose library
│   │   ├── detector/              # YOLOv3 person detector
│   │   ├── pretrained_models/     # .pth weight files (NOT in git — download manually)
│   │   └── build_extensions.sh   # Builds Cython/CUDA extensions
│   ├── MoveNet/                   # OpenVINO .xml/.bin for MoveNet
│   └── OpenVINO/
│       ├── model_api/             # OpenVINO model API wrappers
│       └── pretrained_models/     # .xml/.bin files (NOT in git — download manually)
│
├── ffmpeg_hpe/                    # PRIMARY experiment folder — start here for benchmarks
│   ├── run_experiment.sh          # Basic experiment runner (GPU + CPU metrics only)
│   ├── run_experiment_bcc.sh      # Full run with BCC kernel-level network tracing (recommended)
│   ├── docker-compose.yaml        # Multi-service orchestration (5 services)
│   ├── .env                       # VIDEO_FILE_NAME configuration for the streamer
│   ├── Dockerfile.gpu_metrics     # Dockerfile for GPU metrics sidecar
│   ├── bpftrace-tracer/           # BCC/BPF-based network tracing tools
│   │   ├── Dockerfile.bcc         # BCC tracer container
│   │   └── bcc_rx_bytes.py        # BPF program: counts RX bytes per 10ms interval
│   ├── plot_smi_output.py         # Plot GPU metrics (temp, power, util, memory)
│   ├── plot_rx_bytes.py           # Plot raw RX bytes timeline
│   ├── plot_rx_bytes_trimmed_reset.py  # Plot trimmed/reset RX bytes (preferred)
│   └── review.md                  # Notes on experiments and findings
│
├── monitor_hpe/                   # Simplified CPU/memory monitoring stack
│   ├── docker-compose.yaml
│   ├── plot_graph.py              # CPU + memory usage plots
│   └── run_experiment.sh
│
├── recent-dash/                   # Experimental Prometheus/dashboard monitoring
│   └── perf_monitor/              # bpftrace-based CPU/memory monitor container
│
├── Measure_plot_cpu_perf/         # Linux perf stat plotting tools
│   └── plot_perf_metrics.py       # Plot CPU cycles and utilization from perf stat CSV
│
├── Measure_gpu_dcgm/              # GPU metrics via nvidia-smi / DCGM
│   ├── plot_smi_output.py
│   └── run_nvidia_dcgm.sh
│
├── dev_tools/                     # Developer streaming server utilities
│   ├── stream_video_server.py     # Flask-based local HTTP video stream server
│   ├── stream_video_server_adaptive.py  # Adaptive bitrate variant
│   └── smoke_test.sh              # Quick smoke test script
│
├── unit_tests/
│   ├── images/                    # Sample test images (testImage.jpg, etc.)
│   └── video/                     # Sample test video (giphy.gif)
│
├── optimizations/                 # Performance optimization experiments
│   ├── cpu_performance_optimizer.py
│   ├── enhanced_openvino_hpe.py
│   └── optimized_main.py
│
├── Dockerfile_base                # Active HPE Docker image used by monitor_hpe and ffmpeg_hpe
├── Dockerfile_optimized_multistage_v4  # FFmpeg-only image; not used for the HPE service
├── Dockerfile.hpe                 # Alternative HPE Dockerfile
├── docker-compose.yml             # Root-level compose (GPU metrics stack)
└── README.md                      # Project README with model download links
```

> **Note:** Model weight files (`.pth`, `.bin`) are **not committed to git**. You must download them manually — see [Section 5](#5-downloading-pretrained-model-weights).

---

## 3. Prerequisites

| Requirement | Notes |
|---|---|
| Linux host | Ubuntu 20.04 tested and recommended |
| Docker + Docker Compose | v20+ recommended; Compose v2 (`docker compose`) |
| NVIDIA GPU + drivers | Verified: NVIDIA RTX A4000 (16 GB VRAM), driver **570.181** (CUDA 12.8 runtime). Project ships CUDA 12.1 toolkit; any driver supporting CUDA 12.1+ works. CPU-only methods (`movenet`, `hrnet`, `ae1/2/3`) need no GPU. |
| nvidia-container-toolkit | Enables `runtime: nvidia` in Docker Compose |
| Python 3.8.10 | For local runs; use conda or virtualenv |
| Conda (recommended) | For managing the Python environment |
| `bc` package | For floating-point math in shell scripts; auto-installed by experiment scripts |
| Sufficient disk space | Docker images can be 10–20 GB combined; run `df -h` before starting |

### Hardware floor & expected runtime

A single benchmark run takes roughly **3–7 minutes** on a short VGA clip (e.g. `vga_01_01.mp4`) once the Docker images are already built; the very first `docker compose build` adds ~10–20 minutes on top. The currently deployed handoff target is an **8 vCPU / 16 GB cloud GPU VM on AMD EPYC 7551P + RTX A4000** — the same instance used to validate every fix in `AGENTS.md`. The [optimizations/](file:///c:/Users/bigbu/Downloads/MeasurementsDTs/optimizations) scripts were originally calibrated for a 4 vCPU SKU; their runtime auto-detector adapts to whatever core count is present (see the Hardware Applicability table in [optimizations/README.md](file:///c:/Users/bigbu/Downloads/MeasurementsDTs/optimizations/README.md) for what transfers to other VM CPUs vs. bare metal). As a **practical floor** for new deployments, allocate at least **4 vCPU / 16 GB RAM** — this matches the per-service caps in [ffmpeg_hpe/docker-compose.yaml](file:///c:/Users/bigbu/Downloads/MeasurementsDTs/ffmpeg_hpe/docker-compose.yaml) (`hpe`: 2.5 CPU / 8 GB, `streamer`: 0.75 CPU, `rtsp-broker`: 0.5 CPU, sidecars: ~0.85 CPU combined). Plan for **≥30 GB free disk** for image layers, model weights, and result CSVs. GPU runs additionally need an NVIDIA card with up-to-date drivers and `nvidia-container-toolkit`; CPU-only methods (`movenet`, `hrnet`, `ae1/2/3`) work fine without a GPU.

### Verified working hardware stack

Last end-to-end verified configuration (May 2026):

| Component | Value |
|---|---|
| Host VM | 8 vCPU / 16 GB RAM cloud GPU VM |
| Host CPU (underlying) | AMD EPYC 7551P (Zen 1, AVX2, 64 MB L3) |
| GPU | NVIDIA RTX A4000, 16 GB VRAM |
| Driver | 570.181 |
| CUDA runtime (driver-supported) | 12.8 |
| CUDA toolkit (project-pinned) | 12.1 (PyTorch `cu121` wheels; `Dockerfile_base` is `pytorch/pytorch:2.4.1-cuda12.1-cudnn9-devel`) |
| Driver Persistence Mode | recommended **Enabled** — see the persistence step under "Verify your GPU setup" |

### Verify your GPU setup

```bash
nvidia-smi                          # Should show GPU info
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu20.04 nvidia-smi

# Recommended: enable persistent driver state for stable benchmark timings.
# Without it, the NVIDIA driver tears down its state every time the last
# CUDA process exits, adding ~1–3 s of GPU cold-start plus a power-state
# ramp from P8 to every run — both corrupt container_timing.txt and the
# first samples of gpu_metrics.csv.
sudo systemctl enable --now nvidia-persistenced
nvidia-smi -q | grep Persistence    # should now report: Enabled
```

---

## 4. Environment Setup

### Option A: Conda (recommended)

```bash
# Create and activate environment
conda create -n hpe python=3.8.10 -y
conda activate hpe

# Install PyTorch with CUDA support
conda install pytorch==2.4.1 torchvision==0.19.1 -c pytorch

# Install all remaining dependencies
conda install --file requirements.txt
```

### Option B: pip + virtualenv

```bash
python3 -m venv myenv
source myenv/bin/activate
pip install -r requirements.txt
```

### Build AlphaPose C++/CUDA Extensions

AlphaPose requires compiled Cython and CUDA extensions. Run this after environment setup:

```bash
# Recommended: use the build script (handles CPU/GPU detection automatically)
bash models/AlphaPose/build_extensions.sh

# Alternative: build in-place
python setup.py build_ext --inplace
```

> If you don't have a GPU, the build will fall back to CPU-only extensions. AlphaPose will still work but slower.

### Key Dependencies (from requirements.txt)

| Package | Version | Purpose |
|---|---|---|
| `torch` | 2.4.1 | PyTorch for AlphaPose/MoveNet |
| `openvino` | 2024.4.0 | Inference engine for OpenVINO models |
| `opencv-python` | 4.10.0.84 | Video/image I/O and processing |
| `tensorflow` | 2.13.1 | Used by some MoveNet variants |
| `Cython` | 3.0.11 | AlphaPose C extensions |
| `numpy` | 1.24.4 | Array operations |
| `matplotlib` / `seaborn` | 3.7.5 / 0.13.2 | Plotting results |
| `psutil` | 7.0.0 | Process monitoring |
| `gdown` | 5.2.0 | Google Drive model downloads |
| `flask` | 3.0.3 | Dev streaming server |

---

## 5. Downloading Pretrained Model Weights

**Model files are not in git.** Download each one and place it at the specified path:

### AlphaPose

```bash
# ResNet50 pose estimation weights
wget "https://drive.google.com/uc?export=download&id=1p6bi10UybpUIcq5D2XDsgQRLPJIr2RyI" \
  -O models/AlphaPose/pretrained_models/fast_res50_256x192.pth

# YOLOv3 person detector weights
wget "https://drive.google.com/uc?export=download&id=1k-9cUGcdH5ZFN1NcMvZrO0ApW241tboD" \
  -O models/AlphaPose/detector/yolo/data/yolov3-spp.weights
```

### MoveNet

```bash
wget "https://drive.google.com/uc?export=download&id=15SZwY2jAh1KqHwT-YO6_UByOsQD70RSr" \
  -O models/MoveNet/movenet_multipose_lightning_256x256_FP32.bin
```

### OpenPose (OpenVINO)

```bash
wget "https://drive.google.com/uc?export=download&id=1VNucIyIsdaiw1cYt-JGqBWloVu2TVdsm" \
  -O models/OpenVINO/pretrained_models/intel/human-pose-estimation-0001/human-pose-estimation-0001.bin
```

### HigherHRNet (OpenVINO)

```bash
wget "https://drive.google.com/uc?export=download&id=1fko47eVczJZQb9wWA2X7eQ0TuF4PDXzs" \
  -O models/OpenVINO/pretrained_models/public/FP32/higher-hrnet-w32-human-pose-estimation.bin
```

### EfficientHRNet variants (ae1, ae2, ae3)

```bash
# ae1
wget "https://drive.google.com/uc?export=download&id=1lEUFqQnWHVymQoZvaXuDFcnOyEEKsexP" \
  -O models/OpenVINO/pretrained_models/public/human-pose-estimation-0005/FP32/human-pose-estimation-0005.bin

# ae2
wget "https://drive.google.com/uc?export=download&id=1d8pGQrM9vEfz_oAIey0qRr7Gxp6dS2UE" \
  -O models/OpenVINO/pretrained_models/public/human-pose-estimation-0006/FP32/human-pose-estimation-0006.bin

# ae3
wget "https://drive.google.com/uc?export=download&id=1ZSdsqgD4zUO4gyHMYBfxq3m4UMyQ187j" \
  -O models/OpenVINO/pretrained_models/public/human-pose-estimation-0007/FP32/human-pose-estimation-0007.bin
```

> **Tip:** If `wget` fails for Google Drive links (common with large files), try `gdown` which is included in requirements:
> ```bash
> gdown "https://drive.google.com/uc?id=<FILE_ID>" -O <destination>
> ```

---

## 6. HPE Methods Available

> *For model architectures, file paths, and performance tuning, see [HPE Methods Deep Dive](docs/hpe-methods.md).*

| Method flag | Backend | Device Support | Description |
|---|---|---|---|
| `alphapose` | PyTorch | CPU / GPU | Top-down: detect persons first, then estimate pose per person. Strong accuracy. |
| `movenet` | OpenVINO | CPU / GPU | Lightweight bottom-up model. Fast; excellent for streaming scenarios. |
| `openpose` | OpenVINO | CPU / GPU | Classic OpenPose via OpenVINO IR. Good all-round performance. |
| `hrnet` | OpenVINO | CPU | HigherHRNet multi-person bottom-up. High accuracy, heavier compute. |
| `ae1` | OpenVINO | CPU | EfficientHRNet variant 1 (human-pose-estimation-0005). |
| `ae2` | OpenVINO | CPU | EfficientHRNet variant 2 (human-pose-estimation-0006). |
| `ae3` | OpenVINO | CPU | EfficientHRNet variant 3 (human-pose-estimation-0007). |

> **Default device** is `GPU`. Pass `--device CPU` to force CPU inference.

---

## 7. Running HPE Locally (without Docker)

These commands run inference directly on your machine using the activated conda/venv environment.

### Basic examples

```bash
# Single image — MoveNet, save annotated image
python3 main.py --method movenet --input unit_tests/images/testImage.jpg --save_image

# Image directory — AlphaPose, export keypoints to JSON
python3 main.py --method alphapose --input unit_tests/images/ --json

# GIF/video — EfficientHRNet1, save output video
python3 main.py --method ae1 --input unit_tests/video/giphy.gif --save_video

# HTTP stream — MoveNet, force CPU
python3 main.py --method movenet --input http://192.168.1.10:8089/stream.h264 --device CPU

# AlphaPose with CSV output, custom output directory, explicit device
python3 main.py --method alphapose --input video.mp4 --csv --device GPU --output_dir results/

# Show all flags
python3 main.py --help
```

### All CLI flags

| Flag | Default | Description |
|---|---|---|
| `--method` | required | HPE method: `openpose`, `alphapose`, `movenet`, `hrnet`, `ae1`, `ae2`, `ae3` |
| `--input` | `0` (webcam) | Path to image, directory, video/GIF file, or HTTP stream URL |
| `--output_dir` | None | Directory where output files are saved |
| `--device` | `GPU` | Inference device: `GPU` or `CPU` |
| `--json` | False | Export keypoints to a JSON file |
| `--csv` | False | Export keypoints to a CSV file |
| `--save_image` | False | Save annotated image(s) |
| `--save_video` | False | Save annotated video |
| `--detbatch` | `5` | Detection batch size (AlphaPose only) |
| `--timeout` | `300` | Timeout in seconds for HTTP streams |
| `--max_frames` | `0` | Max frames to process (0 = unlimited) |
| `--measurement_interval_ms` | `100` | Interval for measuring data volume |

### Using the local dev streaming server

```bash
# Terminal 1 — Start a local Flask video stream server
python3 dev_tools/stream_video_server.py
# Streams unit_tests/video/giphy.gif at http://<your-ip>:8080/video_feed

# Terminal 2 — Run HPE against the local stream
python3 main.py --method movenet --input http://$(hostname -I | awk '{print $1}'):8080/video_feed --save_video
```

---

## 8. The Experiment Pipeline

### Architecture Overview

```mermaid
flowchart TB
    subgraph DockerBridge["Docker Bridge Network\n(streaming-network)"]

        RTSP["rtsp-broker<br/>(MediaMTX, :8554)<br/>2 CPU cores, 1 GB"]

        Streamer["streamer<br/>FFmpeg/NVENC<br/>loops local video<br/>and publishes RTSP"]

        HPE["hpe container<br/>Python + OpenCV<br/>Pose Estimation<br/>2.5 CPU, 8 GB<br/>NVIDIA GPU (optional)"]

        Perf["perf_monitor<br/>(bpftrace)<br/>CPU% + mem RSS<br/>→ pid_metrics.csv"]

        BCC["bcc-tracer<br/>(BPF/BCC)<br/>RX bytes per 10ms<br/>→ video_rx.csv"]

        GPU["gpu-metrics<br/>(nvidia-smi)<br/>temp, power<br/>utilization<br/>→ gpu_metrics.csv"]

        Streamer -->|"Publishes RTSP"| RTSP
        RTSP -->|"RTSP Stream"| HPE
        HPE -->|"Consumes stream"| RTSP

        HPE --> Perf
        HPE --> BCC
        HPE --> GPU

    end
```


### Docker Services (defined in `ffmpeg_hpe/docker-compose.yaml`)

> *For complete Docker configuration details, see [Docker Services Deep Dive](docs/docker-services.md).*

#### 1. `rtsp-broker`
- **What it does:** Runs MediaMTX and exposes the RTSP endpoint on port 8554.
- **Image:** `bluenviron/mediamtx:1-ffmpeg`
- **Resources:** 2 CPU cores (limit), 1 GB RAM
- **Healthcheck:** Readiness is enforced by `run_experiment.sh`, which waits for port 8554 before starting dependents.

#### 2. `streamer`
- **What it does:** Loops the local benchmark video with FFmpeg/NVENC and publishes it to `rtsp://rtsp-broker:8554/stream`.
- **Image:** `jrottenberg/ffmpeg:4.4-nvidia`
- **Resources:** GPU-backed producer container
- **Config:** `VIDEO_FILE_NAME` from `.env` selects the local video file under `../videos`.

#### 3. `hpe`
- **What it does:** The main inference container. Reads from the RTSP stream, runs pose estimation, writes keypoint CSVs.
- **Built from:** `Dockerfile_base` at the repo root
- **Command:** `python3 main.py --method <METHOD> --input rtsp://rtsp-broker:8554/stream --csv --output_dir /output/ --device <DEVICE> --measurement_interval_ms 10`
- **Resources:** 2.5 CPU (limit) / 2.0 CPU (reservation), 8 GB RAM (rationale documented inline in `docker-compose.yaml`), GPU runtime only for GPU methods (`alphapose`, `openpose`)
- **Environment:** `HPE_METHOD`, `HPE_INPUT`, `HPE_DEVICE` are injected by experiment scripts.
- **Shared memory:** 8 GB (`shm_size`) — needed for large batch PyTorch operations.

#### 4. `gpu-metrics`
- **What it does:** Polls `nvidia-smi` every 500 ms and writes GPU temperature, power, utilization, and memory to `gpu_metrics.csv`.
- **Output:** `results/gpu/gpu_metrics.csv`
- **Requires:** NVIDIA GPU and `nvidia-container-toolkit`.

#### 5. `perf_monitor`
- **What it does:** Uses bpftrace to monitor the HPE process's CPU usage and memory RSS. Runs in host PID namespace.
- **Output:** `results/perf/pid_metrics.csv` (also `perf_metrics.csv`, `network_stats.csv`)
- **Privileges:** `privileged: true`, `SYS_ADMIN`, `NET_ADMIN` — needed for kernel tracing.

#### 6. `bcc-tracer`
- **What it does:** Uses Linux BCC (BPF Compiler Collection) to trace network RX bytes at the kernel level, counting bytes received from the RTSP broker every 10 ms.
- **Output:** `tracer_output/hpe_video_rx.csv`
- **Network mode:** Shares HPE container's network namespace (`network_mode: "service:hpe"`) to accurately capture the stream traffic.
- **Privileges:** `privileged: true`, `seccomp:unconfined` — required for BPF kernel access.

### Step-by-Step Experiment Flow

When you run `./run_experiment_bcc.sh alphapose`, the script:

1. **Generates a timestamped results directory name** (e.g., `results_alphapose_AMD_EPYC_7551P_20250428_120000/`).
2. **Creates output subdirectories:** `logs/`, `perf/`, `gpu/`, `traces/bcc/`, `hpe_output/`.
3. **Cleans up** any previous containers with `docker compose down -v --remove-orphans`.
4. **Starts `rtsp-broker` and `streamer`** and waits for the broker port probe to pass (up to 30 s).
5. **Starts the HPE container** with the configured method and device.
6. **Starts monitoring sidecars** in parallel: `gpu-metrics`, `perf_monitor`, `bcc-tracer`.
7. **Polls the HPE container** until it exits (video finishes or timeout reached).
8. **Captures diagnostics** (container logs, stream availability) on failure.
9. **Collects all outputs** — copies CSV files from Docker volumes into the results directory.
10. **Writes `container_timing.txt`** with per-container startup times.
11. **Tears down** all containers.

---

## 9. Running Experiments

### First Successful Run — CPU-only Quick Start

> *If you do not have an NVIDIA GPU, or you just want to confirm everything works before configuring CUDA, do this first. The whole path takes ~5 minutes after Docker images are built.*

```bash
# 1. Configure the smallest video for fastest feedback
echo "VIDEO_FILE_NAME=vga_01_01.mp4" > ffmpeg_hpe/.env

# 2. Build images (one-time, ~10-20 minutes)
cd ffmpeg_hpe/
docker compose build

# 3. Run MoveNet on CPU — the lightest backend
HPE_DEVICE=CPU ./run_experiment_bcc.sh movenet
```

**What you should see while it runs:**
- `mediamtx` and `video-producer` (streamer) start within 5 seconds.
- `hpe` container logs `Starting inference loop` and begins printing per-frame messages.
- `bcc-tracer` logs `Successfully attached BPF socket filter` (if you see `Permission denied` instead, your kernel headers are missing — see Section 13).
- The whole run completes in roughly the duration of the looped video (~30s) plus startup overhead.

**Verifying success:**

```bash
# 1. Latest results directory exists and contains data
ls -lt results_movenet_*/ | head

# 2. HPE exited cleanly
cat results_movenet_*/logs/hpe_exit.log   # should print: 0

# 3. Keypoint output exists
wc -l results_movenet_*/hpe_output/*.csv   # should be > 100 rows for a 30s VGA clip

# 4. Network RX captured something
awk -F, 'NR>1 {sum += $2} END {printf "RX total: %.2f MB\n", sum/1024/1024}' \
  results_movenet_*/traces/bcc/hpe_video_rx.csv
# Expected: a few MB for a 30s VGA clip; 0 means the BCC filter didn't attach
```

If all four checks pass, you have a working pipeline. Move on to GPU methods (`alphapose`, `openpose`) once you have CUDA installed.

### Two Experiment Scripts

> *For detailed script flow and all arguments, see [Experiment Scripts Deep Dive](docs/experiment-scripts.md).*

| Script | Use Case |
|---|---|
| `run_experiment.sh` | Quick run: GPU metrics + CPU stats only, no network tracing |
| `run_experiment_bcc.sh` | Full benchmark: includes BCC kernel-level RX byte tracing — **recommended** |

### Build Docker Images

Do this once (or after changes to Dockerfiles):

```bash
cd ffmpeg_hpe/
docker compose build
```

### Run a Benchmark

```bash
cd ffmpeg_hpe/

# AlphaPose on GPU (default)
./run_experiment_bcc.sh alphapose

# MoveNet on GPU
./run_experiment_bcc.sh movenet

# AlphaPose on CPU (override device)
HPE_DEVICE=CPU ./run_experiment_bcc.sh alphapose

# OpenPose on GPU
HPE_DEVICE=GPU ./run_experiment_bcc.sh openpose

# HigherHRNet on CPU
HPE_DEVICE=CPU ./run_experiment_bcc.sh hrnet

# EfficientHRNet variants
HPE_DEVICE=CPU ./run_experiment_bcc.sh ae1
HPE_DEVICE=CPU ./run_experiment_bcc.sh ae2
HPE_DEVICE=CPU ./run_experiment_bcc.sh ae3
```

### Configuring the Video Source

The video file to stream is controlled by the `VIDEO_FILE_NAME` variable in `ffmpeg_hpe/.env`:

```bash
# View current setting
cat ffmpeg_hpe/.env
# VIDEO_FILE_NAME=vga_01_01.mp4

# Edit .env to use a different video
echo "VIDEO_FILE_NAME=hd_00_00.mp4" > ffmpeg_hpe/.env

# Or export for a one-off run without editing .env
VIDEO_FILE_NAME=hd_00_00.mp4 ./run_experiment_bcc.sh alphapose
```

The `../videos/` directory is mounted read-only into the streamer container at `/data/`.

### Cleanup Between Runs

Always clean up before starting a new experiment to avoid stale containers or volumes:

```bash
cd ffmpeg_hpe/
docker compose down -v --remove-orphans
```

---

## 10. Results & Output

### Directory Structure

Results are saved to a timestamped directory inside `ffmpeg_hpe/`:

```
results_alphapose_AMD_EPYC_7551P_32-Core_20250428_120000/
├── container_timing.txt         # Startup time per container (seconds)
├── logs/
│   ├── hpe_startup.log          # HPE container early startup output
│   ├── hpe_startup_full.log     # Full HPE container log
│   ├── hpe_exit.log             # HPE container exit code (0 = clean, non-zero = crash)
│   ├── perf_monitor.log         # bpftrace perf monitor log
│   ├── bcc-tracer.log           # BCC tracer log (port detection, tracing events)
│   └── gpu-metrics.log          # GPU metrics collector log
├── perf/
│   ├── pid_metrics.csv          # Columns: timestamp, pid, cpu_percent, mem_rss_kb, tx_bytes*, rx_bytes*
│   ├── network_stats.csv        # Columns: timestamp, pid, interface, bytes, sent  ← TX data lives here
│   └── perf_metrics.csv         # Additional perf_monitor metrics
├── gpu/
│   └── gpu_metrics.csv          # Columns: timestamp, gpu_id, gpu_utilization, mem_utilization, temperature, power_usage
├── traces/bcc/
│   └── hpe_video_rx.csv         # Columns: timestamp_ms, rx_bytes (per 10ms interval)  ← RX data lives here
└── hpe_output/
    ├── *.csv                    # Keypoint data: frame, person_id, joint coordinates
    └── *.json                   # COCO-format keypoint export (if --json flag used)
```

> `*` The `tx_bytes` and `rx_bytes` columns in `pid_metrics.csv` are always `0` — this is intentional. Network data is collected separately by two different tools (see below).

### TX and RX Network Data — Where to Find It

Network measurement requires two different tools because TX and RX operate in different kernel contexts:

| Direction | Tool | Container | Mechanism | Output file |
|---|---|---|---|---|
| **TX** (HPE → outside) | `bpftrace sys_enter_sendto` in `monitor_pid.sh` | `perf_monitor` | Syscall tracepoint — fires in HPE process context, PID filter valid | `perf/network_stats.csv` (rows where `sent=1`) |
| **RX** (stream → HPE) | `bcc_rx_bytes.py` | `bcc-tracer` | BPF socket filter on the detected tracer interface, filtered by RTSP broker IP + ports | `traces/bcc/hpe_video_rx.csv` |
| ~~RX (attempted)~~ | ~~`bpftrace netif_receive_skb`~~ | ~~`perf_monitor`~~ | ~~Fires in softirq/kernel context — PID never matches HPE~~ | ~~Always ~0, ignore~~ |

**Why the split is necessary:** `sendto()` is a syscall made by the HPE process — the kernel knows the PID. Incoming packets are processed by the kernel network stack in softirq context *before* being associated with any process — PID filtering is impossible at that point. `bcc-tracer` works around this by filtering by IP+port instead, running in a container that shares HPE's network namespace (`network_mode: service:hpe`).

**Rule:** for RX data use `traces/bcc/hpe_video_rx.csv`. For TX data use `perf/network_stats.csv`. Never use the RX column from `pid_metrics.csv` — it is always `0` by design.

### Healthy Run Signals (what "good" looks like)

Before plotting anything, sanity-check the run with these four signals. If any one is wrong, plotting is wasted effort.

| Signal | Where to check | Expected for a 30s VGA `movenet` run | Red flag |
|---|---|---|---|
| **Clean exit** | `logs/hpe_exit.log` | `0` | Non-zero → HPE crashed; check `logs/hpe_startup_full.log` |
| **Frames processed** | `wc -l hpe_output/*.csv` | A few hundred to a few thousand rows | `0` rows → stream never connected; check `logs/hpe_startup_full.log` for `OpenCV: cap.open() failed` |
| **RX bytes captured** | `traces/bcc/hpe_video_rx.csv` | A few MB total over the run | `0` total → BCC filter didn't attach; check `logs/bcc-tracer.log` for `Permission denied` (kernel headers missing) or filter-mismatch messages |
| **CPU% non-zero** | `perf/pid_metrics.csv` column 3 | 30–80% during inference | All zeros → monitor sampled the wrong PID; check `logs/perf_monitor.log` |

### Reading the CSVs (column reference)

The four most important CSVs and what each column means:

```
perf/pid_metrics.csv
  timestamp        — unix epoch seconds (float)
  pid              — host-namespace PID of the python3 main.py process
  cpu_percent      — instantaneous CPU% from /proc/$PID/stat delta over 500ms
                     (NOT pidstat-style lifetime average — see fix #8 in AGENTS.md)
  mem_rss_kb       — resident set size from /proc/$PID/status
  tx_bytes         — ALWAYS 0 — see network_stats.csv instead
  rx_bytes         — ALWAYS 0 — see traces/bcc/hpe_video_rx.csv instead

perf/network_stats.csv         (TX only — use rows where sent=1)
  timestamp, pid, interface, bytes, sent

traces/bcc/hpe_video_rx.csv    (RX only)
  timestamp_ms     — millisecond unix epoch
  rx_bytes         — bytes received in the last 10ms BCC sampling window

gpu/gpu_metrics.csv
  timestamp, gpu_id, gpu_utilization (%), mem_utilization (%),
  temperature (°C), power_usage (W)

hpe_output/<timestamp>_<method>_*.csv
  frame, person_id, then 17 × (x, y, visibility) keypoint columns in COCO order
```

**Reading tip:** `pid_metrics.csv` and `gpu_metrics.csv` are sampled at 500 ms intervals; `hpe_video_rx.csv` is sampled at 10 ms. When correlating CPU/GPU/RX on the same plot, resample one of them or use `pandas.merge_asof` rather than naive joins.

### Quick Data Inspection

```bash
cd results_alphapose_*/

# Total video data received (MB)
awk -F, 'NR>1 {sum += $2} END {printf "%.2f MB\n", sum/1024/1024}' traces/bcc/hpe_video_rx.csv

# Average GPU utilization
awk -F, 'NR>1 {sum += $2; n++} END {printf "%.1f%%\n", sum/n}' gpu/gpu_metrics.csv

# Peak memory usage (MB)
awk -F, 'NR>1 {if ($3 > max) max=$3} END {print max " MB"}' perf/pid_metrics.csv

# Number of frames processed
wc -l hpe_output/*.csv

# Experiment duration (from RX trace)
head -2 traces/bcc/hpe_video_rx.csv && echo "..." && tail -1 traces/bcc/hpe_video_rx.csv
```

---

## 11. Plotting & Visualization

> *For detailed CSV formats and all plotting options, see [Plotting & Analysis Deep Dive](docs/plotting-analysis.md).*

| Script | Input File | Output |
|---|---|---|
| `ffmpeg_hpe/plot_smi_output.py` | `gpu/gpu_metrics.csv` | GPU utilization, temperature, memory, power PNGs |
| `ffmpeg_hpe/plot_rx_bytes_trimmed_reset.py` | `traces/bcc/hpe_video_rx.csv` | Network RX bytes timeline plot |
| `ffmpeg_hpe/plot_rx_bytes.py` | `traces/bcc/hpe_video_rx.csv` | Raw RX bytes plot |
| `monitor_hpe/plot_graph.py` | `perf/pid_metrics.csv` | CPU% + memory usage over time |
| `Measure_plot_cpu_perf/plot_perf_metrics.py` | perf stat CSV | CPU cycles + utilization bar chart |
| `Measure_gpu_dcgm/plot_smi_output.py` | gpu_metrics.csv | DCGM GPU metrics (alternative) |

### Example commands

```bash
cd ffmpeg_hpe/

# GPU plots for the most recent run
python3 plot_smi_output.py results_*/gpu/gpu_metrics.csv

# Network RX timeline (trimmed/reset for cleaner view)
python3 plot_rx_bytes_trimmed_reset.py results_*/traces/bcc/hpe_video_rx.csv

# CPU and memory plot
python3 ../monitor_hpe/plot_graph.py results_*/perf/pid_metrics.csv
```

---

## 12. Monitoring During Experiments

While an experiment is running, you can observe it in real time:

```bash
# Live GPU stats (updates every second)
watch nvidia-smi

# Docker container resource usage (CPU, mem, net, block I/O)
docker stats

# Follow HPE container logs live
docker logs -f hpe

# Follow BCC tracer logs
docker logs -f bcc-tracer

# System-wide resource overview
glances        # apt install glances
htop           # apt install htop

# Check which containers are running
docker ps
```

---

## 13. Troubleshooting

### Disk Space Filling Up

Docker images, volumes, and result files accumulate quickly. Check and clean regularly:

```bash
df -h                              # Check filesystem usage
docker system df                   # Docker-specific disk usage breakdown
docker system prune                # Remove stopped containers, dangling images
docker system prune -a --volumes   # Aggressive cleanup (removes ALL unused images)
```

> **Warning:** `prune -a` will remove cached image layers and force a full rebuild on the next `docker compose build`.

### File Permissions on Result Directories

Containers run as root. Output files may be owned by root on the host:

```bash
sudo chown -R $(whoami):$(whoami) ffmpeg_hpe/results*
sudo chown -R $(whoami):$(whoami) ffmpeg_hpe/tracer_output

# Pre-create directories with open permissions if running tools manually.
# run_experiment.sh removes and recreates tracer_output for normal runs.
mkdir -p ffmpeg_hpe/results ffmpeg_hpe/tracer_output
chmod 777 ffmpeg_hpe/results ffmpeg_hpe/tracer_output
```

### BCC Tracer Port Detection Failure

> *For BPF architecture, kernel requirements, and troubleshooting, see [BCC/BPF Tracing Deep Dive](docs/bcc-bpf-tracing.md).*

The BCC tracer resolves the RTSP broker IP, detects the tracer interface, and auto-detects the HPE source port for the exact broker connection. If it fails:

```bash
# Check what the tracer detected
docker logs bcc-tracer | grep -i "monitor\|detect\|port"

# Manually check connections inside the tracer container
docker exec bcc-tracer ss -ntp

# Check HPE container network connections
docker exec hpe ss -ntp | grep 8554
```

### Stream Connection Issues

```bash
# Get RTSP broker IP address
docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' rtsp-broker

# Test stream is accessible
ffprobe rtsp://rtsp-broker:8554/stream

# Verify stream from within the HPE container
docker exec hpe ffprobe rtsp://rtsp-broker:8554/stream
```

### HPE Container Exits Immediately

```bash
# Check exit logs
docker logs hpe

# Common causes:
# 1. Stream not ready — streaming server healthcheck failed
# 2. GPU not available — check nvidia-smi
# 3. Missing model file — check models/ directory
# 4. Python import error — check conda environment
```

### Stuck or Zombie Containers

```bash
# Stop everything cleanly
cd ffmpeg_hpe/
docker compose down -v --remove-orphans

# Force kill if compose down hangs
docker kill hpe bcc-tracer gpu-metrics perf_monitor 2>/dev/null || true
docker rm -f hpe bcc-tracer gpu-metrics perf_monitor 2>/dev/null || true
```

### GPU Not Available in Container

```bash
# Verify nvidia-container-toolkit is installed
which nvidia-container-runtime
docker info | grep -i runtime

# Test GPU access in a container
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu20.04 nvidia-smi

# If using CPU fallback, set:
export HPE_DEVICE=CPU
```

### AlphaPose Extension Build Failures

```bash
# Ensure you are in the correct conda environment
conda activate hpe

# Check CUDA version compatibility
nvcc --version
python -c "import torch; print(torch.version.cuda)"

# Clean and rebuild
python setup.py clean --all
bash models/AlphaPose/build_extensions.sh
```

---

## 14. Coding & Contribution Standards

### Python Style

- Python **3.8** syntax only.
- **4-space indentation**, Black-style formatting.
- **Type hints** where feasible on function signatures.
- **Explicit imports** — no wildcard `from module import *`.
- **Naming:** `snake_case` for files/functions/variables; `CapWords` for classes.
- Keep CLI flags consistent: `--long-option` with hyphen-separated names.

### Adding a New HPE Method

1. Create `your_method_hpe.py` in the repo root, inheriting from `BaseHPE` in `base_hpe.py`.
2. Implement `load_model()`, `run_inference(frame)`, and any I/O helpers.
3. Add your method to the `method_map` in `main.py`'s `get_hpe_method()` function.
4. Add a test using a sample image/video in `unit_tests/`.
5. Update `requirements.txt` with any new dependencies.

### Testing

```bash
# Smoke test — MoveNet on a sample image (fast, CPU)
python3 main.py --method movenet --input unit_tests/images/testImage.jpg --save_image --device CPU

# Smoke test — AlphaPose on sample images
python3 main.py --method alphapose --input unit_tests/images/ --json --device CPU

# Run unit tests (if any exist)
python3 -m pytest unit_tests/
```

### Commit Messages

```
Add HigherHRNet CPU benchmark support

Extends run_experiment_bcc.sh to accept hrnet as method.
Tested on AMD EPYC 7551P, ~8 FPS on CPU with 1080p input.
Refs #45
```

- First line: imperative, ≤72 characters.
- Body: explains *why* and any perf/accuracy impact.
- Reference issues with `Fixes #N` or `Refs #N`.

### Pull Requests Must Include

- Clear description of the change.
- Reproduction steps and command examples.
- Screenshots or short clips for visual changes.
- Notes on which model files are needed.
- For performance PRs: before/after metrics table with commands used.

---

## 15. Git Branches

| Branch | Purpose |
|---|---|
| `perf-tuning-base` | Performance tuning baseline — likely the most active branch |
| `main` | Upstream default / stable |
| `cuda-dev` | GPU/CUDA-specific optimizations |
| `feat/ov-epyc-4vcpu` | EPYC CPU-targeted OpenVINO configuration (4 vCPU) |
| `feat/openvino-opti-cpu` | CPU performance optimization with OpenVINO tuning |
| `hpe-benchmark` | Dedicated benchmark suite |
| `latest-alphapose-integration` | Latest AlphaPose integration work |

> Check `git log --oneline --all` to see current branch state and recent commits.

---

## 16. Tips for New Contributors

- **Always clean up** between runs: `docker compose down -v --remove-orphans`. Stale containers cause mysterious failures.
- **Pre-create output directories** with write permissions before running experiments — containers write as root.
- **Use `run_experiment_bcc.sh`** for production benchmarks: it collects the most comprehensive data (CPU, GPU, and network RX).
- **Check `df -h`** before long experiments — Docker image layers + results CSVs fill disk fast.
- **The `.env` file** in `ffmpeg_hpe/` controls which video file is streamed. Changing it is the easiest way to test different inputs without modifying scripts.
- **Model weights are NOT in git** — if someone clones fresh, they must download all weights before anything runs. See [Section 5](#5-downloading-pretrained-model-weights).
- **When comparing methods**, use the same video file, same hardware, and similar system load for fair comparison.
- **Save your results directories** — they contain all raw data needed for plotting and analysis later.
- **BCC tracing requires a real Linux kernel** — it will not work inside WSL2 or on macOS. Use a bare-metal Linux or a VM with kernel access.
- **GPU experiments default to `device=GPU`**; CPU experiments require explicitly setting `HPE_DEVICE=CPU` in the environment or passing `--device CPU`.
- **`cv2.setNumThreads(1)`** is set intentionally in `main.py` to prevent OpenCV from spinning up extra threads that would interfere with perf measurements.

---

## 17. Quick Start (TL;DR)

For someone who just wants to run their first benchmark as fast as possible:

```bash
# 1. Clone the repo and enter it
git clone <repo-url> MeasurementsDTs
cd MeasurementsDTs

# 2. Download model weights (see Section 5 for full list)
wget "https://drive.google.com/uc?export=download&id=1p6bi10UybpUIcq5D2XDsgQRLPJIr2RyI" \
  -O models/AlphaPose/pretrained_models/fast_res50_256x192.pth
# ... (download all other models)

# 3. Set up Python environment
conda create -n hpe python=3.8.10 -y && conda activate hpe
conda install pytorch==2.4.1 torchvision==0.19.1 -c pytorch
conda install --file requirements.txt
bash models/AlphaPose/build_extensions.sh

# 4. Configure the video source
echo "VIDEO_FILE_NAME=vga_01_01.mp4" > ffmpeg_hpe/.env

# 5. Build Docker images
cd ffmpeg_hpe/
docker compose build

# 6. Run your first experiment
./run_experiment_bcc.sh alphapose

# Wait for the experiment to complete (~duration of the video)...
# Results land in: results_alphapose_<cpu-model>_<timestamp>/

# 7. Plot the results
python3 plot_smi_output.py results_*/gpu/gpu_metrics.csv
python3 plot_rx_bytes_trimmed_reset.py results_*/traces/bcc/hpe_video_rx.csv
python3 ../monitor_hpe/plot_graph.py results_*/perf/pid_metrics.csv
```

---

## Appendix A: Glossary

Unfamiliar term? Look it up here. Listed in the order a newcomer is most likely to encounter them.

| Term | Meaning in this project |
|---|---|
| **HPE** | Human Pose Estimation — the task of locating body keypoints (joints) in an image. This repo does **2D** HPE (pixel coordinates), not 3D. |
| **Keypoint** | A single body landmark (e.g. left elbow). Each one has `(x, y, visibility)`. |
| **COCO format** | The de-facto JSON schema for keypoint datasets. Uses 17 keypoints per person in a fixed joint order. All backends here output COCO-compatible data. |
| **Backend / Method** | One of the five HPE implementations: `alphapose`, `movenet`, `openpose`, `hrnet`, `ae1/2/3`. They all conform to the [BaseHPE](file:///c:/Users/bigbu/Downloads/MeasurementsDTs/base_hpe.py) abstract class. |
| **OpenVINO** | Intel's inference runtime. Used by every backend except AlphaPose. Loads `.xml` + `.bin` IR model files and runs them efficiently on CPU/iGPU. |
| **PyTorch** | The other inference runtime, used only by AlphaPose. Loads `.pth` weight files; needs CUDA for GPU acceleration. |
| **AlphaPose** | A top-down HPE backend: a YOLOv3 detector finds people, then a ResNet-50 pose network locates keypoints inside each box. GPU strongly preferred. |
| **MoveNet** | A lightweight single-stage HPE model from Google, run here via OpenVINO on CPU. |
| **RTSP** | Real-Time Streaming Protocol — the streaming protocol used between the producer and the HPE consumer in this benchmarking platform. |
| **MediaMTX** | The RTSP broker (`bluenviron/mediamtx:1-ffmpeg` image) that mediates between the FFmpeg producer and HPE consumer. Listens on port 8554. |
| **NVENC** | NVIDIA's hardware H.264 encoder, used by FFmpeg in the `streamer` container to produce the video stream without burning CPU. |
| **Streamer / Producer** | The `video-producer` container running FFmpeg/NVENC; reads a local video file and publishes it as an RTSP stream. |
| **HPE container** | The main inference container running `python3 main.py`. Reads from RTSP, writes keypoint CSVs. |
| **Sidecar** | A monitoring container that runs alongside the HPE container without affecting its work. Examples: `perf_monitor`, `bcc-tracer`, `gpu-metrics`. |
| **bpftrace** | A high-level eBPF tracing language. Used in `perf_monitor` to count `sendto()` syscalls (TX bytes) per HPE PID. |
| **BCC** | BPF Compiler Collection — a Python toolkit for writing eBPF programs. Used by `bcc-tracer` to count incoming TCP bytes via a socket filter. |
| **eBPF / BPF** | Kernel sandbox that runs small verified programs at hook points (syscalls, network events). Both bpftrace and BCC compile down to BPF. |
| **PID filter** | Filtering events by process ID. Works for `sendto()` (syscall context) but **not** for incoming packets (softirq context) — see the TX vs RX section. |
| **Network namespace** | Linux feature that gives a container its own network stack. `bcc-tracer` uses `network_mode: service:hpe` so it sees the same eth0 as HPE. |
| **DCGM** | NVIDIA Data Center GPU Manager — used in some standalone tools (`Measure_gpu_dcgm/`) for GPU power/temp/util data. The main rig uses plain `nvidia-smi`. |
| **FFmpeg** | The Swiss-army-knife multimedia tool. Used by the streamer container to produce video. Optional GPU build via `build_ffmpeg_cuda.sh`. |
| **`pid_metrics.csv`** | Output of `perf_monitor`: per-PID CPU% / RAM. Old name (`aggregated_metrics.csv`) appears in older docs — those are stale. |
| **`hpe_video_rx.csv`** | Output of `bcc-tracer`: incoming bytes from the RTSP stream, per 10ms window. |
| **Padding / Pad-and-resize** | Letterbox preprocessing inside `BaseHPE` so that any input resolution becomes the model's expected size without distorting aspect ratio. |
| **Experiment rig** | A self-contained subdirectory (`monitor_hpe/`, `ffmpeg_hpe/`, `recent-dash/`) with its own `run_experiment.sh` and `docker-compose.yaml`. |
| **Cloud GPU VM** | The canonical deployment target documented in this repo: **8 vCPU + 16 GB RAM + RTX A4000, EPYC 7551P host**. The [optimizations/](file:///c:/Users/bigbu/Downloads/MeasurementsDTs/optimizations) scripts were originally calibrated for a 4 vCPU SKU; their runtime auto-detector adapts to the actual core count present on the host. |

---

*Have questions? Read the code — it's well-structured and the CLI help (`python3 main.py --help`) is a good starting point.*
