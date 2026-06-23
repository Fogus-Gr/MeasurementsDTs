# AGENTS.md — MeasurementsDTs (`perf-tuning-base` branch)

Agent guidance for working in this repository.

## Project Overview

2D Human Pose Estimation (HPE) benchmark suite extended with a containerised
performance measurement platform. Runs multiple HPE backends (AlphaPose,
MoveNet, OpenPose, HigherHRNet, EfficientHRNet) against image, video,
directory, webcam, and IP-stream inputs. Outputs annotated frames and keypoint
data in COCO-format JSON/CSV.

The `perf-tuning-base` branch adds Docker-based experiment rigs for measuring
HPE inference performance — throughput, CPU/GPU utilisation, memory, and
network bandwidth — under realistic streaming conditions.

**Stack:** Python 3.9.13 · OpenVINO 2024.4.0 · PyTorch 2.4.1+cu121 · OpenCV · Docker · NVIDIA DCGM

---

## Repository Layout

```                                                                            
MeasurementsDTs/
├── main.py                     # HPE CLI entry point
├── base_hpe.py                 # Abstract base class + Body/Padding types
├── openvino_base_hpe.py        # OpenVINO backend (OpenPose, HigherHRNet, EfficientHRNet)
├── movenet_hpe.py              # MoveNet backend
├── alphapose_hpe.py            # AlphaPose backend (PyTorch + YOLO detector)
├── build_ffmpeg_cuda.sh        # Build FFmpeg with NVIDIA CUDA support
├── requirements.txt            # Pinned Python dependencies
├── AGENTS.md                   # This file — agent guidance
├── generate_wiki.py            # Multi-page HTML wiki generator
├── generate_single_wiki.py     # Single-page HTML wiki generator
│
├── utils/
│   ├── export_pose_results.py  # COCO JSON/CSV serialisation + Tx measurement
│   └── visualizer.py           # OpenCV skeleton/keypoint rendering
├── models/
│   ├── AlphaPose/              # AlphaPose source + Cython extensions
│   ├── MoveNet/                # OpenVINO IR model files (not committed)
│   └── OpenVINO/               # OpenVINO model_api + IR models (not committed)
├── docs/                       # Deep-dive documentation
│   ├── ONBOARDING.md           # Newcomer onboarding guide
│   ├── CPU_TUNING_GUIDE.md     # OpenVINO thread/stream tuning
│   ├── docker-services.md      # Dockerfile & compose reference
│   ├── experiment-scripts.md   # Experiment script flow
│   ├── bcc-bpf-tracing.md      # BPF network tracing internals
│   ├── plotting-analysis.md    # Plotting scripts & CSV formats
│   └── hpe-methods.md          # HPE class hierarchy & models
├── dev_tools/
│   └── stream_video_server.py  # Flask MJPEG server for IP-stream testing
├── unit_tests/
│   ├── images/                 # Sample images for smoke tests
│   └── video/                  # Sample GIF for video/stream tests
│
├── # Experiment rigs
├── monitor_hpe/                # Rig 1: baseline CPU monitoring
├── ffmpeg_hpe/                 # Rig 2: H.264 stream + GPU monitoring stack
├── ffmpeg_hpe_cpu/             # Rig 2b: CPU-only H.264 stream + monitoring
├── recent-dash/                # Rig 3: DASH/HTTP caching experiment
│
├── # Service implementations
├── rtsp-ipcam/                 # H.264 streaming server (used by ffmpeg_hpe/)
├── shared/perf_monitor/        # perf_monitor sidecar container
├── ffmpeg_hpe/bpftrace-tracer/ # BCC eBPF network tracer
├── ffmpeg_hpe/Dockerfile.gpu_metrics  # GPU metrics sidecar image
│
├── # Standalone tools
├── Measure_Flops/              # GPU FLOPS via Nsight Compute
├── Measure_gpu_dcgm/           # GPU power/temp/util via nvidia-smi
├── Measure_plot_cpu_perf/      # CPU cycles via perf stat
│
├── archive/
│   ├── optimizations/          # Retired OpenVINO CPU tuning scripts
│   └── dockerfiles/            # Archived Dockerfile iterations
│
├── Dockerfile_base             # Active HPE container image (GPU)
├── Dockerfile_cpu              # CPU-only HPE container image
└── docker-compose.yml          # GPU observability stack (DCGM + Prometheus + Grafana)
```

