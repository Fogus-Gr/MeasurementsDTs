# CHANGELOG

All notable changes to the MeasurementsDTs project.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased] — `final-merge-validation` branch

### Added
- Dynamic resource allocation system for HPE containers with environment variable management
  - `HPE_CPU_LIMIT`, `HPE_CPU_RESERVATION` for CPU allocation
  - `HPE_MEMORY_LIMIT`, `HPE_MEMORY_RESERVATION` for memory allocation
  - Automatic calculation based on system vCPUs and HPE method requirements
  - Auto-scaling for `ffmpeg_hpe` rig (`9d45a66`) and `monitor_hpe` rig (`14da4b6`)
  - Per-method resource tuning: GPU methods (alphapose/openpose) capped at 4 OV threads; OpenVINO methods scale threads with vCPU count; hrnet gets 1.5× memory floor
  - Documented in `ffmpeg_hpe/DYNAMIC_RESOURCE_ALLOCATION.md` and `monitor_hpe/SCALING_GUIDE.md` (`f1e2729`, `5d01c4b`)
- BCC-based TX byte counter (`bcc_tx_bytes.py`) complementing RX byte counter (`4491765`)
  - 10ms granularity measurements for precise bandwidth analysis
  - Dual-direction TX/RX monitoring for complete network traffic analysis
  - Filters by HPE PID via `/pids/hpe.pid`; writes `hpe_video_tx.csv`
- BCC polling rate now configurable via `BCC_POLL_INTERVAL_S` env var, defaulting to 10ms (`a1bba0a`)
- Auto-scaling behavior for 4–32 vCPU VMs (documented in `monitor_hpe/SCALING_GUIDE.md`)
- Hardware applicability table comparing cloud VM vs bare metal behavior (documented in `ONBOARDING.md`)
- `requirements_dev.txt` for development-only dependencies (`c6235f2`)
- RTSP support added to `base_hpe.py` input routing, OpenCV init, and HTTP fallback guard (`78b9df5`)
- `ffmpeg_hpe` now uses `Dockerfile_base` (HPE app image) instead of a separate Dockerfile (`ff6b34d`)

### Changed
- **Migrated from HTTP H.264 streaming to RTSP-based streaming pipeline** (`e5fee4b`, `553ec02`)
  - Replaced legacy `h264-streaming-server` (port 8089) with MediaMTX RTSP broker (port 8554)
  - Streamer service now uses `jrottenberg/ffmpeg:4.4-nvidia` with NVENC hardware encoding
  - HPE application consumes RTSP stream with TCP transport for reliable packet capture
  - HLS debugging support on port 8888
  - `bcc-tracer` entrypoint updated for RTSP port 8554 (`aad5940`)
  - `.env` updated for RTSP pipeline (`5d19bd1`)
- RTSP broker (MediaMTX) and streamer services added to Docker Compose for handling increased streaming demands
- Resource allocation strategy updated with dynamic CPU and memory limits based on system vCPUs
- Monitoring capabilities enhanced with dual-direction traffic measurement (TX/RX)
- GPU metrics collection improved with controlled resource limits (0.1 CPU, 128M memory) (`b16122d`)
- Performance monitor resource allocation optimized (0.25 CPU, 256M memory)
- BPF tracer enhanced with 10ms polling interval for synchronized TX/RX comparison
- `run_experiment.sh` (ffmpeg_hpe) RTSP startup hardened: ffprobe/MediaMTX REST API stream liveness check, video file pre-validation, container name release wait (`22684e1`)
- `openvino_base_hpe.py` OpenVINO env vars now read at runtime; `_configure_core()` uses `openvino.properties` API (`3161ac1`)
- `BaseHPE.IMAGE_EXTENSIONS` deduplicated — removed duplicate glob patterns (`da11ade`)
- `requirements_torch_cpu.txt` versions aligned with `requirements.txt` (2.2.1→2.4.1 / 0.17.1→0.19.1) (`54aa916`)
- `ffmpeg_hpe` GPU visibility split so the NVENC streamer keeps GPU access while CPU-only HPE methods run with GPU visibility disabled.
- `ffmpeg_hpe` sidecar CPU documentation now states the actual 2.1 CPU sidecar limit total.

### Fixed
- **Broken bounding boxes and skeletons on all OpenVINO models** — two-bug regression from `797089e` (Aug 2025) (`9031a24`)
  - `open_pose.py`: restored always-on dynamic `max_pool` NMS node; removed `use_pooled_heatmaps` conditional that disabled NMS
  - `openvino_base_hpe.py`: `target_size` set to `None` for all models (was passing hard-coded integers, corrupting coordinate scaling); `ae2`/`ae3` model paths corrected (`intel/` → `public/`)
