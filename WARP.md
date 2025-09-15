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





Of course. I have structured the performance data and analysis into a format that is easy to copy and paste directly into a Google Doc.

Simply copy the entire content below, open a new Google Doc, and paste it. The formatting (headings, bold text, table) will be preserved.

***

### **Performance Comparison of Pose Estimation Methods**

**Video Source Information:**
*   **Duration:** 2 minutes 31.52 seconds (151.52 seconds)
*   **Original Resolution:** 1920×1080 (Full HD)
*   **Frame Rate:** 25 FPS
*   **Total Frames:** 3,788 frames
*   **Streamed Resolution:** 1280×720 (via FFmpeg)

**Test Setup:**
*   **Device:** CPU-only processing
*   **Streamer:** Custom Flask server using FFmpeg (`app_ffmpeg.py`)
*   **Stream Protocol:** MJPEG over HTTP multipart/x-mixed-replace

---

### **Performance Results Summary Table**

| Method     | Total Time (mm:ss) | Real-Time Factor | Approx. FPS | CPU Usage | User Time (s) | System Time (s) |
|------------|--------------------|------------------|-------------|-----------|---------------|-----------------|
| **MoveNet**    | ~2:30              | ~1.0x           | ~25         | 203-255%  | 270 - 334     | 43 - 46         |
| **OpenPose**   | ~2:35 - 3:58       | ~1.0x - 1.6x    | ~16 - 24    | 309-431%  | 600 - 661     | 70 - 75         |
| **AE1**        | ~4:39 - 6:08       | ~1.8x - 2.4x    | ~10 - 14    | 386-483%  | 1178 - 1237   | 172 - 188       |
| **HRNet**      | ~21:30 - 25:07     | ~8.5x - 9.9x    | ~2.5 - 3    | 480-537%  | 6373 - 6619   | 562 - 620       |
| **AlphaPose**  | **39:38**          | **15.7x**       | **~1.6**    | **469%**  | **8509**      | **2668**        |

*   **Real-Time Factor:** Values >1.0 are slower than real-time.
*   **FPS:** Effective frames processed per second.

---

### **Key Observations & Analysis**

1.  **MoveNet is the Optimal Choice for Real-Time Use:**
    *   **Fastest:** Processes the video at or very near real-time speed (1.0x factor).
    *   **Most Efficient:** Achieves this with the lowest CPU usage and system time overhead, indicating a highly optimized model for CPU deployment.

2.  **OpenPose is a Viable Alternative:**
    *   **Near Real-Time:** Can achieve near real-time performance (~1.0x factor in best case).
    *   **High CPU Utilization:** Effectively uses multiple CPU cores (over 400%) but is less optimized than MoveNet, leading to more variable and sometimes slower performance.

3.  **AE1 is for Less Stringent Latency Requirements:**
    *   **Moderate Speed:** Processes video about 2x slower than real-time. Suitable for applications where a short delay is acceptable.

4.  **HRNet and AlphaPose are Computational Heavyweights:**
    *   **Accuracy vs. Speed Trade-off:** These methods are likely chosen for high accuracy but are prohibitively slow for any real-time application on a CPU.
    *   **Extreme Latency:** Process the video 8.5 to 15.7 times slower than its actual duration.
    *   **High System Time (AlphaPose):** AlphaPose's exceptionally high "System Time" suggests significant input/output (I/O) overhead, possibly from reading/writing intermediate data or model loading operations, compounding its slowness.

5.  **Multi-core Utilization:**
    *   All methods successfully leverage multiple CPU cores (evident from CPU usage percentages far exceeding 100%).

---

### **Recommendations**

*   **For Real-Time Applications (e.g., live feedback):** Use **MoveNet**.
*   **For Accuracy-Critical, Non-Real-Time Analysis (e.g., processing recorded videos):** Consider **HRNet** or **AlphaPose**, accepting the long processing time.
*   **For a Balance of Established Accuracy and Good Performance:** **OpenPose** is a reasonable choice.
*   **For General-Purpose Use:** **MoveNet** provides the best balance of speed and efficiency on CPU hardware.

### **Streamer Implementation Notes**

The custom Flask server (`app_ffmpeg.py`) performed reliably, providing a steady MJPEG stream of the video file at the target resolution and framerate. This ensured that the performance bottlenecks measured were solely due to the pose estimation models and not the video streaming source.



1235u 

[OpenVINO Configuration]
  Requested settings: threads=8, mode=throughput, streams=2
  Effective settings:
    Performance mode: PerformanceMode.THROUGHPUT
    CPU threads: 8
    CPU streams: 2
    CPU pinning: True
    Hyper-threading: False


ae1 - Inference time: 80.8ms (11.9 FPS)
movenet - Inference time: 18.7ms (62.9 FPS)