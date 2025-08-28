# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Repository Overview

This is a **2D Human Pose Estimation** research/benchmark repository that implements multiple HPE methods including AlphaPose, OpenPose, MoveNet, HigherHRNet, and EfficientHRNet variants. The codebase is designed for performance measurement and comparison of different pose estimation approaches on various input sources (images, videos, streams, webcams).

## Core Architecture

The project follows an abstract base class pattern with specialized implementations:

- **`BaseHPE`**: Abstract base class defining the common interface and workflow
- **`AlphaPoseHPE`**: PyTorch-based implementation with YOLO detection + AlphaPose pose estimation  
- **`MoveNetHPE`**: OpenVINO-based implementation of Google's MoveNet
- **`OpenVINOBaseHPE`**: Generic OpenVINO wrapper for Intel's pose estimation models (OpenPose, EfficientHRNet variants, HigherHRNet)

### Key Design Patterns

1. **Plugin Architecture**: Each HPE method is a separate class inheriting from `BaseHPE`
2. **Hardware Acceleration**: Supports both CPU and GPU inference with automatic fallback
3. **Input Flexibility**: Unified interface for images, directories, videos, streams, and webcams
4. **Output Standardization**: Common `Body` class for pose results with normalized coordinates
5. **Performance Monitoring**: Built-in measurement capabilities for throughput analysis

### Data Flow

```
Input → Preprocessing → Model Inference → Postprocessing → Visualization/Export
```

- **Preprocessing**: Padding, resizing, normalization specific to each model
- **Model Inference**: Device-specific execution (CPU/GPU)
- **Postprocessing**: Converting raw outputs to standardized `Body` objects
- **Export**: JSON (COCO format), CSV, images, or video output

## Essential Commands

### Environment Setup
```bash
# Create conda environment
conda create -n hpe python=3.8.10 -y
conda activate hpe

# Install PyTorch with CUDA support
conda install pytorch==2.4.1 torchvision==0.19.1 -c pytorch

# Install dependencies
conda install --file requirements.txt

# Build AlphaPose extensions (C++/CUDA components)
bash models/AlphaPose/build_extensions.sh
```

### Model Downloads
The repository requires downloading pretrained models manually using wget commands specified in the README. Models are organized under `models/` by framework:

- `models/AlphaPose/` - PyTorch weights and YOLO detector
- `models/MoveNet/` - OpenVINO IR files  
- `models/OpenVINO/` - Intel model zoo models

### Running Inference
```bash
# Single image with MoveNet
python3 main.py --method movenet --input unit_tests/images/testImage.jpg --save_image

# Directory of images with AlphaPose (batch processing)
python3 main.py --method alphapose --input unit_tests/images/ --json

# Video processing with EfficientHRNet
python3 main.py --method ae1 --input unit_tests/video/giphy.gif --save_video

# Real-time webcam with GPU
python3 main.py --method alphapose --input 0 --device GPU --save_video

# IP camera stream
python3 main.py --method movenet --input http://<ip>:8080/video_feed --save_video
```

### Development Tools
```bash
# Start video streaming server for testing
python3 dev_tools/stream_video_server.py

# Docker-based GPU monitoring (DCGM + Prometheus + Grafana)
docker-compose up -d

# Performance measurement with FLOPS counting  
bash Measure_Flops/measure_flops.sh
```

### Key Arguments
- `--method`: Choose HPE algorithm (`alphapose`, `movenet`, `openpose`, `hrnet`, `ae1`, `ae2`, `ae3`)
- `--device`: Hardware target (`CPU`, `GPU`)
- `--detbatch`: Detection batch size for AlphaPose
- `--measurement_interval_ms`: Monitoring granularity
- `--json/--csv`: Export pose data in structured formats
- `--save_image/--save_video`: Visual output options

## Hardware Support

**AlphaPose**: Full CUDA GPU acceleration including PyNvCodec video decoding
**MoveNet**: CPU only (OpenVINO limitation)  
**OpenVINO Models**: GPU support varies by model (check `MODEL_CONFIGS` in `openvino_base_hpe.py`)

The system automatically falls back to CPU when GPU is requested but unsupported.

## Performance Monitoring

The repository includes comprehensive performance measurement tools:

- **GPU Metrics**: NVIDIA DCGM integration via Docker Compose
- **CPU Profiling**: perf-based monitoring scripts
- **Network Traffic**: RX/TX analysis for streaming inputs
- **FLOPS Counting**: Computational complexity measurement
- **Throughput Analysis**: Frame processing rates with configurable intervals

## Testing Infrastructure

Use the `dev_tools/` directory for development workflows:
- IP camera simulation with Flask
- Adaptive video streaming servers  
- Docker containerization for reproducible environments

The project prioritizes reproducible benchmarking across different hardware configurations and input modalities.