---

## Architecture

### HPE Pipeline

`BaseHPE` (abstract) handles input routing, the main loop, padding/resize,
frame dispatch, and output saving. Concrete subclasses implement:

| Method | Responsibility |
|---|---|
| `load_model()` | Load weights and compile inference graph |
| `run_model(padded)` | Run inference, return raw predictions |
| `postprocess(predictions)` | Convert raw output to `List[Body]` |

`AlphaPoseHPE` overrides `set_padding` and `pad_and_resize` — AlphaPose
handles its own preprocessing internally.

### Benchmarking Platform

Each experiment rig follows the same pattern:

```
<rig-folder>/
  run_experiment.sh     <- single entry point; orchestrates the full lifecycle
  docker-compose.yaml   <- service definitions for that rig
```

`run_experiment.sh` always:
1. Cleans up previous containers and CSV files
2. Starts the streaming server and waits for its healthcheck
3. Starts the HPE container (method and device passed as arguments)
4. Starts monitoring sidecars (perf, GPU, optional eBPF tracer)
5. Polls until the HPE container exits
6. Copies all CSVs and logs into `results_<container_type>_<cpu_model>_<timestamp>/`
7. Tears everything down

Results directories are always timestamped so runs never overwrite each other.

---

## Development Conventions

### Code Style
- Python 3.9 compatible — no walrus operator, no `match` statements.
- No type annotations currently in use; do not add them unless the whole file
  is being refactored.
- 4-space indentation. Match the surrounding file's style exactly.
- Module-level globals in `export_pose_results.py` are intentional (accumulator
  pattern); do not refactor to a class without discussing first.

### Adding a New HPE Backend
1. Subclass `BaseHPE` in a new file `<name>_hpe.py`.
2. Implement `load_model`, `run_model`, `postprocess`, and define `LINES_BODY`.
3. Register the method name in `main.py` -> `method_map` and `argparse choices`.
4. Document required model files in `README.md` under "Download pretrained models".

### Adding a New Experiment Rig
1. Create a new folder with an entry script (`run_experiment.sh` or `run_experiment_bcc.sh`) and `docker-compose.yaml`.
2. Follow the existing lifecycle pattern (cleanup -> start server -> start HPE ->
   start sidecars -> wait -> collect -> teardown).
3. Write results to a timestamped subdirectory.
4. Document the rig in `README.md` under "Experiment Rigs".

### Deep-Dive Docs
Refer to `docs/` for detailed subsystem reference:
- `ONBOARDING.md` — full project walkthrough
- `docker-services.md` — Dockerfile & compose reference
- `experiment-scripts.md` — experiment script flow
- `bcc-bpf-tracing.md` — BPF tracing internals
- `plotting-analysis.md` — plot scripts & CSV formats
- `hpe-methods.md` — HPE class hierarchy & models
- `CPU_TUNING_GUIDE.md` — OpenVINO thread/stream tuning

### Verification
After making changes, run the relevant checks. This repo has no formal test
framework — use smoke tests instead:
```bash
# HPE inference smoke test
python3 main.py --method movenet --input unit_tests/images/testImage.jpg --save_image --device CPU
python3 main.py --method alphapose --input unit_tests/images/ --json --device CPU
python3 main.py --method ae1 --input unit_tests/video/giphy.gif --save_video

# Experiment rig (requires Docker)
cd ffmpeg_hpe && ./run_experiment_bcc.sh movenet
```

No linter or type checker is configured. Mimic the style of files you modify.

### Model Files
Model weights are **not committed**. Listed in `.gitignore`. Never commit
`.bin`, `.pth`, or `.weights` files. Download paths are in `README.md`.

### Output Files
All HPE output goes to `out/` by default (gitignored). Experiment results go
into timestamped directories inside each rig folder. Do not hardcode other
output paths.

