# CHANGELOG

All notable changes to the MeasurementsDTs project.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Dynamic resource allocation system for HPE containers with environment variable management
  - `HPE_CPU_LIMIT`, `HPE_CPU_RESERVATION` for CPU allocation
  - `HPE_MEMORY_LIMIT`, `HPE_MEMORY_RESERVATION` for memory allocation
  - Automatic calculation based on system vCPUs and HPE method requirements
- BCC-based TX byte counter (`bcc_tx_bytes.py`) complementing RX byte counter
  - 10ms granularity measurements for precise bandwidth analysis
  - Dual-direction TX/RX monitoring for complete network traffic analysis
- Auto-scaling behavior for 4-32 vCPU VMs (documented in `monitor_hpe/SCALING_GUIDE.md`)
- Hardware applicability table comparing cloud VM vs bare metal behavior (documented in `ONBOARDING.md`)

### Changed
- **Migrated from HTTP H.264 streaming to RTSP-based streaming pipeline**
  - Replaced legacy `h264-streaming-server` (port 8089) with MediaMTX RTSP broker (port 8554)
  - Streamer service now uses `jrottenberg/ffmpeg:4.4-nvidia` with NVENC hardware encoding
  - HPE application consumes RTSP stream with TCP transport for reliable packet capture
  - HLS debugging support on port 8888
- RTSP broker (MediaMTX) and streamer services added to Docker Compose for handling increased streaming demands
- Resource allocation strategy updated with dynamic CPU and memory limits based on system vCPUs
- Monitoring capabilities enhanced with dual-direction traffic measurement (TX/RX)
- GPU metrics collection improved with controlled resource limits (0.1 CPU, 128M memory)
- Performance monitor resource allocation optimized (0.25 CPU, 256M memory)
- BPF tracer enhanced with 10ms polling interval for synchronized TX/RX comparison

### Fixed
- IP/port BPF filter re-enabled in `bcc_rx_bytes.py` — now counts only video stream traffic
- Plot scripts no longer use hardcoded absolute paths — accept CSV path as CLI arg
- `plot_smi_output.py` column names now match `run_nvidia_dcgm.sh` output
- Docker Compose build context changed from hardcoded path to relative `..`
- `run_experiment.sh` service name corrected from `trace_container` to `bcc-tracer`
- `monitor_pid.sh` double-write bug fixed — each entry written once
- `entrypoint.sh` GPU metrics cleanup moved to EXIT trap (previously unreachable after `exec`)
- CPU% measurement replaced from `pidstat` (blocks 1s) with `/proc/$PID/stat` delta (500ms cadence)
- `perf_monitor` output filename corrected to `pid_metrics.csv`
- BCC tracer output filename corrected to `hpe_video_rx.csv`
- HPE container output (keypoint CSVs/JSON) now copied to results directory
- `plot_graph.py` now uses Agg backend and saves PNGs (no `plt.show()` blocking)

### Removed
- HTTP streaming server and related infrastructure (replaced by RTSP pipeline)
- Legacy HTTP stream byte-reader from `cuda-dev` branch
- `PoseMonitor` class (deprecated)
- `video_detection.py` module (deprecated)
- CLI args `--timeout` and `--max-frames` (removed for simplicity)
- Dual logging system (file + structured JSONL)
- `optimizations/` folder (CPU tuning now integrated into main codebase)
- `OPTIMIZATION_PLAN.md` (completed and superseded by implementation)

---

## [2026-05] — Full Audit and Bug-Fix Pass

**Branch:** `perf-tuning-base`  
**Commits:** `256a21c`, `3e09d55`, `b6a9fd2`, `3c006cf`, `7493830`, `76b8f30`

### Architecture Changes
- Restructured to use RTSP streaming instead of legacy HTTP H.264 streaming server
- Updated Docker Compose configuration to reflect new service dependencies and networking
- Revised component analysis to reflect RTSP broker (rtsp-broker:8554) and streamer service
- Enhanced documentation to reflect the migration from HTTP-based to RTSP-based streaming

### Bug Fixes (14 issues resolved)
See [docs/session-report-2026-05-06.md](docs/session-report-2026-05-06.md) for complete audit.

