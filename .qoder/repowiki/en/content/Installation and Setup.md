# Installation and Setup

<cite>
**Referenced Files in This Document**
- [README.md](file://README.md)
- [requirements.txt](file://requirements.txt)
- [requirements_torch_cpu.txt](file://requirements_torch_cpu.txt)
- [Dockerfile_base](file://Dockerfile_base)
- [Dockerfile.hpe](file://Dockerfile.hpe)
- [docker-compose.yml](file://docker-compose.yml)
- [ffmpeg_hpe/docker-compose.yaml](file://ffmpeg_hpe/docker-compose.yaml)
- [monitor_hpe/docker-compose.yaml](file://monitor_hpe/docker-compose.yaml)
- [ffmpeg_hpe/run_experiment.sh](file://ffmpeg_hpe/run_experiment.sh)
- [dev_tools/install_from_readme.sh](file://dev_tools/install_from_readme.sh)
- [main.py](file://main.py)
- [base_hpe.py](file://base_hpe.py)
- [openvino_base_hpe.py](file://openvino_base_hpe.py)
- [packages.txt](file://packages.txt)
- [setup.py](file://setup.py)
- [entrypoint.sh](file://entrypoint.sh)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [System Requirements](#system-requirements)
3. [Prerequisites Verification](#prerequisites-verification)
4. [Local Development Installation](#local-development-installation)
5. [Docker Configuration](#docker-configuration)
6. [Model Download and Placement](#model-download-and-placement)
7. [Environment Setup](#environment-setup)
8. [Deployment Scenarios](#deployment-scenarios)
9. [Validation Steps](#validation-steps)
10. [Troubleshooting Guide](#troubleshooting-guide)
11. [Performance Considerations](#performance-considerations)
12. [Conclusion](#conclusion)

## Introduction

The MeasurementsDTs project is a comprehensive 2D Human Pose Estimation platform supporting five backends: AlphaPose, OpenPose, HigherHRNet, EfficientHRNet, and MoveNet. It provides both inference capabilities and a sophisticated performance benchmarking platform with Docker-based experiment rigs for measuring inference throughput, CPU/GPU utilization, memory consumption, and network bandwidth under realistic streaming conditions.

This documentation provides complete installation and setup instructions for the MeasurementsDTs project, covering system requirements, dependency installation, model configuration, environment setup, and deployment options for local development, containerized environments, and cloud deployments.

## System Requirements

The project requires specific versions of key components to ensure compatibility and optimal performance:

### Operating System
- **Ubuntu 20.04** - Primary supported Linux distribution

### Core Dependencies
- **Python 3.8.10** - Exact version required for compatibility
- **OpenVINO 2024.2.0** - Neural inference optimization framework
- **PyTorch 2.4.1+cu121** - Machine learning framework with CUDA support
- **CUDA Toolkit 12.6** - NVIDIA GPU computing platform
- **NVIDIA GPU** - Any CUDA-capable GPU required for GPU acceleration

### Additional Requirements
- **Docker Engine** - Required for containerized deployments
- **Docker Compose** - For multi-container orchestration
- **NVIDIA Container Toolkit** - For GPU-enabled containers
- **Git** - For cloning the repository

**Section sources**
- [README.md:7-16](file://README.md#L7-L16)

## Prerequisites Verification

Before installation, verify your system meets all requirements:

### Hardware Requirements
```bash
# Check GPU compatibility
nvidia-smi

# Verify CUDA installation
nvcc --version

# Check available memory
free -h
```

### Software Requirements
```bash
# Verify Ubuntu version
lsb_release -a

# Check Python version
python3 --version

# Verify Docker installation
docker --version
docker compose version
```

### Driver and Kernel Verification
```bash
# Check NVIDIA driver version
cat /proc/driver/nvidia/version

# Verify kernel modules
lsmod | grep nvidia

# Check BPF support (required for network tracing)
grep CONFIG_BPF /boot/config-$(uname -r)
```

**Section sources**
- [packages.txt:1-1703](file://packages.txt#L1-L1703)

## Local Development Installation

### Step 1: Environment Setup

Create and activate a dedicated Conda environment:

```bash
# Remove any existing environment
conda env remove -n hpe

# Create new environment with exact Python version
conda create -n hpe python=3.8.10 -y

# Activate environment
conda activate hpe
```

### Step 2: Install PyTorch and Dependencies

```bash
# Install PyTorch with CUDA 12.1 support
conda install pytorch==2.4.1 torchvision==0.19.1 -c pytorch -y

# Install remaining dependencies
conda install --file requirements.txt -y
```

### Step 3: Build AlphaPose Extensions

```bash
# Navigate to AlphaPose directory
cd models/AlphaPose

# Build Cython extensions
bash build_extensions.sh

# Alternative build method
python setup.py build_ext --inplace
```

### Step 4: Verify Installation

```bash
# Test basic imports
python3 -c "import torch; import openvino; import cv2; print('All imports successful')"
```

**Section sources**
- [README.md:158-172](file://README.md#L158-L172)
- [dev_tools/install_from_readme.sh:1-39](file://dev_tools/install_from_readme.sh#L1-L39)
- [setup.py:1-37](file://setup.py#L1-L37)

## Docker Configuration

### Base Docker Image

The project provides optimized Docker images with all dependencies pre-installed:

```dockerfile
FROM pytorch/pytorch:2.4.1-cuda12.1-cudnn9-devel

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc-9 g++-9 \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libgomp1 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libfontconfig1 \
    libice6 \
    curl \
    iputils-ping \
    dnsutils \
    python3-tk \
    ffmpeg \
    tcpdump \
    cmake \
    git

# Install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Install PyNvCodec for hardware acceleration
RUN pip install --no-cache-dir "setuptools<70" wheel scikit-build && \
    git clone --depth 1 https://github.com/NVIDIA/VideoProcessingFramework.git && \
    cd VideoProcessingFramework && \
    pip install --no-build-isolation --no-cache-dir . && \
    pip install --no-build-isolation --no-cache-dir src/PytorchNvCodec && \
    cd .. && rm -rf VideoProcessingFramework

# Install OpenVINO with GPU support
RUN pip install --no-cache-dir openvino-dev[onnx,tensorflow2,pytorch,caffe]==2024.4.0

# Set CUDA architecture
ENV TORCH_CUDA_ARCH_LIST=8.6
```

### Docker Compose Services

The project includes multiple Docker Compose configurations for different use cases:

#### Performance Benchmarking Stack
```yaml
version: '3.8'

services:
  rtsp-broker:
    image: bluenviron/mediamtx:1-ffmpeg
    ports:
      - "8554:8554"
      - "8888:8888"

  streamer:
    image: jrottenberg/ffmpeg:4.4-nvidia
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - NVIDIA_DRIVER_CAPABILITIES=video,compute,utility

  hpe:
    build: .
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - CUDA_VISIBLE_DEVICES=0
      - OPENCV_FFMPEG_DEBUG=1
      - OPENCV_LOG_LEVEL=DEBUG
      - PYTHONUNBUFFERED=1
      - PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:32

  gpu-metrics:
    build: ./Dockerfile.gpu_metrics
    environment:
      - NVIDIA_VISIBLE_DEVICES=all

  perf_monitor:
    build: ../recent-dash/perf_monitor
    pid: host
    cap_add:
      - SYS_ADMIN
      - NET_ADMIN
      - NET_RAW
      - IPC_LOCK

  bcc-tracer:
    build: ./bpftrace-tracer
    network_mode: "service:hpe"
    privileged: true
    cap_add:
      - SYS_ADMIN
      - NET_ADMIN
      - NET_RAW
      - IPC_LOCK
      - SYS_RESOURCE
```

**Section sources**
- [Dockerfile_base:1-93](file://Dockerfile_base#L1-L93)
- [Dockerfile.hpe:1-122](file://Dockerfile.hpe#L1-L122)
- [docker-compose.yml:1-30](file://docker-compose.yml#L1-L30)
- [ffmpeg_hpe/docker-compose.yaml:1-239](file://ffmpeg_hpe/docker-compose.yaml#L1-L239)
- [monitor_hpe/docker-compose.yaml:1-60](file://monitor_hpe/docker-compose.yaml#L1-L60)

## Model Download and Placement

### Required Models

The project requires downloading pretrained models for each supported backend:

#### AlphaPose Models
```bash
# Download AlphaPose weights
wget "https://drive.google.com/uc?export=download&id=1p6bi10UybpUIcq5D2XDsgQRLPJIr2RyI" \
  -O models/AlphaPose/pretrained_models/fast_res50_256x192.pth

wget "https://drive.google.com/uc?export=download&id=1k-9cUGcdH5ZFN1NcMvZrO0ApW241tboD" \
  -O models/AlphaPose/detector/yolo/data/yolov3-spp.weights
```

#### MoveNet Model
```bash
# Download MoveNet weights
wget "https://drive.google.com/uc?export=download&id=15SZwY2jAh1KqHwT-YO6_UByOsQD70RSr" \
  -O models/MoveNet/movenet_multipose_lightning_256x256_FP32.bin
```

#### OpenVINO Models
```bash
# Download OpenVINO models
wget "https://drive.google.com/uc?export=download&id=1VNucIyIsdaiw1cYt-JGqBWloVu2TVdsm" \
  -O models/OpenVINO/pretrained_models/intel/human-pose-estimation-0001/human-pose-estimation-0001.bin

wget "https://drive.google.com/uc?export=download&id=1fko47eVczJZQb9wWA2X7eQ0TuF4PDXzs" \
  -O models/OpenVINO/pretrained_models/public/FP32/higher-hrnet-w32-human-pose-estimation.bin

wget "https://drive.google.com/uc?export=download&id=1lEUFqQnWHVymQoZvaXuDFcnOyEEKsexP" \
  -O models/OpenVINO/pretrained_models/public/human-pose-estimation-0005/FP32/human-pose-estimation-0005.bin

wget "https://drive.google.com/uc?export=download&id=1d8pGQrM9vEfz_oAIey0qRr7Gxp6dS2UE" \
  -O models/OpenVINO/pretrained_models/public/human-pose-estimation-0006/FP32/human-pose-estimation-0006.bin

wget "https://drive.google.com/uc?export=download&id=1ZSdsqgD4zUO4gyHMYBfxq3m4UMyQ187j" \
  -O models/OpenVINO/pretrained_models/public/human-pose-estimation-0007/FP32/human-pose-estimation-0007.bin
```

### Model Directory Structure

```
models/
├── AlphaPose/
│   ├── pretrained_models/
│   │   └── fast_res50_256x192.pth
│   └── detector/
│       └── yolo/
│           └── data/
│               └── yolov3-spp.weights
├── MoveNet/
│   └── movenet_multipose_lightning_256x256_FP32.bin
└── OpenVINO/
    └── pretrained_models/
        ├── intel/
        │   └── human-pose-estimation-0001/
        │       └── human-pose-estimation-0001.bin
        ├── public/
        │   ├── FP32/
        │   │   └── higher-hrnet-w32-human-pose-estimation.bin
        │   ├── human-pose-estimation-0005/
        │   │   └── FP32/
        │   │   └── human-pose-estimation-0005.bin
        │   ├── human-pose-estimation-0006/
        │   │   └── FP32/
        │   │   └── human-pose-estimation-0006.bin
        │   └── human-pose-estimation-0007/
        │       └── FP32/
        │       └── human-pose-estimation-0007.bin
```

**Section sources**
- [README.md:115-156](file://README.md#L115-L156)

## Environment Setup

### Environment Variables

Configure essential environment variables for optimal performance:

```bash
# Set CUDA architecture (adjust for your GPU)
export TORCH_CUDA_ARCH_LIST=8.6

# OpenVINO configuration
export OV_THREADS=4
export OV_MODE=latency
export OV_CPU_PINNING=true
export OV_HYPER_THREADING=false

# GPU visibility
export NVIDIA_VISIBLE_DEVICES=all
export CUDA_VISIBLE_DEVICES=0

# OpenCV settings for RTSP streaming
export OPENCV_FFMPEG_DEBUG=1
export OPENCV_LOG_LEVEL=DEBUG
export OPENCV_FFMPEG_CAPTURE_OPTIONS=rtsp_transport;tcp
export OPENCV_FFMPEG_OPEN_TIMEOUT=300000
export OPENCV_FFMPEG_READ_TIMEOUT=300000
```

### Performance Tuning

#### CPU Configuration
```bash
# Disable hyperthreading for inference
echo "performance" | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# Pin threads to specific cores
taskset -c 0-7 python3 main.py --method movenet --input video.mp4
```

#### GPU Configuration
```bash
# Set GPU memory allocation
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:32

# Monitor GPU utilization
watch -n 1 nvidia-smi
```

**Section sources**
- [ffmpeg_hpe/docker-compose.yaml:80-99](file://ffmpeg_hpe/docker-compose.yaml#L80-L99)
- [Dockerfile_base:60-62](file://Dockerfile_base#L60-L62)

## Deployment Scenarios

### Local Development Setup

For development and testing on a single machine:

```bash
# Clone repository
git clone https://github.com/MeasurementsDTs/MeasurementsDTs.git
cd MeasurementsDTs

# Create environment
conda create -n hpe python=3.8.10 -y
conda activate hpe

# Install dependencies
conda install pytorch==2.4.1 torchvision==0.19.1 -c pytorch -y
conda install --file requirements.txt -y

# Build extensions
cd models/AlphaPose
bash build_extensions.sh
cd ../..

# Test installation
python3 main.py --help
```

### Containerized Deployment

For production and benchmarking scenarios:

```bash
# Build base image
docker build -f Dockerfile_base -t hpe-base .

# Run single container
docker run --gpus all \
  -v $(pwd)/models:/app/models \
  -v $(pwd)/videos:/videos \
  -v $(pwd)/results:/output \
  hpe-base \
  python3 main.py --method movenet --input /videos/sample.mp4 --csv --output_dir /output
```

### Cloud Deployment

For cloud-based deployments with GPU instances:

```bash
# Pull official image
docker pull pytorch/pytorch:2.4.1-cuda12.1-cudnn9-devel

# Deploy with NVIDIA runtime
docker run --runtime=nvidia \
  --gpus all \
  -e NVIDIA_VISIBLE_DEVICES=all \
  -e NVIDIA_DRIVER_CAPABILITIES=compute,utility,video \
  -v /path/to/models:/app/models \
  -v /path/to/videos:/videos \
  -v /path/to/results:/output \
  pytorch/pytorch:2.4.1-cuda12.1-cudnn9-devel \
  python3 main.py --method openpose --input rtsp://broker:8554/stream
```

**Section sources**
- [Dockerfile_base:1-93](file://Dockerfile_base#L1-L93)
- [ffmpeg_hpe/run_experiment.sh:306-308](file://ffmpeg_hpe/run_experiment.sh#L306-L308)

## Validation Steps

### Installation Verification

Test the installation with basic functionality checks:

```bash
# Test Python imports
python3 -c "
import torch
import openvino as ov
import cv2
import numpy as np
print('PyTorch version:', torch.__version__)
print('OpenVINO version:', ov.__version__)
print('CUDA available:', torch.cuda.is_available())
print('GPU count:', torch.cuda.device_count())
"

# Test model loading
python3 main.py --method movenet --input unit_tests/images/testImage.jpg --save_image
```

### Performance Testing

Run performance benchmarks to validate system configuration:

```bash
# Benchmark MoveNet performance
docker compose -f ffmpeg_hpe/docker-compose.yaml up -d rtsp-broker
docker compose -f ffmpeg_hpe/docker-compose.yaml up -d streamer
docker compose -f ffmpeg_hpe/docker-compose.yaml up -d hpe

# Monitor performance
docker compose -f ffmpeg_hpe/docker-compose.yaml up -d perf_monitor
docker compose -f ffmpeg_hpe/docker-compose.yaml up -d gpu-metrics

# Run experiment script
cd ffmpeg_hpe
./run_experiment.sh movenet
```

### Network Connectivity Test

Verify streaming connectivity:

```bash
# Test RTSP stream
ffprobe -v quiet -rtsp_transport tcp -read_intervals "%+#1" rtsp://localhost:8554/stream

# Test HTTP stream
curl -I http://localhost:8089/stream.h264

# Check port availability
netstat -tulpn | grep 8554
```

**Section sources**
- [ffmpeg_hpe/run_experiment.sh:268-297](file://ffmpeg_hpe/run_experiment.sh#L268-L297)
- [ffmpeg_hpe/run_experiment.sh:394-405](file://ffmpeg_hpe/run_experiment.sh#L394-L405)

## Troubleshooting Guide

### Common Installation Issues

#### CUDA Compatibility Problems
```bash
# Check CUDA version compatibility
nvcc --version
nvidia-smi

# Verify CUDA toolkit installation
ls /usr/local/cuda*

# Check PyTorch CUDA compatibility
python3 -c "import torch; print(torch.version.cuda)"
```

#### OpenVINO Installation Issues
```bash
# Verify OpenVINO installation
python3 -c "import openvino; print(openvino.__version__)"

# Check available devices
python3 -c "
from openvino.runtime import Core
core = Core()
print('Available devices:', core.available_devices)
"

# Reinstall OpenVINO
pip uninstall openvino
pip install openvino-dev[onnx,tensorflow2,pytorch,caffe]==2024.4.0
```

#### Model Loading Failures
```bash
# Verify model files exist
ls -la models/

# Check model file integrity
file models/AlphaPose/pretrained_models/fast_res50_256x192.pth

# Redownload corrupted models
cd models/AlphaPose
rm pretrained_models/fast_res50_256x192.pth
wget "https://drive.google.com/uc?export=download&id=1p6bi10UybpUIcq5D2XDsgQRLPJIr2RyI" -O pretrained_models/fast_res50_256x192.pth
```

#### Docker GPU Issues
```bash
# Check NVIDIA container toolkit
nvidia-container-toolkit --version

# Verify GPU access in container
docker run --rm --gpus all nvidia/cuda:12.1-base-ubuntu20.04 nvidia-smi

# Check Docker daemon configuration
cat /etc/docker/daemon.json

# Restart Docker service
sudo systemctl restart docker
```

### Performance Issues

#### Memory Allocation Problems
```bash
# Check available memory
free -h
nvidia-smi

# Adjust memory allocation
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:32

# Monitor memory usage during processing
watch -n 1 nvidia-smi
```

#### Threading and CPU Performance
```bash
# Check available CPU cores
nproc

# Configure OpenVINO threads
export OV_THREADS=4
export OV_CPU_PINNING=true

# Disable hyperthreading if needed
echo "performance" | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
```

**Section sources**
- [ffmpeg_hpe/run_experiment.sh:44-67](file://ffmpeg_hpe/run_experiment.sh#L44-L67)
- [ffmpeg_hpe/docker-compose.yaml:156-163](file://ffmpeg_hpe/docker-compose.yaml#L156-L163)

## Performance Considerations

### GPU Optimization

The project supports multiple GPU architectures and provides automatic optimization:

```bash
# Set CUDA architecture for your GPU
export TORCH_CUDA_ARCH_LIST=8.6  # For Ampere GPUs
export TORCH_CUDA_ARCH_LIST=7.5  # For Turing GPUs
export TORCH_CUDA_ARCH_LIST=7.0  # For Pascal GPUs

# Configure OpenVINO for optimal performance
export OV_MODE=latency
export OV_THREADS=4
export OV_CPU_PINNING=true
export OV_HYPER_THREADING=false
```

### Memory Management

```bash
# Configure PyTorch memory allocation
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:32

# Monitor memory usage
watch -n 1 nvidia-smi

# Optimize for different model types
# MoveNet: minimal memory requirements
# HigherHRNet: 1.5GB per vCPU minimum
# OpenPose: 8GB fixed for GPU methods
```

### Streaming Performance

```bash
# Configure OpenCV for RTSP streaming
export OPENCV_FFMPEG_CAPTURE_OPTIONS=rtsp_transport;tcp
export OPENCV_FFMPEG_OPEN_TIMEOUT=300000
export OPENCV_FFMPEG_READ_TIMEOUT=300000

# Monitor network bandwidth
iftop -i eth0
```

## Conclusion

The MeasurementsDTs project provides a comprehensive solution for 2D Human Pose Estimation with robust installation and deployment options. By following this guide, you can successfully set up the project for local development, containerized deployments, or cloud-based production environments.

Key success factors include:
- Exact version compliance for Python, OpenVINO, and CUDA
- Proper GPU driver and NVIDIA Container Toolkit installation
- Correct model placement and verification
- Appropriate environment variable configuration
- Thorough validation and performance testing

The project's modular design allows for flexible deployment scenarios, from single-machine development to large-scale cloud deployments with automated benchmarking capabilities. Regular validation and monitoring ensure optimal performance across different hardware configurations and use cases.