### Docker Images
`Dockerfile_base` is the active HPE container image (GPU, includes PyNvCodec).
`Dockerfile_cpu` is the CPU-only variant — identical except PyNvCodec build is
skipped (OpenCV fallback handles video decoding). Used by `ffmpeg_hpe_cpu/`.
The archived Dockerfiles under `archive/dockerfiles/` are iteration history —
do not use them for new work without checking whether `Dockerfile_base` or
`Dockerfile_cpu` already covers the need.

### Network Monitoring — TX vs RX Tool Split

The platform uses two different tools to measure network traffic. They are
complementary, not redundant. Understanding this split is essential before
modifying any monitoring code.

| Tool | Container | Direction | Mechanism | Status |
|---|---|---|---|---|
| `bpftrace sys_enter_sendto` in `monitor_pid.sh` | legacy PID monitor | **TX** (HPE → outside) | Syscall tracepoint — fires in HPE process context, PID filter valid only with a host-correct PID | legacy |
| `bcc_rx_bytes.py` | `bcc-tracer` | **RX** (stream → HPE) | BPF socket filter on `eth0`, filtered by streamer IP + port | ✅ works (filter re-enabled `256a21c`) |
| `bpftrace netif_receive_skb` in `monitor_pid.sh` | legacy PID monitor | RX (attempted) | Network tracepoint fires in softirq context — PID never matches HPE | ❌ always ~0 |

**Why TX and RX need different approaches:**
- `sendto()` is a syscall made by the HPE process — the kernel knows the PID,
  so bpftrace PID filtering works.
- Incoming packets are processed by the kernel network stack in softirq
  context before being associated with any process — PID filtering is
  impossible. Must filter by IP/port instead.

`bcc-tracer` runs in a container sharing HPE's network namespace
(`network_mode: service:hpe`) and attaches a BPF socket filter to `eth0`
filtering by streamer IP + HPE ephemeral port (auto-detected via `ss -ntp`
in `entrypoint.sh`).

**Rule:** for RX data use `traces/bcc/video_rx.csv` from `bcc-tracer`.
The active `ffmpeg_hpe/run_experiment_bcc.sh` path uses a host-PID process
monitor for HPE CPU/memory. Files ending in `*_Tx.csv` are HPE JSON output
payload bytes, not network TX. Never use the RX column from legacy
`network_stats.csv` — it is always ~0.

### Known Issues — Benchmarking Platform

The table below is the authoritative status of all confirmed bugs found during
a full audit of the benchmarking platform. Update it when fixing or discovering
issues.