- Stale `use_pooled_heatmaps: False` key removed from OpenPose config dict in `openvino_base_hpe.py` (`a851eaf`)
- Font scale in `base_hpe.py` FPS overlay was using height instead of width (`f_width` mislabel) (`a851eaf`)
- Missing `logging` import in `openvino_base_hpe.py` (`5ae86f2`)
- CPU-only PyTorch wheels not installable via `pip install -r` due to missing `--index-url` (`be34481`)
- `run_experiment.sh` (ffmpeg_hpe): RTSP pipeline wiring, stream liveness check, TCP transport enforcement (`553ec02`, `c36c65c`)
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
- `plot_graph.py` (ffmpeg_hpe) now validates CSV columns and emptiness before plotting (`54aa916`)
- `plot_graph.py` (monitor_hpe) now uses Agg backend and saves PNGs (no `plt.show()` blocking) (`76b8f30`)
- `bcc_tx_bytes.py`: `args->size` → `args->len` (correct `sys_enter_sendto` field); double-count on first packet fixed; `clear()` removed so map stays cumulative (`54aa916`)
- `entrypoint.sh` (bcc-tracer): `getent hosts` IPv4-only filter to avoid multi-line `STREAMER_IP`; replaced `exec` with plain call + `trap` so TX tracer receives SIGTERM and flushes on shutdown (`54aa916`)
- `_is_stream_url` type annotations removed (project no-annotations rule) (`54aa916`)
- ONBOARDING.md peak memory awk used `$3` (cpu%) instead of `$4` (mem_rss_kb) (`54aa916`)
- `.gitignore`: trailing whitespace on line 5; redundant `models/OpenVINO/pretrained_models/` directory-wide ignore removed (`54aa916`)
- `monitor_hpe/USAGE.md` hrnet memory corrected to 9GB (was 8GB; formula gives 9GB on 6-HPE-vCPU host) (`54aa916`)
- `bcc_rx_bytes.py` default polling interval aligned to 10ms and RX map initialization corrected to avoid double-counting the first matching packet.
- `bcc-tracer` entrypoint now propagates the foreground RX tracer exit code while still shutting down the TX tracer.
- `ffmpeg_hpe` and `monitor_hpe` experiment scripts now propagate failed or uninspectable HPE exits instead of reporting successful runs.
- `ffmpeg_hpe` startup log capture now tolerates early HPE exits so diagnostics can still be collected.
- `run_nvidia_dcgm.sh`, legacy `trace_video_traffic.sh`, and `monitor_hpe/run_experiment.sh` line endings normalized so Bash parses them on Windows/WSL checkouts.
- `Dockerfile_base` duplicate entrypoint copy/chmod removed; `visualizer.py` keypoint loop spacing cleaned up.
- Repowiki metadata now points to the real README instead of the stale "No readme file" placeholder.
- Dynamic resource allocation summary now mirrors the rounded hrnet memory calculation used by the experiment scripts.

### Removed
- `optimizations/` folder and associated scripts (`optimized_main.py`, `cpu_performance_optimizer.py`, `enhanced_openvino_hpe.py`, `optimizations/README.md`) — CPU tuning now integrated into main codebase via ENV vars (`76ac613`)
- HTTP streaming server and related infrastructure (replaced by RTSP pipeline)
- Legacy HTTP stream byte-reader from `cuda-dev` branch
- `PoseMonitor` class (deprecated)
- `video_detection.py` module (deprecated)
- CLI args `--timeout` and `--max-frames` (removed for simplicity)
- Dual logging system (file + structured JSONL)
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
| 2 | `movenet_hpe.py` | Keypoint-level score filtering not yet applied to body score | ✅ Fixed (`final-merge-validation`) — now uses mean keypoint score |
| 3 | `alphapose_hpe.py` | Batch parallelism for directory input not implemented | ⚠️ Open |
| 4 | `alphapose_hpe.py` | Bounding box derived from keypoints, not detector | ✅ Fixed (`final-merge-validation`) — uses detector bbox scaled to padded-frame coords |
| 5 | `visualizer.py` | Keypoint colouring logic only verified correct for MoveNet | ⚠️ Open (colouring rule unchanged; bounds guard added) |
| 6 | `openvino_base_hpe.py` | `results` variable may be unbound if `raw_result` is falsy | ✅ Fixed — `run_model` now returns `[], []` on falsy `raw_result` |
| 7 | `evaluator.py` | Global accumulator never reset between runs | ✅ Fixed — `reset_results()` called at top of both loop methods |
| 8 | Root files | Development artefacts need cleanup (`full_shell_history.txt`, `hist.txt`, `bug.md`, `*.bak`) | ⚠️ Open |
| 9 | `open_pose.py` + `openvino_base_hpe.py` | NMS disabled + wrong target_size — broken bounding boxes/skeletons on all OpenVINO models | ✅ Fixed (`9031a24`, `a851eaf`) |
| 10 | `bcc_tx_bytes.py` | `args->size` wrong field, double-count, `clear()` breaks delta | ✅ Fixed (`54aa916`) |
| 11 | `entrypoint.sh` | TX tracer orphaned on container stop; STREAMER_IP could be multi-line | ✅ Fixed (`54aa916`) |

---

## Notes

- Model weights (`.bin`, `.pth`, `.weights`) are **not committed** — listed in `.gitignore`
- All experiment results go to timestamped directories — runs never overwrite each other
- Docker images: `Dockerfile_base` is active HPE image; other Dockerfiles are iteration history
- Network monitoring: TX uses `perf_monitor` → `network_stats.csv`; RX uses `bcc-tracer` → `hpe_video_rx.csv`
- Never use RX column from `network_stats.csv` — it's always ~0 (PID filter doesn't work for RX)

---

*This changelog documents the evolution from initial HPE inference library through Docker-based benchmarking platform to current RTSP streaming architecture with comprehensive observability.*