### Documentation
- Expanded README with newcomer orientation, experiment rigs table, known issues table
- Added ONBOARDING.md comprehensive guide (1100+ lines)
- Created AGENTS.md for AI agent guidance
- Auto-generated repowiki under `.qoder/repowiki/en/`
- Documented RTSP architecture migration in wiki pages

---

## [2025-09] — HTTP Streaming & Async Processing

**Branch:** `cuda-dev`  
**Last commit:** `7f0a1cc` (Sep 18, 2025)

### Added
- HTTP stream input support for IP camera testing
- Async/threaded OpenVINO HPE processing
- `--timeout` and `--max-frames` CLI arguments
- `PoseMonitor` class for pose tracking
- `video_detection.py` for input type detection
- Dual logging system (file + structured JSONL)
- AlphaPose notebook for interactive experimentation
- CUDA upgrade scripts (`upgrade_cuda.sh`)
- Dockerfile for OpenCV+FFmpeg+CUDA build

### Changed
- COCO output field renamed from `frame_number` to `image_id`
- OpenVINO configuration made env-var driven (`OV_THREADS`, `OV_MODE`, etc.)
- Multi-stage Docker builds introduced

### Infrastructure
- FFmpeg+CUDA Docker build attempts (`Dockerfile_optimized_multistage_v4`)
- NVENC encoding testing with various quality presets
- Disk space optimization for Docker builds

---

## [2025-08] — OpenVINO CPU Tuning & VPS Deployment

### Added
- OpenVINO CPU performance optimization for 4-vCPU VPS
- Thread/hint/pinning configuration experimentation
- WARP.md documentation
- AlphaPose CPU fixes for Apple M1

### Changed
- Extensive `OV_*` environment variable tuning
  - `OV_MODE=latency/throughput`
  - `OV_STREAMS` configuration
  - `OV_THREADS` optimization
- MoveNet CPU testing with different configurations

### Infrastructure
- Deployed to 4-vCPU VPS environment
- Gitignore cleanup for model files

---

## [2025-07] — Dockerized HPE Experiments

### Added
- `ffmpeg_hpe/` experiment rig with full monitoring stack
- `monitor_hpe/` baseline CPU monitoring rig
- GPU metrics collection via `run_nvidia_dcgm.sh`
- Performance monitoring via `monitor_pid.sh`
- BPF-based traffic tracing (`bpftrace-tracer/`)

### Experiments Conducted
- MoveNet GPU inference (Jul 14)
- AlphaPose GPU inference (Jul 14)
- OpenPose CPU inference (Jul 14)
- Multiple CPU runs across VGA and HD resolutions (Jul 15)
- MISO video testing

### Infrastructure
- 13 result directories generated
- Atuin shell history briefly active (Jul 11)
- Heavy `perf` profiling on AMD EPYC 7551P

---

## [2025-06] — Initial Setup & CPU Profiling

### Added
- AMD EPYC 7551P (32-core) server setup
- CPU profiling with `perf` monitoring
- System information collection (`cpuid`, `lscpu`, `cpupower`, `lsmem`, `lshw`)
- Monitoring tools: `btop`, `htop`

### First Artifacts
- `results_perf_AMD_EPYC_7551P_..._20250619_143126` (Jun 19)
- 7 result directories on Jun 23 — heavy CPU benchmarking day

---

## [Pre-2025-06] — HPE Inference Library

### Core Features
- Five 2D Human Pose Estimation backends:
  - **AlphaPose** (PyTorch + YOLO detector, GPU-first)
  - **MoveNet** (OpenVINO runtime, CPU only)
  - **OpenPose** (OpenVINO backend)
  - **HigherHRNet** (OpenVINO backend)
  - **EfficientHRNet** (OpenVINO backend, methods: ae1/ae2/ae3)
- Unified CLI interface (`main.py`)
- Input support: image, video, directory, webcam, HTTP/RTSP stream
- COCO-format JSON/CSV output
- OpenCV visualization and annotation

### Architecture
- `BaseHPE` abstract class defines:
  - Input routing and type detection
  - Main processing loop
  - Padding/resize logic
  - Frame dispatch
  - Output saving
- Concrete subclasses implement:
  - `load_model()` — weight loading and graph compilation
  - `run_model(padded)` — inference execution
  - `postprocess(predictions)` — conversion to `List[Body]`

