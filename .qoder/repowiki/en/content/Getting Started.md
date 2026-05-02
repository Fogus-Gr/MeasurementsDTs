# Getting Started

<cite>
**Referenced Files in This Document**
- [README.md](file://README.md)
- [ONBOARDING.md](file://ONBOARDING.md)
- [requirements.txt](file://requirements.txt)
- [setup.py](file://setup.py)
- [models/AlphaPose/build_extensions.sh](file://models/AlphaPose/build_extensions.sh)
- [models/AlphaPose/pretrained_models/256x192_res50_lr1e-3_1x.yaml](file://models/AlphaPose/pretrained_models/256x192_res50_lr1e-3_1x.yaml)
- [main.py](file://main.py)
- [base_hpe.py](file://base_hpe.py)
- [openvino_base_hpe.py](file://openvino_base_hpe.py)
- [movenet_hpe.py](file://movenet_hpe.py)
- [alphapose_hpe.py](file://alphapose_hpe.py)
- [dev_tools/smoke_test.sh](file://dev_tools/smoke_test.sh)
- [build_ffmpeg_cuda.sh](file://build_ffmpeg_cuda.sh)
- [check_stream_compat.sh](file://check_stream_compat.sh)
- [ffmpeg_hpe/docker-compose.yaml](file://ffmpeg_hpe/docker-compose.yaml)
</cite>

## Update Summary
**Changes Made**
- Added comprehensive ONBOARDING.md guidance with step-by-step setup instructions
- Enhanced environment setup documentation with detailed prerequisites and requirements
- Expanded model download instructions with specific file paths and verification steps
- Added Docker-based experiment pipeline documentation with monitoring capabilities
- Included troubleshooting guides for common setup and runtime issues
- Updated performance optimization documentation with CPU tuning guidelines

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Installation and Setup](#installation-and-setup)
6. [Model Download and Configuration](#model-download-and-configuration)
7. [Basic Usage Examples](#basic-usage-examples)
8. [Experiment Pipeline](#experiment-pipeline)
9. [Performance Optimization](#performance-optimization)
10. [Verification and Testing](#verification-and-testing)
11. [Troubleshooting Guide](#troubleshooting-guide)
12. [Conclusion](#conclusion)

## Introduction
This comprehensive guide provides complete setup instructions for the Human Pose Estimation framework, incorporating the new ONBOARDING.md documentation. The framework supports multiple state-of-the-art methods including AlphaPose, MoveNet, OpenPose, HigherHRNet, and EfficientHRNet variants. It offers both local execution and Docker-based benchmarking capabilities with comprehensive performance monitoring.

**Updated** Enhanced with detailed onboarding procedures from the comprehensive ONBOARDING.md guide, providing step-by-step instructions for environment setup, model configuration, and experiment execution.

## Project Structure
The repository provides a complete HPE benchmarking system with modular components:

```mermaid
graph TB
A["main.py<br/>CLI entrypoint"] --> B["BaseHPE<br/>shared base"]
B --> C["MoveNetHPE<br/>movenet_hpe.py"]
B --> D["OpenVINOBaseHPE<br/>openvino_base_hpe.py"]
B --> E["AlphaPoseHPE<br/>alphapose_hpe.py"]
D --> F["OpenVINO models<br/>models/OpenVINO/pretrained_models"]
E --> G["AlphaPose models<br/>models/AlphaPose/pretrained_models"]
H["Experiment Pipeline<br/>ffmpeg_hpe/"] --> I["Docker Compose<br/>Multi-service orchestration"]
J["Monitoring Tools"] --> K["GPU Metrics<br/>nvidia-smi polling"]
J --> L["CPU Monitoring<br/>bpftrace/perf"]
J --> M["Network Tracing<br/>BCC/BPF"]
```

**Diagram sources**
- [main.py:51-200](file://main.py#L51-L200)
- [base_hpe.py:88-630](file://base_hpe.py#L88-L630)
- [movenet_hpe.py:12-111](file://movenet_hpe.py#L12-L111)
- [openvino_base_hpe.py:55-395](file://openvino_base_hpe.py#L55-L395)
- [alphapose_hpe.py:33-334](file://alphapose_hpe.py#L33-L334)

**Section sources**
- [README.md:63-231](file://README.md#L63-L231)
- [ONBOARDING.md:63-142](file://ONBOARDING.md#L63-L142)

## Core Components
The framework consists of several key components working together:

- **CLI Entry Point**: Parses arguments, selects method, loads model, and manages processing loops
- **BaseHPE**: Common logic for input handling, preprocessing, inference timing, and output generation
- **Method-Specific Classes**: Specialized implementations for each HPE algorithm
- **Experiment Pipeline**: Docker-based benchmarking with comprehensive monitoring
- **Monitoring Stack**: CPU, GPU, and network performance tracking

Key capabilities include automatic video property detection, HTTP stream support, JSON/COCO CSV export, and optional visualization output.

**Section sources**
- [main.py:51-200](file://main.py#L51-L200)
- [base_hpe.py:88-630](file://base_hpe.py#L88-L630)
- [ONBOARDING.md:285-301](file://ONBOARDING.md#L285-L301)

## Architecture Overview
The system provides both local execution and containerized benchmarking:

```mermaid
sequenceDiagram
participant U as "User"
participant M as "main.py"
participant B as "BaseHPE"
participant H as "MethodHPE"
participant V as "Input Source"
U->>M : "python3 main.py --method <method> --input <src>"
M->>M : "parse_arguments()"
M->>M : "get_hpe_method(args)"
M->>H : "load_model()"
H->>B : "initialize BaseHPE(...)"
U->>M : "run main_loop/main_loop_with_timeout"
M->>B : "process_frame(frame)"
B->>H : "pad_and_resize(frame)"
H->>H : "run_model(padded)"
H-->>B : "predictions"
B->>H : "postprocess(predictions)"
H-->>B : "bodies"
B-->>U : "render/save outputs"
```

**Diagram sources**
- [main.py:51-200](file://main.py#L51-L200)
- [base_hpe.py:405-519](file://base_hpe.py#L405-L519)

## Installation and Setup

### Prerequisites
The framework requires specific hardware and software prerequisites:

- **Operating System**: Ubuntu 20.04 (tested and recommended)
- **Python**: 3.8.10 with conda environment support
- **CUDA**: Toolkit 12.6 for GPU acceleration
- **Docker**: Docker Engine + Docker Compose v20+ for containerized experiments
- **Hardware**: NVIDIA GPU with CUDA support (CPU-only mode also supported)

### Environment Setup Options

#### Option A: Conda Environment (Recommended)
```bash
# Create and activate environment
conda create -n hpe python=3.8.10 -y
conda activate hpe

# Install PyTorch with CUDA support
conda install pytorch==2.4.1 torchvision==0.19.1 -c pytorch

# Install all remaining dependencies
conda install --file requirements.txt
```

#### Option B: pip + virtualenv
```bash
python3 -m venv myenv
source myenv/bin/activate
pip install -r requirements.txt
```

**Section sources**
- [ONBOARDING.md:148-167](file://ONBOARDING.md#L148-L167)
- [ONBOARDING.md:170-223](file://ONBOARDING.md#L170-L223)
- [README.md:7-17](file://README.md#L7-L17)

### AlphaPose Extension Building
AlphaPose requires compiled Cython and CUDA extensions:

```bash
# Recommended: use the build script (handles CPU/GPU detection automatically)
bash models/AlphaPose/build_extensions.sh

# Alternative: build in-place
python setup.py build_ext --inplace
```

**Section sources**
- [ONBOARDING.md:194-207](file://ONBOARDING.md#L194-L207)
- [models/AlphaPose/build_extensions.sh:1-25](file://models/AlphaPose/build_extensions.sh#L1-L25)
- [setup.py:1-37](file://setup.py#L1-L37)

## Model Download and Configuration

### Downloading Pretrained Model Weights
Model files are not included in the repository and must be downloaded manually:

#### AlphaPose Models
```bash
# ResNet50 pose estimation weights
wget "https://drive.google.com/uc?export=download&id=1p6bi10UybpUIcq5D2XDsgQRLPJIr2RyI" \
  -O models/AlphaPose/pretrained_models/fast_res50_256x192.pth

# YOLOv3 person detector weights
wget "https://drive.google.com/uc?export=download&id=1k-9cUGcdH5ZFN1NcMvZrO0ApW241tboD" \
  -O models/AlphaPose/detector/yolo/data/yolov3-spp.weights
```

#### MoveNet Model
```bash
wget "https://drive.google.com/uc?export=download&id=15SZwY2jAh1KqHwT-YO6_UByOsQD70RSr" \
  -O models/MoveNet/movenet_multipose_lightning_256x256_FP32.bin
```

#### OpenPose Model
```bash
wget "https://drive.google.com/uc?export=download&id=1VNucIyIsdaiw1cYt-JGqBWloVu2TVdsm" \
  -O models/OpenVINO/pretrained_models/intel/human-pose-estimation-0001/human-pose-estimation-0001.bin
```

#### HigherHRNet Model
```bash
wget "https://drive.google.com/uc?export=download&id=1fko47eVczJZQb9wWA2X7eQ0TuF4PDXzs" \
  -O models/OpenVINO/pretrained_models/public/FP32/higher-hrnet-w32-human-pose-estimation.bin
```

#### EfficientHRNet Variants
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

**Section sources**
- [ONBOARDING.md:225-282](file://ONBOARDING.md#L225-L282)
- [README.md:22-63](file://README.md#L22-L63)

## Basic Usage Examples

### Local Execution Examples
Run the following examples after setting up the environment and downloading models:

#### MoveNet Single Image
```bash
python3 main.py --method movenet --input unit_tests/images/testImage.jpg --save_image
```

#### AlphaPose Directory Processing
```bash
python3 main.py --method alphapose --input unit_tests/images/ --json
```

#### EfficientHRNet Video Processing
```bash
python3 main.py --method ae1 --input unit_tests/video/giphy.gif --save_video
```

#### HTTP Stream Processing
```bash
python3 main.py --method movenet --input http://192.168.1.10:8089/stream.h264 --device CPU
```

#### AlphaPose with Custom Settings
```bash
python3 main.py --method alphapose --input video.mp4 --csv --device GPU --output_dir results/
```

### All CLI Flags
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

**Section sources**
- [ONBOARDING.md:303-356](file://ONBOARDING.md#L303-L356)
- [ONBOARDING.md:329-345](file://ONBOARDING.md#L329-L345)
- [README.md:83-114](file://README.md#L83-L114)

## Experiment Pipeline

### Docker-Based Benchmarking Architecture
The framework provides comprehensive containerized benchmarking with multi-service orchestration:

```mermaid
graph TD
A["h264-streaming-server<br/>FFmpeg/NGINX, :8089"] --> B["H.264 HTTP Stream"]
B --> C["hpe Container<br/>Python + OpenCV + Pose Estimation"]
C --> D["perf_monitor<br/>bpftrace CPU/memory"]
C --> E["bcc-tracer<br/>BPF network tracing"]
C --> F["gpu-metrics<br/>nvidia-smi polling"]
D --> G["aggregated_metrics.csv"]
E --> H["video_rx.csv"]
F --> I["gpu_metrics.csv"]
C --> J["hpe_output/*.csv"]
```

**Diagram sources**
- [ONBOARDING.md:361-427](file://ONBOARDING.md#L361-L427)

### Docker Services Configuration
The experiment pipeline consists of five coordinated services:

#### 1. h264-streaming-server
- **Purpose**: Serves benchmark video as H.264 HTTP stream on port 8089
- **Resource Limits**: 2 CPU cores, 1 GB RAM
- **Configuration**: `VIDEO_FILE` from `.env`, `SERVER_PORT=8089`
- **Healthcheck**: TCP connection to port 8089

#### 2. hpe Container
- **Purpose**: Main inference container running pose estimation
- **Resource Limits**: 4 CPU cores, 16 GB RAM, NVIDIA GPU (via `runtime: nvidia`)
- **Shared Memory**: 8 GB (`shm_size`) for large batch operations
- **Command**: `python3 main.py --method <METHOD> --input http://h264-streaming-server:8089/stream.h264`

#### 3. gpu-metrics Sidecar
- **Purpose**: Polls `nvidia-smi` every 500ms for GPU statistics
- **Output**: `results/gpu/gpu_metrics.csv`
- **Requirements**: NVIDIA GPU and `nvidia-container-toolkit`

#### 4. perf_monitor Sidecar
- **Purpose**: Monitors CPU usage and memory RSS via bpftrace
- **Output**: `results/perf/aggregated_metrics.csv`
- **Privileges**: `privileged: true`, `SYS_ADMIN`, `NET_ADMIN`

#### 5. bcc-tracer Sidecar
- **Purpose**: Kernel-level network RX byte tracing using BCC/BPF
- **Output**: `tracer_output/hpe_video_rx.csv`
- **Network Mode**: Shares HPE container's network namespace

### Experiment Execution Flow
The `run_experiment_bcc.sh` script orchestrates the complete benchmarking process:

1. **Timestamp Generation**: Creates unique results directory name
2. **Directory Creation**: Sets up `logs/`, `perf/`, `gpu/`, `traces/bcc/`, `hpe_output/` subdirectories
3. **Container Cleanup**: Removes previous containers and volumes
4. **Service Startup**: Starts streaming server with health checks
5. **Monitoring Services**: Launches perf, GPU, and BCC monitoring sidecars
6. **Inference Execution**: Runs HPE container with configured method and device
7. **Data Collection**: Copies CSV files from Docker volumes to host
8. **Timing Capture**: Writes per-container startup times
9. **Cleanup**: Tears down all containers

**Section sources**
- [ONBOARDING.md:359-443](file://ONBOARDING.md#L359-L443)
- [ONBOARDING.md:446-520](file://ONBOARDING.md#L446-L520)

## Performance Optimization

### CPU Performance Tuning
The framework includes automated CPU optimization for OpenVINO inference:

```bash
python3 optimizations/optimized_main.py --method openpose --input video.mp4 --device CPU --enable-cpu-opt
```

Key optimizations include:
- Automatic CPU topology detection
- Optimal thread/stream configuration calculation
- Performance mode selection (latency vs throughput)
- CPU pinning and hyper-threading control

### GPU Acceleration Setup
For GPU-enabled environments:
- Ensure NVIDIA drivers support CUDA 12.8
- Verify `nvidia-container-toolkit` installation
- Use `HPE_DEVICE=GPU` environment variable for explicit GPU selection
- Monitor GPU utilization with `nvidia-smi`

### FFmpeg CUDA Integration
Optional FFmpeg build with hardware acceleration:
```bash
bash build_ffmpeg_cuda.sh
```

This script builds FFmpeg with CUDA/NPP/NVENC support for improved pipeline throughput.

**Section sources**
- [ONBOARDING.md:511-520](file://ONBOARDING.md#L511-L520)
- [ONBOARDING.md:570-598](file://ONBOARDING.md#L570-L598)
- [build_ffmpeg_cuda.sh:1-200](file://build_ffmpeg_cuda.sh#L1-L200)

## Verification and Testing

### Smoke Test Execution
Use the smoke test script to verify environment setup:

```bash
# Basic smoke test (CPU)
bash dev_tools/smoke_test.sh CPU hpe

# GPU smoke test (if available)
bash dev_tools/smoke_test.sh GPU hpe
```

The smoke test validates:
- MoveNet single image processing
- AlphaPose directory processing (if models present)
- EfficientHRNet video processing

### Local Development Server
For HTTP stream testing, use the included Flask server:

```bash
# Terminal 1: Start local stream server
python3 dev_tools/stream_video_server.py

# Terminal 2: Process stream with HPE
python3 main.py --method movenet --input http://$(hostname -I | awk '{print $1}'):8080/video_feed --save_video
```

### Docker Experiment Validation
Run a simple experiment to validate the containerized setup:

```bash
cd ffmpeg_hpe/
./run_experiment_bcc.sh movenet
```

**Section sources**
- [dev_tools/smoke_test.sh:1-42](file://dev_tools/smoke_test.sh#L1-L42)
- [ONBOARDING.md:346-356](file://ONBOARDING.md#L346-L356)

## Troubleshooting Guide

### Common Setup Issues

#### Disk Space Management
Docker images and results can consume significant disk space:
```bash
df -h                              # Check filesystem usage
docker system df                   # Docker-specific disk usage
docker system prune                # Remove stopped containers, dangling images
docker system prune -a --volumes   # Aggressive cleanup (removes ALL unused images)
```

#### File Permissions
Container output files may be owned by root:
```bash
sudo chown -R $(whoami):$(whoami) ffmpeg_hpe/results*
sudo chown -R $(whoami):$(whoami) ffmpeg_hpe/tracer_output
```

#### GPU Availability Issues
Verify GPU access and container configuration:
```bash
# Check nvidia-container-toolkit installation
which nvidia-container-runtime
docker info | grep -i runtime

# Test GPU access in container
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu20.04 nvidia-smi
```

### Model Loading Problems
- Verify model files are downloaded to correct locations
- Check AlphaPose YAML configuration references correct weights
- Ensure OpenVINO XML paths match available model files

### Stream Connection Issues
```bash
# Get streaming server IP address
docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' h264-streaming-server

# Test stream accessibility
curl -I http://172.18.0.2:8089/stream.h264
ffprobe http://172.18.0.2:8089/stream.h264
```

### Container Lifecycle Issues
```bash
# Clean shutdown
cd ffmpeg_hpe/
docker compose down -v --remove-orphans

# Force cleanup if needed
docker kill hpe bcc-tracer gpu-metrics perf_monitor 2>/dev/null || true
docker rm -f hpe bcc-tracer gpu-metrics perf_monitor 2>/dev/null || true
```

**Section sources**
- [ONBOARDING.md:627-740](file://ONBOARDING.md#L627-L740)

## Conclusion
You now have comprehensive guidance for setting up and using the Human Pose Estimation framework. The ONBOARDING.md documentation provides detailed step-by-step instructions for environment setup, model configuration, and experiment execution. Whether running locally or using the Docker-based benchmarking pipeline, the framework offers extensive monitoring capabilities and performance optimization features. Use the provided verification steps and troubleshooting guidance to ensure a smooth setup experience.

The framework supports multiple HPE methods with flexible deployment options, making it suitable for both development and production benchmarking scenarios. The comprehensive monitoring stack enables detailed performance analysis across CPU, GPU, and network domains.