# AGENTS.md — MeasurementsDTs

## Project Overview

2D Human Pose Estimation (HPE) benchmark suite with a containerised performance
measurement platform. Runs five HPE backends (AlphaPose, MoveNet, OpenPose,
HigherHRNet, EfficientHRNet) against image, video, directory, webcam, and
RTSP-stream inputs. Outputs annotated frames and COCO-format JSON/CSV.

**Stack:** Python 3.8.10 · OpenVINO 2024.4.0 · PyTorch 2.4.1+cu121 · OpenCV · Docker · NVIDIA DCGM/NVIDIA-SMI

---

## Build & Run

### HPE Inference
```bash
python3 main.py --method movenet --input unit_tests/images/testImage.jpg --save_image
python3 main.py --method alphapose --input unit_tests/images/ --json
python3 main.py --method ae1 --input unit_tests/video/giphy.gif --save_video
python3 main.py --help
```

### Tests
```bash
python3 -m pytest tests/ -v
```

### Experiment Rigs (Docker)
```bash
# Baseline CPU monitoring
cd monitor_hpe && ./run_experiment.sh [METHOD] [VIDEO_FILE]

# RTSP stream + full monitoring stack
cd ffmpeg_hpe && ./run_experiment.sh [METHOD]

# DASH/HTTP caching (separate research thread)
cd recent-dash && ./run_experiment.sh
```

### Environment Setup
```bash
conda create -n hpe python=3.8.10 -y
conda activate hpe
conda install pytorch==2.4.1 torchvision==0.19.1 -c pytorch
conda install --file requirements.txt
bash models/AlphaPose/build_extensions.sh
```

GPU inference requires CUDA 12.x and an NVIDIA driver. MoveNet and HigherHRNet
fall back to CPU automatically.

---

## Code Style

- **Python 3.8 compatible** — no walrus operator, no `match` statements.
- **No type annotations** — project-wide rule.
- 4-space indentation. Match the surrounding file's style exactly.
- Module-level globals in `evaluator.py` are intentional (accumulator pattern).

---

## Repository Layout

```
main.py                        # CLI entry point
base_hpe.py                    # Abstract BaseHPE + Body/Padding types
openvino_base_hpe.py           # OpenVINO backend (OpenPose, HigherHRNet, EfficientHRNet)
movenet_hpe.py                 # MoveNet backend (OpenVINO, CPU only)
alphapose_hpe.py               # AlphaPose backend (PyTorch + YOLO)
utils/
  evaluator.py                 # COCO JSON/CSV output + Tx bandwidth
  visualizer.py                # OpenCV skeleton rendering
tests/
  test_hpe_regressions.py      # Regression tests (MoveNet, OpenPose, AlphaPose)
models/
  AlphaPose/                   # AlphaPose source + Cython extensions
  MoveNet/                     # OpenVINO IR (not committed)
  OpenVINO/                    # model_api + IR (not committed)
dev_tools/
  stream_video_server.py       # Flask MJPEG for local testing
monitor_hpe/                   # Rig 1: CPU monitoring
ffmpeg_hpe/                    # Rig 2: RTSP stream + full stack
recent-dash/                   # Rig 3: DASH/HTTP caching
Measure_Flops/                 # GPU FLOPS via Nsight Compute
Measure_gpu_dcgm/              # GPU power/temp/util via nvidia-smi
Measure_plot_cpu_perf/         # CPU cycles via perf stat
Dockerfile_base                # Active HPE container image
docker-compose.yml             # GPU observability stack
```

---

## Architecture

### HPE Pipeline

`BaseHPE` (abstract) handles input routing, main loop, padding/resize, and
output saving. Concrete subclasses implement:

| Method | Responsibility |
|---|---|
| `load_model()` | Load weights, compile graph |
| `run_model(padded)` | Run inference → raw predictions |
| `postprocess(predictions)` | Convert to `List[Body]` |

`AlphaPoseHPE` overrides `set_padding` and `pad_and_resize` (internal preprocessing).

### Benchmarking Platform

Each rig follows: `run_experiment.sh` → cleanup → start server → start HPE →
start sidecars → wait → collect → teardown. Results go to timestamped directories.

### Network Monitoring (TX vs RX)

| Direction | Tool | Container | Mechanism |
|---|---|---|---|
| **TX** | `bpftrace sys_enter_sendto` | `perf_monitor` | Syscall tracepoint, PID-filtered |
| **RX** | `bcc_rx_bytes.py` | `bcc-tracer` | BPF socket filter, IP/port-filtered |

**Rule:** Use `hpe_video_rx.csv` for RX, `network_stats.csv` for TX. Never use
the RX column from `network_stats.csv` — it's always ~0.

---

## Contributing Guidelines

### Adding a New HPE Backend
1. Subclass `BaseHPE` in `<name>_hpe.py`
2. Implement `load_model`, `run_model`, `postprocess`, define `LINES_BODY`
3. Register in `main.py` → `method_map` and argparse choices
4. Document model files in `README.md`

### Adding a New Experiment Rig
1. Create folder with `run_experiment.sh` + `docker-compose.yaml`
2. Follow lifecycle: cleanup → start server → start HPE → sidecars → wait → collect → teardown
3. Write results to timestamped subdirectory
4. Document in `README.md`

### Commit Style
Imperative subject; body explains *what* and *why*. One logical change per commit.
```
Add option to measure the produced data volume per time period
Fix OpenVINO projection and timeout routing regressions
```

---

## Important Rules

- **Model weights** (`.bin`, `.pth`, `.weights`) are **never committed**. Download paths in `README.md`.
- **Output** goes to `out/` (gitignored). Experiment results go to timestamped dirs per rig.
- **Docker:** `Dockerfile_base` is the active HPE image. Other root-level Dockerfiles are legacy.
- **No type annotations.** Enforced project-wide.
- **Do not refactor** `evaluator.py` globals without discussion.

---

## Known Limitations

| Component | Limitation | Workaround |
|---|---|---|
| `monitor_pid.sh` | `netif_receive_skb` PID filter always reads ~0 (softirq context) | Use `bcc-tracer` for RX |
| `alphapose_hpe.py` | Batch parallelism for directory input not implemented | Sequential processing only |
| `visualizer.py` | Keypoint colouring uses simple model-agnostic rule | Works for all models but not optimal |
| Root files | Dev artefacts (`full_shell_history.txt`, `hist.txt`, `bug.md`, `*.bak`) need cleanup | Ignore — no functional impact |

---

## Further Reading

- **[CHANGELOG.md](.qoder/repowiki/en/CHANGELOG.md)** — Complete project history, all fixes, architecture decisions
- **[ONBOARDING.md](ONBOARDING.md)** — Comprehensive newcomer guide (1100+ lines)
- **[AGENTS-IMPROVEMENT-SPEC.md](AGENTS-IMPROVEMENT-SPEC.md)** — Audit findings and improvement specs
- **[docs/session-report-2026-05-06.md](docs/session-report-2026-05-06.md)** — Full audit report
- **`monitor_hpe/USAGE.md`** — Monitor rig usage guide
- **`monitor_hpe/SCALING_GUIDE.md`** — Auto-scaling (4–32 vCPU VMs)
- **`ffmpeg_hpe/DYNAMIC_RESOURCE_ALLOCATION.md`** — FFmpeg rig resource allocation
