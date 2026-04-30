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

**Stack:** Python 3.8.10 · OpenVINO 2024.2.0 · PyTorch 2.4.1+cu121 · OpenCV · Docker · NVIDIA DCGM

---

## Repository Layout

```
main.py                        # HPE CLI entry point
base_hpe.py                    # Abstract base class (BaseHPE) + Body/Padding types
openvino_base_hpe.py           # OpenVINO backend (OpenPose, HigherHRNet, EfficientHRNet)
movenet_hpe.py                 # MoveNet backend (OpenVINO runtime, CPU only)
alphapose_hpe.py               # AlphaPose backend (PyTorch + YOLO detector)
utils/
  export_pose_results.py       # COCO JSON/CSV serialisation + Tx bandwidth measurement
  visualizer.py                # OpenCV skeleton/keypoint rendering
models/
  AlphaPose/                   # AlphaPose source + Cython extensions (built via setup.py)
  MoveNet/                     # OpenVINO IR model files (not committed — see README)
  OpenVINO/                    # OpenVINO model_api + IR model files (not committed)
dev_tools/
  stream_video_server.py       # Flask MJPEG server for local IP-stream testing
unit_tests/
  images/                      # Sample images for manual smoke tests
  video/                       # Sample GIF for video/stream tests

# Benchmarking platform (this branch)
monitor_hpe/                   # Rig 1: baseline CPU monitoring (no streaming server)
ffmpeg_hpe/                    # Rig 2: H.264 stream + full monitoring stack
recent-dash/                   # Rig 3: DASH/HTTP caching experiment (separate research thread)
rtsp-ipcam/                    # Shared H.264 streaming server used by ffmpeg_hpe/
Measure_Flops/                 # Standalone: GPU FLOPS via Nsight Compute
Measure_gpu_dcgm/              # Standalone: GPU power/temp/util via nvidia-smi
Measure_plot_cpu_perf/         # Standalone: CPU cycles via perf stat
optimizations/                 # OpenVINO CPU thread/stream tuning for 4-vCPU cloud instances
Dockerfile_base                # Active HPE container image (used by monitor_hpe/ and ffmpeg_hpe/)
Dockerfile_optimized_multistage_v4  # Latest multi-stage build iteration
docker-compose.yml             # GPU observability stack (DCGM + Prometheus + Grafana)
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
- Python 3.8 compatible — no walrus operator, no `match` statements.
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
1. Create a new folder with `run_experiment.sh` and `docker-compose.yaml`.
2. Follow the existing lifecycle pattern (cleanup -> start server -> start HPE ->
   start sidecars -> wait -> collect -> teardown).
3. Write results to a timestamped subdirectory.
4. Document the rig in `README.md` under "Experiment Rigs".

### Model Files
Model weights are **not committed**. Listed in `.gitignore`. Never commit
`.bin`, `.pth`, or `.weights` files. Download paths are in `README.md`.

### Output Files
All HPE output goes to `out/` by default (gitignored). Experiment results go
into timestamped directories inside each rig folder. Do not hardcode other
output paths.

### Docker Images
`Dockerfile_base` is the active HPE container image. The other Dockerfiles at
the repo root are iteration history — do not use them for new work without
checking whether `Dockerfile_base` already covers the need.

### Known TODOs in Code
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
- The eBPF/bpftrace tracer (`bcc-tracer`) in `ffmpeg_hpe/` and `recent-dash/`
  is commented out — requires a kernel with debug symbols and is fragile.
- Several root-level files (`full_shell_history.txt`, `hist.txt`, `bug.md`,
  `*.bak`, `original.py`) are development artefacts that need cleanup.

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
cd ffmpeg_hpe   && ./run_experiment.sh movenet
cd recent-dash  && ./run_experiment.sh
```

### Standalone measurement tools
```bash
./Measure_Flops/measure_flops.sh python3 main.py --method movenet --input video.mp4
./Measure_gpu_dcgm/run_nvidia_dcgm.sh
./Measure_plot_cpu_perf/run_perf_plot.sh
```

### CPU optimisations
```bash
python3 optimizations/optimized_main.py --method openpose --input video.mp4 --device CPU --enable-cpu-opt
```

---

## Environment Setup

Requires a Conda environment — the devcontainer does **not** install
dependencies automatically.

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

## Commit Style

Imperative subject line; body explains *what* and *why*. Examples from history:

```
Add option to measure the produced data volume per time period
Resize/Pad input images based on the base model used
```

Keep commits focused on one logical change.