| # | File | Issue | Status |
|---|---|---|---|
| 1 | `ffmpeg_hpe/bpftrace-tracer/bcc_rx_bytes.py` | IP/port BPF filter was disabled — counted all TCP traffic instead of video stream only | ✅ Fixed (`256a21c`) |
| 2 | `ffmpeg_hpe/plot_rx_bytes*.py` | Hardcoded absolute path to old VM — unusable on any other machine | ✅ Fixed (`3e09d55`) — now accepts CSV path as CLI arg |
| 3 | `ffmpeg_hpe/plot_smi_output.py` | Column names didn't match `run_nvidia_dcgm.sh` output — crashed on every run | ✅ Fixed (`3e09d55`) |
| 4 | `ffmpeg_hpe/docker-compose.yaml` | Build context hardcoded to `/home/user/MeasurementsDTs` | ✅ Fixed (`3e09d55`) — changed to `..` |
| 5 | `ffmpeg_hpe/run_experiment.sh` | Referenced `trace_container` service (commented out) instead of `bcc-tracer` | ✅ Fixed (`3e09d55`) |
| 6 | `monitor_hpe/monitor_pid.sh` | `write_net_stats()` wrote each entry twice | ✅ Fixed (`3e09d55`) |
| 7 | `ffmpeg_hpe/entrypoint.sh` | GPU metrics cleanup after `exec` was unreachable | ✅ Fixed (`3e09d55`) — moved to EXIT trap |
| 8 | Both `monitor_pid.sh` files | `ps -o %cpu` reports lifetime average, not per-interval CPU% | ✅ Fixed (`b6a9fd2`) — replaced with `/proc/$PID/stat` delta at 500ms |
| 9 | `ffmpeg_hpe/run_experiment.sh` | `perf_monitor` output filename wrong (`aggregated_metrics.csv`) | ✅ Fixed (`3c006cf`) |
| 10 | `ffmpeg_hpe/run_experiment.sh` | BCC tracer output filename wrong (`trace.csv` → `hpe_video_rx.csv`) | ✅ Fixed (`3c006cf`) |
| 11 | `ffmpeg_hpe/run_experiment.sh` | HPE container output (keypoint CSVs/JSON) never copied to results dir | ✅ Fixed (`3c006cf`) |
| 12 | Both `monitor_pid.sh` files | `netif_receive_skb` bpftrace PID filter fires in softirq context — RX bytes always ~0 | ⚠️ Open — use `bcc-tracer` for accurate RX |
| 13 | `monitor_hpe/plot_graph.py` | Calls `plt.show()` — blocks in headless containers | ⚠️ Open |
| 14 | `ffmpeg_hpe/plot_graph.py` | Headless-safe CPU/memory plot helper for `perf_metrics.csv` and legacy `pid_metrics.csv` | ✅ Implemented |
| 15 | `rtsp-ipcam/docker-compose.yml` | Volume mount hardcoded to `/home/user/MeasurementsDTs/videos/...` | ✅ Fixed (`09d4d71`) — changed to relative `../videos/` |
| 16 | `ffmpeg_hpe/run_experiment_bcc.sh` + `shared/perf_monitor/` | Host-PID monitor consumed a container-namespace PID, producing near-zero CPU and tiny memory for active HPE runs | ✅ Fixed — BCC rig now writes the host PID from `docker inspect` and measures the HPE process directly |
| 17 | `ffmpeg_hpe/validate_run.py` | `bcc_port_detection` regex only matched old log-grep format `"Monitoring HPE traffic on port"`, but `run_experiment_bcc.sh` writes `"BCC detected HPE video port:"` when `$detected_port` is set — caused spurious FAIL on every BCC run | ✅ Fixed — regex now accepts both formats |

### Known TODOs in HPE Inference Code
- `movenet_hpe.py`: keypoint-level score filtering not yet applied to body
  score (marked `# TODO`).
- `alphapose_hpe.py`: batch parallelism for directory input not implemented;
  bounding box is derived from keypoints, not from the detector.
- `visualizer.py`: keypoint colouring logic is only verified correct for
  MoveNet (marked `# TODO`).
- `openvino_base_hpe.py -> run_model`: `results` variable may be unbound if
  `raw_result` is falsy — needs a guard.
- `export_pose_results.py`: global accumulator never reset between runs —
  `reset_results()` exists but is never called.
- `recent-dash/` uses a separate host-networked packet tracer for DASH-only
  proxy RX/TX; do not apply `ffmpeg_hpe` BCC assumptions to that rig.


---

## Running the Project

### HPE inference
```bash
python3 main.py --method movenet --input unit_tests/images/testImage.jpg --save_image
python3 main.py --method alphapose --input unit_tests/images/ --json
python3 main.py --method ae1 --input unit_tests/video/giphy.gif --save_video
python3 main.py --help
```

### IP stream (dev tool)
```bash
python3 dev_tools/stream_video_server.py
python3 main.py --method movenet --input http://<your-ip>:8080/video_feed --save_video
```

### Experiment rigs
```bash
cd monitor_hpe  && ./run_experiment.sh
cd ffmpeg_hpe   && ./run_experiment_bcc.sh movenet
cd ffmpeg_hpe_cpu && ./run_experiment_cpu.sh movenet
cd recent-dash  && ./run_experiment.sh
```

**OpenVINO threading:** The `ffmpeg_hpe` rig uses `ffmpeg_hpe/.env` defaults (`OV_MODE=latency`, `OV_STREAMS=1`, `OV_THREADS=3`, plus matching `OMP_NUM_THREADS`, `MKL_NUM_THREADS`, and `OPENBLAS_NUM_THREADS`) via `docker-compose.yaml`. The `ffmpeg_hpe_cpu` rig uses `ffmpeg_hpe_cpu/.env.cpu` defaults tuned for a 6-vCPU VM (`OV_THREADS=4`, `HPE_CPUS=4.0`, `STREAMER_CPUS=1.0`). Without `OV_THREADS`, the code auto-sizes using cgroup-aware CPU detection (`sched_getaffinity`).