---

## Infrastructure Evolution

### NVIDIA Driver & Kernel
- **Early 2026:** Painful driver upgrade to `nvidia-driver-570`
  - Installed `linux-generic-hwe-20.04` (kernel 5.15)
  - Fixed `apt` broken packages, GRUB EFI issues
  - Switched apt mirrors to resolve download issues
  - Multiple reboots, CUDA repo pin conflict resolution
  - Finally achieved working `nvidia-smi` and Docker GPU passthrough

### CPU Governor & Network Monitoring
- **Early-Mid 2026:**
  - Set CPU to `performance` governor
  - Installed `hwloc`, `nethogs`, `iftop` for network monitoring
  - Investigated `lo` interface traffic (RX/TX discrepancy)
  - Pulled `madtune/opencv-cuda:4.10.0` Docker image

### OpenVINO Optimization
- **Mid 2026:** Final optimization round
  - Extensive env var tuning
  - AlphaPose on GPU, OpenPose and MoveNet on CPU
  - Network traffic analysis with `nethogs` and `iftop`
  - Cleaned old model files (`rm -rf models/ONNX/`)

---

## Branch History

| Branch | Last Commit | Purpose |
|---|---|---|
| `perf-tuning-base` | May 2026 | Performance tuning baseline — active branch |
| `cuda-dev` | 2025-09-17 | GPU/CUDA-specific optimizations |
| `pyav-integration` | 2025-09-17 | PyAV integration enhancements |
| `latest-alphapose-integration` | 2025-09-17 | Latest AlphaPose integration |
| `refactor/video-detection-consolidation` | 2025-09-16 | Video capture timeout improvements |
| `hpe-benchmark` | 2025-09-15 | HPE benchmark Docker Compose setup |
| `feat/ov-epyc-4vcpu` | 2025-08-30 | OpenVINO 4-vCPU configuration |
| `feat/openvino-opti-cpu` | 2025-08-28 | OpenVINO CPU performance configuration |
| `main` | N/A | Upstream default / stable |

---

## Canonical Hardware

**Current Target:** 8 vCPU / 16 GB RAM + RTX A4000 (AMD EPYC 7551P host)

**Historical Calibration:** 4 vCPU AMD EPYC 7551P (original optimization target)

The `optimizations/` folder was originally calibrated for 4 vCPU but runtime auto-detector adapts to actual core count. All documentation now reflects 8 vCPU as canonical deployment target.

---

## Known Issues

| # | Component | Issue | Status |
|---|---|---|---|
| 1 | `monitor_pid.sh` | `netif_receive_skb` bpftrace PID filter fires in softirq context — RX bytes always ~0 | ⚠️ Open — use `bcc-tracer` for accurate RX |
| 2 | `movenet_hpe.py` | Keypoint-level score filtering not yet applied to body score | ⚠️ Open |
| 3 | `alphapose_hpe.py` | Batch parallelism for directory input not implemented | ⚠️ Open |
| 4 | `visualizer.py` | Keypoint colouring logic only verified correct for MoveNet | ⚠️ Open |
| 5 | `openvino_base_hpe.py` | `results` variable may be unbound if `raw_result` is falsy | ⚠️ Open |
| 6 | `export_pose_results.py` | Global accumulator never reset between runs | ⚠️ Open |
| 7 | Root files | Development artefacts need cleanup (`full_shell_history.txt`, `hist.txt`, `bug.md`, `*.bak`) | ⚠️ Open |

---

## Notes

- Model weights (`.bin`, `.pth`, `.weights`) are **not committed** — listed in `.gitignore`
- All experiment results go to timestamped directories — runs never overwrite each other
- Docker images: `Dockerfile_base` is active HPE image; other Dockerfiles are iteration history
- Network monitoring: TX uses `perf_monitor` → `network_stats.csv`; RX uses `bcc-tracer` → `hpe_video_rx.csv`
- Never use RX column from `network_stats.csv` — it's always ~0 (PID filter doesn't work for RX)

---

*This changelog documents the evolution from initial HPE inference library through Docker-based benchmarking platform to current RTSP streaming architecture with comprehensive observability.*