### Standalone measurement tools
```bash
./Measure_Flops/measure_flops.sh python3 main.py --method movenet --input video.mp4
./Measure_gpu_dcgm/run_nvidia_dcgm.sh
./Measure_plot_cpu_perf/run_perf_plot.sh  # See Measure_plot_cpu_perf/README.md for usage
```

### CPU optimisations
See `docs/CPU_TUNING_GUIDE.md` for instructions on how to properly tune OpenVINO threads and performance modes for the containerised rigs via `.env` files.
---

## Environment Setup

Requires a Conda environment — the devcontainer does **not** install
dependencies automatically.

```bash
conda create -n hpe-perf python=3.9.13 -y
conda activate hpe-perf
conda install pytorch==2.4.1 torchvision==0.19.1 -c pytorch
conda install --file requirements.txt
bash models/AlphaPose/build_extensions.sh
```

GPU inference requires CUDA 12.x and an NVIDIA driver. MoveNet and HigherHRNet
fall back to CPU automatically.

---

## Commit Style

Imperative subject line; body explains *what* and *why*. Examples from history:

```
Add option to measure the produced data volume per time period
Resize/Pad input images based on the base model used
```

Keep commits focused on one logical change.

---

## Session History

### May 2026 — Full audit and bug-fix pass

**Branch context recovered after VM loss.** Established that active work was
on `cuda-dev` around July–September 2025, then `perf-tuning-base` from
September 2025 onward. Commit `7f0a1cc` (Enhance video capture handling and
OpenVINO configuration, Sep 18 2025) was the last confirmed working point
before the VM was lost.

**Branch comparison (`cuda-dev` vs `perf-tuning-base`):**
`perf-tuning-base` is a stripped-down, production-focused rewrite of
`cuda-dev`. Key differences: removed HTTP stream byte-reader, structured
logging, `PoseMonitor`, `video_detection.py`.
Added two new multi-stage Dockerfiles. Changed COCO output field
`frame_number` → `image_id`. OpenVINO knobs hardcoded instead of env-var
driven.

**Wiki added to `perf-tuning-base`** (commits `343a114`, `5cbd7d5`,
`362127e`): auto-generated Qoder repowiki under `.qoder/repowiki/` covering
all major subsystems. Note: wiki contains stale references to the `cuda-dev` architecture (e.g. `optimizations/` folder, `pose_monitor.py`) and needs to be regenerated in `docs/new_wiki/`.

**Fixes applied** (all on `perf-tuning-base`, all pushed):

| Commit | What |
|---|---|
| `256a21c` | Re-enable IP/port BPF filter in `bcc_rx_bytes.py`; remove per-packet debug `bpf_trace_printk` |
| `3e09d55` | 7 fixes: plot hardcoded paths, `plot_smi_output.py` columns, docker-compose build context, `run_experiment.sh` service name, `monitor_pid.sh` double-write, `entrypoint.sh` EXIT trap, CPU% method |
| `b6a9fd2` | Replace `pidstat 1 1` (blocks 1s) with `/proc/$PID/stat` delta — preserves 500ms sampling cadence |
| `3c006cf` | Fix `run_experiment.sh` result collection: correct filenames for bcc-tracer and perf_monitor output, add HPE output copy step, guard `docker exec` calls against `set -e` |
| `7493830` | Expand README: newcomer orientation, experiment rigs table, known issues table |
| `aa9fc36` | Improve ffmpeg_hpe plot scripts: add markers, datetime formatting |
| `09d4d71` | Fix rtsp-ipcam volume mount: hardcoded absolute → relative |
| `ee014d5` | Add Measure_plot_cpu_perf README |
| `fee2ed4` | Update root-level docs and scripts: gcc-9→gcc, drop use_pooled_heatmaps, add wiki generators |
